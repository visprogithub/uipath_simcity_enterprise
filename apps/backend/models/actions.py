from typing import Annotated, Any, Dict, Literal, Optional, Union
from pydantic import BaseModel, Field


class TriggerOutageAction(BaseModel):
    type: Literal["trigger_outage"] = "trigger_outage"
    buildingId: str
    severity: Literal["partial", "full"] = "partial"


class SetStaffingAction(BaseModel):
    type: Literal["set_staffing"] = "set_staffing"
    buildingId: str
    level: float = Field(..., ge=0, le=100)


class SetAutonomyAction(BaseModel):
    type: Literal["set_autonomy"] = "set_autonomy"
    agentId: Optional[str] = None  # None = apply globally
    level: int = Field(..., ge=0, le=4)


class ActivateFailoverAction(BaseModel):
    type: Literal["activate_failover"] = "activate_failover"
    targetBuildingId: str


class AcknowledgeAlertAction(BaseModel):
    type: Literal["acknowledge_alert"] = "acknowledge_alert"
    alertId: str


class RestoreBuildingAction(BaseModel):
    type: Literal["restore_building"] = "restore_building"
    buildingId: str


class TriggerUiPathAction(BaseModel):
    type: Literal["trigger_uipath"] = "trigger_uipath"
    processName: str
    inputArgs: Dict[str, Any] = Field(default_factory=dict)


PlayerAction = Annotated[
    Union[
        TriggerOutageAction,
        SetStaffingAction,
        SetAutonomyAction,
        ActivateFailoverAction,
        AcknowledgeAlertAction,
        RestoreBuildingAction,
        TriggerUiPathAction,
    ],
    Field(discriminator="type"),
]
