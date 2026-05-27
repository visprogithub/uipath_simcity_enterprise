"""
Compliance Agent (VERITAS):
- Enforces approval requirements for high-risk workflows
- At autonomy 0-1: blocks all high-risk workflows, creates approval_request
- At autonomy 2+: auto-approves routine workflows, escalates critical
"""
import logging
import uuid
from typing import TYPE_CHECKING

from agents.base_agent import BaseAgent
from models.agent import Agent, AgentStatus
from models.state import AlertSeverity, SimulationEventType, UiPathApproval
from models.workflow import WorkflowPriority, WorkflowStatus, WorkflowType

if TYPE_CHECKING:
    from simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)


class ComplianceAgent(BaseAgent):
    def __init__(self, agent_model: Agent) -> None:
        super().__init__(agent_model)
        self._audit_trail: list = []
        self._last_approval_tick: int = -5

    async def decide(self, engine: "SimulationEngine") -> None:
        self.reset_tick_actions()
        self.set_analyzing()

        workflows = engine.workflow_engine.workflows
        tick = engine.tick_count
        acted = False

        # ─── Process high-risk workflows ──────────────────────────────────
        high_risk_wfs = [
            w for w in workflows
            if w.risk > 0.7 and w.status not in (WorkflowStatus.failed, WorkflowStatus.blocked)
        ]

        for wf in high_risk_wfs[:2]:  # handle up to 2 per tick
            if not self.has_action_budget():
                break

            if not self.can_act_autonomously(2):
                # Block the workflow and create approval request
                wf.status = WorkflowStatus.blocked
                self.record_action(
                    f"VERITAS blocked high-risk workflow {wf.id} "
                    f"(risk={wf.risk:.2f}) — approval required"
                )

                # Create a pending approval in UiPath
                if (tick - self._last_approval_tick) >= 5:
                    self._last_approval_tick = tick
                    approval = UiPathApproval(
                        id=f"appr-{uuid.uuid4().hex[:8]}",
                        title=f"Approve {wf.type.value.replace('_', ' ').title()}",
                        description=(
                            f"High-risk workflow requires approval. "
                            f"Risk level: {wf.risk:.2f}. "
                            f"Route: {wf.sourceId} → {wf.destId}. "
                            f"Priority: {wf.priority.value}"
                        ),
                        requestedBy=self.model.id,
                        severity=AlertSeverity.warning if wf.priority != WorkflowPriority.critical else AlertSeverity.critical,
                        createdAt=__import__("time").time(),
                    )
                    engine.uipath_client._pending_approvals[approval.id] = approval

                    # Trigger UiPath Approval_Chain job
                    job = await engine.uipath_client.start_job(
                        "Approval_Chain",
                        {
                            "workflowId": wf.id,
                            "workflowType": wf.type.value,
                            "risk": wf.risk,
                            "priority": wf.priority.value,
                            "approvalId": approval.id,
                        },
                    )
                    if job:
                        wf.uipathJobId = job.id
                        self.emit_event(
                            engine,
                            SimulationEventType.approval_required,
                            {
                                "agentId": self.model.id,
                                "workflowId": wf.id,
                                "approvalId": approval.id,
                                "risk": wf.risk,
                            },
                        )
                        self.emit_event(
                            engine,
                            SimulationEventType.uipath_job_started,
                            {
                                "agentId": self.model.id,
                                "processName": "Approval_Chain",
                                "jobId": job.id,
                            },
                        )

                self.create_alert(
                    engine,
                    AlertSeverity.warning,
                    f"VERITAS: Workflow {wf.id} blocked pending approval "
                    f"(risk: {wf.risk:.2f}, type: {wf.type.value})",
                    workflow_id=wf.id,
                )
                acted = True

            else:
                # Autonomy >= 2: auto-approve routine, escalate critical
                if wf.priority == WorkflowPriority.critical:
                    # Still escalate critical ones
                    self.create_alert(
                        engine,
                        AlertSeverity.critical,
                        f"VERITAS: ESCALATING critical high-risk workflow {wf.id} "
                        f"(risk={wf.risk:.2f}) for executive review",
                        workflow_id=wf.id,
                    )
                    wf.status = WorkflowStatus.escalated
                    self.record_action(
                        f"Escalated critical workflow {wf.id} (risk={wf.risk:.2f})"
                    )
                    self.emit_event(
                        engine,
                        SimulationEventType.escalation_triggered,
                        {
                            "agentId": self.model.id,
                            "workflowId": wf.id,
                            "reason": "high_risk_critical",
                        },
                    )
                else:
                    # Auto-approve routine high-risk workflows
                    self._audit_trail.append({
                        "tick": tick,
                        "workflowId": wf.id,
                        "action": "auto_approved",
                        "risk": wf.risk,
                    })
                    self.record_action(
                        f"Auto-approved routine workflow {wf.id} (risk={wf.risk:.2f})"
                    )
                    self.emit_event(
                        engine,
                        SimulationEventType.approval_granted,
                        {
                            "agentId": self.model.id,
                            "workflowId": wf.id,
                            "method": "auto_approve",
                        },
                    )
                    engine.trust_system.on_agent_action(self.model, True)

                acted = True

        # ─── Trim audit trail ──────────────────────────────────────────────
        if len(self._audit_trail) > 200:
            self._audit_trail = self._audit_trail[-100:]

        if not acted:
            self.set_idle("Compliance checks passed — monitoring workflow risks")
        else:
            self.set_status(AgentStatus.idle)
