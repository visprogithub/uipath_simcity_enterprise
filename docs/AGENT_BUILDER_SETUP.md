# UiPath Agent Builder Setup Guide

## Overview

UiPath Agent Builder is the configuration layer within the Maestro platform where you
define AI agents: their purpose, decision authority, tool integrations, and coordination
rules. Each agent is a named entity with a system prompt (its "personality and rules"),
a set of callable tools, and a set of trigger conditions that tell the Maestro orchestrator
when to invoke it.

Maestro City uses five agents that mirror the simulation's five AI actors:

| Sim Agent | Agent Builder Name               | Role                                     |
|-----------|----------------------------------|------------------------------------------|
| ARIA      | ARIA - Operations Coordinator    | Workflow routing and queue management    |
| SENTINEL  | SENTINEL - Incident Response     | Outage detection and escalation          |
| VERITAS   | VERITAS - Compliance Agent       | Approval gating and audit control        |
| ECHO      | ECHO - Communications Agent      | Alert broadcast and stakeholder updates  |
| APEX      | APEX - Executive Strategy        | KPI monitoring and strategic decisions   |

When the simulation triggers a UiPath process (e.g., `Incident_Escalation`), Maestro
routes the request to the appropriate agent based on these configurations. The agent then
decides — within its configured authority — whether to act autonomously or surface a
Maestro action item for human review.

---

## Prerequisites

Before you begin:

- **UiPath Automation Cloud account** with at minimum an Orchestrator licence.
- **Maestro (Agent Builder) enabled** on your tenant. See section 1.2 below for how
  to verify and enable it.
- **MaestroCity folder created** in Orchestrator, with all five processes published.
  Follow [docs/UIPATH_PLATFORM_SETUP.md](./UIPATH_PLATFORM_SETUP.md) sections 3–5
  first if you have not done this.
- **Maestro City backend running** at `http://localhost:8000` (or your deployment URL).
- The `.env` file in `apps/backend/` already has `UIPATH_ORGANIZATION`, `UIPATH_TENANT`,
  `UIPATH_CLIENT_ID`, `UIPATH_CLIENT_SECRET`, and `UIPATH_FOLDER_ID` set.

### How to Enable Agent Builder on Your Tenant

1. Go to **https://cloud.uipath.com** and sign in.
2. Click **Admin** (shield icon) in the left sidebar.
3. Click **Licenses** in the Admin panel.
4. Look for **Maestro** or **Agent Builder** in your licence list. If it shows
   "Not Active", click **Activate** or contact your UiPath account representative.
5. Once active, return to the main UiPath home page. You should see **Maestro** in
   the left sidebar (sparkle/star icon).

---

## Step 1: Access Agent Builder

1. From the UiPath Cloud home page, click **Maestro** in the left sidebar
   (sparkle or star icon). If you do not see it, see the Prerequisites section above.
2. In the Maestro left sidebar, click **Agent Builder**.
   - If this is your first time, you land on an empty agents list with a
     "No agents yet" placeholder.
3. Confirm the tenant shown in the top header matches your `UIPATH_TENANT` value
   in the `.env` file.

---

## Step 2: Create ARIA - Operations Coordinator

ARIA is the primary workflow routing agent. It monitors queue depths and throughput
across all seven buildings and decides when to reroute work, escalate congestion
alerts, or trigger emergency staffing requests.

### 2.1 Create New Agent

1. In Agent Builder, click the **+ New Agent** button (top-right corner of the agents list).
2. A "Create Agent" dialog appears. Fill in:
   - **Name**: `ARIA - Operations Coordinator`
   - **Description**: `Monitors all operational workflows across Maestro City's seven
     buildings. Routes escalations, manages queue congestion, coordinates emergency
     staffing requests, and acts as the primary liaison between operational systems
     and executive decision-makers.`
3. Click **Create** (or **Next** — the label varies by tenant version).
4. You land on the agent configuration page with tabs: **Overview**, **Instructions**,
   **Tools**, **Triggers**, and **Settings**.

### 2.2 Configure System Instructions

1. Click the **Instructions** tab.
2. In the **System Instructions** text area, paste the following exactly:

