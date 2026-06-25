"""Admin portal bulk actions and CSV exports.

Two families of endpoints live here:

* ``POST /admin/bulk/{entity}`` — apply one action (suspend/reactivate/
  activate/deactivate/publish/unpublish/delete) to a list of checked ids. Every
  individual item is audit-logged (not just the batch), per security rule 5, and
  state-changers require ``require_super_admin_session``.
* ``GET /admin/export/{entity}.csv`` — stream a CSV of either the checked ids or
  the full current filter. Both admin tiers may export. The export itself is
  audit-logged once. CSV columns are deliberately operational — never lab values,
  prescription contents, or doctor notes (security rules 3, 6, 10).

Money is rendered in rupees (paise / 100, two decimals). Timestamps are
converted from stored UTC to IST (Asia/Kolkata) for display, matching the rest
of the portal's presentation layer.
"""

from __future__ import annotations

import csv
import io
import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.adminui.deps import require_admin_session, require_super_admin_session
from app.core.audit import AuditContext, write_audit
from app.db.enums import ActorRole, ContentStatus
from app.db.session import get_db
from app.repositories import admin_portal as admin_repo
from app.repositories import coupons as coupon_repo
from app.repositories import education as edu_repo
from app.repositories import medication_catalog as catalog_repo

router = APIRouter()

_IST = ZoneInfo("Asia/Kolkata")


