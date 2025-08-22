"""WebSocket event handlers and broadcasters."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from therobotoverlord_api.websocket.manager import WebSocketManager
from therobotoverlord_api.websocket.models import ContentModerationUpdate
from therobotoverlord_api.websocket.models import LoyaltyScoreUpdate
from therobotoverlord_api.websocket.models import OverlordChatMessage
from therobotoverlord_api.websocket.models import QueuePositionUpdate
from therobotoverlord_api.websocket.models import SystemAnnouncement
from therobotoverlord_api.websocket.models import UserActivityUpdate
from therobotoverlord_api.websocket.models import WebSocketEventType
from therobotoverlord_api.websocket.models import WebSocketMessage

logger = logging.getLogger(__name__)


class WebSocketEventBroadcaster:
    """Handles broadcasting of real-time events via WebSocket."""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
    
    async def broadcast_queue_position_update(
        self,
        user_id: UUID,
        queue_type: str,
        old_position: int | None,
        new_position: int,
        estimated_wait_time: int | None = None,
        total_queue_size: int | None = None,
    ):
        """Broadcast queue position update to user."""
        try:
            update_data = QueuePositionUpdate(
                queue_type=queue_type,
                old_position=old_position,
                new_position=new_position,
                estimated_wait_time=estimated_wait_time,
                total_queue_size=total_queue_size or 0,
            )
            
            message = WebSocketMessage(
                event_type=WebSocketEventType.QUEUE_POSITION_UPDATE,
                data=update_data.model_dump(),
                user_id=user_id,
            )
            
            # Send to specific user
            await self.websocket_manager.send_to_user(user_id, message)
            
            # Also broadcast to queue channel for general queue status
            await self.websocket_manager.broadcast_to_channel(
                f"queue_{queue_type}",
                WebSocketMessage(
                    event_type=WebSocketEventType.QUEUE_STATUS_CHANGE,
                    data={
                        "queue_type": queue_type,
                        "total_size": total_queue_size,
                        "updated_at": datetime.utcnow().isoformat(),
                    },
                )
            )
            
            logger.info(f"Broadcasted queue position update for user {user_id}: {old_position} -> {new_position}")
        except Exception as e:
            logger.exception(f"Failed to broadcast queue position update for user {user_id}: {e}")
    
    async def broadcast_content_moderation_result(
        self,
        user_id: UUID,
        content_id: UUID,
        content_type: str,
        decision: str,
        feedback: str | None = None,
        tags: list[str] | None = None,
        loyalty_score_change: int | None = None,
    ):
        """Broadcast content moderation decision to user."""
        try:
            moderation_data = ContentModerationUpdate(
                content_id=content_id,
                content_type=content_type,
                decision=decision,
                feedback=feedback,
                tags=tags or [],
                loyalty_score_change=loyalty_score_change,
            )
            
            event_type = (
                WebSocketEventType.CONTENT_APPROVED if decision == "approved"
                else WebSocketEventType.CONTENT_REJECTED if decision == "rejected"
                else WebSocketEventType.CONTENT_FLAGGED
            )
            
            message = WebSocketMessage(
                event_type=event_type,
                data=moderation_data.model_dump(),
                user_id=user_id,
            )
            
            await self.websocket_manager.send_to_user(user_id, message)
            
            logger.info(f"Broadcasted moderation result for user {user_id}, content {content_id}: {decision}")
        except Exception as e:
            logger.exception(f"Failed to broadcast moderation result for user {user_id}, content {content_id}: {e}")
    
    async def broadcast_overlord_chat_message(
        self,
        user_id: UUID,
        message_text: str,
        response_to: UUID | None = None,
        conversation_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Broadcast Overlord chat message to user."""
        chat_data = OverlordChatMessage(
            message=message_text,
            response_to=response_to,
            conversation_id=conversation_id,
            metadata=metadata or {},
        )
        
        message = WebSocketMessage(
            event_type=WebSocketEventType.OVERLORD_MESSAGE,
            data=chat_data.model_dump(),
            user_id=user_id,
        )
        
        await self.websocket_manager.send_to_user(user_id, message)
        
        logger.info(f"Broadcasted Overlord message to user {user_id}")
    
    async def broadcast_loyalty_score_update(
        self,
        user_id: UUID,
        old_score: int,
        new_score: int,
        reason: str,
        old_rank: str | None = None,
        new_rank: str | None = None,
    ):
        """Broadcast loyalty score update to user."""
        loyalty_data = LoyaltyScoreUpdate(
            old_score=old_score,
            new_score=new_score,
            change=new_score - old_score,
            reason=reason,
            old_rank=old_rank,
            new_rank=new_rank,
        )
        
        message = WebSocketMessage(
            event_type=WebSocketEventType.LOYALTY_SCORE_UPDATE,
            data=loyalty_data.model_dump(),
            user_id=user_id,
        )
        
        await self.websocket_manager.send_to_user(user_id, message)
        
        # If rank changed, send separate rank change event
        if old_rank != new_rank and new_rank:
            rank_message = WebSocketMessage(
                event_type=WebSocketEventType.RANK_CHANGE,
                data={
                    "old_rank": old_rank,
                    "new_rank": new_rank,
                    "loyalty_score": new_score,
                },
                user_id=user_id,
            )
            await self.websocket_manager.send_to_user(user_id, rank_message)
        
        logger.info(f"Broadcasted loyalty score update for user {user_id}: {old_score} -> {new_score}")
    
    async def broadcast_system_announcement(
        self,
        title: str,
        message: str,
        announcement_type: str = "general",
        priority: str = "normal",
        expires_at: datetime | None = None,
        target_user_ids: list[UUID] | None = None,
    ):
        """Broadcast system announcement."""
        announcement_data = SystemAnnouncement(
            title=title,
            message=message,
            announcement_type=announcement_type,
            priority=priority,
            expires_at=expires_at,
        )
        
        ws_message = WebSocketMessage(
            event_type=WebSocketEventType.ANNOUNCEMENT,
            data=announcement_data.model_dump(),
        )
        
        if target_user_ids:
            # Send to specific users
            for user_id in target_user_ids:
                await self.websocket_manager.send_to_user(user_id, ws_message)
        else:
            # Broadcast to all users
            await self.websocket_manager.broadcast_to_channel("announcements", ws_message)
        
        logger.info(f"Broadcasted system announcement: {title}")
    
    async def broadcast_user_activity_update(
        self,
        user_id: UUID,
        username: str,
        status: str,
        last_seen: datetime | None = None,
    ):
        """Broadcast user activity status update."""
        activity_data = UserActivityUpdate(
            user_id=user_id,
            username=username,
            status=status,
            last_seen=last_seen,
        )
        
        event_type = (
            WebSocketEventType.USER_ONLINE if status == "online"
            else WebSocketEventType.USER_OFFLINE
        )
        
        message = WebSocketMessage(
            event_type=event_type,
            data=activity_data.model_dump(),
        )
        
        # Broadcast to all users (for activity indicators)
        await self.websocket_manager.broadcast_to_channel("user_activity", message)
        
        logger.info(f"Broadcasted activity update for user {user_id}: {status}")
    
    async def broadcast_badge_earned(
        self,
        user_id: UUID,
        badge_id: UUID,
        badge_name: str,
        badge_description: str,
        badge_icon: str | None = None,
    ):
        """Broadcast badge earned notification to user."""
        message = WebSocketMessage(
            event_type=WebSocketEventType.BADGE_EARNED,
            data={
                "badge_id": str(badge_id),
                "badge_name": badge_name,
                "badge_description": badge_description,
                "badge_icon": badge_icon,
                "earned_at": datetime.utcnow().isoformat(),
            },
            user_id=user_id,
        )
        
        await self.websocket_manager.send_to_user(user_id, message)
        
        logger.info(f"Broadcasted badge earned for user {user_id}: {badge_name}")
    
    async def broadcast_maintenance_mode(
        self,
        enabled: bool,
        message: str | None = None,
        estimated_duration: int | None = None,
    ):
        """Broadcast maintenance mode status to all users."""
        ws_message = WebSocketMessage(
            event_type=WebSocketEventType.MAINTENANCE_MODE,
            data={
                "enabled": enabled,
                "message": message,
                "estimated_duration": estimated_duration,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        
        await self.websocket_manager.broadcast_to_all(ws_message)
        
        logger.info(f"Broadcasted maintenance mode: {'enabled' if enabled else 'disabled'}")


# Global event broadcaster instance
event_broadcaster: WebSocketEventBroadcaster | None = None


def get_event_broadcaster(websocket_manager: WebSocketManager) -> WebSocketEventBroadcaster:
    """Get or create event broadcaster instance."""
    global event_broadcaster
    if event_broadcaster is None:
        event_broadcaster = WebSocketEventBroadcaster(websocket_manager)
    return event_broadcaster
