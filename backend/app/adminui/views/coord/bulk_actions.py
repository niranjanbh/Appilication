"""Coordinator bulk actions and CSV export.

Multi-select operations across the coordinator list pages plus CSV download.

Clinical-content wall (security rule #3): every export and every bulk action here
deals only in operational/scheduling data. No lab values, prescription contents,
doctor notes, diagnoses, or recordings are ever read, written, or emitted. CSV
columns are an explicit allow-list — never a dump of the ORM row.

Scoping: patient/follow-up/scheduling/intake data is resolved through the
coordinator's assigned-patient set (via the coordinator repo), so a coordinator
can only ever act on or export their own patients. Booking inquiries are the one
pre-account shared queue (no patient assignment), matching the inquiries page.

Audit: every bulk action audit-logs each individual item (allowed or denied).
A CSV export writes one audit row for the export event. Denial/audit rows are
committed before any 4xx or before streaming begins.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_coord_session
from app.adminui.schemas import coordinator as coord_schemas
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole
from app.db.session import get_db
from app.repositories import coordinator_portal as coord_repo

router = APIRouter()

_IST = timezone(timedelta(hours=5, minutes=30))

# Cap a single bulk/export request so one click can't sweep the whole table.
_MAX_IDS = 500


def _ist(dt: datetime | None) -> str:
    """UTC stored, IST displayed (security/data rule: no naive datetimes)."""
    if dt is None:
        return ""
    return dt.astimezone(_IST).strftime("%d %b %Y %H:%M") + " IST"


def _ctx(request: Request, coord: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(coord, UserModel)
    return AuditContext(
        actor_user_id=coord.id,
        actor_role=ActorRole.COORDINATOR,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


def _parse_ids(raw: list[str]) -> list[uuid.UUID]:
    """Parse form ids → UUIDs, dropping anything malformed, capped at _MAX_IDS."""
    out: list[uuid.UUID] = []
    for value in raw[:_MAX_IDS]:
        try:
            out.append(uuid.UUID(value.strip()))
        except (ValueError, AttributeError):
            continue
    return out


def _parse_id_csv(raw: str) -> list[uuid.UUID]:
    """Parse a comma-separated id query param → UUIDs (export selection)."""
    if not raw:
        return []
    return _parse_ids([part for part in raw.split(",") if part.strip()])


def _csv_response(filename: str, header: list[str], rows: list[list[str]]) -> StreamingResponse:
    """Serialise rows to a CSV download. BOM so Excel renders UTF-8 correctly."""
    buffer = io.StringIO()
    buffer.write("﻿")
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _condition_display(conditions: list[str] | None) -> str:
    """Coarse condition categories → human labels. Never clinical detail."""
    if not conditions:
        return ""
    return ", ".join(c.replace("_", " ").title() for c in conditions)


# ── Bulk actions ─────────────────────────────────────────────────────────────


@router.post("/bulk/patients")
async def bulk_patient_action(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    action: str = Form(...),
    ids: list[str] = Form(...),
    template_key: str = Form(default=""),
    channel: str = Form(default="whatsapp"),
    note: str = Form(default=""),
    due_date: str = Form(default=""),
) -> RedirectResponse:
    """Bulk operations over assigned patients: send a pre-approved message, or
    create a follow-up. Each patient is verified as assigned before acting, and
    each item is audit-logged individually."""
    from app.models.identity import User as UserModel

    assert isinstance(coord, UserModel)
    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    patient_ids = _parse_ids(ids)
    results = {"success": 0, "failed": 0}

    if action == "send_message":
        from app.adminui.views.coord.communication import _TEMPLATES, _dispatch_message

        if template_key not in _TEMPLATES or channel not in ("whatsapp", "email"):
            return RedirectResponse(
                url="/coord/patients?bulk_error=invalid_message",
                status_code=status.HTTP_302_FOUND,
            )
        message_text = _TEMPLATES[template_key]
        for pid in patient_ids:
            row = await coord_repo.get_assigned_patient(
                db, coordinator_id=coordinator.id, patient_id=pid
            )
            allowed = row is not None
            await write_audit(
                db, ctx, action="coord_bulk_send_message", resource_type="patient",
                resource_id=pid, allowed=allowed,
                reason=None if allowed else "not_assigned_or_not_found",
                log_metadata={"channel": channel, "template": template_key},
            )
            if row is not None:
                _dispatch_message(channel, row[1], message_text)
                results["success"] += 1
            else:
                results["failed"] += 1

    elif action == "create_followup":
        from datetime import UTC

        try:
            due_at = datetime.fromisoformat(due_date).replace(tzinfo=UTC)
        except ValueError:
            return RedirectResponse(
                url="/coord/patients?bulk_error=invalid_date",
                status_code=status.HTTP_302_FOUND,
            )
        note_text = note.strip()
        if not note_text:
            return RedirectResponse(
                url="/coord/patients?bulk_error=invalid_note",
                status_code=status.HTTP_302_FOUND,
            )
        for pid in patient_ids:
            followup = await coord_repo.create_followup(
                db, coordinator_id=coordinator.id, patient_id=pid,
                note=note_text, due_at=due_at,
            )
            allowed = followup is not None
            await write_audit(
                db, ctx, action="coord_bulk_create_followup", resource_type="followup",
                resource_id=followup.id if followup else None, allowed=allowed,
                reason=None if allowed else "patient_not_assigned",
                log_metadata={"patient_id": str(pid)},
            )
            if followup is not None:
                results["success"] += 1
            else:
                results["failed"] += 1
    else:
        return RedirectResponse(
            url="/coord/patients?bulk_error=invalid_action",
            status_code=status.HTTP_302_FOUND,
        )

    return RedirectResponse(
        url=f"/coord/patients?bulk_success={results['success']}&bulk_failed={results['failed']}",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/bulk/inquiries")
async def bulk_inquiry_action(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    action: str = Form(...),
    ids: list[str] = Form(...),
) -> RedirectResponse:
    """Bulk-claim booking inquiries as contacted (first coordinator wins per item)."""
    from app.models.identity import User as UserModel

    assert isinstance(coord, UserModel)
    ctx = _ctx(request, coord)

    inquiry_ids = _parse_ids(ids)
    results = {"success": 0, "failed": 0}
    for iid in inquiry_ids:
        if action == "mark_contacted":
            claimed = await coord_repo.mark_inquiry_contacted(
                db, inquiry_id=iid, user_id=coord.id
            )
        else:
            return RedirectResponse(
                url="/coord/inquiries?bulk_error=invalid_action",
                status_code=status.HTTP_302_FOUND,
            )
        await write_audit(
            db, ctx, action=f"coord_bulk_{action}", resource_type="booking_inquiry",
            resource_id=iid, allowed=claimed,
            reason=None if claimed else "already_contacted_or_not_found",
        )
        if claimed:
            results["success"] += 1
        else:
            results["failed"] += 1

    return RedirectResponse(
        url=(
            f"/coord/inquiries?show=all&bulk_success={results['success']}"
            f"&bulk_failed={results['failed']}"
        ),
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/bulk/followups")
async def bulk_followup_action(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    action: str = Form(...),
    ids: list[str] = Form(...),
) -> RedirectResponse:
    """Bulk-complete follow-ups owned by this coordinator."""
    from app.models.identity import User as UserModel

    assert isinstance(coord, UserModel)
    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    followup_ids = _parse_ids(ids)
    results = {"success": 0, "failed": 0}
    for fid in followup_ids:
        if action == "mark_complete":
            done = await coord_repo.complete_followup(
                db, coordinator_id=coordinator.id, followup_id=fid
            )
        else:
            return RedirectResponse(
                url="/coord/followups?bulk_error=invalid_action",
                status_code=status.HTTP_302_FOUND,
            )
        allowed = done is not None
        await write_audit(
            db, ctx, action=f"coord_bulk_{action}", resource_type="followup",
            resource_id=fid, allowed=allowed,
            reason=None if allowed else "not_found_or_not_own",
        )
        if allowed:
            results["success"] += 1
        else:
            results["failed"] += 1

    return RedirectResponse(
        url=f"/coord/followups?bulk_success={results['success']}&bulk_failed={results['failed']}",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/bulk/intake")
async def bulk_intake_action(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    action: str = Form(...),
    ids: list[str] = Form(...),
) -> RedirectResponse:
    """Bulk-send a pre-approved reminder for intake-queue consultations.

    The intake queue is scoped to this coordinator's assigned patients; each
    consultation is re-verified against the live queue before sending so a stale
    id can't reach another coordinator's patient."""
    from app.models.identity import User as UserModel

    assert isinstance(coord, UserModel)
    ctx = _ctx(request, coord)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    if action != "send_reminder":
        return RedirectResponse(
            url="/coord/intake?bulk_error=invalid_action",
            status_code=status.HTTP_302_FOUND,
        )

    from app.adminui.views.coord.communication import _TEMPLATES, _dispatch_message

    selected = set(_parse_ids(ids))
    queue = await coord_repo.list_intake_queue(db, coordinator_id=coordinator.id)
    # Map consultation_id -> patient user, but only for this coordinator's queue.
    reachable = {
        consultation.id: patient_user
        for consultation, patient_user in queue
        if patient_user is not None
    }
    message_text = _TEMPLATES["reminder_24h"]

    results = {"success": 0, "failed": 0}
    for cid in selected:
        patient_user = reachable.get(cid)
        allowed = patient_user is not None
        await write_audit(
            db, ctx, action="coord_bulk_send_reminder", resource_type="consultation",
            resource_id=cid, allowed=allowed,
            reason=None if allowed else "not_in_queue_or_not_assigned",
            log_metadata={"channel": "whatsapp", "template": "reminder_24h"},
        )
        if patient_user is not None:
            _dispatch_message("whatsapp", patient_user, message_text)
            results["success"] += 1
        else:
            results["failed"] += 1

    return RedirectResponse(
        url=f"/coord/intake?bulk_success={results['success']}&bulk_failed={results['failed']}",
        status_code=status.HTTP_302_FOUND,
    )


# ── CSV exports ──────────────────────────────────────────────────────────────


async def _audit_export(
    request: Request, db: AsyncSession, coord: object, resource_type: str, count: int
) -> None:
    """Record the export event and commit before streaming begins."""
    await write_audit(
        db, _ctx(request, coord), action="coord_export_csv",
        resource_type=resource_type, resource_id=None, allowed=True,
        log_metadata={"rows": count},
    )
    await db.commit()


@router.get("/export/patients.csv")
async def export_patients_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    ids: str = "",
) -> StreamingResponse:
    """Export assigned patients. NO clinical content — identity + operational only."""
    from app.models.identity import User as UserModel

    assert isinstance(coord, UserModel)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    pairs = coord_schemas.patient_pairs(
        await coord_repo.list_assigned_patients(db, coordinator_id=coordinator.id)
    )
    selected = set(_parse_id_csv(ids))
    if selected:
        pairs = [(p, u) for p, u in pairs if p.id in selected]

    rows = [
        [
            user.name or "",
            user.phone or "",
            user.email or "",
            user.city or "",
            _condition_display(patient.primary_conditions),
            "Complete" if patient.intake_complete_at else "Pending",
        ]
        for patient, user in pairs
    ]
    await _audit_export(request, db, coord, "patient", len(rows))
    return _csv_response(
        "kyros_coord_patients.csv",
        ["Name", "Phone", "Email", "City", "Conditions", "Intake Status"],
        rows,
    )


@router.get("/export/inquiries.csv")
async def export_inquiries_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    ids: str = "",
) -> StreamingResponse:
    """Export booking inquiries (shared pre-account queue). Operational only."""
    from app.models.identity import User as UserModel

    assert isinstance(coord, UserModel)
    inquiries = await coord_repo.list_booking_inquiries(db)
    selected = set(_parse_id_csv(ids))
    if selected:
        inquiries = [(i, name) for i, name in inquiries if i.id in selected]

    rows = [
        [
            inquiry.name or "",
            inquiry.phone or "",
            inquiry.email or "",
            (inquiry.condition_category or "").replace("-", " ").replace("_", " ").title(),
            "Not contacted" if inquiry.status == "new" else (inquiry.status or ""),
            contacted_by or "",
            _ist(inquiry.contacted_at),
            _ist(inquiry.created_at),
        ]
        for inquiry, contacted_by in inquiries
    ]
    await _audit_export(request, db, coord, "booking_inquiry", len(rows))
    return _csv_response(
        "kyros_coord_inquiries.csv",
        ["Name", "Phone", "Email", "Condition", "Status", "Contacted By",
         "Contacted At", "Created At"],
        rows,
    )


@router.get("/export/followups.csv")
async def export_followups_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    ids: str = "",
    show: str = "pending",
) -> StreamingResponse:
    """Export this coordinator's follow-ups. Notes are operational by policy."""
    from app.models.identity import User as UserModel

    assert isinstance(coord, UserModel)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    status_value = "done" if show == "done" else "pending"
    followups = await coord_repo.list_followups(
        db, coordinator_id=coordinator.id, status=status_value
    )
    selected = set(_parse_id_csv(ids))
    if selected:
        followups = [(f, u) for f, u in followups if f.id in selected]

    rows = [
        [
            _ist(followup.due_at),
            user.name or "",
            followup.note or "",
            followup.status or "",
            _ist(followup.completed_at),
        ]
        for followup, user in followups
    ]
    await _audit_export(request, db, coord, "followup", len(rows))
    return _csv_response(
        "kyros_coord_followups.csv",
        ["Due", "Patient", "Note", "Status", "Completed At"],
        rows,
    )


