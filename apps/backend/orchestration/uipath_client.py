"""
UiPath Orchestrator REST API client.
Handles authentication, job management, approvals, and webhook processing.
Fails gracefully when credentials are not configured.
"""
import json
import logging
import os
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

import httpx
from dotenv import load_dotenv

from models.state import AlertSeverity, UiPathApproval, UiPathJob, UiPathStatus

load_dotenv()

logger = logging.getLogger(__name__)

# Path joined to UIPATH_CLOUD_URL so the right Identity Server is used per environment
# (e.g. https://cloud.uipath.com or https://staging.uipath.com for hackathon access).
TOKEN_ENDPOINT_PATH = "identity_/connect/token"
TOKEN_BUFFER_SECONDS = 60  # refresh token 60s before expiry

# Agent Builder: each Maestro City agent is deployed as an Orchestrator process.
# These names must match the Release names in your UiPath Orchestrator folder.
# Override via environment variables e.g. UIPATH_ARIA_PROCESS_NAME=Custom_ARIA_v2
_DEFAULT_AGENT_PROCESSES: Dict[str, str] = {
    "aria": "ARIA_Operations_Coordinator",
    "sentinel": "SENTINEL_Incident_Response",
    "veritas": "VERITAS_Compliance",
    "echo": "ECHO_Communications",
    "apex": "APEX_Executive_Strategy",
}


