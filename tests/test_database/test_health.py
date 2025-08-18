"""Tests for database health check utilities."""

from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from therobotoverlord_api.database.health import DatabaseHealthChecker
from therobotoverlord_api.database.health import health_checker


class TestDatabaseHealthChecker:
    """Test DatabaseHealthChecker class."""

    @pytest.fixture
    def health_checker_instance(self):
        """Create a DatabaseHealthChecker instance for testing."""
        return DatabaseHealthChecker()

    @pytest.mark.asyncio
    async def test_check_connection_success(self, health_checker_instance):
        """Test successful connection check."""
        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchval.return_value = 1
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.check_connection()

            assert result["status"] == "healthy"
            assert result["message"] == "Database connection successful"
            assert result["test_query_result"] == 1
            mock_connection.fetchval.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, health_checker_instance):
        """Test connection check failure."""
        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchval.side_effect = Exception("Connection failed")
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.check_connection()

            assert result["status"] == "unhealthy"
            assert "Database connection failed" in result["message"]
            assert "error" in result

    @pytest.mark.asyncio
    async def test_check_extensions_all_installed(self, health_checker_instance):
        """Test extensions check when all required extensions are installed."""
        mock_records = [
            {"extname": "pgcrypto"},
            {"extname": "citext"},
            {"extname": "vector"},
        ]

        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = mock_records
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.check_extensions()

            assert result["status"] == "healthy"
            assert result["message"] == "All extensions installed"
            assert result["missing_extensions"] == []
            assert set(result["installed_extensions"]) == {
                "pgcrypto",
                "citext",
                "vector",
            }

    @pytest.mark.asyncio
    async def test_check_extensions_missing(self, health_checker_instance):
        """Test extensions check when some extensions are missing."""
        mock_records = [
            {"extname": "pgcrypto"},
        ]

        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = mock_records
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.check_extensions()

            assert result["status"] == "unhealthy"
            assert "Missing extensions" in result["message"]
            assert set(result["missing_extensions"]) == {"citext", "vector"}
            assert result["installed_extensions"] == ["pgcrypto"]

    @pytest.mark.asyncio
    async def test_check_extensions_failure(self, health_checker_instance):
        """Test extensions check failure."""
        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.side_effect = Exception("Query failed")
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.check_extensions()

            assert result["status"] == "unhealthy"
            assert "Extension check failed" in result["message"]

    @pytest.mark.asyncio
    async def test_check_tables_all_exist(self, health_checker_instance):
        """Test tables check when all required tables exist."""
        required_tables = [
            "users",
            "topics",
            "posts",
            "tags",
            "topic_tags",
            "topic_creation_queue",
            "post_moderation_queue",
            "private_message_queue",
            "private_messages",
            "appeals",
            "flags",
            "sanctions",
            "badges",
            "user_badges",
            "moderation_events",
            "translations",
        ]

        mock_records = [{"table_name": table} for table in required_tables]

        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = mock_records
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.check_tables()

            assert result["status"] == "healthy"
            assert result["message"] == "All tables exist"
            assert result["missing_tables"] == []
            assert len(result["existing_tables"]) == len(required_tables)

    @pytest.mark.asyncio
    async def test_check_tables_missing(self, health_checker_instance):
        """Test tables check when some tables are missing."""
        mock_records = [
            {"table_name": "users"},
            {"table_name": "topics"},
        ]

        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = mock_records
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.check_tables()

            assert result["status"] == "unhealthy"
            assert "Missing tables" in result["message"]
            assert "posts" in result["missing_tables"]
            assert len(result["existing_tables"]) == 2

    @pytest.mark.asyncio
    async def test_check_materialized_views_exist_with_data(
        self, health_checker_instance
    ):
        """Test materialized views check when views exist and have data."""
        mock_records = [{"matviewname": "user_leaderboard"}]

        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = mock_records
            mock_connection.fetchval.return_value = 100  # Row count
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.check_materialized_views()

            assert result["status"] == "healthy"
            assert result["message"] == "All materialized views exist"
            assert result["missing_views"] == []
            assert result["view_row_counts"]["user_leaderboard"] == 100

    @pytest.mark.asyncio
    async def test_check_materialized_views_missing(self, health_checker_instance):
        """Test materialized views check when views are missing."""
        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = []  # No views found
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.check_materialized_views()

            assert result["status"] == "unhealthy"
            assert "Missing views" in result["message"]
            assert "user_leaderboard" in result["missing_views"]

    @pytest.mark.asyncio
    async def test_check_indexes_all_exist(self, health_checker_instance):
        """Test indexes check when all critical indexes exist."""
        critical_indexes = [
            "idx_posts_topic_submission_order",
            "idx_topic_queue_priority_score",
            "idx_post_queue_topic_priority",
            "idx_message_queue_conv_priority",
            "idx_users_loyalty_score_desc",
            "idx_leaderboard_user_id",
        ]

        mock_records = [{"indexname": idx} for idx in critical_indexes]

        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = mock_records
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.check_indexes()

            assert result["status"] == "healthy"
            assert result["message"] == "All critical indexes exist"
            assert result["missing_indexes"] == []

    @pytest.mark.asyncio
    async def test_check_indexes_missing(self, health_checker_instance):
        """Test indexes check when some indexes are missing."""
        mock_records = [
            {"indexname": "idx_posts_topic_submission_order"},
        ]

        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = mock_records
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.check_indexes()

            assert result["status"] == "warning"
            assert "Missing indexes" in result["message"]
            assert len(result["missing_indexes"]) > 0

    @pytest.mark.asyncio
    async def test_get_database_stats_success(self, health_checker_instance):
        """Test getting database statistics successfully."""
        mock_table_sizes = [
            {
                "schemaname": "public",
                "tablename": "users",
                "size": "1024 kB",
                "size_bytes": 1048576,
            },
            {
                "schemaname": "public",
                "tablename": "topics",
                "size": "512 kB",
                "size_bytes": 524288,
            },
        ]

        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = mock_table_sizes
            mock_connection.fetchval.side_effect = [100, 50, 25, 10, "PostgreSQL 15.0"]
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.get_database_stats()

            assert result["status"] == "healthy"
            assert "PostgreSQL 15.0" in result["database_version"]
            assert len(result["table_sizes"]) == 2
            assert result["row_counts"]["users"] == 100
            assert result["row_counts"]["topics"] == 50

    @pytest.mark.asyncio
    async def test_get_database_stats_with_errors(self, health_checker_instance):
        """Test database stats when some table queries fail."""
        mock_table_sizes = []

        with patch(
            "therobotoverlord_api.database.health.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = mock_table_sizes
            # First call succeeds, others fail
            mock_connection.fetchval.side_effect = [
                100,  # users count
                Exception("Table not found"),  # topics fails
                Exception("Table not found"),  # posts fails
                Exception("Table not found"),  # private_messages fails
                "PostgreSQL 15.0",  # version
            ]
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await health_checker_instance.get_database_stats()

            assert result["status"] == "healthy"
            assert result["row_counts"]["users"] == 100
            assert result["row_counts"]["topics"] == "error"

    @pytest.mark.asyncio
    async def test_full_health_check_all_healthy(self, health_checker_instance):
        """Test full health check when all checks pass."""
        healthy_result = {"status": "healthy", "message": "OK"}

        with (
            patch.object(
                health_checker_instance, "check_connection", return_value=healthy_result
            ),
            patch.object(
                health_checker_instance, "check_extensions", return_value=healthy_result
            ),
            patch.object(
                health_checker_instance, "check_tables", return_value=healthy_result
            ),
            patch.object(
                health_checker_instance,
                "check_materialized_views",
                return_value=healthy_result,
            ),
            patch.object(
                health_checker_instance, "check_indexes", return_value=healthy_result
            ),
            patch.object(
                health_checker_instance,
                "get_database_stats",
                return_value=healthy_result,
            ),
        ):
            result = await health_checker_instance.full_health_check()

            assert result["overall_status"] == "healthy"
            assert "checks" in result
            assert len(result["checks"]) == 6

    @pytest.mark.asyncio
    async def test_full_health_check_with_warnings(self, health_checker_instance):
        """Test full health check with warning status."""
        healthy_result = {"status": "healthy", "message": "OK"}
        warning_result = {"status": "warning", "message": "Some issues"}

        with (
            patch.object(
                health_checker_instance, "check_connection", return_value=healthy_result
            ),
            patch.object(
                health_checker_instance, "check_extensions", return_value=healthy_result
            ),
            patch.object(
                health_checker_instance, "check_tables", return_value=healthy_result
            ),
            patch.object(
                health_checker_instance,
                "check_materialized_views",
                return_value=healthy_result,
            ),
            patch.object(
                health_checker_instance, "check_indexes", return_value=warning_result
            ),
            patch.object(
                health_checker_instance,
                "get_database_stats",
                return_value=healthy_result,
            ),
        ):
            result = await health_checker_instance.full_health_check()

            assert result["overall_status"] == "warning"

    @pytest.mark.asyncio
    async def test_full_health_check_with_unhealthy(self, health_checker_instance):
        """Test full health check with unhealthy status."""
        healthy_result = {"status": "healthy", "message": "OK"}
        unhealthy_result = {"status": "unhealthy", "message": "Failed"}

        with (
            patch.object(
                health_checker_instance,
                "check_connection",
                return_value=unhealthy_result,
            ),
            patch.object(
                health_checker_instance, "check_extensions", return_value=healthy_result
            ),
            patch.object(
                health_checker_instance, "check_tables", return_value=healthy_result
            ),
            patch.object(
                health_checker_instance,
                "check_materialized_views",
                return_value=healthy_result,
            ),
            patch.object(
                health_checker_instance, "check_indexes", return_value=healthy_result
            ),
            patch.object(
                health_checker_instance,
                "get_database_stats",
                return_value=healthy_result,
            ),
        ):
            result = await health_checker_instance.full_health_check()

            assert result["overall_status"] == "unhealthy"


class TestGlobalHealthChecker:
    """Test global health checker instance."""

    def test_global_instance_exists(self):
        """Test that global health checker instance exists."""
        assert health_checker is not None
        assert isinstance(health_checker, DatabaseHealthChecker)
