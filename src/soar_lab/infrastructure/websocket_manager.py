#!/usr/bin/env python3
"""
SOAR Ransomware Lab - WebSocket Connection Manager (Infrastructure)
Manages WebSocket connections for real-time log streaming.
This is infrastructure - handles WebSocket protocol details.
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Any, Dict

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections - implements WebSocketManager port."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: Any) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: Any) -> None:
        """Remove a WebSocket connection."""
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            logger.warning(f"WebSocket connection not found in active connections")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        await websocket.send_text(message)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all active connections."""
        import json
        message_str = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except WebSocketDisconnect:
                self.active_connections.remove(connection)
            except Exception as e:
                logger.warning(f"Error sending message to connection: {e}")
                self.active_connections.remove(connection)
