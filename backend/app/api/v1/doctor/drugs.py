"""Drug catalogue autocomplete search.

GET /v1/doctor/drugs?q=... — search the curated kc_drug_catalogue for prescribing
autocomplete. Excludes prohibited drugs and Schedule X/H1 from results (no point
surfacing drugs that cannot be prescribed via telemedicine).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.audit import AuditContext, write_audit
from app.core.rbac import get_doctor_user
from app.db.enums import ActorRole
from app.repositories import drug_catalogue as dc_repo

router = APIRouter(tags=["doctor-drugs"])


class DrugCatalogueRead(BaseModel):
    drug_generic_name: str
    drug_schedule: str
    is_prohibited: bool
    requires_vertical: str | None


@router.get("/drugs", response_model=list[DrugCatalogueRead])
async def search_drugs(
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
    q: Annotated[str, Query(min_length=1, max_length=100)],
) -> list[DrugCatalogueRead]:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    drugs = await dc_repo.search_drugs(db, query=q)
    await write_audit(
        db,
        AuditContext(
            actor_user_id=user.id,
            actor_role=ActorRole(user.role.value),
            ip_address=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", ""),
            request_id=getattr(request.state, "request_id", ""),
        ),
        action="search_drug_catalogue",
        resource_type="drug_catalogue",
        allowed=True,
        log_metadata={"result_count": len(drugs)},
    )
    return [
        DrugCatalogueRead(
            drug_generic_name=d.drug_generic_name,
            drug_schedule=d.drug_schedule,
            is_prohibited=d.is_prohibited,
            requires_vertical=d.requires_vertical,
        )
        for d in drugs
    ]
