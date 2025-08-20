"""Unit tests for leaderboard data models."""

from datetime import UTC
from datetime import date
from datetime import datetime
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.leaderboard import BadgeSummary
from therobotoverlord_api.database.models.leaderboard import LeaderboardCursor
from therobotoverlord_api.database.models.leaderboard import LeaderboardEntry
from therobotoverlord_api.database.models.leaderboard import LeaderboardFilters
from therobotoverlord_api.database.models.leaderboard import LeaderboardResponse
from therobotoverlord_api.database.models.leaderboard import LeaderboardSearchResult
from therobotoverlord_api.database.models.leaderboard import LeaderboardStats
from therobotoverlord_api.database.models.leaderboard import PaginationInfo
from therobotoverlord_api.database.models.leaderboard import PersonalLeaderboardStats
from therobotoverlord_api.database.models.leaderboard import RankHistoryEntry
from therobotoverlord_api.database.models.leaderboard import UserRankLookup


class TestBadgeSummary:
    """Test BadgeSummary model."""

    def test_badge_summary_creation(self):
        """Test creating a BadgeSummary instance."""
        badge_pk = uuid4()
        awarded_at = datetime.now(UTC)

        badge = BadgeSummary(
            pk=badge_pk,
            name="Logic Master",
            description="Awarded for logical arguments",
            image_url="https://example.com/badge.png",
            awarded_at=awarded_at,
        )

        assert badge.pk == badge_pk
        assert badge.name == "Logic Master"
        assert badge.description == "Awarded for logical arguments"
        assert badge.image_url == "https://example.com/badge.png"
        assert badge.awarded_at == awarded_at

    def test_badge_summary_from_attributes(self):
        """Test BadgeSummary creation from database row."""
        # Simulate database row
        row_data = {
            "pk": uuid4(),
            "name": "Evidence Defender",
            "description": "Well-sourced arguments",
            "image_url": "https://example.com/evidence.png",
            "awarded_at": datetime.now(UTC),
        }

        badge = BadgeSummary.model_validate(row_data)
        assert badge.name == "Evidence Defender"


class TestLeaderboardCursor:
    """Test LeaderboardCursor model."""

    def test_cursor_creation(self):
        """Test creating a cursor."""
        user_pk = uuid4()
        cursor = LeaderboardCursor(
            rank=42,
            user_pk=user_pk,
            loyalty_score=150,
        )

        assert cursor.rank == 42
        assert cursor.user_pk == user_pk
        assert cursor.loyalty_score == 150

    def test_cursor_encode_decode(self):
        """Test cursor encoding and decoding."""
        user_pk = uuid4()
        original_cursor = LeaderboardCursor(
            rank=42,
            user_pk=user_pk,
            loyalty_score=150,
        )

        # Encode to string
        encoded = original_cursor.encode()
        assert isinstance(encoded, str)
        assert "42" in encoded
        assert str(user_pk) in encoded
        assert "150" in encoded

        # Decode back to cursor
        decoded_cursor = LeaderboardCursor.decode(encoded)
        assert decoded_cursor.rank == original_cursor.rank
        assert decoded_cursor.user_pk == original_cursor.user_pk
        assert decoded_cursor.loyalty_score == original_cursor.loyalty_score

    def test_cursor_decode_invalid_format(self):
        """Test cursor decoding with invalid format."""
        with pytest.raises(ValueError, match="Invalid cursor format"):
            LeaderboardCursor.decode("invalid:format")

        with pytest.raises(ValueError, match="Invalid cursor format"):
            LeaderboardCursor.decode("only_one_part")