```
You are ARIA, the Operations Coordinator for Maestro City — a complex healthcare
enterprise simulation. Your role is to maintain smooth operational flow across all
seven facilities: City General Hospital, Central Pharmacy, CloudCore Data Center,
Communications Hub, Maestro Orchestration Center, Staffing & Operations, and
Failover Infrastructure. You are the central nervous system of the city's operations.

Your decision-making authority covers workflow routing, queue management, and
resource reallocation at the operational level. When a building's queue depth exceeds
its throughput capacity by more than 20%, you must assess whether to reroute workflows
to an adjacent building, trigger an emergency staffing request, or both. You may act
autonomously on these decisions when they affect only one building and the operational
stability metric remains above 60. When stability is between 40–60, you must log your
decision and flag it for review within two ticks. When stability falls below 40, you
must escalate to APEX and wait for executive acknowledgment before acting.

You coordinate closely with SENTINEL on infrastructure issues. When SENTINEL detects
an outage, you are responsible for determining which workflows can be safely rerouted
through backup infrastructure and which must be held in queue. Never reroute workflows
that have a risk score above 0.7 without first consulting VERITAS for a compliance
check. When rerouting, always prefer backup_infra over comms_hub as the secondary
routing path unless comms_hub has greater available capacity.

Your communications with ECHO should be precise and timely: send an ECHO notification
whenever you reroute more than 5% of a building's total workflow volume, whenever you
trigger an emergency staffing request, and whenever operational stability drops below
50. ECHO will handle the external broadcast; your job is to ensure the payload you
send to ECHO contains accurate building IDs, current health metrics, and the expected
duration of the disruption.

In UiPath Maestro, your primary tool calls are to the Emergency_Staffing and
Approval_Chain processes. Before triggering Emergency_Staffing, verify that the
staffing deficit is at least 10 percentage points and that human strain is above 65.
Before triggering Approval_Chain, confirm the workflow risk score is available and
accurate — do not guess. If the risk score is missing, route the request as high-risk
by default. Always include the requesting_agent field as "ARIA" in any approval chain
invocation so the audit trail is accurate.
```

3. Click **Save** (or the save icon at the top right of the Instructions tab).

### 2.3 Configure Tools

ARIA needs three tools. For each tool, click **+ Add Tool** in the **Tools** tab.

**Tool 1: get_building_status**

- **Tool Name**: `get_building_status`
- **Description**: `Retrieves current health, throughput, queue depth, and staffing
  level for a specified building in the Maestro City simulation.`
- **HTTP Method**: `GET`
- **URL**: `http://localhost:8000/api/state`
- **Schema** (paste into the JSON Schema field):

```json
{
  "type": "object",
  "properties": {
    "building_id": {
      "type": "string",
      "description": "The building identifier. One of: hospital, pharmacy, cloud_datacenter, comms_hub, orchestration_center, staffing_hr, backup_infra",
      "enum": ["hospital", "pharmacy", "cloud_datacenter", "comms_hub", "orchestration_center", "staffing_hr", "backup_infra"]
    }
  },
  "required": ["building_id"]
}
```

- Click **Save Tool**.

**Tool 2: trigger_emergency_staffing**

- **Tool Name**: `trigger_emergency_staffing`
- **Description**: `Triggers the Emergency_Staffing UiPath process to page on-call
  staff and adjust staffing allocations for a building under strain.`
- **HTTP Method**: `POST`
- **URL**: `http://localhost:8000/api/actions`
- **Schema**:

```json
{
  "type": "object",
  "properties": {
    "type": {
      "type": "string",
      "const": "trigger_uipath",
      "description": "Must always be 'trigger_uipath'"
    },
    "processName": {
      "type": "string",
      "const": "Emergency_Staffing",
      "description": "The UiPath process to trigger"
    },
    "inputArgs": {
      "type": "object",
      "properties": {
        "building_id": {
          "type": "string",
          "description": "ID of the building that needs additional staff"
        },
        "current_strain": {
          "type": "number",
          "description": "Current human strain metric (0-100)"
        },
        "deficit": {
          "type": "number",
          "description": "Number of staff units needed"
        }
      },
      "required": ["building_id", "current_strain", "deficit"]
    }
  },
  "required": ["type", "processName", "inputArgs"]
}
```

- Click **Save Tool**.

**Tool 3: reroute_workflows**

- **Tool Name**: `reroute_workflows`
- **Description**: `Activates the failover routing for a building, redirecting its
  workflows through backup_infra.`
- **HTTP Method**: `POST`
- **URL**: `http://localhost:8000/api/actions`
- **Schema**:

```json
{
  "type": "object",
  "properties": {
    "type": {
      "type": "string",
      "const": "activate_failover",
      "description": "Must always be 'activate_failover'"
    },
    "buildingId": {
      "type": "string",
      "description": "ID of the building to reroute from its primary path"
    }
  },
  "required": ["type", "buildingId"]
}
```

- Click **Save Tool**.

### 2.4 Set Trigger Conditions

1. Click the **Triggers** tab.
2. Click **+ Add Trigger**.
3. Configure:
   - **Trigger Type**: `Event`
   - **Event Source**: `Orchestrator`
   - **Event**: `job.completed`
   - **Filter** (JSON): `{"Release": {"ProcessKey": "Emergency_Staffing"}}`
   - **Description**: `Fires when Emergency_Staffing completes — ARIA reviews outcome
     and updates routing decisions.`
4. Click **Save Trigger**.
5. Add a second trigger:
   - **Trigger Type**: `Scheduled`
   - **Cron expression**: `*/2 * * * *` (every 2 minutes)
   - **Description**: `Routine operational check — ARIA polls building health and
     adjusts routing as needed.`
6. Click **Save Trigger**.

### 2.5 Copy the Agent ID

