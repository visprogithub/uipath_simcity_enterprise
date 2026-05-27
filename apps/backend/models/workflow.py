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
