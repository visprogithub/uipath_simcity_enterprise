"""
Executive Strategy Agent (APEX):
- Monitors KPI trends over last 10 ticks
- At autonomy >= 1: recommends autonomy level changes
- At autonomy >= 3: auto-adjusts other agents' autonomy levels
"""
import logging
from collections import deque
from typing import TYPE_CHECKING, Deque, List, Optional

from agents.base_agent import BaseAgent
from models.agent import Agent, AgentStatus
from models.state import AlertSeverity, SimulationEventType

if TYPE_CHECKING:
    from simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)

TREND_WINDOW = 10
MIN_TICKS_BETWEEN_ADJUSTMENTS = 8


class ExecutiveStrategyAgent(BaseAgent):
    def __init__(self, agent_model: Agent) -> None:
        super().__init__(agent_model)
        self._stability_history: Deque[float] = deque(maxlen=TREND_WINDOW)
        self._strain_history: Deque[float] = deque(maxlen=TREND_WINDOW)
        self._trust_history: Deque[float] = deque(maxlen=TREND_WINDOW)
        self._last_adjustment_tick: int = -MIN_TICKS_BETWEEN_ADJUSTMENTS
        self._last_staffing_alert_tick: int = -20
        self._last_trust_alert_tick: int = -15

    async def decide(self, engine: "SimulationEngine") -> None:
        self.reset_tick_actions()
        self.set_analyzing()

        metrics = engine.metrics
        tick = engine.tick_count
        agents = engine.agents
        acted = False

        # Track KPI history
        self._stability_history.append(metrics.operationalStability)
        self._strain_history.append(metrics.humanStrain)
        self._trust_history.append(metrics.systemTrust)

        stability_trend = self._compute_trend(self._stability_history)
        can_adjust = (tick - self._last_adjustment_tick) >= MIN_TICKS_BETWEEN_ADJUSTMENTS

        # ─── Stability trending down: boost incident response autonomy ────
        if (
            len(self._stability_history) >= 5
            and stability_trend < -2.0  # declining 2+ pts per tick avg
            and self.can_act_autonomously(1)
            and self.has_action_budget()
        ):
            incident_agent = next((a for a in agents if a.id == "incident_resp"), None)

            if incident_agent:
                if self.can_act_autonomously(3) and can_adjust:
                    # Auto-increase incident response autonomy
                    old_level = incident_agent.autonomyLevel
                    incident_agent.autonomyLevel = min(4, incident_agent.autonomyLevel + 1)
                    self._last_adjustment_tick = tick
                    self.record_action(
                        f"AUTO: Increased {incident_agent.name} autonomy {old_level} → {incident_agent.autonomyLevel} "
                        f"(stability declining at {stability_trend:.1f}/tick)"
                    )
                    self.emit_event(
                        engine,
                        SimulationEventType.agent_action,
                        {
                            "agentId": self.model.id,
                            "action": "increase_autonomy",
                            "targetAgentId": "incident_resp",
                            "newLevel": incident_agent.autonomyLevel,
                            "reason": "stability_decline",
                        },
                    )
                    engine.trust_system.on_agent_action(self.model, True)
                    acted = True
                else:
                    # Recommend increasing autonomy
                    self.create_alert(
                        engine,
                        AlertSeverity.warning,
                        f"{self.model.name}: Stability declining ({stability_trend:.1f}/tick). "
                        f"Recommend increasing {incident_agent.name} autonomy to level "
                        f"{min(4, incident_agent.autonomyLevel + 1)}.",
                    )
                    self.record_action(
                        f"Recommended autonomy increase for {incident_agent.name} (trend: {stability_trend:.1f}/tick)"
                    )
                    acted = True

        # ─── High human strain: recommend staffing ─────────────────────────
        if (
            metrics.humanStrain > 80
            and (tick - self._last_staffing_alert_tick) >= 20
            and self.has_action_budget()
        ):
            self._last_staffing_alert_tick = tick

            if self.can_act_autonomously(3):
                # Auto-trigger Emergency Staffing
                job = await engine.uipath_client.start_job(
                    "Emergency_Staffing",
                    {
                        "humanStrain": metrics.humanStrain,
                        "tick": tick,
                        "phase": engine.phase.value if engine.phase else "unknown",
                    },
                )
                if job:
                    self.emit_event(
                        engine,
                        SimulationEventType.uipath_job_started,
                        {
                            "agentId": self.model.id,
                            "processName": "Emergency_Staffing",
                            "jobId": job.id,
                            "humanStrain": metrics.humanStrain,
                        },
                    )
                    self.emit_event(
                        engine,
                        SimulationEventType.staffing_overload,
                        {
                            "agentId": self.model.id,
                            "humanStrain": metrics.humanStrain,
                        },
                    )
                self.record_action(
                    f"AUTO: Triggered Emergency_Staffing (human strain: {metrics.humanStrain:.0f}%)"
                )
            else:
                self.create_alert(
                    engine,
                    AlertSeverity.critical,
                    f"{self.model.name}: Human strain at {metrics.humanStrain:.0f}%. "
                    f"Emergency staffing resources required. Operations team overloaded.",
                )
                self.emit_event(
                    engine,
                    SimulationEventType.staffing_overload,
                    {"agentId": self.model.id, "humanStrain": metrics.humanStrain},
                )
                self.record_action(f"Alerted: Emergency staffing needed (strain: {metrics.humanStrain:.0f}%)")
            acted = True

        # ─── System trust drop: reduce autonomy levels ─────────────────────
        if (
            metrics.systemTrust < 40
            and (tick - self._last_trust_alert_tick) >= 15
            and self.has_action_budget()
        ):
            self._last_trust_alert_tick = tick

            self.emit_event(
                engine,
                SimulationEventType.trust_drop,
                {
                    "agentId": self.model.id,
                    "systemTrust": metrics.systemTrust,
                    "tick": tick,
                },
            )

            if self.can_act_autonomously(2) and can_adjust:
                # Reduce all agent autonomy by 1 as safety measure
                for agent in agents:
                    if agent.id != self.model.id and agent.autonomyLevel > 0:
                        old = agent.autonomyLevel
                        agent.autonomyLevel = max(0, agent.autonomyLevel - 1)
                        logger.info(
                            f"Trust drop: reduced {agent.id} autonomy {old} -> {agent.autonomyLevel}"
                        )
                self._last_adjustment_tick = tick
                self.record_action(
                    f"SAFETY: Reduced all agent autonomy (system trust: {metrics.systemTrust:.0f}%)"
                )
                engine.trust_system.on_agent_action(self.model, True)
            else:
                self.create_alert(
                    engine,
                    AlertSeverity.critical,
                    f"{self.model.name}: System trust critical at {metrics.systemTrust:.0f}%. "
                    f"Recommend manual review of autonomous decisions.",
                )
                self.record_action(f"Trust drop alert issued (trust: {metrics.systemTrust:.0f}%)")

            # Trigger recovery protocol via UiPath
            job = await engine.uipath_client.start_job(
                "Trust_Recovery_Protocol",
                {"systemTrust": metrics.systemTrust, "tick": tick},
            )
            if job:
                self.emit_event(
                    engine,
                    SimulationEventType.uipath_job_started,
                    {
                        "agentId": self.model.id,
                        "processName": "Trust_Recovery_Protocol",
                        "jobId": job.id,
                    },
                )
            acted = True

        if not acted:
            self.set_idle("KPIs within targets — monitoring enterprise strategy")
        else:
            self.set_status(AgentStatus.idle)

    def _compute_trend(self, history: Deque[float]) -> float:
        """Compute average change per tick (slope) over the history window."""
        if len(history) < 3:
            return 0.0
        values = list(history)
        n = len(values)
        # Simple linear regression slope
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return 0.0
        return numerator / denominator