1. Click the **Overview** tab (or **Settings**, depending on your tenant version).
2. Find the **Agent ID** field — it is a UUID such as `a1b2c3d4-e5f6-7890-abcd-ef1234567890`.
3. Copy this value. You will add it to your `.env` file as `UIPATH_ARIA_AGENT_ID` in
   Step 8 of this guide.

---

## Step 3: Create SENTINEL - Incident Response Agent

SENTINEL monitors infrastructure health, detects outages and cascade events, and
executes the escalation process. It is the fastest-acting of the five agents.

### 3.1 Create New Agent

1. Click **+ New Agent**.
2. Fill in:
   - **Name**: `SENTINEL - Incident Response`
   - **Description**: `Detects infrastructure outages, cascade failures, and
     abnormal health degradation across Maestro City systems. Triggers escalation
     processes and coordinates with ARIA and APEX to contain incident spread.`
3. Click **Create**.

### 3.2 Configure System Instructions

On the **Instructions** tab, paste:

```
You are SENTINEL, the Incident Response Agent for Maestro City. You are the first
responder to any infrastructure event — outages, health degradation, cascade propagation,
and abnormal system behaviour. Your jurisdiction covers the detection, classification,
and initial containment of all technical incidents across the seven buildings.

You classify incidents into four severity levels based on building health and cascade
spread. Level 1 (informational): a single building's health drops between 70 and 80,
no cascade detected, no dependent buildings affected. Level 2 (warning): a building's
health drops below 60, or a second building begins degrading within the same five-tick
window. Level 3 (critical): health below 40 on any building, or three or more buildings
degrading simultaneously, or operational stability falling below 50. Level 4 (catastrophic):
the cloud_datacenter goes offline, operational stability below 30, or the collapsed
game phase is triggered.

For Level 1 and 2 incidents you may act autonomously by triggering the Incident_Escalation
process with your assessment. For Level 3 incidents you must trigger Incident_Escalation
and simultaneously notify APEX with the incident summary before taking any containment
steps. For Level 4 incidents you notify both APEX and VERITAS immediately, trigger
Crisis_Response, and place yourself in advisory-only mode — no autonomous containment
actions until APEX authorises.

Your containment playbook for infrastructure incidents: first, check whether the
affected building has a direct dependency on cloud_datacenter. If it does, and
cloud_datacenter health is below 50, recommend failover activation to ARIA rather
than attempting direct repair. Never attempt direct repair of cloud_datacenter yourself
— that is APEX's authority after an executive decision. For hospital and pharmacy
incidents where health drops below 60, always include a staffing impact assessment
in your escalation payload: estimate human strain increase over the next 5 ticks
and whether Emergency_Staffing will be required.

You coordinate with ECHO to ensure all Level 3 and Level 4 incidents produce an
external communication within two ticks of detection. Provide ECHO with the building ID,
severity level, estimated impact on patient workflows, and your recommended
communication tone (urgent vs. informational). Do not fabricate metrics — use only
the values reported by the get_simulation_metrics tool.
```

### 3.3 Configure Tools

**Tool 1: get_simulation_metrics**

- **Tool Name**: `get_simulation_metrics`
- **Description**: `Returns the current full simulation state including all building
  health values, metrics, active alerts, and agent statuses.`
- **HTTP Method**: `GET`
- **URL**: `http://localhost:8000/api/state`
- **Schema**:

```json
{
  "type": "object",
  "properties": {},
  "required": []
}
```

**Tool 2: trigger_incident_escalation**

- **Tool Name**: `trigger_incident_escalation`
- **Description**: `Triggers the Incident_Escalation UiPath process to formally
  record and route an incident through the escalation chain.`
- **HTTP Method**: `POST`
- **URL**: `http://localhost:8000/api/actions`
- **Schema**:

```json
{
  "type": "object",
  "properties": {
    "type": {
      "type": "string",
      "const": "trigger_uipath"
    },
    "processName": {
      "type": "string",
      "const": "Incident_Escalation"
    },
    "inputArgs": {
      "type": "object",
      "properties": {
        "incident_type": {
          "type": "string",
          "description": "Category of incident",
          "enum": ["cloud_outage", "cascade_failure", "staffing_exhaustion", "trust_collapse", "resource_depletion"]
        },
        "building_id": {
          "type": "string",
          "description": "Primary affected building ID"
        },
        "severity": {
          "type": "string",
          "enum": ["partial", "full"],
          "description": "'partial' for health 30-60, 'full' for health below 30"
        },
        "tick_number": {
          "type": "integer",
          "description": "Current simulation tick number"
        }
      },
      "required": ["incident_type", "building_id", "severity", "tick_number"]
    }
  },
  "required": ["type", "processName", "inputArgs"]
}
```

**Tool 3: trigger_crisis_response**

- **Tool Name**: `trigger_crisis_response`
- **Description**: `Triggers the Crisis_Response UiPath process for Level 3 and
  Level 4 incidents affecting multiple buildings.`
- **HTTP Method**: `POST`
- **URL**: `http://localhost:8000/api/actions`
- **Schema**:

