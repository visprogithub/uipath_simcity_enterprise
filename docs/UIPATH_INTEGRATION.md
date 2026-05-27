# UiPath Integration — Technical Reference

This document is the authoritative technical reference for the Maestro City ↔ UiPath
Orchestrator integration. It covers authentication, every API call the backend makes,
the webhook contract, environment variables, and how simulation events map to UiPath
processes.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Maestro City Platform                              │
│                                                                             │
│  ┌──────────────────┐       WebSocket        ┌──────────────────────────┐  │
│  │  Next.js Frontend│◄─────────────────────► │  FastAPI Backend         │  │
│  │  (port 3000)     │   SimulationState JSON  │  (port 8000)             │  │
│  │                  │                         │                          │  │
│  │  • City grid     │                         │  • Simulation engine     │  │
│  │  • UiPath panel  │                         │  • UiPath client         │  │
│  │  • Agent HUD     │                         │  • Webhook endpoint      │  │
│  └──────────────────┘                         └──────────┬───────────────┘  │
└─────────────────────────────────────────────────────────│────────────────┘
                                                           │ HTTPS REST (OAuth 2.0)
                                                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      UiPath Cloud Platform                                  │
│                                                                             │
│  ┌────────────────────┐        ┌────────────────────────────────────────┐  │
│  │  Identity Server   │        │  Orchestrator                          │  │
│  │  /identity_/connect│        │  /{org}/{tenant}/orchestrator_/        │  │
│  │  /token            │        │                                        │  │
│  │                    │        │  ┌──────────────┐  ┌────────────────┐  │  │
│  │  Issues Bearer     │        │  │  MaestroCity │  │  Action Items  │  │  │
│  │  tokens (3600 s)   │        │  │  Folder      │  │  (Maestro)     │  │  │
│  └────────────────────┘        │  │              │  └────────────────┘  │  │
│                                │  │  Processes:  │                      │  │
│                                │  │  • Incident_ │  ┌────────────────┐  │  │
│                                │  │    Escalation│  │  Webhooks      │  │  │
│                                │  │  • Approval_ │  │  POST → :8000/ │  │  │
│                                │  │    Chain     │  │  api/uipath/   │  │  │
│                                │  │  • Crisis_   │  │  webhook       │  │  │
│                                │  │    Response  │  └────────────────┘  │  │
│                                │  │  • Emergency_│                      │  │
│                                │  │    Staffing  │  ┌────────────────┐  │  │
│                                │  │  • Trust_    │  │  Robots /      │  │  │
│                                │  │    Recovery_ │  │  Serverless    │  │  │
│                                │  │    Protocol  │  └────────────────┘  │  │
│                                │  └──────────────┘                      │  │
│                                └────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### WebSocket Real-Time Flow

```
Frontend                   Backend                     UiPath
   │                          │                           │
   │── WsActionMessage ──────►│                           │
   │   { type: "trigger_     │                           │
   │     uipath", process,   │── POST /Jobs/StartJobs ──►│
   │     inputArgs }         │                           │
   │                          │◄── { Id: 12345 } ────────│
   │◄── WsAckMessage ─────────│                           │
   │◄── WsStateMessage ───────│  (job added to state)    │
   │   uipathStatus.          │                           │
   │   activeJobs = [...]     │          (job runs on robot)
   │                          │                           │
   │                          │◄── POST /webhook ─────────│
   │                          │   { Type: "job.completed",│
   │                          │     Job: { State: "Succ."}│
   │                          │     OutputArguments: ...} │
   │◄── WsStateMessage ───────│                           │
   │   (job removed from      │                           │
   │    activeJobs, effects   │                           │
   │    applied to simulation)│                           │
```

---

## Authentication Flow

Maestro City uses **OAuth 2.0 Client Credentials** (no user redirect required). Tokens
are cached and refreshed before expiry.

### Token Request

```
POST https://cloud.uipath.com/identity_/connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id={UIPATH_CLIENT_ID}
&client_secret={UIPATH_CLIENT_SECRET}
&scope=OR.Jobs OR.Jobs.Write OR.Execution OR.Folders OR.Folders.Read OR.Actions OR.Actions.Write OR.Tasks OR.TaskForms OR.Background
```

