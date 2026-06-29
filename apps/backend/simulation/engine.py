"""
SimulationEngine: the central orchestrator for Maestro City.
Runs the tick loop, coordinates all subsystems, and pushes state to subscribers.
"""
import asyncio
import logging
import os
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv

from models.agent import Agent, AgentStatus
from models.building import Building, BuildingStatus
from models.state import (
    Alert,
    AlertSeverity,
    GamePhase,
    SimulationEvent,
    SimulationEventType,
    SimulationMetrics,
    SimulationState,
    UiPathStatus,
)
from models.workflow import Workflow, WorkflowStatus
from models.actions import (
    ActivateFailoverAction,
    AcknowledgeAlertAction,
    PlayerAction,
    RestoreBuildingAction,
    SetAutonomyAction,
    SetStaffingAction,
    TriggerOutageAction,
    TriggerUiPathAction,
)
from simulation.city_config import (
    get_initial_agents,
    get_initial_buildings,
    get_initial_workflows,
    get_dependency_edges,
    get_scenario_definition,
)
from simulation.dependency_graph import DependencyGraph
from simulation.metrics_calculator import MetricsCalculator
from simulation.phase_detector import PhaseDetector
from simulation.resource_manager import ResourceManager
from simulation.trust_system import TrustSystem
from simulation.workflow_engine import WorkflowEngine
from orchestration.uipath_client import UiPathClient
from orchestration.escalation_router import EscalationRouter

load_dotenv()

logger = logging.getLogger(__name__)

TICK_INTERVAL = float(os.getenv("SIMULATION_TICK_INTERVAL", "1.0"))
MAX_EVENTS = 100
MAX_ALERTS = 50

# Each operational agent maps to its published UiPath coded agent (LangGraph + LLM
# Gateway). When an agent acts, the engine fires this release as a real Orchestrator
# job so the agent's reasoning runs on the platform. See uipath_client.invoke_coded_agent.
_AGENT_TYPE_TO_CODED_RELEASE = {
    "operations_coordinator": "aria",
    "incident_response": "sentinel",
    "compliance": "veritas",
    "communications": "echo",
    "executive_strategy": "apex",
}


