"""
Metrics calculator: computes all SimulationMetrics from current state.
"""
import logging
from typing import List

from models.building import Building, BuildingStatus
from models.workflow import Workflow, WorkflowPriority, WorkflowStatus
from models.agent import Agent
from models.state import SimulationMetrics

logger = logging.getLogger(__name__)

# Building weights for operational stability (critical services weighted more)
_BUILDING_WEIGHTS = {
    "hospital": 3.0,
    "pharmacy": 2.5,
    "cloud_datacenter": 2.0,
    "comms_hub": 1.5,
    "orchestration_center": 1.5,
    "staffing_hr": 1.0,
    "backup_infra": 0.8,
}


class MetricsCalculator:
    def __init__(self) -> None:
        self._cascade_depth: int = 0

    def calculate(
        self,
        buildings: List[Building],
        workflows: List[Workflow],
        agents: List[Agent],
        resource_manager,  # ResourceManager instance
        trust_system,  # TrustSystem instance
    ) -> SimulationMetrics:
        """Calculate all metrics from current state."""
        operational_stability = self._calc_operational_stability(buildings)
        human_strain = self._calc_human_strain(resource_manager, buildings, workflows)
        automation_confidence = self._calc_automation_confidence(trust_system, agents)
        service_availability = self._calc_service_availability(buildings, workflows)
        system_trust = self._calc_system_trust(trust_system, agents)
        resource_capacity = self._calc_resource_capacity(resource_manager, buildings)

        return SimulationMetrics(
            operationalStability=round(operational_stability, 1),
            humanStrain=round(human_strain, 1),
            automationConfidence=round(automation_confidence, 1),
            serviceAvailability=round(service_availability, 1),
            systemTrust=round(system_trust, 1),
            resourceCapacity=round(resource_capacity, 1),
        )

    def _calc_operational_stability(self, buildings: List[Building]) -> float:
        """
        Weighted average of building health, penalized by cascade depth.
        Critical services (hospital, pharmacy) weighted more heavily.
        """
        if not buildings:
            return 0.0

        total_weight = 0.0
        weighted_health = 0.0

        for b in buildings:
            weight = _BUILDING_WEIGHTS.get(b.id, 1.0)
            total_weight += weight
            weighted_health += b.health * weight

        base_stability = weighted_health / total_weight

        # Count offline/critical buildings for cascade penalty
        offline_count = sum(1 for b in buildings if b.status == BuildingStatus.offline)
        critical_count = sum(1 for b in buildings if b.status == BuildingStatus.critical)

        cascade_penalty = (offline_count * 8.0) + (critical_count * 4.0)
        self._cascade_depth = offline_count + critical_count

        return max(0.0, min(100.0, base_stability - cascade_penalty))

    def _calc_human_strain(
        self,
        resource_manager,
        buildings: List[Building],
        workflows: List[Workflow],
    ) -> float:
        """
        Human strain from resource manager, amplified by total queue depth.
        """
        base_strain = resource_manager.humanStrain

        # Additional amplification from very high queues
        total_queue = sum(b.queueDepth for b in buildings)
        if total_queue > 60:
            amplification = min(15.0, (total_queue - 60) * 0.25)
            base_strain = min(100.0, base_strain + amplification)

        # Blocked workflows add strain
        blocked = sum(1 for w in workflows if w.status == WorkflowStatus.blocked)
        if blocked > 5:
            base_strain = min(100.0, base_strain + (blocked - 5) * 0.5)

        return max(0.0, min(100.0, base_strain))

    def _calc_automation_confidence(
        self, trust_system, agents: List[Agent]
    ) -> float:
        """
        Based on trust system's automation confidence and agent trust scores.
        """
        trust_confidence = trust_system.automationConfidence

        # Factor in agent trust scores
        if agents:
            avg_agent_trust = sum(a.trustScore for a in agents) / len(agents)
            # Blend: 70% trust system, 30% agent trust
            blended = trust_confidence * 0.7 + avg_agent_trust * 0.3
        else:
            blended = trust_confidence

        return max(0.0, min(100.0, blended))

    def _calc_service_availability(
        self, buildings: List[Building], workflows: List[Workflow]
    ) -> float:
        """
        Percentage of critical workflows (hospital, pharmacy-related) that are flowing.
        Also accounts for whether hospital and pharmacy are operational.
        """
        hospital = next((b for b in buildings if b.id == "hospital"), None)
        pharmacy = next((b for b in buildings if b.id == "pharmacy"), None)

        # Critical building health contribution (50% of score)
        building_score = 0.0
        if hospital:
            building_score += hospital.health * 0.5
        if pharmacy:
            building_score += pharmacy.health * 0.5

        # Critical workflow flow rate (50% of score)
        critical_workflows = [
            w for w in workflows
            if w.sourceId in ("hospital", "pharmacy") or w.destId in ("hospital", "pharmacy")
        ]

        if critical_workflows:
            flowing = sum(
                1 for w in critical_workflows
                if w.status in (WorkflowStatus.flowing, WorkflowStatus.rerouted)
            )
            workflow_score = (flowing / len(critical_workflows)) * 100.0
        else:
            workflow_score = 100.0

        return max(0.0, min(100.0, building_score * 0.5 + workflow_score * 0.5))

    def _calc_system_trust(self, trust_system, agents: List[Agent]) -> float:
        """
        Weighted by autonomy levels and recent outcomes.
        High autonomy agents contribute more to system trust calculation.
        """
        base_trust = trust_system.systemTrust

        # Autonomy-weighted agent trust
        if agents:
            total_weight = sum(a.autonomyLevel + 1 for a in agents)
            weighted_agent_trust = sum(
                a.trustScore * (a.autonomyLevel + 1) for a in agents
            ) / total_weight
            # Blend: 60% trust system, 40% weighted agent trust
            blended = base_trust * 0.6 + weighted_agent_trust * 0.4
        else:
            blended = base_trust

        return max(0.0, min(100.0, blended))

    def _calc_resource_capacity(self, resource_manager, buildings: List[Building]) -> float:
        """
        Recovery capacity weighted by backup_infra health.
        """
        base_capacity = resource_manager.recoveryCapacity

        backup = next((b for b in buildings if b.id == "backup_infra"), None)
        if backup:
            # If backup is degraded, recovery capacity ceiling is lower
            capacity = min(base_capacity, backup.health * 0.9 + 10.0)
        else:
            capacity = base_capacity

        return max(0.0, min(100.0, capacity))

    @property
    def cascade_depth(self) -> int:
        return self._cascade_depth
