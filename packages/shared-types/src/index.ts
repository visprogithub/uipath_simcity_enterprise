// ─── Entity Types ───────────────────────────────────────────────────────────

export type BuildingType =
  | 'hospital'
  | 'pharmacy'
  | 'cloud_datacenter'
  | 'comms_hub'
  | 'orchestration_center'
  | 'staffing_hr'
  | 'backup_infra';

export type BuildingStatus = 'operational' | 'degraded' | 'critical' | 'offline';

export interface BuildingPosition {
  x: number; // grid column
  y: number; // grid row
  w: number; // width in tiles
  h: number; // height in tiles
}

export interface Building {
  id: string;
  type: BuildingType;
  name: string;
  icon?: string;          // emoji shown on the sprite (decoupled from structural type)
  pos: BuildingPosition;
  status: BuildingStatus;
  health: number;       // 0-100
  throughput: number;   // 0-100
  staffingLevel: number; // 0-100
  trustLevel: number;   // 0-100
  dependencies: string[]; // building IDs this building depends on
  queueDepth: number;   // pending workflows
  recoveryCapacity: number; // 0-100
}

export type WorkflowStatus = 'flowing' | 'queued' | 'blocked' | 'rerouted' | 'failed' | 'escalated';
export type WorkflowPriority = 'low' | 'medium' | 'high' | 'critical';

export interface Workflow {
  id: string;
  type: 'ehr_record' | 'prescription' | 'comm_packet' | 'approval_request' | 'escalation' | 'failover_cmd' | 'staffing_request';
  sourceId: string;
  destId: string;
  priority: WorkflowPriority;
  status: WorkflowStatus;
  automationEligible: boolean;
  risk: number;         // 0-1
  progress: number;     // 0-1 along the path
  uipathJobId?: string; // tracked UiPath job
}

export type AgentType =
  | 'operations_coordinator'
  | 'incident_response'
  | 'compliance'
  | 'communications'
  | 'executive_strategy';

export type AgentStatus = 'idle' | 'analyzing' | 'acting' | 'escalating' | 'blocked';

export type AutonomyLevel = 0 | 1 | 2 | 3 | 4;

export interface Agent {
  id: string;
  type: AgentType;
  name: string;
  autonomyLevel: AutonomyLevel;
  trustScore: number;   // 0-100
  status: AgentStatus;
  lastAction: string;
  lastActionAt: number;
  actionsThisTick: number;
  targetBuildingId?: string; // where the drone is heading
  currentBuildingId?: string; // where it currently is
}

// ─── Metrics ────────────────────────────────────────────────────────────────

export interface SimulationMetrics {
  operationalStability: number;    // 0-100
  humanStrain: number;             // 0-100 (high = bad)
  automationConfidence: number;    // 0-100
  serviceAvailability: number;     // 0-100
  systemTrust: number;             // 0-100
  resourceCapacity: number;        // 0-100
}

// ─── Events and Alerts ──────────────────────────────────────────────────────

export type AlertSeverity = 'info' | 'warning' | 'critical';

export interface Alert {
  id: string;
  severity: AlertSeverity;
  message: string;
  buildingId?: string;
  agentId?: string;
  workflowId?: string;
  timestamp: number;
  acknowledged: boolean;
}

export type SimulationEventType =
  | 'outage_started'
  | 'outage_recovered'
  | 'escalation_triggered'
  | 'approval_required'
  | 'approval_granted'
  | 'agent_action'
  | 'player_action'
  | 'failover_activated'
  | 'trust_drop'
  | 'staffing_overload'
  | 'uipath_job_started'
  | 'uipath_job_completed'
  | 'cascade_propagated';

export interface SimulationEvent {
  id: string;
  type: SimulationEventType;
  data: Record<string, unknown>;
  timestamp: number;
  tick: number;
}

export type GamePhase = 'healthy' | 'degrading' | 'crisis' | 'recovering' | 'collapsed';

export type OverlayMode =
  | 'none'
  | 'dependency'
  | 'congestion'
  | 'trust'
  | 'staffing'
  | 'outage'
  | 'orchestration';

// ─── Full Simulation State ───────────────────────────────────────────────────

export interface SimulationState {
  tick: number;
  timestamp: number;
  phase: GamePhase;
  buildings: Building[];
  workflows: Workflow[];
  agents: Agent[];
  metrics: SimulationMetrics;
  alerts: Alert[];
  recentEvents: SimulationEvent[];
  uipathStatus: UiPathStatus;
}

export interface UiPathStatus {
  connected: boolean;
  activeJobs: UiPathJob[];
  pendingApprovals: UiPathApproval[];
  lastSync: number;
  /** "direct" = per-agent Orchestrator jobs; "maestro" = routed through the Maestro Case. */
  orchestrationMode?: 'direct' | 'maestro';
  maestroCaseProcess?: string;
}

export interface UiPathJob {
  id: string;
  processName: string;
  state: 'Pending' | 'Running' | 'Successful' | 'Faulted' | 'Stopped';
  startedAt: number;
  simulationContext: string;
}

export interface UiPathApproval {
  id: string;
  title: string;
  description: string;
  requestedBy: string;
  severity: AlertSeverity;
  createdAt: number;
}

// ─── Player Actions ──────────────────────────────────────────────────────────

export interface TriggerOutageAction {
  type: 'trigger_outage';
  buildingId: string;
  severity: 'partial' | 'full';
}

export interface SetStaffingAction {
  type: 'set_staffing';
  buildingId: string;
  level: number; // 0-100
}

export interface SetAutonomyAction {
  type: 'set_autonomy';
  agentId?: string;   // if undefined, applies globally
  level: AutonomyLevel;
}

export interface ActivateFailoverAction {
  type: 'activate_failover';
  targetBuildingId: string;
}

export interface AcknowledgeAlertAction {
  type: 'acknowledge_alert';
  alertId: string;
}

export interface RestoreBuildingAction {
  type: 'restore_building';
  buildingId: string;
}

export interface TriggerUiPathAction {
  type: 'trigger_uipath';
  processName: string;
  inputArgs: Record<string, unknown>;
}

export type PlayerAction =
  | TriggerOutageAction
  | SetStaffingAction
  | SetAutonomyAction
  | ActivateFailoverAction
  | AcknowledgeAlertAction
  | RestoreBuildingAction
  | TriggerUiPathAction;

// ─── WebSocket Messages ──────────────────────────────────────────────────────

export interface WsStateMessage {
  type: 'state';
  payload: SimulationState;
}

export interface WsActionMessage {
  type: 'action';
  payload: PlayerAction;
}

export interface WsAckMessage {
  type: 'ack';
  actionId: string;
  success: boolean;
  error?: string;
}

export type WsClientMessage = WsActionMessage;
export type WsServerMessage = WsStateMessage | WsAckMessage;
