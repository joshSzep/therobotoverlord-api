"""Authentication API endpoints for The Robot Overlord API."""

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import status

from therobotoverlord_api.auth.middleware import AuthenticatedUser
from therobotoverlord_api.auth.middleware import get_current_user
from therobotoverlord_api.auth.models import LoginRequest
from therobotoverlord_api.auth.models import LogoutRequest
from therobotoverlord_api.auth.rate_limiting import check_auth_rate_limit
from therobotoverlord_api.auth.service import AuthService
from therobotoverlord_api.config.auth import get_auth_settings

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/login")
async def initiate_login():
    """Initiate Google OAuth login flow."""
    auth_service = AuthService()
    authorization_url, state = await auth_service.initiate_login()

    return {
        "status": "ok",
        "data": {
            "authorization_url": authorization_url,
            "state": state,
        },
    }


@router.post("/callback")
async def oauth_callback(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    _: Annotated[None, Depends(check_auth_rate_limit)],
):
    """Handle Google OAuth callback and complete login."""
    try:
        auth_service = AuthService()

        # Get client info for session tracking
        ip_address = _get_client_ip(request)
        user_agent = request.headers.get("user-agent")

        # Complete login
        auth_response, token_pair = await auth_service.complete_login(
            authorization_code=login_data.code,
            state=login_data.state,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Set authentication cookies
        _set_auth_cookies(response, token_pair)

        return {
            "status": "ok",
            "data": auth_response,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        ) from e


@router.post("/refresh")
async def refresh_tokens(
    request: Request,
    response: Response,
    _: Annotated[None, Depends(check_auth_rate_limit)],
):
    """Refresh access token using refresh token."""
    refresh_token = request.cookies.get("__Secure-trl_rt")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    try:
        auth_service = AuthService()

        # Get client info for session tracking
        ip_address = _get_client_ip(request)
        user_agent = request.headers.get("user-agent")

        # Refresh tokens
        token_pair = await auth_service.refresh_tokens(
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not token_pair:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Set new authentication cookies
        _set_auth_cookies(response, token_pair)

        return {
            "status": "ok",
            "data": {
                "message": "Tokens refreshed successfully",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        ) from e


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    logout_data: LogoutRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    _: Annotated[None, Depends(check_auth_rate_limit)],
):
    """Logout user by revoking session(s)."""
    try:
        auth_service = AuthService()

        if logout_data.revoke_all_sessions:
            # Revoke all user sessions
            revoked_count = await auth_service.logout_all_sessions(current_user.user_id)
            message = f"Logged out from {revoked_count} sessions"
        else:
            # Revoke current session only
            success = await auth_service.logout(current_user.session_id)
            message = "Logged out successfully" if success else "Logout failed"

        # Clear authentication cookies
        _clear_auth_cookies(response)

        return {
            "status": "ok",
            "data": {
                "message": message,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        ) from e


@router.get("/me")
async def get_current_user_info(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
):
    """Get current authenticated user information."""
    auth_service = AuthService()
    user = await auth_service.get_user_info(current_user.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "status": "ok",
        "data": {
            "user_id": user.pk,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "loyalty_score": user.loyalty_score,
            "permissions": current_user.permissions,
            "created_at": user.created_at,
        },
    }


@router.get("/jwks")
async def get_jwks():
    """Get JSON Web Key Set for token validation."""
    auth_service = AuthService()
    return auth_service.jwt_service.create_jwks_response()


def _get_client_ip(request: Request) -> str | None:
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

    return None


def _set_auth_cookies(response: Response, token_pair) -> None:
    """Set authentication cookies on response."""
    settings = get_auth_settings()

    response.set_cookie(
        key="__Secure-trl_at",
        value=token_pair.access_token.token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
        expires=token_pair.access_token.expires_at,
    )

    response.set_cookie(
        key="__Secure-trl_rt",
        value=token_pair.refresh_token.token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
        expires=token_pair.refresh_token.expires_at,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies from response."""
    settings = get_auth_settings()

    response.delete_cookie(
        key="__Secure-trl_at",
        domain=settings.cookie_domain,
        path="/",
    )

    response.delete_cookie(
        key="__Secure-trl_rt",
        domain=settings.cookie_domain,
        path="/",
    )
