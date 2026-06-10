from __future__ import annotations


class KyrosDomainError(Exception):
    """Base for all domain errors. Subclasses map to HTTP status codes in api/errors.py."""

    status_code: int = 400
    detail: str = "bad_request"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(KyrosDomainError):
    status_code = 404
    detail = "not_found"


class ConflictError(KyrosDomainError):
    status_code = 409
    detail = "conflict"


class BusinessRuleError(KyrosDomainError):
    status_code = 422
    detail = "business_rule_violation"


class PaymentRequiredError(KyrosDomainError):
    status_code = 402
    detail = "payment_required"


class AuthenticationError(KyrosDomainError):
    status_code = 401
    detail = "authentication_required"


class AuthorizationError(KyrosDomainError):
    status_code = 403
    detail = "forbidden"


class PhoneNotVerifiedError(KyrosDomainError):
    status_code = 403
    detail = "phone_not_verified"

    def __init__(self, phone: str | None = None) -> None:
        super().__init__()
        self.phone = phone


class OtpCooldownError(KyrosDomainError):
    status_code = 429
    detail = "otp_cooldown"


class OtpMaxAttemptsError(KyrosDomainError):
    status_code = 429
    detail = "otp_max_attempts"


class RateLimitedError(KyrosDomainError):
    status_code = 429
    detail = "rate_limited"
