"""InsightSQL for HPE GreenLake SAP Operations - FastAPI Application."""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.engine import init_db, close_db, get_pool
from app.db.seed import seed_all
from app.ws.manager import manager
from app.ingestion.router import router as ingestion_router
from app.incidents.router import router as incidents_router
from app.panels.router import router as panels_router
from app.topology.router import router as topology_router
from app.demo.router import router as demo_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup
    print("[APP] Starting InsightSQL...")
    pool = await init_db()
    await seed_all(pool)
    print("[APP] Ready.")
    yield
    # Shutdown
    from app.agent.llm import close_client
    await close_client()
    await close_db()
    print("[APP] Shut down.")


app = FastAPI(
    title="InsightSQL for HPE GreenLake SAP Operations",
    description="AI-driven self-healing dashboard for HPE GreenLake SAP workloads",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - use explicit origins (wildcard + credentials violates CORS spec)
_cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(ingestion_router, prefix="/api/webhooks", tags=["Ingestion"])
app.include_router(incidents_router, prefix="/api/incidents", tags=["Incidents"])
app.include_router(panels_router, prefix="/api/panels", tags=["Panels"])
app.include_router(topology_router, prefix="/api/topology", tags=["Topology"])
app.include_router(demo_router, prefix="/api/demo", tags=["Demo"])


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for client messages
            data = await websocket.receive_text()
            # Client can send pings or commands
            if data == "ping":
                await manager.send_personal(websocket, "pong", {})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        version = await conn.fetchval("SELECT version()")
    return {
        "status": "healthy",
        "database": "connected",
        "pg_version": version,
    }