### Token Response

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "token_type": "Bearer",
  "scope": "OR.Jobs OR.Jobs.Write OR.Execution ..."
}
```

### Python Implementation (Backend)

```python
import asyncio
import time
import httpx

class UiPathTokenCache:
    """Thread-safe, async token cache with proactive refresh."""

    _token: str = ""
    _expires_at: float = 0.0
    _lock = asyncio.Lock()

    @classmethod
    async def get_token(
        cls,
        client_id: str,
        client_secret: str,
        token_url: str = "https://cloud.uipath.com/identity_/connect/token",
    ) -> str:
        async with cls._lock:
            # Refresh 60 seconds before actual expiry
            if time.time() < cls._expires_at - 60:
                return cls._token

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "scope": (
                            "OR.Jobs OR.Jobs.Write OR.Execution "
                            "OR.Folders OR.Folders.Read OR.Actions "
                            "OR.Actions.Write OR.Tasks OR.TaskForms OR.Background"
                        ),
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            cls._token = data["access_token"]
            cls._expires_at = time.time() + data["expires_in"]
            return cls._token
```

All subsequent API calls include:
```
Authorization: Bearer {access_token}
X-UIPATH-OrganizationUnitId: {UIPATH_FOLDER_ID}
```

---

## API Reference

All URLs follow the pattern:
```
https://cloud.uipath.com/{UIPATH_ORGANIZATION}/{UIPATH_TENANT}/orchestrator_/...
```

### 1. Look Up Release Key for a Process

Before starting a job you need the `ReleaseKey` (a UUID) for the process in your folder.
Cache this — it does not change between runs unless you unpublish and republish.

```
GET /odata/Releases?$filter=ProcessKey eq 'Incident_Escalation'
Headers:
  Authorization: Bearer {token}
  X-UIPATH-OrganizationUnitId: {folder_id}
```

**Response:**
```json
{
  "@odata.context": "...",
  "value": [
    {
      "Id": 88,
      "Key": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "ProcessKey": "Incident_Escalation",
      "ProcessVersion": "1.0.0",
      "IsLatestVersion": true,
      "IsProcessDeleted": false,
      "Description": "",
      "Name": "Incident_Escalation",
      "EnvironmentId": null,
      "FolderId": 12345
    }
  ]
}
```

Extract `value[0].Key` — this is the `ReleaseKey` used to start jobs.

**Python helper:**
```python
async def get_release_key(
    http: httpx.AsyncClient,
    base_url: str,
    process_key: str,
    token: str,
    folder_id: str,
) -> str:
    resp = await http.get(
        f"{base_url}/odata/Releases",
        params={"$filter": f"ProcessKey eq '{process_key}'"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-UIPATH-OrganizationUnitId": folder_id,
        },
    )
    resp.raise_for_status()
    values = resp.json().get("value", [])
    if not values:
        raise ValueError(f"Process '{process_key}' not found in folder {folder_id}")
    return values[0]["Key"]
```

---

### 2. Start a Job

```
POST /odata/Jobs/UiPath.Server.Configuration.OData.StartJobs
Headers:
  Authorization: Bearer {token}
  X-UIPATH-OrganizationUnitId: {folder_id}
  Content-Type: application/json
```

**Request body:**
```json
{
  "startInfo": {
    "ReleaseKey": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "Strategy": "Unattended",
    "RobotIds": [],
    "NoOfRobots": 0,
    "Source": "Manual",
    "InputArguments": "{\"incident_type\": \"cloud_outage\", \"building_id\": \"cloud_datacenter\", \"severity\": \"full\", \"tick_number\": 42}"
  }
}
```

> **Important:** `InputArguments` is a **JSON-encoded string**, not a nested object.
> The inner JSON must be serialised to a string before being included in the outer body.

**Response:**
```json
{
  "@odata.context": "...",
  "value": [
    {
      "Id": 12345,
      "Key": "job-uuid-here",
      "State": "Pending",
      "JobPriority": "Normal",
      "Source": "Manual",
      "BatchExecutionKey": "batch-uuid",
      "Info": "",
      "CreationTime": "2024-01-15T10:30:00Z",
      "StartTime": null,
      "EndTime": null,
      "Robot": null,
      "Release": { "ProcessKey": "Incident_Escalation" },
      "OutputArguments": null
    }
  ]
}
```

Extract `value[0].Id` as the job ID for polling and webhook correlation.

**Python helper:**
```python
import json