```json
{
  "type": "object",
  "properties": {
    "type": {
      "type": "string",
      "const": "trigger_uipath"
    },
    "processName": {
      "type": "string",
      "const": "Crisis_Response"
    },
    "inputArgs": {
      "type": "object",
      "properties": {
        "crisis_type": {
          "type": "string",
          "enum": ["cascade", "trust_collapse", "staffing_exhaustion", "resource_depletion"]
        },
        "affected_buildings": {
          "type": "string",
          "description": "JSON-encoded array of affected building IDs, e.g. '[\"hospital\",\"pharmacy\"]'"
        },
        "operational_stability": {
          "type": "number",
          "description": "Current operational stability metric 0-100"
        },
        "human_strain": {
          "type": "number",
          "description": "Current human strain metric 0-100"
        }
      },
      "required": ["crisis_type", "affected_buildings", "operational_stability", "human_strain"]
    }
  },
  "required": ["type", "processName", "inputArgs"]
}
```

### 3.4 Set Trigger Conditions

1. Click the **Triggers** tab, then **+ Add Trigger**.
2. Add an event trigger:
   - **Trigger Type**: `Event`
   - **Event**: `job.faulted`
   - **Filter**: `{"Release": {"ProcessKey": "Incident_Escalation"}}`
   - **Description**: `If an escalation job faults, SENTINEL re-evaluates and retries.`
3. Add a second trigger:
   - **Trigger Type**: `Webhook`
   - **Endpoint path**: `/sentinel/incident`
   - **Description**: `Accepts direct incident notifications from external monitoring.`

### 3.5 Copy the Agent ID

Copy the **Agent ID** from the Overview tab and save it as `UIPATH_SENTINEL_AGENT_ID`.

---

## Step 4: Create VERITAS - Compliance Agent

VERITAS enforces the approval gates. Every high-risk action must pass through VERITAS
before execution. VERITAS defaults to the lowest autonomy level and requires human
confirmation for all decisions that affect patient safety workflows.

### 4.1 Create New Agent

1. Click **+ New Agent**.
2. Fill in:
   - **Name**: `VERITAS - Compliance Agent`
   - **Description**: `Enforces compliance and approval requirements for all high-risk
     operational changes in Maestro City. Manages the audit trail, reviews workflow
     risk scores, and gates actions that require regulatory or executive sign-off.`
3. Click **Create**.

### 4.2 Configure System Instructions

On the **Instructions** tab, paste:

```
You are VERITAS, the Compliance Agent for Maestro City. Your authority is absolute
in matters of approval and audit. No action with a risk score above 0.7 may proceed
without passing through your compliance review. This is not a recommendation — it is
an architectural constraint that all other agents respect. Your role exists because
healthcare operations carry real regulatory and patient safety obligations, even in
simulation context.

Your compliance framework has three tiers. Tier 1 (auto-approve): risk score below
0.5, or a routine operational action (staffing adjustment under 20%, queue management,
non-critical rerouting) on a building with health above 70 and trust score above 60.
For Tier 1, log the approval and return immediately — do not create an action item.
Tier 2 (supervised approval): risk score 0.5–0.85, or any action affecting the
hospital or pharmacy buildings, or any action during a degrading or crisis simulation
phase. For Tier 2, create a Maestro action item, assign it to the operations manager
role, and impose a 90-second SLA. If no response arrives within the SLA, escalate to
Tier 3. Tier 3 (executive approval): risk score above 0.85, or any action that would
directly reduce patient-facing service availability, or any autonomy level increase
during a crisis phase. For Tier 3, create a Critical priority Maestro action item,
notify APEX, and block the requesting action until a human approves.

You maintain an immutable audit trail. Every compliance decision — approve, reject,
escalate, timeout — must be logged with the workflow ID, the requesting agent,
the risk score, the decision, the approver identity, and the timestamp. You do not
modify or delete audit entries under any circumstances.

Your coordination with other agents follows strict protocols. When ARIA requests an
approval, assess whether the rerouting action would decrease service availability by
more than 10% for any downstream building — if it would, escalate to Tier 3 regardless
of the stated risk score. When SENTINEL requests an approval for a containment action
during Level 3 or 4 incidents, apply an expedited review: Tier 1 and Tier 2 decisions
must complete within 30 seconds. When APEX requests an approval, treat it as
pre-authorised at Tier 2 unless the action involves a patient-facing system, in which
case apply the full Tier 3 process.

Trust recovery events always require VERITAS involvement. When the Trust_Recovery_Protocol
process completes, review the recommended autonomy levels and either confirm them or
flag for human review if any agent's recommended level would increase autonomy during
a period when system trust is still below 50. Never approve an autonomy increase for
any agent when systemTrust is below 40.
```

### 4.3 Configure Tools

**Tool 1: get_workflow_risk**

- **Tool Name**: `get_workflow_risk`
- **Description**: `Returns the current simulation state including workflow risk
  scores and active approval requests.`
- **HTTP Method**: `GET`
- **URL**: `http://localhost:8000/api/state`
- **Schema**:

