"""
Webhook handler: validates UiPath webhook signatures and processes events.
Updates simulation state based on incoming UiPath webhook payloads.
"""
import hashlib
import hmac
import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("UIPATH_WEBHOOK_SECRET", "")


class WebhookHandler:
    def __init__(self) -> None:
        self._secret: str = WEBHOOK_SECRET

    def validate_signature(
        self, payload_bytes: bytes, signature_header: str
    ) -> bool:
        """
        Validate UiPath webhook HMAC-SHA256 signature.
        Header format: sha256=<hex_digest>
        Returns True if valid or if no secret is configured (dev mode).
        """
        if not self._secret:
            logger.debug("No webhook secret configured, skipping signature validation")
            return True

        if not signature_header:
            logger.warning("Webhook received without signature header")
            return False

        # Header format: "sha256=abc123..."
        parts = signature_header.split("=", 1)
        if len(parts) != 2 or parts[0] != "sha256":
            logger.warning(f"Invalid signature header format: {signature_header[:50]}")
            return False

        expected_sig = parts[1]
        computed_sig = hmac.new(
            self._secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        valid = hmac.compare_digest(expected_sig, computed_sig)
        if not valid:
            logger.warning("Webhook signature validation failed")
        return valid

    async def process_webhook(
        self, payload: Dict[str, Any], engine: "SimulationEngine"
    ) -> Dict[str, Any]:
        """
        Parse and process an incoming UiPath webhook.
        Returns a summary of what was processed.
        """
        event_type = payload.get("Type", "Unknown")
        timestamp = payload.get("Timestamp", time.time())

        logger.info(f"Processing webhook: type={event_type}")

        result: Dict[str, Any] = {
            "processed": True,
            "eventType": event_type,
            "timestamp": timestamp,
            "actions": [],
        }

        # Route to appropriate handler
        if event_type in ("job.completed", "job.faulted", "job.stopped"):
            actions = await self._handle_job_event(payload, engine, event_type)
            result["actions"].extend(actions)

        elif event_type in ("action.completed", "action.approved", "action.rejected"):
            actions = await self._handle_approval_event(payload, engine, event_type)
            result["actions"].extend(actions)

        elif event_type == "robot.connected":
            self._handle_robot_event(payload, result)

        elif event_type.startswith("queue."):
            self._handle_queue_event(payload, result)

        else:
            logger.debug(f"Unhandled webhook event type: {event_type}")
            result["actions"].append(f"No handler for event type: {event_type}")

        # Pass raw payload to UiPath client for job tracking
        await engine.uipath_client.handle_webhook(payload)

        return result

    async def _handle_job_event(
        self,
        payload: Dict[str, Any],
        engine: "SimulationEngine",
        event_type: str,
    ) -> list:
        """Handle job completion/fault/stop events."""
        actions = []
        job_data = payload.get("Job", {})
        job_id = str(job_data.get("Id", ""))
        process_name = job_data.get("ReleaseName", "Unknown")
        state = job_data.get("State", "Unknown")

        logger.info(f"Job event: {job_id} ({process_name}) -> {state}")

        success = state == "Successful"

        # Find corresponding job in UiPath client
        job = engine.uipath_client._active_jobs.get(job_id)

        if job:
            job.state = state
            engine.trust_system.on_uipath_result(job, success)
            actions.append(f"Updated job {job_id} state to {state}")

        # Apply simulation effects based on process name
        if success:
            effect = self._apply_job_success_effect(process_name, job_data, engine)
            actions.append(effect)
        else:
            effect = self._apply_job_failure_effect(process_name, job_data, engine)
            actions.append(effect)

        return actions

    async def _handle_approval_event(
        self,
        payload: Dict[str, Any],
        engine: "SimulationEngine",
        event_type: str,
    ) -> list:
        """Handle action item / approval events."""
        actions = []
        action_id = str(payload.get("ActionId", ""))
        action_result = payload.get("Result", {})
        approved = event_type == "action.approved"

        if action_id in engine.uipath_client._pending_approvals:
            del engine.uipath_client._pending_approvals[action_id]
            actions.append(f"Approval {action_id} resolved: {'approved' if approved else 'rejected'}")

        if approved:
            # Release only the workflow tied to this approval. Do not force it to
            # flowing here; the workflow engine will recompute whether the route is
            # actually usable on the next tick.
            workflow_id = payload.get("WorkflowId", "")
            if workflow_id:
                engine.uipath_client._resolved_workflows.add(workflow_id)
                wf = next(
                    (w for w in engine.workflow_engine.workflows if w.id == workflow_id),
                    None,
                )
                if wf:
                    wf.awaitingApproval = False
                actions.append(f"Released approval gate for workflow {workflow_id}")
                from models.state import SimulationEventType
                engine.emit_event(
                    SimulationEventType.approval_granted,
                    {
                        "workflowId": workflow_id,
                        "approvalId": action_id,
                        "approvedVia": "webhook",
                    },
                )
        else:
            engine.trust_system.on_approval_denied()
            actions.append("Trust score adjusted for denied approval")

        return actions

    def _handle_robot_event(
        self, payload: Dict[str, Any], result: Dict[str, Any]
    ) -> None:
        robot_name = payload.get("Robot", {}).get("Name", "Unknown")
        result["actions"].append(f"Robot connected: {robot_name}")
        logger.info(f"Robot connected webhook: {robot_name}")

    def _handle_queue_event(
        self, payload: Dict[str, Any], result: Dict[str, Any]
    ) -> None:
        queue_name = payload.get("QueueName", "Unknown")
        result["actions"].append(f"Queue event for: {queue_name}")

    def _apply_job_success_effect(
        self, process_name: str, job_data: dict, engine: "SimulationEngine"
    ) -> str:
        """Apply positive simulation effects when a UiPath job succeeds."""
        effect_map = {
            "Incident_Escalation": self._effect_incident_escalation_success,
            "Crisis_Response": self._effect_crisis_response_success,
            "Emergency_Staffing": self._effect_emergency_staffing_success,
            "Trust_Recovery_Protocol": self._effect_trust_recovery_success,
            "Notification_Blast": lambda e: "Notifications delivered",
        }

        handler = effect_map.get(process_name)
        if handler:
            return handler(engine)
        return f"Job {process_name} completed successfully"

    def _apply_job_failure_effect(
        self, process_name: str, job_data: dict, engine: "SimulationEngine"
    ) -> str:
        """Apply negative simulation effects when a UiPath job fails."""
        engine.trust_system.automationConfidence = max(
            0.0, engine.trust_system.automationConfidence - 3.0
        )
        return f"Job {process_name} faulted — automation confidence reduced"

    def _effect_incident_escalation_success(self, engine: "SimulationEngine") -> str:
        cloud = next((b for b in engine.buildings if b.type == "cloud_datacenter"), None)
        if not cloud:
            return "Incident escalation successful; no primary infrastructure target found"

        # Escalation is diagnosis + command coordination. It must not resurrect a full
        # outage by itself; actual repair starts after failover/staffing are engaged.
        if not engine.resource_manager.failover_active:
            cloud.throughput = min(100.0, cloud.throughput + 2.0)
            cloud.clamp()
            return "Incident escalation successful; failover/staffing still required for repair"

        high_auton = sum(1 for a in engine.agents if a.autonomyLevel >= 3)
        coordination = max(0.0, (high_auton - 1) / max(1, len(engine.agents) - 1))
        boost = 1.5 * (cloud.staffingLevel / 100.0) + 2.0 * coordination
        cloud.health = min(100.0, cloud.health + boost)
        cloud.clamp()
        return "Incident escalation successful — CloudCore recovery boosted"

    def _effect_crisis_response_success(self, engine: "SimulationEngine") -> str:
        # Boost all degraded buildings slightly
        if not engine.resource_manager.failover_active:
            engine.resource_manager.humanStrain = max(
                0.0, engine.resource_manager.humanStrain - 2.0
            )
            return "Crisis response successful; cascade isolated, repair levers still required"

        high_auton = sum(1 for a in engine.agents if a.autonomyLevel >= 3)
        coordination = max(0.0, (high_auton - 1) / max(1, len(engine.agents) - 1))
        repaired = 0
        for b in engine.buildings:
            if b.health < 60:
                boost = 0.8 * (b.staffingLevel / 100.0) + 1.2 * coordination
                b.health = min(100.0, b.health + boost)
                b.clamp()
                repaired += 1
        return f"Crisis response successful; coordinated repair applied to {repaired} buildings"
        return "Crisis response successful — all buildings boosted"

    def _effect_emergency_staffing_success(self, engine: "SimulationEngine") -> str:
        # Reduce human strain modestly. Staffing automation is a supporting lever, not
        # a full recovery lever.
        engine.resource_manager.humanStrain = max(
            0.0, engine.resource_manager.humanStrain - 8.0
        )
        # Boost staffing on the primary service buildings by TYPE so every scenario
        # gets the same treatment regardless of scenario-specific building IDs.
        for building_type in ("hospital", "pharmacy"):
            b = next((b for b in engine.buildings if b.type == building_type), None)
            if b:
                b.staffingLevel = min(90.0, b.staffingLevel + 8.0)
                b.clamp()
        return "Emergency staffing deployed — strain reduced"

    def _effect_approval_chain_success(self, engine: "SimulationEngine") -> str:
        # Unblock oldest blocked workflow
        from models.workflow import WorkflowStatus
        for wf in engine.workflow_engine.workflows:
            if wf.status == WorkflowStatus.blocked:
                wf.status = WorkflowStatus.flowing
                return f"Approval chain completed — workflow {wf.id} unblocked"
        return "Approval chain completed"

    def _effect_trust_recovery_success(self, engine: "SimulationEngine") -> str:
        engine.trust_system.systemTrust = min(
            100.0, engine.trust_system.systemTrust + 10.0
        )
        engine.trust_system.automationConfidence = min(
            100.0, engine.trust_system.automationConfidence + 5.0
        )
        return "Trust recovery protocol successful — trust and confidence restored"
