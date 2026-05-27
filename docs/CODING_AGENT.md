# Coding Agent: AI-Generated UiPath Workflows

## What is the Coding Agent?

The Coding Agent is a feature in Maestro City that uses Claude AI
(`claude-sonnet-4-6`) to dynamically generate complete, valid UiPath XAML workflow
files based on the real-time state of your simulation. Instead of starting from a
blank Studio canvas, the Coding Agent inspects what is happening in your city — which
buildings are degraded, which agents are active, what the current crisis type is —
and produces a tailored automation workflow that directly addresses the situation.

This demonstrates one of the most practical applications of coding agents in enterprise
settings: accelerating the creation of automation artifacts from scratch by having an
AI that understands both the domain (healthcare operations, UiPath workflow structure)
and the specific context (your exact incident state) generate an appropriate starting
point.

---

## How It Works

### End-to-End Flow

```
1. User clicks "Coding Agent" button in the Maestro City toolbar
        │
        ▼
2. Selects a process type from the dropdown
   (Incident Escalation / Approval Chain / Crisis Response /
    Emergency Staffing / Trust Recovery Protocol)
        │
        ▼
3. Backend builds a rich context object from the current simulation state:
   • Current building health values for all 7 buildings
   • Active alerts and their severity
   • Current game phase (stable / degrading / crisis / collapsed)
   • Agent autonomy levels
   • Operational stability, human strain, system trust metrics
   • Recent simulation events (last 20 ticks)
        │
        ▼
4. Backend constructs a specialised XAML-generation prompt combining:
   • The context object above
   • UiPath XAML schema constraints and valid activity types
   • Process-specific argument definitions
   • A requirement to include UiPath Action Center integration points
        │
        ▼
5. Backend sends the prompt to the Claude API (claude-sonnet-4-6)
   via the Anthropic SDK
        │
        ▼
6. Claude returns a complete, valid XAML workflow tailored to the
   current simulation context
        │
        ▼
7. Frontend displays the XAML in a syntax-highlighted viewer
        │
        ▼
8. User clicks "Download" to save the .xaml file, then imports it
   directly into UiPath Studio
```

### What Makes the Generated XAML Context-Aware

A static template always produces the same output. The Coding Agent produces different
output each time based on your simulation state. Examples:

- If `cloud_datacenter.health < 30` when you generate an Incident Escalation workflow,
  the XAML includes a failover activation branch that would not appear in a healthy-state
  generation.
- If `humanStrain > 80` when you generate an Emergency Staffing workflow, the XAML
  includes the critical-urgency paging sequence with a 5-minute arrival target instead
  of the standard 15-minute sequence.
- If the game phase is `crisis` when you generate a Crisis Response workflow, the XAML
  includes parallel execution branches for failover, staffing, and external notification —
  because all three are needed simultaneously. In a `degrading` phase it generates
  sequential branches with guard conditions.
- If VERITAS is at autonomy level 0 when you generate an Approval Chain workflow, the
  generated XAML includes a mandatory human-in-the-loop wait activity at every decision
  point, matching VERITAS's configured posture.

---

## Setup

### Required Environment Variable

```env
ANTHROPIC_API_KEY=sk-ant-...
```

Add this to `apps/backend/.env`. The Coding Agent feature is disabled if this variable
is not set — the "Coding Agent" button in the UI will show "AI generation unavailable"
and fall back to the static process templates (still downloadable, just not context-aware).

