from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import DbSession, Redis
from app.api.v1.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    SendOtpRequest,
    SendOtpResponse,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    VerifyOtpRequest,
)
from app.core.config import settings
from app.core.ratelimit import rate_limit
from app.services import auth as auth_service

router = APIRouter(tags=["auth"])


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
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth_login", limit=10))],
)
async def login(
    body: LoginRequest,
    request: Request,
    db: DbSession,
    redis: Redis,
) -> TokenResponse:
    tokens = await auth_service.login(
        db,
        redis,
        email_or_phone=body.email_or_phone,
        password=body.password,
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
