# UiPath Platform Setup Guide for Maestro City

This guide walks you through configuring UiPath from scratch so that the Maestro City
simulation can trigger real automation jobs, receive webhook callbacks, and surface
Maestro action items in the UI. Follow every step in order. The guide assumes you have
a UiPath Cloud account but have never created an Orchestrator project before.

---

## 1. Account and Tenant Setup

### 1.1 Sign In

1. Open a browser and go to **https://cloud.uipath.com**.
2. Click **Sign In** in the top-right corner.
3. Enter your email and password (or use SSO if your organisation requires it).
4. After signing in you land on the **Home** page of the UiPath Cloud Platform.

### 1.2 Locate Your Organization Name

Your organisation name appears in every API URL. You need it later.

1. Look at the browser address bar. The URL format is:
   `https://cloud.uipath.com/{OrgName}/portal_`
2. The segment between `cloud.uipath.com/` and `/portal_` is your **OrgName**.
   Example: if the URL is `https://cloud.uipath.com/acmecorp/portal_` then
   `OrgName = acmecorp`.
3. Write this value down. You will place it in the `.env` file as `UIPATH_ORGANIZATION`.

### 1.3 Locate Your Tenant Name

A UiPath organisation can contain multiple tenants. The default tenant is usually called
`DefaultTenant` or a short version of your company name.

1. In the left sidebar, click **Admin** (the shield icon near the bottom).
2. In the Admin panel, click **Tenants** in the left column.
3. You will see a list of tenants. Find the one you want to use (typically the only
   one listed). Note the **Name** column value — this is your `TenantName`.
4. Write this down. You will place it in `.env` as `UIPATH_TENANT`.

### 1.4 Confirm the Orchestrator URL Pattern

All Orchestrator API calls use:
```
https://cloud.uipath.com/{OrgName}/{TenantName}/orchestrator_/
```
Make sure you can construct this URL before proceeding.

---

## 2. Create an External Application (OAuth 2.0 Client Credentials)

Maestro City authenticates against UiPath using OAuth 2.0 client credentials. You must
register an external application to get a **Client ID** and **Client Secret**.

### 2.1 Open External Applications

1. From the top-left UiPath logo, make sure you are in the correct **organisation**
   (check the org switcher drop-down if it is visible).
2. Click **Admin** in the left sidebar (shield icon).
3. In the Admin left panel, click **External Applications**.
   - If you do not see this option, make sure you have the **Organization Administrator**
     role. Contact whoever manages your UiPath account.

### 2.2 Add a New Application

1. Click the **+ Add Application** button (top right of the External Applications page).
2. Fill in the form:
   - **Application name**: `MaestroCity Integration`
   - **Application type**: Select **Confidential application**
     (this enables client secrets, which is required for server-to-server calls).
   - **Homepage URL**: `http://localhost:3000` (required but not used at runtime).
3. Under **Application Scopes**, click **Add Scopes**.
4. In the scope picker dialog, find and check each of the following scopes. You may need
   to scroll or search by name:

   | Scope name               | Purpose                                    |
   |--------------------------|--------------------------------------------|
   | `OR.Jobs`                | Read job information                       |
   | `OR.Jobs.Write`          | Start and stop jobs                        |
   | `OR.Execution`           | Execute robots                             |
   | `OR.Folders`             | Read folder structure                      |
   | `OR.Folders.Read`        | Additional folder read access              |
   | `OR.Actions`             | Read Maestro action items                  |
   | `OR.Actions.Write`       | Create and update action items             |
   | `OR.Tasks`               | Read task forms                            |
   | `OR.TaskForms`           | Manage task form submissions               |
   | `OR.Background`          | Background job execution                   |

5. Click **Save** in the scope picker.
6. Back on the Add Application form, click **Add** (or **Save**).

### 2.3 Copy Your Credentials

After saving, a dialog appears with your credentials. **This is the only time the secret
is shown in full.**

1. Copy the **Client ID** field. It looks like a UUID (e.g., `a1b2c3d4-...`).
2. Click **Generate Secret** (or the secret may already be displayed).
3. Copy the **Client Secret** value. It is a long random string.
4. Store both values immediately. They go into your `.env` file:
   ```
   UIPATH_CLIENT_ID=<paste Client ID here>
   UIPATH_CLIENT_SECRET=<paste Client Secret here>
   ```
5. Click **Close** on the dialog.

### 2.4 Token Endpoint