class UiPathClient:
    def __init__(self) -> None:
        self.base_url: str = os.getenv("UIPATH_CLOUD_URL", "https://cloud.uipath.com")
        self.org: Optional[str] = os.getenv("UIPATH_ORGANIZATION")
        self.tenant: Optional[str] = os.getenv("UIPATH_TENANT")
        self.client_id: Optional[str] = os.getenv("UIPATH_CLIENT_ID")
        self.client_secret: Optional[str] = os.getenv("UIPATH_CLIENT_SECRET")
        self.folder_id: Optional[str] = os.getenv("UIPATH_FOLDER_ID")

        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0
        self.connected: bool = False
        self._active_jobs: Dict[str, UiPathJob] = {}
        self._pending_approvals: Dict[str, UiPathApproval] = {}
        self._job_callbacks: Dict[str, List[Callable]] = {}
        self._configured: bool = self._check_configured()

        # Orchestration mode: "direct" = agents fire individual Orchestrator jobs;
        # "maestro" = agent actions are routed into a single published Maestro Case
        # instance (MaestroCity_PipelineTest) that orchestrates the agents + human approval.
        self.orchestration_mode: str = os.getenv("UIPATH_ORCHESTRATION_MODE", "direct").lower()
        self.maestro_case_process: str = os.getenv("UIPATH_MAESTRO_CASE_PROCESS", "MaestroCity_PipelineTest")
        self._last_maestro_start: float = 0.0
        # Dedupe window: one Maestro Case instance per burst of agent actions.
        self._maestro_cooldown: float = float(os.getenv("UIPATH_MAESTRO_COOLDOWN_SECONDS", "25"))

        # Human-in-the-loop approval state:
        #  - workflows a human has already decided on never re-gate (no treadmill)
        #  - after any human decision, VERITAS backs off creating new approvals so the
        #    queue actually stays cleared instead of instantly refilling.
        self._resolved_workflows: set = set()
        self._last_human_decision: float = 0.0
        self._approval_cooldown: float = float(os.getenv("UIPATH_APPROVAL_COOLDOWN_SECONDS", "45"))

        # Resolve agent process names from env vars (allow override per-agent)
        self._agent_processes: Dict[str, str] = {
            agent_id: os.getenv(
                f"UIPATH_{agent_id.upper()}_PROCESS_NAME",
                default_name,
            )
            for agent_id, default_name in _DEFAULT_AGENT_PROCESSES.items()
        }

        if not self._configured:
            logger.warning(
                "UiPath credentials not fully configured. "
                "Simulation will run without real automation jobs. "
                "Set UIPATH_CLIENT_ID, UIPATH_CLIENT_SECRET, UIPATH_ORGANIZATION, "
                "UIPATH_TENANT in your .env file to enable UiPath integration."
            )

    def _check_configured(self) -> bool:
        """Check if all required env vars are set."""
        required = [self.client_id, self.client_secret, self.org, self.tenant]
        return all(v and v not in ("your-client-id", "your-client-secret", "your-org", "your-tenant") for v in required)

    async def authenticate(self) -> bool:
        """Authenticate with UiPath Cloud and cache the access token."""
        if not self._configured:
            return False

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/{TOKEN_ENDPOINT_PATH}",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "scope": "OR.Jobs OR.Execution OR.Folders OR.Tasks",
                    },
                )
                response.raise_for_status()
                data = response.json()
                self._access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self._token_expiry = time.time() + expires_in - TOKEN_BUFFER_SECONDS
                self.connected = True
                logger.info("UiPath authentication successful")
                return True
        except httpx.HTTPStatusError as e:
            logger.error(f"UiPath auth failed (HTTP {e.response.status_code}): {e.response.text[:200]}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"UiPath auth error: {e}")
            self.connected = False
            return False

    async def _get_token(self) -> Optional[str]:
        """Return cached token or re-authenticate if expired."""
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        success = await self.authenticate()
        return self._access_token if success else None

    def _build_orchestrator_url(self, path: str) -> str:
        return f"{self.base_url}/{self.org}/{self.tenant}/orchestrator_/{path.lstrip('/')}"

    def _build_headers(self, token: str) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if self.folder_id:
            headers["X-UIPATH-OrganizationUnitId"] = str(self.folder_id)
        return headers

    async def get_release_key(self, process_name: str) -> Optional[str]:
        """Get the release key for a process by name."""
        if not self._configured:
            return None

        token = await self._get_token()
        if not token:
            return None

        try:
            url = self._build_orchestrator_url(
                f"odata/Releases?$filter=Name eq '{process_name}'"
            )
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self._build_headers(token))
                response.raise_for_status()
                data = response.json()
                releases = data.get("value", [])
                if releases:
                    return releases[0].get("Key")
                logger.warning(f"No release found for process: {process_name}")
                return None
        except Exception as e:
            logger.error(f"Failed to get release key for {process_name}: {e}")
            return None

    async def start_job(
        self,
        process_name: str,
        input_args: dict,
        folder_id: Optional[str] = None,
    ) -> Optional[UiPathJob]:
        """Start a UiPath automation job.

        In "maestro" orchestration mode, individual agent process calls are folded
        into a single published Maestro Case instance instead of firing separately.
        """
        if (
            self.orchestration_mode == "maestro"
            and self._configured
            and process_name != self.maestro_case_process
        ):
            now = time.time()
            if now - self._last_maestro_start < self._maestro_cooldown:
                # A Maestro Case is already orchestrating this burst — don't spawn another.
                logger.info(
                    f"Maestro mode: '{process_name}' folded into the active Maestro Case "
                    f"(within {self._maestro_cooldown:.0f}s window)"
                )
                return None
            self._last_maestro_start = now
            return await self._start_maestro_case(process_name, input_args, folder_id)

        # Create a simulation-tracked job regardless of UiPath connection
        job_id = f"sim-{uuid.uuid4().hex[:8]}"
        sim_job = UiPathJob(
            id=job_id,
            processName=process_name,
            state="Pending",
            startedAt=time.time(),
            simulationContext=json.dumps({
                "process": process_name,
                "args": input_args,
                "simulated": not self._configured,
            }),
        )

        def _fault(reason: str) -> UiPathJob:
            # Fail-forward: surface the failure as a Faulted job in the UI — never fake success.
            sim_job.state = "Faulted"
            sim_job.simulationContext = reason
            self._active_jobs[sim_job.id] = sim_job
            logger.error(f"UiPath job '{process_name}' faulted: {reason}")
            return sim_job

        if not self._configured:
            return _fault("UiPath not configured — set UiPath credentials in the backend .env")

        token = await self._get_token()
        if not token:
            return _fault("UiPath auth unavailable — could not obtain an access token")

        try:
            release_key = await self.get_release_key(process_name)
            if not release_key:
                return _fault(f"Process '{process_name}' is not published to the configured folder")

            url = self._build_orchestrator_url(
                "odata/Jobs/UiPath.Server.Configuration.OData.StartJobs"
            )
            effective_folder = folder_id or self.folder_id

            payload = {
                "startInfo": {
                    "ReleaseKey": release_key,
                    # Serverless Automation Cloud Robots: modern strategy + Serverless runtime.
                    # (Legacy "Unattended" strategy fails with errorCode 2818 on serverless folders.)
                    "Strategy": "ModernJobsCount",
                    "RuntimeType": "Serverless",
                    "JobsCount": 1,
                    "InputArguments": json.dumps(input_args),
                }
            }
            if effective_folder:
                payload["startInfo"]["OrganizationUnitId"] = int(effective_folder)

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    url,
                    headers=self._build_headers(token),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                jobs_created = data.get("value", [{}])
                if jobs_created:
                    real_id = str(jobs_created[0].get("Id", job_id))
                    sim_job.id = real_id
                    sim_job.state = "Running"

            self._active_jobs[sim_job.id] = sim_job
            logger.info(f"Started UiPath job: {process_name} (id={sim_job.id})")
            return sim_job

        except httpx.HTTPStatusError as e:
            return _fault(f"StartJobs failed: HTTP {e.response.status_code} {e.response.text[:150]}")
        except Exception as e:
            return _fault(f"StartJobs error: {e}")

    def set_orchestration_mode(self, mode: str) -> str:
        """Switch between 'direct' (per-agent jobs) and 'maestro' (single Maestro Case)."""
        mode = (mode or "").lower()
        if mode not in ("direct", "maestro"):
            raise ValueError("orchestration mode must be 'direct' or 'maestro'")
        self.orchestration_mode = mode
        self._last_maestro_start = 0.0  # allow an immediate Maestro start after switching
        logger.info(f"Orchestration mode set to '{mode}'")
        return mode

    async def _start_maestro_case(
        self, triggering_process: str, input_args: dict, folder_id: Optional[str] = None
    ) -> Optional[UiPathJob]:
        """Start a real Maestro Case instance via StartJobs.

        Fail-forward: if auth/release/start fails, the job is surfaced as Faulted in the
        UI with the reason — never a silently faked success.
        """
        job_id = f"maestro-{uuid.uuid4().hex[:8]}"
        job = UiPathJob(
            id=job_id,
            processName=f"Maestro Case ◆ {self.maestro_case_process}",
            state="Pending",
            startedAt=time.time(),
            simulationContext=f"triggered by {triggering_process}",
        )

        def _fault(reason: str) -> UiPathJob:
            job.state = "Faulted"
            job.simulationContext = reason
            self._active_jobs[job.id] = job
            logger.error(f"Maestro Case start failed ({triggering_process}): {reason}")
            return job

        token = await self._get_token()
        if not token:
            return _fault("UiPath auth unavailable — could not start Maestro Case")

        release_key = await self.get_release_key(self.maestro_case_process)
        if not release_key:
            return _fault(f"Maestro Case '{self.maestro_case_process}' is not published to this folder")

        try:
            url = self._build_orchestrator_url(
                "odata/Jobs/UiPath.Server.Configuration.OData.StartJobs"
            )
            payload = {
                "startInfo": {
                    "ReleaseKey": release_key,
                    "Strategy": "ModernJobsCount",
                    "RuntimeType": "Serverless",
                    "JobsCount": 1,
                    "InputArguments": json.dumps(
                        {"triggeringProcess": triggering_process, **input_args}
                    ),
                }
            }
            effective_folder = folder_id or self.folder_id
            if effective_folder:
                payload["startInfo"]["OrganizationUnitId"] = int(effective_folder)

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    url, headers=self._build_headers(token), json=payload
                )
                response.raise_for_status()
                jobs_created = response.json().get("value", [{}])
                if jobs_created:
                    job.id = str(jobs_created[0].get("Id", job_id))
                job.state = "Running"

            self._active_jobs[job.id] = job
            logger.info(
                f"Started Maestro Case '{self.maestro_case_process}' (id={job.id}) "
                f"triggered by {triggering_process}"
            )
            return job
        except httpx.HTTPStatusError as e:
            return _fault(f"Maestro Case start failed: HTTP {e.response.status_code} {e.response.text[:150]}")
        except Exception as e:
            return _fault(f"Maestro Case start error: {e}")

    async def get_job_status(self, job_id: str) -> Optional[UiPathJob]:
        """Get the current status of a UiPath job."""
        if not self._configured or job_id.startswith("sim-"):
            return self._active_jobs.get(job_id)

        token = await self._get_token()
        if not token:
            return self._active_jobs.get(job_id)

        try:
            url = self._build_orchestrator_url(f"odata/Jobs({job_id})")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self._build_headers(token))
                response.raise_for_status()
                data = response.json()

                job = self._active_jobs.get(job_id)
                if not job:
                    job = UiPathJob(
                        id=str(data.get("Id", job_id)),
                        processName=data.get("ReleaseName", "Unknown"),
                        state=data.get("State", "Unknown"),
                        startedAt=time.time(),
                        simulationContext="",
                    )

                job.state = data.get("State", job.state)
                self._active_jobs[job_id] = job
                return job
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return self._active_jobs.get(job_id)

    async def create_action_item(
        self, title: str, app_name: str, data: dict
    ) -> Optional[str]:
        """Create a UiPath Maestro action item (for approvals)."""
        if not self._configured:
            action_id = f"action-{uuid.uuid4().hex[:8]}"
            logger.info(f"Simulated action item: {title} (id={action_id})")
            return action_id

        token = await self._get_token()
        if not token:
            return None

        try:
            url = self._build_orchestrator_url("api/ActionItems")
            payload = {
                "title": title,
                "appName": app_name,
                "data": data,
                "priority": "High",
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url,
                    headers=self._build_headers(token),
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
                return str(result.get("Id", ""))
        except Exception as e:
            logger.error(f"Failed to create action item '{title}': {e}")
            return None

    async def poll_active_jobs(self) -> None:
        """Update status of all active jobs. Called each tick to sync job states."""
        if not self._active_jobs:
            return

        jobs_to_check = list(self._active_jobs.items())

        for job_id, job in jobs_to_check:
            if job.state in ("Successful", "Faulted", "Stopped"):
                continue  # already terminal

            if not self._configured or job_id.startswith("sim-"):
                # Simulate job progression
                elapsed = time.time() - job.startedAt
                if elapsed > 8.0:  # simulate ~8 second job completion
                    import random
                    job.state = "Successful" if random.random() > 0.1 else "Faulted"
                    # Trigger callbacks
                    await self._fire_callbacks(job)
            else:
                updated = await self.get_job_status(job_id)
                if updated and updated.state in ("Successful", "Faulted", "Stopped"):
                    await self._fire_callbacks(updated)

    async def _fire_callbacks(self, job: UiPathJob) -> None:
        """Fire registered callbacks for a completed job."""
        callbacks = self._job_callbacks.get(job.id, [])
        for cb in callbacks:
            try:
                await cb(job)
            except Exception as e:
                logger.error(f"Job callback error for {job.id}: {e}")

    def on_job_completed(self, job_id: str, callback: Callable) -> None:
        """Register a callback for when a specific job completes."""
        if job_id not in self._job_callbacks:
            self._job_callbacks[job_id] = []
        self._job_callbacks[job_id].append(callback)

    async def get_status(self) -> UiPathStatus:
        """Return the full UiPath status object."""
        active_jobs = [
            j for j in self._active_jobs.values()
            if j.state in ("Pending", "Running")
        ]
        pending_approvals = list(self._pending_approvals.values())

        return UiPathStatus(
            connected=self.connected,
            activeJobs=active_jobs,
            pendingApprovals=pending_approvals,
            lastSync=time.time(),
        )

    async def handle_webhook(self, payload: dict) -> None:
        """
        Process incoming webhook from UiPath.
        Updates job status and triggers callbacks.
        """
        event_type = payload.get("Type", "")
        job_data = payload.get("Job", {})

        if not job_data:
            logger.debug(f"Webhook received with no job data: {event_type}")
            return

        job_id = str(job_data.get("Id", ""))
        if not job_id:
            return

        if job_id in self._active_jobs:
            job = self._active_jobs[job_id]
            old_state = job.state
            job.state = job_data.get("State", job.state)
            logger.info(f"Webhook: job {job_id} state {old_state} -> {job.state}")

            if job.state in ("Successful", "Faulted", "Stopped"):
                await self._fire_callbacks(job)
        else:
            # New job we haven't seen (might be triggered externally)
            new_job = UiPathJob(
                id=job_id,
                processName=job_data.get("ReleaseName", "Unknown"),
                state=job_data.get("State", "Unknown"),
                startedAt=time.time(),
                simulationContext=json.dumps(payload),
            )
            self._active_jobs[job_id] = new_job
            logger.info(f"Webhook: registered new job {job_id} ({new_job.processName})")

        # Handle approval results
        if event_type in ("action.completed", "action.approved", "action.rejected"):
            action_id = str(payload.get("ActionId", ""))
            if action_id in self._pending_approvals:
                del self._pending_approvals[action_id]
                logger.info(f"Approval {action_id} resolved via webhook")

    async def invoke_agent(
        self,
        agent_id: str,
        context: dict,
        folder_id: Optional[str] = None,
    ) -> Optional[UiPathJob]:
        """
        Invoke a UiPath Agent Builder agent by its agent ID.

        Agent Builder agents are deployed as Orchestrator Processes. This method
        resolves the agent_id to its configured process name and calls StartJobs.

        agent_id: one of "aria", "sentinel", "veritas", "echo", "apex"
        context: dict passed as InputArguments to the process
        """
        process_name = self._agent_processes.get(agent_id.lower())
        if not process_name:
            logger.warning(f"Unknown agent_id for invocation: {agent_id}")
            return None

        input_args = {
            "in_AgentId": agent_id,
            "in_Context": json.dumps(context),
            "in_SimulationTick": context.get("tick", 0),
            "in_Phase": context.get("phase", "unknown"),
        }
        logger.info(f"Invoking Agent Builder agent: {agent_id} -> process: {process_name}")
        return await self.start_job(process_name, input_args, folder_id)

    async def trigger_api_workflow(
        self,
        trigger_slug: str,
        payload: dict,
        folder_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger an Integration Service API Workflow via an Orchestrator API Trigger.

        API Triggers are created in Orchestrator under Triggers > API Triggers.
        The trigger_slug is the unique path segment you assigned when creating the trigger
        (e.g. "ehr-availability-check" → POST /api/triggers/ehr-availability-check).

        Docs: https://docs.uipath.com/orchestrator/latest/user-guide/managing-api-triggers
        """
        if not self._configured:
            logger.info(f"Simulated API trigger: {trigger_slug}")
            return {"jobId": f"sim-{uuid.uuid4().hex[:8]}", "status": "Pending", "simulated": True}

        token = await self._get_token()
        if not token:
            return None

        try:
            url = self._build_orchestrator_url(f"api/triggers/{trigger_slug}")
            effective_folder = folder_id or self.folder_id
            headers = self._build_headers(token)
            if effective_folder:
                headers["X-UIPATH-OrganizationUnitId"] = str(effective_folder)

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, headers=headers, json={"data": payload})
                response.raise_for_status()
                result = response.json()
                logger.info(f"API trigger fired: {trigger_slug} -> {result}")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(
                f"API trigger {trigger_slug} failed (HTTP {e.response.status_code}): "
                f"{e.response.text[:200]}"
            )
            return None
        except Exception as e:
            logger.error(f"API trigger error for {trigger_slug}: {e}")
            return None

    def cleanup_jobs(self) -> None:
        """Remove completed jobs older than 5 minutes."""
        cutoff = time.time() - 300
        to_remove = [
            jid for jid, j in self._active_jobs.items()
            if j.state in ("Successful", "Faulted", "Stopped") and j.startedAt < cutoff
        ]
        for jid in to_remove:
            del self._active_jobs[jid]
            self._job_callbacks.pop(jid, None)
