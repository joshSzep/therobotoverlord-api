"""Leaderboard data models for The Robot Overlord API."""

from datetime import date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field


class BadgeSummary(BaseModel):
    """Summary of a user badge for leaderboard display."""

    pk: UUID
    name: str
    description: str
    image_url: str
    awarded_at: datetime

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    """Single entry in the leaderboard."""

    user_pk: UUID
    username: str
    loyalty_score: int
    rank: int
    percentile_rank: float = Field(..., ge=0.0, le=1.0)
    badges: list[BadgeSummary] = Field(default_factory=list)
    topic_creation_enabled: bool
    topics_created_count: int = 0
    is_current_user: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class LeaderboardCursor(BaseModel):
    """Cursor for pagination through leaderboard results."""

    rank: int
    user_pk: UUID
    loyalty_score: int

    def encode(self) -> str:
        """Encode cursor to string for API responses."""
        return f"{self.rank}:{self.user_pk}:{self.loyalty_score}"

    @classmethod
    def decode(cls, cursor_str: str) -> "LeaderboardCursor":
        """Decode cursor from string."""
        parts = cursor_str.split(":")
        if len(parts) != 3:
            raise ValueError("Invalid cursor format")

        return cls(
            rank=int(parts[0]), user_pk=UUID(parts[1]), loyalty_score=int(parts[2])
        )


class PaginationInfo(BaseModel):
    """Pagination metadata for leaderboard responses."""

    limit: int
    has_next: bool
    has_previous: bool
    next_cursor: str | None = None
    previous_cursor: str | None = None
    total_count: int | None = None


class LeaderboardFilters(BaseModel):
    """Filters for leaderboard queries."""

    badge_name: str | None = None
    min_loyalty_score: int | None = None
    max_loyalty_score: int | None = None
    min_rank: int | None = None
    max_rank: int | None = None
    username_search: str | None = None
    topic_creators_only: bool = False
    active_users_only: bool = True  # Exclude banned users by default


class LeaderboardResponse(BaseModel):
    """Complete leaderboard API response."""

    entries: list[LeaderboardEntry]
    pagination: PaginationInfo
    current_user_position: LeaderboardEntry | None = None
    total_users: int
    last_updated: datetime
    filters_applied: LeaderboardFilters


class PersonalLeaderboardStats(BaseModel):
    """Personal leaderboard statistics for a user."""

    current_position: LeaderboardEntry
    rank_history: list["RankHistoryEntry"]
    nearby_users: list[LeaderboardEntry]  # ±10 positions
    achievement_progress: dict[str, float]
    percentile_improvement: float | None = None  # Change in percentile over time


class RankHistoryEntry(BaseModel):
    """Historical rank data for a user."""

    rank: int
    loyalty_score: int
    percentile_rank: float
    snapshot_date: date
    rank_change: int | None = None  # Change from previous snapshot

    class Config:
        from_attributes = True


class LeaderboardStats(BaseModel):
    """Overall leaderboard statistics."""

    total_users: int
    active_users: int
    average_loyalty_score: float
    median_loyalty_score: int
    top_10_percent_threshold: int
    score_distribution: dict[str, int]  # Score ranges and counts
    last_updated: datetime = Field(default_factory=datetime.now)


class UserRankLookup(BaseModel):
    """Result for looking up a specific user's rank."""

    user_pk: UUID
    username: str
    rank: int
    loyalty_score: int
    percentile_rank: float
    found: bool = True

    class Config:
        from_attributes = True


class LeaderboardSearchResult(BaseModel):
    """Search result for username searches."""

    user_pk: UUID
    username: str
    rank: int
    loyalty_score: int
    match_score: float  # Relevance score for search results

    class Config:
        from_attributes = True