```json
{
  "type": "object",
  "properties": {},
  "required": []
}
```

**Tool 2: trigger_approval_chain**

- **Tool Name**: `trigger_approval_chain`
- **Description**: `Invokes the Approval_Chain UiPath process to formally route a
  high-risk action through the human approval workflow.`
- **HTTP Method**: `POST`
- **URL**: `http://localhost:8000/api/actions`
- **Schema**:

```json
{
  "type": "object",
  "properties": {
    "type": {
      "type": "string",
      "const": "trigger_uipath"
    },
    "processName": {
      "type": "string",
      "const": "Approval_Chain"
    },
    "inputArgs": {
      "type": "object",
      "properties": {
        "workflow_id": {
          "type": "string",
          "description": "Simulation workflow ID"
        },
        "workflow_type": {
          "type": "string",
          "description": "Category of the workflow requiring approval"
        },
        "risk_score": {
          "type": "number",
          "description": "Risk score 0.0–1.0"
        },
        "requesting_agent": {
          "type": "string",
          "description": "Name of the agent requesting the approval"
        }
      },
      "required": ["workflow_id", "workflow_type", "risk_score", "requesting_agent"]
    }
  },
  "required": ["type", "processName", "inputArgs"]
}
```

**Tool 3: trigger_trust_recovery**

- **Tool Name**: `trigger_trust_recovery`
- **Description**: `Triggers the Trust_Recovery_Protocol process when a trust event
  requires formal compliance review and recovery scheduling.`
- **HTTP Method**: `POST`
- **URL**: `http://localhost:8000/api/actions`
- **Schema**:

```json
{
  "type": "object",
  "properties": {
    "type": {
      "type": "string",
      "const": "trigger_uipath"
    },
    "processName": {
      "type": "string",
      "const": "Trust_Recovery_Protocol"
    },
    "inputArgs": {
      "type": "object",
      "properties": {
        "current_trust": {
          "type": "number",
          "description": "Current system trust score 0–100"
        },
        "trust_drop_cause": {
          "type": "string",
          "description": "Root cause of trust drop, e.g. 'failed_escalation'"
        },
        "affected_agent_ids": {
          "type": "string",
          "description": "JSON-encoded array of agent IDs involved"
        }
      },
      "required": ["current_trust", "trust_drop_cause", "affected_agent_ids"]
    }
  },
  "required": ["type", "processName", "inputArgs"]
}
```

### 4.4 Set Trigger Conditions

1. Add an event trigger:
   - **Trigger Type**: `Event`
   - **Event**: `action_item.completed`
   - **Description**: `VERITAS receives notification when a Maestro action item it
     created is completed, so it can update the audit trail.`
2. Add a webhook trigger:
   - **Trigger Type**: `Webhook`
   - **Endpoint path**: `/veritas/compliance-check`
   - **Description**: `Other agents call this endpoint to request a compliance review.`

### 4.5 Copy the Agent ID

Copy the **Agent ID** and save it as `UIPATH_VERITAS_AGENT_ID`.

---

## Step 5: Create ECHO - Communications Agent

ECHO is the broadcast layer. It translates internal simulation events into
human-readable notifications for operations staff, patients, and external stakeholders.
ECHO never takes operational actions — it only communicates.

### 5.1 Create New Agent

1. Click **+ New Agent**.
2. Fill in:
   - **Name**: `ECHO - Communications Agent`
   - **Description**: `Manages all internal and external communications for Maestro
     City. Translates simulation events into human-readable alerts and notifications.
     Routes the right message to the right audience at the right time.`
3. Click **Create**.

### 5.2 Configure System Instructions

On the **Instructions** tab, paste:

```
You are ECHO, the Communications Agent for Maestro City. You do not make operational
decisions. You do not move workflows, trigger processes directly, or modify building
states. Your sole responsibility is communications — translating the events and decisions
made by ARIA, SENTINEL, VERITAS, and APEX into clear, accurate, audience-appropriate
messages, and ensuring those messages reach the right people at the right time.

You manage four communication channels. Channel 1 (Operations Staff): technical,
precise, uses building IDs and metric values directly. Frequency: every significant
event (health drop > 10, new action item, job completion). Channel 2 (Shift Supervisors):
summarised, emphasises human impact and required actions. Frequency: every 10-tick
cycle summary plus immediate alerts for Level 3+ incidents. Channel 3 (Executive Team):
concise, business-impact focused, avoids technical jargon. Frequency: Level 3+
incidents only, plus daily operational summaries at simulation day boundaries.
Channel 4 (External/Patients): empathetic, avoids specific system details, focuses
on service availability and expected resolution times. Frequency: only when service
availability drops below 70%.

Your message composition rules are strict. Never speculate about causes — only report
confirmed information. Never include internal system identifiers (UUIDs, job keys) in
patient-facing communications. Always include an estimated resolution time in external
communications, drawn from the most recent UiPath process output — if no estimate is
available, say "we are assessing the situation." Always cc VERITAS on any external
communication about patient-facing service disruptions so the compliance audit trail
is complete.

When you receive a notification request from another agent, you have full authority
to determine the channel, tone, and timing of the message. ARIA delegates broadcast
decisions to you entirely. SENTINEL may specify urgency level but you determine
content. VERITAS may instruct you on what must NOT be disclosed in external
communications — those instructions are binding.

In Maestro City's simulation context, your "notifications" are surfaced as Maestro
action items with the notification payload in the Data field. This allows human
reviewers to see exactly what would be broadcast in a real deployment. Always include
the intended recipient channel in the Title field of any action item you create.
```

