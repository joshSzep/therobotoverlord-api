"""WebSocket connection manager for real-time updates."""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID
from uuid import uuid4

from fastapi import WebSocket
from fastapi import WebSocketDisconnect

from therobotoverlord_api.websocket.models import WebSocketConnectionInfo
from therobotoverlord_api.websocket.models import WebSocketEventType
from therobotoverlord_api.websocket.models import WebSocketMessage

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        # Active connections: connection_id -> WebSocket
        self.active_connections: dict[str, WebSocket] = {}
        
        # User connections: user_id -> list[connection_id]
        self.user_connections: dict[UUID, list[str]] = {}
        
        # Connection info: connection_id -> WebSocketConnectionInfo
        self.connection_info: dict[str, WebSocketConnectionInfo] = {}
        
        # Subscriptions: channel -> list[connection_id]
        self.subscriptions: dict[str, list[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: UUID) -> str:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        connection_id = str(uuid4())
        now = datetime.utcnow()
        
        # Store connection
        self.active_connections[connection_id] = websocket
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(connection_id)
        
        # Store connection info
        self.connection_info[connection_id] = WebSocketConnectionInfo(
            connection_id=connection_id,
            user_id=user_id,
            connected_at=now,
            last_ping=now,
        )
        
        logger.info(f"WebSocket connection established: {connection_id} for user {user_id}")
        
        # Send connection confirmation
        await self.send_to_connection(
            connection_id,
            WebSocketMessage(
                event_type=WebSocketEventType.CONNECT,
                data={"connection_id": connection_id, "status": "connected"},
                user_id=user_id,
            )
        )
        
        return connection_id
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id not in self.active_connections:
            return
        
        connection_info = self.connection_info.get(connection_id)
        if connection_info:
            user_id = connection_info.user_id
            
            # Remove from user connections
            if user_id in self.user_connections:
                self.user_connections[user_id].remove(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Remove from subscriptions
            for channel, subscribers in self.subscriptions.items():
                if connection_id in subscribers:
                    subscribers.remove(connection_id)
            
            # Clean up empty subscription channels
            self.subscriptions = {
                channel: subscribers 
                for channel, subscribers in self.subscriptions.items() 
                if subscribers
            }
            
            logger.info(f"WebSocket connection closed: {connection_id} for user {user_id}")
        
        # Remove connection
        self.active_connections.pop(connection_id, None)
        self.connection_info.pop(connection_id, None)
    
    async def send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send message to a specific connection."""
        websocket = self.active_connections.get(connection_id)
        if not websocket:
            return
        
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            self.disconnect(connection_id)
    
    async def send_to_user(self, user_id: UUID, message: WebSocketMessage):
        """Send message to all connections for a specific user."""
        connection_ids = self.user_connections.get(user_id, [])
        for connection_id in connection_ids.copy():  # Copy to avoid modification during iteration
            await self.send_to_connection(connection_id, message)
    
    async def broadcast_to_channel(self, channel: str, message: WebSocketMessage):
        """Broadcast message to all subscribers of a channel."""
        connection_ids = self.subscriptions.get(channel, [])
        for connection_id in connection_ids.copy():  # Copy to avoid modification during iteration
            await self.send_to_connection(connection_id, message)
    
    async def broadcast_to_all(self, message: WebSocketMessage):
        """Broadcast message to all active connections."""
        for connection_id in list(self.active_connections.keys()):
            await self.send_to_connection(connection_id, message)
    
    def subscribe_to_channel(self, connection_id: str, channel: str):
        """Subscribe a connection to a channel."""
        if connection_id not in self.active_connections:
            return
        
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []
        
        if connection_id not in self.subscriptions[channel]:
            self.subscriptions[channel].append(connection_id)
        
        # Update connection info
        if connection_id in self.connection_info:
            if channel not in self.connection_info[connection_id].subscriptions:
                self.connection_info[connection_id].subscriptions.append(channel)
        
        logger.info(f"Connection {connection_id} subscribed to channel {channel}")
    
    def unsubscribe_from_channel(self, connection_id: str, channel: str):
        """Unsubscribe a connection from a channel."""
        if channel in self.subscriptions and connection_id in self.subscriptions[channel]:
            self.subscriptions[channel].remove(connection_id)
            
            if not self.subscriptions[channel]:
                del self.subscriptions[channel]
        
        # Update connection info
        if connection_id in self.connection_info:
            if channel in self.connection_info[connection_id].subscriptions:
                self.connection_info[connection_id].subscriptions.remove(channel)
        
        logger.info(f"Connection {connection_id} unsubscribed from channel {channel}")
    
    def get_user_connections(self, user_id: UUID) -> list[str]:
        """Get all connection IDs for a user."""
        return self.user_connections.get(user_id, [])
    
    def get_channel_subscribers(self, channel: str) -> list[str]:
        """Get all connection IDs subscribed to a channel."""
        return self.subscriptions.get(channel, [])
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)
    
    def get_user_count(self) -> int:
        """Get total number of connected users."""
        return len(self.user_connections)
    
    def is_user_online(self, user_id: UUID) -> bool:
        """Check if a user has any active connections."""
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0
    
    async def handle_ping(self, connection_id: str):
        """Handle ping from client to keep connection alive."""
        if connection_id in self.connection_info:
            self.connection_info[connection_id].last_ping = datetime.utcnow()
            
            # Send pong response
            await self.send_to_connection(
                connection_id,
                WebSocketMessage(
                    event_type=WebSocketEventType.CONNECT,
                    data={"type": "pong"},
                )
            )


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


async def get_websocket_manager() -> WebSocketManager:
    """Dependency injection for WebSocket manager."""
    return websocket_manager
