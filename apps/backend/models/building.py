from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class BuildingType(str, Enum):
    hospital = "hospital"
    pharmacy = "pharmacy"
    cloud_datacenter = "cloud_datacenter"
    comms_hub = "comms_hub"
    orchestration_center = "orchestration_center"
    staffing_hr = "staffing_hr"
    backup_infra = "backup_infra"


class BuildingStatus(str, Enum):
    operational = "operational"
    degraded = "degraded"
    critical = "critical"
    offline = "offline"


class BuildingPosition(BaseModel):
    x: int = Field(..., description="Grid column (left edge)")
    y: int = Field(..., description="Grid row (top edge)")
    w: int = Field(..., description="Width in tiles")
    h: int = Field(..., description="Height in tiles")


class Building(BaseModel):
    id: str
    type: BuildingType
    name: str
    pos: BuildingPosition
    status: BuildingStatus = BuildingStatus.operational
    health: float = Field(100.0, ge=0.0, le=100.0)
    throughput: float = Field(100.0, ge=0.0, le=100.0)
    staffingLevel: float = Field(100.0, ge=0.0, le=100.0)
    trustLevel: float = Field(100.0, ge=0.0, le=100.0)
    dependencies: List[str] = Field(default_factory=list)
    queueDepth: int = Field(0, ge=0)
    recoveryCapacity: float = Field(100.0, ge=0.0, le=100.0)

    def derive_status(self) -> "BuildingStatus":
        """Derive status from health value."""
        if self.health >= 70:
            return BuildingStatus.operational
        elif self.health >= 40:
            return BuildingStatus.degraded
        elif self.health >= 15:
            return BuildingStatus.critical
        else:
            return BuildingStatus.offline

    def update_status(self) -> None:
        """Update the status field based on current health."""
        self.status = self.derive_status()

    def clamp(self) -> None:
        """Clamp all numeric fields to valid ranges."""
        self.health = max(0.0, min(100.0, self.health))
        self.throughput = max(0.0, min(100.0, self.throughput))
        self.staffingLevel = max(0.0, min(100.0, self.staffingLevel))
        self.trustLevel = max(0.0, min(100.0, self.trustLevel))
        self.recoveryCapacity = max(0.0, min(100.0, self.recoveryCapacity))
        self.queueDepth = max(0, self.queueDepth)
        self.update_status()
