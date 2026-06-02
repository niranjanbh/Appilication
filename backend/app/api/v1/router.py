from __future__ import annotations

from fastapi import APIRouter

api_v1_router = APIRouter()

# Sub-routers are registered here as each domain is built in P2+.
# Example:
#   from app.api.v1 import auth, clinic, wellness, doctor, admin, webhooks
#   api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
