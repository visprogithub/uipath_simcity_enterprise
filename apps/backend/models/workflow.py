from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class WorkflowType(str, Enum):
    ehr_record = "ehr_record"
    prescription = "prescription"
    comm_packet = "comm_packet"
    approval_request = "approval_request"
    escalation = "escalation"
    failover_cmd = "failover_cmd"
    staffing_request = "staffing_request"


class WorkflowStatus(str, Enum):
    flowing = "flowing"
    queued = "queued"
    blocked = "blocked"
    rerouted = "rerouted"
    failed = "failed"
    escalated = "escalated"


class WorkflowPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Workflow(BaseModel):
    id: str
    type: WorkflowType
    sourceId: str
    destId: str
    priority: WorkflowPriority = WorkflowPriority.medium
    status: WorkflowStatus = WorkflowStatus.flowing
    automationEligible: bool = True
    risk: float = Field(0.1, ge=0.0, le=1.0)
    progress: float = Field(0.0, ge=0.0, le=1.0)
    uipathJobId: Optional[str] = None
    # True while a critical-priority workflow is genuinely paused awaiting a human
    # decision. Survives the per-tick status recompute so the block is real (an
    # approval that doesn't actually hold the workflow is just noise). Cleared on
    # approve (resume) or reject (escalate/fail).
    awaitingApproval: bool = False
