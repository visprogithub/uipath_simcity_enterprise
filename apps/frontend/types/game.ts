// Re-export all shared types
export type {
  BuildingType,
  BuildingStatus,
  BuildingPosition,
  Building,
  WorkflowStatus,
  WorkflowPriority,
  Workflow,
  AgentType,
  AgentStatus,
  AutonomyLevel,
  Agent,
  SimulationMetrics,
  AlertSeverity,
  Alert,
  SimulationEventType,
  SimulationEvent,
  GamePhase,
  OverlayMode,
  SimulationState,
  UiPathStatus,
  UiPathJob,
  UiPathApproval,
  TriggerOutageAction,
  SetStaffingAction,
  SetAutonomyAction,
  ActivateFailoverAction,
  AcknowledgeAlertAction,
  RestoreBuildingAction,
  TriggerUiPathAction,
  PlayerAction,
  WsClientMessage,
  WsServerMessage,
  WsStateMessage,
  WsActionMessage,
  WsAckMessage,
} from '@shared/index';

// ─── Frontend-specific types ─────────────────────────────────────────────────

export interface UIOverlayState {
  mode: import('@shared/index').OverlayMode;
  opacity: number;
}

export interface SparklinePoint {
  tick: number;
  value: number;
}

export interface TooltipPosition {
  x: number;
  y: number;
}

export interface BuildingTooltipData {
  buildingId: string;
  position: TooltipPosition;
}

export interface TimelineEventDisplay {
  id: string;
  type: import('@shared/index').SimulationEventType;
  label: string;
  color: string;
  tick: number;
  timestamp: number;
  buildingId?: string;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

export interface PanelTab {
  id: string;
  label: string;
  icon?: string;
}
