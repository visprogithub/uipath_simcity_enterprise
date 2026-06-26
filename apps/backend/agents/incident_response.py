"""
Incident Response Agent (SENTINEL):
- Detects outage patterns, cascade starts, queue overflow
- At autonomy >= 2: auto-triggers UiPath escalation workflows
- At autonomy >= 3: recommends failover for operator activation
"""
import logging
from typing import TYPE_CHECKING

from agents.base_agent import BaseAgent
from models.agent import Agent, AgentStatus
from models.building import BuildingStatus
from models.state import AlertSeverity, SimulationEventType

if TYPE_CHECKING:
    from simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)


class IncidentResponseAgent(BaseAgent):
    def __init__(self, agent_model: Agent) -> None:
        super().__init__(agent_model)
        self._last_cloud_alert_tick: int = -20  # prevent spam
        self._last_crisis_tick: int = -20

    async def decide(self, engine: "SimulationEngine") -> None:
        self.reset_tick_actions()
        self.set_analyzing()

        buildings = engine.buildings
        tick = engine.tick_count

        # Resolve by TYPE (consistent across every scenario, incl. custom), not by id.
        cloud = self.find_building_by_type(buildings, "cloud_datacenter")
        hospital = self.find_building_by_type(buildings, "hospital")
        pharmacy = self.find_building_by_type(buildings, "pharmacy")
        backup = self.find_building_by_type(buildings, "backup_infra")

        acted = False

        # ─── Cloud datacenter health monitor ──────────────────────────────
        if cloud and cloud.health < 60 and (tick - self._last_cloud_alert_tick) >= 10:
            self._last_cloud_alert_tick = tick

            self.create_alert(
                engine,
                AlertSeverity.critical,
                f"{self.model.name}: {cloud.name} health critical at {cloud.health:.0f}%. "
                f"Cascade failure risk elevated. Immediate intervention required.",
                building_id=cloud.id,
            )
            self.record_action(
                f"Detected {cloud.name} health drop to {cloud.health:.0f}%"
            )
            acted = True

            # Level >= 2: trigger UiPath escalation
            if self.can_act_autonomously(2) and self.has_action_budget():
                job = await engine.uipath_client.start_job(
                    "Incident_Escalation",
                    {
                        "buildingId": cloud.id,
                        "health": cloud.health,
                        "severity": "critical",
                        "tick": tick,
                    },
                )
                if job:
                    self.emit_event(
                        engine,
                        SimulationEventType.uipath_job_started,
                        {
                            "agentId": self.model.id,
                            "processName": "Incident_Escalation",
                            "jobId": job.id,
                            "trigger": "cloud_health_critical",
                        },
                    )
                    self.record_action(
                        f"Triggered UiPath Incident_Escalation job (cloud health: {cloud.health:.0f}%)"
                    )
                engine.trust_system.on_agent_action(self.model, True)

            # Level >= 3: recommend failover without changing backup capacity or reporting activation.
            if self.can_act_autonomously(3) and backup and self.has_action_budget():
                self.emit_event(
                    engine,
                    SimulationEventType.agent_action,
                    {
                        "agentId": self.model.id,
                        "action": "recommend_failover",
                        "targetBuildingId": backup.id,
                        "reason": "cloud_health_critical",
                        "cloudHealth": cloud.health,
                    },
                )
                self.record_action(
                    f"Failover RECOMMENDED (cloud: {cloud.health:.0f}%) — operator action required"
                )
                engine.trust_system.on_agent_action(self.model, True)

        # ─── Multiple degraded buildings (cascade detection) ───────────────
        degraded_buildings = [
            b for b in buildings
            if b.status in (BuildingStatus.degraded, BuildingStatus.critical, BuildingStatus.offline)
        ]

        if len(degraded_buildings) >= 3 and (tick - self._last_crisis_tick) >= 15:
            self._last_crisis_tick = tick

            degraded_names = [b.name for b in degraded_buildings[:3]]
            self.create_alert(
                engine,
                AlertSeverity.critical,
                f"{self.model.name}: CRISIS DETECTED — {len(degraded_buildings)} buildings degraded simultaneously: "
                f"{', '.join(degraded_names)}. Cascade propagation in progress.",
            )
            acted = True

            if self.has_action_budget():
                self.emit_event(
                    engine,
                    SimulationEventType.cascade_propagated,
                    {
                        "agentId": self.model.id,
                        "affectedBuildings": [b.id for b in degraded_buildings],
                        "tick": tick,
                    },
                )
                engine.trust_system.on_cascade_event()

            # Level >= 2: trigger Crisis_Response job
            if self.can_act_autonomously(2) and self.has_action_budget():
                job = await engine.uipath_client.start_job(
                    "Crisis_Response",
                    {
                        "affectedBuildings": [b.id for b in degraded_buildings],
                        "severity": "critical",
                        "tick": tick,
                        "phase": engine.phase.value if engine.phase else "crisis",
                    },
                )
                if job:
                    self.emit_event(
                        engine,
                        SimulationEventType.uipath_job_started,
                        {
                            "agentId": self.model.id,
                            "processName": "Crisis_Response",
                            "jobId": job.id,
                        },
                    )
                    self.record_action(
                        f"Triggered UiPath Crisis_Response — {len(degraded_buildings)} buildings affected"
                    )

            # Notify executive strategy agent (move it to escalating status)
            exec_agent = next(
                (a for a in engine.agents if a.id == "exec_strategy"), None
            )
            if exec_agent:
                exec_agent.status = AgentStatus.escalating

        # ─── Hospital/pharmacy offline alert ──────────────────────────────
        for critical_bld in [hospital, pharmacy]:
            if critical_bld and critical_bld.status == BuildingStatus.offline:
                if self.has_action_budget():
                    self.create_alert(
                        engine,
                        AlertSeverity.critical,
                        f"{self.model.name}: {critical_bld.name} is OFFLINE. "
                        f"Critical services severely impacted. Emergency protocol activated.",
                        building_id=critical_bld.id,
                    )
                    self.record_action(f"Critical alert: {critical_bld.name} offline")
                    acted = True

        if not acted:
            self.set_idle("All systems nominal — monitoring for incidents")
        else:
            self.set_status(AgentStatus.idle)
