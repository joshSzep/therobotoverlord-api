"""Database health check utilities for The Robot Overlord API."""

import logging

from typing import Any

from therobotoverlord_api.database.connection import get_db_connection

logger = logging.getLogger(__name__)


class DatabaseHealthChecker:
    """Database health check and validation utilities."""

    async def check_connection(self) -> dict[str, Any]:
        """Check basic database connectivity."""
        try:
            async with get_db_connection() as connection:
                result = await connection.fetchval("SELECT 1")
                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                    "test_query_result": result,
                }
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {e!s}",
                "error": str(e),
            }

    async def check_extensions(self) -> dict[str, Any]:
        """Check if required PostgreSQL extensions are installed."""
        required_extensions = ["pgcrypto", "citext", "vector"]

        try:
            async with get_db_connection() as connection:
                query = """
                    SELECT extname
                    FROM pg_extension
                    WHERE extname = ANY($1)
                """
                installed = await connection.fetch(query, required_extensions)
                installed_names = [record["extname"] for record in installed]

                missing = [
                    ext for ext in required_extensions if ext not in installed_names
                ]

                return {
                    "status": "healthy" if not missing else "unhealthy",
                    "required_extensions": required_extensions,
                    "installed_extensions": installed_names,
                    "missing_extensions": missing,
                    "message": "All extensions installed"
                    if not missing
                    else f"Missing extensions: {missing}",
                }
        except Exception as e:
            logger.error(f"Extension check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Extension check failed: {e!s}",
                "error": str(e),
            }

    async def check_tables(self) -> dict[str, Any]:
        """Check if all required tables exist."""
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

        try:
            async with get_db_connection() as connection:
                query = """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = ANY($1)
                """
                existing = await connection.fetch(query, required_tables)
                existing_names = [record["table_name"] for record in existing]

                missing = [
                    table for table in required_tables if table not in existing_names
                ]

                return {
                    "status": "healthy" if not missing else "unhealthy",
                    "required_tables": required_tables,
                    "existing_tables": existing_names,
                    "missing_tables": missing,
                    "message": "All tables exist"
                    if not missing
                    else f"Missing tables: {missing}",
                }
        except Exception as e:
            logger.error(f"Table check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Table check failed: {e!s}",
                "error": str(e),
            }

    async def check_materialized_views(self) -> dict[str, Any]:
        """Check if materialized views exist and are populated."""
        required_views = ["user_leaderboard"]

        try:
            async with get_db_connection() as connection:
                # Check if views exist
                query = """
                    SELECT schemaname, matviewname
                    FROM pg_matviews
                    WHERE matviewname = ANY($1)
                """
                existing = await connection.fetch(query, required_views)
                existing_names = [record["matviewname"] for record in existing]

                missing = [
                    view for view in required_views if view not in existing_names
                ]

                # Check if views have data
                view_stats = {}
                for view_name in existing_names:
                    count_query = f"SELECT COUNT(*) FROM {view_name}"
                    count = await connection.fetchval(count_query)
                    view_stats[view_name] = count

                return {
                    "status": "healthy" if not missing else "unhealthy",
                    "required_views": required_views,
                    "existing_views": existing_names,
                    "missing_views": missing,
                    "view_row_counts": view_stats,
                    "message": "All materialized views exist"
                    if not missing
                    else f"Missing views: {missing}",
                }
        except Exception as e:
            logger.error(f"Materialized view check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Materialized view check failed: {e!s}",
                "error": str(e),
            }

    async def check_indexes(self) -> dict[str, Any]:
        """Check if critical indexes exist."""
        critical_indexes = [
            "idx_posts_topic_submission_order",
            "idx_topic_queue_priority_score",
            "idx_post_queue_topic_priority",
            "idx_message_queue_conv_priority",
            "idx_users_loyalty_score_desc",
            "idx_leaderboard_user_id",
        ]

        try:
            async with get_db_connection() as connection:
                query = """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND indexname = ANY($1)
                """
                existing = await connection.fetch(query, critical_indexes)
                existing_names = [record["indexname"] for record in existing]

                missing = [idx for idx in critical_indexes if idx not in existing_names]

                return {
                    "status": "healthy" if not missing else "warning",
                    "critical_indexes": critical_indexes,
                    "existing_indexes": existing_names,
                    "missing_indexes": missing,
                    "message": "All critical indexes exist"
                    if not missing
                    else f"Missing indexes: {missing}",
                }
        except Exception as e:
            logger.error(f"Index check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Index check failed: {e!s}",
                "error": str(e),
            }

    async def get_database_stats(self) -> dict[str, Any]:
        """Get general database statistics."""
        try:
            async with get_db_connection() as connection:
                # Get table sizes
                size_query = """
                    SELECT
                        schemaname,
                        tablename,
                        pg_size_pretty(
                            pg_total_relation_size(schemaname||'.'||tablename)
                        ) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """
                table_sizes = await connection.fetch(size_query)

                # Get row counts for main tables
                main_tables = ["users", "topics", "posts", "private_messages"]
                row_counts = {}
                for table in main_tables:
                    try:
                        count = await connection.fetchval(
                            f"SELECT COUNT(*) FROM {table}"
                        )
                        row_counts[table] = count
                    except Exception:
                        row_counts[table] = "error"

                # Get database version
                version = await connection.fetchval("SELECT version()")

                return {
                    "status": "healthy",
                    "database_version": version,
                    "table_sizes": [dict(record) for record in table_sizes],
                    "row_counts": row_counts,
                }
        except Exception as e:
            logger.error(f"Database stats check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Database stats check failed: {e!s}",
                "error": str(e),
            }

    async def full_health_check(self) -> dict[str, Any]:
        """Perform a comprehensive health check."""
        checks = {
            "connection": await self.check_connection(),
            "extensions": await self.check_extensions(),
            "tables": await self.check_tables(),
            "materialized_views": await self.check_materialized_views(),
            "indexes": await self.check_indexes(),
            "stats": await self.get_database_stats(),
        }

        # Determine overall status
        statuses = [check["status"] for check in checks.values()]
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return {
            "overall_status": overall_status,
            "timestamp": "NOW()",
            "checks": checks,
        }


# Global health checker instance
health_checker = DatabaseHealthChecker()