The OAuth token endpoint for UiPath Cloud is always:
```
https://cloud.uipath.com/identity_/connect/token
```
This value is already hardcoded in the Maestro City backend. You do not need to
configure it separately.

---

## 3. Create the "MaestroCity" Orchestrator Folder

All five automation processes must live inside a dedicated folder in Orchestrator.
A **Modern Folder** is required for Unattended robots and for Maestro action items.

### 3.1 Open Orchestrator

1. In the left sidebar of the UiPath Cloud Platform, click **Orchestrator**
   (the robot-head icon).
2. Orchestrator opens in the same browser tab. Make sure the correct tenant is shown
   in the top header drop-down (matches your `TenantName`).

### 3.2 Create the Folder

1. In the Orchestrator left sidebar, click **Folders** (folder icon).
   If you do not see it, look for a **Tenant** section at the top of the sidebar and
   expand it.
2. Click the **+ Add Folder** button (top right).
3. Fill in:
   - **Display Name**: `MaestroCity`
   - **Provisioning Type**: Select **Manual** (you will add the robot manually in step 4).
   - **Folder Type**: Make sure it shows **Modern** (not Classic). Modern is the default
     for new tenants.
4. Click **Create**.

### 3.3 Note the Folder ID

The folder ID is a number that must go into your `.env` file.

**Method A — from the URL:**
1. Click on the **MaestroCity** folder to open it.
2. Look at the browser address bar. The URL contains something like:
   `/folders/12345`. The number after `/folders/` is your folder ID.

**Method B — via the API (if the URL method is unclear):**
```
GET https://cloud.uipath.com/{OrgName}/{TenantName}/orchestrator_/odata/Folders
     ?$filter=DisplayName eq 'MaestroCity'
```
Run this from a REST client (Postman, curl) using a Bearer token. The response contains
`"Id": 12345`.

3. Add to `.env`:
   ```
   UIPATH_FOLDER_ID=12345
   ```

---

## 4. Create a Robot / Machine Template

For the hackathon you need at least one robot capable of running the five processes.
UiPath offers a **Serverless** (cloud) option and a **local machine** option.

### 4.1 Option A — Serverless Robot (Recommended for Hackathon)

If your UiPath licence includes **Automation Cloud Robots** (serverless), no local
machine setup is needed.

1. Inside the **MaestroCity** folder, click **Robots** in the left sidebar.
2. Click **+ Add Robot**.
3. Select **Automation Cloud Robot — Serverless**.
4. Give it a name: `MaestroCity_Robot`.
5. Click **Create**.
6. The robot is immediately available. No machine key is needed.

### 4.2 Option B — Local Machine (if serverless is unavailable)

1. On your local machine, download and install **UiPath Robot** from
   https://www.uipath.com/product/platform/download.
2. In Orchestrator, inside the **MaestroCity** folder:
   a. Click **Machines** in the left sidebar.
   b. Click **+ Add Machine**.
   c. Select **Standard Machine**.
   d. Name: `MaestroCity_Dev_Machine`.
   e. Click **Create**.
   f. Copy the **Machine Key** displayed on screen.
3. On your local machine, open **UiPath Robot** from the system tray.
4. Click the gear icon > **Orchestrator Settings**.
5. Enter:
   - **Machine URL**: `https://cloud.uipath.com`
   - **Machine Key**: paste the value from step f.
6. Click **Connect**. The robot status should change to **Available**.
7. Back in Orchestrator, click **Robots** and add an **Unattended Robot**:
   - **Name**: `MaestroCity_Unattended`
   - **Machine**: select `MaestroCity_Dev_Machine`
   - **Domain\Username**: enter the Windows username that will run the robot
     (e.g., `DESKTOP-ABC123\YourWindowsUser`).
   - **Password**: the Windows login password for that account.
   - Click **Create**.

---

## 5. Create the Five Required Processes in UiPath Studio

Each process below must be created as a UiPath Studio project, then published to the
**MaestroCity** folder in Orchestrator.

### 5.0 General Setup Steps (Do This for Every Process)

1. Open **UiPath Studio** (download from https://www.uipath.com/product/studio if not
   installed).
