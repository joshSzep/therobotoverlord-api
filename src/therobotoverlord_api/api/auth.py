"""Authentication API endpoints for The Robot Overlord API."""

import logging

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import status

from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.models import EmailLoginRequest
from therobotoverlord_api.auth.models import LoginRequest
from therobotoverlord_api.auth.models import LogoutRequest
from therobotoverlord_api.auth.models import RegisterRequest
from therobotoverlord_api.auth.service import AuthService
from therobotoverlord_api.config.auth import get_auth_settings
from therobotoverlord_api.database.models.user import User

logger = logging.getLogger(__name__)

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


@router.get("/callback")
async def handle_callback(
    request: Request,
    response: Response,
    login_data: LoginRequest,
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
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Logout user by revoking session(s)."""
    try:
        auth_service = AuthService()

        if logout_data.revoke_all_sessions:
            # Revoke all user sessions
            revoked_count = await auth_service.logout_all_sessions(current_user.pk)
            message = f"Logged out from {revoked_count} sessions"
        else:
            # Revoke current session only
            # Get session ID from request cookies for current session logout
            refresh_token = request.cookies.get("__Secure-trl_rt")
            success = (
                await auth_service.logout_by_refresh_token(refresh_token)
                if refresh_token
                else False
            )
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
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current authenticated user information."""
    auth_service = AuthService()
    user = await auth_service.get_user_info(current_user.pk)

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
            "permissions": [],  # TODO(@josh): Add permissions logic
            "created_at": user.created_at,
        },
    }


