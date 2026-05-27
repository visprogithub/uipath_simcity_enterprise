"""
Trust system: tracks system trust and automation confidence.
Trust affects autonomy effectiveness. Automation confidence affects UiPath job weight.
"""
import logging
from typing import List, Optional

from models.agent import Agent
from models.building import Building
from models.state import SimulationMetrics, UiPathJob

logger = logging.getLogger(__name__)


class TrustSystem:
    def __init__(self) -> None:
        self.systemTrust: float = 90.0        # 0-100
        self.automationConfidence: float = 85.0  # 0-100
        self._recent_job_results: List[bool] = []  # last 10 UiPath job results
        self._recent_agent_results: List[bool] = []  # last 10 agent action results

    def tick(
        self,
        buildings: List[Building],
        agents: List[Agent],
        metrics: SimulationMetrics,
    ) -> None:
        """Per-tick trust update."""
        self._decay_trust(buildings, metrics)
        self._update_from_agents(agents)
        self._clamp()

    def _decay_trust(
        self, buildings: List[Building], metrics: SimulationMetrics
    ) -> None:
        """Apply trust decay or growth based on system state."""
        from models.building import BuildingStatus  # avoid circular at module level

        critical_count = sum(
            1 for b in buildings
            if b.status in (BuildingStatus.critical, BuildingStatus.offline)
        )

        # Trust decays during cascades
        if critical_count >= 3:
            self.systemTrust = max(0.0, self.systemTrust - 1.2)
            self.automationConfidence = max(0.0, self.automationConfidence - 0.8)
        elif critical_count >= 1:
            self.systemTrust = max(0.0, self.systemTrust - 0.4)
        else:
            # Slowly recover trust when stable
            if metrics.operationalStability > 70:
                self.systemTrust = min(100.0, self.systemTrust + 0.15)
                self.automationConfidence = min(100.0, self.automationConfidence + 0.10)

        # Low service availability erodes trust
        if metrics.serviceAvailability < 40:
            self.systemTrust = max(0.0, self.systemTrust - 0.8)
        elif metrics.serviceAvailability > 80:
            self.systemTrust = min(100.0, self.systemTrust + 0.05)

    def _update_from_agents(self, agents: List[Agent]) -> None:
        """Update trust based on agent trust scores."""
        if not agents:
            return
        avg_agent_trust = sum(a.trustScore for a in agents) / len(agents)

        # Pull system trust slightly toward average agent trust
        delta = (avg_agent_trust - self.systemTrust) * 0.02
        self.systemTrust = max(0.0, min(100.0, self.systemTrust + delta))

    def on_agent_action(self, agent: Agent, success: bool) -> None:
        """Update trust based on agent action outcome."""
        self._recent_agent_results.append(success)
        if len(self._recent_agent_results) > 20:
            self._recent_agent_results.pop(0)

        if success:
            agent.trustScore = min(100.0, agent.trustScore + 0.5)
            self.systemTrust = min(100.0, self.systemTrust + 0.2)
        else:
            agent.trustScore = max(0.0, agent.trustScore - 1.5)
            self.systemTrust = max(0.0, self.systemTrust - 0.8)
            self.automationConfidence = max(0.0, self.automationConfidence - 0.5)

        logger.debug(
            f"Agent {agent.id} action {'succeeded' if success else 'failed'}; "
            f"trust score now {agent.trustScore:.1f}"
        )

    def on_uipath_result(self, job: UiPathJob, success: bool) -> None:
        """Update automation confidence based on UiPath job outcome."""
        self._recent_job_results.append(success)
        if len(self._recent_job_results) > 10:
            self._recent_job_results.pop(0)

        if success:
            self.automationConfidence = min(100.0, self.automationConfidence + 2.0)
            self.systemTrust = min(100.0, self.systemTrust + 0.5)
            logger.info(f"UiPath job {job.id} ({job.processName}) succeeded; confidence up")
        else:
            self.automationConfidence = max(0.0, self.automationConfidence - 4.0)
            self.systemTrust = max(0.0, self.systemTrust - 1.0)
            logger.warning(f"UiPath job {job.id} ({job.processName}) faulted; confidence down")

    def on_cascade_event(self) -> None:
        """Called when a cascade propagation is detected."""
        self.systemTrust = max(0.0, self.systemTrust - 3.0)
        self.automationConfidence = max(0.0, self.automationConfidence - 1.5)

    def on_successful_recovery(self, building_id: str) -> None:
        """Called when a building recovers."""
        self.systemTrust = min(100.0, self.systemTrust + 1.5)
        self.automationConfidence = min(100.0, self.automationConfidence + 0.8)
        logger.info(f"Recovery at {building_id} boosted trust to {self.systemTrust:.1f}")

    def on_approval_denied(self) -> None:
        """Called when an approval is denied."""
        self.systemTrust = max(0.0, self.systemTrust - 1.0)

    def get_autonomy_effectiveness(self, agent: Agent) -> float:
        """
        Return effectiveness multiplier for agent actions based on trust.
        High trust + high autonomy = full effectiveness.
        """
        trust_factor = self.systemTrust / 100.0
        autonomy_factor = agent.autonomyLevel / 4.0
        return (trust_factor * 0.6 + autonomy_factor * 0.4)

    def _clamp(self) -> None:
        self.systemTrust = max(0.0, min(100.0, self.systemTrust))
        self.automationConfidence = max(0.0, min(100.0, self.automationConfidence))
