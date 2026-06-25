"""
Resource manager: tracks staffing consumption, recovery capacity, human strain.
"""
import logging
from typing import List

from models.building import Building, BuildingStatus
from models.workflow import Workflow, WorkflowStatus

logger = logging.getLogger(__name__)


class ResourceManager:
    def __init__(self) -> None:
        self.humanStrain: float = 10.0  # 0-100, high = bad
        self.recoveryCapacity: float = 100.0  # 0-100
        self._failover_active: bool = False
        self._pending_approvals: int = 0

    def tick(self, buildings: List[Building], workflows: List[Workflow]) -> None:
        """Per-tick resource update."""
        self._update_human_strain(buildings, workflows)
        self._update_recovery_capacity(buildings)
        self._clamp()

    def _update_human_strain(
        self, buildings: List[Building], workflows: List[Workflow]
    ) -> None:
        strain_delta = 0.0

        # Queue depth contribution
        total_queue = sum(b.queueDepth for b in buildings)
        if total_queue > 50:
            strain_delta += 0.8
        elif total_queue > 30:
            strain_delta += 0.4
        elif total_queue > 15:
            strain_delta += 0.15

        # Degraded buildings contribution
        degraded_count = sum(
            1 for b in buildings
            if b.status in (BuildingStatus.degraded, BuildingStatus.critical, BuildingStatus.offline)
        )
        strain_delta += degraded_count * 0.3

        # Approval backlog pressure
        approval_wf = [
            w for w in workflows
            if w.type.value == "approval_request" and w.status in (WorkflowStatus.blocked, WorkflowStatus.queued)
        ]
        if len(approval_wf) > 3:
            strain_delta += 0.5

        # Staffing exhaustion amplifier
        if self.humanStrain > 70:
            strain_delta *= 1.4

        # Recovery: automation reduces strain when things are stable
        stable_count = sum(1 for b in buildings if b.status == BuildingStatus.operational)
        total = len(buildings) if buildings else 1
        stability_ratio = stable_count / total

        if stability_ratio > 0.8 and degraded_count == 0:
            strain_delta -= 0.6  # recover quickly when stable
        elif stability_ratio > 0.6:
            strain_delta -= 0.2

        self.humanStrain = max(0.0, min(100.0, self.humanStrain + strain_delta))
        self._pending_approvals = len(approval_wf)

    def _update_recovery_capacity(self, buildings: List[Building]) -> None:
        backup = next((b for b in buildings if b.type == "backup_infra"), None)

        if self._failover_active:
            # Failover drains recovery capacity
            self.recoveryCapacity = max(0.0, self.recoveryCapacity - 0.5)
        else:
            # Slowly regenerate when stable
            stable = all(b.status == BuildingStatus.operational for b in buildings)
            if stable:
                self.recoveryCapacity = min(100.0, self.recoveryCapacity + 0.3)
            else:
                self.recoveryCapacity = min(100.0, self.recoveryCapacity + 0.1)

        # Backup infra health affects recovery capacity ceiling
        if backup and backup.health < 50:
            self.recoveryCapacity = min(self.recoveryCapacity, backup.health * 0.8)

    def _clamp(self) -> None:
        self.humanStrain = max(0.0, min(100.0, self.humanStrain))
        self.recoveryCapacity = max(0.0, min(100.0, self.recoveryCapacity))

    def activate_failover(self) -> None:
        self._failover_active = True
        self.recoveryCapacity = max(0.0, self.recoveryCapacity - 15.0)
        logger.info("Failover activated; recovery capacity reduced")

    def deactivate_failover(self) -> None:
        self._failover_active = False
        logger.info("Failover deactivated")

    def apply_staffing_action(self, building: Building, level: float) -> None:
        """Apply a staffing level change to a building."""
        old_level = building.staffingLevel
        building.staffingLevel = max(0.0, min(100.0, level))

        # Increased staffing reduces human strain
        if level > old_level:
            relief = (level - old_level) * 0.1
            self.humanStrain = max(0.0, self.humanStrain - relief)
            # Boost throughput proportional to staffing increase
            building.throughput = min(100.0, building.throughput + (level - old_level) * 0.3)
        else:
            # Reduced staffing increases strain
            impact = (old_level - level) * 0.05
            self.humanStrain = min(100.0, self.humanStrain + impact)

        logger.info(
            f"Staffing at {building.id} changed from {old_level:.0f} to {level:.0f}; "
            f"strain now {self.humanStrain:.1f}"
        )

    @property
    def pending_approvals(self) -> int:
        return self._pending_approvals

    @property
    def failover_active(self) -> bool:
        return self._failover_active
