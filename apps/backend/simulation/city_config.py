"""
Initial city configuration for Maestro City simulation.
All buildings, dependency edges, initial workflows, and agents defined here.
"""
import copy
import uuid
from typing import List, Tuple

from models.building import Building, BuildingPosition, BuildingStatus, BuildingType
from models.workflow import Workflow, WorkflowPriority, WorkflowStatus, WorkflowType
from models.agent import Agent, AgentStatus


# ─── Buildings ───────────────────────────────────────────────────────────────

_BUILDINGS_RAW: List[Building] = [
    Building(
        id="hospital",
        type=BuildingType.hospital,
        name="City General Hospital",
        pos=BuildingPosition(x=1, y=1, w=3, h=3),
        status=BuildingStatus.operational,
        health=100.0,
        throughput=85.0,
        staffingLevel=75.0,
        trustLevel=90.0,
        dependencies=["cloud_datacenter", "orchestration_center", "staffing_hr"],
        queueDepth=12,
        recoveryCapacity=60.0,
    ),
    Building(
        id="pharmacy",
        type=BuildingType.pharmacy,
        name="Central Pharmacy",
        pos=BuildingPosition(x=6, y=1, w=2, h=2),
        status=BuildingStatus.operational,
        health=100.0,
        throughput=90.0,
        staffingLevel=80.0,
        trustLevel=88.0,
        dependencies=["cloud_datacenter", "hospital", "orchestration_center"],
        queueDepth=8,
        recoveryCapacity=70.0,
    ),
    Building(
        id="cloud_datacenter",
        type=BuildingType.cloud_datacenter,
        name="CloudCore Data Center",
        pos=BuildingPosition(x=14, y=1, w=3, h=3),
        status=BuildingStatus.operational,
        health=100.0,
        throughput=95.0,
        staffingLevel=60.0,
        trustLevel=95.0,
        dependencies=[],
        queueDepth=0,
        recoveryCapacity=100.0,
    ),
    Building(
        id="comms_hub",
        type=BuildingType.comms_hub,
        name="Communications Hub",
        pos=BuildingPosition(x=10, y=1, w=2, h=2),
        status=BuildingStatus.operational,
        health=100.0,
        throughput=88.0,
        staffingLevel=65.0,
        trustLevel=92.0,
        dependencies=["cloud_datacenter"],
        queueDepth=5,
        recoveryCapacity=80.0,
    ),
    Building(
        id="orchestration_center",
        type=BuildingType.orchestration_center,
        name="Maestro Orchestration Center",
        pos=BuildingPosition(x=18, y=1, w=2, h=2),
        status=BuildingStatus.operational,
        health=100.0,
        throughput=92.0,
        staffingLevel=70.0,
        trustLevel=94.0,
        dependencies=["cloud_datacenter", "comms_hub"],
        queueDepth=3,
        recoveryCapacity=85.0,
    ),
    Building(
        id="staffing_hr",
        type=BuildingType.staffing_hr,
        name="Staffing & Operations",
        pos=BuildingPosition(x=22, y=1, w=2, h=2),
        status=BuildingStatus.operational,
        health=100.0,
        throughput=78.0,
        staffingLevel=85.0,
        trustLevel=80.0,
        dependencies=["comms_hub"],
        queueDepth=15,
        recoveryCapacity=50.0,
    ),
    Building(
        id="backup_infra",
        type=BuildingType.backup_infra,
        name="Failover Infrastructure",
        pos=BuildingPosition(x=26, y=1, w=2, h=2),
        status=BuildingStatus.operational,
        health=100.0,
        throughput=40.0,
        staffingLevel=50.0,
        trustLevel=85.0,
        dependencies=[],
        queueDepth=0,
        recoveryCapacity=100.0,
    ),
]

# Dependency edges: (dependent_id, dependency_id) — meaning 'dependent' depends on 'dependency'
DEPENDENCY_EDGES: List[Tuple[str, str]] = [
    ("hospital", "cloud_datacenter"),
    ("hospital", "orchestration_center"),
    ("hospital", "staffing_hr"),
    ("pharmacy", "cloud_datacenter"),
    ("pharmacy", "hospital"),
    ("pharmacy", "orchestration_center"),
    ("comms_hub", "cloud_datacenter"),
    ("orchestration_center", "cloud_datacenter"),
    ("orchestration_center", "comms_hub"),
    ("staffing_hr", "comms_hub"),
]

# backup_infra has no dependencies (standalone)


def _make_workflow(
    wf_id: str,
    wf_type: WorkflowType,
    source: str,
    dest: str,
    priority: WorkflowPriority,
    risk: float,
    progress: float,
    automation: bool = True,
    status: WorkflowStatus = WorkflowStatus.flowing,
) -> Workflow:
    return Workflow(
        id=wf_id,
        type=wf_type,
        sourceId=source,
        destId=dest,
        priority=priority,
        status=status,
        automationEligible=automation,
        risk=risk,
        progress=progress,
    )


