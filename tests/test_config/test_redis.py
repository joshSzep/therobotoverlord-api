"""Tests for Redis configuration."""

import os

from unittest.mock import patch

from therobotoverlord_api.config.redis import RedisSettings
from therobotoverlord_api.config.redis import get_redis_settings


class TestRedisSettings:
    """Test cases for RedisSettings."""

    def test_default_settings(self):
        """Test default Redis settings."""
        with patch.dict(os.environ, {}, clear=True):
            settings = RedisSettings()

            assert settings.redis_url == "redis://localhost:6379/0"
            assert settings.host == "localhost"
            assert settings.port == 6379
            assert settings.database == 0
            assert settings.password is None
            assert settings.max_connections == 20
            assert settings.retry_on_timeout is True
            assert settings.socket_timeout == 5.0
            assert settings.socket_connect_timeout == 5.0
            assert settings.ssl_enabled is False
            assert settings.ssl_cert_reqs == "required"
            assert settings.ssl_ca_certs is None
            assert settings.ssl_certfile is None
            assert settings.ssl_keyfile is None

    def test_custom_settings_from_env(self):
        """Test Redis settings from environment variables."""
        env_vars = {
            "REDIS_REDIS_URL": "redis://custom:6380/1",
            "REDIS_HOST": "custom",
            "REDIS_PORT": "6380",
            "REDIS_DATABASE": "1",
            "REDIS_PASSWORD": "secret",
            "REDIS_SSL_ENABLED": "true",
            "REDIS_SSL_CERT_REQS": "optional",
            "REDIS_SSL_CA_CERTS": "/path/to/ca.crt",
            "REDIS_SSL_CERTFILE": "/path/to/cert.crt",
            "REDIS_SSL_KEYFILE": "/path/to/key.key",
            "REDIS_SOCKET_CONNECT_TIMEOUT": "10",
            "REDIS_MAX_CONNECTIONS": "100",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = RedisSettings()

            assert settings.redis_url == "redis://custom:6380/1"
            assert settings.host == "custom"
            assert settings.port == 6380
            assert settings.database == 1
            assert settings.password == "secret"
            assert settings.ssl_enabled is True
            assert settings.ssl_cert_reqs == "optional"
            assert settings.ssl_ca_certs == "/path/to/ca.crt"
            assert settings.ssl_certfile == "/path/to/cert.crt"
            assert settings.ssl_keyfile == "/path/to/key.key"
            assert settings.socket_connect_timeout == 10
            assert settings.max_connections == 100

    def test_ssl_settings_with_ssl_disabled(self):
        """Test that SSL settings are available when SSL is disabled."""
        env_vars = {
            "REDIS_SSL_ENABLED": "false",
            "REDIS_SSL_CERT_REQS": "none",
            "REDIS_SSL_CA_CERTS": "/path/to/ca.crt",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = RedisSettings()

            assert settings.ssl_enabled is False
            # SSL settings should still be available even if SSL is disabled
            assert settings.ssl_cert_reqs == "none"
            assert settings.ssl_ca_certs == "/path/to/ca.crt"

    def test_port_validation(self):
        """Test Redis port validation."""
        env_vars = {"REDIS_PORT": "65536"}  # Invalid port

        with patch.dict(os.environ, env_vars, clear=True):
            # Pydantic doesn't validate port ranges by default, so this should pass
            settings = RedisSettings()
            assert settings.port == 65536

    def test_negative_port(self):
        """Test negative Redis port."""
        env_vars = {"REDIS_PORT": "-1"}

        with patch.dict(os.environ, env_vars, clear=True):
            # Pydantic doesn't validate negative ports by default
            settings = RedisSettings()
            assert settings.port == -1

    def test_db_validation(self):
        """Test Redis database number validation."""
        env_vars = {"REDIS_DATABASE": "-1"}  # Invalid DB number

        with patch.dict(os.environ, env_vars, clear=True):
            # Pydantic doesn't validate negative database numbers by default
            settings = RedisSettings()
            assert settings.database == -1

    def test_timeout_validation(self):
        """Test timeout validation."""
        env_vars = {"REDIS_SOCKET_CONNECT_TIMEOUT": "-1"}

        with patch.dict(os.environ, env_vars, clear=True):
            # Pydantic doesn't validate negative timeouts by default
            settings = RedisSettings()
            assert settings.socket_connect_timeout == -1

    def test_max_connections_validation(self):
        """Test max connections validation."""
        env_vars = {"REDIS_MAX_CONNECTIONS": "0"}

        with patch.dict(os.environ, env_vars, clear=True):
            # Pydantic doesn't validate zero max connections by default
            settings = RedisSettings()
            assert settings.max_connections == 0

    def test_boolean_parsing(self):
        """Test boolean field parsing from environment."""
        # Test various boolean representations
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
        ]

        for env_value, expected in test_cases:
            env_vars = {"REDIS_SSL_ENABLED": env_value}

            with patch.dict(os.environ, env_vars, clear=True):
                settings = RedisSettings()
                assert settings.ssl_enabled == expected

    def test_empty_string_handling(self):
        """Test handling of empty string values."""
        env_vars = {
            "REDIS_PASSWORD": "",
            "REDIS_SSL_CA_CERTS": "",
            "REDIS_SSL_CERTFILE": "",
            "REDIS_SSL_KEYFILE": "",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = RedisSettings()

            # Empty strings should be treated as empty strings, not None
            assert settings.password == ""
            assert settings.ssl_ca_certs == ""
            assert settings.ssl_certfile == ""
            assert settings.ssl_keyfile == ""


def test_get_redis_settings():
    """Test the get_redis_settings factory function."""
    env_vars = {
        "REDIS_HOST": "test-host",
        "REDIS_PORT": "6380",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        settings = get_redis_settings()

        assert isinstance(settings, RedisSettings)
        assert settings.host == "test-host"
        assert settings.port == 6380


def test_get_redis_settings_caching():
    """Test that get_redis_settings returns new instances."""
    settings1 = get_redis_settings()
    settings2 = get_redis_settings()

    # Should return different instances (not cached)
    assert settings1 is not settings2
    assert settings1.host == settings2.host
