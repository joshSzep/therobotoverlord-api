"""Authentication models for The Robot Overlord API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import EmailStr
from pydantic import Field

from therobotoverlord_api.database.models.base import UserRole


class TokenClaims(BaseModel):
    """JWT token claims model."""

    sub: UUID = Field(description="User UUID")
    role: UserRole = Field(description="User role")
    sid: str = Field(description="Session ID")
    authz_ver: int = Field(default=1, description="Authorization version")
    token_version: int = Field(default=1, description="Token version")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    scopes: list[str] = Field(default_factory=list, description="Token scopes")
    iss: str = Field(description="Token issuer")
    aud: str = Field(description="Token audience")
    iat: int = Field(description="Issued at timestamp")
    exp: int = Field(description="Expiration timestamp")
    nbf: int = Field(description="Not before timestamp")

    model_config = ConfigDict(use_enum_values=True)


class AccessToken(BaseModel):
    """Access token model."""

    token: str = Field(description="JWT access token")
    expires_at: datetime = Field(description="Token expiration time")
    max_expires_at: datetime = Field(description="Maximum token expiration time")


class RefreshToken(BaseModel):
    """Refresh token model."""

    token: str = Field(description="JWT refresh token")
    expires_at: datetime = Field(description="Token expiration time")
    session_id: str = Field(description="Session ID")


class TokenPair(BaseModel):
    """Token pair model."""

    access_token: AccessToken
    refresh_token: RefreshToken


class GoogleUserInfo(BaseModel):
    """Google OAuth user information."""

    id: str = Field(description="Google user ID")
    email: str = Field(description="User email")
    verified_email: bool = Field(description="Email verification status")
    name: str = Field(description="User full name")
    given_name: str = Field(description="User first name")
    family_name: str = Field(description="User last name")
    picture: str = Field(description="User profile picture URL")


class AuthResponse(BaseModel):
    """Authentication response model."""

    user_pk: UUID = Field(description="User UUID")
    username: str = Field(description="Username")
    role: UserRole = Field(description="User role")
    loyalty_score: int = Field(description="User loyalty score")
    is_new_user: bool = Field(description="Whether this is a new user registration")

    model_config = ConfigDict(use_enum_values=True)


class LoginRequest(BaseModel):
    """Login request model."""

    code: str = Field(description="OAuth authorization code")
    state: str | None = Field(default=None, description="OAuth state parameter")


class RefreshRequest(BaseModel):
    """Token refresh request model."""

    refresh_token: str = Field(description="Refresh token")


class LogoutRequest(BaseModel):
    """Logout request model."""

    revoke_all_sessions: bool = Field(
        default=False, description="Revoke all user sessions"
    )


class SessionInfo(BaseModel):
    """Session information model."""

    session_id: str = Field(description="Session ID")
    user_pk: UUID = Field(description="User UUID")
    created_at: datetime = Field(description="Session creation time")
    last_used_at: datetime = Field(description="Last session activity")
    last_used_ip: str | None = Field(default=None, description="Last used IP address")
    last_used_user_agent: str | None = Field(
        default=None, description="Last used user agent"
    )
    is_revoked: bool = Field(default=False, description="Session revocation status")
    reuse_detected: bool = Field(
        default=False, description="Token reuse detection flag"
    )


class EmailLoginRequest(BaseModel):
    """Email/password login request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=100, description="Username")
    password: str = Field(..., min_length=8, description="User password")


class PasswordResetRequest(BaseModel):
    """Password reset request."""

    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class EmailAuthResponse(BaseModel):
    """Email/password authentication response."""

    success: bool = Field(..., description="Whether authentication was successful")
    message: str = Field(..., description="Response message")
    user: dict | None = Field(None, description="User data if successful")
    access_token: str | None = Field(None, description="JWT access token")
    refresh_token: str | None = Field(None, description="JWT refresh token")
