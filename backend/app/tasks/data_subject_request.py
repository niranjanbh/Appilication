from __future__ import annotations

import enum
import io
import json
import uuid
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.worker import celery_app


def _run_async(coro: object) -> None:
    import asyncio as _asyncio
    _asyncio.run(coro)  # type: ignore[arg-type]


def _jsonify(value: Any) -> Any:
    """Serialize ORM field values to JSON-safe primitives."""
    if value is None or isinstance(value, (str, int, float, bool, dict, list)):
        return value
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, bytes):
        return "[binary omitted]"
    return str(value)


def _rows_to_dicts(rows: list[Any], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    return [{f: _jsonify(getattr(row, f, None)) for f in fields} for row in rows]


_EXPORT_README = (
    "Kyros Clinic — Personal Data Export (DPDP Act, 2023 — right to access)\n"
    "====================================================================\n\n"
    "This archive contains the personal data Kyros Clinic holds about your\n"
    "account, exported on request. Each JSON file covers one data category.\n\n"
    "Not included here:\n"
    "  - Clinician-authored private notes form part of the medical record and\n"
    "    are retained under NMC/Telemedicine guidelines. Request them via a\n"
    "    formal medical-records request.\n"
    "  - Draft prescriptions that were never issued to you.\n\n"
    "Questions: privacy@kyrosclinic.com\n"
)


@celery_app.task(name="kyros.admin.process_data_export", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def process_data_export(self: object, user_id_str: str, request_id_str: str) -> None:
    _run_async(
        _process_data_export_async(uuid.UUID(user_id_str), uuid.UUID(request_id_str))
    )


@celery_app.task(name="kyros.admin.process_erasure", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def process_erasure(self: object, user_id_str: str, request_id_str: str) -> None:
    _run_async(
        _process_erasure_async(uuid.UUID(user_id_str), uuid.UUID(request_id_str))
    )


async def _process_data_export_async(
    user_id: uuid.UUID,
    request_id: uuid.UUID,
    db: object = None,
) -> None:
    """Build a ZIP of the user's exportable data and mark the DSR completed.

    In tests, pass db=<AsyncSession> to reuse the test transaction instead of
    opening a new session (which would not see uncommitted test fixtures).
    """
    import asyncio

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.enums import DataSubjectRequestStatus, PrescriptionStatus
    from app.integrations import s3
    from app.models.clinic import (
        Consultation,
        Diagnosis,
        LabReport,
        Patient,
        Prescription,
        PrescriptionItem,
    )
    from app.models.consent import ConsentRecord, DataSubjectRequest
    from app.models.education import EducationAssignment
    from app.models.identity import User
    from app.models.notifications import Notification
    from app.models.payment import Payment
    from app.models.wellness import HealthDatapoint, Reminder
    from app.repositories import consent as consent_repo

    async def _fetch(session: AsyncSession, stmt: Any) -> list[Any]:
        return list((await session.execute(stmt)).scalars())

    async def _run(session: AsyncSession, owns_session: bool) -> None:
        user = await session.scalar(select(User).where(User.id == user_id))
        if user is None:
            return

        sections: dict[str, Any] = {}

        # ── Account profile ───────────────────────────────────────────────────
        sections["profile.json"] = {
            f: _jsonify(getattr(user, f, None))
            for f in (
                "id", "role", "email", "phone", "phone_verified", "email_verified",
                "name", "date_of_birth", "gender", "city", "state",
                "language_preference", "timezone", "last_login_at", "created_at",
            )
        }

        # ── Account-scoped data (any role) ───────────────────────────────────
        sections["consent_records.json"] = _rows_to_dicts(
            await _fetch(session, select(ConsentRecord).where(ConsentRecord.user_id == user_id)),
            ("id", "consent_type", "version", "granted", "granted_at", "revoked_at", "consent_text_hash"),
        )
        sections["data_subject_requests.json"] = _rows_to_dicts(
            await _fetch(session, select(DataSubjectRequest).where(DataSubjectRequest.user_id == user_id)),
            ("id", "request_type", "status", "received_at", "completed_at"),
        )
        sections["reminders.json"] = _rows_to_dicts(
            await _fetch(session, select(Reminder).where(Reminder.user_id == user_id)),
            ("id", "type", "label", "schedule_cron", "schedule_interval_minutes", "active", "created_at"),
        )
        sections["notifications.json"] = _rows_to_dicts(
            await _fetch(session, select(Notification).where(Notification.user_id == user_id)),
            ("id", "template_name", "title", "body", "channels", "read_at", "sent_at"),
        )
        sections["payments.json"] = _rows_to_dicts(
            await _fetch(session, select(Payment).where(Payment.user_id == user_id)),
            ("id", "consultation_id", "amount_paise", "currency", "status",
             "gst_invoice_number", "created_at"),
        )
        sections["health_data.json"] = _rows_to_dicts(
            await _fetch(session, select(HealthDatapoint).where(HealthDatapoint.user_id == user_id)),
            ("id", "source", "type", "value", "measured_at", "created_at"),
        )

        # ── Patient-scoped clinical data (only if a patient profile exists) ──
        patient = await session.scalar(select(Patient).where(Patient.user_id == user_id))
        if patient is not None:
            sections["patient_profile.json"] = {
                f: _jsonify(getattr(patient, f, None))
                for f in (
                    "id", "kyros_patient_id", "abha_number", "primary_conditions",
                    "allergies", "chronic_conditions", "current_medications",
                    "emergency_contact", "intake_complete_at", "created_at",
                )
            }
            sections["consultations.json"] = _rows_to_dicts(
                await _fetch(session, select(Consultation).where(Consultation.patient_id == patient.id)),
                ("id", "doctor_id", "condition_category", "consultation_type",
                 "scheduled_start_at", "scheduled_end_at", "actual_start_at",
                 "actual_end_at", "status", "consultation_fee_paise", "discount_paise",
                 "cancellation_reason", "created_at"),
            )
            sections["diagnoses.json"] = _rows_to_dicts(
                await _fetch(session, select(Diagnosis).where(Diagnosis.patient_id == patient.id)),
                ("id", "consultation_id", "icd10_code", "icd10_description", "is_primary", "created_at"),
            )
            sections["lab_reports.json"] = _rows_to_dicts(
                await _fetch(session, select(LabReport).where(LabReport.patient_id == patient.id)),
                ("id", "source", "lab_name", "report_date", "original_filename",
                 "status", "parsed_json", "patient_attention_flags", "created_at"),
            )
            sections["education_assignments.json"] = _rows_to_dicts(
                await _fetch(session, select(EducationAssignment).where(EducationAssignment.patient_id == patient.id)),
                ("id", "content_id", "consultation_id", "read_at", "notes", "created_at"),
            )

            # Issued prescriptions only — drafts are never patient-visible (security rule 2).
            rx_rows = await _fetch(
                session,
                select(Prescription).where(
                    Prescription.patient_id == patient.id,
                    Prescription.status != PrescriptionStatus.DRAFT,
                ),
            )
            sections["prescriptions.json"] = _rows_to_dicts(
                rx_rows,
                ("id", "consultation_id", "status", "signed_at", "version",
                 "diagnosis_note", "general_instructions", "created_at"),
            )
            rx_ids = [r.id for r in rx_rows]
            rx_items = (
                await _fetch(session, select(PrescriptionItem).where(PrescriptionItem.prescription_id.in_(rx_ids)))
                if rx_ids else []
            )
            sections["prescription_items.json"] = _rows_to_dicts(
                rx_items,
                ("id", "prescription_id", "drug_generic_name", "drug_form", "dosage",
                 "frequency", "duration_days", "instructions", "drug_schedule"),
            )

        # ── Build the ZIP ────────────────────────────────────────────────────
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.txt", _EXPORT_README)
            for name, payload in sections.items():
                zf.writestr(name, json.dumps(payload, ensure_ascii=False, indent=2))
        zip_bytes = buf.getvalue()
        zip_size = len(zip_bytes)

        # ── Upload to S3 (SSE-KMS) at a deterministic, DSR-derivable key ─────
        export_key = s3.data_export_s3_key(user_id, request_id)
        await asyncio.to_thread(
            s3.put_bytes,
            s3_key=export_key,
            data=zip_bytes,
            content_type="application/zip",
        )

        await consent_repo.update_data_subject_request_status(
            session,
            request_id=request_id,
            status=DataSubjectRequestStatus.COMPLETED,
            completed_at=datetime.now(UTC),
            notes=json.dumps({
                "zip_size_bytes": zip_size,
                "export_s3_key": export_key,
                "categories": sorted(sections.keys()),
            }),
        )
        if owns_session:
            await session.commit()

    if db is not None:
        assert isinstance(db, AsyncSession)
        await _run(db, owns_session=False)
    else:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as owned_db:
            await _run(owned_db, owns_session=True)


# NMC Medical Records statutory retention: 7 years from erasure date.
# This is a legal constant — changing it requires explicit code review and
# documented regulatory justification.
_NMC_RETENTION_YEARS = 7


async def _process_erasure_async(
    user_id: uuid.UUID,
    request_id: uuid.UUID,
    db: object = None,
) -> None:
    """Erasure with legal hold — DPDP §12 + TPG 2020 medical records retention.

    Steps:
      1. Anonymize PII on the user row (name, email, phone, dob, city/state, tokens, etc.)
      2. Revoke all refresh tokens.
      3. Apply 7-year NMC legal hold to all consultations + prescriptions.
      4. Mark DSR COMPLETED with audit notes.

    Idempotent: rows already erased (erased_at IS NOT NULL) or already on hold
    (legal_hold_until IS NOT NULL) are skipped. Safe to run twice.

    In tests, pass db=<AsyncSession> to reuse the test transaction.
    """
    from datetime import timedelta

    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.enums import DataSubjectRequestStatus
    from app.models.identity import RefreshToken, User
    from app.repositories import consent as consent_repo
    from app.repositories.erasure import anonymize_pii_values, apply_legal_hold

    async def _run(session: AsyncSession, owns_session: bool) -> None:
        now = datetime.now(UTC)

        # 1. Anonymize PII — only if not already erased (idempotency guard)
        pii_values = anonymize_pii_values(user_id, now)
        await session.execute(
            update(User)
            .where(User.id == user_id, User.erased_at.is_(None))
            .values(**pii_values)
        )

        # 2. Revoke all active tokens
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

        # 3. Apply NMC 7-year legal hold to all clinical records
        hold_until = now + timedelta(days=_NMC_RETENTION_YEARS * 365)
        consult_count, rx_count = await apply_legal_hold(
            session,
            user_id=user_id,
            hold_until=hold_until,
            reason="nmc_7yr_retention",
        )

        # 4. Mark DSR completed with audit notes (no PHI in notes)
        notes = json.dumps({
            "anonymized": True,
            "consults_held": consult_count,
            "rx_held": rx_count,
            "hold_until": hold_until.isoformat(),
            "retention_reason": "nmc_7yr_retention",
        })
        await consent_repo.update_data_subject_request_status(
            session,
            request_id=request_id,
            status=DataSubjectRequestStatus.COMPLETED,
            completed_at=now,
            notes=notes,
        )
        if owns_session:
            await session.commit()

    if db is not None:
        assert isinstance(db, AsyncSession)
        await _run(db, owns_session=False)
    else:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as owned_db:
            await _run(owned_db, owns_session=True)
