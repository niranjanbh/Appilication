"""ICD-10 reference catalog search.

GET /v1/doctor/icd10-codes?q=... — autocomplete search over the curated kc_icd10_codes catalog.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.rbac import get_doctor_user
from app.repositories import diagnoses as diagnoses_repo

router = APIRouter(tags=["doctor-icd10"])


class Icd10CodeRead(BaseModel):
    code: str
    description: str
    category: str


@router.get("/icd10-codes", response_model=list[Icd10CodeRead])
async def search_icd10_codes(
    db: DbSession,
    user: Annotated[object, Depends(get_doctor_user)],
    q: Annotated[str, Query(min_length=1, max_length=100)],
) -> list[Icd10CodeRead]:
    codes = await diagnoses_repo.search_icd10_codes(db, query=q)
    return [
        Icd10CodeRead(code=c.code, description=c.description, category=c.category)
        for c in codes
    ]
