"""Rate limiting dependencies and middleware for FastAPI."""

import logging

from typing import Annotated

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status

from therobotoverlord_api.auth.middleware import AuthenticatedUser
from therobotoverlord_api.auth.middleware import get_current_user_optional
from therobotoverlord_api.services.rate_limiting_service import (
    get_rate_limiting_service,
)

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check for forwarded headers first
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # Fall back to direct connection
    if request.client and hasattr(request.client, "host"):
        return request.client.host

    return "unknown"


async def check_auth_rate_limit(request: Request) -> None:
    """Rate limiting dependency for authentication endpoints."""
    rate_service = await get_rate_limiting_service()
    ip_address = _get_client_ip(request)

    # Get user ID if available (for refresh token endpoints)
    user = await get_current_user_optional(request)
    user_id = str(user.user_id) if user else None

    result = await rate_service.check_auth_rate_limit(ip_address, user_id)

    if not result.allowed:
        logger.warning(
            f"Auth rate limit exceeded for IP {ip_address}, "
            f"user {user_id}, limit: {result.limit}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication requests. Please try again later.",
            headers={
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Reset": str(int(result.reset_time.timestamp())),
                "Retry-After": str(result.retry_after) if result.retry_after else "60",
            },
        )


async def check_admin_rate_limit(
    request: Request,
    current_user: Annotated[
        AuthenticatedUser | None, Depends(get_current_user_optional)
    ],
) -> None:
    """Rate limiting dependency for admin endpoints."""
    if not current_user:
        return  # Let auth middleware handle authentication

    rate_service = await get_rate_limiting_service()
    result = await rate_service.check_admin_rate_limit(str(current_user.user_id))

    if not result.allowed:
        logger.warning(
            f"Admin rate limit exceeded for user {current_user.user_id}, "
            f"limit: {result.limit}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many admin requests. Please try again later.",
            headers={
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Reset": str(int(result.reset_time.timestamp())),
                "Retry-After": str(result.retry_after) if result.retry_after else "60",
            },
        )


async def check_rbac_rate_limit(
    request: Request,
    current_user: Annotated[
        AuthenticatedUser | None, Depends(get_current_user_optional)
    ],
) -> None:
    """Rate limiting dependency for RBAC endpoints."""
    if not current_user:
        return  # Let auth middleware handle authentication

    rate_service = await get_rate_limiting_service()
    result = await rate_service.check_rbac_rate_limit(str(current_user.user_id))

    if not result.allowed:
        logger.warning(
            f"RBAC rate limit exceeded for user {current_user.user_id}, "
            f"limit: {result.limit}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many RBAC requests. Please try again later.",
            headers={
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Reset": str(int(result.reset_time.timestamp())),
                "Retry-After": str(result.retry_after) if result.retry_after else "60",
            },
        )


async def check_sanctions_rate_limit(
    request: Request,
    current_user: Annotated[
        AuthenticatedUser | None, Depends(get_current_user_optional)
    ],
) -> None:
    """Rate limiting dependency for sanctions endpoints."""
    if not current_user:
        return  # Let auth middleware handle authentication

    rate_service = await get_rate_limiting_service()
    result = await rate_service.check_sanctions_rate_limit(str(current_user.user_id))

    if not result.allowed:
        logger.warning(
            f"Sanctions rate limit exceeded for user {current_user.user_id}, "
            f"limit: {result.limit}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sanctions requests. Please try again later.",
            headers={
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Reset": str(int(result.reset_time.timestamp())),
                "Retry-After": str(result.retry_after) if result.retry_after else "60",
            },
        )


async def check_content_rate_limit(
    request: Request,
    current_user: Annotated[
        AuthenticatedUser | None, Depends(get_current_user_optional)
    ],
) -> None:
    """Rate limiting dependency for content creation endpoints."""
    if not current_user:
        return  # Let auth middleware handle authentication

    rate_service = await get_rate_limiting_service()
    result = await rate_service.check_content_rate_limit(str(current_user.user_id))

    if not result.allowed:
        logger.warning(
            f"Content rate limit exceeded for user {current_user.user_id}, "
            f"limit: {result.limit}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many content creation requests. Please try again later.",
            headers={
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Reset": str(int(result.reset_time.timestamp())),
                "Retry-After": str(result.retry_after) if result.retry_after else "60",
            },
        )


async def check_general_rate_limit(request: Request) -> None:
    """Rate limiting dependency for general API endpoints."""
    rate_service = await get_rate_limiting_service()
    ip_address = _get_client_ip(request)

    result = await rate_service.check_general_rate_limit(ip_address)

    if not result.allowed:
        logger.warning(
            f"General rate limit exceeded for IP {ip_address}, limit: {result.limit}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Reset": str(int(result.reset_time.timestamp())),
                "Retry-After": str(result.retry_after) if result.retry_after else "60",
            },
        )
