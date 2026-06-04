"""Doctor self-profile endpoints.

GET   /v1/doctor/me               — read own profile (doctor + user merged)
PATCH /v1/doctor/me               — update allowed fields (bio, languages, specialty)
POST  /v1/doctor/me/bank-details  — submit bank details (encrypted, triggers admin alert)
"""

from __future__ import annotations

import base64
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole
from app.repositories import doctor_portal as dr_repo

router = APIRouter(tags=["doctor-profile"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class DoctorProfileRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    nmc_registration_number: str
    nmc_state_council: str | None
    specialty: list[str]
    conditions_treated: list[str]
    consultation_languages: list[str]
    bio_short: str | None
    bio_long: str | None
    photo_url: str | None
    status: str
    consultation_duration_minutes_default: int
    buffer_time_minutes: int
    has_bank_details: bool


class DoctorProfilePatch(BaseModel):
    bio_short: str | None = Field(default=None, max_length=500)
    bio_long: str | None = Field(default=None)
    consultation_languages: list[str] | None = Field(default=None)
    specialty: list[str] | None = Field(default=None)
    conditions_treated: list[str] | None = Field(default=None)


class BankDetailsRequest(BaseModel):
    account_holder_name: str = Field(..., min_length=2, max_length=100)
    account_number: str = Field(..., min_length=9, max_length=18)
    ifsc_code: str = Field(..., pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$")
    bank_name: str = Field(..., min_length=2, max_length=100)


class BankDetailsResponse(BaseModel):
    message: str


# ── Helpers ────────────────────────────────────────────────────────────────────


def _audit_ctx(request: Request, user: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    return AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


def _to_read(doctor: object, user: object) -> DoctorProfileRead:
    from app.models.doctor import Doctor as DoctorModel
    from app.models.identity import User as UserModel

    assert isinstance(doctor, DoctorModel)
    assert isinstance(user, UserModel)
    return DoctorProfileRead(
        id=doctor.id,
        user_id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        nmc_registration_number=doctor.nmc_registration_number,
        nmc_state_council=doctor.nmc_state_council,
        specialty=list(doctor.specialty),
        conditions_treated=list(doctor.conditions_treated),
        consultation_languages=list(doctor.consultation_languages),
        bio_short=doctor.bio_short,
        bio_long=doctor.bio_long,
        photo_url=doctor.photo_url,
        status=doctor.status.value,
        consultation_duration_minutes_default=doctor.consultation_duration_minutes_default,
        buffer_time_minutes=doctor.buffer_time_minutes,
        has_bank_details=doctor.bank_details_encrypted is not None,
    )


def _encrypt_bank_details(data: str) -> bytes:
    """Encrypt bank details JSON using Fernet with a key derived from jwt_secret."""
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    from app.core.config import settings

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"kyros-bank-details-v1",
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.jwt_secret.encode()))
    return Fernet(key).encrypt(data.encode())


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/me", response_model=DoctorProfileRead)
async def get_my_profile(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> DoctorProfileRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if row is None:
        await write_audit(
            db, ctx, action="view_own_profile",
            resource_type="doctor", allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, user_row = row
    await write_audit(
        db, ctx, action="view_own_profile",
        resource_type="doctor", resource_id=doctor.id, allowed=True,
    )
    return _to_read(doctor, user_row)


@router.patch("/me", response_model=DoctorProfileRead)
async def patch_my_profile(
    body: DoctorProfilePatch,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> DoctorProfileRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if row is None:
        await write_audit(
            db, ctx, action="update_own_profile",
            resource_type="doctor", allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, user_row = row

    patch: dict[str, object] = {}
    if body.bio_short is not None:
        patch["bio_short"] = body.bio_short
    if body.bio_long is not None:
        patch["bio_long"] = body.bio_long
    if body.consultation_languages is not None:
        patch["consultation_languages"] = body.consultation_languages
    if body.specialty is not None:
        patch["specialty"] = body.specialty
    if body.conditions_treated is not None:
        patch["conditions_treated"] = body.conditions_treated

    updated = await dr_repo.update_doctor_profile(db, doctor_id=doctor.id, fields=patch)
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="update_own_profile",
        resource_type="doctor", resource_id=doctor.id, allowed=True,
    )
    return _to_read(updated, user_row)


@router.post("/me/bank-details", response_model=BankDetailsResponse, status_code=status.HTTP_200_OK)
async def submit_bank_details(
    body: BankDetailsRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
) -> BankDetailsResponse:
    """Submit bank account details for revenue share.

    Details are encrypted at rest; a verification alert is sent to super admin.
    """
    import json

    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)

    row = await dr_repo.get_doctor_with_user(db, user_id=user.id)
    if row is None:
        await write_audit(
            db, ctx, action="submit_bank_details",
            resource_type="doctor", allowed=False, reason="doctor_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    doctor, user_row = row

    payload = json.dumps(
        {
            "account_holder_name": body.account_holder_name,
            "account_number": body.account_number,
            "ifsc_code": body.ifsc_code,
            "bank_name": body.bank_name,
        }
    )
    encrypted = _encrypt_bank_details(payload)

    saved = await dr_repo.save_bank_details_encrypted(
        db, doctor_id=doctor.id, encrypted_bytes=encrypted
    )
    if saved is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx, action="submit_bank_details",
        resource_type="doctor", resource_id=doctor.id, allowed=True,
    )

    # Dispatch admin notification asynchronously — no PHI in task args.
    from app.tasks.doctor_tasks import bank_details_verification

    bank_details_verification.delay(
        doctor_id=str(doctor.id),
        doctor_name=user_row.name,
    )

    return BankDetailsResponse(message="Bank details saved. Pending admin verification.")
