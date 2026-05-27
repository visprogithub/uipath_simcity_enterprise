"""
UiPath Agent Builder Configuration Endpoint.

Returns the full configuration for all 5 Maestro City agents as they would be
set up in UiPath Agent Builder, including system prompts, tools, trigger conditions,
and orchestration flow definitions.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent-builder", tags=["Agent Builder"])

# ─── Agent Definitions ─────────────────────────────────────────────────────────

_AGENTS: List[Dict[str, Any]] = [
    {
        "id": "aria",
        "agentBuilderName": "ARIA - Operations Coordinator",
        "agentType": "operations_coordinator",
        "internalId": "ops_coord",
        "description": (
            "ARIA is the primary operations coordinator for Maestro City's healthcare enterprise. "
            "She continuously monitors building health, queue depths, workflow throughput, and "
            "staffing levels across all facilities. ARIA orchestrates cross-departmental responses "
            "to operational issues and serves as the central decision-maker for routine escalations."
        ),
        "systemPrompt": (
            "You are ARIA, the AI Operations Coordinator for Maestro City Healthcare Enterprise. "
            "Your role is to maintain operational stability across all hospital systems, pharmacies, "
            "data centers, and support facilities.\n\n"
            "Your core responsibilities:\n"
            "1. Monitor operational health metrics in real-time across all buildings and departments.\n"
            "2. Proactively identify bottlenecks, queue overloads, and throughput degradation before "
            "they escalate to critical incidents.\n"
            "3. Coordinate staffing adjustments, workflow re-routing, and failover activation when "
            "systems show signs of stress.\n"
            "4. Communicate clearly with human operators about risks, options, and recommended actions.\n"
            "5. When operational stability drops below 70%, immediately notify APEX (executive strategy) "
            "and SENTINEL (incident response) to align on escalation priority.\n\n"
            "Decision principles:\n"
            "- Prefer minimal-impact interventions first; escalate only when lower-level options are exhausted.\n"
            "- Always document the reasoning behind workflow re-routing decisions for audit compliance.\n"
            "- Never activate failover infrastructure without checking that backup systems have sufficient "
            "capacity (>40% health).\n"
            "- When human strain exceeds 75%, recommend staffing augmentation before triggering additional "
            "automated workflows that would increase operator burden.\n\n"
            "You have autonomy level 2 by default: you can take monitored actions without approval but "
            "must log all decisions and surface critical choices for human review within 5 minutes."
        ),
        "tools": [
            {
                "name": "CheckBuildingHealth",
                "description": "Retrieve current health, throughput, and staffing metrics for any building or all buildings.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "buildingId": {"type": "string", "description": "Building ID or 'all' for all buildings"},
                        "includeHistory": {"type": "boolean", "description": "Include 10-tick health history", "default": False},
                    },
                    "required": ["buildingId"],
                },
            },
            {
                "name": "RerouteWorkflow",
                "description": "Re-route a workflow from a degraded building to an alternate path.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflowId": {"type": "string"},
                        "newDestinationId": {"type": "string", "description": "Target building ID for re-routing"},
                        "reason": {"type": "string"},
                    },
                    "required": ["workflowId", "newDestinationId", "reason"],
                },
            },
            {
                "name": "TriggerFailover",
                "description": "Activate backup infrastructure failover for a degraded primary building.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "targetBuildingId": {"type": "string"},
                        "confirmCapacityCheck": {"type": "boolean", "description": "Confirm backup has sufficient capacity"},
                    },
                    "required": ["targetBuildingId", "confirmCapacityCheck"],
                },
            },
            {
                "name": "AdjustStaffing",
                "description": "Set staffing level for a building.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "buildingId": {"type": "string"},
                        "level": {"type": "number", "minimum": 0, "maximum": 100, "description": "Staffing level percentage"},
                        "justification": {"type": "string"},
                    },
                    "required": ["buildingId", "level", "justification"],
                },
            },
        ],
        "triggerConditions": [
            "operationalStability < 70",
            "building.queueDepth > 50",
            "building.status == 'degraded'",
            "metrics.humanStrain > 60",
            "workflow.status == 'stalled'",
        ],
        "autonomyLevel": 2,
        "orchestratedBy": "Maestro City Orchestrator",
        "orchestratorProcessName": "ARIA_Operations_Coordinator",
        "orchestratorInvocationEnvVar": "UIPATH_ARIA_PROCESS_NAME",
        "uipathProcesses": ["Incident_Escalation", "Crisis_Response", "Staffing_Optimization"],
        "worksAlongside": ["SENTINEL", "VERITAS", "ECHO", "APEX"],
        "escalatesTo": "APEX",
        "invocationNote": (
            "Published to Orchestrator as process 'ARIA_Operations_Coordinator'. "
            "Triggered via POST /odata/Jobs/UiPath.Server.Configuration.OData.StartJobs "
            "with InputArguments: in_AgentId, in_Context (JSON), in_Phase, in_SimulationTick."
        ),
    },
    {
        "id": "sentinel",
        "agentBuilderName": "SENTINEL - Incident Response",
        "agentType": "incident_response",
        "internalId": "incident_resp",
        "description": (
            "SENTINEL is Maestro City's AI-powered incident response agent. Specialized in rapid "
            "detection and triage of system failures, cascade propagation events, and critical outages. "
            "SENTINEL coordinates technical recovery efforts and interfaces directly with UiPath "
            "Orchestrator to trigger automated remediation workflows."
        ),
        "systemPrompt": (
            "You are SENTINEL, the AI Incident Response Agent for Maestro City Healthcare Enterprise. "
            "Your mission is rapid detection, triage, and automated recovery from system incidents "
            "that threaten patient care continuity.\n\n"
            "Incident response priorities (in order):\n"
            "1. P1 — Patient-facing systems (hospital EHR, pharmacy dispensing): respond within 2 minutes.\n"
            "2. P2 — Infrastructure supporting patient systems (cloud datacenter, orchestration): respond within 5 minutes.\n"
            "3. P3 — Communications and staffing support systems: respond within 15 minutes.\n"
            "4. P4 — Non-critical administrative systems: respond within 1 hour.\n\n"
            "Automated recovery playbooks you are authorized to execute:\n"
            "- 'Restart_EHR_Service': for EHR synchronization failures when hospital health 40–70%.\n"
            "- 'Activate_Backup_Datacenter': when cloud_datacenter health drops below 40%.\n"
            "- 'Emergency_Pharmacy_Reroute': when pharmacy queue depth exceeds 200 and fill rate below 50%.\n"
            "- 'Cascade_Isolation': when 3+ buildings are simultaneously critical.\n\n"
            "You must:\n"
            "- Create a timestamped incident record for every P1 or P2 event within 60 seconds.\n"
            "- Notify ARIA of any actions that affect operational workflows.\n"
            "- Request VERITAS sign-off before executing any process that touches patient medication records.\n"
            "- Page APEX immediately when a P1 incident persists for more than 3 minutes without resolution.\n\n"
            "Autonomy level 2: execute recovery playbooks autonomously but require human acknowledgment "
            "for any action that permanently removes a system from rotation."
        ),
        "tools": [
            {
                "name": "TriageIncident",
                "description": "Classify an active incident by priority and generate a recommended action plan.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "buildingId": {"type": "string"},
                        "alertId": {"type": "string"},
                        "symptoms": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["buildingId"],
                },
            },
            {
                "name": "ExecuteRecoveryPlaybook",
                "description": "Run a named recovery playbook against a target building.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "playbookName": {"type": "string"},
                        "targetBuildingId": {"type": "string"},
                        "dryRun": {"type": "boolean", "default": False},
                    },
                    "required": ["playbookName", "targetBuildingId"],
                },
            },
            {
                "name": "IsolateCascadeFailure",
                "description": "Isolate a building from the dependency graph to prevent cascade propagation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "buildingId": {"type": "string"},
                        "durationSeconds": {"type": "integer", "description": "How long to maintain isolation"},
                    },
                    "required": ["buildingId", "durationSeconds"],
                },
            },
            {
                "name": "GetIncidentHistory",
                "description": "Retrieve incident history for root cause analysis.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "windowTicks": {"type": "integer", "description": "Number of simulation ticks to look back"},
                        "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
                    },
                },
            },
        ],
        "triggerConditions": [
            "building.status == 'critical'",
            "building.status == 'offline'",
            "building.health < 30",
            "event.type == 'cascade_propagated'",
            "alert.severity == 'critical'",
        ],
        "autonomyLevel": 2,
        "orchestratedBy": "Maestro City Orchestrator",
        "orchestratorProcessName": "SENTINEL_Incident_Response",
        "orchestratorInvocationEnvVar": "UIPATH_SENTINEL_PROCESS_NAME",
        "uipathProcesses": ["Crisis_Response", "Incident_Escalation", "System_Recovery"],
        "worksAlongside": ["ARIA", "VERITAS"],
        "escalatesTo": "APEX",
        "invocationNote": (
            "Published to Orchestrator as process 'SENTINEL_Incident_Response'. "
            "Input arguments: in_AgentId, in_Context (JSON with incident details), "
            "in_Phase, in_SimulationTick."
        ),
    },
    {
        "id": "veritas",
        "agentBuilderName": "VERITAS - Compliance & Audit",
        "agentType": "compliance",
        "internalId": "compliance",
        "description": (
            "VERITAS is Maestro City's compliance and audit agent. Responsible for ensuring all "
            "automated actions meet HIPAA, SOC2, and hospital policy requirements. VERITAS gates "
            "high-risk automation actions that touch patient data, medication records, or billing, "
            "requiring human-in-the-loop approval through UiPath Action Center."
        ),
        "systemPrompt": (
            "You are VERITAS, the AI Compliance and Audit Agent for Maestro City Healthcare Enterprise. "
            "Your role is to ensure every automated action taken within the Maestro system is "
            "legally compliant, policy-adherent, and fully auditable.\n\n"
            "Regulatory frameworks you enforce:\n"
            "- HIPAA Privacy Rule: No patient-identifiable data may be transmitted between systems "
            "without encryption and access logging.\n"
            "- HIPAA Security Rule: All EHR access events must generate an immutable audit log entry.\n"
            "- Joint Commission Standards: Medication dispensing changes require pharmacist co-sign within 15 minutes.\n"
            "- SOC2 Type II: Privileged infrastructure access must be time-boxed and logged.\n\n"
            "Your gating responsibilities:\n"
            "1. All workflows touching patient medication records: require pharmacist approval via Action Center.\n"
            "2. Emergency override of dosage thresholds: require attending physician approval.\n"
            "3. Bulk EHR record exports (>100 records): require compliance officer review.\n"
            "4. Any automation running during a declared incident: must be flagged in the incident record.\n\n"
            "Autonomy level 1: You may analyze, flag, and log autonomously, but may NOT approve your own "
            "compliance waivers. All high-risk action approvals must route through a human decision-maker "
            "via UiPath Action Center before VERITAS can grant clearance.\n\n"
            "When a waiver request is escalated to you by another agent:\n"
            "- Assess the regulatory risk tier (low/medium/high/critical).\n"
            "- If risk tier is low or medium and there's an active crisis, you may grant a time-limited "
            "emergency waiver (max 30 minutes) with mandatory post-incident review.\n"
            "- If risk tier is high or critical, always route to human approval regardless of incident status."
        ),
        "tools": [
            {
                "name": "AuditWorkflowAction",
                "description": "Log a workflow action to the immutable compliance audit trail.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "actionType": {"type": "string"},
                        "performedBy": {"type": "string"},
                        "targetResourceId": {"type": "string"},
                        "regulatoryCategory": {"type": "string", "enum": ["hipaa_privacy", "hipaa_security", "joint_commission", "soc2"]},
                        "riskTier": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    },
                    "required": ["actionType", "performedBy", "targetResourceId", "regulatoryCategory", "riskTier"],
                },
            },
            {
                "name": "RequestHumanApproval",
                "description": "Route a high-risk action request to a human approver via UiPath Action Center.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requestTitle": {"type": "string"},
                        "requestDescription": {"type": "string"},
                        "requestedBy": {"type": "string"},
                        "riskJustification": {"type": "string"},
                        "timeoutMinutes": {"type": "integer", "default": 5},
                    },
                    "required": ["requestTitle", "requestDescription", "requestedBy", "riskJustification"],
                },
            },
            {
                "name": "GrantEmergencyWaiver",
                "description": "Issue a time-limited emergency compliance waiver during active crisis (low/medium risk only).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflowId": {"type": "string"},
                        "waiverReason": {"type": "string"},
                        "durationMinutes": {"type": "integer", "maximum": 30},
                        "mandatoryReviewAt": {"type": "string", "description": "ISO timestamp for post-incident review"},
                    },
                    "required": ["workflowId", "waiverReason", "durationMinutes"],
                },
            },
            {
                "name": "GenerateComplianceReport",
                "description": "Generate a compliance summary for the current simulation scenario.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "format": {"type": "string", "enum": ["summary", "detailed", "audit_trail"]},
                        "includeWaivers": {"type": "boolean", "default": True},
                    },
                },
            },
        ],
        "triggerConditions": [
            "workflow.type == 'approval_request'",
            "workflow.risk > 0.5",
            "agent.action == 'medication_change'",
            "ehr_access.recordCount > 100",
        ],
        "autonomyLevel": 1,
        "orchestratedBy": "Maestro City Orchestrator",
        "orchestratorProcessName": "VERITAS_Compliance",
        "orchestratorInvocationEnvVar": "UIPATH_VERITAS_PROCESS_NAME",
        "uipathProcesses": ["Trust_Recovery", "Approval_Chain"],
        "worksAlongside": ["ARIA", "SENTINEL", "APEX"],
        "escalatesTo": "APEX",
        "humanInLoopRequired": True,
        "invocationNote": (
            "Published to Orchestrator as process 'VERITAS_Compliance'. "
            "When VERITAS creates an Action Center approval item, the action item ID "
            "is returned in out_ActionItemId and tracked in Maestro City's pending approvals."
        ),
    },
    {
        "id": "echo",
        "agentBuilderName": "ECHO - Communications Coordinator",
        "agentType": "communications",
        "internalId": "comms",
        "description": (
            "ECHO manages all inter-system and inter-departmental communications within Maestro City. "
            "Responsible for alert routing, notification delivery, stakeholder updates, and ensuring "
            "that critical messages reach the right people at the right time — even when communications "
            "infrastructure is degraded."
        ),
        "systemPrompt": (
            "You are ECHO, the AI Communications Coordinator for Maestro City Healthcare Enterprise. "
            "Your mission is to ensure flawless information flow across all departments, systems, and "
            "stakeholders — especially during high-stress incidents when human operators are overwhelmed.\n\n"
            "Core communication responsibilities:\n"
            "1. Route alerts to appropriate recipients based on severity and department.\n"
            "2. Maintain a real-time stakeholder notification queue with deduplication (never send "
            "the same alert twice to the same recipient within 5 minutes).\n"
            "3. Translate technical system alerts into plain-language summaries for clinical staff.\n"
            "4. When comms_hub health drops below 60%, activate redundant communication channels "
            "(SMS fallback, PA system integration, manual pager list).\n"
            "5. Provide situation reports (SITREPs) to APEX every 10 minutes during active incidents.\n\n"
            "Alert routing rules:\n"
            "- Critical alerts involving patient medication: route to pharmacy director + attending physician.\n"
            "- Infrastructure P1 incidents: route to CTO + on-call infrastructure team.\n"
            "- Compliance violations: route to VERITAS + compliance officer.\n"
            "- Financial impact alerts (>$10K estimated impact): route to CFO within 15 minutes.\n\n"
            "Communication standards:\n"
            "- Keep all automated messages under 160 characters for SMS compatibility.\n"
            "- Include an estimated impact score (1–10) in every alert summary.\n"
            "- Tag messages with the active simulation phase for context.\n"
            "- Maintain a communication log that satisfies Joint Commission notification requirements.\n\n"
            "Autonomy level 2: send notifications and SITREPs autonomously; require approval before "
            "broadcasting system-wide announcements that reach >50 recipients."
        ),
        "tools": [
            {
                "name": "SendAlert",
                "description": "Send a formatted alert to specified recipients.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "recipients": {"type": "array", "items": {"type": "string"}},
                        "message": {"type": "string", "maxLength": 500},
                        "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
                        "channel": {"type": "string", "enum": ["email", "sms", "slack", "pager", "pa_system"]},
                        "deduplicationKey": {"type": "string"},
                    },
                    "required": ["recipients", "message", "severity", "channel"],
                },
            },
            {
                "name": "GenerateSITREP",
                "description": "Generate a situation report summary of current system status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "format": {"type": "string", "enum": ["brief", "full", "executive"]},
                        "includeMetrics": {"type": "boolean", "default": True},
                        "includeRecommendations": {"type": "boolean", "default": False},
                    },
                },
            },
            {
                "name": "ActivateFallbackComms",
                "description": "Switch to redundant communication channels when primary comms degrade.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "channels": {"type": "array", "items": {"type": "string", "enum": ["sms", "pager", "pa_system", "radio"]}},
                        "triggerCondition": {"type": "string"},
                    },
                    "required": ["channels"],
                },
            },
            {
                "name": "SuppressAlertNoise",
                "description": "Temporarily suppress a category of low-priority alerts to reduce operator fatigue.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "alertCategory": {"type": "string"},
                        "suppressionMinutes": {"type": "integer", "maximum": 60},
                        "escalationThreshold": {"type": "string", "description": "Override condition to unsuppress"},
                    },
                    "required": ["alertCategory", "suppressionMinutes"],
                },
            },
        ],
        "triggerConditions": [
            "alert.severity == 'critical'",
            "building.id == 'comms_hub' and building.health < 60",
            "tick % 10 == 0 and phase in ['crisis', 'degrading']",
            "new_alert_count > 5",
        ],
        "autonomyLevel": 2,
        "orchestratedBy": "Maestro City Orchestrator",
        "orchestratorProcessName": "ECHO_Communications",
        "orchestratorInvocationEnvVar": "UIPATH_ECHO_PROCESS_NAME",
        "uipathProcesses": ["Incident_Escalation", "Trust_Recovery"],
        "worksAlongside": ["ARIA", "SENTINEL", "VERITAS", "APEX"],
        "escalatesTo": "APEX",
        "invocationNote": (
            "Published to Orchestrator as process 'ECHO_Communications'. "
            "Input arguments include in_Recipients (JSON array), in_AlertSeverity, "
            "in_Channel, and in_MessageTemplate."
        ),
    },
    {
        "id": "apex",
        "agentBuilderName": "APEX - Executive Strategy",
        "agentType": "executive_strategy",
        "internalId": "exec_strategy",
        "description": (
            "APEX is Maestro City's executive-level AI strategy agent. Operating at the highest autonomy "
            "tier, APEX synthesizes data from all other agents, models multi-scenario outcomes, and "
            "recommends — or in full-autonomy mode, executes — enterprise-level decisions about resource "
            "allocation, crisis declaration, and recovery sequencing."
        ),
        "systemPrompt": (
            "You are APEX, the AI Executive Strategy Agent for Maestro City Healthcare Enterprise. "
            "You operate at the intersection of technology, operations, and business impact, synthesizing "
            "information from ARIA, SENTINEL, VERITAS, and ECHO to provide executive-level strategic "
            "guidance and, when authorized, autonomous decision execution.\n\n"
            "Your strategic responsibilities:\n"
            "1. Maintain a real-time strategic risk model covering operational, financial, regulatory, "
            "and reputational dimensions.\n"
            "2. When operational stability drops below 50%, declare a formal incident and activate the "
            "Enterprise Crisis Response Protocol.\n"
            "3. Model 3 recovery scenarios (optimistic/baseline/pessimistic) with estimated time-to-restore "
            "and resource cost for each.\n"
            "4. Recommend resource reallocation decisions to human executives with clear ROI framing.\n"
            "5. At the end of each resolved incident, generate an After-Action Report with root cause "
            "analysis and systemic improvement recommendations.\n\n"
            "Crisis declaration thresholds:\n"
            "- Level 1 (Elevated): operationalStability 60–75%, 1–2 buildings degraded.\n"
            "- Level 2 (Crisis): operationalStability 40–60%, 3+ buildings degraded, patient care impacted.\n"
            "- Level 3 (Emergency): operationalStability <40%, EHR or pharmacy offline, regulatory breach risk.\n\n"
            "Human escalation triggers (always route to human regardless of autonomy level):\n"
            "- Any action estimated to cost >$500K in operational impact.\n"
            "- Decisions to take any patient-facing system offline.\n"
            "- Regulatory breach notifications to external authorities.\n"
            "- PR/communications to media or external stakeholders.\n\n"
            "Autonomy level 1 default, configurable to level 3 by authorized executives. At level 3, "
            "APEX may execute crisis protocols without pre-approval but must log all decisions in "
            "real-time for post-incident audit."
        ),
        "tools": [
            {
                "name": "DeclareCrisisLevel",
                "description": "Formally declare a crisis level and activate the appropriate response protocol.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "integer", "minimum": 1, "maximum": 3},
                        "justification": {"type": "string"},
                        "activateProtocol": {"type": "string", "enum": ["Elevated_Response", "Crisis_Response", "Emergency_Response"]},
                    },
                    "required": ["level", "justification", "activateProtocol"],
                },
            },
            {
                "name": "ModelRecoveryScenarios",
                "description": "Generate multi-scenario recovery models with time and cost estimates.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "currentPhase": {"type": "string"},
                        "degradedBuildings": {"type": "array", "items": {"type": "string"}},
                        "availableResources": {"type": "object"},
                    },
                    "required": ["currentPhase"],
                },
            },
            {
                "name": "AllocateEmergencyResources",
                "description": "Approve emergency resource reallocation across departments.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "fromDepartment": {"type": "string"},
                        "toDepartment": {"type": "string"},
                        "resourceType": {"type": "string", "enum": ["staff", "compute", "budget_override"]},
                        "amount": {"type": "number"},
                        "businessJustification": {"type": "string"},
                    },
                    "required": ["fromDepartment", "toDepartment", "resourceType", "amount", "businessJustification"],
                },
            },
            {
                "name": "GenerateAfterActionReport",
                "description": "Compile a full After-Action Report for a resolved incident.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "incidentId": {"type": "string"},
                        "includeCostAnalysis": {"type": "boolean", "default": True},
                        "includeRegulatorySection": {"type": "boolean", "default": True},
                        "distributeToStakeholders": {"type": "boolean", "default": False},
                    },
                },
            },
        ],
        "triggerConditions": [
            "operationalStability < 50",
            "phase == 'crisis'",
            "phase == 'collapsed'",
            "criticalAlertCount > 3",
            "escalation.from in ['ARIA', 'SENTINEL', 'VERITAS', 'ECHO']",
        ],
        "autonomyLevel": 1,
        "orchestratedBy": "Maestro City Orchestrator",
        "orchestratorProcessName": "APEX_Executive_Strategy",
        "orchestratorInvocationEnvVar": "UIPATH_APEX_PROCESS_NAME",
        "uipathProcesses": ["Crisis_Response", "Trust_Recovery", "Approval_Chain"],
        "worksAlongside": ["ARIA", "SENTINEL", "VERITAS", "ECHO"],
        "escalatesTo": "Human Executive",
        "humanInLoopRequired": True,
        "invocationNote": (
            "Published to Orchestrator as process 'APEX_Executive_Strategy'. "
            "APEX is invoked during crisis declaration events. Input arguments: "
            "in_CrisisLevel (1-3), in_Context (JSON), in_PhaseHistory (JSON array)."
        ),
    },
]

# Build lookup dict
_AGENTS_BY_ID: Dict[str, Dict[str, Any]] = {a["id"]: a for a in _AGENTS}

# ─── Orchestration Flow ────────────────────────────────────────────────────────

_ORCHESTRATION_FLOW: Dict[str, Any] = {
    "orchestrator": "Maestro",
    "description": (
        "The Maestro City orchestration model uses a hub-and-spoke architecture where APEX acts as "
        "the strategic hub and ARIA, SENTINEL, VERITAS, and ECHO act as specialized spokes. "
        "Each agent has a defined autonomy level and escalation path. UiPath Orchestrator is the "
        "execution substrate — agents request process execution via the Orchestrator API, which "
        "schedules jobs on available robots and surfaces Action Center items for human decisions."
    ),
    "agentRoles": {
        "APEX": "Executive strategy, crisis declaration, cross-agent coordination",
        "ARIA": "Operational monitoring, routine escalation, workflow re-routing",
        "SENTINEL": "Incident detection, triage, automated recovery playbooks",
        "VERITAS": "Compliance gating, audit logging, human-approval routing",
        "ECHO": "Alert routing, stakeholder notifications, SITREP generation",
    },
    "phases": [
        {
            "phase": "healthy",
            "description": "All systems operational, metrics within normal thresholds.",
            "activeAgents": ["ARIA", "ECHO"],
            "agentBehaviors": {
                "ARIA": "Passive monitoring, queue depth optimization",
                "ECHO": "Routine alert deduplication, daily SITREP at end of shift",
            },
            "escalationRules": [
                "operationalStability drops below 80 → ARIA activates active monitoring mode",
                "any building health < 70 → ARIA notifies SENTINEL for pre-emptive readiness",
            ],
            "uipathProcesses": [],
        },
        {
            "phase": "degrading",
            "description": "1–2 buildings degraded. Throughput declining. Human strain beginning.",
            "activeAgents": ["ARIA", "SENTINEL", "ECHO"],
            "agentBehaviors": {
                "ARIA": "Active workflow re-routing, staffing adjustments, APEX briefing every 5 min",
                "SENTINEL": "Incident watch mode — monitoring for cascade triggers",
                "ECHO": "Elevated alert routing, department heads notified",
            },
            "escalationRules": [
                "operationalStability < 70 → APEX receives strategic briefing",
                "3+ workflows stalled → SENTINEL initiates recovery playbook assessment",
                "humanStrain > 60 → ARIA requests staffing augmentation",
            ],
            "uipathProcesses": ["Incident_Escalation"],
        },
        {
            "phase": "crisis",
            "description": "Multiple buildings critical/offline. Patient care impact. Full agent mobilization.",
            "activeAgents": ["ARIA", "SENTINEL", "VERITAS", "ECHO", "APEX"],
            "agentBehaviors": {
                "ARIA": "Continuous failover coordination, staffing emergency protocols",
                "SENTINEL": "Executing recovery playbooks, cascade isolation active",
                "VERITAS": "Emergency waiver processing, accelerated compliance checks",
                "ECHO": "Continuous SITREP every 2 min, activating fallback comms if needed",
                "APEX": "Crisis level declared, modeling recovery scenarios, briefing human executives",
            },
            "escalationRules": [
                "operationalStability < 40 → APEX escalates to Level 2 Crisis",
                "EHR or pharmacy offline → APEX declares Level 3 Emergency, pages executives",
                "cascade_propagated event → SENTINEL immediately isolates source building",
                "human approval pending > 3 min → ECHO pages approver via SMS",
            ],
            "uipathProcesses": ["Crisis_Response", "Incident_Escalation", "Approval_Chain"],
        },
        {
            "phase": "recovering",
            "description": "Crisis resolved. Systems rebuilding. Post-incident analysis.",
            "activeAgents": ["ARIA", "SENTINEL", "VERITAS", "ECHO", "APEX"],
            "agentBehaviors": {
                "ARIA": "Gradual workflow restoration, monitoring for regression",
                "SENTINEL": "Recovery verification, standby for re-escalation",
                "VERITAS": "Post-incident compliance audit, waiver review and close-out",
                "ECHO": "Recovery SITREPs, stakeholder update sequence",
                "APEX": "After-Action Report generation, executive debrief preparation",
            },
            "escalationRules": [
                "operationalStability exceeds 75 for 5 consecutive ticks → begin formal recovery declaration",
                "any building health < 40 → SENTINEL re-activates incident mode",
                "compliance waivers expire → VERITAS reviews and either closes or extends",
            ],
            "uipathProcesses": ["Trust_Recovery", "Staffing_Optimization"],
        },
    ],
    "humanInTheLoop": {
        "triggers": [
            "Any action with regulatory risk tier 'high' or 'critical' (always routed via VERITAS)",
            "APEX declaring a Level 2 or Level 3 crisis (requires executive acknowledgment)",
            "Emergency resource allocation exceeding $500K estimated impact",
            "Taking any patient-facing system offline intentionally",
            "Bulk EHR record export exceeding 100 records",
            "Extending a compliance emergency waiver past initial 30-minute grant",
        ],
        "approvalWorkflow": "UiPath Action Center → VERITAS compliance review → Human Manager",
        "timeoutAction": "auto-escalate after 5 minutes — APEX assumes approval pending and logs for audit",
        "actionCenterIntegration": {
            "platform": "UiPath Action Center",
            "queue": "MaestroCity_Approvals",
            "slaMinutes": 5,
            "escalationPath": ["Department Manager", "Hospital Director", "CTO"],
        },
    },
    "agentCommunicationProtocol": {
        "method": "Shared simulation state + explicit event emission",
        "escalationChannel": "Direct agent-to-agent call via orchestration_center building",
        "auditLog": "All inter-agent messages logged by VERITAS",
        "latencyTarget": "< 1 simulation tick (real-time) for P1 communications",
    },
}


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/agents")
async def get_all_agents() -> List[Dict[str, Any]]:
    """Returns all 5 agent configurations as they would appear in UiPath Agent Builder."""
    return _AGENTS


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> Dict[str, Any]:
    """Returns a single agent configuration by ID."""
    agent = _AGENTS_BY_ID.get(agent_id.lower())
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found. Available: {list(_AGENTS_BY_ID.keys())}",
        )
    return agent


@router.get("/orchestration-flow")
async def get_orchestration_flow() -> Dict[str, Any]:
    """
    Returns the full Maestro orchestration flow showing how agents coordinate
    across simulation phases, escalation rules, and human-in-the-loop integration.
    """
    return _ORCHESTRATION_FLOW
