"""
WebSocket manager for real-time simulation state streaming.
Handles multiple client connections, pushes state every tick,
and receives player actions from clients.
"""
import json
import logging
import time
from typing import Any, Dict, List, Set

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from models.actions import (
    AcknowledgeAlertAction,
    ActivateFailoverAction,
    RestoreBuildingAction,
    SetAutonomyAction,
    SetStaffingAction,
    TriggerOutageAction,
    TriggerUiPathAction,
)
from models.state import SimulationState

logger = logging.getLogger(__name__)

_ACTION_MAP = {
    "trigger_outage": TriggerOutageAction,
    "set_staffing": SetStaffingAction,
    "set_autonomy": SetAutonomyAction,
    "activate_failover": ActivateFailoverAction,
    "acknowledge_alert": AcknowledgeAlertAction,
    "restore_building": RestoreBuildingAction,
    "trigger_uipath": TriggerUiPathAction,
}


class ConnectionManager:
    """Manages all active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.info(
            f"WebSocket client connected. Total connections: {len(self._connections)}"
        )

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        logger.info(
            f"WebSocket client disconnected. Total connections: {len(self._connections)}"
        )

    async def broadcast_state(self, state: SimulationState) -> None:
        """
        Broadcast full simulation state to all connected clients.
        Called by the engine on every tick via the subscription callback.
        """
        if not self._connections:
            return

        # Serialize once, send to all
        try:
            message = json.dumps({
                "type": "state",
                "payload": state.model_dump(),
            })
        except Exception as e:
            logger.error(f"State serialization error: {e}")
            return

        disconnected: List[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

    async def send_ack(
        self,
        websocket: WebSocket,
        action_id: str,
        success: bool,
        error: str = None,
    ) -> None:
        """Send an acknowledgement message to a specific client."""
        try:
            msg: Dict[str, Any] = {
                "type": "ack",
                "actionId": action_id,
                "success": success,
            }
            if error:
                msg["error"] = error
            await websocket.send_text(json.dumps(msg))
        except Exception as e:
            logger.debug(f"Failed to send ack: {e}")

    async def send_error(self, websocket: WebSocket, message: str) -> None:
        """Send an error message to a specific client."""
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": message,
                "timestamp": time.time(),
            }))
        except Exception:
            pass

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Singleton connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Main WebSocket endpoint handler.
    Registers as a subscriber to the engine's state updates,
    and handles incoming action messages from clients.
    """
    from simulation.engine import engine

    await manager.connect(websocket)

    # Send current state immediately on connect
    try:
        current_state = engine.get_current_state()
        await websocket.send_text(json.dumps({
            "type": "state",
            "payload": current_state.model_dump(),
        }))
    except Exception as e:
        logger.warning(f"Failed to send initial state: {e}")

    # Register for automatic state pushes via engine subscription
    async def state_push_callback(state: SimulationState) -> None:
        await manager.broadcast_state(state)

    # Only register the global broadcast once (not per-connection)
    # The manager.broadcast_state handles all connections
    # We use a per-connection listener approach for receive loop

    try:
        while True:
            # Wait for messages from this client
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                break

            # Parse incoming message
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_error(websocket, "Invalid JSON")
                continue

            msg_type = msg.get("type")

            if msg_type == "action":
                await _handle_action_message(websocket, msg, engine)
            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
            else:
                await manager.send_error(websocket, f"Unknown message type: {msg_type}")

    except Exception as e:
        logger.debug(f"WebSocket handler exception: {e}")
    finally:
        manager.disconnect(websocket)


async def _handle_action_message(
    websocket: WebSocket, msg: Dict[str, Any], engine: Any
) -> None:
    """Parse and apply a player action received via WebSocket."""
    action_id = msg.get("actionId", f"action-{time.time()}")
    payload = msg.get("payload", {})

    if not payload:
        await manager.send_ack(websocket, action_id, False, "Missing payload")
        return

    action_type = payload.get("type")
    if not action_type:
        await manager.send_ack(websocket, action_id, False, "Missing action type in payload")
        return

    action_cls = _ACTION_MAP.get(action_type)
    if not action_cls:
        await manager.send_ack(
            websocket, action_id, False,
            f"Unknown action type: {action_type}"
        )
        return

    try:
        action = action_cls(**payload)
    except ValidationError as e:
        await manager.send_ack(websocket, action_id, False, str(e))
        return
    except Exception as e:
        await manager.send_ack(websocket, action_id, False, f"Parse error: {str(e)}")
        return

    result = engine.apply_action(action)
    success = result.get("success", False)
    error = result.get("error")

    await manager.send_ack(websocket, action_id, success, error)

    if success:
        logger.info(f"WS action applied: {action_type}")
    else:
        logger.warning(f"WS action failed: {action_type} — {error}")
