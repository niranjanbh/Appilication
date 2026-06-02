from __future__ import annotations

import uuid


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def new_uuid_str() -> str:
    return str(uuid.uuid4())
