"""
Workflow engine: manages all active workflows, animates progress,
handles blocking/rerouting/completion, and generates new workflows.
"""
import logging
import random
import uuid
from typing import Dict, List, Optional, Tuple

from models.agent import Agent
from models.building import Building, BuildingStatus
from models.workflow import Workflow, WorkflowPriority, WorkflowStatus, WorkflowType

logger = logging.getLogger(__name__)

MIN_WORKFLOWS = 15
MAX_WORKFLOWS = 30

# Base progress per tick per workflow type (multiplied by throughput factor)
BASE_PROGRESS_RATE = 0.05


def _find_building(buildings: List[Building], bid: str) -> Optional[Building]:
    for b in buildings:
        if b.id == bid:
            return b
    return None


def _throughput_factor(b: Optional[Building]) -> float:
    if b is None:
        return 0.1
    return max(0.05, b.throughput / 100.0)


def _is_usable(b: Optional[Building]) -> bool:
    if b is None:
        return False
    return b.status not in (BuildingStatus.offline, BuildingStatus.critical)


def _is_operational(b: Optional[Building]) -> bool:
    if b is None:
        return False
    return b.status == BuildingStatus.operational


# Maps workflow type to typical (source_type, dest_type) pairs
_WORKFLOW_TEMPLATES: List[Tuple[WorkflowType, str, str, WorkflowPriority, float]] = [
    (WorkflowType.ehr_record, "hospital", "pharmacy", WorkflowPriority.high, 0.18),
    (WorkflowType.ehr_record, "hospital", "orchestration_center", WorkflowPriority.medium, 0.15),
    (WorkflowType.prescription, "pharmacy", "hospital", WorkflowPriority.high, 0.25),
    (WorkflowType.prescription, "pharmacy", "orchestration_center", WorkflowPriority.medium, 0.20),
    (WorkflowType.comm_packet, "comms_hub", "hospital", WorkflowPriority.medium, 0.06),
    (WorkflowType.comm_packet, "comms_hub", "pharmacy", WorkflowPriority.low, 0.05),
    (WorkflowType.comm_packet, "comms_hub", "orchestration_center", WorkflowPriority.medium, 0.07),
    (WorkflowType.comm_packet, "comms_hub", "staffing_hr", WorkflowPriority.low, 0.05),
    (WorkflowType.staffing_request, "hospital", "staffing_hr", WorkflowPriority.medium, 0.12),
    (WorkflowType.staffing_request, "pharmacy", "staffing_hr", WorkflowPriority.low, 0.10),
    (WorkflowType.approval_request, "hospital", "orchestration_center", WorkflowPriority.high, 0.55),
    (WorkflowType.approval_request, "pharmacy", "orchestration_center", WorkflowPriority.medium, 0.45),
    (WorkflowType.escalation, "orchestration_center", "cloud_datacenter", WorkflowPriority.high, 0.40),
    (WorkflowType.failover_cmd, "backup_infra", "cloud_datacenter", WorkflowPriority.critical, 0.05),
]


