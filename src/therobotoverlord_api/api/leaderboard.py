"""Leaderboard API endpoints for The Robot Overlord."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import status

from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import require_role
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.leaderboard import LeaderboardEntry
from therobotoverlord_api.database.models.leaderboard import LeaderboardFilters
from therobotoverlord_api.database.models.leaderboard import LeaderboardResponse
from therobotoverlord_api.database.models.leaderboard import LeaderboardSearchResult
from therobotoverlord_api.database.models.leaderboard import LeaderboardStats
from therobotoverlord_api.database.models.leaderboard import PersonalLeaderboardStats
from therobotoverlord_api.database.models.leaderboard import UserRankLookup
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.services.leaderboard_service import get_leaderboard_service

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/", response_model=LeaderboardResponse)
async def get_leaderboard(  # noqa: PLR0913
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(description="Pagination cursor")] = None,
    badge_name: Annotated[str | None, Query(description="Filter by badge name")] = None,
    min_loyalty_score: Annotated[
        int | None, Query(description="Minimum loyalty score")
    ] = None,
    max_loyalty_score: Annotated[
        int | None, Query(description="Maximum loyalty score")
    ] = None,
    min_rank: Annotated[int | None, Query(ge=1, description="Minimum rank")] = None,
    max_rank: Annotated[int | None, Query(ge=1, description="Maximum rank")] = None,
    username_search: Annotated[
        str | None, Query(description="Search by username")
    ] = None,
    topic_creators_only: Annotated[  # noqa: FBT002
        bool, Query(description="Show only users who created topics")
    ] = False,
    active_users_only: Annotated[  # noqa: FBT002
        bool, Query(description="Show only active (non-banned) users")
    ] = True,
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
):
    """
    Get the global leaderboard with optional filtering and search.

    Uses cursor-based pagination for consistency during concurrent updates.
    All citizens can see the leaderboard - it's public by design.
    """
    # Validate parameter ranges
    if (
        min_loyalty_score is not None
        and max_loyalty_score is not None
        and min_loyalty_score > max_loyalty_score
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_loyalty_score cannot be greater than max_loyalty_score",
        )

    if min_rank is not None and max_rank is not None and min_rank > max_rank:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_rank cannot be greater than max_rank",
        )

    filters = LeaderboardFilters(
        badge_name=badge_name,
        min_loyalty_score=min_loyalty_score,
        max_loyalty_score=max_loyalty_score,
        min_rank=min_rank,
        max_rank=max_rank,
        username_search=username_search,
        topic_creators_only=topic_creators_only,
        active_users_only=active_users_only,
    )

    service = await get_leaderboard_service()
    current_user_pk = current_user.pk if current_user else None

    try:
        return await service.get_leaderboard(
            limit=limit,
            cursor=cursor,
            filters=filters,
            current_user_pk=current_user_pk,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/top/{count}")
async def get_top_users(
    count: Annotated[int, Path(ge=1, le=50)],
):
    """
    Get the top N users for widgets and homepage displays.

    Optimized for caching and fast response times.
    """
    service = await get_leaderboard_service()
    return {
        "status": "ok",
        "data": await service.get_top_users(count),
    }


@router.get("/stats", response_model=LeaderboardStats)
async def get_leaderboard_stats():
    """
    Get overall leaderboard statistics and metadata.

    Includes score distribution, thresholds, and system health info.
    """
    service = await get_leaderboard_service()
    return await service.get_leaderboard_stats()


@router.get("/search")
async def search_users(
    q: Annotated[str, Query(min_length=2, max_length=50, description="Search query")],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> dict[str, str | list[LeaderboardSearchResult]]:
    """
    Search for users by username with fuzzy matching.

    Returns results sorted by relevance score and rank.
    """
    service = await get_leaderboard_service()
    results = await service.search_users(q, limit)

    return {
        "status": "ok",
        "data": results,
    }


@router.get("/user/{user_pk}", response_model=UserRankLookup)
async def get_user_rank(user_pk: UUID):
    """
    Get a specific user's rank and position in the leaderboard.

    Public endpoint - anyone can look up any user's rank.
    """
    service = await get_leaderboard_service()
    user_rank = await service.repository.get_user_rank(user_pk)

    if not user_rank or not user_rank.found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_pk} not found in leaderboard",
        )

    return user_rank


@router.get("/me", response_model=PersonalLeaderboardStats)
async def get_my_leaderboard_stats(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get personal leaderboard statistics for the authenticated user.

    Includes current position, rank history, nearby users, and achievement progress.
    """
    service = await get_leaderboard_service()

    try:
        return await service.get_user_personal_stats(current_user.pk)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/user/{user_pk}/stats", response_model=PersonalLeaderboardStats)