class TestLeaderboardEntry:
    """Test LeaderboardEntry model."""

    def test_leaderboard_entry_creation(self):
        """Test creating a leaderboard entry."""
        user_pk = uuid4()
        created_at = datetime.now(UTC)

        entry = LeaderboardEntry(
            user_pk=user_pk,
            username="test_citizen",
            loyalty_score=100,
            rank=5,
            percentile_rank=0.05,
            badges=[],
            topic_creation_enabled=True,
            topics_created_count=3,
            is_current_user=False,
            created_at=created_at,
        )

        assert entry.user_pk == user_pk
        assert entry.username == "test_citizen"
        assert entry.loyalty_score == 100
        assert entry.rank == 5
        assert entry.percentile_rank == 0.05
        assert entry.topic_creation_enabled is True
        assert entry.topics_created_count == 3
        assert entry.is_current_user is False

    def test_leaderboard_entry_with_badges(self):
        """Test leaderboard entry with badges."""
        user_pk = uuid4()
        badge = BadgeSummary(
            pk=uuid4(),
            name="Logic Master",
            description="Logical arguments",
            image_url="https://example.com/badge.png",
            awarded_at=datetime.now(UTC),
        )

        entry = LeaderboardEntry(
            user_pk=user_pk,
            username="badge_holder",
            loyalty_score=200,
            rank=1,
            percentile_rank=0.0,
            badges=[badge],
            topic_creation_enabled=True,
            topics_created_count=10,
            is_current_user=True,
            created_at=datetime.now(UTC),
        )

        assert len(entry.badges) == 1
        assert entry.badges[0].name == "Logic Master"
        assert entry.is_current_user is True

    def test_percentile_rank_validation(self):
        """Test percentile rank validation."""
        user_pk = uuid4()

        # Valid percentile ranks
        for percentile in [0.0, 0.5, 1.0]:
            entry = LeaderboardEntry(
                user_pk=user_pk,
                username="test",
                loyalty_score=100,
                rank=1,
                percentile_rank=percentile,
                topic_creation_enabled=False,
                created_at=datetime.now(UTC),
            )
            assert entry.percentile_rank == percentile

        # Invalid percentile ranks should raise validation error
        with pytest.raises(ValueError):
            LeaderboardEntry(
                user_pk=user_pk,
                username="test",
                loyalty_score=100,
                rank=1,
                percentile_rank=-0.1,  # Invalid: below 0
                topic_creation_enabled=False,
                created_at=datetime.now(UTC),
            )

        with pytest.raises(ValueError):
            LeaderboardEntry(
                user_pk=user_pk,
                username="test",
                loyalty_score=100,
                rank=1,
                percentile_rank=1.1,  # Invalid: above 1
                topic_creation_enabled=False,
                created_at=datetime.now(UTC),
            )


class TestLeaderboardFilters:
    """Test LeaderboardFilters model."""

    def test_default_filters(self):
        """Test default filter values."""
        filters = LeaderboardFilters()

        assert filters.badge_name is None
        assert filters.min_loyalty_score is None
        assert filters.max_loyalty_score is None
        assert filters.min_rank is None
        assert filters.max_rank is None
        assert filters.username_search is None
        assert filters.topic_creators_only is False
        assert filters.active_users_only is True  # Default to active users

    def test_filters_with_values(self):
        """Test filters with specific values."""
        filters = LeaderboardFilters(
            badge_name="Logic Master",
            min_loyalty_score=50,
            max_loyalty_score=200,
            min_rank=1,
            max_rank=100,
            username_search="citizen",
            topic_creators_only=True,
            active_users_only=False,
        )

        assert filters.badge_name == "Logic Master"
        assert filters.min_loyalty_score == 50
        assert filters.max_loyalty_score == 200
        assert filters.min_rank == 1
        assert filters.max_rank == 100
        assert filters.username_search == "citizen"
        assert filters.topic_creators_only is True
        assert filters.active_users_only is False


class TestPaginationInfo:
    """Test PaginationInfo model."""

    def test_pagination_info_creation(self):
        """Test creating pagination info."""
        pagination = PaginationInfo(
            limit=50,
            has_next=True,
            has_previous=False,
            next_cursor="next_cursor_string",
            previous_cursor=None,
            total_count=1000,
        )

        assert pagination.limit == 50
        assert pagination.has_next is True
        assert pagination.has_previous is False
        assert pagination.next_cursor == "next_cursor_string"
        assert pagination.previous_cursor is None
        assert pagination.total_count == 1000


class TestLeaderboardResponse:
    """Test LeaderboardResponse model."""

    def test_leaderboard_response_creation(self):
        """Test creating a complete leaderboard response."""
        user_pk = uuid4()
        entry = LeaderboardEntry(
            user_pk=user_pk,
            username="test_user",
            loyalty_score=100,
            rank=1,
            percentile_rank=0.0,
            topic_creation_enabled=True,
            created_at=datetime.now(UTC),
        )

        pagination = PaginationInfo(
            limit=50,
            has_next=False,
            has_previous=False,
            total_count=1,
        )

        filters = LeaderboardFilters()
        last_updated = datetime.now(UTC)

        response = LeaderboardResponse(
            entries=[entry],
            pagination=pagination,
            current_user_position=entry,
            total_users=1,
            last_updated=last_updated,
            filters_applied=filters,
        )

        assert len(response.entries) == 1
        assert response.entries[0].username == "test_user"
        assert response.current_user_position == entry
        assert response.total_users == 1
        assert response.last_updated == last_updated
        assert response.filters_applied == filters