2. On first launch, sign in with the same UiPath Cloud account.
3. For each process:
   a. Click **File > New > Process** (or click **New Project** on the home screen and
      choose **Process**).
   b. Set:
      - **Name**: as specified below.
      - **Location**: a folder on your machine (e.g., `C:\UiPath\MaestroCity\`).
      - **Compatibility**: **Windows** (recommended) or **Cross-Platform**.
      - **Language**: VB.NET or C# (VB.NET is the default).
   c. Click **Create**.
4. Build the workflow as described in each section below.
5. To publish: click the **Publish** button in the Studio ribbon (top bar).
   - **Publish to**: select **Orchestrator Tenant Processes Feed** (or **Orchestrator
     Personal Workspace**, then move it to the folder — the former is simpler).
   - In the Publish dialog, under **Orchestrator Folder**, select **MaestroCity**.
   - Click **Publish**.
   - After publishing, verify the process appears in Orchestrator:
     Orchestrator > MaestroCity folder > **Processes**.

### 5.1 Process 1: `Incident_Escalation`

**Purpose:** Receives an incident from the simulation, escalates it via email and a
Maestro action item, and returns an escalation ID plus recommendations.

**Studio project name:** `Incident_Escalation`

**Step 1 — Define Input Arguments**

Open `Main.xaml`. In the **Arguments** panel (bottom of screen), add:

| Name           | Direction | Type   | Description                                    |
|----------------|-----------|--------|------------------------------------------------|
| `incident_type`| In        | String | e.g., `"cloud_outage"`, `"cascade_failure"`    |
| `building_id`  | In        | String | Which building is affected, e.g., `"hospital"` |
| `severity`     | In        | String | `"partial"` or `"full"`                        |
| `tick_number`  | In        | Int64  | Current simulation tick (integer)               |

**Step 2 — Define Output Arguments**

| Name                      | Direction | Type   |
|---------------------------|-----------|--------|
| `escalation_id`           | Out       | String |
| `action_taken`            | Out       | String |
| `recovery_recommendation` | Out       | String |

**Step 3 — Build the Sequence (Main.xaml)**

Add the following activities in order inside the **Main** sequence:

1. **Log Message** activity:
   - LogLevel: `Info`
   - Message: `"Incident received: " + incident_type + " at " + building_id`

2. **If** activity — condition: `severity = "full"`
   - **Then** branch:
     a. **Send Outlook Mail Message** activity (or **Send SMTP Mail Message** if
        Outlook is not installed):
        - To: `operations@company.com`
        - Subject: `"CRITICAL INCIDENT: " + incident_type + " at " + building_id`
        - Body: `"Tick: " + tick_number.ToString() + Chr(10) + "Severity: FULL" +
                 Chr(10) + "Immediate action required."`
     b. **Create Action Item** activity (from UiPath.Persistence.Activities package,
        if using Maestro):
        - Catalog Name: `"MaestroCity"`
        - Title: `"Critical Incident: " + building_id`
        - Priority: `High`
        - Data (JSON string): `"{ ""incident_type"": """ + incident_type + """ }"`
   - **Else** branch: **Log Message** with `"Severity is partial — standard routing."`

3. **Delay** activity: Duration `00:00:05` (5 seconds — simulates escalation routing).

4. **Assign** activity: `escalation_id = System.Guid.NewGuid().ToString()`

5. **If** activity — condition: `severity = "full"`
   - Then: **Assign** `action_taken = "Escalated to Level 3"`
   - Else: **Assign** `action_taken = "Escalated to Level 2"`

6. **If** activity — condition: `incident_type = "cloud_outage"`
   - Then: **Assign** `recovery_recommendation = "Activate backup_infra failover.
     Redirect workflows via comms_hub. Restore cloud_datacenter primary within 5 ticks."`
   - Else: **Assign** `recovery_recommendation = "Isolate affected building.
     Reduce autonomy for incident_response agent. Monitor cascade propagation."`

**Step 4 — Publish** as described in section 5.0.

---

### 5.2 Process 2: `Approval_Chain`

**Purpose:** Evaluates a workflow's risk score and either auto-approves or routes to a
human via a Maestro action item.

**Studio project name:** `Approval_Chain`

**Input Arguments:**

| Name              | Direction | Type   | Description                              |
|-------------------|-----------|--------|------------------------------------------|
| `workflow_id`     | In        | String | Simulation workflow ID (e.g., `"wf-012"`) |
| `workflow_type`   | In        | String | e.g., `"approval_request"`              |
| `risk_score`      | In        | Double | 0.0 – 1.0 (higher = riskier)            |
| `requesting_agent`| In        | String | Agent name (e.g., `"ARIA"`)             |

**Output Arguments:**

| Name             | Direction | Type    |
|------------------|-----------|---------|
| `approved`       | Out       | Boolean |
| `approver`       | Out       | String  |
| `reason`         | Out       | String  |
| `audit_trail_id` | Out       | String  |

**Sequence Logic:**

1. **Assign**: `audit_trail_id = System.Guid.NewGuid().ToString()`

2. **If** — condition: `risk_score > 0.85`
   - **Then** (requires human approval):
     a. **Create Action Item** activity:
        - Title: `"High-Risk Approval Required: " + workflow_type`
        - Priority: `High`
        - CatalogName: `"MaestroCity"`
        - Data: `"{ ""workflow_id"": """ + workflow_id + """, ""risk_score"": " +
                   risk_score.ToString() + ", ""agent"": """ + requesting_agent + """ }"`
     b. **Wait for Action Item** activity (or **Task Form** activity):
        - Capture the `Decision` field from the form submission.
     c. **If** — Decision = "Approve":
        - Assign: `approved = True`, `approver = "Human Reviewer"`,
          `reason = "Manual approval granted for high-risk workflow."`
     d. Else:
        - Assign: `approved = False`, `approver = "Human Reviewer"`,
          `reason = "Rejected by human reviewer."`

3. **Else If** — condition: `risk_score >= 0.7 AND risk_score <= 0.85`
   - **Then** (auto-approve with audit log):
     a. **Assign**: `approved = True`, `approver = "AutoApproval_System"`,
        `reason = "Risk score within auto-approve threshold."`
     b. **Append Line** activity (writes to `Data\audit_log.csv`):
        - File: `"Data\audit_log.csv"`
        - Text: `audit_trail_id + "," + workflow_id + "," + risk_score.ToString() +
                 ",AutoApproved," + Now.ToString()`

4. **Else** (risk_score < 0.7):
   - **Assign**: `approved = True`, `approver = "AutoApproval_System"`,
     `reason = "Low risk — automatic approval."`

**Publish** as in section 5.0.

---

### 5.3 Process 3: `Crisis_Response`

**Purpose:** Coordinates an enterprise-wide response to a cascade, trust collapse,
staffing exhaustion, or resource depletion crisis.

**Studio project name:** `Crisis_Response`

**Input Arguments:**

| Name                   | Direction | Type   | Description                                         |
|------------------------|-----------|--------|-----------------------------------------------------|
| `crisis_type`          | In        | String | `"cascade"`, `"trust_collapse"`, `"staffing_exhaustion"`, `"resource_depletion"` |
| `affected_buildings`   | In        | String | JSON array e.g. `'["hospital","pharmacy"]'`         |
| `operational_stability`| In        | Double | 0 – 100                                             |
| `human_strain`         | In        | Double | 0 – 100                                             |

**Output Arguments:**

| Name                        | Direction | Type   |
|-----------------------------|-----------|--------|
| `recovery_plan`             | Out       | String |
| `estimated_recovery_ticks`  | Out       | Int64  |
| `emergency_resources_needed`| Out       | String |

**Sequence Logic:**

1. **Log Message**: `"Crisis triggered: " + crisis_type`

2. **Append Line** (audit log):
   - File: `"Data\crisis_log.csv"`
   - Text: `Now.ToString() + "," + crisis_type + "," + operational_stability.ToString() +
            "," + human_strain.ToString() + "," + affected_buildings`

3. **If** — `crisis_type = "cascade"`:
   - **Invoke Workflow File** (or use a separate sequence inline):
     - Purpose: reroutes workflows away from affected buildings.
     - Log: `"Cascade detected — rerouting workflows from: " + affected_buildings`
   - **Assign**: `estimated_recovery_ticks = 15`
   - **Assign**: `emergency_resources_needed = "[""backup_infra"", ""comms_hub""]"`

4. **Else If** — `crisis_type = "trust_collapse"`:
   - **Assign**: `estimated_recovery_ticks = 25`
   - **Assign**: `emergency_resources_needed = "[""executive_strategy_agent""]"`

5. **Else If** — `crisis_type = "staffing_exhaustion"`:
   - **Assign**: `estimated_recovery_ticks = 10`
   - **Assign**: `emergency_resources_needed = "[""staffing_hr""]"`

6. **Else** (resource_depletion):
   - **Assign**: `estimated_recovery_ticks = 20`
   - **Assign**: `emergency_resources_needed = "[""backup_infra""]"`

7. **Create Action Item** activity:
   - Title: `"CRISIS — Executive Action Required: " + crisis_type`
   - Priority: `Critical`
   - CatalogName: `"MaestroCity"`
   - Data: `"{ ""crisis_type"": """ + crisis_type + """, ""stability"": " +
              operational_stability.ToString() + " }"`

8. **Assign**: `recovery_plan = "{ ""type"": """ + crisis_type + """,
     ""steps"": [""Isolate affected buildings"", ""Activate failover"",
     ""Reduce agent autonomy"", ""Notify executive team""],
     ""priority_order"": " + affected_buildings + " }"`

**Publish** as in section 5.0.

---

### 5.4 Process 4: `Emergency_Staffing`

**Purpose:** Identifies available staff, matches them to the affected building, and
schedules deployment.

**Studio project name:** `Emergency_Staffing`

**Input Arguments:**

| Name             | Direction | Type   | Description                           |
|------------------|-----------|--------|---------------------------------------|
| `building_id`    | In        | String | Building that needs staff             |
| `current_strain` | In        | Double | Human strain 0 – 100 (high = bad)    |
| `deficit`        | In        | Double | Staff units needed                    |

**Output Arguments:**

| Name                      | Direction | Type   |
|---------------------------|-----------|--------|
| `staff_assigned`          | Out       | Int64  |
| `new_staffing_level`      | Out       | Double |
| `estimated_relief_in_ticks`| Out      | Int64  |

**Data Folder Setup:**

Create a `Data` folder inside your Studio project. Add a file `staff_roster.csv` with
columns: `StaffId, Name, Skills, Available, AssignedBuilding`.
Example rows:
```
S001,Alice Chen,"hospital,pharmacy",True,
S002,Bob Martinez,"cloud_datacenter,comms_hub",True,
S003,Carol Singh,"staffing_hr,orchestration_center",True,
```

**Sequence Logic:**

1. **Read CSV File** activity:
   - FilePath: `"Data\staff_roster.csv"`
   - Output: a DataTable variable named `rosterTable`.

2. **Filter Data Table** activity: filter where `Available = "True"` AND
   `Skills` contains `building_id`. Store result in `availableStaff`.

3. **Assign**: `staff_assigned = availableStaff.Rows.Count`
   (Capped: if `staff_assigned > deficit`, set `staff_assigned = CInt(deficit)`)

4. **If** — `staff_assigned > 0`:
   - **For Each Row** in `availableStaff` (up to `staff_assigned` rows):
     - **Assign**: `rosterTable.Rows(rowIndex)("AssignedBuilding") = building_id`
     - **Assign**: `rosterTable.Rows(rowIndex)("Available") = "False"`
   - **Write CSV File**: save updated `rosterTable` back to `"Data\staff_roster.csv"`.

5. **Assign**: `new_staffing_level = Math.Min(100.0, (100.0 - current_strain) +
              (staff_assigned * 5.0))`

6. **If** — `current_strain > 80`:
   - **Assign**: `estimated_relief_in_ticks = 3`
7. **Else If** — `current_strain > 60`:
   - **Assign**: `estimated_relief_in_ticks = 5`
8. **Else**:
   - **Assign**: `estimated_relief_in_ticks = 8`

9. **Create Action Item** activity:
   - Title: `"Staffing Deployed: " + staff_assigned.ToString() + " to " + building_id`
   - Priority: `High`
   - CatalogName: `"MaestroCity"`
   - Data: `"{ ""building_id"": """ + building_id + """, ""staff_assigned"": " +
              staff_assigned.ToString() + " }"`

**Publish** as in section 5.0.

---

### 5.5 Process 5: `Trust_Recovery_Protocol`

**Purpose:** Analyses a trust drop event, adjusts agent autonomy recommendations, and
generates a step-by-step recovery checklist with Maestro action items.

**Studio project name:** `Trust_Recovery_Protocol`

**Input Arguments:**

| Name                | Direction | Type   | Description                                       |
|---------------------|-----------|--------|---------------------------------------------------|
| `current_trust`     | In        | Double | Current system trust score 0 – 100                |
| `trust_drop_cause`  | In        | String | e.g., `"failed_escalation"`, `"incorrect_action"` |
| `affected_agent_ids`| In        | String | JSON array e.g. `'["ops_coord","incident_resp"]'`  |

**Output Arguments:**

| Name                         | Direction | Type   |
|------------------------------|-----------|--------|
| `recommended_autonomy_levels`| Out       | String |
| `recovery_checklist`         | Out       | String |
| `estimated_trust_recovery_ticks`| Out   | Int64  |

**Sequence Logic:**

1. **Log Message**: `"Trust recovery initiated. Current trust: " +
   current_trust.ToString() + ". Cause: " + trust_drop_cause`

2. **If** — `current_trust < 40`:
   - **Assign**: `recommended_autonomy_levels =
     "{ ""ops_coord"": 1, ""incident_resp"": 1, ""compliance"": 0,
        ""comms"": 1, ""exec_strategy"": 1 }"`
   - **Assign**: `estimated_trust_recovery_ticks = 30`
3. **Else If** — `current_trust < 70`:
   - **Assign**: `recommended_autonomy_levels =
     "{ ""ops_coord"": 2, ""incident_resp"": 1, ""compliance"": 1,
        ""comms"": 2, ""exec_strategy"": 1 }"`
   - **Assign**: `estimated_trust_recovery_ticks = 15`
4. **Else**:
   - **Assign**: `recommended_autonomy_levels =
     "{ ""ops_coord"": 2, ""incident_resp"": 2, ""compliance"": 1,
        ""comms"": 2, ""exec_strategy"": 2 }"`
   - **Assign**: `estimated_trust_recovery_ticks = 8`

5. **Assign**: `recovery_checklist =
   "[""Reduce autonomy for affected agents"",
     ""Run audit trail review on recent agent actions"",
     ""Human-in-the-loop approval required for next 5 high-risk decisions"",
     ""Monitor trust score for 10 ticks before restoring autonomy"",
     ""Conduct post-incident review with executive team""]"`

6. **Create Action Item** for each step:
   - Use a **For Each** over the steps (parse the JSON or enumerate inline):
     - Title: `"Trust Recovery Step: " + stepDescription`
     - Priority: `High`
     - CatalogName: `"MaestroCity"`

7. **Log Message**: `"Trust recovery plan created. ETA: " +
   estimated_trust_recovery_ticks.ToString() + " ticks."`

**Publish** as in section 5.0.

---

## 6. Verify All Five Processes in Orchestrator

1. In Orchestrator, open the **MaestroCity** folder.
2. Click **Processes** in the left sidebar.
3. Confirm you see all five entries:
   - `Incident_Escalation`
   - `Approval_Chain`
   - `Crisis_Response`
   - `Emergency_Staffing`
   - `Trust_Recovery_Protocol`
4. For each process, click on it and note the **Package Name** and **Package Version**.
   The Maestro City backend uses the process name (not version) to look up the release
   key, so the name must match exactly (case-sensitive).

---

## 6.1 Set Up Integration Service API Triggers

API Triggers let external systems (like Maestro City) fire a UiPath process via a simple
HTTP POST without needing to look up a Release Key first. Create one trigger per
enterprise system endpoint listed below.

### 6.1.1 Open API Triggers

1. In Orchestrator, open the **MaestroCity** folder.
2. In the left sidebar, look for **Triggers** (clock icon). Click it.
3. Click the **API Triggers** tab.
4. Click **+ Add Trigger**.

### 6.1.2 Create the Five Required Triggers

For each trigger, fill in the form and click **Create**:

| Display Name              | Slug (unique URL path)    | Process to invoke         | Enabled |
|---------------------------|---------------------------|---------------------------|---------|
| EHR Availability Check    | `ehr-availability-check`  | `Incident_Escalation`     | Yes     |
| Pharmacy Inventory Sync   | `pharmacy-inventory-sync` | `Emergency_Staffing`      | Yes     |
| Staffing Status Update    | `staffing-status-update`  | `Emergency_Staffing`      | Yes     |
| Outage Notification       | `outage-notification`     | `Crisis_Response`         | Yes     |
| Escalation Notify         | `escalation-notify`       | `Incident_Escalation`     | Yes     |

After creating each trigger, copy the slug exactly as shown and confirm it matches
the corresponding `UIPATH_TRIGGER_*_SLUG` value in your `.env` file.

### 6.1.3 How API Triggers Work

When Maestro City receives an external notification (e.g., `POST /api/enterprise/outage/notify`),
the backend fires the corresponding UiPath API Trigger:

```
POST https://cloud.uipath.com/{org}/{tenant}/orchestrator_/api/triggers/{slug}
Authorization: Bearer {token}
X-UIPATH-OrganizationUnitId: {folder_id}
Content-Type: application/json

{ "data": { "notificationId": "...", "systemId": "ehr", "severity": "high" } }
```

UiPath Orchestrator then starts the linked process and passes the `data` payload as
input arguments. No Release Key lookup is needed — the trigger handles that internally.

---

## 7. Set Up Webhooks

Webhooks allow Orchestrator to push job status updates back to the Maestro City backend
the moment a job finishes, rather than waiting for polling.

### 7.1 Open Webhook Settings

1. In Orchestrator, click the gear icon (Settings) in the top-right, OR look for
   **Integrations** in the left sidebar.
2. Click **Webhooks**.
3. Click **+ Add** (top right).

### 7.2 Configure the Webhook

Fill in the form:

- **URL**: `http://YOUR_SERVER_IP:8000/api/uipath/webhook`
  Replace `YOUR_SERVER_IP` with the public IP or hostname where the Maestro City backend
  runs. For local development use a tunnel tool (e.g., `ngrok http 8000`) and paste the
  ngrok HTTPS URL.
- **Enabled**: toggle ON.
- **Secret**: Click **Generate** or type a random 32-character string.
  Example: `mc-webhook-secret-a7f3k9p2q8r1s4t6`
  Copy this value. It goes in your `.env` file as `UIPATH_WEBHOOK_SECRET`.
- **Subscribe to events**: Check all of the following:
  - `job.created`
  - `job.started`
  - `job.completed`
  - `job.faulted`
  - `job.stopped`
  - `process.schedule.executed`
  - `action_item.created`
  - `action_item.completed`
- **Scope**: leave as **Tenant** (applies to all folders including MaestroCity), or
  select **Folder** and choose **MaestroCity** for tighter scoping.

### 7.3 Save and Test

1. Click **Add** to save.
2. Orchestrator will show the webhook in the list with status **Active**.
3. To test: trigger a dummy job from Orchestrator (any process), then check your backend
   logs to confirm the webhook payload arrived at `/api/uipath/webhook`.

---

## 8. Set Up UiPath Maestro Agents (If on Maestro Tier)

If your UiPath licence includes **Maestro** (the agentic orchestration layer), follow
these steps to configure Maestro agents that mirror the simulation's five agent types.

### 8.1 Open Maestro

1. In the UiPath left sidebar, click **Maestro** (the star/sparkle icon).
2. If you do not see it, your licence may not include Maestro. The simulation works
   without this section — UiPath Orchestrator jobs are the primary integration point.

### 8.2 Create a Catalog

1. Click **Catalogs** in the Maestro left sidebar.
2. Click **+ New Catalog**.
3. Name: `MaestroCity`
4. Description: `Automation catalog for Maestro City simulation agents`
5. Click **Create**.

### 8.3 Add Agents to the Catalog

For each of the five simulation agents, create a corresponding Maestro agent:

| Agent Name       | Type                  | Capabilities / Skills                              |
|------------------|-----------------------|----------------------------------------------------|
| ARIA             | Operations Coordinator| Workflow routing, queue management, status reporting|
| SENTINEL         | Incident Response     | Outage detection, escalation, failover triggering  |
| VERITAS          | Compliance            | Audit trail, approval gating, risk assessment      |
| ECHO             | Communications        | Alert broadcasting, stakeholder notification       |
| APEX             | Executive Strategy    | KPI monitoring, strategic reallocation             |

For each:
1. In the **MaestroCity** catalog, click **+ Add Agent**.
2. Fill in **Name**, **Description**, and **Instructions** matching the agent's role.
3. Under **Skills**, link the relevant UiPath processes:
   - SENTINEL → `Incident_Escalation`, `Crisis_Response`
   - VERITAS → `Approval_Chain`
   - ARIA → `Emergency_Staffing`
   - APEX → `Trust_Recovery_Protocol`
   - ECHO → all processes (communications role)
4. Click **Save**.

---

## 9. Complete `.env` File Reference

After completing all steps above, your `.env` file in `apps/backend/` should look like:

```env
# ─── UiPath Connection ────────────────────────────────────────────────────────
UIPATH_CLOUD_URL=https://cloud.uipath.com
UIPATH_ORGANIZATION=your-org-name
UIPATH_TENANT=your-tenant-name
UIPATH_CLIENT_ID=a1b2c3d4-e5f6-7890-abcd-ef1234567890
UIPATH_CLIENT_SECRET=very-long-secret-string-from-uipath
UIPATH_FOLDER_ID=12345
UIPATH_WEBHOOK_SECRET=mc-webhook-secret-a7f3k9p2q8r1s4t6

# ─── Agent Builder: Orchestrator Process Names ────────────────────────────────
# Each Agent Builder agent is published as an Orchestrator process.
# These names must match the Release names in your MaestroCity folder exactly.
# The backend calls StartJobs with these names when invoking agents.
UIPATH_ARIA_PROCESS_NAME=ARIA_Operations_Coordinator
UIPATH_SENTINEL_PROCESS_NAME=SENTINEL_Incident_Response
UIPATH_VERITAS_PROCESS_NAME=VERITAS_Compliance
UIPATH_ECHO_PROCESS_NAME=ECHO_Communications
UIPATH_APEX_PROCESS_NAME=APEX_Executive_Strategy

# ─── Integration Service API Trigger Slugs ────────────────────────────────────
# Create these triggers in Orchestrator > Triggers > API Triggers.
# The slug is the unique path segment you assign when creating each trigger.
# Leave as default if you use the exact names from UIPATH_PLATFORM_SETUP step 6.
UIPATH_TRIGGER_EHR_SLUG=ehr-availability-check
UIPATH_TRIGGER_PHARMACY_SLUG=pharmacy-inventory-sync
UIPATH_TRIGGER_STAFFING_SLUG=staffing-status-update
UIPATH_TRIGGER_OUTAGE_SLUG=outage-notification
UIPATH_TRIGGER_ESCALATION_SLUG=escalation-notify

# ─── Coding Agent (OpenAI) ────────────────────────────────────────────────────
# Required for the Coding Agent bonus feature (AI-generated XAML workflows).
# Model: gpt-4o. Without this key the feature runs in demo mode.
# Get your key at: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-...

# ─── Simulation Settings ──────────────────────────────────────────────────────
SIMULATION_TICK_INTERVAL=1.0
```

---

## 10. Test the Full Integration

### 10.1 Start the Backend

```bash
cd apps/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Look for this line in the logs:
```
UiPath client initialised — connected to org=your-org tenant=your-tenant
```
If you see `UiPath not configured — running in offline mode`, check that all five
`UIPATH_*` env vars are set.

### 10.2 Test Job Triggering

Use `curl` or the Swagger UI at `http://localhost:8000/docs` to POST a test action:

```bash
curl -X POST http://localhost:8000/api/action \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trigger_uipath",
    "processName": "Incident_Escalation",
    "inputArgs": {
      "incident_type": "cloud_outage",
      "building_id": "cloud_datacenter",
      "severity": "partial",
      "tick_number": 1
    }
  }'
```

Go to Orchestrator > MaestroCity folder > **Jobs** and confirm a new job appears
with state `Pending` or `Running`.

### 10.3 Verify Webhook

Once the job completes, check your backend logs for:
```
[webhook] Received job.completed for job_id=XXXXX
```

If running locally with ngrok, the ngrok console at `http://localhost:4040` shows
incoming webhook requests.

### 10.4 Monitor in Orchestrator

1. Orchestrator > MaestroCity folder > **Jobs**: all triggered jobs with state and logs.
2. Orchestrator > **Action Items**: shows any Maestro action items created by the
   workflows.
3. Orchestrator > **Logs**: detailed execution logs from each robot run.

---

## Troubleshooting Quick Reference

| Problem                                  | Likely Cause                                 | Fix                                                          |
|------------------------------------------|----------------------------------------------|--------------------------------------------------------------|
| `401 Unauthorized` on API calls          | Wrong Client ID/Secret or expired token      | Regenerate secret in External Applications                   |
| `404 Not Found` for process              | Process not published to MaestroCity folder  | Republish from Studio, select MaestroCity folder             |
| `No robots available`                    | Robot is offline or disconnected             | Check Robot service on local machine; use serverless instead |
| Webhook not arriving                     | URL not reachable from UiPath Cloud          | Use ngrok tunnel; confirm firewall allows inbound on port 8000|
| `Folder ID not found`                    | Wrong UIPATH_FOLDER_ID in .env               | Use the API filter method in step 3.3 to get correct ID      |
| Action items not appearing               | Maestro Activities package not installed     | In Studio: Manage Packages > Official > install UiPath.Persistence.Activities |
