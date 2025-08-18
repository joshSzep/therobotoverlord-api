"""Tests for database configuration module."""

import os

from unittest.mock import patch

from therobotoverlord_api.config.database import DatabaseSettings
from therobotoverlord_api.config.database import get_database_settings
from therobotoverlord_api.config.database import get_database_url
from therobotoverlord_api.config.database import get_migration_database_url


class TestDatabaseSettings:
    """Test DatabaseSettings configuration class."""

    def test_default_values(self):
        """Test default configuration values."""
        settings = DatabaseSettings()

        assert settings.database_url == ""
        assert settings.username == "postgres"
        assert settings.password == "password"
        assert settings.host == "localhost"
        assert settings.port == 5432
        assert settings.database == "therobotoverlord"
        assert settings.ssl_mode == "prefer"
        assert settings.min_pool_size == 5
        assert settings.max_pool_size == 20
        assert settings.pool_timeout == 30.0
        assert settings.query_timeout == 30.0
        assert settings.command_timeout == 60.0
        assert settings.migration_table == "_yoyo_migration"
        assert settings.ssl_require is False
        assert settings.ssl_cert_path is None
        assert settings.ssl_key_path is None
        assert settings.ssl_ca_path is None

    def test_custom_values(self):
        """Test custom configuration values."""
        settings = DatabaseSettings(
            username="custom_user",
            password="custom_pass",
            host="custom_host",
            port=5433,
            database="custom_db",
            ssl_mode="require",
            min_pool_size=2,
            max_pool_size=10,
            pool_timeout=15.0,
            query_timeout=20.0,
            command_timeout=40.0,
            ssl_require=True,
            ssl_cert_path="/path/to/cert",
            ssl_key_path="/path/to/key",
            ssl_ca_path="/path/to/ca",
        )

        assert settings.username == "custom_user"
        assert settings.password == "custom_pass"
        assert settings.host == "custom_host"
        assert settings.port == 5433
        assert settings.database == "custom_db"
        assert settings.ssl_mode == "require"
        assert settings.min_pool_size == 2
        assert settings.max_pool_size == 10
        assert settings.pool_timeout == 15.0
        assert settings.query_timeout == 20.0
        assert settings.command_timeout == 40.0
        assert settings.ssl_require is True
        assert settings.ssl_cert_path == "/path/to/cert"
        assert settings.ssl_key_path == "/path/to/key"
        assert settings.ssl_ca_path == "/path/to/ca"

    @patch.dict(
        os.environ,
        {
            "DATABASE_USERNAME": "env_user",
            "DATABASE_PASSWORD": "env_pass",
            "DATABASE_HOST": "env_host",
            "DATABASE_PORT": "5434",
            "DATABASE_DATABASE": "env_db",
        },
    )
    def test_environment_variables(self):
        """Test configuration from environment variables."""
        settings = DatabaseSettings()

        assert settings.username == "env_user"
        assert settings.password == "env_pass"
        assert settings.host == "env_host"
        assert settings.port == 5434
        assert settings.database == "env_db"


class TestGetDatabaseSettings:
    """Test get_database_settings function."""

    def test_returns_database_settings_instance(self):
        """Test that function returns DatabaseSettings instance."""
        settings = get_database_settings()
        assert isinstance(settings, DatabaseSettings)

    @patch.dict(os.environ, {"DATABASE_USERNAME": "test_user"})
    def test_uses_environment_variables(self):
        """Test that function uses environment variables."""
        settings = get_database_settings()
        assert settings.username == "test_user"


class TestGetDatabaseUrl:
    """Test get_database_url function."""

    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/db"})
    def test_uses_database_url_env_var(self):
        """Test that DATABASE_URL environment variable takes precedence."""
        url = get_database_url()
        assert url == "postgresql://user:pass@host:5432/db"

    @patch.dict(
        os.environ, {"POSTGRES_URL": "postgresql://user:pass@host:5432/db"}, clear=True
    )
    def test_uses_postgres_url_env_var(self):
        """Test that POSTGRES_URL environment variable is used."""
        url = get_database_url()
        assert url == "postgresql://user:pass@host:5432/db"

    @patch.dict(
        os.environ,
        {"POSTGRESQL_URL": "postgresql://user:pass@host:5432/db"},
        clear=True,
    )
    def test_uses_postgresql_url_env_var(self):
        """Test that POSTGRESQL_URL environment variable is used."""
        url = get_database_url()
        assert url == "postgresql://user:pass@host:5432/db"

    @patch.dict(os.environ, {}, clear=True)
    def test_builds_url_from_settings(self):
        """Test that URL is built from settings when no env vars are set."""
        url = get_database_url()
        expected = "postgresql://postgres:password@localhost:5432/therobotoverlord?sslmode=prefer"
        assert url == expected

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://env:env@env:5432/env",
            "POSTGRES_URL": "postgresql://postgres:postgres@postgres:5432/postgres",
        },
    )
    def test_database_url_precedence(self):
        """Test that DATABASE_URL takes precedence over other env vars."""
        url = get_database_url()
        assert url == "postgresql://env:env@env:5432/env"

    @patch.dict(
        os.environ,
        {
            "DATABASE_USERNAME": "custom_user",
            "DATABASE_PASSWORD": "custom_pass",
            "DATABASE_HOST": "custom_host",
            "DATABASE_PORT": "5433",
            "DATABASE_DATABASE": "custom_db",
            "DATABASE_SSL_MODE": "require",
        },
        clear=True,
    )
    def test_builds_url_with_custom_settings(self):
        """Test URL building with custom settings from env vars."""
        url = get_database_url()
        expected = "postgresql://custom_user:custom_pass@custom_host:5433/custom_db?sslmode=require"
        assert url == expected


class TestGetMigrationDatabaseUrl:
    """Test get_migration_database_url function."""

    @patch("therobotoverlord_api.config.database.get_database_url")
    def test_returns_postgresql_url_unchanged(self, mock_get_url):
        """Test that postgresql:// URLs are returned unchanged."""
        mock_get_url.return_value = "postgresql://user:pass@host:5432/db"
        url = get_migration_database_url()
        assert url == "postgresql://user:pass@host:5432/db"

    @patch("therobotoverlord_api.config.database.get_database_url")
    def test_converts_postgres_to_postgresql(self, mock_get_url):
        """Test that postgres:// URLs are converted to postgresql://."""
        mock_get_url.return_value = "postgres://user:pass@host:5432/db"
        url = get_migration_database_url()
        assert url == "postgresql://user:pass@host:5432/db"

    @patch("therobotoverlord_api.config.database.get_database_url")
    def test_only_converts_first_occurrence(self, mock_get_url):
        """Test that only the first postgres:// is converted."""
        mock_get_url.return_value = "postgres://user:postgres://pass@host:5432/db"
        url = get_migration_database_url()
        assert url == "postgresql://user:postgres://pass@host:5432/db"