@router.get("/export/scheduling.csv")
async def export_scheduling_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    ids: str = "",
) -> StreamingResponse:
    """Export upcoming consultations for assigned patients. Scheduling fields only."""
    from app.models.identity import User as UserModel

    assert isinstance(coord, UserModel)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    triples = coord_schemas.consultation_user_user_triples(
        await coord_repo.list_upcoming_consultations(db, coordinator_id=coordinator.id)
    )
    selected = set(_parse_id_csv(ids))
    if selected:
        triples = [(c, p, d) for c, p, d in triples if c.id in selected]

    rows = [
        [
            _ist(consultation.scheduled_start_at),
            patient_user.name if patient_user else "",
            doctor_user.name if doctor_user else "",
            (consultation.condition_category or "").replace("_", " ").title(),
            consultation.status.value,
        ]
        for consultation, patient_user, doctor_user in triples
    ]
    await _audit_export(request, db, coord, "consultation", len(rows))
    return _csv_response(
        "kyros_coord_scheduling.csv",
        ["When", "Patient", "Doctor", "Condition", "Status"],
        rows,
    )


@router.get("/export/intake.csv")
async def export_intake_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    coord: Annotated[object, Depends(require_coord_session)],
    ids: str = "",
) -> StreamingResponse:
    """Export the intake queue for assigned patients. Scheduling fields only."""
    from app.models.identity import User as UserModel

    assert isinstance(coord, UserModel)
    coordinator = await coord_repo.get_coordinator_by_user_id(db, user_id=coord.id)
    if coordinator is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    queue = coord_schemas.consultation_user_pairs(
        await coord_repo.list_intake_queue(db, coordinator_id=coordinator.id)
    )
    selected = set(_parse_id_csv(ids))
    if selected:
        queue = [(c, u) for c, u in queue if c.id in selected]

    rows = [
        [
            patient_user.name if patient_user else "",
            (consultation.condition_category or "").replace("_", " ").title(),
            consultation.consultation_type or "",
            _ist(consultation.scheduled_start_at),
            consultation.status.value,
        ]
        for consultation, patient_user in queue
    ]
    await _audit_export(request, db, coord, "consultation", len(rows))
    return _csv_response(
        "kyros_coord_intake.csv",
        ["Patient", "Condition", "Type", "Scheduled", "Status"],
        rows,
    )
