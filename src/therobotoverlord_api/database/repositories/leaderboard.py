"""Leaderboard repository for The Robot Overlord API."""

from datetime import date
from datetime import timedelta
from uuid import UUID

import asyncpg

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.leaderboard import BadgeSummary
from therobotoverlord_api.database.models.leaderboard import LeaderboardCursor
from therobotoverlord_api.database.models.leaderboard import LeaderboardEntry
from therobotoverlord_api.database.models.leaderboard import LeaderboardFilters
from therobotoverlord_api.database.models.leaderboard import LeaderboardSearchResult
from therobotoverlord_api.database.models.leaderboard import LeaderboardStats
from therobotoverlord_api.database.models.leaderboard import RankHistoryEntry
from therobotoverlord_api.database.models.leaderboard import UserRankLookup
from therobotoverlord_api.database.repositories.base import BaseRepository


class LeaderboardRepository(BaseRepository):
    """Repository for leaderboard queries and operations."""

    def __init__(self):
        super().__init__("leaderboard_rankings")

    def _record_to_model(self, record):
        """Convert database record to model instance (not used in this repository)."""
        # This method is required by BaseRepository but not used in LeaderboardRepository
        # since we have custom query methods that handle model conversion directly
        raise NotImplementedError("Use specific query methods instead")

    async def get_leaderboard_page(
        self,
        limit: int = 50,
        cursor: LeaderboardCursor | None = None,
        filters: LeaderboardFilters | None = None,
        current_user_pk: UUID | None = None,
    ) -> tuple[list[LeaderboardEntry], bool]:
        """Get a page of leaderboard entries with cursor-based pagination."""
        filters = filters or LeaderboardFilters()

        # Build the base query
        query_parts = [
            """
            SELECT
                lr.user_pk,
                lr.username,
                lr.loyalty_score,
                lr.rank,
                lr.percentile_rank,
                lr.topics_created_count,
                lr.topic_creation_enabled,
                lr.user_created_at,
                CASE WHEN lr.user_pk = $1 THEN true ELSE false END as is_current_user
            FROM leaderboard_rankings lr
            """
        ]

        where_conditions = []
        query_params: list[object] = [current_user_pk]
        param_count = 1

        # Apply filters
        if filters.active_users_only:
            # This is already handled by the materialized view (excludes banned users)
            pass

        if filters.badge_name:
            query_parts.insert(
                -1,
                """
                JOIN user_badges ub ON lr.user_pk = ub.user_pk
                JOIN badges b ON ub.badge_pk = b.pk
            """,
            )
            param_count += 1
            where_conditions.append(f"b.name = ${param_count}")
            query_params.append(filters.badge_name)

        if filters.min_loyalty_score is not None:
            param_count += 1
            where_conditions.append(f"lr.loyalty_score >= ${param_count}")
            query_params.append(filters.min_loyalty_score)

        if filters.max_loyalty_score is not None:
            param_count += 1
            where_conditions.append(f"lr.loyalty_score <= ${param_count}")
            query_params.append(filters.max_loyalty_score)

        if filters.min_rank is not None:
            param_count += 1
            where_conditions.append(f"lr.rank >= ${param_count}")
            query_params.append(filters.min_rank)

        if filters.max_rank is not None:
            param_count += 1
            where_conditions.append(f"lr.rank <= ${param_count}")
            query_params.append(filters.max_rank)

        if filters.username_search:
            param_count += 1
            where_conditions.append(f"lr.username ILIKE ${param_count}")
            query_params.append(f"%{filters.username_search}%")

        if filters.topic_creators_only:
            where_conditions.append("lr.topics_created_count > 0")

        # Cursor-based pagination
        if cursor:
            param_count += 1
            where_conditions.append(f"""
                (lr.rank > ${param_count} OR
                 (lr.rank = ${param_count} AND lr.user_pk > ${param_count + 1}))
            """)
            query_params.extend([cursor.rank, cursor.user_pk])
            param_count += 1

        # Add WHERE clause if we have conditions
        if where_conditions:
            query_parts.append("WHERE " + " AND ".join(where_conditions))

        # Add ordering and limit
        query_parts.extend(
            ["ORDER BY lr.rank ASC, lr.user_pk ASC", f"LIMIT ${param_count + 1}"]
        )
        query_params.append(limit + 1)  # Get one extra to check if there's a next page

        query = " ".join(query_parts)

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, *query_params)

            # Check if there are more results
            has_next = len(rows) > limit
            if has_next:
                rows = rows[:-1]  # Remove the extra row

            # Convert to LeaderboardEntry objects
            entries = []
            for row in rows:
                # Get badges for this user
                badges = await self._get_user_badges(conn, row["user_pk"])

                entry = LeaderboardEntry(
                    user_pk=row["user_pk"],
                    username=row["username"],
                    loyalty_score=row["loyalty_score"],
                    rank=row["rank"],
                    percentile_rank=max(0.0, min(1.0, float(row["percentile_rank"]))),
                    badges=badges,
                    topic_creation_enabled=row["topic_creation_enabled"],
                    topics_created_count=row["topics_created_count"],
                    is_current_user=row["is_current_user"],
                    created_at=row["user_created_at"],
                )
                entries.append(entry)

            return entries, has_next

    async def get_user_rank(self, user_pk: UUID) -> UserRankLookup | None:
        """Get a specific user's rank and position."""
        query = """
            SELECT
                user_pk,
                username,
                rank,
                loyalty_score,
                percentile_rank
            FROM leaderboard_rankings
            WHERE user_pk = $1
        """

        async with get_db_connection() as conn:
            row = await conn.fetchrow(query, user_pk)

            if not row:
                return UserRankLookup(
                    user_pk=user_pk,
                    username="",
                    rank=0,
                    loyalty_score=0,
                    percentile_rank=1.0,
                    found=False,
                )

            return UserRankLookup(
                user_pk=row["user_pk"],
                username=row["username"],
                rank=row["rank"],
                loyalty_score=row["loyalty_score"],
                percentile_rank=max(0.0, min(1.0, float(row["percentile_rank"]))),
                found=True,
            )

    async def get_nearby_users(
        self, user_pk: UUID, context_size: int = 10
    ) -> list[LeaderboardEntry]:
        """Get users near the specified user's rank."""
        # First get the user's rank
        user_rank = await self.get_user_rank(user_pk)
        if not user_rank or not user_rank.found:
            return []

        # Get users within context_size positions
        min_rank = max(1, user_rank.rank - context_size)
        max_rank = user_rank.rank + context_size

        query = """
            SELECT
                user_pk,
                username,
                loyalty_score,
                rank,
                percentile_rank,
                topics_created_count,
                topic_creation_enabled,
                user_created_at,
                CASE WHEN user_pk = $1 THEN true ELSE false END as is_current_user
            FROM leaderboard_rankings
            WHERE rank BETWEEN $2 AND $3
            ORDER BY rank ASC
        """

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, user_pk, min_rank, max_rank)

            entries = []
            for row in rows:
                badges = await self._get_user_badges(conn, row["user_pk"])

                entry = LeaderboardEntry(
                    user_pk=row["user_pk"],
                    username=row["username"],
                    loyalty_score=row["loyalty_score"],
                    rank=row["rank"],
                    percentile_rank=max(0.0, min(1.0, float(row["percentile_rank"]))),
                    badges=badges,
                    topic_creation_enabled=row["topic_creation_enabled"],
                    topics_created_count=row["topics_created_count"],
                    is_current_user=row["is_current_user"],
                    created_at=row["user_created_at"],
                )
                entries.append(entry)

            return entries

    async def search_users(
        self, search_term: str, limit: int = 20
    ) -> list[LeaderboardSearchResult]:
        """Search for users by username with relevance scoring."""
        query = """
            SELECT
                user_pk,
                username,
                rank,
                loyalty_score,
                similarity(username, $1) as match_score
            FROM leaderboard_rankings
            WHERE username ILIKE $2 OR similarity(username, $1) > 0.3
            ORDER BY match_score DESC, rank ASC
            LIMIT $3
        """

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, search_term, f"%{search_term}%", limit)

            results = []
            for row in rows:
                result = LeaderboardSearchResult(
                    user_pk=row["user_pk"],
                    username=row["username"],
                    rank=row["rank"],
                    loyalty_score=row["loyalty_score"],
                    match_score=float(row["match_score"]),
                )
                results.append(result)

            return results

    async def get_leaderboard_stats(self) -> LeaderboardStats:
        """Get overall leaderboard statistics."""
        query = """
            SELECT
                COUNT(*) as total_users,
                AVG(loyalty_score) as avg_score,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY loyalty_score) as median_score,
                MIN(CASE WHEN percentile_rank <= 0.1 THEN loyalty_score END) as top_10_threshold,
                calculated_at as last_updated
            FROM leaderboard_rankings
        """

        # Score distribution query
        distribution_query = """
            SELECT
                CASE
                    WHEN loyalty_score < 0 THEN 'negative'
                    WHEN loyalty_score = 0 THEN 'zero'
                    WHEN loyalty_score BETWEEN 1 AND 10 THEN '1-10'
                    WHEN loyalty_score BETWEEN 11 AND 50 THEN '11-50'
                    WHEN loyalty_score BETWEEN 51 AND 100 THEN '51-100'
                    ELSE '100+'
                END as score_range,
                COUNT(*) as count
            FROM leaderboard_rankings
            GROUP BY score_range
        """

        async with get_db_connection() as conn:
            stats_row = await conn.fetchrow(query)
            distribution_rows = await conn.fetch(distribution_query)

            if stats_row is None:
                raise ValueError("No leaderboard statistics found")

            score_distribution = {
                row["score_range"]: row["count"] for row in distribution_rows
            }

            return LeaderboardStats(
                total_users=stats_row["total_users"],
                active_users=stats_row[
                    "total_users"
                ],  # Materialized view only includes active users
                average_loyalty_score=float(stats_row["avg_score"] or 0),
                median_loyalty_score=int(stats_row["median_score"] or 0),
                top_10_percent_threshold=int(stats_row["top_10_threshold"] or 0),
                score_distribution=score_distribution,
                last_updated=stats_row["last_updated"],
            )

    async def get_user_rank_history(
        self, user_pk: UUID, days: int = 30
    ) -> list[RankHistoryEntry]:
        """Get historical rank data for a user."""
        query = """
            SELECT
                rank,
                loyalty_score,
                percentile_rank,
                snapshot_date,
                LAG(rank) OVER (ORDER BY snapshot_date) as previous_rank
            FROM leaderboard_snapshots
            WHERE user_pk = $1
            AND snapshot_date >= $2
            ORDER BY snapshot_date DESC
        """

        since_date = date.today() - timedelta(days=days)

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, user_pk, since_date)

            history = []
            for row in rows:
                rank_change = None
                if row["previous_rank"] is not None:
                    rank_change = (
                        row["previous_rank"] - row["rank"]
                    )  # Positive = improvement

                entry = RankHistoryEntry(
                    rank=row["rank"],
                    loyalty_score=row["loyalty_score"],
                    percentile_rank=max(0.0, min(1.0, float(row["percentile_rank"]))),
                    snapshot_date=row["snapshot_date"],
                    rank_change=rank_change,
                )
                history.append(entry)

            return history

    async def get_top_users(self, limit: int = 10) -> list[LeaderboardEntry]:
        """Get the top N users for widgets and displays."""
        query = """
            SELECT
                user_pk,
                username,
                loyalty_score,
                rank,
                percentile_rank,
                topics_created_count,
                topic_creation_enabled,
                user_created_at
            FROM leaderboard_rankings
            ORDER BY rank ASC
            LIMIT $1
        """

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, limit)

            entries = []
            for row in rows:
                badges = await self._get_user_badges(conn, row["user_pk"])

                entry = LeaderboardEntry(
                    user_pk=row["user_pk"],
                    username=row["username"],
                    loyalty_score=row["loyalty_score"],
                    rank=row["rank"],
                    percentile_rank=max(0.0, min(1.0, float(row["percentile_rank"]))),
                    badges=badges,
                    topic_creation_enabled=row["topic_creation_enabled"],
                    topics_created_count=row["topics_created_count"],
                    is_current_user=False,
                    created_at=row["user_created_at"],
                )
                entries.append(entry)

            return entries

    async def refresh_leaderboard(self) -> bool:
        """Refresh the materialized view and return success status."""
        try:
            async with get_db_connection() as conn:
                await conn.execute("SELECT refresh_leaderboard_rankings()")
                return True
        except Exception:
            return False

    async def create_daily_snapshot(self) -> bool:
        """Create daily snapshot and return success status."""
        try:
            async with get_db_connection() as conn:
                await conn.execute("SELECT create_daily_leaderboard_snapshot()")
                return True
        except Exception:
            return False

    async def _get_user_badges(
        self, conn: asyncpg.Connection, user_pk: UUID
    ) -> list[BadgeSummary]:
        """Get badges for a specific user."""
        query = """
            SELECT
                b.pk,
                b.name,
                b.description,
                b.image_url,
                ub.awarded_at
            FROM user_badges ub
            JOIN badges b ON ub.badge_pk = b.pk
            WHERE ub.user_pk = $1
            ORDER BY ub.awarded_at DESC
        """

        rows = await conn.fetch(query, user_pk)

        badges = []
        for row in rows:
            badge = BadgeSummary(
                pk=row["pk"],
                name=row["name"],
                description=row["description"],
                image_url=row["image_url"],
                awarded_at=row["awarded_at"],
            )
            badges.append(badge)

        return badges

    async def get_users_by_rank_range(
        self, start_rank: int, end_rank: int
    ) -> list[LeaderboardEntry]:
        """Get users within a specific rank range."""
        query = """
            SELECT
                lr.user_pk,
                lr.username,
                lr.loyalty_score,
                lr.rank,
                lr.percentile_rank,
                u.topics_created_count,
                u.topic_creation_enabled,
                u.created_at as user_created_at,
                FALSE as is_current_user
            FROM leaderboard_rankings lr
            JOIN users u ON lr.user_pk = u.pk
            WHERE lr.rank BETWEEN $1 AND $2
            ORDER BY lr.rank ASC
        """

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, start_rank, end_rank)
            entries = []
            for row in rows:
                # Load badges for each user
                badges = await self._get_user_badges(conn, row["user_pk"])

                entry = LeaderboardEntry(
                    user_pk=row["user_pk"],
                    username=row["username"],
                    loyalty_score=row["loyalty_score"],
                    rank=row["rank"],
                    percentile_rank=row["percentile_rank"],
                    topics_created_count=row["topics_created_count"],
                    topic_creation_enabled=row["topic_creation_enabled"],
                    created_at=row["user_created_at"],
                    is_current_user=row["is_current_user"],
                    badges=badges,
                )
                entries.append(entry)
            return entries

    async def get_users_by_percentile_range(
        self, start_percentile: float, end_percentile: float
    ) -> list[LeaderboardEntry]:
        """Get users within a specific percentile range."""
        query = """
            SELECT
                lr.user_pk,
                lr.username,
                lr.loyalty_score,
                lr.rank,
                lr.percentile_rank,
                u.topics_created_count,
                u.topic_creation_enabled,
                u.created_at as user_created_at,
                FALSE as is_current_user
            FROM leaderboard_rankings lr
            JOIN users u ON lr.user_pk = u.pk
            WHERE lr.percentile_rank BETWEEN $1 AND $2
            ORDER BY lr.rank ASC
        """

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, start_percentile, end_percentile)
            entries = []
            for row in rows:
                # Load badges for each user
                badges = await self._get_user_badges(conn, row["user_pk"])

                entry = LeaderboardEntry(
                    user_pk=row["user_pk"],
                    username=row["username"],
                    loyalty_score=row["loyalty_score"],
                    rank=row["rank"],
                    percentile_rank=row["percentile_rank"],
                    topics_created_count=row["topics_created_count"],
                    topic_creation_enabled=row["topic_creation_enabled"],
                    created_at=row["user_created_at"],
                    is_current_user=row["is_current_user"],
                    badges=badges,
                )
                entries.append(entry)
            return entries