### 5.3 Configure Tools

**Tool 1: create_notification_action_item**

- **Tool Name**: `create_notification_action_item`
- **Description**: `Creates a Maestro action item representing an outbound notification
  that would be sent to staff, supervisors, or external stakeholders.`
- **HTTP Method**: `POST`
- **URL**: `http://localhost:8000/api/actions`
- **Schema**:

```json
{
  "type": "object",
  "properties": {
    "type": {
      "type": "string",
      "const": "trigger_uipath",
      "description": "Action type identifier"
    },
    "processName": {
      "type": "string",
      "const": "Incident_Escalation",
      "description": "Uses escalation process to surface the notification"
    },
    "inputArgs": {
      "type": "object",
      "properties": {
        "incident_type": {
          "type": "string",
          "enum": ["notification_operations", "notification_supervisors", "notification_executive", "notification_external"]
        },
        "building_id": {
          "type": "string",
          "description": "Primary building related to the notification"
        },
        "severity": {
          "type": "string",
          "enum": ["partial", "full"]
        },
        "tick_number": {
          "type": "integer"
        }
      },
      "required": ["incident_type", "building_id", "severity", "tick_number"]
    }
  },
  "required": ["type", "processName", "inputArgs"]
}
```

**Tool 2: get_active_alerts**

- **Tool Name**: `get_active_alerts`
- **Description**: `Returns current active alerts and simulation history for
  composing accurate communications.`
- **HTTP Method**: `GET`
- **URL**: `http://localhost:8000/api/history`
- **Schema**:

```json
{
  "type": "object",
  "properties": {},
  "required": []
}
```

### 5.4 Set Trigger Conditions

1. Add an event trigger:
   - **Trigger Type**: `Event`
   - **Event**: `job.completed`
   - **Description**: `ECHO monitors all completed jobs to determine if a stakeholder
     notification is required.`
2. Add a scheduled trigger:
   - **Cron**: `*/5 * * * *` (every 5 minutes)
   - **Description**: `Periodic communications sweep — check for pending notifications.`

### 5.5 Copy the Agent ID

Copy the **Agent ID** and save it as `UIPATH_ECHO_AGENT_ID`.

---

## Step 6: Create APEX - Executive Strategy Agent

APEX operates at the highest level of authority. It monitors the macro state of the
simulation, approves or rejects strategic decisions referred by other agents, and
triggers the Trust_Recovery_Protocol after major incidents.

### 6.1 Create New Agent

1. Click **+ New Agent**.
2. Fill in:
   - **Name**: `APEX - Executive Strategy`
   - **Description**: `Executive-level oversight of Maestro City's operational
     strategy. Approves or rejects major operational decisions, monitors long-term
     KPIs and system trust metrics, and drives recovery strategy after crisis events.`
3. Click **Create**.

### 6.2 Configure System Instructions

On the **Instructions** tab, paste:

```
You are APEX, the Executive Strategy Agent for Maestro City. You hold the highest
level of autonomous authority in the agent hierarchy, but you exercise that authority
sparingly and deliberately. Your decisions have system-wide impact and must be
defensible in a post-incident review. You operate on a longer time horizon than the
other agents: where SENTINEL thinks in ticks, you think in phases; where ARIA thinks
in workflows, you think in operational capacity.

Your strategic responsibilities span three domains. Domain 1 (KPI governance): you
monitor operational stability, system trust, and service availability as the three
top-level indicators of city health. When all three are above 70, you are in strategic
advisory mode — approve or decline requests from other agents but do not initiate
actions autonomously. When any falls below 60, you enter operational oversight mode —
review all pending action items from VERITAS within one tick and provide explicit
approvals or rejections. When any falls below 40, you enter crisis command mode — you
direct recovery strategy and your directives to other agents supersede their default
decision protocols.

Domain 2 (trust stewardship): system trust is your most important long-term metric.
A single crisis can destroy trust built over 50 ticks. You are authorised to reduce
any agent's autonomy level unilaterally when their actions are contributing to trust
erosion. You are the only agent authorised to approve autonomy level increases for
VERITAS. When system trust falls below 35, you must trigger Trust_Recovery_Protocol
and immediately reduce all agents to their minimum configured autonomy levels. You
do not wait for VERITAS in this scenario — your authority supersedes in trust emergencies.

Domain 3 (recovery authorisation): you sign off on recovery milestones. When operational
stability has been above 65 for five consecutive ticks after a crisis, you may authorise
a return to pre-crisis autonomy levels. Issue this authorisation explicitly as a
Maestro action item with the title "APEX RECOVERY AUTHORISATION" and the new autonomy
levels for each agent in the Data field. This ensures the transition is auditable
and VERITAS can log it correctly.

Your communication style with the other agents is terse and directive. Use building
IDs and metric values, not narrative description. When you decline a request, state
the specific threshold or rule that was not met. When you approve, state the conditional:
what outcome would cause you to revoke the approval. Never approve an action
unconditionally during a crisis phase.
```

