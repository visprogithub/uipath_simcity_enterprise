"""
Maestro City — FastAPI application entry point.
Starts the simulation engine as a background task and serves REST + WebSocket APIs.
"""
import asyncio
import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from api.websocket import manager, websocket_endpoint
from api.enterprise_systems import router as enterprise_router
from api.agent_builder import router as agent_builder_router
from api.coding_agent import router as coding_agent_router
from api.approvals import router as approvals_router
from api.scenario_generator import router as scenario_generator_router
from simulation.engine import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: start/stop the simulation engine."""
    # Register the WebSocket manager as a state subscriber
    engine.subscribe(manager.broadcast_state)

    # Auto-idle the sim when no browser is connected, so the live deployment doesn't
    # tick (and fire UiPath jobs) overnight with no viewers.
    engine.get_viewer_count = lambda: manager.connection_count

    # Start the simulation engine in the background
    sim_task = asyncio.create_task(engine.start())
    logger.info("Maestro City simulation engine started")

    yield

    # Cleanup on shutdown
    await engine.stop()
    sim_task.cancel()
    try:
        await sim_task
    except asyncio.CancelledError:
        pass
    logger.info("Maestro City simulation engine stopped")


app = FastAPI(
    title="Maestro City API",
    description="Real-time enterprise healthcare operations simulation engine",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins for hackathon demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(router)
app.include_router(enterprise_router)
app.include_router(agent_builder_router)
app.include_router(coding_agent_router)
app.include_router(approvals_router)
app.include_router(scenario_generator_router)


# WebSocket endpoint
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket_endpoint(websocket)
