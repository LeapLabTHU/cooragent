import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket connection manager"""
    
    def __init__(self):
        # Store mapping from user ID to WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Establish WebSocket connection"""
        await websocket.accept()
        
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
        
        logger.info(f"User {user_id} established WebSocket connection, current connections: {len(self.active_connections[user_id])}")
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect WebSocket connection"""
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        
        logger.info(f"User {user_id} disconnected WebSocket connection")
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to specified user"""
        if user_id not in self.active_connections:
            logger.debug(f"User {user_id} has no active WebSocket connections")
            return False
        
        # Get all connections for the user
        connections = self.active_connections[user_id].copy()
        disconnected_connections = set()
        sent_count = 0
        
        for websocket in connections:
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
                sent_count += 1
                logger.debug(f"Successfully sent message to user {user_id} connection: {message}")
            except Exception as e:
                logger.warning(f"Failed to send message to user {user_id}: {e}")
                disconnected_connections.add(websocket)
        
        # Clean up disconnected connections
        if disconnected_connections:
            async with self._lock:
                if user_id in self.active_connections:
                    self.active_connections[user_id] -= disconnected_connections
                    if not self.active_connections[user_id]:
                        del self.active_connections[user_id]
        
        logger.debug(f"Message sending to user {user_id} completed, successfully sent to {sent_count} connections")
        return sent_count > 0
    
    async def broadcast_tool_start(self, user_id: str, tool_name: str, tool_params: dict = None):
        """Broadcast tool start usage message"""
        message = {
            "type": "tool_start",
            "name": tool_name,
            "timestamp": datetime.now().isoformat(),
            "params": tool_params or {}
        }
        
        logger.info(f"Broadcasting tool start message: user {user_id}, tool {tool_name}")
        success = await self.send_to_user(user_id, message)
        
        if not success:
            logger.warning(f"Tool start message sending failed: user {user_id}, tool {tool_name}")
        
        return success
    
    async def broadcast_tool_end(self, user_id: str, tool_name: str, success: bool = True, result: str = None):
        """Broadcast tool end usage message"""
        message = {
            "type": "tool_end",
            "name": tool_name,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "result": result
        }
        
        logger.info(f"Broadcasting tool end message: user {user_id}, tool {tool_name}, success: {success}")
        return await self.send_to_user(user_id, message)
    
    async def broadcast_tool_status(self, user_id: str, active_tools: list):
        """Broadcast current active tools status"""
        message = {
            "type": "tool_status",
            "active_tools": active_tools,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.debug(f"Broadcasting tool status message: user {user_id}, active tools: {active_tools}")
        return await self.send_to_user(user_id, message)
    
    def get_connected_users(self) -> list:
        """Get all connected user IDs"""
        return list(self.active_connections.keys())
    
    def get_connection_count(self, user_id: str) -> int:
        """Get connection count for specified user"""
        return len(self.active_connections.get(user_id, set()))
    
    def get_total_connections(self) -> int:
        """Get total connection count"""
        return sum(len(connections) for connections in self.active_connections.values())

# Global WebSocket manager instance
websocket_manager = WebSocketManager() 