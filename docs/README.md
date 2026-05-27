# Maestro City — UiPath AgentHack Submission

Maestro City is a real-time city management simulation that demonstrates **human-in-the-loop
AI orchestration** using UiPath Maestro and Orchestrator. You manage a living digital
city powered by five autonomous AI agents. When the city goes wrong — outages cascade,
staff burn out, workflows jam — UiPath automation kicks in: escalating incidents, routing
approvals, coordinating crisis response, and rebuilding trust. You watch it all happen,
intervene when needed, and decide how much authority to give the machines.

Built for the **UiPath AgentHack** hackathon.

---

## What It Demonstrates

- **Agentic Orchestration**: Five specialised agents (ARIA, SENTINEL, VERITAS, ECHO, APEX)
  operate autonomously at configurable autonomy levels (0 = fully manual, 4 = fully
  autonomous). Their decisions are routed through UiPath Orchestrator as real automation jobs.

- **Human-in-the-Loop**: High-risk decisions surface as UiPath Maestro action items.
  A human approver in the Maestro UI can approve or reject them; the simulation responds
  immediately.

- **Real-Time Feedback**: Every UiPath job start and completion is reflected live in the
  city grid via WebSocket — watch a staffing robot deploy, see an escalation resolve a
  cascade, observe trust scores recover after a compliance audit.

- **Graceful Degradation**: The simulation runs fully without UiPath credentials. Plug in
  your credentials at any time to switch from simulation-only mode to live automation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Maestro City                                       │
