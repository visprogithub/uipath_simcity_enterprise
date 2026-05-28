# Maestro City — UiPath AgentHack Submission

Maestro City is a real-time enterprise operations simulation that demonstrates **human-in-the-loop
AI orchestration** using the UiPath platform. You select an industry scenario, manage a living
city of interconnected systems, and watch five autonomous AI agents respond to cascading failures
— escalating incidents, routing approvals, coordinating crisis response, and rebuilding trust.

The simulation is backed by real UiPath integrations: Agent Builder for agent definitions,
Orchestrator for job execution, Maestro for human approval gates, and the Coding Agent for
AI-generated XAML workflows. It runs fully without UiPath credentials for reliable demos.

Built for the **UiPath AgentHack** hackathon.

---

## Judging Criteria Alignment

| Criterion | Maestro City Feature | Where to See It |
|-----------|---------------------|-----------------|
| UiPath Agent Builder | 5 agents defined with full system prompts, tool schemas, and trigger conditions | Agent Builder panel in Maestro UI; [docs/AGENT_BUILDER_SETUP.md](./AGENT_BUILDER_SETUP.md) |
| API Workflows | 6 enterprise system endpoints (EHR, pharmacy, staffing, infrastructure, outage notify, escalation notify) wired to Integration Service triggers | `/api/enterprise/*` |
| Maestro Orchestration | Phase-aware agent coordination routed through UiPath Maestro, scenario-specific process names | Main city view + Agent Builder panel |
| Human Approval Step | VERITAS compliance agent gates high-risk actions and triggers approval modal | Click any building in crisis phase; check Maestro action items |
| Dynamic Rerouting | ARIA reroutes workflows to backup infrastructure with visual flash on city grid | City view during degrading phase |
| Long-running Workflows | Stuck workflow badge + stuck counter visible on city HUD | Top-left badge during queued phase |
| Coding Agents Bonus | GPT-4o generates context-aware UiPath XAML dynamically from live simulation state | "Coding Agent" button in toolbar; [docs/CODING_AGENT.md](./CODING_AGENT.md) |
| After-Action Report | Scenario-specific enterprise PDF/JSON report with numbered recommendations | Reports → After-Action tab; `GET /api/report/after-action` |

---

## Four Enterprise Scenarios

Select your scenario at the landing screen. Each scenario is a complete independent
simulation with industry-appropriate buildings, agents, compliance frameworks, UiPath
process names, and outage presets.

| Scenario | Industry | Primary Crisis | Compliance |
|----------|----------|----------------|------------|
| 🏥 Healthcare Enterprise | Healthcare | EHR/pharmacy cascade, patient safety | HIPAA, HL7 FHIR, SOC 2 |
| 📈 Financial Services | Finance | Trading halt, risk system failure | SOX, MiFID II, Basel III |
| 🛒 Retail & E-commerce | Retail | Order management, payment gateway outage | PCI-DSS, GDPR, SOC 2 |
| 🏭 Manufacturing & Industry 4.0 | Manufacturing | SCADA failure, supply chain disruption | ISO 9001, IEC 62443, OSHA |

Switching scenarios resets the simulation and reconfigures all buildings, agents, workflows,
and generated report vocabulary for the selected industry.

---

## Enterprise Deliverables

After every scenario run, Maestro City generates four **concrete, actionable artifacts**:

### 1. After-Action Report (`GET /api/report/after-action`)
Structured incident review document with scenario-specific terminology:
- Which systems failed first and cascade sequence
- Per-intervention stability delta (what worked vs. backfired)
- Automation-vs-human recovery breakdown with counterfactual
- Numbered recommendations for process improvement

### 2. Operational Runbook (`GET /api/report/runbook`)
Validated step-by-step incident response procedure importable into PagerDuty, ServiceNow,
or Confluence. Includes scenario-specific escalation chain with UiPath process names,
trigger conditions drawn from observed metric thresholds, and `SIMULATION VALIDATED` badge.

### 3. Autonomy Calibration Certificate (`GET /api/report/autonomy-calibration`)
Per-agent readiness assessment with evidence trail: current level, recommended level,
accuracy %, trust score, and specific rationale for each upgrade/downgrade recommendation.