Get your API key at [console.anthropic.com](https://console.anthropic.com).

### Verify the Setup

Start the backend and check:

```bash
curl http://localhost:8000/health
```

If `ANTHROPIC_API_KEY` is set, the response includes:

```json
{
  "coding_agent": {
    "enabled": true,
    "model": "claude-sonnet-4-6"
  }
}
```

---

## API Reference

### POST /api/coding-agent/generate-workflow

Generates a complete XAML workflow file for a specified process type, informed by
the current simulation state.

**Request:**

```http
POST http://localhost:8000/api/coding-agent/generate-workflow
Content-Type: application/json

{
  "process_type": "Incident_Escalation",
  "context_override": {}
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `process_type` | string | Yes | One of: `Incident_Escalation`, `Approval_Chain`, `Crisis_Response`, `Emergency_Staffing`, `Trust_Recovery_Protocol` |
| `context_override` | object | No | Override specific context values. Useful for generating workflows for hypothetical scenarios. |

**Response:**

```json
{
  "process_type": "Incident_Escalation",
  "xaml": "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<Activity ...",
  "context_used": {
    "phase": "crisis",
    "operational_stability": 28.4,
    "human_strain": 76.1,
    "affected_buildings": ["cloud_datacenter", "hospital", "pharmacy"],
    "crisis_type": "cascade"
  },
  "model": "claude-sonnet-4-6",
  "generation_time_ms": 2840,
  "download_filename": "Incident_Escalation_crisis_tick042.xaml"
}
```

**curl example:**

```bash
curl -X POST http://localhost:8000/api/coding-agent/generate-workflow \
  -H "Content-Type: application/json" \
  -d '{"process_type": "Crisis_Response"}'
```

---

### POST /api/coding-agent/generate-entities

Generates the data entity definitions (argument schemas, DataTable structures, enum
constants) for a process, formatted as UiPath-compatible type definitions. Useful when
you want to build a workflow from scratch but need the correct argument names and types.

**Request:**

```http
POST http://localhost:8000/api/coding-agent/generate-entities
Content-Type: application/json

{
  "process_type": "Approval_Chain",
  "include_examples": true
}
```

**Response:**

```json
{
  "process_type": "Approval_Chain",
  "input_arguments": [
    {"name": "in_RequestType", "type": "String", "direction": "In", "description": "..."},
    {"name": "in_RiskLevel", "type": "String", "direction": "In", "description": "..."}
  ],
  "output_arguments": [
    {"name": "out_ApprovalId", "type": "String", "direction": "Out", "description": "..."}
  ],
  "enums": {
    "RiskLevel": ["low", "medium", "high"],
    "ApprovalStatus": ["Approved", "Rejected", "Timeout", "Escalated"]
  },
  "example_input": {
    "in_RequestType": "failover_activation",
    "in_RequestedBy": "ARIA",
    "in_TargetBuildingId": "cloud_datacenter",
    "in_RiskLevel": "high",
    "in_AutoApproveThreshold": 0.0
  }
}
```

---

### POST /api/coding-agent/debug-workflow

Takes an existing XAML string as input and asks Claude to identify issues, suggest
improvements, and optionally return a corrected version. Useful after importing a
generated workflow into Studio and encountering validation errors.

**Request:**

```http
POST http://localhost:8000/api/coding-agent/debug-workflow
Content-Type: application/json

{
  "xaml": "<?xml version=\"1.0\" ...>",
  "error_description": "Activity 'InvokeMethod' does not have a TargetObject",
  "fix": true
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `xaml` | string | Yes | The XAML content to debug |
| `error_description` | string | No | The Studio validation error or runtime error message |
| `fix` | boolean | No | If `true`, returns a corrected XAML; if `false`, returns analysis only |

**Response:**

```json
{
  "issues_found": [
    "InvokeMethod at line 94 is missing TargetObject — the List variable v_ActionList must be referenced explicitly",
    "Assign at line 112 uses OutArgument without type argument — should be OutArgument(x:String)"
  ],
  "fixes_applied": 2,
  "corrected_xaml": "<?xml version=\"1.0\" ...",
  "model": "claude-sonnet-4-6"
}
```

---

## Example: Generated Incident Response Workflow

Below is a representative excerpt of XAML generated by the Coding Agent during a
`crisis` phase where `cloud_datacenter.health = 12` and `hospital.health = 44`. Note
the context-specific elements: the datacenter failover check, the patient-workflow
protection block, and the Level 3 escalation path.

```xml
<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap sap2010 sap2020"
    x:Class="MaestroCity.Incident_Escalation_Generated"
    xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members>
    <x:Property Name="in_BuildingId" Type="InArgument(x:String)" />
    <x:Property Name="in_Severity" Type="InArgument(x:String)" />
    <x:Property Name="in_OperationalStability" Type="InArgument(x:Double)" />
    <x:Property Name="in_AffectedWorkflows" Type="InArgument(x:Int32)" />
    <x:Property Name="out_EscalationId" Type="OutArgument(x:String)" />
    <x:Property Name="out_EscalationLevel" Type="OutArgument(x:Int32)" />
    <x:Property Name="out_ActionsTaken" Type="OutArgument(x:String)" />
  </x:Members>
  <Sequence DisplayName="Incident Escalation — Crisis Context (Generated)">
    <Sequence.Variables>
      <Variable Name="v_EscalationId" Type="x:String" />
      <Variable Name="v_Level" Type="x:Int32" Default="[3]" />
      <Variable Name="v_Actions" Type="x:String" Default="[&quot;&quot;]" />
    </Sequence.Variables>

    <!-- CONTEXT: cloud_datacenter health=12, hospital health=44, phase=crisis -->
    <!-- Generator: claude-sonnet-4-6, tick=42, stability=28.4 -->

    <WriteLine Text="[Incident_Escalation] CRISIS CONTEXT — cloud_datacenter=12%, hospital=44%" />

    <!-- Level 3 escalation forced: stability=28.4 < 30 threshold -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_Level]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[3]</InArgument></Assign.Value>
    </Assign>

    <!-- CRISIS BRANCH: datacenter is primary cascade origin — activate failover first -->
    <If Condition="[in_BuildingId.Get(context) = &quot;cloud_datacenter&quot; OrElse
                    in_BuildingId.Get(context) = &quot;hospital&quot;]">
      <If.Then>
        <Sequence DisplayName="Datacenter-Hospital Crisis Protocol">
          <WriteLine Text="[Incident_Escalation] Datacenter-hospital cascade detected — initiating failover check" />
          <!-- TODO: Call GET /api/enterprise/infrastructure/status to verify backup_infra health -->
          <!-- TODO: If backup_infra.health > 60, invoke Emergency_Staffing for hospital -->
          <!-- TODO: Create UiPath Action Center task: Priority=Critical, Title=CRISIS EXECUTIVE APPROVAL -->
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:String">[v_Actions]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:String">
              ["failover_check,hospital_staffing_request,executive_notification,level3_escalation"]
            </InArgument></Assign.Value>
          </Assign>
        </Sequence>
      </If.Then>
    </If>

    <!-- Generate escalation ID with crisis marker -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[v_EscalationId]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">
        ["ESC-CRISIS-" + DateTime.Now.ToString("yyyyMMddHHmmss")]
      </InArgument></Assign.Value>
    </Assign>

    <!-- Set outputs -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_EscalationId]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">[v_EscalationId]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[out_EscalationLevel]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_Level]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_ActionsTaken]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">[v_Actions]</InArgument></Assign.Value>
    </Assign>

    <WriteLine Text="[Incident_Escalation] Generated workflow complete — {v_EscalationId} Level={v_Level}" />
  </Sequence>
</Activity>
```

Compare this to the static template in `UIPATH_PLATFORM_SETUP.md` section 5.1: the
generated version has a hardcoded `v_Level = 3` default (because the simulation was in
crisis when it was generated), a datacenter-hospital specific branch based on the
observed cascade, and `<!-- TODO: -->` comments that reference the actual backend API
endpoints (`/api/enterprise/infrastructure/status`) instead of generic placeholders.

---

## Why This Matters for Enterprises

### The Gap Between Automation Intent and Implementation

The hardest part of enterprise UiPath adoption is not deciding to automate — it is
translating that decision into a working Studio project with the right argument names,
the right activity structure, and the right integration hooks for your specific
environment. Teams often spend days on scaffolding that a coding agent can produce in
seconds.

### Context Is the Differentiator

Generic XAML templates (including the static ones Maestro City also provides) give you
a valid starting point. The Coding Agent gives you a starting point that already knows:

- Which buildings are the current cascade origin
- What phase the system is in and therefore which branches are most likely to be needed
- What the human strain level is and therefore which urgency tier to default to
- Which agents are at low autonomy and therefore need more human-in-the-loop checkpoints

This is the difference between a template and an artifact. The coding agent produces
an artifact.

### Accelerating the Automation Development Lifecycle

In a production deployment of UiPath, a team receiving the output of the Coding Agent
would spend their time on two activities instead of four:

- **Removed**: Writing argument definitions from scratch
- **Removed**: Structuring the decision logic skeleton
- **Remains**: Replacing `<!-- TODO: -->` comments with real API calls, database
  queries, and service integrations
- **Remains**: Testing in Studio Test Manager before publishing to Orchestrator

For large-scale automation programs, this acceleration compounds: if a team is creating
or updating 20 processes per quarter, and each process takes 4 hours to scaffold from
scratch but 45 minutes to complete from a Coding Agent output, the time savings over
a year is substantial — and the quality floor is higher because the generated scaffold
already encodes the structural patterns that passed simulation validation.

### The Validation Loop

Maestro City is unique in combining live simulation with coding agent output: you can
generate a workflow for the current crisis scenario, download it, import it into Studio,
publish it to Orchestrator, and then watch the simulation respond to jobs run by that
actual workflow — all within a single demo session. This closes the loop between
simulation insight and automation artifact in a way that static templates cannot.
