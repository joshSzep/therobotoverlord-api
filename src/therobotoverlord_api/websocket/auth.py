"""WebSocket authentication and authorization."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import HTTPException
from fastapi import Query
from fastapi import WebSocket
from fastapi import status

from therobotoverlord_api.auth.jwt_service import JWTService
from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.repositories.user import UserRepository

logger = logging.getLogger(__name__)


async def authenticate_websocket(
    websocket: WebSocket,
    token: Annotated[str | None, Query()] = None,
) -> User:
    """Authenticate WebSocket connection using JWT token."""
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        raise HTTPException(status_code=401, detail="Authentication token required")

    try:
        # Decode JWT token using JWTService
        jwt_service = JWTService()
        token_claims = jwt_service.decode_token(token)
        
        if not token_claims:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = UUID(str(token_claims.sub))

        # Get user from database
        async with get_db_connection() as conn:
            user_repo = UserRepository(conn)
            user = await user_repo.get_by_id(user_id)

            if not user:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
                raise HTTPException(status_code=401, detail="User not found")

            if not user.is_active:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Account inactive")
                raise HTTPException(status_code=401, detail="Account inactive")

            return user

    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        raise HTTPException(status_code=401, detail="Authentication failed") from None


def require_websocket_role(*allowed_roles: str):
    """Decorator to require specific roles for WebSocket connections."""
    def decorator(func):
        async def wrapper(websocket: WebSocket, user: User, *args, **kwargs):
            if user.role not in allowed_roles:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason=f"Insufficient permissions. Required: {allowed_roles}"
                )
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(websocket, user, *args, **kwargs)
        return wrapper
    return decorator


async def authorize_channel_access(user: User, channel: str) -> bool:
    """Check if user has access to a specific WebSocket channel."""
    # Channel access rules
    channel_rules = {
        # Public channels - all authenticated users
        "announcements": lambda _: True,
        "system_status": lambda _: True,
        
        # User-specific channels
        f"user_{user.pk}": lambda u: u.pk == user.pk,
        f"user_{user.pk}_queue": lambda u: u.pk == user.pk,
        f"user_{user.pk}_notifications": lambda u: u.pk == user.pk,
        
        # Role-based channels
        "moderation": lambda u: u.role in ["MODERATOR", "ADMIN", "SUPERADMIN"],
        "admin": lambda u: u.role in ["ADMIN", "SUPERADMIN"],
        "superadmin": lambda u: u.role == "SUPERADMIN",
        
        # Topic-based channels (format: topic_{topic_id})
        # Queue-based channels (format: queue_{queue_type})
    }
    
    # Check direct channel rules
    if channel in channel_rules:
        return channel_rules[channel](user)
    
    # Check pattern-based rules
    if channel.startswith("topic_"):
        # All authenticated users can subscribe to topic updates
        return True
    
    if channel.startswith("queue_"):
        # Users can subscribe to queue updates if they have content in that queue
        # This would require checking the database - for now, allow all authenticated users
        return True
    
    if channel.startswith("user_") and channel != f"user_{user.pk}":
        # Users can only access their own user channels
        return False
    
    # Default: deny access to unknown channels
    logger.warning(f"Access denied to unknown channel: {channel} for user {user.pk}")
    return False