async def start_job(
    http: httpx.AsyncClient,
    base_url: str,
    release_key: str,
    input_args: dict,
    token: str,
    folder_id: str,
) -> int:
    """Returns the job Id (integer)."""
    resp = await http.post(
        f"{base_url}/odata/Jobs/UiPath.Server.Configuration.OData.StartJobs",
        json={
            "startInfo": {
                "ReleaseKey": release_key,
                "Strategy": "Unattended",
                "RobotIds": [],
                "NoOfRobots": 0,
                "Source": "Manual",
                "InputArguments": json.dumps(input_args),
            }
        },
        headers={
            "Authorization": f"Bearer {token}",
            "X-UIPATH-OrganizationUnitId": folder_id,
            "Content-Type": "application/json",
        },
    )
    resp.raise_for_status()
    jobs = resp.json().get("value", [])
    if not jobs:
        raise RuntimeError("StartJobs returned empty value list")
    return jobs[0]["Id"]
```

---

### 3. Poll Job Status

Use this when webhooks are unavailable or as a fallback for long-running jobs.

```
GET /odata/Jobs({job_id})
Headers:
  Authorization: Bearer {token}
  X-UIPATH-OrganizationUnitId: {folder_id}
```

**Response:**
```json
{
  "Id": 12345,
  "State": "Successful",
  "Info": "Job completed successfully",
  "StartTime": "2024-01-15T10:30:05Z",
  "EndTime": "2024-01-15T10:30:18Z",
  "OutputArguments": "{\"escalation_id\": \"abc-def-123\", \"action_taken\": \"Escalated to Level 2\", \"recovery_recommendation\": \"Activate backup_infra failover.\"}"
}
```

Job states: `Pending` → `Running` → `Successful` | `Faulted` | `Stopped`

**OutputArguments** is a JSON-encoded string, same as InputArguments. Parse it:
```python
output = json.loads(job["OutputArguments"] or "{}")
escalation_id = output.get("escalation_id")
```

**Polling loop (with exponential back-off):**
```python
import asyncio

async def wait_for_job(
    http: httpx.AsyncClient,
    base_url: str,
    job_id: int,
    token: str,
    folder_id: str,
    timeout_seconds: int = 120,
) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    delay = 2.0

    while asyncio.get_event_loop().time() < deadline:
        resp = await http.get(
            f"{base_url}/odata/Jobs({job_id})",
            headers={
                "Authorization": f"Bearer {token}",
                "X-UIPATH-OrganizationUnitId": folder_id,
            },
        )
        resp.raise_for_status()
        job = resp.json()

        if job["State"] in ("Successful", "Faulted", "Stopped"):
            return job

        await asyncio.sleep(delay)
        delay = min(delay * 1.5, 15.0)  # cap at 15 s

    raise TimeoutError(f"Job {job_id} did not complete within {timeout_seconds}s")
```

---

### 4. Create a Maestro Action Item

Action items surface in the Maestro UI for human review. Triggered by high-risk or
manual-approval scenarios.

```
POST /api/ActionItems
Headers:
  Authorization: Bearer {token}
  X-UIPATH-OrganizationUnitId: {folder_id}
  Content-Type: application/json
