from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AgentType(str, Enum):
    operations_coordinator = "operations_coordinator"
    incident_response = "incident_response"
    compliance = "compliance"
    communications = "communications"
    executive_strategy = "executive_strategy"


class AgentStatus(str, Enum):
    idle = "idle"
    analyzing = "analyzing"
    acting = "acting"
    escalating = "escalating"
    blocked = "blocked"


class AutonomyLevel(int, Enum):
    level_0 = 0
    level_1 = 1
    level_2 = 2
    level_3 = 3
    level_4 = 4


class Agent(BaseModel):
    id: str
    type: AgentType
    name: str
    autonomyLevel: int = Field(2, ge=0, le=4)
    trustScore: float = Field(85.0, ge=0.0, le=100.0)
    status: AgentStatus = AgentStatus.idle
    lastAction: str = "Initializing"
    lastActionAt: float = 0.0
    actionsThisTick: int = 0
    targetBuildingId: Optional[str] = None
    currentBuildingId: Optional[str] = None
