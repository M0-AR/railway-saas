from typing import Any


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, details: Any = None, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if code:
            self.code = code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class EntitlementError(AppError):
    status_code = 402
    code = "entitlement_required"


class QuotaExceededError(AppError):
    status_code = 402
    code = "quota_exceeded"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"


class NotConfiguredError(AppError):
    status_code = 503
    code = "not_configured"