```

**Request body:**
```json
{
  "Title": "Critical Incident: CloudCore Data Center",
  "Type": "FormTask",
  "Priority": "High",
  "CatalogName": "MaestroCity",
  "AssignedToUser": null,
  "DueDate": null,
  "Data": "{\"workflow_id\": \"wf-012\", \"risk_score\": 0.92, \"building_id\": \"cloud_datacenter\"}"
}
```

Valid `Priority` values: `"Low"`, `"Medium"`, `"High"`, `"Critical"`

**Response:**
```json
{
  "Id": 9876,
  "Title": "Critical Incident: CloudCore Data Center",
  "Status": "Unassigned",
  "Priority": "High",
  "CreationTime": "2024-01-15T10:30:00Z"
}
```

---

### 5. List Active Action Items

```
GET /api/ActionItems?$filter=Status ne 'Completed'&$orderby=CreationTime desc&$top=20
Headers:
  Authorization: Bearer {token}
  X-UIPATH-OrganizationUnitId: {folder_id}
```

---

### 6. Per-Process Input/Output Reference

#### `Incident_Escalation`

```python
input_args = {
    "incident_type": "cloud_outage",   # str: "cloud_outage"|"cascade_failure"|...
    "building_id": "cloud_datacenter",  # str: building id from city config
    "severity": "full",                 # str: "partial"|"full"
    "tick_number": 42,                  # int: current simulation tick
}

# OutputArguments (after job completes):
{
    "escalation_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "action_taken": "Escalated to Level 3",
    "recovery_recommendation": "Activate backup_infra failover. Redirect workflows via comms_hub."
}
```

#### `Approval_Chain`

```python
input_args = {
    "workflow_id": "wf-012",             # str: workflow id
    "workflow_type": "approval_request", # str: workflow type
    "risk_score": 0.87,                  # float: 0.0–1.0
    "requesting_agent": "ARIA",          # str: agent name
}

# OutputArguments:
{
    "approved": True,                          # bool
    "approver": "Human Reviewer",              # str
    "reason": "Manual approval granted for high-risk workflow.",
    "audit_trail_id": "e3b0c44298fc1c149afb"   # str: unique audit ID
}
```

#### `Crisis_Response`

```python
input_args = {
    "crisis_type": "cascade",                     # str: crisis category
    "affected_buildings": '["hospital","pharmacy"]',  # JSON-encoded str
    "operational_stability": 35.5,                 # float: 0–100
    "human_strain": 78.2,                          # float: 0–100
}

# OutputArguments:
{
    "recovery_plan": '{"type":"cascade","steps":[...],"priority_order":["hospital","pharmacy"]}',
    "estimated_recovery_ticks": 15,               # int
    "emergency_resources_needed": '["backup_infra","comms_hub"]'  # JSON-encoded str
}
```

#### `Emergency_Staffing`

```python
input_args = {
    "building_id": "hospital",  # str: building needing staff
    "current_strain": 82.0,     # float: 0–100
    "deficit": 3.0,             # float: staff units needed
}

# OutputArguments:
{
    "staff_assigned": 2,              # int: how many staff were deployed
    "new_staffing_level": 68.5,       # float: projected new staffing %
    "estimated_relief_in_ticks": 3    # int: ticks until strain reduces
}
```

#### `Trust_Recovery_Protocol`

```python
input_args = {
    "current_trust": 38.0,                         # float: 0–100
    "trust_drop_cause": "failed_escalation",        # str: reason for drop
    "affected_agent_ids": '["ops_coord","incident_resp"]',  # JSON-encoded str
}