### 4. UiPath Process Templates (`GET /api/report/process-templates`)
Importable UiPath Studio project files (XAML + project.json) for all 5 automation processes,
named to match the active scenario's Orchestrator process names.

---

## What It Demonstrates

- **Agentic Orchestration**: Five specialised agents operate autonomously at configurable
  autonomy levels (0 = fully manual, 4 = fully autonomous). Each agent is configured in
  UiPath Agent Builder with detailed system prompts, tool schemas, and trigger conditions.
  See [docs/AGENT_BUILDER_SETUP.md](./AGENT_BUILDER_SETUP.md).

- **Human-in-the-Loop**: High-risk decisions surface as UiPath Maestro action items.
  A human approver can approve or reject them; the simulation responds immediately.

- **Real-Time Feedback**: Every UiPath job start and completion is reflected live in the
  city grid via WebSocket — watch automation jobs deploy, see escalations resolve cascades,
  observe trust scores recover after compliance audits.

- **Coding Agent**: The "Coding Agent" button uses OpenAI GPT-4o to generate context-aware
  UiPath XAML workflows based on the live simulation state. A workflow generated during a
  crisis phase differs structurally from one generated during stable operations.
  See [docs/CODING_AGENT.md](./CODING_AGENT.md).

- **Graceful Degradation**: Runs fully without UiPath credentials. All features work in
  simulation mode; plug in credentials to switch to live automation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Maestro City                                       │