│                                                                             │
│   Browser (Next.js + PixiJS)                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  City Grid (7 buildings, 24 workflows, 5 agent drones)             │  │
│   │  Live metrics panel  │  Agent HUD  │  UiPath status panel          │  │
│   └──────────────────────────┬──────────────────────────────────────────┘  │
│                              │ WebSocket (ws://localhost:8000/ws)           │
│   ┌──────────────────────────▼──────────────────────────────────────────┐  │
│   │  FastAPI Backend (Python)                                           │  │
│   │  • Simulation engine (tick loop, building health, cascade logic)   │  │
│   │  • Agent decision engine (5 agent types × 5 autonomy levels)       │  │
│   │  • UiPath client (OAuth 2.0, job triggering, webhook receiver)     │  │
│   │  • State broadcaster (JSON over WebSocket every tick)              │  │
│   └──────────────────────────┬──────────────────────────────────────────┘  │
└─────────────────────────────│────────────────────────────────────────────┘
                               │ HTTPS REST (OAuth 2.0 Bearer token)
                               │ Webhooks (POST /api/uipath/webhook)
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  UiPath Cloud                                                               │
│  • Orchestrator: 5 automation processes in MaestroCity folder              │
│  • Maestro: action items, approvals, agent catalog                         │
│  • Serverless robots: execute processes on demand                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Seven Buildings

| Building                  | ID                    | Role                                           |
|---------------------------|-----------------------|------------------------------------------------|
| City General Hospital     | `hospital`            | Patient workflow hub; highest staffing demand  |
| Central Pharmacy          | `pharmacy`            | Prescription processing; depends on hospital   |
| CloudCore Data Center     | `cloud_datacenter`    | Core infrastructure; cascade origin point      |
| Communications Hub        | `comms_hub`           | Alert routing; bridges data center to rest     |
| Maestro Orchestration Center | `orchestration_center` | UiPath integration node; approval gateway   |
| Staffing & Operations     | `staffing_hr`         | Human resource dispatch                        |
| Failover Infrastructure   | `backup_infra`        | Emergency routing when cloud_datacenter fails  |

### The Five AI Agents

| Agent   | Name     | Type                   | Default Autonomy | Home Building          |
|---------|----------|------------------------|------------------|------------------------|
| ARIA    | ARIA     | Operations Coordinator | 2 (supervised)   | Orchestration Center   |
| SENTINEL| SENTINEL | Incident Response      | 2 (supervised)   | CloudCore Data Center  |
| VERITAS | VERITAS  | Compliance             | 1 (human-led)    | City General Hospital  |
| ECHO    | ECHO     | Communications         | 2 (supervised)   | Communications Hub     |
| APEX    | APEX     | Executive Strategy     | 1 (human-led)    | Orchestration Center   |

### The Five UiPath Processes

| Process                   | Triggered By                                 | Human Approval? |
|---------------------------|----------------------------------------------|-----------------|
| `Incident_Escalation`     | Building health drops below 60               | No (auto)       |
| `Approval_Chain`          | Workflow risk score > 0.7                    | Yes (if > 0.85) |
| `Crisis_Response`         | Two or more buildings degraded simultaneously| Yes (always)    |
| `Emergency_Staffing`      | Staffing level < 30% or human strain > 80%   | No (auto)       |
| `Trust_Recovery_Protocol` | System trust drops > 10 points in one tick   | No (auto)       |

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

This installs Node dependencies for the frontend and Python dependencies for the backend.

If `npm run install:all` fails on the Python side:
```bash
cd apps/backend
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
cp apps/backend/.env.example apps/backend/.env
```

Open `apps/backend/.env` in a text editor. At minimum the simulation works with no
changes. To connect UiPath, fill in the five `UIPATH_*` variables:

```env
UIPATH_ORGANIZATION=your-org
UIPATH_TENANT=your-tenant
UIPATH_CLIENT_ID=your-client-id
UIPATH_CLIENT_SECRET=your-client-secret
UIPATH_FOLDER_ID=12345
```

See [docs/UIPATH_PLATFORM_SETUP.md](./UIPATH_PLATFORM_SETUP.md) for exact instructions
on where to find each value.

### Step 3: Start the Backend

```bash
cd apps/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Simulation engine started — tick interval: 1.0s
```

If UiPath is configured:
```
INFO:     UiPath client initialised — org=your-org tenant=your-tenant folder=12345
```

If not configured:
```
INFO:     UiPath not configured — running in offline mode
```

### Step 4: Start the Frontend

In a new terminal:
```bash
cd apps/frontend
npm run dev
```

You should see:
```
  ▲ Next.js 14.x.x
  - Local:  http://localhost:3000
```

### Step 5: Open the App

Go to **http://localhost:3000** in your browser.

The city grid appears. The simulation starts automatically. Within 30 seconds you should
see workflow particles moving between buildings, agent drones patrolling, and the
metrics panel updating each tick.

To run both backend and frontend simultaneously from the project root:
```bash
npm run dev
```

---

## Environment Variables

Full reference in [docs/UIPATH_INTEGRATION.md](./UIPATH_INTEGRATION.md#environment-variables-reference).

| Variable                   | Required | Description                                    |
|----------------------------|----------|------------------------------------------------|
| `UIPATH_CLOUD_URL`         | No       | UiPath Cloud base URL (default: https://cloud.uipath.com) |
| `UIPATH_ORGANIZATION`      | Yes*     | Your organisation name from the cloud URL      |
| `UIPATH_TENANT`            | Yes*     | Tenant name within your organisation           |
| `UIPATH_CLIENT_ID`         | Yes*     | OAuth 2.0 client ID                            |
| `UIPATH_CLIENT_SECRET`     | Yes*     | OAuth 2.0 client secret                        |
| `UIPATH_FOLDER_ID`         | Yes*     | Orchestrator folder ID (integer)               |
| `UIPATH_WEBHOOK_SECRET`    | No       | HMAC secret for webhook signature verification |
| `OPENAI_API_KEY`           | No       | Enables LLM narrative generation               |
| `SIMULATION_TICK_INTERVAL` | No       | Seconds per tick (default: 1.0)                |

`*` Required only for UiPath integration. The simulation runs without them.

---

## UiPath Setup

See **[docs/UIPATH_PLATFORM_SETUP.md](./UIPATH_PLATFORM_SETUP.md)** for the complete
step-by-step setup guide, including:

- Creating the OAuth external application and scopes
- Setting up the MaestroCity Orchestrator folder
- Building all five Studio automation projects with exact arguments
- Configuring webhooks
- Testing the integration end-to-end

See **[docs/UIPATH_INTEGRATION.md](./UIPATH_INTEGRATION.md)** for the developer
technical reference, including:

- Full REST API call examples with request/response bodies
- HMAC webhook verification implementation
- Simulation event → UiPath process mapping table
- Error handling and offline mode behaviour
- Rate limit guidance

---

## How to Play

### The Goal

Keep the city operational. Operational Stability should stay above 50. System Trust
should stay above 40. If either collapses to zero, the simulation enters **Collapsed**
phase — game over.

### Controls

**Click a building** to see its health, throughput, staffing level, and trust score.
From the building panel you can:
- **Trigger Outage**: Drop the building's health to simulate a failure.
- **Restore Building**: Immediately restore health to 80%.
- **Activate Failover**: Route the building's workflows through `backup_infra`.
- **Set Staffing Level**: Drag to adjust staffing (reduces human strain).

**Click an agent** (the glowing drone on the grid) to see its status and autonomy level.
From the agent panel you can:
- **Set Autonomy Level**: 0 (fully human) through 4 (fully autonomous).
  Lower autonomy = the agent asks for more approvals. Higher = acts independently.

**Left sidebar — Overlay modes:**
- **Dependency**: highlights the dependency graph between buildings (which buildings
  fail if cloud_datacenter goes offline).
- **Congestion**: shows queue depths (red = backlogged).
- **Trust**: heatmap of building and agent trust scores.
- **Staffing**: shows staffing levels (blue = fully staffed, red = overloaded).
- **Outage**: highlights buildings in degraded/critical/offline state.
- **Orchestration**: shows active UiPath job flows.

**UiPath Status Panel** (bottom right):
- Shows whether UiPath is connected.
- Lists active jobs currently running on Orchestrator.
- Lists pending Maestro action items awaiting human approval.
- Click an action item to open the Maestro approval UI directly.

### Demo Script (5-Minute Walkthrough)

**Minute 1 — Introduction**
Open the app. Point out the seven buildings, the workflow particles flowing between
them, and the metrics panel showing all-green. Explain the three critical metrics:
Operational Stability, Human Strain, and System Trust.

**Minute 2 — Trigger an Incident**
Click the **CloudCore Data Center** building. Click **Trigger Outage → Full**. Watch:
- Building health drops to near zero.
- Dependent buildings (hospital, pharmacy, orchestration center, comms hub) begin
  degrading within 2–3 ticks.
- If UiPath is connected: `Incident_Escalation` job appears in the UiPath status panel.
  A critical alert fires in the alert log.
- SENTINEL agent switches to `escalating` status and moves toward the data center.

**Minute 3 — Watch the Cascade**
Do nothing. After 5–8 ticks, the cascade propagates:
- Hospital and pharmacy degrade.
- Human Strain rises as queues back up.
- If UiPath is connected: `Crisis_Response` job triggers automatically. An executive
  action item appears in the Maestro panel.
- System Trust begins dropping.

**Minute 4 — Intervene**
- Click **Failover Infrastructure** > **Activate Failover for CloudCore**. Workflows
  begin routing through the backup.
- Click **Staffing & Operations** > **Set Staffing Level 90%**. Human Strain starts
  dropping.
- If UiPath is connected: click the pending Maestro action item to open the approval
  form. Approve the crisis response plan. The simulation's recovery timeline accelerates.

**Minute 5 — Recovery**
- Click **CloudCore Data Center** > **Restore Building**.
- Watch the cascade reverse: pharmacy and hospital recover, workflows resume, trust
  climbs back.
- If UiPath is connected: `Trust_Recovery_Protocol` fires automatically when trust
  recovers past 50. Recommended autonomy levels appear in the agent HUD.

### Tips

- Do not let `human_strain > 85` persist for more than 5 ticks — it causes a
  `staffing_exhaustion` crisis that triggers `Emergency_Staffing`.
- VERITAS (compliance agent) at autonomy level 0 blocks all high-risk approvals manually.
  Great for demos — every approval lights up as a Maestro action item.
- Lower `SIMULATION_TICK_INTERVAL` to `0.25` in `.env` for a fast demo. Increase to
  `3.0` to give more time to explain each step.

---

## Project Structure

```
maestro-city/
├── apps/
│   ├── backend/                  # FastAPI simulation engine
│   │   ├── main.py               # App entrypoint, WebSocket handler, API routes
│   │   ├── simulation/
│   │   │   ├── city_config.py    # Initial city state: buildings, workflows, agents
│   │   │   └── engine.py         # Tick loop, cascade logic, agent decisions
│   │   ├── models/
│   │   │   ├── building.py       # Building type, status, health model
│   │   │   ├── workflow.py       # Workflow routing model
│   │   │   ├── agent.py          # Agent type, autonomy, trust model
│   │   │   ├── state.py          # Full SimulationState, UiPath status models
│   │   │   └── actions.py        # Player action types (union discriminated)
│   │   ├── uipath/
│   │   │   ├── client.py         # OAuth token cache, StartJobs, Releases API
│   │   │   └── webhook.py        # Webhook receiver, HMAC verification
│   │   ├── requirements.txt
│   │   └── .env.example
│   └── frontend/                 # Next.js + PixiJS
│       ├── app/                  # Next.js App Router pages
│       ├── components/
│       │   ├── CityCanvas.tsx    # PixiJS rendering layer
│       │   ├── BuildingSprite.tsx
│       │   ├── AgentDrone.tsx
│       │   ├── WorkflowParticle.tsx
│       │   ├── MetricsPanel.tsx
│       │   ├── UiPathPanel.tsx   # Active jobs + action items display
│       │   └── AlertLog.tsx
│       ├── lib/
│       │   ├── store.ts          # Zustand game state store
│       │   └── websocket.ts      # WS client + action dispatcher
│       └── types/game.ts         # Frontend-specific types
├── packages/
│   └── shared-types/
│       └── src/index.ts          # Shared TypeScript types (Building, Agent, etc.)
├── docs/
│   ├── README.md                 # This file
│   ├── UIPATH_PLATFORM_SETUP.md  # Step-by-step UiPath configuration guide
│   └── UIPATH_INTEGRATION.md     # Developer technical reference
└── package.json                  # Workspace root with dev/build scripts
```

---

## Technology Stack

| Layer          | Technology                          | Version |
|----------------|-------------------------------------|---------|
| Frontend UI    | Next.js (App Router)                | 14.x    |
| 2D Rendering   | PixiJS via @pixi/react              | 7.x     |
| Frontend State | Zustand                             | 4.x     |
| Backend        | FastAPI + Uvicorn                   | 0.111 / 0.30 |
| HTTP Client    | HTTPX (async)                       | 0.27    |
| Data Models    | Pydantic v2                         | 2.7     |
| Simulation     | Pure Python + NetworkX (graph deps) | 3.3     |
| Real-Time      | WebSockets (native FastAPI)         | —       |
| Automation     | UiPath Orchestrator (REST API v2)   | Cloud   |

---

## Hackathon Submission

**Event**: UiPath AgentHack

**Track**: Enterprise Automation + Human-in-the-Loop AI

**Team**: djbobbysocks@gmail.com

### What Makes This Submission Stand Out

1. **End-to-end UiPath integration** — real OAuth 2.0 authentication, real job
   triggering via the StartJobs API, real webhook receipt and verification. This is not
   a mock.

2. **Genuine agentic decision-making** — five agents with independent autonomy levels
   make different choices in the same situation. SENTINEL at level 4 auto-escalates
   without asking. VERITAS at level 1 blocks everything for human review.

3. **Human-in-the-loop by design** — Maestro action items are not an afterthought.
   High-risk approval decisions halt the simulation until a human approves in the Maestro
   UI. The simulation state reflects the outcome the moment the form is submitted.

4. **Graceful degradation** — the simulation is a fully playable experience even without
   UiPath credentials. This makes live demos reliable.

5. **Production-quality codebase** — typed models shared between frontend and backend,
   HMAC webhook security, async token caching with proactive refresh, deduplication
   guards against event storms, per-building dependency graph for realistic cascades.

### Demo Checklist

- [ ] App starts with `npm run dev` from repo root
- [ ] City grid renders with all seven buildings and workflow particles
- [ ] Triggering an outage causes visible cascade in the grid
- [ ] UiPath panel shows active jobs (requires UiPath credentials)
- [ ] Webhook panel updates when jobs complete (requires UiPath + public endpoint)
- [ ] Maestro action items appear for high-risk approvals (requires UiPath Maestro tier)
- [ ] Approving/rejecting in Maestro reflects in simulation within 1–2 ticks
- [ ] Simulation continues correctly in offline mode (no UiPath credentials set)
