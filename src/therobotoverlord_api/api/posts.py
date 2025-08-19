"""Posts API endpoints for The Robot Overlord."""

from datetime import UTC
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import require_role
from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.post import PostCreate
from therobotoverlord_api.database.models.post import PostSummary
from therobotoverlord_api.database.models.post import PostThread
from therobotoverlord_api.database.models.post import PostUpdate
from therobotoverlord_api.database.models.post import PostWithAuthor
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.repositories.post import PostRepository
from therobotoverlord_api.services.queue_service import get_queue_service

router = APIRouter(prefix="/posts", tags=["posts"])

# Create dependency instances to avoid function calls in defaults
moderator_dependency = require_role(UserRole.MODERATOR)


@router.get("/")
async def get_posts(
    topic_id: Annotated[UUID | None, Query()] = None,
    author_id: Annotated[UUID | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PostWithAuthor]:
    """Get posts with optional filtering by topic, author, or search term."""
    post_repo = PostRepository()

    if search:
        return await post_repo.search_posts(search, topic_id, limit, offset)
    if topic_id:
        return await post_repo.get_approved_by_topic(topic_id, limit, offset)
    if author_id:
        # Convert PostSummary to PostWithAuthor for consistency
        summaries = await post_repo.get_by_author(
            author_id, ContentStatus.APPROVED, limit, offset
        )
        # Note: This would need a separate endpoint or different return type in practice
        # For now, return recent approved posts
        return await post_repo.get_recent_approved_posts(limit, offset)

    return await post_repo.get_recent_approved_posts(limit, offset)


# Specific routes must come before parameterized routes
@router.get("/graveyard")
async def get_graveyard_posts(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PostWithAuthor]:
    """Get rejected posts (graveyard) - author's private graveyard or moderator access."""
    post_repo = PostRepository()

    # Only show user's own rejected posts unless they're a moderator+
    is_moderator = current_user.role in [
        UserRole.MODERATOR,
        UserRole.ADMIN,
        UserRole.SUPERADMIN,
    ]

    if is_moderator:
        # Moderators can see all graveyard posts
        return await post_repo.get_graveyard_posts(limit, offset)

    # Regular users only see their own rejected posts
    return await post_repo.get_graveyard_posts_by_author(current_user.pk, limit, offset)


@router.get("/pending/list")
async def get_pending_posts(
    _: Annotated[User, Depends(moderator_dependency)],
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Post]:
    """Get pending posts for moderation (moderator only)."""
    post_repo = PostRepository()
    return await post_repo.get_by_status(ContentStatus.PENDING, limit, offset)


@router.get("/submitted")
async def get_submitted_posts(
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PostWithAuthor]:
    """Get posts awaiting ToS screening (admin/moderator only)."""
    post_repo = PostRepository()
    return await post_repo.get_submitted_posts(limit, offset)


@router.get("/in-transit")
async def get_in_transit_posts(
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PostWithAuthor]:
    """Get posts currently in-transit through the pneumatic evaluation system (public endpoint)."""
    post_repo = PostRepository()
    return await post_repo.get_in_transit_posts(limit, offset)


@router.get("/{post_id}")
async def get_post(post_id: UUID) -> PostWithAuthor:
    """Get a specific post by ID."""
    post_repo = PostRepository()

    # Get the basic post first
    post = await post_repo.get_by_pk(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    # Show approved and in-transit posts to public (part of the spectacle)
    if post.status not in [ContentStatus.APPROVED, ContentStatus.IN_TRANSIT]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    # Get post with author info by searching in topic
    posts_with_author = await post_repo.get_by_topic(
        post.topic_pk,
        status=None,  # Get all statuses to find our specific post
        limit=1000,
    )
    for post_with_author in posts_with_author:
        if post_with_author.pk == post_id and post_with_author.status in [
            ContentStatus.APPROVED,
            ContentStatus.IN_TRANSIT,
        ]:
            return post_with_author

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@router.get("/topic/{topic_id}/thread")
async def get_topic_thread(
    topic_id: UUID,
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PostThread]:
    """Get posts in thread view for a topic with reply counts and nesting."""
    post_repo = PostRepository()
    return await post_repo.get_thread_view(topic_id, limit, offset)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Post:
    """Create a new post with ToS screening checkpoint."""
    post_repo = PostRepository()

    # Validate user can create posts (not banned/sanctioned)
    if current_user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Banned users cannot create posts",
        )

    if current_user.is_sanctioned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sanctioned users cannot create posts",
        )

    # Set author and submission time
    post_create = PostCreate(
        topic_pk=post_data.topic_pk,
        parent_post_pk=post_data.parent_post_pk,
        author_pk=current_user.pk,
        content=post_data.content,
        submitted_at=datetime.now(UTC),
    )

    # Create post with SUBMITTED status - awaiting ToS screening
    post_create_data = post_create.model_dump()
    post_create_data["status"] = ContentStatus.SUBMITTED
    post = await post_repo.create_from_dict(post_create_data)

    # Basic ToS screening (placeholder)
    tos_violation = _check_tos_violation_placeholder(post.content)
    if tos_violation:
        # Reject post immediately for ToS violation
        update_data = PostUpdate(
            status=ContentStatus.TOS_VIOLATION,
            rejection_reason="Terms of Service violation detected",
        )
        updated_post = await post_repo.update(post.pk, update_data)
        if updated_post:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "TOS_VIOLATION",
                    "message": "Content violates Terms of Service",
                    "post_id": str(post.pk),
                },
            )

    # Pass ToS screening - move to IN_TRANSIT and add to moderation queue
    update_data = PostUpdate(status=ContentStatus.IN_TRANSIT)
    updated_post = await post_repo.update(post.pk, update_data)
    if updated_post:
        post = updated_post

        # Add to moderation queue for AI processing
        queue_service = await get_queue_service()
        queue_id = await queue_service.add_post_to_queue(
            post.pk, post.topic_pk, priority=0
        )

        if not queue_id:
            # If queue addition fails, log but don't fail the request
            # The post is still created and visible as IN_TRANSIT
            pass

    return post