class TestUserRankLookup:
    """Test UserRankLookup model."""

    def test_user_rank_lookup_found(self):
        """Test user rank lookup when user is found."""
        user_pk = uuid4()
        lookup = UserRankLookup(
            user_pk=user_pk,
            username="found_user",
            rank=42,
            loyalty_score=150,
            percentile_rank=0.42,
            found=True,
        )

        assert lookup.user_pk == user_pk
        assert lookup.username == "found_user"
        assert lookup.rank == 42
        assert lookup.loyalty_score == 150
        assert lookup.percentile_rank == 0.42
        assert lookup.found is True

    def test_user_rank_lookup_not_found(self):
        """Test user rank lookup when user is not found."""
        user_pk = uuid4()
        lookup = UserRankLookup(
            user_pk=user_pk,
            username="",
            rank=0,
            loyalty_score=0,
            percentile_rank=1.0,
            found=False,
        )

        assert lookup.user_pk == user_pk
        assert lookup.username == ""
        assert lookup.found is False


class TestRankHistoryEntry:
    """Test RankHistoryEntry model."""

    def test_rank_history_entry_creation(self):
        """Test creating a rank history entry."""
        snapshot_date = date.today()
        entry = RankHistoryEntry(
            rank=42,
            loyalty_score=150,
            percentile_rank=0.42,
            snapshot_date=snapshot_date,
            rank_change=5,  # Improved by 5 positions
        )

        assert entry.rank == 42
        assert entry.loyalty_score == 150
        assert entry.percentile_rank == 0.42
        assert entry.snapshot_date == snapshot_date
        assert entry.rank_change == 5

    def test_rank_history_entry_no_change(self):
        """Test rank history entry with no rank change data."""
        entry = RankHistoryEntry(
            rank=42,
            loyalty_score=150,
            percentile_rank=0.42,
            snapshot_date=date.today(),
            rank_change=None,  # No previous data
        )

        assert entry.rank_change is None


class TestLeaderboardStats:
    """Test LeaderboardStats model."""

    def test_leaderboard_stats_creation(self):
        """Test creating leaderboard statistics."""
        last_updated = datetime.now(UTC)
        score_distribution = {
            "negative": 10,
            "zero": 50,
            "1-10": 100,
            "11-50": 200,
            "51-100": 150,
            "100+": 90,
        }

        stats = LeaderboardStats(
            total_users=600,
            active_users=580,
            average_loyalty_score=45.5,
            median_loyalty_score=35,
            top_10_percent_threshold=120,
            score_distribution=score_distribution,
            last_updated=last_updated,
        )

        assert stats.total_users == 600
        assert stats.active_users == 580
        assert stats.average_loyalty_score == 45.5
        assert stats.median_loyalty_score == 35
        assert stats.top_10_percent_threshold == 120
        assert stats.score_distribution == score_distribution
        assert stats.last_updated == last_updated


class TestLeaderboardSearchResult:
    """Test LeaderboardSearchResult model."""

    def test_search_result_creation(self):
        """Test creating a search result."""
        user_pk = uuid4()
        result = LeaderboardSearchResult(
            user_pk=user_pk,
            username="search_result_user",
            rank=25,
            loyalty_score=75,
            match_score=0.85,
        )

        assert result.user_pk == user_pk
        assert result.username == "search_result_user"
        assert result.rank == 25
        assert result.loyalty_score == 75
        assert result.match_score == 0.85


class TestPersonalLeaderboardStats:
    """Test PersonalLeaderboardStats model."""

    def test_personal_stats_creation(self):
        """Test creating personal leaderboard statistics."""
        user_pk = uuid4()
        current_position = LeaderboardEntry(
            user_pk=user_pk,
            username="personal_user",
            loyalty_score=100,
            rank=10,
            percentile_rank=0.1,
            topic_creation_enabled=True,
            created_at=datetime.now(UTC),
        )

        rank_history = [
            RankHistoryEntry(
                rank=12,
                loyalty_score=90,
                percentile_rank=0.12,
                snapshot_date=date.today(),
                rank_change=2,  # Improved by 2
            )
        ]

        nearby_users = [current_position]  # Simplified

        achievement_progress = {
            "topic_creator": 0.6,
            "loyalty_builder": 0.8,
            "top_10_percent": 1.0,
        }

        stats = PersonalLeaderboardStats(
            current_position=current_position,
            rank_history=rank_history,
            nearby_users=nearby_users,
            achievement_progress=achievement_progress,
            percentile_improvement=0.02,
        )

        assert stats.current_position == current_position
        assert len(stats.rank_history) == 1
        assert stats.rank_history[0].rank == 12
        assert len(stats.nearby_users) == 1
        assert stats.achievement_progress["topic_creator"] == 0.6
        assert stats.percentile_improvement == 0.02