def _ctx(request: Request, admin: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(admin, UserModel)
    return AuditContext(
        actor_user_id=admin.id,
        actor_role=ActorRole(admin.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


def _parse_ids(values: Iterable[str]) -> list[uuid.UUID]:
    """Parse form/query id strings to UUIDs, silently dropping malformed ones."""
    out: list[uuid.UUID] = []
    for raw in values:
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                out.append(uuid.UUID(part))
            except ValueError:
                continue
    return out


def _fmt_dt(value: datetime | None) -> str:
    """UTC → IST display string, blank for None."""
    if value is None:
        return ""
    if value.tzinfo is None:
        from datetime import UTC

        value = value.replace(tzinfo=UTC)
    return value.astimezone(_IST).strftime("%Y-%m-%d %H:%M")


def _fmt_date(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        from datetime import UTC

        value = value.replace(tzinfo=UTC)
    return value.astimezone(_IST).strftime("%Y-%m-%d")


def _rupees(paise: int | None) -> str:
    if paise is None:
        return ""
    return f"{paise / 100:.2f}"


def _csv_response(header: list[str], rows: list[list[str]], filename_stem: str) -> StreamingResponse:
    """Build a fully-materialized CSV StreamingResponse.

    The CSV is rendered into memory before the response is returned so the DB
    session (closed by the get_db dependency once the handler returns) is never
    read from inside the streaming generator.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    content = buffer.getvalue()
    stamp = datetime.now(_IST).strftime("%Y%m%d")
    filename = f"{filename_stem}_export_{stamp}.csv"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Bulk actions ─────────────────────────────────────────────────────────────


@router.post("/bulk/users")
async def bulk_user_action(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    action: str = Form(...),
    ids: list[str] = Form(default=[]),
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    results = {"success": 0, "failed": 0}
    for uid in _parse_ids(ids):
        if action == "suspend":
            updated = await admin_repo.suspend_user(db, uid)
        elif action == "reactivate":
            updated = await admin_repo.reactivate_user(db, uid)
        else:
            continue
        await write_audit(
            db, ctx, action=f"admin_bulk_{action}_user", resource_type="user",
            resource_id=uid, allowed=updated is not None,
            reason=None if updated is not None else "not_found",
        )
        results["success" if updated is not None else "failed"] += 1
    return RedirectResponse(
        url=f"/admin/users?bulk_success={results['success']}&bulk_failed={results['failed']}",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/bulk/doctors")
async def bulk_doctor_action(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    action: str = Form(...),
    ids: list[str] = Form(default=[]),
) -> RedirectResponse:
    from app.db.enums import DoctorStatus

    ctx = _ctx(request, admin)
    results = {"success": 0, "failed": 0}
    for did in _parse_ids(ids):
        row = await admin_repo.get_doctor_detail(db, did)
        ok = False
        if row is not None:
            doctor, _user = row
            if action == "suspend" and admin_repo.can_suspend(doctor.status):
                await admin_repo.update_doctor_status(db, did, DoctorStatus.SUSPENDED)
                ok = True
            elif action == "reactivate" and admin_repo.can_reactivate(doctor.status):
                await admin_repo.update_doctor_status(db, did, DoctorStatus.ACTIVE)
                ok = True
        if action not in ("suspend", "reactivate"):
            continue
        await write_audit(
            db, ctx, action=f"admin_bulk_{action}_doctor", resource_type="doctor",
            resource_id=did, allowed=ok,
            reason=None if ok else "not_found_or_invalid_transition",
        )
        results["success" if ok else "failed"] += 1
    return RedirectResponse(
        url=f"/admin/doctors?bulk_success={results['success']}&bulk_failed={results['failed']}",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/bulk/staff")
async def bulk_staff_action(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    action: str = Form(...),
    ids: list[str] = Form(default=[]),
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    results = {"success": 0, "failed": 0}
    for uid in _parse_ids(ids):
        if action == "suspend":
            updated = await admin_repo.suspend_user(db, uid)
        elif action == "reactivate":
            updated = await admin_repo.reactivate_user(db, uid)
        else:
            continue
        await write_audit(
            db, ctx, action=f"admin_bulk_{action}_staff", resource_type="user",
            resource_id=uid, allowed=updated is not None,
            reason=None if updated is not None else "not_found",
        )
        results["success" if updated is not None else "failed"] += 1
    return RedirectResponse(
        url=f"/admin/staff?bulk_success={results['success']}&bulk_failed={results['failed']}",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/bulk/coupons")
async def bulk_coupon_action(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    action: str = Form(...),
    ids: list[str] = Form(default=[]),
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    results = {"success": 0, "failed": 0}
    for cid in _parse_ids(ids):
        if action == "activate":
            ok = await coupon_repo.activate_coupon(db, coupon_id=cid) is not None
        elif action == "deactivate":
            ok = await coupon_repo.deactivate_coupon(db, coupon_id=cid) is not None
        elif action == "delete":
            ok = await coupon_repo.delete_coupon(db, coupon_id=cid)
        else:
            continue
        await write_audit(
            db, ctx, action=f"admin_bulk_{action}_coupon", resource_type="coupon",
            resource_id=cid, allowed=ok, reason=None if ok else "not_found",
        )
        results["success" if ok else "failed"] += 1
    return RedirectResponse(
        url=f"/admin/coupons?bulk_success={results['success']}&bulk_failed={results['failed']}",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/bulk/content")
async def bulk_content_action(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    action: str = Form(...),
    ids: list[str] = Form(default=[]),
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    results = {"success": 0, "failed": 0}
    for cid in _parse_ids(ids):
        if action == "publish":
            ok = await edu_repo.update_content_status(db, cid, ContentStatus.PUBLISHED) is not None
        elif action == "unpublish":
            ok = await edu_repo.update_content_status(db, cid, ContentStatus.ARCHIVED) is not None
        elif action == "delete":
            ok = await edu_repo.delete_content(db, cid)
        else:
            continue
        await write_audit(
            db, ctx, action=f"admin_bulk_{action}_content", resource_type="education_content",
            resource_id=cid, allowed=ok, reason=None if ok else "not_found",
        )
        results["success" if ok else "failed"] += 1
    return RedirectResponse(
        url=f"/admin/content?bulk_success={results['success']}&bulk_failed={results['failed']}",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/bulk/medications")
async def bulk_medication_action(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_super_admin_session)],
    action: str = Form(...),
    ids: list[str] = Form(default=[]),
) -> RedirectResponse:
    ctx = _ctx(request, admin)
    results = {"success": 0, "failed": 0}
    for mid in _parse_ids(ids):
        if action == "activate":
            ok = await catalog_repo.update_fields(db, catalog_id=mid, active=True) is not None
        elif action == "deactivate":
            ok = await catalog_repo.update_fields(db, catalog_id=mid, active=False) is not None
        elif action == "delete":
            ok = await catalog_repo.soft_delete(db, catalog_id=mid)
        else:
            continue
        await write_audit(
            db, ctx, action=f"admin_bulk_{action}_medication", resource_type="medication_catalog",
            resource_id=mid, allowed=ok, reason=None if ok else "not_found",
        )
        results["success" if ok else "failed"] += 1
    return RedirectResponse(
        url=f"/admin/medication-catalog?bulk_success={results['success']}&bulk_failed={results['failed']}",
        status_code=status.HTTP_302_FOUND,
    )


# ── CSV exports ──────────────────────────────────────────────────────────────


async def _audit_export(
    db: AsyncSession, ctx: AuditContext, *, entity: str, count: int, selected: bool
) -> None:
    await write_audit(
        db, ctx, action=f"admin_export_{entity}_csv", resource_type=entity,
        allowed=True, log_metadata={"rows": count, "scope": "selected" if selected else "filtered"},
    )
    await db.commit()


@router.get("/export/users.csv")
async def export_users_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    ids: str = "",
    search: str = "",
    role: str = "",
) -> StreamingResponse:
    ctx = _ctx(request, admin)
    parsed = _parse_ids([ids])
    if parsed:
        users = await admin_repo.get_users_by_ids(db, parsed)
        selected = True
    else:
        users, _ = await admin_repo.list_users(
            db, search=search or None, role_filter=role or None, page=1, page_size=10_000
        )
        selected = False
    rows = [
        [
            u.name, u.phone or "", u.email or "", u.role.value,
            _fmt_date(u.created_at),
            "Suspended" if u.deleted_at else "Active",
        ]
        for u in users
    ]
    await _audit_export(db, ctx, entity="user", count=len(rows), selected=selected)
    return _csv_response(
        ["Name", "Phone", "Email", "Role", "Joined", "Status"], rows, "users"
    )


@router.get("/export/doctors.csv")
async def export_doctors_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    ids: str = "",
    search: str = "",
    status_filter: str = "",
) -> StreamingResponse:
    ctx = _ctx(request, admin)
    parsed = _parse_ids([ids])
    if parsed:
        pairs = await admin_repo.get_doctors_by_ids(db, parsed)
        selected = True
    else:
        pairs, _ = await admin_repo.list_doctors(
            db, search=search or None, status_filter=status_filter or None,
            page=1, page_size=10_000,
        )
        selected = False
    rows = [
        [
            user.name, doctor.nmc_registration_number,
            ", ".join(doctor.specialty or []), doctor.status.value,
            _fmt_date(doctor.created_at),
        ]
        for doctor, user in pairs
    ]
    await _audit_export(db, ctx, entity="doctor", count=len(rows), selected=selected)
    return _csv_response(
        ["Name", "NMC Registration", "Specialty", "Status", "Joined"], rows, "doctors"
    )


@router.get("/export/consultations.csv")
async def export_consultations_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    ids: str = "",
    status_filter: str = "",
    date_from: str = "",
) -> StreamingResponse:
    ctx = _ctx(request, admin)
    parsed = _parse_ids([ids])
    if parsed:
        triples = await admin_repo.get_consultations_by_ids(db, parsed)
        selected = True
    else:
        parsed_date: datetime | None = None
        if date_from:
            try:
                parsed_date = datetime.fromisoformat(date_from)
            except ValueError:
                parsed_date = None
        triples, _ = await admin_repo.list_all_consultations(
            db, status_filter=status_filter or None, date_from=parsed_date,
            page=1, page_size=10_000,
        )
        selected = False
    rows = [
        [
            patient_user.name if patient_user else "",
            doctor_user.name if doctor_user else "",
            consultation.condition_category,
            consultation.consultation_type.value,
            consultation.status.value,
            _fmt_dt(consultation.scheduled_start_at),
            _rupees(consultation.consultation_fee_paise),
        ]
        for consultation, patient_user, doctor_user in triples
    ]
    await _audit_export(db, ctx, entity="consultation", count=len(rows), selected=selected)
    return _csv_response(
        ["Patient", "Doctor", "Condition", "Type", "Status", "Scheduled (IST)", "Fee (₹)"],
        rows, "consultations",
    )


@router.get("/export/payments.csv")
async def export_payments_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    ids: str = "",
    status_filter: str = "",
    search: str = "",
) -> StreamingResponse:
    ctx = _ctx(request, admin)
    parsed = _parse_ids([ids])
    if parsed:
        pairs = await admin_repo.get_payments_by_ids(db, parsed)
        selected = True
    else:
        pairs, _ = await admin_repo.list_payments(
            db, status_filter=status_filter or None, search=search or None,
            page=1, page_size=10_000,
        )
        selected = False
    rows = [
        [
            payer.name if payer else "",
            payment.razorpay_order_id,
            payment.razorpay_payment_id or "",
            _rupees(payment.amount_paise),
            payment.status.value,
            _fmt_dt(payment.created_at),
        ]
        for payment, payer in pairs
    ]
    await _audit_export(db, ctx, entity="payment", count=len(rows), selected=selected)
    return _csv_response(
        ["Patient", "Order ID", "Payment ID", "Amount (₹)", "Status", "Date (IST)"],
        rows, "payments",
    )


@router.get("/export/staff.csv")
async def export_staff_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    ids: str = "",
    role: str = "",
) -> StreamingResponse:
    ctx = _ctx(request, admin)
    parsed = _parse_ids([ids])
    if parsed:
        staff = await admin_repo.get_staff_by_ids(db, parsed)
        selected = True
    else:
        staff, _ = await admin_repo.list_staff(
            db, role_filter=role or None, page=1, page_size=10_000
        )
        selected = False
    rows = [
        [
            member.name, member.role.value, member.email or "",
            _fmt_date(member.created_at),
            "Suspended" if member.deleted_at else "Active",
        ]
        for member in staff
    ]
    await _audit_export(db, ctx, entity="staff", count=len(rows), selected=selected)
    return _csv_response(
        ["Name", "Role", "Email", "Joined", "Status"], rows, "staff"
    )


@router.get("/export/coupons.csv")
async def export_coupons_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    ids: str = "",
    active_only: str = "",
) -> StreamingResponse:
    ctx = _ctx(request, admin)
    parsed = _parse_ids([ids])
    if parsed:
        items = []
        for cid in parsed:
            coupon = await coupon_repo.get_by_id(db, coupon_id=cid)
            if coupon is not None:
                items.append(coupon)
        selected = True
    else:
        items, _ = await coupon_repo.list_coupons(
            db, active_only=bool(active_only), page=1, page_size=10_000
        )
        selected = False
    rows = []
    for c in items:
        if c.discount_type == "percent":
            discount = f"{c.discount_value}%"
        else:
            discount = _rupees(c.discount_value)
        uses = str(c.redemption_count)
        if c.max_redemptions:
            uses = f"{c.redemption_count}/{c.max_redemptions}"
        rows.append([
            c.code, discount, c.discount_type, uses,
            "Active" if c.active else "Inactive",
            _fmt_date(c.valid_until),
        ])
    await _audit_export(db, ctx, entity="coupon", count=len(rows), selected=selected)
    return _csv_response(
        ["Code", "Discount", "Type", "Uses", "Active", "Expiry"], rows, "coupons"
    )


@router.get("/export/content.csv")
async def export_content_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[object, Depends(require_admin_session)],
    ids: str = "",
    status_filter: str = "",
) -> StreamingResponse:
    ctx = _ctx(request, admin)
    parsed = _parse_ids([ids])
    if parsed:
        items = []
        for cid in parsed:
            content = await edu_repo.get_content_by_id(db, content_id=cid, published_only=False)
            if content is not None:
                items.append(content)
        selected = True
    else:
        items, _ = await edu_repo.list_all_content(
            db,
            status=ContentStatus(status_filter) if status_filter else None,
            page=1, page_size=10_000,
        )
        selected = False
    rows = [
        [
            item.title,
            item.content_type.value if item.content_type else "",
            ", ".join(item.condition_categories or []),
            item.status.value,
            _fmt_date(item.created_at),
        ]
        for item in items
    ]
    await _audit_export(db, ctx, entity="education_content", count=len(rows), selected=selected)
    return _csv_response(
        ["Title", "Type", "Conditions", "Status", "Created"], rows, "content"
    )
