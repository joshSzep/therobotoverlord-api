"""JWT token service for The Robot Overlord API."""

import secrets

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
from uuid import UUID

import jwt

from jwt import DecodeError
from jwt import ExpiredSignatureError
from jwt import InvalidTokenError

from therobotoverlord_api.auth.models import AccessToken
from therobotoverlord_api.auth.models import RefreshToken
from therobotoverlord_api.auth.models import TokenClaims
from therobotoverlord_api.auth.models import TokenPair
from therobotoverlord_api.config.auth import get_auth_settings
from therobotoverlord_api.database.models.base import UserRole


class JWTService:
    """JWT token management service."""

    def __init__(self):
        self._settings = get_auth_settings()

    def generate_session_id(self) -> str:
        """Generate a secure session ID."""
        return secrets.token_urlsafe(32)

    def create_token_pair(
        self,
        user_id: UUID,
        role: UserRole,
        permissions: list[str] | None = None,
        session_id: str | None = None,
    ) -> TokenPair:
        """Create access and refresh token pair."""
        if permissions is None:
            permissions = []
        if session_id is None:
            session_id = self.generate_session_id()

        now = datetime.now(UTC)
        access_expires_at = now + timedelta(
            seconds=self._settings.access_token_lifetime
        )
        max_expires_at = now + timedelta(
            seconds=self._settings.access_token_max_lifetime
        )
        refresh_expires_at = now + timedelta(
            seconds=self._settings.refresh_token_lifetime
        )

        # Create access token
        access_claims = TokenClaims(
            sub=user_id,
            role=role,
            sid=session_id,
            permissions=permissions,
            iss=self._settings.jwt_issuer,
            aud=self._settings.jwt_audience,
            iat=int(now.timestamp()),
            exp=int(access_expires_at.timestamp()),
            nbf=int(now.timestamp()),
        )

        access_token = AccessToken(
            token=self._encode_token(access_claims.model_dump()),
            expires_at=access_expires_at,
            max_expires_at=max_expires_at,
        )

        # Create refresh token
        refresh_claims = {
            "sub": str(user_id),
            "sid": session_id,
            "type": "refresh",
            "iss": self._settings.jwt_issuer,
            "aud": self._settings.jwt_audience,
            "iat": int(now.timestamp()),
            "exp": int(refresh_expires_at.timestamp()),
            "nbf": int(now.timestamp()),
        }

        refresh_token = RefreshToken(
            token=self._encode_token(refresh_claims),
            expires_at=refresh_expires_at,
            session_id=session_id,
        )

        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    def extend_access_token(
        self,
        token: str,
        max_expires_at: datetime,
    ) -> AccessToken | None:
        """Extend access token lifetime based on activity."""
        try:
            token_claims = self.decode_token(token)
            if not token_claims:
                return None

            now = datetime.now(UTC)
            current_exp = datetime.fromtimestamp(token_claims.exp, UTC)

            # Check if token can be extended (not past max lifetime)
            if now >= max_expires_at:
                return None

            # Calculate new expiration (original + extension, but not past max)
            new_expires_at = min(
                current_exp + timedelta(seconds=self._settings.access_token_extension),
                max_expires_at,
            )

            # Create updated claims dict for encoding
            claims_dict = token_claims.model_dump()
            claims_dict["exp"] = int(new_expires_at.timestamp())
            claims_dict["iat"] = int(now.timestamp())

            return AccessToken(
                token=self._encode_token(claims_dict),
                expires_at=new_expires_at,
                max_expires_at=max_expires_at,
            )

        except (DecodeError, ExpiredSignatureError, InvalidTokenError):
            return None

    def decode_token(self, token: str) -> TokenClaims | None:
        """Decode and validate JWT token."""
        try:
            claims = jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=[self._settings.jwt_algorithm],
                audience=self._settings.jwt_audience,
                issuer=self._settings.jwt_issuer,
            )
            return TokenClaims(**claims)
        except (DecodeError, ExpiredSignatureError, InvalidTokenError):
            return None

    def decode_token_claims(self, token: str) -> TokenClaims | None:
        """Decode token into TokenClaims model."""
        return self.decode_token(token)

    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired."""
        try:
            jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=[self._settings.jwt_algorithm],
                audience=self._settings.jwt_audience,
                issuer=self._settings.jwt_issuer,
            )
            return False
        except ExpiredSignatureError:
            return True
        except (DecodeError, InvalidTokenError):
            return True

    def extract_session_id(self, token: str) -> str | None:
        """Extract session ID from token without full validation."""
        try:
            # Decode without verification to get session ID
            claims = jwt.decode(token, options={"verify_signature": False})
            return claims.get("sid")
        except Exception:
            return None

    def _encode_token(self, claims: dict[str, Any]) -> str:
        """Encode claims into JWT token."""
        # Convert UUIDs to strings for JSON serialization
        serializable_claims = {}
        for key, value in claims.items():
            if isinstance(value, UUID):
                serializable_claims[key] = str(value)
            elif isinstance(value, datetime):
                serializable_claims[key] = int(value.timestamp())
            else:
                serializable_claims[key] = value

        return jwt.encode(
            serializable_claims,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

    def create_jwks_response(self) -> dict[str, Any]:
        """Create JWKS (JSON Web Key Set) response for token validation."""
        # For HS256, we don't expose the key in JWKS
        # This is a placeholder for future asymmetric key support
        return {
            "keys": [
                {
                    "kty": "oct",
                    "use": "sig",
                    "kid": "default",
                    "alg": self._settings.jwt_algorithm,
                }
            ]
        }