class SimulationEngine:
    """
    The central simulation engine for Maestro City.
    Manages all subsystems and coordinates the per-tick update cycle.
    """

    def __init__(self, scenario_id: str = None) -> None:
        self.active_scenario_id: str = scenario_id or os.getenv("ACTIVE_SCENARIO", "healthcare")
        self.active_scenario = get_scenario_definition(self.active_scenario_id)

        self.tick_count: int = 0
        self.buildings: List[Building] = get_initial_buildings(self.active_scenario_id)
        self.agents: List[Agent] = get_initial_agents(self.active_scenario_id)
        self.alerts: List[Alert] = []
        self.events: List[SimulationEvent] = []
        self.phase: GamePhase = GamePhase.healthy
        self.metrics: SimulationMetrics = SimulationMetrics()

        # Subsystems
        self.dependency_graph = DependencyGraph()
        self.workflow_engine = WorkflowEngine()
        self.resource_manager = ResourceManager()
        self.trust_system = TrustSystem()
        self.metrics_calculator = MetricsCalculator()
        self.phase_detector = PhaseDetector()
        self.uipath_client = UiPathClient()
        self.escalation_router = EscalationRouter(self.uipath_client)

        # Initialize workflow engine with starting workflows
        self.workflow_engine.initialize(get_initial_workflows(self.active_scenario_id))

        # Build initial dependency graph
        self.dependency_graph.build_graph(self.buildings)

        # Agent instances (import here to avoid circular imports)
        self._agent_handlers: Dict[str, Any] = {}
        self._init_agent_handlers()

        # State push callbacks (WebSocket subscribers)
        self._state_callbacks: List[Callable] = []

        self.running: bool = False
        self._task: Optional[asyncio.Task] = None

        # Pause / auto-idle. The sim only advances (and only fires UiPath jobs) when not
        # paused AND someone is watching. get_viewer_count is wired in main.py to the live
        # WebSocket connection count, so the deployed app idles overnight with no viewers
        # instead of burning the tenant's robot minutes. None = always run (local dev).
        self.paused: bool = False
        self.get_viewer_count: Optional[Callable[[], int]] = None

        # ─── Reporting subsystems ─────────────────────────────────────────────
        from simulation.scenario_tracker import ScenarioTracker
        from simulation.after_action_reporter import AfterActionReporter
        from simulation.runbook_generator import RunbookGenerator
        from simulation.autonomy_calibrator import AutonomyCalibrator
        from orchestration.process_template_generator import ProcessTemplateGenerator

        self.scenario_tracker = ScenarioTracker()
        self.after_action_reporter = AfterActionReporter()
        self.runbook_generator = RunbookGenerator()
        self.autonomy_calibrator = AutonomyCalibrator()
        self.template_generator = ProcessTemplateGenerator()

        # Auto-start scenario tracking
        self.scenario_tracker.start_scenario()

    def _init_agent_handlers(self) -> None:
        """Initialize agent handler instances."""
        from agents.operations_coordinator import OperationsCoordinator
        from agents.incident_response import IncidentResponseAgent
        from agents.compliance_agent import ComplianceAgent
        from agents.communications_agent import CommunicationsAgent
        from agents.executive_strategy import ExecutiveStrategyAgent

        for agent in self.agents:
            if agent.type.value == "operations_coordinator":
                self._agent_handlers[agent.id] = OperationsCoordinator(agent)
            elif agent.type.value == "incident_response":
                self._agent_handlers[agent.id] = IncidentResponseAgent(agent)
            elif agent.type.value == "compliance":
                self._agent_handlers[agent.id] = ComplianceAgent(agent)
            elif agent.type.value == "communications":
                self._agent_handlers[agent.id] = CommunicationsAgent(agent)
            elif agent.type.value == "executive_strategy":
                self._agent_handlers[agent.id] = ExecutiveStrategyAgent(agent)

        logger.info(f"Initialized {len(self._agent_handlers)} agent handlers")

    async def start(self) -> None:
        """Start the simulation tick loop."""
        if self.running:
            logger.warning("SimulationEngine.start() called but already running")
            return

        self.running = True
        logger.info(f"Simulation engine starting (tick interval: {TICK_INTERVAL}s)")

        # Attempt UiPath authentication in background
        asyncio.create_task(self._init_uipath())

        while self.running:
            try:
                if self._should_tick():
                    await self._tick()
            except Exception as e:
                logger.error(f"Tick {self.tick_count} error: {e}", exc_info=True)
            await asyncio.sleep(TICK_INTERVAL)

    def _should_tick(self) -> bool:
        """Advance the sim only when not paused AND someone is watching.

        Auto-idles when no WebSocket client is connected so the live deployment doesn't
        fire UiPath jobs overnight with no viewers. When get_viewer_count is unset (local
        dev) the sim always runs.
        """
        if self.paused:
            return False
        if self.get_viewer_count is not None and self.get_viewer_count() <= 0:
            return False
        return True

    def set_paused(self, paused: bool) -> bool:
        """Pause/resume the live simulation (stops ticking and UiPath job firing)."""
        self.paused = bool(paused)
        logger.info(f"Simulation {'paused' if self.paused else 'resumed'} (by request)")
        return self.paused

    async def stop(self) -> None:
        """Stop the simulation."""
        self.running = False
        logger.info("Simulation engine stopped")

    async def _init_uipath(self) -> None:
        """Attempt UiPath authentication asynchronously."""
        try:
            success = await self.uipath_client.authenticate()
            if success:
                logger.info("UiPath integration active")
            else:
                logger.info("UiPath integration inactive (running in simulation-only mode)")
        except Exception as e:
            logger.error(f"UiPath initialization error: {e}")

    async def _tick(self) -> None:
        """Execute one simulation tick."""
        self.tick_count += 1

        # 1. Propagate dependency failures (cascade effects). The cascade is held back
        #    by PEOPLE — staffing + multi-agent coordination — so both feed in. (Failover
        #    revives the dead hub via recovery, but does not shield dependents here.)
        high_auton = sum(1 for a in self.agents if a.autonomyLevel >= 3)
        # One high-autonomy agent contributes a real slice (~1/N), scaling up as more
        # agents coordinate — a single agent helps but can't carry a recovery alone.
        coordination = high_auton / max(1, len(self.agents))
        affected = self.dependency_graph.propagate_failures(
            self.buildings, self.resource_manager.failover_active, coordination
        )
        if affected:
            self._generate_cascade_alerts(affected)

        # 2. Natural health recovery for non-failed buildings
        self._apply_health_recovery()

        # 3. Update workflow engine
        self.workflow_engine.tick(self.buildings, self.agents)

        # 4. Update resources
        self.resource_manager.tick(self.buildings, self.workflow_engine.workflows)

        # 5. Reset per-tick agent action counts
        for agent in self.agents:
            agent.actionsThisTick = 0

        # 6. Run agent decision loops
        for agent in self.agents:
            await self._run_agent(agent)

        # 7. Poll UiPath job statuses
        try:
            await self.uipath_client.poll_active_jobs()
            self.uipath_client.cleanup_jobs()
        except Exception as e:
            logger.debug(f"UiPath poll error (non-fatal): {e}")

        # 8. Recalculate metrics
        self.metrics = self.metrics_calculator.calculate(
            self.buildings,
            self.workflow_engine.workflows,
            self.agents,
            self.resource_manager,
            self.trust_system,
        )

        # 9. Trust system tick
        self.trust_system.tick(self.buildings, self.agents, self.metrics)

        # 10. Detect game phase
        self.phase = self.phase_detector.detect_phase(self.metrics, self.buildings)

        # 11. Generate system alerts
        self._generate_system_alerts()

        # 12. Trim history
        self.events = self.events[-MAX_EVENTS:]
        self.alerts = [a for a in self.alerts if not a.acknowledged][-MAX_ALERTS:]

        # 13. Record tick snapshot for reporting (before push so reports have current data)
        self.scenario_tracker.record_tick(
            self.tick_count,
            self.buildings,
            self.metrics,
            self.phase,
            self.workflow_engine.workflows,
            self.agents,
        )

        # 14. Push state to all WebSocket subscribers
        state = self._build_state()
        for cb in list(self._state_callbacks):
            try:
                await cb(state)
            except Exception as e:
                logger.debug(f"State callback error: {e}")

        if self.tick_count % 30 == 0:
            logger.info(
                f"Tick {self.tick_count}: phase={self.phase.value}, "
                f"stability={self.metrics.operationalStability:.0f}, "
                f"workflows={len(self.workflow_engine.workflows)}, "
                f"alerts={len(self.alerts)}"
            )

    def _apply_health_recovery(self) -> None:
        """Recover building health each tick.

        Recovery is the player's counter to cascade decay, so it must be a real,
        tunable lever — not a token 0.15/tick that the cascade (~1.8/tick per dead
        neighbour) trivially outpaces. Two things scale it:
          • Staffing: a fully-staffed building heals far faster than a skeleton crew,
            so the Staffing control actually moves the needle on collapse.
          • Failover: active backup infrastructure accelerates recovery grid-wide,
            so Activate Failover (player- or agent-triggered) visibly turns the tide.
        The data center is no longer excluded — as the dependency hub, leaving it
        unable to self-heal guaranteed an irreversible spiral.
        """
        failover = self.resource_manager.failover_active
        # Coordination: recovery scales with how many agents are operating at HIGH
        # autonomy (>=3). No single agent is a silver bullet — promoting one agent to
        # level 3 contributes a slice, not a cure. A real recovery needs several agents
        # coordinating AND staffing effort AND failover infrastructure stacked together.
        high_auton = sum(1 for a in self.agents if a.autonomyLevel >= 3)
        # One high-autonomy agent contributes a real slice (~1/N), scaling up as more
        # agents coordinate — a single agent helps but can't carry a recovery alone.
        coordination = high_auton / max(1, len(self.agents))
        capacity_factor = self.resource_manager.recoveryCapacity / 100.0

        for b in self.buildings:
            # ── Understaffing degrades health (makes Staffing a real lever) ──────
            # A building below half-staff cannot sustain operations and deteriorates.
            # This applies at ANY health level, so dropping staffing has immediate,
            # visible impact — buildings decline and eventually fail — while keeping
            # staffing up holds the line. This upstream effect was missing entirely,
            # which is why setting staffing to 0 previously did nothing.
            if b.staffingLevel < 50.0:
                understaff = (50.0 - b.staffingLevel) / 50.0   # 0..1
                b.health = max(0.0, b.health - understaff * 1.5)  # up to -1.5/tick at 0 staff
                b.clamp()

            if b.health >= 100:
                continue
            # A CRASHED building (critical/offline, <40% — including a failing hub that
            # receives no cascade decay and would otherwise self-heal) cannot be revived
            # by people alone. Failover infrastructure (or an explicit Restore) must bring
            # it back online; only then do staffing + coordination lift it. This is why no
            # amount of agent autonomy alone resurrects a downed data center.
            CRASH_THRESHOLD = 40.0
            if b.health < CRASH_THRESHOLD and not failover:
                continue
            # Recovery is a SUM of partial levers — each meaningful, none sufficient
            # alone. Beating a real multi-neighbour cascade (~1.5-3 health/tick of
            # decay) requires stacking most of them: that's the intended realism.
            rate = 0.06                                  # passive baseline
            rate += 0.28 * (b.staffingLevel / 100.0)     # staffing effort (depletes under stress)
            if failover:
                rate += 0.20                             # failover infrastructure (one ingredient)
            rate += 0.95 * coordination                  # multi-agent coordination
            rate *= 0.45 + (0.55 * capacity_factor)      # exhausted recovery teams heal slower
            b.health = min(100.0, b.health + rate)
            b.clamp()

    async def _run_agent(self, agent: Agent) -> None:
        """Run decision logic for one agent."""
        handler = self._agent_handlers.get(agent.id)
        if not handler:
            return

        try:
            await handler.decide(self)
            # When the agent acts, run its REASONING on UiPath as a real coded-agent job
            # (LangGraph + LLM Gateway). Non-blocking and cooldown-gated inside
            # invoke_coded_agent, so the tick loop never stalls on the round-trip.
            #
            # Direct mode: each agent fires its own coded-agent job here. Maestro mode: the
            # published Maestro orchestrator (MaestroCity_Orchestrator) fans out to all five
            # agents itself, so we skip here to avoid double-firing.
            if agent.actionsThisTick > 0 and self.uipath_client.orchestration_mode != "maestro":
                release = _AGENT_TYPE_TO_CODED_RELEASE.get(agent.type.value)
                if release:
                    await self.uipath_client.invoke_coded_agent(
                        release,
                        self._agent_reasoning_context(agent),
                        phase=self.phase.value,
                        tick=self.tick_count,
                    )
        except Exception as e:
            logger.error(f"Agent {agent.id} decision error: {e}", exc_info=True)
            agent.status = AgentStatus.idle
            agent.lastAction = f"Error: {str(e)[:80]}"

    def _agent_reasoning_context(self, agent: Agent) -> dict:
        """Compact, JSON-serializable crisis snapshot handed to a coded agent to reason over."""
        return {
            "agent": agent.name,
            "phase": self.phase.value,
            "tick": self.tick_count,
            "lastAction": agent.lastAction,
            "metrics": {
                "opStability": round(self.metrics.operationalStability, 1),
                "serviceAvailability": round(self.metrics.serviceAvailability, 1),
                "systemTrust": round(self.metrics.systemTrust, 1),
                "humanStrain": round(self.metrics.humanStrain, 1),
            },
            "degradedBuildings": [
                {"name": b.name, "health": round(b.health, 1), "status": b.status.value}
                for b in self.buildings if b.health < 90
            ][:6],
        }

    def _generate_cascade_alerts(self, affected_ids: List[str]) -> None:
        """Generate alerts when cascade propagation occurs."""
        if not affected_ids:
            return

        building_map = {b.id: b for b in self.buildings}
        critical_affected = [
            bid for bid in affected_ids
            if bid in building_map
            and building_map[bid].status in (BuildingStatus.critical, BuildingStatus.offline)
        ]

        if critical_affected:
            self.create_alert(
                severity=AlertSeverity.critical,
                message=(
                    f"CASCADE FAILURE: {len(critical_affected)} buildings critically impacted: "
                    + ", ".join(building_map[bid].name for bid in critical_affected[:3])
                ),
                agent_id=None,
            )
            self.emit_event(
                SimulationEventType.cascade_propagated,
                {
                    "affectedBuildings": affected_ids,
                    "criticalCount": len(critical_affected),
                    "tick": self.tick_count,
                },
            )

    def _generate_system_alerts(self) -> None:
        """Generate periodic system-level alerts based on metrics."""
        m = self.metrics

        # Low service availability
        if m.serviceAvailability < 30 and self.tick_count % 15 == 0:
            self.create_alert(
                AlertSeverity.critical,
                f"Service availability critically low: {m.serviceAvailability:.0f}%. "
                f"Patient care operations severely impacted.",
            )

        # Low operational stability
        if m.operationalStability < 25 and self.tick_count % 20 == 0:
            self.create_alert(
                AlertSeverity.critical,
                f"Operational stability at {m.operationalStability:.0f}%. "
                f"System collapse imminent without intervention.",
            )

    def apply_action(self, action: PlayerAction) -> Dict[str, Any]:
        """Apply a player action and surface any failure as a visible alert (fail-forward)."""
        result = self._dispatch_action(action)
        if isinstance(result, dict) and not result.get("success", True):
            self.create_alert(
                AlertSeverity.warning,
                f"Action failed: {result.get('error', 'unknown error')}",
            )
        return result

    def _dispatch_action(self, action: PlayerAction) -> Dict[str, Any]:
        """Dispatch player action to appropriate handler."""
        try:
            # Capture metrics snapshot before action for intervention tracking
            metrics_before = self.metrics

            if isinstance(action, TriggerOutageAction):
                result = self._handle_trigger_outage(action)
                if result.get("success"):
                    self.scenario_tracker.record_intervention(
                        action_type="trigger_outage",
                        description=f"Player triggered {action.severity} outage on building {action.buildingId}",
                        source="player",
                        current_metrics=metrics_before,
                        target_building_id=action.buildingId,
                    )
                return result
            elif isinstance(action, SetStaffingAction):
                result = self._handle_set_staffing(action)
                if result.get("success"):
                    self.scenario_tracker.record_intervention(
                        action_type="set_staffing",
                        description=f"Player set staffing level to {action.level} for building {action.buildingId}",
                        source="player",
                        current_metrics=metrics_before,
                        target_building_id=action.buildingId,
                    )
                return result
            elif isinstance(action, SetAutonomyAction):
                result = self._handle_set_autonomy(action)
                if result.get("success"):
                    target_id = action.agentId or "all"
                    self.scenario_tracker.record_intervention(
                        action_type="set_autonomy",
                        description=f"Player set autonomy level to {action.level} for agent {target_id}",
                        source="player",
                        current_metrics=metrics_before,
                        target_agent_id=action.agentId,
                    )
                return result
            elif isinstance(action, ActivateFailoverAction):
                result = self._handle_activate_failover(action)
                if result.get("success"):
                    self.scenario_tracker.record_intervention(
                        action_type="activate_failover",
                        description=f"Player activated failover for building {action.targetBuildingId}",
                        source="player",
                        current_metrics=metrics_before,
                        target_building_id=action.targetBuildingId,
                    )
                return result
            elif isinstance(action, AcknowledgeAlertAction):
                return self._handle_acknowledge_alert(action)
            elif isinstance(action, RestoreBuildingAction):
                result = self._handle_restore_building(action)
                if result.get("success"):
                    self.scenario_tracker.record_intervention(
                        action_type="restore_building",
                        description=f"Player initiated restoration of building {action.buildingId}",
                        source="player",
                        current_metrics=metrics_before,
                        target_building_id=action.buildingId,
                    )
                return result
            elif isinstance(action, TriggerUiPathAction):
                return self._handle_trigger_uipath(action)
            else:
                return {"success": False, "error": f"Unknown action type: {type(action).__name__}"}
        except Exception as e:
            logger.error(f"Action handler error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _handle_trigger_outage(self, action: TriggerOutageAction) -> Dict[str, Any]:
        b = next((b for b in self.buildings if b.id == action.buildingId), None)
        if not b:
            return {"success": False, "error": f"Building not found: {action.buildingId}"}

        if action.severity == "full":
            b.health = 0.0
            b.throughput = 0.0
        else:  # partial
            b.health = max(0.0, b.health * 0.35)
            b.throughput = max(0.0, b.throughput * 0.4)

        b.clamp()
        self.emit_event(
            SimulationEventType.outage_started,
            {
                "buildingId": action.buildingId,
                "buildingName": b.name,
                "severity": action.severity,
                "health": b.health,
                "triggeredByPlayer": True,
            },
        )
        self.create_alert(
            AlertSeverity.critical,
            f"PLAYER ACTION: {action.severity.upper()} outage triggered at {b.name}",
            building_id=action.buildingId,
        )
        logger.info(f"Outage triggered: {action.buildingId} ({action.severity})")
        return {"success": True, "error": None}

    def _handle_set_staffing(self, action: SetStaffingAction) -> Dict[str, Any]:
        b = next((b for b in self.buildings if b.id == action.buildingId), None)
        if not b:
            return {"success": False, "error": f"Building not found: {action.buildingId}"}

        self.resource_manager.apply_staffing_action(b, action.level)
        self.emit_event(
            SimulationEventType.player_action,
            {
                "action": "set_staffing",
                "buildingId": action.buildingId,
                "level": action.level,
            },
        )
        return {"success": True, "error": None}

    def _handle_set_autonomy(self, action: SetAutonomyAction) -> Dict[str, Any]:
        if action.agentId:
            agent = next((a for a in self.agents if a.id == action.agentId), None)
            if not agent:
                return {"success": False, "error": f"Agent not found: {action.agentId}"}
            agent.autonomyLevel = max(0, min(4, action.level))
        else:
            # Apply globally
            for agent in self.agents:
                agent.autonomyLevel = max(0, min(4, action.level))

        self.emit_event(
            SimulationEventType.player_action,
            {
                "action": "set_autonomy",
                "agentId": action.agentId,
                "level": action.level,
            },
        )
        return {"success": True, "error": None}

    def _handle_activate_failover(self, action: ActivateFailoverAction) -> Dict[str, Any]:
        b = next((b for b in self.buildings if b.id == action.targetBuildingId), None)
        # The backup building is identified by TYPE (every scenario has one "backup_infra"
        # slot), not by a fixed id — the id is scenario-specific (e.g. disaster_recovery_site).
        backup = next((bld for bld in self.buildings if bld.type == "backup_infra"), None)

        if not b:
            return {"success": False, "error": f"Building not found: {action.targetBuildingId}"}
        if not backup:
            return {"success": False, "error": "No backup infrastructure exists in this scenario"}

        # Activate failover: the backup spins up and visibly carries load, while the
        # failed building recovers as traffic reroutes through the backup.
        self.resource_manager.activate_failover()

        # Backup comes online and takes over — light it up "in the mix".
        backup.health = min(100.0, max(backup.health, 85.0))
        backup.throughput = min(100.0, max(backup.throughput, 80.0))
        backup.clamp()

        # Target building is stabilized because backup is serving traffic, but this
        # is not a full restore. The player still needs staffing and coordinated
        # autonomy increases to climb from degraded/critical back to healthy.
        target_floor = 34.0 + (backup.health * 0.10) + (b.staffingLevel * 0.05)
        throughput_floor = 42.0 + (backup.throughput * 0.12) + (b.staffingLevel * 0.06)
        b.health = max(b.health, min(52.0, target_floor))
        b.throughput = max(b.throughput, min(60.0, throughput_floor))
        b.clamp()

        self.emit_event(
            SimulationEventType.failover_activated,
            {
                "targetBuildingId": action.targetBuildingId,
                "backupHealth": backup.health,
                "triggeredByPlayer": True,
            },
        )
        self.create_alert(
            AlertSeverity.warning,
            f"PLAYER: Failover activated for {b.name}. Backup infrastructure engaged.",
            building_id=action.targetBuildingId,
        )
        logger.info(f"Player activated failover for {action.targetBuildingId}")
        return {"success": True, "error": None}

    def _handle_acknowledge_alert(self, action: AcknowledgeAlertAction) -> Dict[str, Any]:
        alert = next((a for a in self.alerts if a.id == action.alertId), None)
        if not alert:
            return {"success": False, "error": f"Alert not found: {action.alertId}"}

        alert.acknowledged = True
        return {"success": True, "error": None}

    def _handle_restore_building(self, action: RestoreBuildingAction) -> Dict[str, Any]:
        b = next((b for b in self.buildings if b.id == action.buildingId), None)
        if not b:
            return {"success": False, "error": f"Building not found: {action.buildingId}"}

        # Full restore: boost health and throughput significantly
        b.health = min(100.0, b.health + 60.0)
        b.throughput = min(100.0, b.throughput + 40.0)
        b.clamp()

        self.trust_system.on_successful_recovery(action.buildingId)
        self.emit_event(
            SimulationEventType.outage_recovered,
            {
                "buildingId": action.buildingId,
                "buildingName": b.name,
                "newHealth": b.health,
                "triggeredByPlayer": True,
            },
        )
        self.create_alert(
            AlertSeverity.info,
            f"PLAYER: {b.name} restoration initiated. Health boosted to {b.health:.0f}%.",
            building_id=action.buildingId,
        )
        logger.info(f"Player restored building {action.buildingId}")
        return {"success": True, "error": None}

    def _handle_trigger_uipath(self, action: TriggerUiPathAction) -> Dict[str, Any]:
        """Schedule a UiPath job to start (non-blocking)."""
        asyncio.create_task(
            self._async_trigger_uipath(action.processName, action.inputArgs)
        )
        return {"success": True, "error": None}

    async def _async_trigger_uipath(
        self, process_name: str, input_args: dict
    ) -> None:
        try:
            job = await self.uipath_client.start_job(process_name, input_args)
            if job:
                self.emit_event(
                    SimulationEventType.uipath_job_started,
                    {
                        "processName": process_name,
                        "jobId": job.id,
                        "triggeredByPlayer": True,
                    },
                )
                self.create_alert(
                    AlertSeverity.info,
                    f"UiPath job started: {process_name} (id={job.id})",
                )
        except Exception as e:
            logger.error(f"Failed to trigger UiPath job {process_name}: {e}")

    # ─── State Building ────────────────────────────────────────────────────────

    def _build_state(self) -> SimulationState:
        """Assemble the full SimulationState snapshot."""
        # Build UiPath status synchronously from cached data (avoid unawaited coroutine warning)
        uipath_status = UiPathStatus(
            connected=self.uipath_client.connected,
            activeJobs=list(self.uipath_client._active_jobs.values()),
            pendingApprovals=list(self.uipath_client._pending_approvals.values()),
            lastSync=time.time(),
            orchestrationMode=self.uipath_client.orchestration_mode,
            maestroCaseProcess=self.uipath_client.maestro_case_process,
        )

        return SimulationState(
            tick=self.tick_count,
            timestamp=time.time(),
            phase=self.phase,
            buildings=list(self.buildings),
            workflows=list(self.workflow_engine.workflows),
            agents=list(self.agents),
            metrics=self.metrics,
            alerts=list(self.alerts),
            recentEvents=list(self.events[-20:]),
            uipathStatus=uipath_status,
            failoverActive=self.resource_manager.failover_active,
            recoveryCapacity=self.resource_manager.recoveryCapacity,
        )

    # ─── Alert & Event Helpers ─────────────────────────────────────────────────

    def create_alert(
        self,
        severity: AlertSeverity,
        message: str,
        agent_id: Optional[str] = None,
        building_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> Alert:
        """Create and register a new alert."""
        alert = Alert(
            id=f"alert-{uuid.uuid4().hex[:8]}",
            severity=severity,
            message=message,
            buildingId=building_id,
            agentId=agent_id,
            workflowId=workflow_id,
            timestamp=time.time(),
            acknowledged=False,
        )
        self.alerts.append(alert)
        return alert

    def emit_event(
        self, event_type: SimulationEventType, data: Dict[str, Any]
    ) -> SimulationEvent:
        """Create and record a simulation event."""
        event = SimulationEvent(
            id=f"evt-{uuid.uuid4().hex[:8]}",
            type=event_type,
            data=data,
            timestamp=time.time(),
            tick=self.tick_count,
        )
        self.events.append(event)
        return event

    # ─── Subscription Management ──────────────────────────────────────────────

    def subscribe(self, callback: Callable) -> None:
        """Subscribe to state updates (called on every tick)."""
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)

    def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from state updates."""
        try:
            self._state_callbacks.remove(callback)
        except ValueError:
            pass

    def get_current_state(self) -> SimulationState:
        """Return current state snapshot synchronously."""
        return self._build_state()

    # ─── Report Generation ────────────────────────────────────────────────────

    def generate_after_action_report(self) -> dict:
        """Generate and return after-action report for the current scenario."""
        buildings_config = [{"id": b.id, "name": b.name} for b in self.buildings]
        return self.after_action_reporter.generate(
            self.scenario_tracker,
            buildings_config,
            vocabulary=self.active_scenario.vocabulary,
            scenario_name=self.active_scenario.name,
            uipath_processes=self.active_scenario.uipath_processes,
        )

    def generate_runbook(self) -> dict:
        """Generate operational runbook from current scenario data."""
        buildings_config = [{"id": b.id, "name": b.name} for b in self.buildings]
        return self.runbook_generator.generate(self.scenario_tracker, buildings_config)

    def generate_autonomy_calibration(self) -> dict:
        """Generate autonomy calibration certificate from current scenario."""
        return self.autonomy_calibrator.generate_calibration(self.scenario_tracker, self.agents)

    def generate_process_templates(self) -> dict:
        """Get UiPath Studio process templates for all 5 automation processes."""
        return self.template_generator.generate_all_templates()

    def reset_scenario(self) -> None:
        """Reset all buildings/agents to initial state and start a new scenario."""
        self.buildings = get_initial_buildings(self.active_scenario_id)
        self.agents = get_initial_agents(self.active_scenario_id)
        self.workflow_engine.initialize(get_initial_workflows(self.active_scenario_id))
        self.dependency_graph.build_graph(self.buildings)
        self.resource_manager = ResourceManager()
        self.trust_system = TrustSystem()
        self.metrics = SimulationMetrics()
        self.phase = GamePhase.healthy
        self.alerts.clear()
        self.events.clear()
        self.uipath_client.reset_simulation_run_state()
        self._init_agent_handlers()
        self.scenario_tracker.start_scenario()
        logger.info(f"Scenario reset — new scenario started (scenario={self.active_scenario_id})")

    def select_scenario(self, scenario_id: str) -> dict:
        """Switch to a different scenario, resetting all simulation state."""
        from scenarios.registry import get_scenario as _registry_get
        try:
            new_scenario = _registry_get(scenario_id)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        self.active_scenario_id = scenario_id
        self.active_scenario = new_scenario

        # Reset all state to the new scenario
        self.buildings = get_initial_buildings(scenario_id)
        self.agents = get_initial_agents(scenario_id)
        self.workflow_engine.initialize(get_initial_workflows(scenario_id))
        self.dependency_graph.build_graph(self.buildings)
        self.resource_manager = ResourceManager()
        self.trust_system = TrustSystem()
        self.metrics = SimulationMetrics()
        self.phase = GamePhase.healthy
        self.alerts.clear()
        self.events.clear()
        self.uipath_client.reset_simulation_run_state()
        self._init_agent_handlers()
        self.scenario_tracker.start_scenario()

        logger.info(f"Scenario switched to: {scenario_id} ({new_scenario.name})")
        return {
            "success": True,
            "scenarioId": scenario_id,
            "scenarioName": new_scenario.name,
        }


# ─── Singleton ────────────────────────────────────────────────────────────────
engine = SimulationEngine()
