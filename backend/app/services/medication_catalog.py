"""Medication catalog service — admin CRUD, image upload lifecycle, doctor search.

Image upload mirrors the lab-report flow:
  initiate_image_upload → presigned S3 POST (key stored on the row)
  (client uploads directly to S3)
  finalize_image_upload → HEAD-verify the object exists
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DrugForm
from app.integrations import s3
from app.models.clinic import MedicationCatalog
from app.repositories import medication_catalog as catalog_repo

logger = structlog.get_logger(__name__)

_ALLOWED_IMAGE_TYPES = s3.IMAGE_CONTENT_TYPES
_MAX_IMAGE_BYTES = s3.MAX_IMAGE_SIZE_BYTES


class MedicationCatalogError(Exception):
    """Raised for validation failures (duplicate name, bad image type/size)."""


async def create_entry(
    db: AsyncSession,
    *,
    name: str,
    generic_name: str | None,
    form: DrugForm | None,
    strength: str | None,
    created_by_user_id: uuid.UUID,
) -> MedicationCatalog:
    name = name.strip()
    if not name:
        raise MedicationCatalogError("name is required")
    if await catalog_repo.get_by_name(db, name=name) is not None:
        raise MedicationCatalogError(f"A medication named '{name}' already exists")
    return await catalog_repo.create(
        db,
        name=name,
        generic_name=(generic_name or None),
        form=form,
        strength=(strength or None),
        created_by_user_id=created_by_user_id,
    )


async def update_entry(
    db: AsyncSession,
    *,
    catalog_id: uuid.UUID,
    **fields: Any,
) -> MedicationCatalog | None:
    # Drop keys the caller left unset so PATCH is partial.
    updates = {k: v for k, v in fields.items() if v is not None}
    if "name" in updates:
        new_name = str(updates["name"]).strip()
        existing = await catalog_repo.get_by_name(db, name=new_name)
        if existing is not None and existing.id != catalog_id:
            raise MedicationCatalogError(f"A medication named '{new_name}' already exists")
        updates["name"] = new_name
    return await catalog_repo.update_fields(db, catalog_id=catalog_id, **updates)


def _validate_image(content_type: str, file_size_bytes: int) -> None:
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise MedicationCatalogError(
            f"content_type must be one of: {', '.join(sorted(_ALLOWED_IMAGE_TYPES))}"
        )
    if file_size_bytes <= 0 or file_size_bytes > _MAX_IMAGE_BYTES:
        raise MedicationCatalogError(
            f"file_size_bytes must be between 1 and {_MAX_IMAGE_BYTES}"
        )


async def initiate_image_upload(
    db: AsyncSession,
    *,
    catalog_id: uuid.UUID,
    filename: str,
    content_type: str,
    file_size_bytes: int,
) -> dict[str, Any] | None:
    """Return presigned POST fields; store the pending key on the row."""
    _validate_image(content_type, file_size_bytes)
    entry = await catalog_repo.get(db, catalog_id=catalog_id)
    if entry is None:
        return None

    key = s3.medication_catalog_s3_key(entry.id, filename)
    presigned = s3.generate_image_upload_url(s3_key=key, content_type=content_type)
    await catalog_repo.set_image(
        db, catalog_id=entry.id, image_s3_key=key, image_content_type=content_type
    )
    logger.info("medication_catalog.image_initiated", catalog_id=str(entry.id))
    return {
        "catalog_id": entry.id,
        "upload_url": presigned["upload_url"],
        "fields": presigned["fields"],
        "s3_key": presigned["s3_key"],
        "content_type": content_type,
    }


async def finalize_image_upload(
    db: AsyncSession,
    *,
    catalog_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Verify the S3 object exists; returns None if catalog entry not found."""
    entry = await catalog_repo.get(db, catalog_id=catalog_id)
    if entry is None:
        return None
    if entry.image_s3_key is None:
        raise MedicationCatalogError("No pending image upload to finalize")

    meta = await asyncio.to_thread(s3.head_object, s3_key=entry.image_s3_key)
    if meta is None:
        raise MedicationCatalogError(
            "Upload not found in S3. Complete the upload before finalizing."
        )
    logger.info("medication_catalog.image_finalized", catalog_id=str(entry.id))
    return {"catalog_id": entry.id, "image_uploaded": True}


async def get_image_url(
    db: AsyncSession,
    *,
    catalog_id: uuid.UUID,
) -> str | None:
    """Presigned GET URL for the catalog image, or None if no image / not found."""
    entry = await catalog_repo.get(db, catalog_id=catalog_id)
    if entry is None or entry.image_s3_key is None:
        return None
    return s3.generate_download_url(s3_key=entry.image_s3_key)


async def store_image_bytes(
    db: AsyncSession,
    *,
    catalog_id: uuid.UUID,
    data: bytes,
    content_type: str,
    filename: str,
) -> MedicationCatalog | None:
    """Server-side image upload (admin portal): PUT bytes to S3, set the key.

    Unlike the mobile presigned flow, the admin portal posts the file to the
    backend, which uploads it to S3 with SSE-KMS via ``s3.put_bytes``.
    """
    _validate_image(content_type, len(data))
    entry = await catalog_repo.get(db, catalog_id=catalog_id)
    if entry is None:
        return None
    key = s3.medication_catalog_s3_key(entry.id, filename)
    await asyncio.to_thread(
        s3.put_bytes, s3_key=key, data=data, content_type=content_type
    )
    logger.info("medication_catalog.image_stored", catalog_id=str(entry.id))
    return await catalog_repo.set_image(
        db, catalog_id=entry.id, image_s3_key=key, image_content_type=content_type
    )
