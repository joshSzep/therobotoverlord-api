"""Tests for Google OAuth service."""

import asyncio

from unittest.mock import AsyncMock
from unittest.mock import PropertyMock
from unittest.mock import patch
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest

from therobotoverlord_api.auth.google_oauth import GoogleOAuthService
from therobotoverlord_api.auth.models import GoogleUserInfo


class TestGoogleOAuthService:
    """Test Google OAuth service functionality."""

    @pytest.fixture
    def oauth_service(self, auth_settings):
        """Create Google OAuth service instance."""
        with patch(
            "therobotoverlord_api.auth.google_oauth.get_auth_settings",
            return_value=auth_settings,
        ):
            return GoogleOAuthService()

    def test_get_authorization_url(self, oauth_service):
        """Test authorization URL generation."""
        state = "test_state"
        auth_url, returned_state = oauth_service.get_authorization_url(state)

        # Parse URL components
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)

        assert parsed_url.scheme == "https"
        assert parsed_url.netloc == "accounts.google.com"
        assert parsed_url.path == "/o/oauth2/auth"

        # Check required parameters
        assert query_params["client_id"][0] == "test_client_id"
        assert (
            query_params["redirect_uri"][0]
            == "http://localhost:8000/api/v1/auth/callback"
        )
        assert query_params["response_type"][0] == "code"
        assert query_params["scope"][0] == "openid email profile"
        assert query_params["state"][0] == state
        assert "access_type" in query_params
        assert "prompt" in query_params

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(
        self, oauth_service, mock_httpx_client, mock_google_oauth_response
    ):
        """Test successful code exchange for tokens."""
        # Setup mock response
        mock_httpx_client.set_response(
            "https://oauth2.googleapis.com/token", mock_google_oauth_response
        )

        with (
            patch("therobotoverlord_api.auth.google_oauth.Flow") as mock_flow_class,
            patch("therobotoverlord_api.auth.google_oauth.id_token") as mock_id_token,
        ):
            # Mock flow instance
            mock_flow = mock_flow_class.from_client_config.return_value
            mock_credentials = AsyncMock()
            mock_credentials.token = "mock_access_token"
            mock_credentials.id_token = "mock_id_token"
            mock_flow.credentials = mock_credentials

            # Mock ID token verification
            mock_id_token.verify_oauth2_token.return_value = {
                "sub": "123456789",
                "email": "test@example.com",
                "email_verified": True,
                "name": "Test User",
                "given_name": "Test",
                "family_name": "User",
            }

            user_info, access_token = await oauth_service.exchange_code_for_tokens(
                "test_code", "test_state"
            )

        assert isinstance(user_info, GoogleUserInfo)
        assert user_info.id == "123456789"
        assert user_info.email == "test@example.com"
        assert access_token == "mock_access_token"

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_failure(
        self, oauth_service, mock_httpx_client
    ):
        """Test failed code exchange."""
        # Setup mock error response
        mock_httpx_client.set_response(
            "https://oauth2.googleapis.com/token",
            {
                "error": "invalid_grant",
                "error_description": "Invalid authorization code",
            },
            status_code=400,
        )

        with patch(
            "therobotoverlord_api.auth.google_oauth.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            with pytest.raises(Exception, match="OAuth client was not found"):
                await oauth_service.exchange_code_for_tokens(
                    "invalid_code", "test_state"
                )

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, oauth_service, mock_httpx_client):
        """Test successful user info retrieval."""
        user_info_response = {
            "id": "123456789",
            "email": "test@example.com",
            "verified_email": True,
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/avatar.jpg",
            "locale": "en",
        }

        mock_httpx_client.set_response(
            "https://www.googleapis.com/oauth2/v2/userinfo", user_info_response
        )

        with patch(
            "therobotoverlord_api.auth.google_oauth.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            user_info = await oauth_service.get_user_info("mock_access_token")

        assert isinstance(user_info, GoogleUserInfo)
        assert user_info.id == "123456789"
        assert user_info.email == "test@example.com"
        assert user_info.verified_email is True
        assert user_info.name == "Test User"

    @pytest.mark.asyncio
    async def test_get_user_info_failure(self, oauth_service, mock_httpx_client):
        """Test failed user info retrieval."""
        mock_httpx_client.set_response(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            {"error": "invalid_token"},
            status_code=401,
        )

        with patch(
            "therobotoverlord_api.auth.google_oauth.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            with pytest.raises(Exception, match="HTTP 401"):
                await oauth_service.get_user_info("invalid_token")

    @pytest.mark.asyncio
    async def test_revoke_token_success(self, oauth_service, mock_httpx_client):
        """Test successful token revocation."""
        mock_httpx_client.set_response(
            "https://oauth2.googleapis.com/revoke", {}, status_code=200
        )

        with patch(
            "therobotoverlord_api.auth.google_oauth.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            result = await oauth_service.revoke_token("mock_access_token")

        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_token_failure(self, oauth_service, mock_httpx_client):
        """Test failed token revocation."""
        mock_httpx_client.set_response(
            "https://oauth2.googleapis.com/revoke",
            {"error": "invalid_token"},
            status_code=400,
        )

        with patch(
            "therobotoverlord_api.auth.google_oauth.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            result = await oauth_service.revoke_token("invalid_token")

        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_token_network_error(self, oauth_service):
        """Test token revocation with network error."""
        with patch(
            "therobotoverlord_api.auth.google_oauth.httpx.AsyncClient"
        ) as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = (
                Exception("Network error")
            )

            result = await oauth_service.revoke_token("mock_access_token")
            assert result is False

    def test_authorization_url_with_custom_state(self, oauth_service):
        """Test authorization URL with custom state parameter."""
        custom_state = "custom_csrf_token_12345"
        auth_url, returned_state = oauth_service.get_authorization_url(custom_state)

        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)

        assert query_params["state"][0] == custom_state

    def test_authorization_url_parameters(self, oauth_service):
        """Test all required parameters in authorization URL."""
        auth_url, returned_state = oauth_service.get_authorization_url("test_state")
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)

        # Required OAuth 2.0 parameters
        required_params = [
            "client_id",
            "redirect_uri",
            "response_type",
            "scope",
            "state",
        ]

        for param in required_params:
            assert param in query_params, f"Missing required parameter: {param}"

        # Google-specific parameters
        assert query_params["access_type"][0] == "offline"
        assert query_params["prompt"][0] == "consent"

    @pytest.mark.asyncio
    async def test_user_info_model_validation(self, oauth_service, mock_httpx_client):
        """Test user info model validation with various data."""
        # Test with minimal required fields
        minimal_response = {
            "id": "123456789",
            "email": "test@example.com",
            "verified_email": True,
        }

        mock_httpx_client.set_response(
            "https://www.googleapis.com/oauth2/v2/userinfo", minimal_response
        )

        with patch(
            "therobotoverlord_api.auth.google_oauth.httpx.AsyncClient",
            return_value=mock_httpx_client,
        ):
            user_info = await oauth_service.get_user_info("mock_access_token")

        assert user_info.id == "123456789"
        assert user_info.email == "test@example.com"
        assert user_info.verified_email is True
        # Optional fields should be None or empty string
        assert user_info.name in (None, "")
        assert user_info.given_name in (None, "")
        assert user_info.family_name in (None, "")

    @pytest.mark.asyncio
    async def test_concurrent_token_exchanges(
        self, oauth_service, mock_httpx_client, mock_google_oauth_response
    ):
        """Test concurrent token exchanges."""
        mock_httpx_client.set_response(
            "https://oauth2.googleapis.com/token", mock_google_oauth_response
        )

        async def exchange_token(code):
            with (
                patch("google_auth_oauthlib.flow.Flow.fetch_token"),
                patch(
                    "google_auth_oauthlib.flow.Flow.credentials",
                    new_callable=PropertyMock,
                ) as mock_credentials,
                patch(
                    "google.oauth2.id_token.verify_oauth2_token",
                    return_value={
                        "sub": f"user_{code}",
                        "email": f"user{code}@example.com",
                        "email_verified": True,
                        "name": f"User {code}",
                        "given_name": "User",
                        "family_name": str(code),
                    },
                ),
            ):
                mock_credentials.return_value.id_token = "mock_id_token"
                mock_credentials.return_value.token = {"access_token": "mock_token"}
                return await oauth_service.exchange_code_for_tokens(
                    f"code_{code}", f"state_{code}"
                )

        # Run multiple exchanges concurrently
        tasks = [exchange_token(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 5
        for i, result in enumerate(results):
            user_info, token = result
            assert user_info.id == f"user_{i}"
            assert user_info.email == f"user{i}@example.com"

    @pytest.mark.asyncio
    async def test_http_client_context_management(self, oauth_service):
        """Test that HTTP client is properly managed."""
        with (
            patch("google_auth_oauthlib.flow.Flow.fetch_token"),
            patch(
                "google_auth_oauthlib.flow.Flow.credentials", new_callable=PropertyMock
            ) as mock_credentials,
            patch(
                "google.oauth2.id_token.verify_oauth2_token",
                return_value={
                    "sub": "test_user",
                    "email": "test@example.com",
                    "email_verified": True,
                    "name": "Test User",
                    "given_name": "Test",
                    "family_name": "User",
                },
            ),
        ):
            mock_credentials.return_value.id_token = "mock_id_token"
            mock_credentials.return_value.token = {"access_token": "test"}

            result = await oauth_service.exchange_code_for_tokens(
                "test_code", "test_state"
            )

            # Verify successful exchange
            user_info, token = result
            assert user_info.id == "test_user"
            assert user_info.email == "test@example.com"
            assert token == {"access_token": "test"}

    def test_google_user_info_model(self, google_user_info):
        """Test GoogleUserInfo model functionality."""
        # Test serialization
        user_dict = google_user_info.model_dump()
        assert user_dict["id"] == "123456789"
        assert user_dict["email"] == "test@example.com"

        # Test deserialization
        new_user_info = GoogleUserInfo.model_validate(user_dict)
        assert new_user_info.id == google_user_info.id
        assert new_user_info.email == google_user_info.email

        # Test optional fields
        assert google_user_info.name == "Test User"
        assert google_user_info.picture == "https://example.com/avatar.jpg"
