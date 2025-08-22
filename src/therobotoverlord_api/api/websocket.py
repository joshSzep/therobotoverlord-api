"""WebSocket API endpoints for real-time connections."""

import json
import logging
from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.websocket.auth import authenticate_websocket
from therobotoverlord_api.websocket.auth import authorize_channel_access
from therobotoverlord_api.websocket.events import get_event_broadcaster
from therobotoverlord_api.websocket.manager import get_websocket_manager
from therobotoverlord_api.websocket.manager import WebSocketManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    websocket_manager: Annotated[WebSocketManager, Depends(get_websocket_manager)],
):
    """Main WebSocket connection endpoint."""
    connection_id = None
    user = None
    
    try:
        # Authenticate the WebSocket connection
        user = await authenticate_websocket(websocket)
        
        # Establish connection
        connection_id = await websocket_manager.connect(websocket, user.pk)
        
        # Auto-subscribe to user-specific channels
        websocket_manager.subscribe_to_channel(connection_id, f"user_{user.pk}")
        websocket_manager.subscribe_to_channel(connection_id, f"user_{user.pk}_queue")
        websocket_manager.subscribe_to_channel(connection_id, f"user_{user.pk}_notifications")
        websocket_manager.subscribe_to_channel(connection_id, "announcements")
        websocket_manager.subscribe_to_channel(connection_id, "system_status")
        
        # Broadcast user online status
        event_broadcaster = get_event_broadcaster(websocket_manager)
        await event_broadcaster.broadcast_user_activity_update(
            user_id=user.pk,
            username=user.username,
            status="online"
        )
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await handle_websocket_message(
                    connection_id, user, message, websocket_manager
                )
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from connection {connection_id}")
            except Exception as e:
                logger.error(f"Error handling message from {connection_id}: {e}")
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        if connection_id:
            websocket_manager.disconnect(connection_id)
        
        if user:
            # Broadcast user offline status
            event_broadcaster = get_event_broadcaster(websocket_manager)
            await event_broadcaster.broadcast_user_activity_update(
                user_id=user.pk,
                username=user.username,
                status="offline"
            )


async def handle_websocket_message(
    connection_id: str,
    user: User,
    message: dict,
    websocket_manager: WebSocketManager,
):
    """Handle incoming WebSocket messages from clients."""
    message_type = message.get("type")
    
    if message_type == "ping":
        await websocket_manager.handle_ping(connection_id)
    
    elif message_type == "subscribe":
        channel = message.get("channel")
        if channel and await authorize_channel_access(user, channel):
            websocket_manager.subscribe_to_channel(connection_id, channel)
            logger.info(f"User {user.pk} subscribed to channel {channel}")
        else:
            logger.warning(f"User {user.pk} denied access to channel {channel}")
    
    elif message_type == "unsubscribe":
        channel = message.get("channel")
        if channel:
            websocket_manager.unsubscribe_from_channel(connection_id, channel)
            logger.info(f"User {user.pk} unsubscribed from channel {channel}")
    
    elif message_type == "chat_message":
        # Handle Overlord chat messages
        await handle_chat_message(connection_id, user, message, websocket_manager)
    
    else:
        logger.warning(f"Unknown message type: {message_type} from user {user.pk}")


async def handle_chat_message(
    connection_id: str,
    user: User,
    message: dict,
    websocket_manager: WebSocketManager,
):
    """Handle chat messages sent to the Overlord."""
    chat_text = message.get("message", "").strip()
    if not chat_text:
        return
    
    # TODO: Integrate with AI/LLM service for Overlord responses
    # For now, send a placeholder response
    
    event_broadcaster = get_event_broadcaster(websocket_manager)
    
    # Echo the user's message back (temporary)
    await event_broadcaster.broadcast_overlord_chat_message(
        user_id=user.pk,
        message_text=f"I received your message: '{chat_text}'. The AI integration is coming soon!",
        conversation_id=message.get("conversation_id"),
        metadata={
            "user_message": chat_text,
            "response_type": "placeholder"
        }
    )
    
    logger.info(f"Handled chat message from user {user.pk}: {chat_text[:50]}...")


@router.get("/stats")
async def get_websocket_stats(
    websocket_manager: Annotated[WebSocketManager, Depends(get_websocket_manager)],
):
    """Get WebSocket connection statistics."""
    return {
        "active_connections": websocket_manager.get_connection_count(),
        "connected_users": websocket_manager.get_user_count(),
        "channels": len(websocket_manager.subscriptions),
        "total_subscriptions": sum(
            len(subscribers) for subscribers in websocket_manager.subscriptions.values()
        ),
    }
