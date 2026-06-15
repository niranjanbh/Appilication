from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import DbSession, Redis
from app.api.v1.auth.schemas import (
    AuthConfigResponse,
    GoogleLoginRequest,
    LoginRequest,
    MfaChallengeResponse,
    MfaConfirmRequest,
    MfaConfirmResponse,
    MfaDisableRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RefreshRequest,
    SendOtpRequest,
    SendOtpResponse,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    VerifyOtpRequest,
)
from app.core.audit import AuditContext
from app.core.config import settings
from app.core.ratelimit import rate_limit
from app.core.rbac import get_any_staff_user, require_mfa
from app.db.enums import ActorRole
from app.services import auth as auth_service
from app.services import platform_settings_service

router = APIRouter(tags=["auth"])


def _audit_ctx(request: Request, user: object) -> AuditContext:
    from app.models.identity import User as UserModel

    assert isinstance(user, UserModel)
    return AuditContext(
        actor_user_id=user.id,
        actor_role=ActorRole(user.role.value),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=201,
    dependencies=[Depends(rate_limit("auth_signup", limit=10))],
)
async def signup(
    body: SignupRequest,
    request: Request,
    db: DbSession,
    redis: Redis,
) -> SignupResponse:
    result = await auth_service.signup(
        db,
        redis,
        phone=body.phone,
        email=body.email,
        name=body.name,
        password=body.password,
        channel=body.channel,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    otp_hint: str | None = None
    if settings.debug:
        otp_hint = await redis.get(f"otp:phone:{result.phone}:debug")
    return SignupResponse(
        message="Account created. Check your phone for the OTP.",
        phone=result.phone,
        otp_hint=otp_hint,
    )


@router.post(
    "/send-otp",
    response_model=SendOtpResponse,
    dependencies=[Depends(rate_limit("auth_send_otp", limit=5))],
)
async def send_otp(
    body: SendOtpRequest,
    request: Request,
    db: DbSession,
    redis: Redis,
) -> SendOtpResponse:
    await auth_service.send_otp(
        db,
        redis,
        phone=body.phone,
        channel=body.channel,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    return SendOtpResponse(message="OTP sent.")


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth_verify_otp", limit=10))],
)
async def verify_otp(
    body: VerifyOtpRequest,
    request: Request,
    db: DbSession,
    redis: Redis,
) -> TokenResponse:
    tokens = await auth_service.verify_otp(
        db,
        redis,
        phone=body.phone,
        otp=body.otp,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post(
    "/login",
    response_model=TokenResponse | MfaChallengeResponse,
    dependencies=[Depends(rate_limit("auth_login", limit=10))],
)
async def login(
    body: LoginRequest,
    request: Request,
    db: DbSession,
    redis: Redis,
) -> TokenResponse | MfaChallengeResponse:
    result = await auth_service.login(
        db,
        redis,
        email_or_phone=body.email_or_phone,
        password=body.password,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    if isinstance(result, auth_service.MfaChallenge):
        return MfaChallengeResponse(
            challenge_token=result.challenge_token,
            expires_in=result.expires_in,
        )
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_in=result.expires_in,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth_refresh", limit=30))],
)
async def refresh(
    body: RefreshRequest,
    request: Request,
    db: DbSession,
) -> TokenResponse:
    tokens = await auth_service.refresh(
        db,
        raw_token=body.refresh_token,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
    dependencies=[Depends(rate_limit("auth_password_reset_request", limit=5))],
)
async def password_reset_request(
    body: PasswordResetRequest,
    request: Request,
    db: DbSession,
    redis: Redis,
) -> PasswordResetRequestResponse:
    user_id = await auth_service.request_password_reset(
        db,
        redis,
        identifier=body.identifier,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    otp_hint: str | None = None
    if settings.debug and user_id is not None:
        otp_hint = await redis.get(f"otp:pwd_reset:{user_id}:debug")
    # Generic message — identical whether or not the identifier exists.
    return PasswordResetRequestResponse(
        message="If an account exists, a reset code has been sent.",
        otp_hint=otp_hint,
    )


@router.post(
    "/password-reset/confirm",
    response_model=PasswordResetConfirmResponse,
    dependencies=[Depends(rate_limit("auth_password_reset_confirm", limit=10))],
)
async def password_reset_confirm(
    body: PasswordResetConfirmRequest,
    request: Request,
    db: DbSession,
    redis: Redis,
) -> PasswordResetConfirmResponse:
    await auth_service.confirm_password_reset(
        db,
        redis,
        identifier=body.identifier,
        otp=body.otp,
        new_password=body.new_password,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    return PasswordResetConfirmResponse(
        message="Password updated. Please sign in with your new password."
    )


@router.post(
    "/google",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth_google", limit=10))],
)
async def google_login(
    body: GoogleLoginRequest,
    request: Request,
    db: DbSession,
) -> TokenResponse:
    tokens = await auth_service.google_login(
        db,
        id_token=body.id_token,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.get("/config", response_model=AuthConfigResponse)
async def auth_config(db: DbSession) -> AuthConfigResponse:
    """Public client config — lets the app decide whether to show Google sign-in."""
    return AuthConfigResponse(
        google_oauth_enabled=await platform_settings_service.is_google_oauth_enabled(db),
    )


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(
    request: Request,
    db: DbSession,
    user: object = Depends(get_any_staff_user),
) -> MfaSetupResponse:
    secret, uri = await auth_service.mfa_setup(
        db,
        user,  # type: ignore[arg-type]
        _audit_ctx(request, user),
        mfa_verified=bool(getattr(request.state, "mfa_verified", False)),
    )
    return MfaSetupResponse(secret=secret, provisioning_uri=uri)


@router.post("/mfa/confirm", response_model=MfaConfirmResponse)
async def mfa_confirm(
    body: MfaConfirmRequest,
    request: Request,
    db: DbSession,
    user: object = Depends(get_any_staff_user),
) -> MfaConfirmResponse:
    recovery_codes = await auth_service.mfa_confirm(
        db,
        user,  # type: ignore[arg-type]
        _audit_ctx(request, user),
        code=body.code,
    )
    return MfaConfirmResponse(recovery_codes=recovery_codes)


@router.post("/mfa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def mfa_disable(
    body: MfaDisableRequest,
    request: Request,
    db: DbSession,
    user: object = Depends(require_mfa),
) -> None:
    await auth_service.mfa_disable(
        db,
        user,  # type: ignore[arg-type]
        _audit_ctx(request, user),
        password=body.password,
    )


@router.post(
    "/mfa/verify",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth_mfa_verify", limit=10))],
)
async def mfa_verify(
    body: MfaVerifyRequest,
    request: Request,
    db: DbSession,
    redis: Redis,
) -> TokenResponse:
    tokens = await auth_service.mfa_verify(
        db,
        redis,
        challenge_token=body.challenge_token,
        code=body.code,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        request_id=getattr(request.state, "request_id", ""),
    )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )
