"""WebSocket connection manager for real-time dashboard updates."""

import json
import asyncio
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Manages WebSocket connections and broadcasts messages to all clients."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WS] Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message_type: str, payload: dict):
        """Broadcast a typed message to all connected clients."""
        message = {
            "type": message_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        message_json = json.dumps(message, default=str)

        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message_json)
            except (WebSocketDisconnect, RuntimeError):
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def send_personal(self, websocket: WebSocket, message_type: str, payload: dict):
        """Send a message to a specific client."""
        message = {
            "type": message_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await websocket.send_text(json.dumps(message, default=str))


# Singleton instance
manager = ConnectionManager()