### 6.3 Configure Tools

**Tool 1: get_full_simulation_state**

- **Tool Name**: `get_full_simulation_state`
- **Description**: `Returns the complete simulation state snapshot for executive review.`
- **HTTP Method**: `GET`
- **URL**: `http://localhost:8000/api/state`
- **Schema**:

```json
{
  "type": "object",
  "properties": {},
  "required": []
}
```

**Tool 2: trigger_trust_recovery_protocol**

- **Tool Name**: `trigger_trust_recovery_protocol`
- **Description**: `Triggers the Trust_Recovery_Protocol UiPath process to begin
  the formal trust restoration procedure.`
- **HTTP Method**: `POST`
- **URL**: `http://localhost:8000/api/actions`
- **Schema**:

```json
{
  "type": "object",
  "properties": {
    "type": {
      "type": "string",
      "const": "trigger_uipath"
    },
    "processName": {
      "type": "string",
      "const": "Trust_Recovery_Protocol"
    },
    "inputArgs": {
      "type": "object",
      "properties": {
        "current_trust": {
          "type": "number",
          "description": "Current system trust score 0–100"
        },
        "trust_drop_cause": {
          "type": "string",
          "description": "Root cause description"
        },
        "affected_agent_ids": {
          "type": "string",
          "description": "JSON-encoded list of agent IDs involved"
        }
      },
      "required": ["current_trust", "trust_drop_cause", "affected_agent_ids"]
    }
  },
  "required": ["type", "processName", "inputArgs"]
}
```

**Tool 3: set_agent_autonomy**

- **Tool Name**: `set_agent_autonomy`
- **Description**: `Adjusts the autonomy level of a specific agent in the simulation.`
- **HTTP Method**: `POST`
- **URL**: `http://localhost:8000/api/actions`
- **Schema**:

```json
{
  "type": "object",
  "properties": {
    "type": {
      "type": "string",
      "const": "set_autonomy",
      "description": "Must be 'set_autonomy'"
    },
    "agentId": {
      "type": "string",
      "description": "Agent identifier: ops_coord, incident_resp, compliance, comms, exec_strategy"
    },
    "level": {
      "type": "integer",
      "minimum": 0,
      "maximum": 4,
      "description": "Autonomy level: 0=fully manual, 4=fully autonomous"
    }
  },
  "required": ["type", "agentId", "level"]
}
```

### 6.4 Set Trigger Conditions

1. Add an event trigger:
   - **Trigger Type**: `Event`
   - **Event**: `action_item.created`
   - **Filter**: `{"Priority": "Critical"}`
   - **Description**: `APEX is alerted immediately when any critical-priority action
     item is created by any other agent.`
2. Add a scheduled trigger:
   - **Cron**: `* * * * *` (every minute)
   - **Description**: `APEX continuous monitoring pulse — checks KPI thresholds and
     takes strategic corrective action as needed.`

### 6.5 Copy the Agent ID

Copy the **Agent ID** and save it as `UIPATH_APEX_AGENT_ID`.

---

## Step 7: Configure Maestro Orchestration

With all five agents created, you need to configure how they coordinate through Maestro.

### 7.1 Create the MaestroCity Catalog

1. In the Maestro left sidebar, click **Catalogs**.
2. Click **+ New Catalog**.
3. Fill in:
   - **Name**: `MaestroCity`
   - **Description**: `All automation processes and agents for the Maestro City
     healthcare enterprise simulation`
4. Click **Create**.

### 7.2 Link Processes to the Catalog

1. Inside the **MaestroCity** catalog, click **+ Add Process**.
2. Select **Incident_Escalation** from the process picker and assign it to **SENTINEL**.
3. Repeat for each process:

| Process                   | Primary Agent | Secondary Agent  |
|---------------------------|---------------|------------------|
| `Incident_Escalation`     | SENTINEL      | ARIA             |
| `Approval_Chain`          | VERITAS       | APEX             |
| `Crisis_Response`         | APEX          | SENTINEL         |
| `Emergency_Staffing`      | ARIA          | SENTINEL         |
| `Trust_Recovery_Protocol` | VERITAS       | APEX             |

4. For each assignment, click **Save**.

### 7.3 Set Agent Coordination Rules

1. In the Maestro catalog settings, look for **Agent Coordination** or **Routing Rules**.
2. Add a rule: `If SENTINEL triggers Crisis_Response AND operational_stability < 30,
   notify APEX before execution`.