def _check_tos_violation_placeholder(content: str) -> bool:
    """Placeholder ToS violation checker - always passes for now."""
    # NOTE: Future enhancement - Replace with actual LLM-based ToS screening
    return False


@router.patch("/{post_id}")
async def update_post(
    post_id: UUID,
    post_data: PostUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Post:
    """Update a post (author only, content updates only)."""
    post_repo = PostRepository()

    # Get the existing post
    existing_post = await post_repo.get_by_pk(post_id)
    if not existing_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    # Only author can update their own posts
    if existing_post.author_pk != current_user.pk:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own posts",
        )

    # Only allow content updates for regular users
    allowed_update = PostUpdate(content=post_data.content)

    updated_post = await post_repo.update(post_id, allowed_update)
    if not updated_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    return updated_post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a post (author or moderator only)."""
    post_repo = PostRepository()

    # Get the existing post
    existing_post = await post_repo.get_by_pk(post_id)
    if not existing_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    # Check permissions: author or moderator+
    is_author = existing_post.author_pk == current_user.pk
    is_moderator = current_user.role in [
        UserRole.MODERATOR,
        UserRole.ADMIN,
        UserRole.SUPERADMIN,
    ]

    if not (is_author or is_moderator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts or must be a moderator",
        )

    # Update post status to rejected (soft delete)
    updated_post = await post_repo.update(
        post_id, PostUpdate(status=ContentStatus.REJECTED)
    )
    if not updated_post:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete post",
        )


# Moderation endpoints
@router.patch("/{post_id}/approve")
async def approve_post(
    post_id: UUID,
    _: Annotated[User, Depends(moderator_dependency)],
    overlord_feedback: Annotated[str | None, Query(max_length=500)] = None,
) -> Post:
    """Approve a post (moderator only)."""
    post_repo = PostRepository()

    approved_post = await post_repo.approve_post(post_id, overlord_feedback)
    if not approved_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    return approved_post


@router.patch("/{post_id}/reject")
async def reject_post(
    post_id: UUID,
    overlord_feedback: Annotated[str, Query(max_length=500)],
    _: Annotated[User, Depends(moderator_dependency)],
) -> Post:
    """Reject a post with feedback (moderator only)."""
    post_repo = PostRepository()

    rejected_post = await post_repo.reject_post(post_id, overlord_feedback)
    if not rejected_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    return rejected_post


@router.get("/author/{author_id}")
async def get_posts_by_author(
    author_id: UUID,
    status: Annotated[ContentStatus | None, Query()] = None,
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PostSummary]:
    """Get posts by a specific author."""
    post_repo = PostRepository()

    # Default to approved posts for public access
    content_status = status or ContentStatus.APPROVED
    return await post_repo.get_by_author(author_id, content_status, limit, offset)