# OutputArguments:
{
    "recommended_autonomy_levels": '{"ops_coord":1,"incident_resp":1,"compliance":0,"comms":1,"exec_strategy":1}',
    "recovery_checklist": '["Reduce autonomy for affected agents","Run audit trail review",...]',
    "estimated_trust_recovery_ticks": 30   # int
}
```

---

## Webhook Integration

### Receiving Webhooks

The backend exposes `POST /api/uipath/webhook`. UiPath Cloud POSTs to this endpoint
whenever a subscribed event occurs.

### Webhook Payload Format

**job.completed:**
```json
{
  "Type": "job.completed",
  "EventId": "550e8400-e29b-41d4-a716-446655440000",
  "Timestamp": "2024-01-15T10:30:18.000Z",
  "TenantId": 1001,
  "UserId": 5,
  "Job": {
    "Id": 12345,
    "Key": "job-key-uuid",
    "State": "Successful",
    "Info": "Job completed successfully",
    "StartTime": "2024-01-15T10:30:05Z",
    "EndTime": "2024-01-15T10:30:18Z",
    "OutputArguments": "{\"escalation_id\": \"abc-123\", \"action_taken\": \"Escalated to Level 2\"}",
    "Robot": { "Name": "MaestroCity_Robot", "Id": 7 },
    "Release": { "ProcessKey": "Incident_Escalation", "Key": "release-key-uuid" }
  }
}
```

**job.faulted:**
```json
{
  "Type": "job.faulted",
  "EventId": "...",
  "Timestamp": "...",
  "Job": {
    "Id": 12346,
    "State": "Faulted",
    "Info": "System.Exception: Could not connect to mail server.",
    "OutputArguments": null
  }
}
```

**action_item.created / action_item.completed:**
```json
{
  "Type": "action_item.completed",
  "EventId": "...",
  "Timestamp": "...",
  "ActionItem": {
    "Id": 9876,
    "Title": "Critical Incident: CloudCore Data Center",
    "Status": "Completed",
    "Priority": "High",
    "Data": "{\"workflow_id\": \"wf-012\", \"risk_score\": 0.92}"
  }
}
```

### HMAC-SHA256 Signature Verification

UiPath signs every webhook request. Verify the signature before processing to prevent
spoofed payloads.

The signature is in the request header: `X-UiPath-Signature`

```python
import hmac
import hashlib

def verify_uipath_signature(
    raw_body: bytes,
    signature_header: str,
    webhook_secret: str,
) -> bool:
    """
    Returns True if the request is genuinely from UiPath.
    
    Args:
        raw_body: The raw bytes of the POST body (before JSON parsing).
        signature_header: Value of the X-UiPath-Signature header.
        webhook_secret: The UIPATH_WEBHOOK_SECRET from your .env file.
    """
    expected_sig = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    expected_header = f"sha256={expected_sig}"
    # Use compare_digest to prevent timing attacks
    return hmac.compare_digest(expected_header, signature_header)
```

**FastAPI endpoint implementation:**
```python
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional

router = APIRouter()

@router.post("/api/uipath/webhook")
async def uipath_webhook(
    request: Request,
    x_uipath_signature: Optional[str] = Header(None),
):
    raw_body = await request.body()
    secret = os.getenv("UIPATH_WEBHOOK_SECRET", "")

    if secret and x_uipath_signature:
        if not verify_uipath_signature(raw_body, x_uipath_signature, secret):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    event_type = payload.get("Type")

    if event_type == "job.completed":
        await handle_job_completed(payload)
    elif event_type == "job.faulted":
        await handle_job_faulted(payload)
    elif event_type in ("action_item.created", "action_item.completed"):
        await handle_action_item(payload)

    return {"status": "ok"}


async def handle_job_completed(payload: dict) -> None:
    job = payload["Job"]
    job_id = str(job["Id"])
    output_raw = job.get("OutputArguments") or "{}"
    outputs = json.loads(output_raw)
    process_key = job.get("Release", {}).get("ProcessKey", "")

    # Apply simulation effects based on which process completed
    await apply_job_outputs_to_simulation(process_key, outputs)
    # Broadcast updated state to all WebSocket clients
    await broadcast_state_update()