class WorkflowEngine:
    def __init__(self) -> None:
        self.workflows: List[Workflow] = []
        self._completed_count: int = 0

    def initialize(self, initial_workflows: List[Workflow]) -> None:
        self.workflows = [w.model_copy(deep=True) for w in initial_workflows]

    def tick(self, buildings: List[Building], agents: List[Agent]) -> None:
        """Main per-tick update."""
        building_map: Dict[str, Building] = {b.id: b for b in buildings}
        completed_ids: List[str] = []

        for wf in self.workflows:
            src = building_map.get(wf.sourceId)
            dst = building_map.get(wf.destId)

            # Determine new status
            new_status = self._determine_status(wf, src, dst, building_map)
            wf.status = new_status

            if new_status in (WorkflowStatus.flowing, WorkflowStatus.rerouted):
                # Advance progress
                tf_src = _throughput_factor(src)
                tf_dst = _throughput_factor(dst)
                tf = (tf_src + tf_dst) / 2.0
                wf.progress = min(1.0, wf.progress + BASE_PROGRESS_RATE * tf)

            elif new_status == WorkflowStatus.queued:
                # Slow advance when queued
                wf.progress = min(1.0, wf.progress + BASE_PROGRESS_RATE * 0.15)

            elif new_status in (WorkflowStatus.blocked, WorkflowStatus.failed):
                # No progress; slightly regress
                wf.progress = max(0.0, wf.progress - 0.01)

            # Mark completed
            if wf.progress >= 1.0:
                completed_ids.append(wf.id)

        # Remove completed workflows
        self.workflows = [w for w in self.workflows if w.id not in completed_ids]
        self._completed_count += len(completed_ids)

        # Update queue depths on buildings
        self._update_queue_depths(buildings)

        # Generate new workflows to maintain count
        attempts = 0
        while len(self.workflows) < MIN_WORKFLOWS and attempts < 20:
            new_wf = self.generate_workflow(buildings)
            if new_wf:
                self.workflows.append(new_wf)
            attempts += 1

        # Trim if over limit
        if len(self.workflows) > MAX_WORKFLOWS:
            # Remove lowest priority non-critical flowing ones first
            self.workflows.sort(
                key=lambda w: (
                    0 if w.priority == WorkflowPriority.critical else
                    1 if w.priority == WorkflowPriority.high else
                    2 if w.priority == WorkflowPriority.medium else 3
                )
            )
            self.workflows = self.workflows[:MAX_WORKFLOWS]

    def _determine_status(
        self,
        wf: Workflow,
        src: Optional[Building],
        dst: Optional[Building],
        building_map: Dict[str, Building],
    ) -> WorkflowStatus:
        """Determine what status a workflow should have based on building states."""
        src_down = src is None or src.status in (BuildingStatus.offline,)
        dst_down = dst is None or dst.status in (BuildingStatus.offline,)
        src_critical = src is not None and src.status == BuildingStatus.critical
        dst_critical = dst is not None and dst.status == BuildingStatus.critical

        if src_down or dst_down:
            # Try to reroute through orchestration_center
            rerouted = self.reroute_workflow(wf, building_map)
            if rerouted:
                return WorkflowStatus.rerouted
            return WorkflowStatus.blocked

        if src_critical or dst_critical:
            # Try to reroute; otherwise queue
            rerouted = self.reroute_workflow(wf, building_map)
            if rerouted:
                return WorkflowStatus.rerouted
            return WorkflowStatus.queued

        if src is not None and src.status == BuildingStatus.degraded:
            return WorkflowStatus.queued

        if dst is not None and dst.status == BuildingStatus.degraded:
            return WorkflowStatus.queued

        # If currently rerouted but original path works, restore
        if wf.status == WorkflowStatus.rerouted:
            if _is_operational(src) and _is_operational(dst):
                return WorkflowStatus.flowing

        if wf.status in (WorkflowStatus.flowing, WorkflowStatus.rerouted, WorkflowStatus.queued):
            return wf.status

        # Default for brand new or previously blocked/failed
        return WorkflowStatus.flowing

    def reroute_workflow(
        self, wf: Workflow, building_map: Dict[str, Building]
    ) -> bool:
        """
        Attempt to reroute a workflow through backup or orchestration center.
        Returns True if rerouting is possible.
        """
        orch = building_map.get("orchestration_center")
        backup = building_map.get("backup_infra")

        # Reroute via orchestration_center if available
        if orch and _is_usable(orch) and orch.health > 40:
            return True

        # Reroute via backup_infra for failover types
        if wf.type in (WorkflowType.failover_cmd, WorkflowType.escalation):
            if backup and _is_usable(backup):
                return True

        return False

    def generate_workflow(self, buildings: List[Building]) -> Optional[Workflow]:
        """Create a contextually appropriate new workflow based on building states."""
        building_map: Dict[str, Building] = {b.id: b for b in buildings}

        # Weight templates by how relevant they are given current state
        weighted: List[Tuple[float, Tuple[WorkflowType, str, str, WorkflowPriority, float]]] = []

        for template in _WORKFLOW_TEMPLATES:
            wf_type, src_id, dst_id, priority, risk = template
            src = building_map.get(src_id)
            dst = building_map.get(dst_id)

            if not src or not dst:
                continue

            # Base weight
            weight = 1.0

            # Increase weight for relevant conditions
            if wf_type == WorkflowType.ehr_record and _is_usable(src) and _is_usable(dst):
                weight = 3.0
            elif wf_type == WorkflowType.prescription and _is_usable(src) and _is_usable(dst):
                weight = 3.0
            elif wf_type == WorkflowType.comm_packet and _is_usable(src):
                weight = 2.0
            elif wf_type == WorkflowType.staffing_request:
                hospital = building_map.get("hospital")
                if hospital and hospital.queueDepth > 15:
                    weight = 4.0
                else:
                    weight = 1.5
            elif wf_type == WorkflowType.approval_request:
                # Generate approvals when buildings are degraded
                degraded_count = sum(
                    1 for b in buildings
                    if b.status in (BuildingStatus.degraded, BuildingStatus.critical)
                )
                weight = 1.0 + degraded_count * 0.8
            elif wf_type == WorkflowType.escalation:
                cloud = building_map.get("cloud_datacenter")
                if cloud and cloud.health < 70:
                    weight = 5.0
                else:
                    weight = 0.3
            elif wf_type == WorkflowType.failover_cmd:
                cloud = building_map.get("cloud_datacenter")
                if cloud and cloud.health < 50:
                    weight = 6.0
                else:
                    weight = 0.1

            # Reduce weight if source or dest is down
            if not _is_usable(src) or not _is_usable(dst):
                weight *= 0.1

            weighted.append((weight, template))

        if not weighted:
            return None

        # Weighted random selection
        total = sum(w for w, _ in weighted)
        if total <= 0:
            return None

        r = random.uniform(0, total)
        cumulative = 0.0
        selected = weighted[0][1]
        for w, template in weighted:
            cumulative += w
            if r <= cumulative:
                selected = template
                break

        wf_type, src_id, dst_id, priority, base_risk = selected

        # Adjust risk based on building health
        src = building_map.get(src_id)
        dst = building_map.get(dst_id)
        risk_modifier = 1.0
        if src and src.health < 70:
            risk_modifier += 0.3
        if dst and dst.health < 70:
            risk_modifier += 0.2

        actual_risk = min(1.0, base_risk * risk_modifier)

        return Workflow(
            id=f"wf-{uuid.uuid4().hex[:8]}",
            type=wf_type,
            sourceId=src_id,
            destId=dst_id,
            priority=priority,
            status=WorkflowStatus.flowing,
            automationEligible=True,
            risk=actual_risk,
            progress=0.0,
        )

    def _update_queue_depths(self, buildings: List[Building]) -> None:
        """Update building queue depths based on blocked/queued workflows."""
        # Count blocked/queued workflows per building
        queue_additions: Dict[str, int] = {}

        for wf in self.workflows:
            if wf.status in (WorkflowStatus.blocked, WorkflowStatus.queued):
                queue_additions[wf.sourceId] = queue_additions.get(wf.sourceId, 0) + 1
                queue_additions[wf.destId] = queue_additions.get(wf.destId, 0) + 1

        for b in buildings:
            addition = queue_additions.get(b.id, 0)
            # Gradually drain queues when flowing
            if addition == 0:
                b.queueDepth = max(0, b.queueDepth - 1)
            else:
                # Queues grow based on blocked workflows
                b.queueDepth = min(50, b.queueDepth + addition)

    def get_blocked_count(self) -> int:
        return sum(1 for w in self.workflows if w.status == WorkflowStatus.blocked)

    def get_flowing_count(self) -> int:
        return sum(1 for w in self.workflows if w.status in (WorkflowStatus.flowing, WorkflowStatus.rerouted))

    def get_critical_workflows(self) -> List[Workflow]:
        return [w for w in self.workflows if w.priority == WorkflowPriority.critical]

    def block_workflow(self, workflow_id: str) -> bool:
        for wf in self.workflows:
            if wf.id == workflow_id:
                wf.status = WorkflowStatus.blocked
                return True
        return False

    def set_workflow_status(self, workflow_id: str, status: WorkflowStatus) -> bool:
        for wf in self.workflows:
            if wf.id == workflow_id:
                wf.status = status
                return True
        return False
