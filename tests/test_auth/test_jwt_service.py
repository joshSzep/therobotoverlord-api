"""Tests for JWT service."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from therobotoverlord_api.auth.jwt_service import JWTService
from therobotoverlord_api.auth.models import TokenClaims
from therobotoverlord_api.database.models.base import UserRole


class TestJWTService:
    """Test JWT service functionality."""

    def test_generate_session_id(self, jwt_service):
        """Test session ID generation."""
        session_id = jwt_service.generate_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) == 43  # URL-safe base64 encoded 32 bytes

        # Ensure uniqueness
        session_id2 = jwt_service.generate_session_id()
        assert session_id != session_id2

    def test_create_token_pair(self, jwt_service):
        """Test token pair creation."""
        user_id = uuid4()
        role = UserRole.CITIZEN
        permissions = ["view_content", "create_posts"]

        token_pair = jwt_service.create_token_pair(
            user_id=user_id,
            role=role,
            permissions=permissions,
        )

        assert token_pair.access_token.token
        assert token_pair.refresh_token.token
        assert token_pair.access_token.expires_at > datetime.now(UTC)
        assert token_pair.refresh_token.expires_at > token_pair.access_token.expires_at

        # Verify token claims
        access_claims = jwt_service.decode_token(token_pair.access_token.token)
        assert access_claims.sub == user_id
        assert access_claims.role == role
        assert access_claims.permissions == permissions
        assert access_claims.sid == token_pair.refresh_token.session_id

    def test_create_token_pair_with_session_id(self, jwt_service):
        """Test token pair creation with specific session ID."""
        user_id = uuid4()
        role = UserRole.CITIZEN
        session_id = "custom_session_id"

        token_pair = jwt_service.create_token_pair(
            user_id=user_id,
            role=role,
            session_id=session_id,
        )

        access_claims = jwt_service.decode_token(token_pair.access_token.token)
        assert access_claims.sid == session_id

    def test_decode_valid_token(
        self, jwt_service, valid_access_token, test_token_claims
    ):
        """Test decoding valid token."""
        claims = jwt_service.decode_token(valid_access_token)

        assert claims.sub == test_token_claims.sub
        assert claims.role == test_token_claims.role
        assert claims.permissions == test_token_claims.permissions
        assert claims.sid == test_token_claims.sid

    def test_decode_expired_token(self, jwt_service, expired_access_token):
        """Test decoding expired token."""
        claims = jwt_service.decode_token(expired_access_token)
        assert claims is None

    def test_decode_invalid_token(self, jwt_service):
        """Test decoding invalid token."""
        claims = jwt_service.decode_token("invalid.token.here")
        assert claims is None

    def test_decode_token_wrong_issuer(self, jwt_service, auth_settings):
        """Test decoding token with wrong issuer."""
        # Create token with different issuer
        with patch(
            "therobotoverlord_api.auth.jwt_service.get_auth_settings",
            return_value=auth_settings.model_copy(
                update={"jwt_issuer": "wrong-issuer"}
            ),
        ):
            wrong_issuer_service = JWTService()
        user_id = uuid4()
        token_pair = wrong_issuer_service.create_token_pair(
            user_id=user_id,
            role=UserRole.CITIZEN,
        )

        # Token from wrong issuer should return None
        claims = jwt_service.decode_token(token_pair.access_token.token)
        assert claims is None

    def test_extend_token_valid(self, jwt_service, test_token_claims):
        """Test extending valid token."""
        # Create token that can be extended
        user_id = test_token_claims.sub
        token_pair = jwt_service.create_token_pair(
            user_id=user_id,
            role=test_token_claims.role,
            permissions=test_token_claims.permissions,
        )

        # Test extend_access_token method
        # Use a much later max_expires_at to ensure extension happens
        max_expires_at = datetime.now(UTC) + timedelta(hours=24)
        original_expires_at = token_pair.access_token.expires_at
        extended_token = jwt_service.extend_access_token(
            token_pair.access_token.token, max_expires_at
        )
        assert extended_token is not None
        # Extended token should have later or equal expiration time
        # Allow for small timing differences by checking seconds difference
        time_diff = (extended_token.expires_at - original_expires_at).total_seconds()
        assert time_diff >= 0, (
            f"Extended token expires {time_diff} seconds before original"
        )

    def test_extend_token_not_needed(self, jwt_service, valid_access_token):
        """Test extending token that doesn't need extension."""
        # If max_expires_at is in the past, extension should fail
        max_expires_at = datetime.now(UTC) - timedelta(hours=1)
        extended_token = jwt_service.extend_access_token(
            valid_access_token, max_expires_at
        )
        assert extended_token is None

    def test_extend_token_past_max_lifetime(self, jwt_service, test_token_claims):
        """Test extending token past max lifetime."""
        # Create a token
        user_id = test_token_claims.sub
        token_pair = jwt_service.create_token_pair(
            user_id=user_id,
            role=test_token_claims.role,
        )

        # Try to extend past max lifetime (set max_expires_at in the past)
        max_expires_at = datetime.now(UTC) - timedelta(hours=1)
        extended_token = jwt_service.extend_access_token(
            token_pair.access_token.token, max_expires_at
        )
        assert extended_token is None

    def test_extend_expired_token(self, jwt_service, expired_access_token):
        """Test extending expired token."""
        max_expires_at = datetime.now(UTC) + timedelta(hours=8)
        extended_token = jwt_service.extend_access_token(
            expired_access_token, max_expires_at
        )
        assert extended_token is None

    def test_validate_token_valid(self, jwt_service, valid_access_token):
        """Test validating valid token."""
        claims = jwt_service.decode_token(valid_access_token)
        assert claims is not None
        assert isinstance(claims, TokenClaims)

    def test_validate_token_expired(self, jwt_service, expired_access_token):
        """Test validating expired token."""
        claims = jwt_service.decode_token(expired_access_token)
        assert claims is None

    def test_validate_token_invalid(self, jwt_service):
        """Test validating invalid token."""
        claims = jwt_service.decode_token("invalid.token")
        assert claims is None

    def test_create_jwks_response(self, jwt_service):
        """Test JWKS response creation."""
        jwks = jwt_service.create_jwks_response()

        assert "keys" in jwks
        assert len(jwks["keys"]) == 1

        key = jwks["keys"][0]
        assert key["kty"] == "oct"
        assert key["use"] == "sig"
        assert key["alg"] == "HS256"
        assert key["kid"] == "default"
        # Note: 'k' key is not exposed for HS256 symmetric keys

    def test_token_claims_serialization(self, test_token_claims):
        """Test token claims can be serialized/deserialized."""
        # Test model dump
        claims_dict = test_token_claims.model_dump()
        assert "sub" in claims_dict
        assert "role" in claims_dict
        assert "permissions" in claims_dict

        # Test model validation
        new_claims = TokenClaims.model_validate(claims_dict)
        assert new_claims.sub == test_token_claims.sub
        assert new_claims.role == test_token_claims.role

    def test_different_token_types(self, jwt_service, test_token_claims):
        """Test creating different token types."""
        user_id = test_token_claims.sub
        token_pair = jwt_service.create_token_pair(
            user_id=user_id,
            role=test_token_claims.role,
            permissions=test_token_claims.permissions,
        )

        assert token_pair.access_token.token != token_pair.refresh_token.token

        # Access token should decode to TokenClaims
        access_claims = jwt_service.decode_token(token_pair.access_token.token)
        assert access_claims is not None
        assert access_claims.sub == user_id
        assert access_claims.role == test_token_claims.role

    def test_permissions_handling(self, jwt_service):
        """Test permissions handling in tokens."""
        user_id = uuid4()

        # Test with no permissions
        token_pair = jwt_service.create_token_pair(
            user_id=user_id,
            role=UserRole.CITIZEN,
        )
        claims = jwt_service.decode_token(token_pair.access_token.token)
        assert claims.permissions == []

        # Test with permissions
        permissions = ["view_content", "create_posts", "moderate_content"]
        token_pair = jwt_service.create_token_pair(
            user_id=user_id,
            role=UserRole.MODERATOR,
            permissions=permissions,
        )
        claims = jwt_service.decode_token(token_pair.access_token.token)
        assert claims.permissions == permissions

    def test_token_version_handling(self, jwt_service):
        """Test token version in claims."""
        user_id = uuid4()
        token_pair = jwt_service.create_token_pair(
            user_id=user_id,
            role=UserRole.CITIZEN,
        )

        claims = jwt_service.decode_token(token_pair.access_token.token)
        assert claims.authz_ver == 1  # Default version

    def test_concurrent_session_ids(self, jwt_service):
        """Test that concurrent token creation generates unique session IDs."""
        user_id = uuid4()

        token_pairs = []
        for _ in range(10):
            token_pair = jwt_service.create_token_pair(
                user_id=user_id,
                role=UserRole.CITIZEN,
            )
            token_pairs.append(token_pair)
            # Ensure all session IDs are unique
        session_ids = [
            token_pair.refresh_token.session_id for token_pair in token_pairs
        ]
        assert len(set(session_ids)) == len(session_ids)