```

---

## Simulation Event to UiPath Process Mapping

| Simulation Event            | Trigger Condition                                              | UiPath Process            | Key Input Args                                                              | Effect on Simulation After Job Completes                                                         |
|-----------------------------|----------------------------------------------------------------|---------------------------|-----------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| `outage_started`            | `cloud_datacenter.health < 60`                                 | `Incident_Escalation`     | `incident_type="cloud_outage"`, `building_id`, `severity`, `tick_number`    | Simulation event `uipath_job_completed` logged; `recovery_recommendation` shown in alert panel   |
| `outage_started`            | Any building with `health < 40` AND `health > 0`              | `Incident_Escalation`     | `incident_type="cascade_failure"`, `building_id`, `severity="partial"`, `tick_number` | Escalation logged; affected building gets `recoveryCapacity` boost from output             |
| `approval_required`         | `workflow.risk > 0.7` AND `workflow.type = "approval_request"` | `Approval_Chain`           | `workflow_id`, `workflow_type`, `risk_score`, `requesting_agent`            | If `approved=True`: workflow status → `flowing`; if `False`: workflow status → `failed`         |
| `cascade_propagated`        | Two or more buildings degraded in same tick                    | `Crisis_Response`          | `crisis_type="cascade"`, `affected_buildings` (JSON), `operational_stability`, `human_strain` | `recovery_plan` logged; `estimated_recovery_ticks` drives recovery timeline UI counter   |
| `staffing_overload`         | `building.staffingLevel < 30` OR `metrics.humanStrain > 80`   | `Emergency_Staffing`       | `building_id`, `current_strain`, `deficit`                                  | `building.staffingLevel` increased by `staff_assigned * 5`; `humanStrain` metric reduced        |
| `trust_drop`                | `metrics.systemTrust` drops more than 10 points in one tick   | `Trust_Recovery_Protocol`  | `current_trust`, `trust_drop_cause`, `affected_agent_ids` (JSON)            | Agent `autonomyLevel` values updated from `recommended_autonomy_levels`; checklist shown in HUD  |

### Deduplication Key

To avoid triggering duplicate jobs for the same event within a short window:

```python
def dedup_key(process_name: str, building_id: str, tick: int) -> str:
    """
    Returns a key that is the same for all ticks within a 10-tick window.
    Use a set of recently-triggered keys to skip duplicate triggers.
    """
    window = tick // 10
    return f"{process_name}:{building_id}:{window}"
```

Do not trigger the same `(process_name, building_id)` combination more than once per
10-tick window. The backend stores triggered keys in an in-memory set that is cleared
every 100 ticks.

---

## Environment Variables Reference

All variables live in `apps/backend/.env`. Copy `apps/backend/.env.example` as a
starting point.

| Variable                   | Required | Default                          | Description                                                                                   | Where to Find                                          |
|----------------------------|----------|----------------------------------|-----------------------------------------------------------------------------------------------|--------------------------------------------------------|
| `UIPATH_CLOUD_URL`         | No       | `https://cloud.uipath.com`       | Base URL for all UiPath Cloud API calls. Only change if using an on-prem Orchestrator.       | Hardcoded — do not change for cloud deployments        |
| `UIPATH_ORGANIZATION`      | Yes      | —                                | Your UiPath organisation name (appears in browser URL after cloud.uipath.com/)               | cloud.uipath.com/{**OrgName**}/portal_                 |
| `UIPATH_TENANT`            | Yes      | —                                | Tenant name within your organisation.                                                         | Admin > Tenants > Name column                          |
| `UIPATH_CLIENT_ID`         | Yes      | —                                | OAuth 2.0 client ID for the MaestroCity Integration application.                              | Admin > External Applications > MaestroCity Integration |
| `UIPATH_CLIENT_SECRET`     | Yes      | —                                | OAuth 2.0 client secret. Rotate immediately if compromised.                                   | Generated during External Application creation         |
| `UIPATH_FOLDER_ID`         | Yes      | —                                | Integer ID of the MaestroCity folder in Orchestrator.                                         | From URL or GET /odata/Folders API                     |
| `UIPATH_WEBHOOK_SECRET`    | No       | `""` (verification disabled)     | HMAC secret for validating incoming webhook requests from UiPath.                             | Set in Orchestrator > Integrations > Webhooks          |
| `OPENAI_API_KEY`           | No       | —                                | If set, enables LLM-generated incident narrative text in the frontend.                        | platform.openai.com/api-keys                           |
| `SIMULATION_TICK_INTERVAL` | No       | `1.0`                            | Seconds between simulation ticks. Lower = faster simulation. Minimum `0.1`.                  | Application setting — no external service              |

### Checking Connection Status at Runtime

The backend exposes a health endpoint that reports UiPath connectivity:

```
GET http://localhost:8000/api/health
```

```json
{
  "status": "ok",
  "uipath": {
    "connected": true,
    "organization": "acmecorp",
    "tenant": "DefaultTenant",
    "folder_id": "12345",
    "last_token_refresh": "2024-01-15T10:29:45Z"
  }
}
```