_INITIAL_WORKFLOWS_RAW: List[Workflow] = [
    # EHR Records: hospital -> pharmacy
    _make_workflow("wf-001", WorkflowType.ehr_record, "hospital", "pharmacy", WorkflowPriority.high, 0.15, 0.10),
    _make_workflow("wf-002", WorkflowType.ehr_record, "hospital", "pharmacy", WorkflowPriority.high, 0.20, 0.40),
    _make_workflow("wf-003", WorkflowType.ehr_record, "hospital", "pharmacy", WorkflowPriority.medium, 0.10, 0.70),
    _make_workflow("wf-004", WorkflowType.ehr_record, "hospital", "pharmacy", WorkflowPriority.critical, 0.30, 0.05),
    # Prescriptions: pharmacy -> hospital
    _make_workflow("wf-005", WorkflowType.prescription, "pharmacy", "hospital", WorkflowPriority.high, 0.25, 0.20),
    _make_workflow("wf-006", WorkflowType.prescription, "pharmacy", "hospital", WorkflowPriority.critical, 0.35, 0.55),
    _make_workflow("wf-007", WorkflowType.prescription, "pharmacy", "hospital", WorkflowPriority.medium, 0.15, 0.80),
    # Comm packets: comms_hub -> hospital
    _make_workflow("wf-008", WorkflowType.comm_packet, "comms_hub", "hospital", WorkflowPriority.medium, 0.05, 0.30),
    _make_workflow("wf-009", WorkflowType.comm_packet, "comms_hub", "hospital", WorkflowPriority.low, 0.05, 0.60),
    _make_workflow("wf-010", WorkflowType.comm_packet, "comms_hub", "pharmacy", WorkflowPriority.low, 0.05, 0.15),
    _make_workflow("wf-011", WorkflowType.comm_packet, "comms_hub", "orchestration_center", WorkflowPriority.medium, 0.08, 0.45),
    # Approval requests: hospital -> orchestration_center
    _make_workflow("wf-012", WorkflowType.approval_request, "hospital", "orchestration_center", WorkflowPriority.high, 0.60, 0.25),
    _make_workflow("wf-013", WorkflowType.approval_request, "pharmacy", "orchestration_center", WorkflowPriority.medium, 0.55, 0.50),
    # Staffing requests: hospital -> staffing_hr
    _make_workflow("wf-014", WorkflowType.staffing_request, "hospital", "staffing_hr", WorkflowPriority.medium, 0.10, 0.35),
    _make_workflow("wf-015", WorkflowType.staffing_request, "hospital", "staffing_hr", WorkflowPriority.high, 0.20, 0.65),
    _make_workflow("wf-016", WorkflowType.staffing_request, "pharmacy", "staffing_hr", WorkflowPriority.low, 0.10, 0.10),
    # Escalations: orchestration_center -> cloud_datacenter
    _make_workflow("wf-017", WorkflowType.escalation, "orchestration_center", "cloud_datacenter", WorkflowPriority.high, 0.40, 0.20),
    # Failover commands from backup
    _make_workflow("wf-018", WorkflowType.failover_cmd, "backup_infra", "cloud_datacenter", WorkflowPriority.low, 0.05, 0.90),
    # Additional mixed workflows
    _make_workflow("wf-019", WorkflowType.ehr_record, "hospital", "orchestration_center", WorkflowPriority.medium, 0.18, 0.50),
    _make_workflow("wf-020", WorkflowType.comm_packet, "comms_hub", "staffing_hr", WorkflowPriority.low, 0.05, 0.75),
    _make_workflow("wf-021", WorkflowType.prescription, "pharmacy", "orchestration_center", WorkflowPriority.high, 0.28, 0.12),
    _make_workflow("wf-022", WorkflowType.approval_request, "hospital", "staffing_hr", WorkflowPriority.medium, 0.45, 0.38),
    _make_workflow("wf-023", WorkflowType.ehr_record, "hospital", "pharmacy", WorkflowPriority.high, 0.22, 0.85),
    _make_workflow("wf-024", WorkflowType.comm_packet, "comms_hub", "hospital", WorkflowPriority.medium, 0.06, 0.22),
]


_AGENTS_RAW: List[Agent] = [
    Agent(
        id="ops_coord",
        type="operations_coordinator",
        name="ARIA",
        autonomyLevel=2,
        trustScore=85.0,
        status=AgentStatus.idle,
        lastAction="Monitoring queue depths",
        lastActionAt=0.0,
        actionsThisTick=0,
        currentBuildingId="orchestration_center",
        targetBuildingId=None,
    ),
    Agent(
        id="incident_resp",
        type="incident_response",
        name="SENTINEL",
        autonomyLevel=2,
        trustScore=90.0,
        status=AgentStatus.idle,
        lastAction="All systems nominal",
        lastActionAt=0.0,
        actionsThisTick=0,
        currentBuildingId="cloud_datacenter",
        targetBuildingId=None,
    ),
    Agent(
        id="compliance",
        type="compliance",
        name="VERITAS",
        autonomyLevel=1,
        trustScore=78.0,
        status=AgentStatus.idle,
        lastAction="Compliance checks passed",
        lastActionAt=0.0,
        actionsThisTick=0,
        currentBuildingId="hospital",
        targetBuildingId=None,
    ),
    Agent(
        id="comms",
        type="communications",
        name="ECHO",
        autonomyLevel=2,
        trustScore=82.0,
        status=AgentStatus.idle,
        lastAction="Alerts synchronized",
        lastActionAt=0.0,
        actionsThisTick=0,
        currentBuildingId="comms_hub",
        targetBuildingId=None,
    ),
    Agent(
        id="exec_strategy",
        type="executive_strategy",
        name="APEX",
        autonomyLevel=1,
        trustScore=88.0,
        status=AgentStatus.idle,
        lastAction="KPIs within targets",
        lastActionAt=0.0,
        actionsThisTick=0,
        currentBuildingId="orchestration_center",
        targetBuildingId=None,
    ),
]


def get_initial_buildings() -> List[Building]:
    """Return a deep copy of the initial building config."""
    return [b.model_copy(deep=True) for b in _BUILDINGS_RAW]


def get_initial_workflows() -> List[Workflow]:
    """Return a deep copy of the initial workflow config."""
    return [w.model_copy(deep=True) for w in _INITIAL_WORKFLOWS_RAW]


def get_initial_agents() -> List[Agent]:
    """Return a deep copy of the initial agent config."""
    return [a.model_copy(deep=True) for a in _AGENTS_RAW]
