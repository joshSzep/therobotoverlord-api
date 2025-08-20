"""Loyalty Score repository for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
from uuid import UUID
from uuid import uuid4

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.loyalty_score import ContentType
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventFilters
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventOutcome
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventResponse
from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreBreakdown
from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreHistory
from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreStats
from therobotoverlord_api.database.models.loyalty_score import ModerationEvent
from therobotoverlord_api.database.models.loyalty_score import ModerationEventType
from therobotoverlord_api.database.models.loyalty_score import UserLoyaltyProfile
from therobotoverlord_api.database.repositories.base import BaseRepository


class LoyaltyScoreRepository(BaseRepository):
    """Repository for loyalty score operations."""

    def __init__(self):
        super().__init__("moderation_events")

    def _record_to_model(self, record: Record) -> ModerationEvent:
        """Convert database record to ModerationEvent model."""
        return ModerationEvent(
            pk=record["pk"],
            user_pk=record["user_pk"],
            event_type=ModerationEventType(record["event_type"]),
            content_type=ContentType(record["content_type"]),
            content_pk=record["content_pk"],
            outcome=LoyaltyEventOutcome(record["outcome"]),
            score_delta=record["score_delta"],
            previous_score=record["previous_score"],
            new_score=record["new_score"],
            moderator_pk=record["moderator_pk"],
            reason=record["reason"],
            metadata=record["metadata"] or {},
            created_at=record["created_at"],
        )

    async def record_moderation_event(
        self,
        user_pk: UUID,
        event_type: ModerationEventType,
        content_type: ContentType,
        content_pk: UUID,
        outcome: LoyaltyEventOutcome,
        score_delta: int,
        moderator_pk: UUID | None = None,
        reason: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> ModerationEvent:
        """Record a moderation event and update user's loyalty score."""
        event_pk = uuid4()
        now = datetime.now(UTC)

        async with get_db_connection() as conn:
            async with conn.transaction():
                # Get current user score
                current_score_row = await conn.fetchrow(
                    "SELECT loyalty_score FROM users WHERE pk = $1", user_pk
                )
                if not current_score_row:
                    raise ValueError(f"User {user_pk} not found")

                previous_score = current_score_row["loyalty_score"]
                new_score = previous_score + score_delta

                # Update user's loyalty score
                await conn.execute(
                    """
                    UPDATE users
                    SET loyalty_score = $1, updated_at = $2
                    WHERE pk = $3
                    """,
                    new_score,
                    now,
                    user_pk,
                )

                # Insert moderation event
                await conn.execute(
                    """
                    INSERT INTO moderation_events
                    (pk, user_pk, event_type, content_type, content_pk, outcome,
                     score_delta, previous_score, new_score, moderator_pk, reason,
                     metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    """,
                    event_pk,
                    user_pk,
                    event_type.value,
                    content_type.value,
                    content_pk,
                    outcome.value,
                    score_delta,
                    previous_score,
                    new_score,
                    moderator_pk,
                    reason,
                    metadata,
                    now,
                )

                # Insert score history record
                await conn.execute(
                    """
                    INSERT INTO loyalty_score_history
                    (user_pk, score, recorded_at, event_pk)
                    VALUES ($1, $2, $3, $4)
                    """,
                    user_pk,
                    new_score,
                    now,
                    event_pk,
                )

        # Return the created event
        return ModerationEvent(
            pk=event_pk,
            user_pk=user_pk,
            event_type=event_type,
            content_type=content_type,
            content_pk=content_pk,
            outcome=outcome,
            score_delta=score_delta,
            previous_score=previous_score,
            new_score=new_score,
            moderator_pk=moderator_pk,
            reason=reason,
            metadata=metadata or {},
            created_at=now,
        )

    async def get_user_loyalty_profile(self, user_pk: UUID) -> UserLoyaltyProfile:
        """Get complete loyalty profile for a user."""
        async with get_db_connection() as conn:
            # Get user basic info and current score
            user_row = await conn.fetchrow(
                """
                SELECT u.username, u.loyalty_score, lr.rank, lr.percentile_rank,
                       lr.topic_creation_enabled
                FROM users u
                LEFT JOIN leaderboard_rankings lr ON u.pk = lr.user_pk
                WHERE u.pk = $1
                """,
                user_pk,
            )

            if not user_row:
                raise ValueError(f"User {user_pk} not found")

            # Get score breakdown
            breakdown = await self.get_score_breakdown(user_pk)

            # Get recent events (last 10)
            recent_events = await self.get_user_events(user_pk, None, 1, 10)

            # Get score history (last 30 days)
            history = await self.get_user_score_history(user_pk, 30)

            # Calculate next threshold
            thresholds = await self._get_score_thresholds()
            current_score = user_row["loyalty_score"]
            next_threshold = None
            next_threshold_description = None

            for threshold_name, threshold_score in thresholds.items():
                if current_score < threshold_score and (
                    next_threshold is None or threshold_score < next_threshold
                ):
                    next_threshold = threshold_score
                    next_threshold_description = threshold_name

            return UserLoyaltyProfile(
                user_pk=user_pk,
                username=user_row["username"],
                current_score=current_score,
                rank=user_row["rank"],
                percentile_rank=user_row["percentile_rank"],
                breakdown=breakdown,
                recent_events=recent_events.events,
                score_history=history,
                can_create_topics=user_row["topic_creation_enabled"] or False,
                next_threshold=next_threshold,
                next_threshold_description=next_threshold_description,
            )

    async def get_score_breakdown(self, user_pk: UUID) -> LoyaltyScoreBreakdown:
        """Get detailed score breakdown for a user."""
        query = """
        SELECT
            u.pk as user_pk,
            u.loyalty_score as current_score,
            COALESCE(SUM(CASE WHEN me.content_type = 'post' AND me.outcome = 'approved' THEN me.score_delta ELSE 0 END), 0) as post_approved_score,
            COALESCE(SUM(CASE WHEN me.content_type = 'post' AND me.outcome = 'rejected' THEN me.score_delta ELSE 0 END), 0) as post_rejected_score,
            COALESCE(SUM(CASE WHEN me.content_type = 'topic' AND me.outcome = 'approved' THEN me.score_delta ELSE 0 END), 0) as topic_approved_score,
            COALESCE(SUM(CASE WHEN me.content_type = 'topic' AND me.outcome = 'rejected' THEN me.score_delta ELSE 0 END), 0) as topic_rejected_score,
            COALESCE(SUM(CASE WHEN me.content_type = 'private_message' AND me.outcome = 'approved' THEN me.score_delta ELSE 0 END), 0) as message_approved_score,
            COALESCE(SUM(CASE WHEN me.content_type = 'private_message' AND me.outcome = 'rejected' THEN me.score_delta ELSE 0 END), 0) as message_rejected_score,
            COALESCE(SUM(CASE WHEN me.outcome IN ('appeal_sustained', 'appeal_denied') THEN me.score_delta ELSE 0 END), 0) as appeal_adjustments,
            COALESCE(SUM(CASE WHEN me.event_type = 'manual_adjustment' THEN me.score_delta ELSE 0 END), 0) as manual_adjustments,
            COUNT(CASE WHEN me.content_type = 'post' AND me.outcome = 'approved' THEN 1 END) as total_approved_posts,
            COUNT(CASE WHEN me.content_type = 'post' AND me.outcome = 'rejected' THEN 1 END) as total_rejected_posts,
            COUNT(CASE WHEN me.content_type = 'topic' AND me.outcome = 'approved' THEN 1 END) as total_approved_topics,
            COUNT(CASE WHEN me.content_type = 'topic' AND me.outcome = 'rejected' THEN 1 END) as total_rejected_topics,
            COUNT(CASE WHEN me.content_type = 'private_message' AND me.outcome = 'approved' THEN 1 END) as total_approved_messages,
            COUNT(CASE WHEN me.content_type = 'private_message' AND me.outcome = 'rejected' THEN 1 END) as total_rejected_messages,
            u.updated_at as last_updated
        FROM users u
        LEFT JOIN moderation_events me ON u.pk = me.user_pk
        WHERE u.pk = $1
        GROUP BY u.pk, u.loyalty_score, u.updated_at
        """

        async with get_db_connection() as conn:
            row = await conn.fetchrow(query, user_pk)

            if not row:
                raise ValueError(f"User {user_pk} not found")

            return LoyaltyScoreBreakdown(
                user_pk=user_pk,
                current_score=row["current_score"],
                post_score=row["post_approved_score"] + row["post_rejected_score"],
                topic_score=row["topic_approved_score"] + row["topic_rejected_score"],
                private_message_score=row["message_approved_score"]
                + row["message_rejected_score"],
                appeal_adjustments=row["appeal_adjustments"],
                manual_adjustments=row["manual_adjustments"],
                total_approved_posts=row["total_approved_posts"],
                total_rejected_posts=row["total_rejected_posts"],
                total_approved_topics=row["total_approved_topics"],
                total_rejected_topics=row["total_rejected_topics"],
                total_approved_messages=row["total_approved_messages"],
                total_rejected_messages=row["total_rejected_messages"],
                last_updated=row["last_updated"],
            )

    async def get_user_events(
        self,
        user_pk: UUID,
        filters: LoyaltyEventFilters | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> LoyaltyEventResponse:
        """Get moderation events for a user with pagination."""
        offset = (page - 1) * page_size
        where_conditions = ["user_pk = $1"]
        params: list[Any] = [user_pk]
        param_count = 1

        # Apply filters
        if filters:
            if filters.event_type:
                param_count += 1
                where_conditions.append(f"event_type = ${param_count}")
                params.append(filters.event_type.value)

            if filters.content_type:
                param_count += 1
                where_conditions.append(f"content_type = ${param_count}")
                params.append(filters.content_type.value)

            if filters.outcome:
                param_count += 1
                where_conditions.append(f"outcome = ${param_count}")
                params.append(filters.outcome.value)

            if filters.start_date:
                param_count += 1
                where_conditions.append(f"created_at >= ${param_count}")
                params.append(filters.start_date)

            if filters.end_date:
                param_count += 1
                where_conditions.append(f"created_at <= ${param_count}")
                params.append(filters.end_date)

        # Count query
        count_query = f"""
        SELECT COUNT(*)
        FROM moderation_events
        WHERE {" AND ".join(where_conditions)}
        """

        # Data query
        data_query = f"""
        SELECT *
        FROM moderation_events
        WHERE {" AND ".join(where_conditions)}
        ORDER BY created_at DESC
        LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """

        async with get_db_connection() as conn:
            total_count_result = await conn.fetchval(count_query, *params)
            total_count = total_count_result or 0
            rows = await conn.fetch(data_query, *params, page_size, offset)

            events = [self._record_to_model(row) for row in rows]

            return LoyaltyEventResponse(
                events=events,
                total_count=total_count,
                page=page,
                page_size=page_size,
                has_next=offset + len(events) < total_count,
                filters_applied=filters or LoyaltyEventFilters(),
            )

    async def get_user_score_history(
        self, user_pk: UUID, days: int = 30
    ) -> list[LoyaltyScoreHistory]:
        """Get historical score data for a user."""
        since_date = datetime.now(UTC) - timedelta(days=days)

        query = """
        SELECT user_pk, score, recorded_at, event_pk
        FROM loyalty_score_history
        WHERE user_pk = $1 AND recorded_at >= $2
        ORDER BY recorded_at DESC
        LIMIT 100
        """

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, user_pk, since_date)

            return [
                LoyaltyScoreHistory(
                    user_pk=row["user_pk"],
                    score=row["score"],
                    recorded_at=row["recorded_at"],
                    event_pk=row["event_pk"],
                )
                for row in rows
            ]

    async def get_system_stats(self) -> LoyaltyScoreStats:
        """Get system-wide loyalty score statistics."""
        stats_query = """
        SELECT
            COUNT(*) as total_users,
            AVG(loyalty_score) as average_score,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY loyalty_score) as median_score,
            MIN(CASE WHEN lr.percentile_rank <= 0.1 THEN loyalty_score END) as top_10_threshold
        FROM users u
        LEFT JOIN leaderboard_rankings lr ON u.pk = lr.user_pk
        WHERE u.is_banned = false
        """

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
        FROM users
        WHERE is_banned = false
        GROUP BY score_range
        """

        events_query = """
        SELECT COUNT(*) as total_events
        FROM moderation_events
        """

        async with get_db_connection() as conn:
            stats_row = await conn.fetchrow(stats_query)
            distribution_rows = await conn.fetch(distribution_query)
            events_row = await conn.fetchrow(events_query)

            if not stats_row or not events_row:
                raise ValueError("Failed to retrieve system statistics")

            score_distribution = {
                row["score_range"]: row["count"] for row in distribution_rows
            }

            # Calculate topic creation threshold (top 10%)
            topic_threshold = int(stats_row["top_10_threshold"] or 0)

            return LoyaltyScoreStats(
                total_users=stats_row["total_users"],
                average_score=float(stats_row["average_score"] or 0),
                median_score=int(stats_row["median_score"] or 0),
                score_distribution=score_distribution,
                top_10_percent_threshold=int(stats_row["top_10_threshold"] or 0),
                topic_creation_threshold=topic_threshold,
                total_events_processed=events_row["total_events"],
                last_updated=datetime.now(UTC),
            )

    async def apply_manual_adjustment(
        self,
        user_pk: UUID,
        adjustment: int,
        reason: str,
        admin_notes: str | None,
        admin_pk: UUID,
    ) -> ModerationEvent:
        """Apply manual loyalty score adjustment."""
        metadata = {}
        if admin_notes:
            metadata["admin_notes"] = admin_notes

        return await self.record_moderation_event(
            user_pk=user_pk,
            event_type=ModerationEventType.MANUAL_ADJUSTMENT,
            content_type=ContentType.POST,  # Placeholder
            content_pk=uuid4(),  # Placeholder
            outcome=LoyaltyEventOutcome.APPROVED
            if adjustment > 0
            else LoyaltyEventOutcome.REJECTED,
            score_delta=adjustment,
            moderator_pk=admin_pk,
            reason=reason,
            metadata=metadata,
        )

    async def recalculate_user_score(self, user_pk: UUID) -> int:
        """Recalculate a user's loyalty score from scratch."""
        query = """
        SELECT COALESCE(SUM(score_delta), 0) as total_score
        FROM moderation_events
        WHERE user_pk = $1
        """

        async with get_db_connection() as conn:
            async with conn.transaction():
                # Calculate total from events
                result = await conn.fetchrow(query, user_pk)
                if not result:
                    raise ValueError(f"Failed to calculate score for user {user_pk}")
                new_score = result["total_score"]

                # Update user record
                await conn.execute(
                    """
                    UPDATE users
                    SET loyalty_score = $1, updated_at = $2
                    WHERE pk = $3
                    """,
                    new_score,
                    datetime.now(UTC),
                    user_pk,
                )

                return new_score

    async def get_users_by_score_range(
        self, min_score: int, max_score: int, limit: int = 100
    ) -> list[UserLoyaltyProfile]:
        """Get users within a specific score range."""
        query = """
        SELECT u.pk, u.username, u.loyalty_score, lr.rank, lr.percentile_rank,
               lr.topic_creation_enabled
        FROM users u
        LEFT JOIN leaderboard_rankings lr ON u.pk = lr.user_pk
        WHERE u.loyalty_score BETWEEN $1 AND $2
        AND u.is_banned = false
        ORDER BY u.loyalty_score DESC
        LIMIT $3
        """

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, min_score, max_score, limit)

            profiles = []
            for row in rows:
                # Get basic breakdown for each user
                breakdown = await self.get_score_breakdown(row["pk"])

                profile = UserLoyaltyProfile(
                    user_pk=row["pk"],
                    username=row["username"],
                    current_score=row["loyalty_score"],
                    rank=row["rank"],
                    percentile_rank=row["percentile_rank"],
                    breakdown=breakdown,
                    recent_events=[],  # Skip for bulk queries
                    score_history=[],  # Skip for bulk queries
                    can_create_topics=row["topic_creation_enabled"] or False,
                )
                profiles.append(profile)

            return profiles

    async def get_recent_events(
        self, filters: LoyaltyEventFilters | None = None, limit: int = 100
    ) -> list[ModerationEvent]:
        """Get recent moderation events across all users."""
        where_conditions = []
        params: list[Any] = []
        param_count = 0

        # Apply filters
        if filters:
            if filters.event_type:
                param_count += 1
                where_conditions.append(f"event_type = ${param_count}")
                params.append(filters.event_type.value)

            if filters.content_type:
                param_count += 1
                where_conditions.append(f"content_type = ${param_count}")
                params.append(filters.content_type.value)

            if filters.outcome:
                param_count += 1
                where_conditions.append(f"outcome = ${param_count}")
                params.append(filters.outcome.value)

        where_clause = ""
        if where_conditions:
            where_clause = f"WHERE {' AND '.join(where_conditions)}"

        query = f"""
        SELECT *
        FROM moderation_events
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_count + 1}
        """

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, *params, limit)
            return [self._record_to_model(row) for row in rows]

    async def _get_score_thresholds(self) -> dict[str, int]:
        """Get current score thresholds."""
        stats = await self.get_system_stats()
        return {
            "topic_creation": stats.topic_creation_threshold,
            "priority_moderation": 500,
            "extended_appeals": 1000,
        }