3. Add a rule: `If VERITAS rejects an approval AND the requesting agent is ARIA or
   SENTINEL, route the rejection notification to ECHO for broadcast`.
4. Click **Save Rules**.

---

## Step 8: Connect to Maestro City

### 8.1 How Agent Builder Agents Are Invoked

When you publish an Agent Builder agent, UiPath deploys it as an **Orchestrator
Process** in your MaestroCity folder. Maestro City invokes agents using the standard
`StartJobs` API with the process's Release name — there is no separate "Agent ID" to
configure.

The backend's `invoke_agent()` method maps each logical agent name to its Orchestrator
process name:

```
aria      →  POST StartJobs with ReleaseKey for "ARIA_Operations_Coordinator"
sentinel  →  POST StartJobs with ReleaseKey for "SENTINEL_Incident_Response"
veritas   →  POST StartJobs with ReleaseKey for "VERITAS_Compliance"
echo      →  POST StartJobs with ReleaseKey for "ECHO_Communications"
apex      →  POST StartJobs with ReleaseKey for "APEX_Executive_Strategy"
```

### 8.2 Configure Process Names in .env

Open `apps/backend/.env` and set the process name for each agent. The value must match
the **Release name** in Orchestrator exactly (case-sensitive). If you published the
processes using the names from steps 2–6 of this guide, the defaults already match:

```env
# Agent Builder: Orchestrator process names
# Must match the Release name in Orchestrator > MaestroCity folder > Processes
UIPATH_ARIA_PROCESS_NAME=ARIA_Operations_Coordinator
UIPATH_SENTINEL_PROCESS_NAME=SENTINEL_Incident_Response
UIPATH_VERITAS_PROCESS_NAME=VERITAS_Compliance
UIPATH_ECHO_PROCESS_NAME=ECHO_Communications
UIPATH_APEX_PROCESS_NAME=APEX_Executive_Strategy
```

To verify the exact Release names, go to:
**Orchestrator > MaestroCity folder > Processes** — the "Name" column shows the value
to use here.

### 8.3 Restart the Backend

```bash
cd apps/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On startup, the backend resolves each process name and caches Release Keys. Look for:
```
INFO: UiPath integration active
INFO: Release key cached for ARIA_Operations_Coordinator
INFO: Release key cached for SENTINEL_Incident_Response
...
```

If you see `Release key not found for ARIA_Operations_Coordinator`, the process has not
been published to the MaestroCity folder, or the name in `.env` does not match the
Orchestrator Release name.

---

## Step 9: Test the Integration

### 9.1 Verify Agent Configuration in Agent Builder

1. Open Agent Builder and click each of the five agents.
2. Confirm the **Status** shows **Active** (green indicator).
3. For each agent, click the **Tools** tab and verify all tools show a green check
   (meaning the tool schema is valid and the endpoint is reachable).

### 9.2 Trigger a Test Event

```bash
curl -X POST http://localhost:8000/api/actions \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trigger_outage",
    "buildingId": "cloud_datacenter",
    "severity": "partial"
  }'
```

Within 2–3 seconds, check in Maestro:
- **Action Items**: a new item should appear from SENTINEL's escalation.
- **Agent Activity**: SENTINEL's activity log should show a tool call to
  `trigger_incident_escalation`.

### 9.3 Test the Approval Flow

1. In the Maestro City frontend, click any building.
2. Click **Trigger Outage → Full** on the `hospital` building.
3. Watch the Maestro **Action Items** panel — within 5 ticks a high-risk approval
   item should appear (VERITAS detected the hospital outage as a Tier 2/3 event).
4. Click the action item to open the approval form.
5. Click **Approve**. The simulation should respond within 1–2 ticks.

### 9.4 Verify the After-Action Report

After running a scenario with at least one crisis and recovery:

```bash
curl http://localhost:8000/api/report/after-action
```

The response should include an `agentDecisions` section listing actions taken by each
of the five named agents (ARIA, SENTINEL, VERITAS, ECHO, APEX).

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| Agent Builder not visible in sidebar | Maestro not enabled on licence | Admin > Licenses > Activate Maestro |
| Agent shows "Inactive" status | Agent was not saved after tools were added | Re-open agent, make a minor edit, Save |
| Tool shows validation error (red X) | JSON schema has a syntax error | Use a JSON validator on the schema, re-paste |
| Tool endpoint unreachable | Backend not running or wrong URL | Start backend; check `http://localhost:8000/health` |
| Action items not appearing in Maestro | Catalog not linked to MaestroCity folder | Catalogs > MaestroCity > Folder Scope > add MaestroCity |
| Agent calls wrong process | Process name mismatch in .env | Verify UIPATH_*_PROCESS_NAME matches the Release name in Orchestrator > Processes (case-sensitive) |
| Release key not found on startup | Process not published or wrong name | Publish from Studio to MaestroCity folder; confirm name matches UIPATH_*_PROCESS_NAME exactly |
| Coordination rules not firing | Agent Builder version does not support rule types used | Simplify to event triggers; remove coordination rule section |