If `connected` is `false`, check that all five required env vars are set and that the
client credentials are valid.

---

## Error Handling and Offline Mode

### When UiPath Is Not Configured

If any of the four required env vars (`UIPATH_ORGANIZATION`, `UIPATH_TENANT`,
`UIPATH_CLIENT_ID`, `UIPATH_CLIENT_SECRET`) are missing or empty:

- The UiPath client initialises in **offline mode**.
- `uipathStatus.connected = false` in every `SimulationState` broadcast.
- No jobs are triggered — all `trigger_uipath` player actions are silently ignored.
- The simulation runs fully, including outages, agent logic, and cascades.
- The frontend UiPath panel shows "Not Connected — offline mode".

This design means the app can be demoed end-to-end without UiPath credentials.

### Error Recovery Strategy

| Error Type                  | Backend Behaviour                                                          |
|-----------------------------|----------------------------------------------------------------------------|
| `401 Unauthorized`          | Discard cached token, retry once with fresh token. If still 401, log error and mark job as `Faulted`. |
| `404 Release not found`     | Log warning: "Process not published to MaestroCity folder". Skip trigger.  |
| `429 Rate Limited`          | Respect `Retry-After` header. Queue job trigger for retry after delay.      |
| `500 Server Error`          | Retry up to 3 times with exponential back-off (2 s, 4 s, 8 s).            |
| Webhook signature mismatch  | Return `401` to UiPath. Log warning. Do not process payload.               |
| Job `Faulted`               | Log `job.faulted` event in simulation event log. Apply no output effects.  |
| Token fetch failure         | Mark client as disconnected. Retry token fetch on next trigger attempt.    |

### Logging

The backend logs all UiPath operations at the `INFO` level:
```
[uipath] Fetching token...
[uipath] Token acquired, expires in 3600s
[uipath] Starting job: Incident_Escalation (release_key=f47ac10b...)
[uipath] Job 12345 started — State: Pending
[webhook] Received job.completed for job_id=12345
[uipath] Applying outputs for Incident_Escalation: escalation_id=abc-123
```

Errors are logged at `ERROR` level and surfaced as `critical` alerts in the simulation.

---

## Rate Limits and Best Practices

### UiPath API Rate Limits

UiPath Cloud enforces rate limits at the tenant level. As of 2024:

- **General API**: ~100 requests per minute per tenant.
- **StartJobs**: no specific sub-limit, but counts toward the general limit.
- **Webhook delivery**: UiPath retries failed deliveries up to 5 times with exponential
  back-off. Your endpoint must respond within 10 seconds with a 2xx status.

### Best Practices for Maestro City

1. **Cache release keys.** Look up `ReleaseKey` once at startup and store in memory.
   Do not re-fetch on every job trigger. Keys only change if you unpublish a process.

2. **Use webhooks, not polling.** Webhooks give sub-second job completion notification.
   Only poll as a fallback for jobs that have been running longer than expected
   (e.g., > 60 seconds).

3. **Deduplicate triggers.** Use the 10-tick window deduplication key described above.
   A cascade event can fire multiple times per second — without deduplication you will
   exhaust rate limits instantly.

4. **Respect the simulation tick rate.** At `SIMULATION_TICK_INTERVAL=1.0` (1 tick/sec),
   the maximum possible job triggers is 1 per event type per 10 ticks = 6 events × 0.1
   triggers/sec = well within rate limits. If you lower tick interval below `0.25`,
   increase the deduplication window to 20 ticks.

5. **Never block the simulation loop on UiPath calls.** All API calls are `async` and
   use `asyncio`. If UiPath is slow or unavailable, the simulation continues unaffected.

6. **Validate webhook payloads.** Always verify the HMAC signature. Log and reject
   any payload that fails verification.

7. **Rotate secrets periodically.** The `UIPATH_CLIENT_SECRET` and
   `UIPATH_WEBHOOK_SECRET` should be rotated before any public demo to prevent
   credential exposure in git history.
