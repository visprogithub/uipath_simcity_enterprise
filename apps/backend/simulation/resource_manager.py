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
        self._update_staffing(buildings)
        self._update_human_strain(buildings, workflows)
        self._update_recovery_capacity(buildings)
        self._clamp()

    def _update_staffing(self, buildings: List[Building]) -> None:
        """Staffing depletes under stress and slowly regenerates when stable.

        This makes Staffing a REAL lever instead of a free constant: during a crisis
        crews get overwhelmed and staffing drains, weakening the recovery it feeds —
        so the player must actively re-staff as part of a coordinated response, not
        rely on the default 100. Operational buildings slowly recover their own crews.
        """
        for b in buildings:
            if b.staffingLevel < 25.0:
                # Skeleton crews cannot keep throughput stable. This makes the
                # Staffing sliders matter even before a hard outage happens.
                b.throughput = max(15.0, b.throughput - (25.0 - b.staffingLevel) * 0.08)
                if b.staffingLevel < 10.0 and b.status == BuildingStatus.operational:
                    b.health = max(70.0, b.health - 0.2)
            if b.status == BuildingStatus.offline:
                b.staffingLevel = max(0.0, b.staffingLevel - 1.0)
            elif b.status == BuildingStatus.critical:
                b.staffingLevel = max(0.0, b.staffingLevel - 0.7)
            elif b.status == BuildingStatus.degraded:
                b.staffingLevel = max(0.0, b.staffingLevel - 0.4)
            elif b.staffingLevel < 100.0:
                b.staffingLevel = min(100.0, b.staffingLevel + 0.3)
            b.clamp()

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

        # Understaffed buildings create operator strain and SLA pressure even when
        # infrastructure is technically healthy.
        understaffed_count = sum(1 for b in buildings if b.staffingLevel < 25.0)
        severe_understaffed_count = sum(1 for b in buildings if b.staffingLevel < 10.0)
        strain_delta += understaffed_count * 0.45
        strain_delta += severe_understaffed_count * 0.35

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
            # Failover ENABLES recovery — it must not drain the capacity recovery
            # depends on, or the longer it runs the weaker recovery gets (which made
            # the combination unwinnable). Hold steady with a slow regen; the
            # backup-health cap below still limits the ceiling.
            self.recoveryCapacity = min(100.0, self.recoveryCapacity + 0.1)
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
            delta = level - old_level
            relief = delta * 0.1
            self.humanStrain = max(0.0, self.humanStrain - relief)
            # Boost throughput proportional to staffing increase
            building.throughput = min(100.0, building.throughput + delta * 0.3)
            # Immediate health bump so staffing up a failing building is felt right
            # away — not just via the per-tick recovery multiplier. Crews triage on
            # arrival. Scaled modestly so it complements, not replaces, recovery.
            building.health = min(100.0, building.health + delta * 0.15)
            building.clamp()
        else:
            # Reduced staffing increases strain
            impact = (old_level - level) * 0.05
            self.humanStrain = min(100.0, self.humanStrain + impact)
            # Pulling staff immediately reduces effective throughput. Severe cuts
            # also start a controlled degradation that the tick loop can amplify.
            delta = old_level - level
            building.throughput = max(10.0, building.throughput - delta * 0.45)
            if level < 10.0:
                building.health = max(65.0, building.health - delta * 0.08)
            building.clamp()

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