@router.post("/login/email")
async def login_with_email(
    request: Request,
    response: Response,
    login_data: EmailLoginRequest,
):
    """Login with email and password."""

    logger.info(f"Starting login for email: {login_data.email}")

    try:
        logger.info("Creating AuthService instance")
        auth_service = AuthService()

        logger.info("Extracting client information")
        ip_address = _get_client_ip(request)
        user_agent = request.headers.get("user-agent")
        logger.info(f"Client IP: {ip_address}, User Agent: {user_agent}")

        logger.info("Calling auth_service.login_user")
        # Login user
        result = await auth_service.login_user(
            email=login_data.email,
            password=login_data.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not result:
            logger.warning(f"Login failed for {login_data.email}: Invalid credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        auth_response, token_pair = result
        logger.info(f"Login successful for user: {auth_response.user_pk}")

        logger.info("Setting authentication cookies")
        # Set cookies
        _set_auth_cookies(response, token_pair)

        logger.info("Preparing response data")
        response_data = {
            "status": "ok",
            "data": {
                "user": {
                    "id": str(auth_response.user_pk),
                    "email": login_data.email,
                    "username": auth_response.username,
                    "role": auth_response.role,
                    "loyalty_score": auth_response.loyalty_score,
                },
            },
        }

        logger.info("Login completed successfully")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed for {login_data.email}: {str(e)}")  # noqa: RUF010
        logger.exception("Full login error traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",  # noqa: RUF010
        ) from e


@router.post("/register")
async def register_user(
    request: Request,
    response: Response,
    register_data: RegisterRequest,
):
    """Register a new user with email and password."""

    logger.info(f"Starting registration for email: {register_data.email}")

    try:
        logger.info("Creating AuthService instance")
        auth_service = AuthService()

        logger.info("Extracting client information")
        ip_address = _get_client_ip(request)
        user_agent = request.headers.get("user-agent")
        logger.info(f"Client IP: {ip_address}, User Agent: {user_agent}")

        logger.info("Calling auth_service.register_user")
        # Register user
        auth_response, token_pair = await auth_service.register_user(
            email=register_data.email,
            username=register_data.username,
            password=register_data.password,
            ip_address=ip_address or "unknown",
            user_agent=user_agent,
        )
        logger.info(f"Registration successful for user: {auth_response.user_pk}")

        logger.info("Setting authentication cookies")
        # Set cookies
        _set_auth_cookies(response, token_pair)

        logger.info("Preparing response data")
        response_data = {
            "status": "ok",
            "data": {
                "user": {
                    "id": str(auth_response.user_pk),
                    "email": register_data.email,
                    "username": auth_response.username,
                    "role": auth_response.role,
                    "loyalty_score": auth_response.loyalty_score,
                },
            },
        }

        logger.info("Registration completed successfully")
        return response_data

    except Exception as e:
        logger.error(f"Registration failed for {register_data.email}: {str(e)}")  # noqa: RUF010
        logger.exception("Full registration error traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",  # noqa: RUF010
        ) from e


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
        return str(request.client.host)

    return None


def _set_auth_cookies(response: Response, token_pair) -> None:
    """Set authentication cookies on response."""

    settings = get_auth_settings()

    logger.info(
        f"Setting auth cookies with settings: domain='{settings.cookie_domain}', secure={settings.cookie_secure}, samesite={settings.cookie_samesite}"
    )

    # Use secure cookie names only in production (HTTPS)
    access_cookie_name = "__Secure-trl_at" if settings.cookie_secure else "trl_at"
    refresh_cookie_name = "__Secure-trl_rt" if settings.cookie_secure else "trl_rt"

    logger.info(
        f"Using cookie names: access={access_cookie_name}, refresh={refresh_cookie_name}"
    )

    # Prepare cookie kwargs
    access_cookie_kwargs = {
        "key": access_cookie_name,
        "value": token_pair.access_token.token,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
        "expires": token_pair.access_token.expires_at,
    }

    refresh_cookie_kwargs = {
        "key": refresh_cookie_name,
        "value": token_pair.refresh_token.token,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
        "expires": token_pair.refresh_token.expires_at,
    }

    # Only set domain if it's not empty
    if settings.cookie_domain:
        access_cookie_kwargs["domain"] = settings.cookie_domain
        refresh_cookie_kwargs["domain"] = settings.cookie_domain
        logger.info(f"Setting cookies with domain: {settings.cookie_domain}")
    else:
        logger.info("Setting cookies without domain (localhost)")

    logger.info(f"Access token expires at: {token_pair.access_token.expires_at}")
    logger.info(f"Refresh token expires at: {token_pair.refresh_token.expires_at}")

    response.set_cookie(
        key=access_cookie_kwargs["key"],
        value=access_cookie_kwargs["value"],
        httponly=access_cookie_kwargs["httponly"],
        secure=access_cookie_kwargs["secure"],
        samesite=access_cookie_kwargs["samesite"],
        path=access_cookie_kwargs["path"],
        expires=access_cookie_kwargs["expires"],
        domain=access_cookie_kwargs.get("domain"),
    )
    response.set_cookie(
        key=refresh_cookie_kwargs["key"],
        value=refresh_cookie_kwargs["value"],
        httponly=refresh_cookie_kwargs["httponly"],
        secure=refresh_cookie_kwargs["secure"],
        samesite=refresh_cookie_kwargs["samesite"],
        path=refresh_cookie_kwargs["path"],
        expires=refresh_cookie_kwargs["expires"],
        domain=refresh_cookie_kwargs.get("domain"),
    )

    logger.info("Auth cookies set successfully")


def _clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies from response."""
    settings = get_auth_settings()

    # Use correct cookie names based on secure setting
    access_cookie_name = "__Secure-trl_at" if settings.cookie_secure else "trl_at"
    refresh_cookie_name = "__Secure-trl_rt" if settings.cookie_secure else "trl_rt"

    # Prepare delete cookie kwargs
    delete_kwargs = {"path": "/"}
    if settings.cookie_domain:
        delete_kwargs["domain"] = settings.cookie_domain

    response.delete_cookie(key=access_cookie_name, **delete_kwargs)  # type: ignore[arg-type]
    response.delete_cookie(key=refresh_cookie_name, **delete_kwargs)  # type: ignore[arg-type]