│                                                                             │
│   Browser (Next.js + PixiJS)                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  Scenario Selector (landing)                                        │  │
│   │  City Grid (7 buildings, workflows, 5 agent drones)                │  │
│   │  Live metrics panel  │  Agent HUD  │  UiPath status panel          │  │
│   └──────────────────────────┬──────────────────────────────────────────┘  │
│                              │ WebSocket (ws://localhost:8000/ws)           │
│   ┌──────────────────────────▼──────────────────────────────────────────┐  │
│   │  FastAPI Backend (Python)                                           │  │
│   │  • Scenario registry (4 enterprise scenarios, plug-in architecture)│  │
│   │  • Simulation engine (tick loop, building health, cascade logic)   │  │
│   │  • Agent decision engine (5 agent types × 5 autonomy levels)       │  │
│   │  • UiPath client (OAuth 2.0, StartJobs, Integration Service)       │  │
│   │  • State broadcaster (JSON over WebSocket every tick)              │  │
│   └──────────────────────────┬──────────────────────────────────────────┘  │
└─────────────────────────────│────────────────────────────────────────────┘
                               │ HTTPS REST (OAuth 2.0 Bearer token)
                               │ Webhooks (POST /api/uipath/webhook)
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  UiPath Cloud                                                               │
│  • Agent Builder: 5 agent definitions with system prompts and tools        │
│  • Orchestrator: scenario-specific automation processes in MaestroCity folder│
│  • Maestro: action items, approvals, agent catalog                         │
│  • Integration Service: API triggers for enterprise system connections      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### City Layout

Each scenario maps its industry concepts to 7 buildings using a shared `BuildingType` enum
so the PixiJS renderer works across all scenarios unchanged.

| Slot | Healthcare | Financial Services | Retail & E-commerce | Manufacturing |
|------|-----------|-------------------|---------------------|---------------|
| Primary hub | City General Hospital | Trading Floor | Order Management Hub | Factory Floor Control |
| Secondary system | Central Pharmacy | Risk Management | Payment Gateway | Quality Control System |
| Core infrastructure | CloudCore Data Center | Cloud Infrastructure | Cloud Platform | Cloud SCADA Platform |
| Comms | Communications Hub | Communications Hub | Communications Hub | Plant Communications |
| Orchestration | Maestro Orchestration Center | Orchestration Center | Orchestration Center | Industrial Automation Hub |
| Human resources / supply | Staffing & Operations | Compliance Center | Fulfillment Operations | Supply Chain Management |
| Failover | Failover Infrastructure | DR Site | Backup Infrastructure | Backup Control Center |

### The Five AI Agents

Each scenario has five agents mapped to the same five role types:

| Role | Healthcare | Financial | Retail | Manufacturing |
|------|-----------|-----------|--------|---------------|
| Operations Coordinator | ARIA | MERIDIAN | FLUX | FORGE |
| Incident Response | SENTINEL | GUARDIAN | SHIELD | TITAN |
| Compliance | VERITAS | LEXIS | CIPHER | PRISM |
| Communications | ECHO | HERALD | PULSE | BEACON |
| Executive Strategy | APEX | NEXUS | SUMMIT | APEX |

### The Five UiPath Processes

Each scenario configures scenario-specific process names (e.g., `Trade_Incident_Escalation`
vs. `Production_Incident_Escalation`). The trigger logic is the same; only the process name
and vocabulary differ.

| Process | Triggered By | Human Approval? |
|---------|-------------|-----------------|
| `<Scenario>_Incident_Escalation` | Building health drops below 60 | No (auto) |
| `<Scenario>_Approval_Chain` | Workflow risk score > 0.7 | Yes (if > 0.85) |
| `<Scenario>_Crisis_Response` | Two or more buildings degraded simultaneously | Yes (always) |
| `<Scenario>_Staffing` | Staffing level < 30% or human strain > 80% | No (auto) |
| `Trust_Recovery_Protocol` | System trust drops > 10 points in one tick | No (auto) |

---

## Quick Start (5 Steps)

### Prerequisites

- Python 3.11 or later
- Node.js 18 or later
- `pip` and `npm` available in your `PATH`
- A UiPath Cloud account (optional — the sim runs without it)

### Step 1: Clone and Install

```bash
git clone <repo-url> maestro-city
cd maestro-city
npm run install:all
```

If `npm run install:all` fails on the Python side:
```bash
cd apps/backend
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
cp apps/backend/.env.example apps/backend/.env
```

At minimum the simulation works with no changes. To connect UiPath, fill in the five
`UIPATH_*` variables:

```env
UIPATH_ORGANIZATION=your-org
UIPATH_TENANT=your-tenant
UIPATH_CLIENT_ID=your-client-id
UIPATH_CLIENT_SECRET=your-client-secret
UIPATH_FOLDER_ID=12345
```

To enable the Coding Agent (AI-generated XAML):

```env
OPENAI_API_KEY=sk-...
```

See [docs/UIPATH_PLATFORM_SETUP.md](./UIPATH_PLATFORM_SETUP.md) for exact instructions.

### Step 3: Start the Backend

```bash
cd apps/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Start the Frontend

In a new terminal:
```bash
cd apps/frontend
npm run dev
```

Or run both from the project root:
```bash
npm run dev
```

### Step 5: Open the App

Go to **http://localhost:3000**. The scenario selector appears — choose an industry
scenario to start the simulation.

---

## Scenario API

The frontend communicates with these endpoints to drive the scenario selector:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scenarios` | GET | List all available scenarios with metadata |
| `/api/scenario/select` | POST | Switch to a scenario (resets simulation) |
| `/api/scenario/active` | GET | Return the active scenario (for page reload restore) |
| `/api/scenario/reset` | POST | Reset current scenario to initial state |

---

## How to Add a New Scenario

The scenario system is designed for this. Adding a new enterprise scenario requires **one file**.

### Step 1: Create the scenario file

```bash
touch apps/backend/scenarios/my_new_scenario.py
```

### Step 2: Implement `get_scenario()`

Copy the structure from any existing scenario (e.g., `scenarios/healthcare.py`) and fill
in your values. The `ScenarioDefinition` dataclass documents every field:

```python
from scenarios.base import ScenarioDefinition

def get_scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        id="energy",                          # URL-safe, unique
        name="Energy & Utilities",            # Display name on the card
        tagline="Keep the grid stable under ...",  # One sentence for the card
        description="...",                    # 2–3 sentences for detail panel
        industry="Energy",
        icon="⚡",
        color="#EAB308",                      # Hex accent used for card border/glow

        # 7 buildings — use the existing BuildingType enum values for visuals.
        # The renderer uses `type` for the sprite, `name` is display-only.
        # BuildingType options: hospital, pharmacy, cloud_datacenter, comms_hub,
        #                       orchestration_center, staffing_hr, backup_infra
        buildings=[
            {
                "id": "control_room",        # unique within this scenario
                "type": "hospital",           # picks the visual sprite
                "name": "Grid Control Room",  # shown in tooltips
                "pos": {"x": 1, "y": 1, "w": 3, "h": 3},
                "status": "operational",
                "health": 100.0,
                "throughput": 90.0,
                "staffingLevel": 75.0,
                "trustLevel": 90.0,
                "dependencies": ["cloud_datacenter", "orchestration_center"],
                "queueDepth": 10,
                "recoveryCapacity": 60.0,
            },
            # ... 6 more buildings
        ],

        # 5 agents — use the existing AgentType enum values.
        # AgentType options: operations_coordinator, incident_response, compliance,
        #                    communications, executive_strategy
        agents=[
            {
                "id": "ops_coord",
                "type": "operations_coordinator",
                "name": "VOLT",               # scenario-specific name
                "autonomyLevel": 2,
                "trustScore": 85.0,
                "status": "idle",
                "lastAction": "Grid load balancing and substation coordination",
                "lastActionAt": 0.0,
                "actionsThisTick": 0,
                "currentBuildingId": "orchestration_center",
                "targetBuildingId": None,
            },
            # ... 4 more agents
        ],

        # Workflows connecting buildings (use existing WorkflowType enum values)
        workflows=[
            {"id": "wf-001", "type": "ehr_record", "sourceId": "control_room",
             "destId": "orchestration_center", "priority": "high",
             "status": "flowing", "automationEligible": True, "risk": 0.20, "progress": 0.40},
            # ...
        ],

        # Dependency edges: (from_id, to_id) — cascade propagates along these
        dependency_edges=[
            ("control_room", "cloud_datacenter"),
            # ...
        ],

        # Vocabulary maps generic labels to industry terms in reports and runbooks
        vocabulary={
            "service_unit": "megawatt-hour",
            "primary_system": "Grid Control Room",
            "secondary_system": "Substation Network",
            "workflow_type_primary": "load dispatch",
            "workflow_type_secondary": "fault isolation",
            "staffing_role": "grid operator",
            "incident_name": "Grid Stability Incident",
            "outage_label": "Grid Outage",
            "org_unit": "substation",
        },

        compliance_frameworks=["NERC CIP", "IEC 62351", "FERC Order 2222"],

        # Process names must match your Orchestrator folder releases exactly
        uipath_processes=[
            "Grid_Incident_Escalation",
            "Grid_Approval_Chain",
            "Grid_Crisis_Response",
            "Operator_Coverage_Staffing",
            "Trust_Recovery_Protocol",
        ],

        # Outage presets shown in the trigger panel
        outage_presets=[
            {
                "id": "control_room_failure",
                "name": "Grid Control Room Failure",
                "buildingId": "control_room",
                "severity": "full",
                "description": "Primary control room failure — grid visibility lost",
            },
        ],

        industry_context=(
            "Electric grid operations require continuous availability of control systems "
            "to maintain frequency stability and prevent cascading outages under NERC CIP."
        ),
    )
```

### Step 3: Register it

Open `apps/backend/scenarios/registry.py` and add two lines:

```python
from scenarios.my_new_scenario import get_scenario as get_energy  # add this

SCENARIO_REGISTRY = {
    "healthcare": get_healthcare(),
    "financial_services": get_financial(),
    "retail_ecommerce": get_retail(),
    "manufacturing": get_manufacturing(),
    "energy": get_energy(),               # add this
}
```

That's it. The scenario now appears in the frontend selector, generates scenario-specific
after-action reports and runbooks, and uses the correct UiPath process names in all outputs.
No frontend changes required.

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | URL-safe identifier used in API calls |
| `name` | string | Full display name |
| `tagline` | string | One sentence shown on the scenario card |
| `description` | string | 2–3 sentences for the detail view |
| `industry` | string | Industry pill label |
| `icon` | string | Emoji displayed on the card and in reports |
| `color` | string | Hex accent color (`#RRGGBB`) |
| `buildings` | list | 7 building dicts — must include all required fields |
| `agents` | list | 5 agent dicts — one per role type |
| `workflows` | list | Initial workflow connections |
| `dependency_edges` | list | `(from_id, to_id)` tuples for cascade propagation |
| `vocabulary` | dict | Maps generic terms to scenario-specific language in reports |
| `compliance_frameworks` | list | Shown as pills on the card and cited in reports |
| `uipath_processes` | list | Orchestrator release names for all 5 processes |
| `outage_presets` | list | Named outage presets shown in the trigger panel |
| `industry_context` | string | Paragraph used in executive summary of after-action report |

---

## How to Play

### The Goal

Keep the city operational. Operational Stability should stay above 50. System Trust should
stay above 40. If either collapses to zero, the simulation enters **Collapsed** phase.

### Controls

**Click a building** to see its health, throughput, staffing level, and trust score.
From the building panel you can:
- **Trigger Outage**: Drop the building's health to simulate a failure.
- **Restore Building**: Immediately restore health to 80%.
- **Activate Failover**: Route the building's workflows through backup infrastructure.
- **Set Staffing Level**: Drag to adjust staffing (reduces human strain).

**Click an agent** to see its status and autonomy level:
- **Set Autonomy Level**: 0 (fully human) through 4 (fully autonomous).

**Left sidebar — Overlay modes:**
- **Dependency**: highlights the dependency graph between buildings.
- **Congestion**: shows queue depths (red = backlogged).
- **Trust**: heatmap of building and agent trust scores.
- **Staffing**: shows staffing levels (blue = fully staffed, red = overloaded).
- **Outage**: highlights buildings in degraded/critical/offline state.
- **Orchestration**: shows active UiPath job flows.

**Toolbar:**
- **Reports**: generates and downloads all four enterprise deliverables.
- **Coding Agent**: generates a context-aware UiPath XAML workflow from current sim state.
- **Agent Builder**: shows all 5 agent configurations with UiPath deployment details.

### Demo Script (5-Minute Walkthrough)

**Minute 1 — Scenario Selection**
Open the app. The scenario selector landing page appears. Walk through the four industry
cards — point out different compliance frameworks, agent names, and UiPath process names.
Select **Healthcare Enterprise** (or Financial Services for a trading-focused audience).

**Minute 2 — Trigger an Incident**
Click the **cloud infrastructure building** (CloudCore Data Center / Cloud Infrastructure /
Cloud Platform / Cloud SCADA Platform depending on scenario). Click **Trigger Outage → Full**.
Watch the cascade: dependent buildings degrade within 2–3 ticks, the alert feed fires, and
the UiPath status panel shows the first automation job.

**Minute 3 — Watch the Cascade**
Do nothing for 5–8 ticks. Human Strain rises, System Trust drops. If UiPath is connected,
the crisis response job triggers and an executive action item appears in the Maestro panel.

**Minute 4 — Intervene**
Activate failover, set staffing to 90%, and approve any pending Maestro action items.
Point out how the after-action report will capture exactly these interventions.

**Minute 5 — Download Outputs**
Click **Reports**. Download the After-Action Report, Runbook, and Calibration Certificate.
Click **Coding Agent → Crisis Response** to generate context-aware XAML that reflects
the exact crisis you just ran through.

### Tips

- Set `VERITAS` (compliance) to autonomy level 0 — every high-risk approval becomes a
  Maestro action item, making the human-in-the-loop story very visible.
- Lower `SIMULATION_TICK_INTERVAL` to `0.25` in `.env` for a fast demo. Raise to `3.0`
  to give more time to explain each step.
- Do not let `human_strain > 85` persist for more than 5 ticks — triggers emergency staffing.

---

## Project Structure

```
maestro-city/
├── apps/
│   ├── backend/                        # FastAPI simulation engine
│   │   ├── main.py                     # App entrypoint, lifecycle, router mounts
│   │   ├── scenarios/                  # ← Scenario registry (plug-in architecture)
│   │   │   ├── base.py                 # ScenarioDefinition dataclass
│   │   │   ├── registry.py             # SCENARIO_REGISTRY + list/get functions
│   │   │   ├── healthcare.py           # 🏥 Healthcare Enterprise scenario
│   │   │   ├── financial_services.py   # 📈 Financial Services scenario
│   │   │   ├── retail_ecommerce.py     # 🛒 Retail & E-commerce scenario
│   │   │   └── manufacturing.py        # 🏭 Manufacturing & Industry 4.0 scenario
│   │   ├── simulation/
│   │   │   ├── city_config.py          # Delegates to active scenario definition
│   │   │   ├── engine.py               # Tick loop, cascade logic, select_scenario()
│   │   │   ├── scenario_tracker.py     # Per-tick intervention and event tracking
│   │   │   ├── after_action_reporter.py# Generates scenario-specific AAR
│   │   │   ├── runbook_generator.py    # Generates validated runbook
│   │   │   └── autonomy_calibrator.py  # Per-agent readiness certificate
│   │   ├── api/
│   │   │   ├── routes.py               # Main REST routes + scenario endpoints
│   │   │   ├── agent_builder.py        # Agent definitions with UiPath metadata
│   │   │   ├── coding_agent.py         # OpenAI GPT-4o XAML generation
│   │   │   ├── enterprise_systems.py   # Integration Service API trigger endpoints
│   │   │   ├── approvals.py            # Maestro approval queue
│   │   │   └── websocket.py            # WebSocket state broadcaster
│   │   ├── models/
│   │   │   ├── building.py             # Building type, status, health model
│   │   │   ├── workflow.py             # Workflow routing model
│   │   │   ├── agent.py                # Agent type, autonomy, trust model
│   │   │   ├── state.py                # Full SimulationState, UiPath status models
│   │   │   └── actions.py              # Player action types
│   │   ├── agents/                     # Per-agent decision logic
│   │   ├── orchestration/
│   │   │   ├── uipath_client.py        # OAuth 2.0, StartJobs, API Triggers
│   │   │   ├── escalation_router.py    # Routes events to correct processes
│   │   │   ├── webhook_handler.py      # Webhook receipt + HMAC verification
│   │   │   └── process_template_generator.py  # XAML scaffold templates
│   │   ├── requirements.txt
│   │   └── .env.example
│   └── frontend/                       # Next.js + PixiJS
│       ├── app/page.tsx                # Conditional: ScenarioSelector or city view
│       ├── components/
│       │   ├── ScenarioSelector.tsx    # ← Full-screen scenario landing page
│       │   ├── TopBar.tsx              # Scenario badge + toolbar controls
│       │   ├── city/                   # PixiJS rendering (CityCanvas, sprites)
│       │   ├── panels/                 # MetricsPanel, AlertFeed, ControlsPanel
│       │   ├── reports/                # AfterActionReport, Runbook, etc.
│       │   ├── AgentBuilderPanel.tsx   # Agent config viewer
│       │   └── CodeGenModal.tsx        # Coding Agent XAML viewer
│       ├── lib/
│       │   ├── store.ts                # Zustand store (sim state + scenario state)
│       │   └── reports.ts              # Report type definitions
│       └── types/game.ts               # Frontend-specific types
├── packages/
│   └── shared-types/src/index.ts       # Shared TypeScript types
├── docs/
│   ├── README.md                       # This file
│   ├── UIPATH_PLATFORM_SETUP.md        # Step-by-step UiPath configuration guide
│   ├── UIPATH_INTEGRATION.md           # Developer API reference
│   ├── AGENT_BUILDER_SETUP.md          # Agent Builder click-by-click setup
│   └── CODING_AGENT.md                 # Coding Agent (GPT-4o XAML generation)
└── package.json                        # Workspace root with dev/build scripts
```

---

## Environment Variables

Full reference in [docs/UIPATH_INTEGRATION.md](./UIPATH_INTEGRATION.md#environment-variables-reference).

| Variable | Required | Description |
|----------|----------|-------------|
| `UIPATH_ORGANIZATION` | Yes* | Your organisation name from the Cloud URL |
| `UIPATH_TENANT` | Yes* | Tenant name within your organisation |
| `UIPATH_CLIENT_ID` | Yes* | OAuth 2.0 client ID |
| `UIPATH_CLIENT_SECRET` | Yes* | OAuth 2.0 client secret |
| `UIPATH_FOLDER_ID` | Yes* | Orchestrator folder ID (integer) |
| `UIPATH_WEBHOOK_SECRET` | No | HMAC secret for webhook signature verification |
| `OPENAI_API_KEY` | No | Enables Coding Agent XAML generation via GPT-4o |
| `SIMULATION_TICK_INTERVAL` | No | Seconds per tick (default: 1.0) |
| `ACTIVE_SCENARIO` | No | Default scenario on cold start (default: `healthcare`) |
| `UIPATH_ARIA_PROCESS_NAME` | No | Override Orchestrator process name for ARIA |
| `UIPATH_SENTINEL_PROCESS_NAME` | No | Override Orchestrator process name for SENTINEL |
| `UIPATH_VERITAS_PROCESS_NAME` | No | Override Orchestrator process name for VERITAS |

`*` Required only for UiPath integration. The simulation runs without them.

---

## UiPath Setup

See **[docs/UIPATH_PLATFORM_SETUP.md](./UIPATH_PLATFORM_SETUP.md)** for the complete
step-by-step setup guide, including:

- Creating the OAuth external application and scopes
- Setting up the MaestroCity Orchestrator folder
- Building all five Studio automation projects with exact arguments
- Configuring Integration Service API triggers
- Configuring webhooks
- Testing the integration end-to-end

See **[docs/AGENT_BUILDER_SETUP.md](./AGENT_BUILDER_SETUP.md)** for the Agent Builder
setup guide: defining all five agents with system prompts, tool schemas, and trigger
conditions.

See **[docs/CODING_AGENT.md](./CODING_AGENT.md)** for how the Coding Agent bonus feature
works: GPT-4o generating context-aware UiPath XAML from live simulation state.

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend UI | Next.js (App Router) | 14.x |
| 2D Rendering | PixiJS via @pixi/react | 7.x |
| Frontend State | Zustand | 4.x |
| Backend | FastAPI + Uvicorn | 0.111 / 0.30 |
| HTTP Client | HTTPX (async) | 0.27 |
| Data Models | Pydantic v2 | 2.7 |
| Simulation | Pure Python | — |
| Real-Time | WebSockets (native FastAPI) | — |
| XAML Generation | OpenAI GPT-4o | — |
| Automation | UiPath Orchestrator (REST API v2) | Cloud |

---

## Hackathon Submission

**Event**: UiPath AgentHack

**Track**: Enterprise Automation + Human-in-the-Loop AI

**Team**: djbobbysocks@gmail.com

### What Makes This Submission Stand Out

1. **Four complete enterprise scenarios** — the simulation is not a healthcare demo with
   a coat of paint for other industries. Each scenario has fully independent building IDs,
   agent names, compliance frameworks, UiPath process names, outage presets, and report
   vocabulary. Switching scenarios resets and reconfigures the entire simulation.

2. **End-to-end UiPath integration** — real OAuth 2.0 authentication, real job triggering
   via the StartJobs API, real Integration Service API triggers, real webhook receipt and
   HMAC verification. This is not a mock.

3. **Genuine agentic decision-making** — five agents with independent autonomy levels make
   different choices in the same situation. The incident response agent at level 4 auto-escalates
   without asking; the compliance agent at level 1 blocks everything for human review.

4. **Human-in-the-loop by design** — Maestro action items are not an afterthought.
   High-risk approval decisions halt the simulation until a human approves. The simulation
   reflects the outcome the moment the form is submitted.

5. **Actionable enterprise outputs** — four downloadable artifacts per scenario run that
   cross back into real operational decisions: an evidence-based post-incident report, a
   validated runbook, an autonomy calibration certificate, and importable Studio projects.

6. **Extensible by design** — adding a fifth scenario is one file and two lines. Adding a
   sixth enterprise deliverable follows the same pattern in `simulation/`.

### Demo Checklist

- [ ] Scenario selector appears on first load; all 4 scenarios visible with compliance badges
- [ ] Selecting a scenario resets and starts the simulation
- [ ] City grid renders with buildings, workflow particles, and agent drones
- [ ] Triggering an outage causes visible cascade in the grid
- [ ] TopBar shows active scenario name and "Change" button
- [ ] UiPath panel shows active jobs (requires UiPath credentials)
- [ ] Maestro action items appear for high-risk approvals
- [ ] After-Action Report uses scenario-specific terminology
- [ ] Coding Agent button generates context-aware XAML (requires `OPENAI_API_KEY`)
- [ ] Simulation runs correctly in offline mode (no UiPath credentials)
