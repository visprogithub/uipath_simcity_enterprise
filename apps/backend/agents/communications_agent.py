"""
Communications Agent (ECHO):
- Manages alert deduplication and escalation
- At autonomy >= 2: auto-acknowledges resolved alerts
- Regulates alert storms (max 3 new alerts per tick)
"""
import logging
from typing import TYPE_CHECKING, Dict, List, Set

from agents.base_agent import BaseAgent
from models.agent import Agent, AgentStatus
from models.building import BuildingStatus
from models.state import Alert, AlertSeverity, SimulationEventType

if TYPE_CHECKING:
    from simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)

MAX_NEW_ALERTS_PER_TICK = 3
DEDUP_WINDOW = 5  # ticks


class CommunicationsAgent(BaseAgent):
    def __init__(self, agent_model: Agent) -> None:
        super().__init__(agent_model)
        self._seen_messages: Dict[str, int] = {}  # message_key -> last_tick
        self._new_alerts_this_tick: int = 0

    async def decide(self, engine: "SimulationEngine") -> None:
        self.reset_tick_actions()
        self._new_alerts_this_tick = 0
        self.set_analyzing()

        buildings = engine.buildings
        alerts = engine.alerts
        tick = engine.tick_count
        acted = False

        comms_hub = self.find_building_by_type(buildings, "comms_hub")

        # ─── Alert deduplication ──────────────────────────────────────────
        self._deduplicate_alerts(engine, tick)

        # ─── Comms hub degraded: escalate critical alerts ─────────────────
        if comms_hub and comms_hub.status in (BuildingStatus.degraded, BuildingStatus.critical):
            # Upgrade warning alerts to critical when comms are down
            for alert in alerts:
                if alert.severity == AlertSeverity.warning and not alert.acknowledged:
                    alert.severity = AlertSeverity.critical
            if self.has_action_budget():
                self.record_action(
                    f"Escalated alert severity: comms hub at {comms_hub.health:.0f}%"
                )
                acted = True

        # ─── Unacknowledged critical alerts ───────────────────────────────
        unacked_critical = [
            a for a in alerts
            if a.severity == AlertSeverity.critical and not a.acknowledged
        ]

        if len(unacked_critical) > 5:
            if self.has_action_budget():
                # Level >= 2: trigger notification blast
                if self.can_act_autonomously(2):
                    job = await engine.uipath_client.start_job(
                        "Notification_Blast",
                        {
                            "alertCount": len(unacked_critical),
                            "alertIds": [a.id for a in unacked_critical[:5]],
                            "tick": tick,
                        },
                    )
                    if job:
                        self.emit_event(
                            engine,
                            SimulationEventType.uipath_job_started,
                            {
                                "agentId": self.model.id,
                                "processName": "Notification_Blast",
                                "jobId": job.id,
                                "alertCount": len(unacked_critical),
                            },
                        )
                        self.record_action(
                            f"Triggered Notification_Blast for {len(unacked_critical)} unacknowledged critical alerts"
                        )
                        acted = True
                else:
                    self.create_alert(
                        engine,
                        AlertSeverity.warning,
                        f"{self.model.name}: {len(unacked_critical)} unacknowledged critical alerts. "
                        f"Increase autonomy to level 2 to enable auto-notification blast.",
                    )
                    acted = True

        # ─── Auto-acknowledge resolved alerts ─────────────────────────────
        if self.can_act_autonomously(2) and self.has_action_budget():
            resolved_count = 0
            for alert in list(alerts):
                if alert.acknowledged:
                    continue
                # If the referenced building is now operational, auto-ack
                if alert.buildingId and not alert.acknowledged:
                    b = self.find_building(buildings, alert.buildingId)
                    if b and b.status == BuildingStatus.operational and b.health > 80:
                        alert.acknowledged = True
                        resolved_count += 1

            if resolved_count > 0:
                self.record_action(
                    f"Auto-acknowledged {resolved_count} resolved alerts (buildings restored)"
                )
                acted = True

        # ─── Alert storm regulation ────────────────────────────────────────
        # Engine will call _can_emit_alert before adding alerts when this agent is active
        # We track the count here for regulation
        total_alerts = len(alerts)
        if total_alerts > 40:
            # Compress duplicate alerts by severity
            self._compress_alerts(engine)
            if self.has_action_budget():
                self.record_action(f"Compressed alert queue: {total_alerts} -> {len(engine.alerts)}")
                acted = True

        if not acted:
            self.set_idle("Alerts synchronized — monitoring communications")
        else:
            self.set_status(AgentStatus.idle)

    def _deduplicate_alerts(self, engine: "SimulationEngine", tick: int) -> None:
        """Remove near-duplicate alerts based on message similarity."""
        seen: Dict[str, Alert] = {}
        to_remove: Set[str] = set()

        for alert in engine.alerts:
            # Create dedup key from first 60 chars of message + building_id
            key = f"{alert.message[:60]}|{alert.buildingId or ''}"
            if key in seen:
                existing = seen[key]
                # Keep the more severe / more recent one
                if alert.severity == AlertSeverity.critical and existing.severity != AlertSeverity.critical:
                    to_remove.add(existing.id)
                    seen[key] = alert
                elif existing.timestamp > alert.timestamp:
                    to_remove.add(alert.id)
                else:
                    to_remove.add(existing.id)
                    seen[key] = alert
            else:
                seen[key] = alert

        if to_remove:
            engine.alerts = [a for a in engine.alerts if a.id not in to_remove]

    def _compress_alerts(self, engine: "SimulationEngine") -> None:
        """Keep only most recent/severe alerts when the queue is overflowing."""
        # Sort by severity (critical first) then by timestamp (newest first)
        severity_order = {AlertSeverity.critical: 0, AlertSeverity.warning: 1, AlertSeverity.info: 2}
        engine.alerts.sort(
            key=lambda a: (severity_order.get(a.severity, 2), -a.timestamp)
        )
        # Keep top 30
        engine.alerts = engine.alerts[:30]

    def can_emit_alert(self) -> bool:
        """Check if we can emit another alert this tick (rate limiting)."""
        if self._new_alerts_this_tick < MAX_NEW_ALERTS_PER_TICK:
            self._new_alerts_this_tick += 1
            return True
        return False