async def get_user_personal_stats(user_pk: UUID):
    """
    Get personal leaderboard statistics for a specific user.

    Includes current position, rank history, nearby users, and achievement progress.
    """
    service = await get_leaderboard_service()

    try:
        return await service.get_user_personal_stats(user_pk)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/rank-range")
async def get_users_by_rank_range(
    start_rank: Annotated[int, Query(ge=1)],
    end_rank: Annotated[int, Query(ge=1)],
) -> list[LeaderboardEntry]:
    """
    Get users within a specific rank range.
    """
    if start_rank > end_rank:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_rank must be less than or equal to end_rank",
        )

    service = await get_leaderboard_service()
    return await service.get_users_by_rank_range(start_rank, end_rank)


@router.get("/percentile-range")
async def get_users_by_percentile_range(
    start_percentile: Annotated[float, Query(ge=0.0, le=1.0)],
    end_percentile: Annotated[float, Query(ge=0.0, le=1.0)],
) -> list[LeaderboardEntry]:
    """
    Get users within a specific percentile range.
    """
    if start_percentile > end_percentile:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_percentile must be less than or equal to end_percentile",
        )

    service = await get_leaderboard_service()
    return await service.get_users_by_percentile_range(start_percentile, end_percentile)


@router.get("/user/{user_pk}/nearby")
async def get_nearby_users(
    user_pk: UUID,
    context_size: Annotated[int, Query(ge=1, le=25)] = 10,
):
    """
    Get users near the specified user's rank position.

    Useful for showing context around a specific user's position.
    """
    service = await get_leaderboard_service()
    nearby_users = await service.repository.get_nearby_users(user_pk, context_size)

    if not nearby_users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_pk} not found in leaderboard",
        )

    return {
        "status": "ok",
        "data": nearby_users,
    }


@router.post("/refresh")
async def refresh_leaderboard(
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
):
    """
    Manually refresh the leaderboard materialized view and clear caches.

    Admin-only endpoint for maintenance and troubleshooting.
    """
    service = await get_leaderboard_service()
    success = await service.refresh_leaderboard_data()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh leaderboard data",
        )

    return {
        "status": "ok",
        "message": "Leaderboard data refreshed successfully",
    }


@router.get("/rank/{rank}")
async def get_user_at_rank(
    rank: Annotated[int, Path(ge=1, description="Rank position to lookup")],
):
    """
    Get the user at a specific rank position.

    Useful for "show me who's at rank 100" type queries.
    """
    # Use the regular leaderboard endpoint with rank filters
    service = await get_leaderboard_service()

    filters = LeaderboardFilters(
        min_rank=rank,
        max_rank=rank,
        active_users_only=True,
    )

    result = await service.get_leaderboard(
        limit=1,
        cursor=None,
        filters=filters,
        current_user_pk=None,
    )

    if not result.entries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found at rank {rank}",
        )

    return {
        "status": "ok",
        "data": result.entries[0],
    }


@router.get("/percentile/{percentile}")
async def get_users_in_percentile(
    percentile: Annotated[
        float, Path(ge=0.0, le=1.0, description="Percentile threshold (0.1 = top 10%)")
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """
    Get users within a specific percentile range.

    Examples:
    - percentile=0.1 gets top 10% users
    - percentile=0.9 gets bottom 10% users
    """
    service = await get_leaderboard_service()
    stats = await service.get_leaderboard_stats()

    # Calculate the rank range for this percentile
    total_users = stats.total_users
    if percentile <= 0.5:
        # Top percentile (0.1 = top 10%)
        max_rank = max(1, int(total_users * percentile))
        min_rank = 1
    else:
        # Bottom percentile (0.9 = bottom 10%)
        min_rank = max(1, int(total_users * percentile))
        max_rank = total_users

    filters = LeaderboardFilters(
        min_rank=min_rank,
        max_rank=max_rank,
        active_users_only=True,
    )

    result = await service.get_leaderboard(
        limit=limit,
        cursor=None,
        filters=filters,
        current_user_pk=None,
    )

    return {
        "status": "ok",
        "data": result.entries,
        "percentile_info": {
            "percentile": percentile,
            "rank_range": {"min": min_rank, "max": max_rank},
            "total_users": total_users,
        },
    }
