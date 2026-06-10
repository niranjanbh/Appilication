from __future__ import annotations

from pathlib import Path

import structlog
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine

logger = structlog.get_logger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


class SchemaOutOfDateError(RuntimeError):
    """The database schema does not match the Alembic head revision(s)."""


def script_heads() -> set[str]:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    return set(ScriptDirectory.from_config(cfg).get_heads())


async def assert_schema_is_current(engine: AsyncEngine) -> None:
    """Security rule 15 safety net: refuse to serve traffic against an
    outdated schema. Migrations are applied via `make migrate`, never here.
    """
    heads = script_heads()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            applied = {row[0] for row in result}
    except (ProgrammingError, DBAPIError) as err:
        raise SchemaOutOfDateError(
            "alembic_version table not found — no migrations applied. "
            "Run `make migrate` before starting the application."
        ) from err
    if applied != heads:
        raise SchemaOutOfDateError(
            f"Database schema revision {sorted(applied)} does not match "
            f"migration head {sorted(heads)}. Run `make migrate` before "
            "starting the application."
        )
    logger.info("schema_check_passed", revision=sorted(applied))
