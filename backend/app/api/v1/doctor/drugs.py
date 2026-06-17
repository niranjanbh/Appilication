"""Drug catalogue autocomplete search.

GET /v1/doctor/drugs?q=... — search the curated kc_drug_catalogue for prescribing
autocomplete. Excludes prohibited drugs and Schedule X/H1 from results (no point
surfacing drugs that cannot be prescribed via telemedicine).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.rbac import get_doctor_user
from app.repositories import drug_catalogue as dc_repo

router = APIRouter(tags=["doctor-drugs"])


class DrugCatalogueRead(BaseModel):
    drug_generic_name: str
    drug_schedule: str
    is_prohibited: bool
    requires_vertical: str | None


@router.get("/drugs", response_model=list[DrugCatalogueRead])
async def search_drugs(
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
    q: Annotated[str, Query(min_length=1, max_length=100)],
) -> list[DrugCatalogueRead]:
    drugs = await dc_repo.search_drugs(db, query=q)
    return [
        DrugCatalogueRead(
            drug_generic_name=d.drug_generic_name,
            drug_schedule=d.drug_schedule,
            is_prohibited=d.is_prohibited,
            requires_vertical=d.requires_vertical,
        )
        for d in drugs
    ]
