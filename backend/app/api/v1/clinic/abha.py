"""ABHA Integration (M1) — verify existing health ID and create via Aadhaar OTP.

All endpoints are patient-only and audit-logged.
PHI: ABHA numbers are never returned in error responses.
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from app.api.deps import DbSession, Redis
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_patient_user
from app.db.enums import ActorRole
from app.services import abha as abha_service

router = APIRouter(tags=["abha"])

_ABHA_RE = re.compile(r"^(\d{14}|\d{2}-\d{4}-\d{4}-\d{4})$")
_AADHAAR_RE = re.compile(r"^\d{12}$")


# ── Schemas ───────────────────────────────────────────────────────────────────


class AbhaStatusRead(BaseModel):
    linked: bool
    abha_number_masked: str | None = None  # e.g. "XX-XXXX-XXXX-1234"


class AbhaLinkRequest(BaseModel):
    abha_number: str = Field(..., description="14-digit ABHA health ID, with or without dashes")

    @field_validator("abha_number")
    @classmethod
    def _validate_format(cls, v: str) -> str:
        if not _ABHA_RE.match(v):
            raise ValueError("ABHA number must be 14 digits or formatted as XX-XXXX-XXXX-XXXX")
        return v


class AbhaCreateInitRequest(BaseModel):
    aadhaar_number: str = Field(..., description="12-digit Aadhaar number")

    @field_validator("aadhaar_number")
    @classmethod
    def _validate_aadhaar(cls, v: str) -> str:
        if not _AADHAAR_RE.match(v):
            raise ValueError("Aadhaar number must be exactly 12 digits")
        return v


class AbhaCreateInitResponse(BaseModel):
    txn_id: str
    message: str = "OTP sent to your Aadhaar-linked mobile number"


class AbhaCreateConfirmRequest(BaseModel):
    txn_id: str
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


# ── Helpers ────────────────────────────────────────────────────────────────────


def _mask_abha(abha_number: str) -> str:
    """Return 'XX-XXXX-XXXX-1234' style masked display string."""
    digits = abha_number.replace("-", "")
    return f"XX-XXXX-XXXX-{digits[-4:]}"


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


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("/abha", response_model=AbhaStatusRead)
async def get_abha_status(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> AbhaStatusRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    result = await abha_service.get_abha_status(db, user_id=user.id)

    if not result["patient_exists"]:
        await write_audit(
            db, ctx,
            action="view_abha_status", resource_type="abha",
            resource_id=user.id, allowed=False, reason="patient_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="view_abha_status", resource_type="abha",
        resource_id=user.id, allowed=True,
    )
    abha_num: str | None = result["abha_number"]  # type: ignore[assignment]
    return AbhaStatusRead(
        linked=bool(result["linked"]),
        abha_number_masked=_mask_abha(abha_num) if abha_num else None,
    )


@router.post("/abha/link", response_model=AbhaStatusRead)
async def link_abha_number(
    body: AbhaLinkRequest,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_patient_user)],
) -> AbhaStatusRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    result = await abha_service.link_abha_number(db, user_id=user.id, abha_number=body.abha_number)

    if not result["patient_exists"]:
        await write_audit(
            db, ctx,
            action="link_abha", resource_type="abha",
            resource_id=user.id, allowed=False, reason="patient_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    if result.get("error") == "abha_not_found":
        await write_audit(
            db, ctx,
            action="link_abha", resource_type="abha",
            resource_id=user.id, allowed=False, reason="abha_not_found_in_abdm",
        )
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="ABHA number not found in ABDM registry")

    await write_audit(
        db, ctx,
        action="link_abha", resource_type="abha",
        resource_id=user.id, allowed=True,
    )
    abha_num_link: str | None = result["abha_number"]  # type: ignore[assignment]
    return AbhaStatusRead(
        linked=True,
        abha_number_masked=_mask_abha(abha_num_link) if abha_num_link else None,
    )


@router.post("/abha/create/init", response_model=AbhaCreateInitResponse, status_code=status.HTTP_200_OK)
async def init_abha_creation(
    body: AbhaCreateInitRequest,
    request: Request,
    db: DbSession,
    redis: Redis,
    user: Annotated[object, Depends(get_patient_user)],
) -> AbhaCreateInitResponse:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    result = await abha_service.init_abha_creation(
        db, redis, user_id=user.id, aadhaar_number=body.aadhaar_number
    )

    if not result["patient_exists"]:
        await write_audit(
            db, ctx,
            action="init_abha_creation", resource_type="abha",
            resource_id=user.id, allowed=False, reason="patient_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    await write_audit(
        db, ctx,
        action="init_abha_creation", resource_type="abha",
        resource_id=user.id, allowed=True,
    )
    return AbhaCreateInitResponse(txn_id=str(result["txn_id"]))


@router.post("/abha/create/confirm", response_model=AbhaStatusRead)
async def confirm_abha_creation(
    body: AbhaCreateConfirmRequest,
    request: Request,
    db: DbSession,
    redis: Redis,
    user: Annotated[object, Depends(get_patient_user)],
) -> AbhaStatusRead:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    ctx = _audit_ctx(request, user)
    result = await abha_service.confirm_abha_creation(
        db, redis, user_id=user.id, txn_id=body.txn_id, otp=body.otp
    )

    if not result["patient_exists"]:
        await write_audit(
            db, ctx,
            action="confirm_abha_creation", resource_type="abha",
            resource_id=user.id, allowed=False, reason="patient_profile_not_found",
        )
        await db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    error = result.get("error")
    if error == "invalid_or_expired_txn":
        await write_audit(
            db, ctx,
            action="confirm_abha_creation", resource_type="abha",
            resource_id=user.id, allowed=False, reason="invalid_or_expired_txn",
        )
        await db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Transaction expired or invalid")

    if error == "invalid_otp":
        await write_audit(
            db, ctx,
            action="confirm_abha_creation", resource_type="abha",
            resource_id=user.id, allowed=False, reason="invalid_otp",
        )
        await db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

    await write_audit(
        db, ctx,
        action="confirm_abha_creation", resource_type="abha",
        resource_id=user.id, allowed=True,
    )
    abha_num_confirm: str | None = result["abha_number"]  # type: ignore[assignment]
    return AbhaStatusRead(
        linked=True,
        abha_number_masked=_mask_abha(abha_num_confirm) if abha_num_confirm else None,
    )
