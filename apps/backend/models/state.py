from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from models.building import Building
from models.workflow import Workflow
from models.agent import Agent


class SimulationMetrics(BaseModel):
    operationalStability: float = Field(100.0, ge=0.0, le=100.0)
    humanStrain: float = Field(0.0, ge=0.0, le=100.0)
    automationConfidence: float = Field(100.0, ge=0.0, le=100.0)
    serviceAvailability: float = Field(100.0, ge=0.0, le=100.0)
    systemTrust: float = Field(100.0, ge=0.0, le=100.0)
    resourceCapacity: float = Field(100.0, ge=0.0, le=100.0)


class AlertSeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class Alert(BaseModel):
    id: str
    severity: AlertSeverity
    message: str
    buildingId: Optional[str] = None
    agentId: Optional[str] = None
    workflowId: Optional[str] = None
    timestamp: float
    acknowledged: bool = False


class SimulationEventType(str, Enum):
    outage_started = "outage_started"
    outage_recovered = "outage_recovered"
    escalation_triggered = "escalation_triggered"
    approval_required = "approval_required"
    approval_granted = "approval_granted"
    agent_action = "agent_action"
    player_action = "player_action"
    failover_activated = "failover_activated"
    trust_drop = "trust_drop"
    staffing_overload = "staffing_overload"
    uipath_job_started = "uipath_job_started"
    uipath_job_completed = "uipath_job_completed"
    cascade_propagated = "cascade_propagated"


class SimulationEvent(BaseModel):
    id: str
    type: SimulationEventType
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float
    tick: int


class GamePhase(str, Enum):
    healthy = "healthy"
    degrading = "degrading"
    crisis = "crisis"
    recovering = "recovering"
    collapsed = "collapsed"


class UiPathJob(BaseModel):
    id: str
    processName: str
    state: str = "Pending"  # 'Pending' | 'Running' | 'Successful' | 'Faulted' | 'Stopped'
    startedAt: float
    simulationContext: str = ""


class UiPathApproval(BaseModel):
    id: str
    title: str
    description: str
    requestedBy: str
    severity: AlertSeverity = AlertSeverity.warning
    createdAt: float


class UiPathStatus(BaseModel):
    connected: bool = False
    activeJobs: List[UiPathJob] = Field(default_factory=list)
    pendingApprovals: List[UiPathApproval] = Field(default_factory=list)
    lastSync: float = 0.0


class SimulationState(BaseModel):
    tick: int
    timestamp: float
    phase: GamePhase
    buildings: List[Building]
    workflows: List[Workflow]
    agents: List[Agent]
    metrics: SimulationMetrics
    alerts: List[Alert]
    recentEvents: List[SimulationEvent]
    uipathStatus: UiPathStatus
