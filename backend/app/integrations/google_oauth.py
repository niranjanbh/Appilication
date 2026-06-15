"""Google Sign-In — server-side ID token verification.

The mobile app obtains a Google ID token (JWT) via the native Google sign-in
flow and posts it to the backend. We verify the token's signature, issuer, and
expiry against Google's published certs, then check the audience against our
configured client IDs. No client secret is needed for ID-token verification.

────────────────────────────────────────────────────────────────────────────────
SETUP
────────────────────────────────────────────────────────────────────────────────
1. Create OAuth 2.0 client IDs in Google Cloud Console (one per platform: Web,
   iOS, Android). The ID token's `aud` claim equals the client ID that requested
   it, so every client ID the app may use must be listed.

2. Set the accepted audiences (comma-separated) in .env / Secrets Manager:
     KYROS_GOOGLE_OAUTH_CLIENT_IDS=<web-id>.apps.googleusercontent.com,<ios-id>...

3. Activation is gated by an admin toggle in ad_platform_settings
   (google_oauth_enabled). The feature does nothing until an admin turns it on,
   even if client IDs are configured.

No PHI is logged here — only the Google subject hash on failure.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import anyio
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Valid issuers for Google-issued ID tokens.
_GOOGLE_ISSUERS = frozenset(
    {"accounts.google.com", "https://accounts.google.com"}
)


@dataclass
class GoogleIdentity:
    sub: str
    email: str | None
    email_verified: bool
    name: str | None


def _verify_sync(token: str) -> dict[str, object]:
    # Imported lazily so the dependency only loads when the feature is used.
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    request = google_requests.Request()
    # verify_oauth2_token checks signature, expiry, and issuer. We verify the
    # audience ourselves below to support multiple client IDs (web/iOS/Android).
    # google-auth ships no type stubs, hence the ignore.
    claims: dict[str, object] = google_id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
        token, request
    )
    return claims


async def verify_id_token(token: str) -> GoogleIdentity | None:
    """Verify a Google ID token. Returns the identity, or None if invalid.

    Non-raising — the caller maps None to an authentication error.
    """
    audiences = settings.google_oauth_client_id_list
    if not audiences:
        logger.error("google_oauth.no_client_ids_configured")
        return None

    try:
        claims = await anyio.to_thread.run_sync(_verify_sync, token)
    except Exception:
        logger.warning("google_oauth.token_verify_failed")
        return None

    if str(claims.get("iss", "")) not in _GOOGLE_ISSUERS:
        logger.warning("google_oauth.bad_issuer")
        return None

    if claims.get("aud") not in audiences:
        logger.warning("google_oauth.audience_mismatch")
        return None

    sub = claims.get("sub")
    if not sub:
        logger.warning("google_oauth.missing_subject")
        return None

    email = claims.get("email")
    return GoogleIdentity(
        sub=str(sub),
        email=str(email) if email else None,
        email_verified=bool(claims.get("email_verified", False)),
        name=str(claims["name"]) if claims.get("name") else None,
    )


def sub_hash(sub: str) -> str:
    return hashlib.sha256(sub.encode()).hexdigest()[:12]
