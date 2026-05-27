"""
Base agent class with shared utilities for all AI agents.
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

from models.agent import Agent, AgentStatus
from models.building import Building, BuildingStatus
from models.state import Alert, AlertSeverity, SimulationEvent, SimulationEventType

if TYPE_CHECKING:
    from simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)

MAX_ACTIONS_PER_TICK = 3


class BaseAgent(ABC):
    """
    Abstract base for all AI agents in the simulation.
    Provides utility methods, rate limiting, and action recording.
    """

    def __init__(self, agent_model: Agent) -> None:
        self.model = agent_model
        self._action_count: int = 0

    @abstractmethod
    async def decide(self, engine: "SimulationEngine") -> None:
        """Make decisions and modify engine state. Called once per tick."""
        pass

    # ─── Utility Methods ──────────────────────────────────────────────────────

    def find_building(
        self, buildings: List[Building], building_id: str
    ) -> Optional[Building]:
        return next((b for b in buildings if b.id == building_id), None)

    def find_building_by_type(
        self, buildings: List[Building], building_type: str
    ) -> Optional[Building]:
        return next((b for b in buildings if b.type.value == building_type), None)

    def find_most_degraded(self, buildings: List[Building]) -> Optional[Building]:
        """Return the building with the lowest health (excluding fully operational)."""
        candidates = [b for b in buildings if b.health < 90]
        if not candidates:
            return None
        return min(candidates, key=lambda b: b.health)

    def find_most_critical(self, buildings: List[Building]) -> Optional[Building]:
        """Return the most critical (lowest health) building."""
        if not buildings:
            return None
        return min(buildings, key=lambda b: b.health)

    def can_act_autonomously(self, required_level: int) -> bool:
        """Check if this agent has sufficient autonomy level to act autonomously."""
        return self.model.autonomyLevel >= required_level

    def has_action_budget(self) -> bool:
        """Check if this agent can still act this tick."""
        return self._action_count < MAX_ACTIONS_PER_TICK

    def reset_tick_actions(self) -> None:
        """Reset per-tick action counter."""
        self._action_count = 0
        self.model.actionsThisTick = 0

    def record_action(self, action_desc: str) -> None:
        """Record that an action was taken."""
        self._action_count += 1
        self.model.actionsThisTick = self._action_count
        self.model.lastAction = action_desc
        self.model.lastActionAt = time.time()
        self.model.status = AgentStatus.acting

    def set_status(self, status: AgentStatus) -> None:
        self.model.status = status

    def set_idle(self, last_action: Optional[str] = None) -> None:
        self.model.status = AgentStatus.idle
        if last_action:
            self.model.lastAction = last_action

    def set_analyzing(self) -> None:
        self.model.status = AgentStatus.analyzing

    # ─── Alert & Event Helpers ────────────────────────────────────────────────

    def create_alert(
        self,
        engine: "SimulationEngine",
        severity: AlertSeverity,
        message: str,
        building_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> Alert:
        """Create and register an alert via the engine."""
        alert = engine.create_alert(
            severity=severity,
            message=message,
            agent_id=self.model.id,
            building_id=building_id,
            workflow_id=workflow_id,
        )
        return alert

    def emit_event(
        self,
        engine: "SimulationEngine",
        event_type: SimulationEventType,
        data: dict,
    ) -> SimulationEvent:
        """Emit a simulation event via the engine."""
        return engine.emit_event(event_type, data)

    # ─── Building State Checks ────────────────────────────────────────────────

    def is_operational(self, b: Optional[Building]) -> bool:
        return b is not None and b.status == BuildingStatus.operational

    def is_degraded(self, b: Optional[Building]) -> bool:
        return b is not None and b.status == BuildingStatus.degraded

    def is_critical_or_worse(self, b: Optional[Building]) -> bool:
        return b is not None and b.status in (
            BuildingStatus.critical, BuildingStatus.offline
        )

    def count_degraded(self, buildings: List[Building]) -> int:
        return sum(
            1 for b in buildings
            if b.status in (BuildingStatus.degraded, BuildingStatus.critical, BuildingStatus.offline)
        )
