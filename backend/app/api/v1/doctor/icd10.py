"""ICD-10 reference catalog search.

GET /v1/doctor/icd10-codes?q=... — autocomplete search over the curated kc_icd10_codes catalog.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole
from app.repositories import diagnoses as diagnoses_repo

router = APIRouter(tags=["doctor-icd10"])


class Icd10CodeRead(BaseModel):
    code: str
    description: str
    category: str


@router.get("/icd10-codes", response_model=list[Icd10CodeRead])
async def search_icd10_codes(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
    q: Annotated[str, Query(min_length=1, max_length=100)],
) -> list[Icd10CodeRead]:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    codes = await diagnoses_repo.search_icd10_codes(db, query=q)
    await write_audit(
        db,
        AuditContext(
            actor_user_id=user.id,
            actor_role=ActorRole(user.role.value),
            ip_address=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", ""),
            request_id=getattr(request.state, "request_id", ""),
        ),
        action="search_icd10_catalogue",
        resource_type="icd10_code",
        allowed=True,
        log_metadata={"result_count": len(codes)},
    )
    return [
        Icd10CodeRead(code=c.code, description=c.description, category=c.category)
        for c in codes
    ]
