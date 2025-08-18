"""Google OAuth integration service for The Robot Overlord API."""

import secrets

import httpx

from google.auth.transport.requests import Request  # type: ignore[import-untyped]
from google.oauth2 import id_token  # type: ignore[import-untyped]
from google_auth_oauthlib.flow import Flow

from therobotoverlord_api.auth.models import GoogleUserInfo
from therobotoverlord_api.config.auth import get_auth_settings


class GoogleOAuthService:
    """Google OAuth 2.0 integration service."""

    def __init__(self):
        self._settings = get_auth_settings()
        self._scopes = [
            "openid",
            "email",
            "profile",
        ]

    def get_authorization_url(self, state: str | None = None) -> tuple[str, str]:
        """Generate Google OAuth authorization URL."""
        if state is None:
            state = secrets.token_urlsafe(32)

        # Create OAuth flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self._settings.google_client_id,
                    "client_secret": self._settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self._settings.google_redirect_uri],
                }
            },
            scopes=self._scopes,
        )
        flow.redirect_uri = self._settings.google_redirect_uri

        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="consent",  # Force consent to ensure we get refresh token
        )

        return authorization_url, state

    async def exchange_code_for_tokens(
        self, authorization_code: str, state: str | None = None
    ) -> tuple[GoogleUserInfo, str]:
        """Exchange authorization code for access token and user info."""
        # Create OAuth flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self._settings.google_client_id,
                    "client_secret": self._settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self._settings.google_redirect_uri],
                }
            },
            scopes=self._scopes,
            state=state,
        )
        flow.redirect_uri = self._settings.google_redirect_uri

        # Exchange code for tokens
        flow.fetch_token(code=authorization_code)

        # Get user info from ID token
        credentials = flow.credentials
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            Request(),
            self._settings.google_client_id,
        )

        # Validate required fields
        if not id_info.get("email_verified", False):
            raise ValueError("Email not verified by Google")

        user_info = GoogleUserInfo(
            id=id_info["sub"],
            email=id_info["email"],
            verified_email=id_info.get("email_verified", False),
            name=id_info.get("name", ""),
            given_name=id_info.get("given_name", ""),
            family_name=id_info.get("family_name", ""),
            picture=id_info.get("picture", ""),
        )

        return user_info, credentials.token

    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """Get user information using access token."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()

            data = response.json()

            return GoogleUserInfo(
                id=data["id"],
                email=data["email"],
                verified_email=data.get("verified_email", False),
                name=data.get("name", ""),
                given_name=data.get("given_name", ""),
                family_name=data.get("family_name", ""),
                picture=data.get("picture", ""),
            )

    async def revoke_token(self, access_token: str) -> bool:
        """Revoke Google access token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    data={"token": access_token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                return response.status_code == 200
        except Exception:
            return False

    def generate_state_parameter(self) -> str:
        """Generate secure state parameter for CSRF protection."""
        return secrets.token_urlsafe(32)
