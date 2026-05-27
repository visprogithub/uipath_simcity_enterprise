"""
REST API routes for Maestro City backend.
"""
import logging
import time
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from models.actions import (
    AcknowledgeAlertAction,
    ActivateFailoverAction,
    PlayerAction,
    RestoreBuildingAction,
    SetAutonomyAction,
    SetStaffingAction,
    TriggerOutageAction,
    TriggerUiPathAction,
)
from models.state import SimulationState, UiPathStatus
from orchestration.webhook_handler import WebhookHandler
from simulation.engine import engine

logger = logging.getLogger(__name__)

router = APIRouter()
webhook_handler = WebhookHandler()


# ─── Health & State ────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Returns current health status of the simulation backend."""
    return {
        "status": "ok",
        "tick": engine.tick_count,
        "phase": engine.phase.value if engine.phase else "unknown",
        "running": engine.running,
        "timestamp": time.time(),
    }


@router.get("/api/state", response_model=SimulationState)
async def get_state() -> SimulationState:
    """Returns the current full simulation state snapshot."""
    return engine.get_current_state()


@router.get("/api/history")
async def get_history() -> Dict[str, Any]:
    """Returns the last 100 simulation events."""
    return {
        "events": [e.model_dump() for e in engine.events[-100:]],
        "total": len(engine.events),
        "tick": engine.tick_count,
    }


@router.get("/api/replay")
async def get_replay() -> Dict[str, Any]:
    """Returns the full event log for timeline replay."""
    return {
        "events": [e.model_dump() for e in engine.events],
        "total": len(engine.events),
        "tick": engine.tick_count,
        "phase": engine.phase.value if engine.phase else "unknown",
        "timestamp": time.time(),
    }


# ─── Player Actions ────────────────────────────────────────────────────────────

@router.post("/api/actions")
async def apply_action(request: Request) -> Dict[str, Any]:
    """
    Apply a player action to the simulation.
    Accepts a discriminated union PlayerAction based on the 'type' field.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    action_type = body.get("type")
    if not action_type:
        raise HTTPException(status_code=400, detail="Missing 'type' field in action")

    # Deserialize into the correct action type
    action_map = {
        "trigger_outage": TriggerOutageAction,
        "set_staffing": SetStaffingAction,
        "set_autonomy": SetAutonomyAction,
        "activate_failover": ActivateFailoverAction,
        "acknowledge_alert": AcknowledgeAlertAction,
        "restore_building": RestoreBuildingAction,
        "trigger_uipath": TriggerUiPathAction,
    }

    action_cls = action_map.get(action_type)
    if not action_cls:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action type: {action_type}. "
                   f"Valid types: {list(action_map.keys())}",
        )

    try:
        action = action_cls(**body)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Action validation error: {str(e)}")

    result = engine.apply_action(action)

    if not result.get("success"):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result.get("error", "Unknown error")},
        )

    return {"success": True, "error": None, "tick": engine.tick_count}


# ─── UiPath Integration ────────────────────────────────────────────────────────

@router.get("/api/uipath/status")
async def get_uipath_status() -> Dict[str, Any]:
    """Returns UiPath integration status."""
    status = await engine.uipath_client.get_status()
    return status.model_dump()


@router.post("/api/uipath/trigger")
async def trigger_uipath_process(request: Request) -> Dict[str, Any]:
    """Manually trigger a UiPath automation process."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    process_name = body.get("processName")
    if not process_name:
        raise HTTPException(status_code=400, detail="Missing 'processName' field")

    input_args = body.get("inputArgs", {})

    job = await engine.uipath_client.start_job(process_name, input_args)
    if not job:
        raise HTTPException(status_code=500, detail=f"Failed to start process: {process_name}")

    from models.state import SimulationEventType
    engine.emit_event(
        SimulationEventType.uipath_job_started,
        {
            "processName": process_name,
            "jobId": job.id,
            "triggeredManually": True,
        },
    )

    return {
        "success": True,
        "job": job.model_dump(),
        "tick": engine.tick_count,
    }


@router.post("/api/uipath/webhook")
async def receive_uipath_webhook(
    request: Request, background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Receive and process UiPath webhook events.
    Validates HMAC signature if configured.
    """
    payload_bytes = await request.body()
    signature_header = request.headers.get("X-UiPath-Signature", "")

    # Validate signature
    if not webhook_handler.validate_signature(payload_bytes, signature_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        import json
        payload = json.loads(payload_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON webhook payload")

    # Process webhook in background to return quickly
    background_tasks.add_task(
        _process_webhook_background, payload
    )

    return {"received": True, "timestamp": time.time()}


async def _process_webhook_background(payload: dict) -> None:
    """Process webhook in background task."""
    try:
        result = await webhook_handler.process_webhook(payload, engine)
        logger.info(f"Webhook processed: {result}")
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
