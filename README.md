# Maestro City

**An autonomous enterprise-operations simulator where five AI agents keep a digital city running — orchestrated end-to-end through UiPath.**

Built for the [UiPath AgentHack](https://uipath-agenthack.devpost.com/) (Track 1 — Maestro Case). When a system fails, the agents reason over the situation using **UiPath's LLM Gateway**, fire **real Orchestrator jobs**, and gate high-risk actions behind **human approval** — either as individual processes or as a single **Maestro Case** instance, toggleable live in the UI.

---

## What it does

- A live "city" of enterprise systems (EHR, data center, pharmacy, comms, …) runs on a real-time tick loop.
- Five role-based agents — **APEX** (executive strategy), **SENTINEL** (incident response), **VERITAS** (compliance), **ECHO** (communications), **ARIA** (operations) — monitor the city and act within configurable **autonomy levels**.
- When an outage hits, agents start **real UiPath jobs** on serverless robots. Coded agents reason with **gpt-4.1-mini through UiPath's LLM Gateway** (no direct OpenAI calls).
- High-risk actions are **gated for human approval**; the Maestro Case delivers the approval task to Action Center.
- A **Coding Agent** and **custom-scenario generator** also run on UiPath robots — generating XAML workflows and new scenarios from natural language.

> **No silent fallbacks.** If UiPath or the LLM is unavailable, failures surface in the UI (a `Faulted` job, an error toast) rather than being faked. You always know whether it really ran.

---

## Why an enterprise would actually use this

The city is the demo vehicle. The **sellable asset is the agentic incident-response layer underneath it** — the UiPath coded agents, the Orchestrator runbooks, and the Maestro Case with human-approval gates. **Maestro City is the rehearsal-and-validation environment for that layer.**

> You wouldn't put an AI agent in charge of your incident response without testing it first — but there's no safe place to test autonomous, cross-system crisis response. Maestro City is that place. The **same** coded agents and Orchestrator runbooks that would run in production get stress-tested against cascading-failure scenarios — with human-approval gates proven out — before they ever touch a real system.

It lands in budget lines enterprises already fund:

| Existing budget | What Maestro City extends it to |
|---|---|
| Disaster-recovery drills / tabletop exercises | …exercising **AI agents that take autonomous action**, not just human runbooks |
| Chaos engineering (Gremlin, AWS FIS) | …at the **business-process / orchestration** layer, not just infrastructure |
| SOC / NOC operator training | …rehearsing **cross-functional cascade response** in one pane of glass |

**This is not hypothetical.** Recent cascading failures — the AWS region outage, Change Healthcare (~$2.3B response), Ascension (~$1.3B), TSB (£330M) — are the bill for an *unrehearsed* response. Modern operations fail as networks, vendors, payments, cloud regions, identity, staffing, and recovery workflows cascade together. Every one of those is a scenario you can rehearse here.

---

## Orchestration modes

A switch in the **UiPath Integration** panel flips how agent actions reach UiPath:

| Mode | Behavior |
|------|----------|
| **Direct** | Each agent fires its own Orchestrator process (`Incident_Escalation`, `Approval_Chain`, …). |
| **Maestro Case** | Agent actions are routed into a single **`MaestroCity_PipelineTest`** Maestro Case instance that orchestrates the agents + human approval. A burst of actions during one outage collapses into one Case instance. |

Default is set by `UIPATH_ORCHESTRATION_MODE` (`direct` | `maestro`) and can be changed at runtime.

---

## Human-in-the-loop approvals

When **VERITAS** (the compliance agent) sees a compliance-sensitive workflow during a crisis, it **holds it for human approval** instead of letting it run. Pending approvals surface in the **Human Approvals** modal (top bar) and the **UiPath** sidebar panel; both Approve/Reject buttons call the real `/api/approvals/{id}/approve|reject` endpoints. In **Maestro Case** mode the same gate is also delivered to **UiPath Action Center**.

**What gets gated:** any workflow typed `approval_request` (compliance-sensitive by definition), or any workflow whose risk exceeds `0.7`.

**How the queue stays manageable** (so you're not click-spammed):

- **Dedupe** — at most one pending approval per workflow.
- **Queue cap** — at most **5** pending VERITAS approvals at once; new ones wait until some are resolved.
- **Auto-expire** — approvals past their 5-minute SLA are dropped automatically.
- **Decided = done** — once you approve or reject a workflow, it is **never re-gated**.
- **Cooldown** — after *any* human decision, VERITAS pauses creating new approvals for `UIPATH_APPROVAL_COOLDOWN_SECONDS` (default **45s**), so clearing the queue actually sticks instead of instantly refilling. Once the cooldown elapses, an ongoing crisis may surface a few new approvals (ongoing crisis = ongoing oversight).

The Human Approvals modal contains **only genuine approval decisions** — critical alerts are deliberately **not** mixed into it (that previously created an un-clearable treadmill). The modal reports the unacknowledged-critical *count* so the UI can badge "N in Alert Feed →", but the full alert stream lives in the **Alert Feed**, not the approvals queue.

---

## Failure behavior — no silent fallbacks

Both orchestration modes are **fail-forward**: if UiPath is unconfigured, a release isn't published, auth fails, or a job faults, the UI shows a **Faulted job with the real reason** and the API returns a true `502/503` — it never fakes a successful run. Failed player actions (e.g. activating failover with no backup building in the scenario) surface as a warning **alert** rather than silently doing nothing. You can always tell whether automation actually ran.

---

## Exports — what they are and where they go

The **Coding Agent** (top bar), the **Debug Workflow** tab, and the **Reports** modal all produce downloadable artifacts. They split into two kinds: **things you import into UiPath Studio and publish to Orchestrator**, and **human-facing documents**.

| Export | What it is | Where it goes / how to use it |
|--------|------------|-------------------------------|
| **Reports → Process Templates → Download** | Per-process `Main.xaml` + `project.json` for the five response processes (`Incident_Escalation`, `Crisis_Response`, `Approval_Chain`, `Emergency_Staffing`, `Trust_Recovery_Protocol`). Hand-structured, demo-ready. | Put both files in a folder, open it as a project in **UiPath Studio** (or `uipath pack`), then **publish to Orchestrator**. These are the exact processes the agents trigger at runtime. |
| **Coding Agent → Download XAML** | A `workflow.xaml` generated *live* from the current crisis by the `coding_gen` robot (gpt-4.1-mini via the LLM Gateway). | Import into **UiPath Studio** and **publish to Orchestrator**, same as above. It's LLM-generated, so treat it as a starting point that may need cleanup before it runs. |
| **Debug Workflow → suggested fix / XAML patch** | A root-cause diagnosis plus a corrected **XAML fragment** for a faulted workflow. | **Not** a full import — paste the patch into your *existing* workflow in Studio and apply the listed remediation steps. |
| **Reports → After-Action Report → Download JSON** | Incident retrospective: timeline, metrics, and what each agent did. | A **deliverable** — file or share it (incident review, post-mortem). Not a UiPath import. |
| **Reports → Runbook → Download .md / .json** | An operational runbook for responders, generated from the run. | **Documentation** for the ops / SOC team. Not a UiPath import. |
| **Reports → Calibration Score** | An autonomy-calibration certificate — evidence the agents acted at appropriate trust/autonomy levels. | **Governance / compliance artifact.** Not a UiPath import. |

> **Note:** these buttons are browser downloads — the import-and-publish step into UiPath Studio / Orchestrator is **manual**. (Separately, the running agents *do* start jobs on already-published processes via the Orchestrator API — that's the live integration; these exports are the "author new automation" side.)

---

## Architecture

```
apps/frontend   Next.js 14 (App Router) + PixiJS city renderer + Zustand   → Vercel
apps/backend    FastAPI + WebSocket + Pydantic, real-time tick loop        → Railway / Render
packages/shared-types   TypeScript types shared via the @shared/* path alias
_uipath_build   Coded-agent source + publishing scripts (uipath CLI / uipcli)
```

The backend is **stateful** (in-memory simulation + a WebSocket broadcast loop), so it must run on a long-lived host — **not** a serverless function.

---

## UiPath components used

- **External Application** (OAuth2 client-credentials) for API auth against the tenant.
- **Orchestrator** — folders, packages, releases, `StartJobs` (OData), job polling.
- **Serverless Automation Cloud Robots** — run all jobs (`Strategy: ModernJobsCount`, `RuntimeType: Serverless`).
- **Coded agents** (`uipath-langchain`, LangGraph + `UiPathAzureChatOpenAI`) — the 5 operational agents, the Coding Agent (`coding_gen`), and the scenario generator (`scenario_gen`), all reasoning via the **LLM Gateway**.
- **Orchestrator processes** — the 5 response workflows (`Incident_Escalation`, `Crisis_Response`, `Approval_Chain`, `Emergency_Staffing`, `Trust_Recovery_Protocol`).
- **Maestro Case** (`MaestroCity_PipelineTest`) — rule-driven case with agent tasks + a human-in-the-loop approval delivered to **Action Center**.

See [docs/UIPATH_PLATFORM_SETUP.md](docs/UIPATH_PLATFORM_SETUP.md) and [docs/AGENT_BUILDER_SPEC.md](docs/AGENT_BUILDER_SPEC.md) for the full setup.

---

## Local setup

**Prerequisites:** Node 18+, Python 3.11+, and (for real automation) a UiPath Automation Cloud tenant with an External Application.

```bash
# 1. Install everything
npm run install:all          # installs frontend + pip deps

# 2. Configure backend secrets
cp apps/backend/.env.example apps/backend/.env
#    fill in your UiPath values (see env table below)

# 3. (optional) point the frontend at the backend
cp apps/frontend/.env.example apps/frontend/.env.local
#    NEXT_PUBLIC_BACKEND_URL defaults to http://localhost:8000

# 4. Run both (concurrently)
npm run dev
```

Frontend: <http://localhost:3000> · Backend: <http://localhost:8000>

Run individually with `npm run dev:backend` / `npm run dev:frontend`.

---

## Environment variables

### Backend (`apps/backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `UIPATH_CLOUD_URL` | yes | Tenant base URL, e.g. `https://cloud.uipath.com` |
| `UIPATH_ORGANIZATION` | yes | Organization (account-logical) name |
| `UIPATH_TENANT` | yes | Tenant name, e.g. `DefaultTenant` |
| `UIPATH_CLIENT_ID` | yes | External Application client ID |
| `UIPATH_CLIENT_SECRET` | yes | External Application client secret (**single-quote in `.env`** if it contains special chars) |
| `UIPATH_FOLDER_ID` | yes | Orchestrator folder (organization-unit) ID |
| `UIPATH_WEBHOOK_SECRET` | no | HMAC-SHA256 secret used to verify inbound Orchestrator webhooks. Only needed if you wire up webhooks (set it when creating the webhook in Orchestrator). |
| `UIPATH_ORCHESTRATION_MODE` | no | `direct` (default) or `maestro` |
| `UIPATH_MAESTRO_CASE_PROCESS` | no | Maestro Case release name (default `MaestroCity_PipelineTest`) |
| `UIPATH_MAESTRO_COOLDOWN_SECONDS` | no | Dedupe window for Maestro Case starts (default `25`) |
| `UIPATH_APPROVAL_COOLDOWN_SECONDS` | no | After a human approve/reject, seconds VERITAS waits before creating new approvals (default `45`) |

If credentials are absent, the app runs but UiPath calls report as unavailable in the UI (no faked success).

### Frontend (`apps/frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_BACKEND_URL` | Backend base URL (e.g. `https://your-backend.up.railway.app`) |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL (defaults to the backend URL with `ws(s)://…/ws`) |

---

## Deploy

### Backend → Railway or Render

**Railway:** New Project → Deploy from repo → set **Root Directory** to `apps/backend` (picks up [`apps/backend/railway.json`](apps/backend/railway.json) / [`Procfile`](apps/backend/Procfile)). Add the UiPath env vars under Variables. Railway injects `$PORT`.

**Render:** New → Blueprint, pointed at [`render.yaml`](render.yaml). Fill the `sync: false` UiPath vars in the dashboard.

Either way the start command is:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Frontend → Vercel

New Project → set **Root Directory** to `apps/frontend` (the `@shared/*` alias resolves against the cloned repo). Add:

- `NEXT_PUBLIC_BACKEND_URL` = your deployed backend URL
- `NEXT_PUBLIC_WS_URL` = `wss://<backend-host>/ws`

[`apps/frontend/vercel.json`](apps/frontend/vercel.json) sets the framework preset.

---

## Security

- **Secrets live only in `.env` / the host dashboard** — every `.env` is gitignored; only `.env.example` placeholders are committed.
- Rotate the UiPath client secret before sharing the repo publicly.
- Never commit `apps/backend/.env` or any `_uipath_build/**/.env` (all ignored by the bare `.env` rule).

---

## Project structure

```
apps/
  backend/          FastAPI app, simulation engine, agents, UiPath client
    agents/         APEX / SENTINEL / VERITAS / ECHO / ARIA decision logic
    orchestration/  uipath_client.py, agent_invoker.py, template generator
    scenarios/      slot-factory scenario specs + registry
    api/            REST routes, WebSocket, coding agent, scenario generator
  frontend/         Next.js + PixiJS UI
packages/
  shared-types/     shared TS types
docs/               UiPath setup, agent specs, coding-agent guide
```
