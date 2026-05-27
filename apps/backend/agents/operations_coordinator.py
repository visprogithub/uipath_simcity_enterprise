"""
Operations Coordinator Agent (ARIA):
- Monitors queue depths and workflow routing
- Autonomously reroutes blocked workflows at level >= 2
- Rebalances throughput at level >= 3
"""
import logging
from typing import TYPE_CHECKING

from agents.base_agent import BaseAgent
from models.agent import Agent, AgentStatus
from models.building import BuildingStatus
from models.state import AlertSeverity, SimulationEventType
from models.workflow import WorkflowStatus

if TYPE_CHECKING:
    from simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)


class OperationsCoordinator(BaseAgent):
    def __init__(self, agent_model: Agent) -> None:
        super().__init__(agent_model)

    async def decide(self, engine: "SimulationEngine") -> None:
        self.reset_tick_actions()
        self.set_analyzing()

        buildings = engine.buildings
        workflows = engine.workflow_engine.workflows

        hospital = self.find_building(buildings, "hospital")
        pharmacy = self.find_building(buildings, "pharmacy")
        cloud = self.find_building(buildings, "cloud_datacenter")
        orch = self.find_building(buildings, "orchestration_center")
        backup = self.find_building(buildings, "backup_infra")

        acted = False

        # ─── Reroute blocked workflows ─────────────────────────────────────
        if self.can_act_autonomously(2) and self.has_action_budget():
            blocked_workflows = [
                w for w in workflows if w.status == WorkflowStatus.blocked
            ]

            for wf in blocked_workflows[:2]:  # handle up to 2 per tick
                if not self.has_action_budget():
                    break

                # Can we reroute via orchestration center?
                if orch and self.is_operational(orch):
                    wf.status = WorkflowStatus.rerouted
                    self.record_action(
                        f"Rerouted workflow {wf.id} ({wf.type.value}) via orchestration center"
                    )
                    self.emit_event(
                        engine,
                        SimulationEventType.agent_action,
                        {
                            "agentId": self.model.id,
                            "action": "reroute_workflow",
                            "workflowId": wf.id,
                            "via": "orchestration_center",
                        },
                    )
                    engine.trust_system.on_agent_action(self.model, True)
                    acted = True

        # ─── Hospital queue depth alert ────────────────────────────────────
        if hospital and hospital.queueDepth > 20 and self.has_action_budget():
            self.create_alert(
                engine,
                AlertSeverity.warning,
                f"Hospital queue depth critical: {hospital.queueDepth} pending workflows. "
                f"Additional staffing recommended.",
                building_id="hospital",
            )
            self.record_action(f"Alerted: Hospital queue depth at {hospital.queueDepth}")
            acted = True

        # ─── Pharmacy reroute when cloud degraded ─────────────────────────
        if (
            pharmacy
            and cloud
            and pharmacy.throughput < 50
            and cloud.status in (BuildingStatus.degraded, BuildingStatus.critical, BuildingStatus.offline)
            and backup
            and self.is_operational(backup)
            and self.can_act_autonomously(2)
            and self.has_action_budget()
        ):
            # Reroute pharmacy workflows through backup
            pharmacy_blocked = [
                w for w in workflows
                if (w.sourceId == "pharmacy" or w.destId == "pharmacy")
                and w.status == WorkflowStatus.blocked
            ]
            for wf in pharmacy_blocked[:1]:
                wf.status = WorkflowStatus.rerouted
                self.record_action(
                    f"Rerouted pharmacy workflow {wf.id} through backup_infra "
                    f"(cloud degraded)"
                )
                self.emit_event(
                    engine,
                    SimulationEventType.agent_action,
                    {
                        "agentId": self.model.id,
                        "action": "reroute_pharmacy_via_backup",
                        "workflowId": wf.id,
                    },
                )
                engine.trust_system.on_agent_action(self.model, True)
                acted = True

        # ─── Level 3: Rebalance throughput ────────────────────────────────
        if self.can_act_autonomously(3) and self.has_action_budget():
            # Find most congested building and boost its throughput slightly
            congested = max(buildings, key=lambda b: b.queueDepth, default=None)
            if congested and congested.queueDepth > 10 and congested.throughput < 90:
                old_tp = congested.throughput
                congested.throughput = min(100.0, congested.throughput + 3.0)
                congested.clamp()
                self.record_action(
                    f"Rebalanced throughput at {congested.name}: "
                    f"{old_tp:.0f}% -> {congested.throughput:.0f}%"
                )
                acted = True

        # ─── Level 1: Recommend rerouting ─────────────────────────────────
        if not self.can_act_autonomously(2) and self.can_act_autonomously(1):
            blocked_count = sum(1 for w in workflows if w.status == WorkflowStatus.blocked)
            if blocked_count > 3 and self.has_action_budget():
                self.create_alert(
                    engine,
                    AlertSeverity.warning,
                    f"ARIA recommends manual rerouting: {blocked_count} workflows blocked. "
                    f"Increase autonomy to level 2 to enable auto-rerouting.",
                )
                self.record_action(f"Recommended rerouting for {blocked_count} blocked workflows")
                acted = True

        if not acted:
            self.set_idle("Monitoring queue depths and workflow routing")
        else:
            self.set_status(AgentStatus.idle)
