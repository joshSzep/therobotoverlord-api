"""Test fixtures for leaderboard testing."""

from datetime import UTC
from datetime import date
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.leaderboard import BadgeSummary
from therobotoverlord_api.database.models.leaderboard import LeaderboardEntry
from therobotoverlord_api.database.models.leaderboard import LeaderboardFilters
from therobotoverlord_api.database.models.leaderboard import LeaderboardStats
from therobotoverlord_api.database.models.leaderboard import RankHistoryEntry
from therobotoverlord_api.database.models.leaderboard import UserRankLookup


@pytest.fixture
def sample_user_pk():
    """Sample user UUID for testing."""
    return uuid4()


@pytest.fixture
def sample_badge():
    """Sample badge for testing."""
    return BadgeSummary(
        pk=uuid4(),
        name="Logic Master",
        description="Awarded for logical arguments",
        image_url="https://example.com/badge.png",
        awarded_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_leaderboard_entry(sample_user_pk, sample_badge):
    """Sample leaderboard entry for testing."""
    return LeaderboardEntry(
        user_pk=sample_user_pk,
        username="test_citizen",
        loyalty_score=100,
        rank=5,
        percentile_rank=0.05,
        badges=[sample_badge],
        topic_creation_enabled=True,
        topics_created_count=3,
        is_current_user=False,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_leaderboard_entries():
    """Sample list of leaderboard entries for testing."""
    entries = []
    for i in range(10):
        entry = LeaderboardEntry(
            user_pk=uuid4(),
            username=f"citizen_{i}",
            loyalty_score=100 - i * 10,
            rank=i + 1,
            percentile_rank=i * 0.1,
            badges=[],
            topic_creation_enabled=i < 3,  # Top 3 can create topics
            topics_created_count=max(0, 5 - i),
            is_current_user=False,
            created_at=datetime.now(UTC),
        )
        entries.append(entry)
    return entries


@pytest.fixture
def sample_filters():
    """Sample filters for testing."""
    return LeaderboardFilters(
        badge_name="Logic Master",
        min_loyalty_score=50,
        max_loyalty_score=200,
        username_search="citizen",
        topic_creators_only=False,
        active_users_only=True,
    )


@pytest.fixture
def sample_user_rank_lookup(sample_user_pk):
    """Sample user rank lookup for testing."""
    return UserRankLookup(
        user_pk=sample_user_pk,
        username="test_citizen",
        rank=42,
        loyalty_score=150,
        percentile_rank=0.42,
        found=True,
    )


@pytest.fixture
def sample_rank_history():
    """Sample rank history for testing."""
    return [
        RankHistoryEntry(
            rank=45,
            loyalty_score=140,
            percentile_rank=0.45,
            snapshot_date=date.today(),
            rank_change=3,  # Improved by 3 positions
        ),
        RankHistoryEntry(
            rank=48,
            loyalty_score=130,
            percentile_rank=0.48,
            snapshot_date=date(2025, 8, 18),
            rank_change=-2,  # Dropped by 2 positions
        ),
    ]


@pytest.fixture
def sample_leaderboard_stats():
    """Sample leaderboard statistics for testing."""
    return LeaderboardStats(
        total_users=1000,
        active_users=950,
        average_loyalty_score=75.5,
        median_loyalty_score=65,
        top_10_percent_threshold=150,
        score_distribution={
            "negative": 50,
            "zero": 100,
            "1-10": 200,
            "11-50": 300,
            "51-100": 200,
            "100+": 100,
        },
        last_updated=datetime.now(UTC),
    )


@pytest.fixture
def sample_leaderboard_response(sample_leaderboard_entries):
    """Sample leaderboard response for testing."""
    from therobotoverlord_api.database.models.leaderboard import LeaderboardFilters
    from therobotoverlord_api.database.models.leaderboard import LeaderboardResponse
    from therobotoverlord_api.database.models.leaderboard import PaginationInfo

    return LeaderboardResponse(
        entries=sample_leaderboard_entries[:5],
        pagination=PaginationInfo(
            limit=5,
            has_next=False,
            has_previous=False,
            next_cursor=None,
            previous_cursor=None,
            total_count=5,
        ),
        total_users=100,
        last_updated=datetime.now(UTC),
        filters_applied=LeaderboardFilters(),
        current_user_position=None,
    )


@pytest.fixture
def mock_db_connection():
    """Mock database connection for testing."""
    mock_conn = AsyncMock()

    # Mock common database operations
    mock_conn.fetch = AsyncMock()
    mock_conn.fetchrow = AsyncMock()
    mock_conn.execute = AsyncMock()

    return mock_conn


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_redis = AsyncMock()

    # Mock Redis operations
    mock_redis.get = AsyncMock(return_value=None)  # Default to cache miss
    mock_redis.setex = AsyncMock()
    mock_redis.delete = AsyncMock()
    mock_redis.keys = AsyncMock(return_value=[])

    return mock_redis


@pytest.fixture
def mock_leaderboard_repository():
    """Mock leaderboard repository for testing."""
    mock_repo = AsyncMock()

    # Set up default return values
    mock_repo.get_leaderboard_page = AsyncMock(return_value=([], False))
    mock_repo.get_user_rank = AsyncMock(return_value=None)
    mock_repo.get_nearby_users = AsyncMock(return_value=[])
    mock_repo.search_users = AsyncMock(return_value=[])
    mock_repo.get_leaderboard_stats = AsyncMock()
    mock_repo.get_user_rank_history = AsyncMock(return_value=[])
    mock_repo.get_top_users = AsyncMock(return_value=[])
    mock_repo.refresh_leaderboard = AsyncMock(return_value=True)
    mock_repo.create_daily_snapshot = AsyncMock(return_value=True)

    return mock_repo


@pytest.fixture
def mock_database_rows():
    """Mock database rows for leaderboard queries."""

    def create_mock_row(**kwargs):
        """Create a mock database row with dict-like access."""
        row = MagicMock()
        for key, value in kwargs.items():
            row.__getitem__ = MagicMock(side_effect=lambda k: kwargs.get(k))
            setattr(row, key, value)
        return row

    return create_mock_row


@pytest.fixture
def sample_db_leaderboard_rows():
    """Sample database rows for leaderboard queries."""

    def create_mock_row(**kwargs):
        """Create a mock database row with dict-like access."""
        row = MagicMock()
        # Store the data in a way that __getitem__ can access it
        row._data = kwargs.copy()
        row.__getitem__ = lambda self, key: self._data[key]
        row.__setitem__ = lambda self, key, value: self._data.update({key: value})

        # Support copy() method
        def copy_method():
            return create_mock_row(**row._data)

        row.copy = copy_method

        # Also set attributes for direct access
        for key, value in kwargs.items():
            setattr(row, key, value)
        return row

    rows = []
    for i in range(25):  # Create enough rows for pagination testing
        created_at = datetime.now(UTC)
        row = create_mock_row(
            user_pk=uuid4(),
            username=f"db_citizen_{i}",
            loyalty_score=200 - i * 20,
            rank=i + 1,
            percentile_rank=i * 0.2,
            topics_created_count=max(0, 3 - i),
            topic_creation_enabled=i < 10,  # More users can create topics
            user_created_at=created_at,
            created_at=created_at,  # Add this field for repository tests
            is_current_user=False,
        )
        rows.append(row)
    return rows


@pytest.fixture
def sample_db_badge_rows(mock_database_rows):
    """Sample database rows for badge queries."""
    return [
        mock_database_rows(
            pk=uuid4(),
            name="Logic Master",
            description="Logical arguments",
            image_url="https://example.com/logic.png",
            awarded_at=datetime.now(UTC),
        ),
        mock_database_rows(
            pk=uuid4(),
            name="Evidence Defender",
            description="Well-sourced posts",
            image_url="https://example.com/evidence.png",
            awarded_at=datetime.now(UTC),
        ),
    ]


@pytest.fixture
def sample_db_stats_row(mock_database_rows):
    """Sample database row for statistics query."""
    return mock_database_rows(
        total_users=1000,
        avg_score=75.5,
        median_score=65,
        top_10_threshold=150,
        last_updated=datetime.now(UTC),
    )


@pytest.fixture
def sample_db_distribution_rows(mock_database_rows):
    """Sample database rows for score distribution query."""
    return [
        mock_database_rows(score_range="negative", count=50),
        mock_database_rows(score_range="zero", count=100),
        mock_database_rows(score_range="1-10", count=200),
        mock_database_rows(score_range="11-50", count=300),
        mock_database_rows(score_range="51-100", count=200),
        mock_database_rows(score_range="100+", count=100),
    ]


class MockAsyncContextManager:
    """Mock async context manager for database connections."""

    def __init__(self, mock_connection):
        self.mock_connection = mock_connection

    async def __aenter__(self):
        return self.mock_connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_get_db_connection(mock_connection):
    """Mock the get_db_connection function."""

    def _mock_get_db_connection():
        return MockAsyncContextManager(mock_connection)

    return _mock_get_db_connection
