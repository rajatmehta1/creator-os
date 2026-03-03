"""WebSocket handler for real-time agent status updates."""

from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = structlog.get_logger()

websocket_router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections per creator_id."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, creator_id: str) -> None:
        await websocket.accept()
        if creator_id not in self.active_connections:
            self.active_connections[creator_id] = []
        self.active_connections[creator_id].append(websocket)
        logger.info("ws.connected", creator_id=creator_id)

    def disconnect(self, websocket: WebSocket, creator_id: str) -> None:
        if creator_id in self.active_connections:
            self.active_connections[creator_id].remove(websocket)
            if not self.active_connections[creator_id]:
                del self.active_connections[creator_id]
        logger.info("ws.disconnected", creator_id=creator_id)

    async def send_to_creator(self, creator_id: str, data: dict[str, Any]) -> None:
        """Send a message to all connections for a specific creator."""
        if creator_id in self.active_connections:
            for connection in self.active_connections[creator_id]:
                try:
                    await connection.send_json(data)
                except Exception:
                    logger.warning("ws.send_error", creator_id=creator_id)

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        for creator_id in self.active_connections:
            await self.send_to_creator(creator_id, data)


# Singleton connection manager
manager = ConnectionManager()


@websocket_router.websocket("/api/v1/ws/{creator_id}")
async def websocket_endpoint(websocket: WebSocket, creator_id: str) -> None:
    """WebSocket endpoint for real-time agent updates."""
    await manager.connect(websocket, creator_id)
    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_json()
            # Handle ping/pong or client commands
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, creator_id)
