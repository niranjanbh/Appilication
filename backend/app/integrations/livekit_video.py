"""LiveKit video integration.

Replaces the legacy 100ms (HMS) integration. Provides room creation, role-scoped
participant token generation, and S3 egress (recording) control.

Stub mode is active when KYROS_LIVEKIT_API_KEY is empty — returns synthetic IDs
and tokens so local dev and tests work without a running LiveKit server.

Token generation uses the official `livekit-api` Python SDK
(`livekit.api.AccessToken` + `livekit.api.VideoGrants`). Room management and egress
go through the SDK's async `LiveKitAPI` client over the REST/Twirp endpoint.

Data residency: the LiveKit deployment and its S3 egress bucket must live in
ap-south-1. The host is supplied via KYROS_LIVEKIT_HOST.

LiveKit docs: https://docs.livekit.io/home/get-started/authentication/
"""

from __future__ import annotations

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Participant token TTL — 1 h, plenty for a consultation session.
_TOKEN_TTL_SECONDS = 3600
# Room lifecycle tuning for a clinical call. The participant cap is per-room and
# resolved at creation: an explicit value (e.g. a staff-raised on-demand consult)
# wins, otherwise the platform default applies.
_EMPTY_TIMEOUT_SECONDS = 300


def _room_name(consultation_id: str) -> str:
    """Deterministic LiveKit room name for a consultation."""
    return f"kyros-consult-{consultation_id}"


def _api_url() -> str:
    """The HTTP(S) base URL for LiveKit server-side API calls.

    The configured host is a WebSocket URL (ws://…/wss://…) used by clients.
    The REST/Twirp API is reached over the matching http/https scheme.
    """
    host = settings.livekit_host
    if host.startswith("wss://"):
        return "https://" + host[len("wss://") :]
    if host.startswith("ws://"):
        return "http://" + host[len("ws://") :]
    return host


# ── Public API ─────────────────────────────────────────────────────────────────


def is_stub_mode() -> bool:
    return not settings.livekit_api_key


def _build_token(*, room_name: str, identity: str, user_id: str, is_doctor: bool) -> str:
    """Build a signed LiveKit participant JWT via the livekit-api SDK.

    Grants: join the named room, publish audio+video, subscribe to tracks.
    Doctors additionally get permission to update other participants' metadata
    (mute others) and to control egress (recording).
    """
    from livekit import api  # imported lazily so the module loads without the SDK

    grants = api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )
    if is_doctor:
        # Doctor moderation + recording control.
        grants.room_admin = True
        grants.can_update_own_metadata = True

    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(user_id)
        .with_ttl(_seconds_as_timedelta(_TOKEN_TTL_SECONDS))
        .with_grants(grants)
    )
    return str(token.to_jwt())


def _seconds_as_timedelta(seconds: int):  # type: ignore[no-untyped-def]
    from datetime import timedelta

    return timedelta(seconds=seconds)


async def create_room(
    *, consultation_id: str, max_participants: int | None = None
) -> str:
    """Create a LiveKit room for the given consultation.

    ``max_participants`` caps the room size; when None the platform default
    (settings.video_default_max_participants) applies. Returns the room name (used
    as the stable room identifier downstream). In stub mode returns a deterministic
    synthetic ID without hitting the server.
    """
    room_name = _room_name(consultation_id)
    cap = max_participants or settings.video_default_max_participants

    if is_stub_mode():
        synthetic_id = f"stub-room-{consultation_id}"
        logger.info("livekit.create_room.stub", consultation_id=consultation_id, room_id=synthetic_id)
        return synthetic_id

    from livekit import api

    lk = api.LiveKitAPI(
        url=_api_url(),
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )
    try:
        await lk.room.create_room(
            api.CreateRoomRequest(
                name=room_name,
                max_participants=cap,
                empty_timeout=_EMPTY_TIMEOUT_SECONDS,
            )
        )
    finally:
        await lk.aclose()

    logger.info(
        "livekit.create_room.ok",
        consultation_id=consultation_id,
        room_id=room_name,
        max_participants=cap,
    )
    return room_name


def generate_patient_token(*, room_id: str, user_id: str) -> str:
    """Return a patient-identity participant token for joining the room."""
    if is_stub_mode():
        return f"stub-patient-token-{room_id}-{user_id}"
    return _build_token(room_name=room_id, identity="patient", user_id=user_id, is_doctor=False)


def generate_doctor_token(*, room_id: str, user_id: str) -> str:
    """Return a doctor-identity participant token with moderation + recording rights."""
    if is_stub_mode():
        return f"stub-doctor-token-{room_id}-{user_id}"
    return _build_token(room_name=room_id, identity="doctor", user_id=user_id, is_doctor=True)


def generate_staff_token(*, room_id: str, user_id: str, role: str) -> str:
    """Return a support-participant token for staff (coordinator/admin).

    The participant joins with a visible role identity ("coordinator"/"admin") so
    their presence is never covert — the doctor (room admin) sees every
    participant. Staff may publish (an interpreter speaks) and subscribe, but get
    NO moderation or recording rights; only the doctor moderates and records.
    """
    if is_stub_mode():
        return f"stub-{role}-token-{room_id}-{user_id}"
    return _build_token(room_name=room_id, identity=role, user_id=user_id, is_doctor=False)


async def start_recording(*, room_name: str) -> str | None:
    """Start an S3 egress recording for the room if a recordings bucket is set.

    Returns the egress_id, or None when recording is not configured or in stub mode.
    """
    if is_stub_mode():
        logger.info("livekit.start_recording.stub", room=room_name)
        return None
    if not settings.livekit_recordings_bucket:
        logger.info("livekit.start_recording.skipped", reason="no_bucket")
        return None

    from livekit import api

    lk = api.LiveKitAPI(
        url=_api_url(),
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )
    try:
        s3_upload = api.S3Upload(
            bucket=settings.livekit_recordings_bucket,
            region=settings.aws_region,
            access_key=settings.aws_access_key_id,
            secret=settings.aws_secret_access_key,
        )
        # Security rule #6: all PHI in S3 must be encrypted with SSE-KMS.
        # LiveKit's S3Upload proto doesn't expose SSE params directly — encryption
        # is enforced by a bucket-default KMS policy on the recordings bucket.
        # Infra must set the bucket's default encryption to aws:kms with the key
        # from KYROS_S3_KMS_KEY_ID before recordings are enabled in production.
        if not settings.s3_kms_key_id:
            logger.warning(
                "livekit.start_recording.no_kms_key",
                reason="s3_kms_key_id not configured; relying on bucket-default encryption",
            )
        request = api.RoomCompositeEgressRequest(
            room_name=room_name,
            file_outputs=[
                api.EncodedFileOutput(
                    file_type=api.EncodedFileType.MP4,
                    filepath=f"{room_name}/{{time}}.mp4",
                    s3=s3_upload,
                )
            ],
        )
        info = await lk.egress.start_room_composite_egress(request)
    finally:
        await lk.aclose()

    egress_id: str = info.egress_id
    logger.info("livekit.start_recording.ok", room=room_name, egress_id=egress_id)
    return egress_id


async def stop_recording(*, egress_id: str) -> None:
    """Stop an active egress recording by id. No-op in stub mode."""
    if is_stub_mode():
        logger.info("livekit.stop_recording.stub", egress_id=egress_id)
        return

    from livekit import api

    lk = api.LiveKitAPI(
        url=_api_url(),
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )
    try:
        await lk.egress.stop_egress(api.StopEgressRequest(egress_id=egress_id))
    finally:
        await lk.aclose()

    logger.info("livekit.stop_recording.ok", egress_id=egress_id)
