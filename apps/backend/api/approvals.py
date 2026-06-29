"""
Human Approval Endpoints.

Surfaces pending approval items from the UiPath client and critical alerts that
need human acknowledgment. Provides approve/reject actions that update engine state
and emit simulation events.
"""
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.state import AlertSeverity, SimulationEventType, UiPathApproval
from models.workflow import WorkflowStatus
from simulation.engine import engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/approvals", tags=["Human Approvals"])


# ─── Request Models ────────────────────────────────────────────────────────────

class ApproveRequest(BaseModel):
    approvedBy: str
    notes: Optional[str] = None


class RejectRequest(BaseModel):
    rejectedBy: str
    reason: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_approval_item(approval_id: str) -> Optional[UiPathApproval]:
    """Look up a pending approval by ID."""
    return engine.uipath_client._pending_approvals.get(approval_id)


def _serialize_approval(approval: UiPathApproval) -> Dict[str, Any]:
    """Serialize a UiPathApproval to a standard response shape."""
    timeout_seconds = 5 * 60  # 5-minute SLA
    return {
        "id": approval.id,
        "title": approval.title,
        "description": approval.description,
        "severity": approval.severity.value,
        "requestedBy": approval.requestedBy,
        "createdAt": approval.createdAt,
        "timeoutAt": approval.createdAt + timeout_seconds,
        "isOverdue": time.time() > (approval.createdAt + timeout_seconds),
        "source": "uipath_action_center",
    }


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/pending")
async def get_pending_approvals() -> Dict[str, Any]:
    """
    Returns the pending approval items from the UiPath Action Center queue.
    Critical alerts are NOT included here (they live in the Alert Feed); only their
    unacknowledged count is reported, so the UI can badge "N in Alert Feed →".
    """
    # Auto-expire approvals past their SLA so the queue can't grow unbounded.
    timeout_seconds = 5 * 60
    now = time.time()
    expired = [
        aid for aid, a in engine.uipath_client._pending_approvals.items()
        if now > a.createdAt + timeout_seconds
    ]
    for aid in expired:
        del engine.uipath_client._pending_approvals[aid]

    # UiPath Action Center approvals — the ONLY thing that belongs in this queue.
    # This modal is a human-in-the-loop *decision* surface, not an alert inbox.
    # Critical alerts are deliberately NOT merged in here: they have no per-workflow
    # dedupe / cooldown / queue cap, and the engine keeps a rolling backlog of up to
    # MAX_ALERTS unacknowledged ones — so surfacing them created an un-clearable
    # treadmill (clear 3, 3 more surface) that was especially brutal in "direct"
    # orchestration mode, where every agent fires its own job and faults pile up fast.
    # Critical alerts live in the Alert Feed; we only report their COUNT here so the
    # UI can badge "N in Alert Feed →" without putting them in the clickable list.
    uipath_items = [
        _serialize_approval(approval)
        for approval in engine.uipath_client._pending_approvals.values()
    ]

    # In Maestro mode, ALSO surface the REAL Action Center tasks the Maestro Case created,
    # so the modal shows genuine human-in-the-loop tasks. Approving one (id "ac-<taskId>")
    # completes it on UiPath and resumes the case. (Additive — simulated approvals still work.)
    if engine.uipath_client.orchestration_mode == "maestro" and engine.uipath_client._configured:
        try:
            for t in await engine.uipath_client.list_action_center_tasks():
                data = t.get("Data") if isinstance(t.get("Data"), dict) else {}
                uipath_items.append({
                    "id": f"ac-{t.get('Id')}",
                    "title": t.get("Title") or "Maestro Case approval",
                    "description": (data.get("description") or data.get("Description")
                                    or "Human-in-the-loop approval from the Maestro Case."),
                    "severity": "critical",
                    "requestedBy": "Maestro Case · Action Center",
                    "createdAt": now,
                    "timeoutAt": now + timeout_seconds,
                    "isOverdue": False,
                    "source": "uipath_action_center",
                })
        except Exception as e:  # never let Action Center hiccups break the modal
            logger.error(f"Could not fetch Action Center tasks: {e}")

    unacked_critical_count = sum(
        1 for a in engine.alerts
        if not a.acknowledged and a.severity == AlertSeverity.critical
    )

    # Sort by createdAt descending (newest first), then by overdue flag
    uipath_items.sort(key=lambda x: (-int(x["isOverdue"]), -x["createdAt"]))

    overdue_count = sum(1 for item in uipath_items if item["isOverdue"])

    return {
        "items": uipath_items,
        "count": len(uipath_items),
        "uipathApprovalCount": len(uipath_items),
        "criticalAlertCount": unacked_critical_count,
        "overdueCount": overdue_count,
        "phase": engine.phase.value,
        "timestamp": time.time(),
    }


@router.post("/{approval_id}/approve")
async def approve_item(approval_id: str, body: ApproveRequest) -> Dict[str, Any]:
    """
    Approve a pending approval item.

    For UiPath Action Center items: marks as granted and resumes the associated workflow.
    For critical alert acknowledgments: marks the alert as acknowledged.
    """
    # Real Action Center task (Maestro Case) — complete it on UiPath to resume the case.
    if approval_id.startswith("ac-"):
        ok = await engine.uipath_client.complete_action_center_task(
            approval_id[3:], approved=True,
            data={"approvedBy": body.approvedBy, "notes": body.notes},
        )
        if not ok:
            raise HTTPException(status_code=502, detail="Failed to complete the Action Center task on UiPath.")
        engine.emit_event(SimulationEventType.approval_granted, {
            "approvalId": approval_id, "approvedBy": body.approvedBy, "notes": body.notes,
            "source": "action_center", "effect": "maestro_case_resumed",
        })
        engine.create_alert(
            severity=AlertSeverity.info,
            message=f"ACTION CENTER: task approved by {body.approvedBy} — Maestro Case resumed",
        )
        return {"success": True, "approvalId": approval_id, "effect": "maestro_case_resumed",
                "approvedBy": body.approvedBy, "timestamp": time.time()}

    # Check UiPath approvals first
    approval = _get_approval_item(approval_id)
    if approval:
        # Remove from pending queue + record the human decision so this workflow never
        # re-gates and VERITAS backs off creating new approvals for a cooldown.
        del engine.uipath_client._pending_approvals[approval_id]
        engine.uipath_client._last_human_decision = time.time()
        if approval.workflowId:
            engine.uipath_client._resolved_workflows.add(approval.workflowId)
            # Resume any workflow that was genuinely paused awaiting this decision.
            wf = next(
                (w for w in engine.workflow_engine.workflows if w.id == approval.workflowId),
                None,
            )
            if wf:
                wf.awaitingApproval = False

        # Emit approval_granted event
        engine.emit_event(
            SimulationEventType.approval_granted,
            {
                "approvalId": approval_id,
                "approvedBy": body.approvedBy,
                "notes": body.notes,
                "title": approval.title,
                "requestedBy": approval.requestedBy,
                "effect": "workflow_resumed",
            },
        )

        # Info alert to confirm approval
        engine.create_alert(
            severity=AlertSeverity.info,
            message=(
                f"APPROVAL GRANTED: '{approval.title}' approved by {body.approvedBy}"
                + (f" — {body.notes}" if body.notes else "")
            ),
        )

        logger.info(
            f"Approval {approval_id} granted by {body.approvedBy}: {approval.title}"
        )

        return {
            "success": True,
            "approvalId": approval_id,
            "title": approval.title,
            "effect": "workflow_resumed",
            "approvedBy": body.approvedBy,
            "timestamp": time.time(),
        }

    # Check if it's a critical alert ID
    alert = next((a for a in engine.alerts if a.id == approval_id), None)
    if alert:
        if alert.acknowledged:
            return {
                "success": True,
                "approvalId": approval_id,
                "effect": "already_acknowledged",
                "timestamp": time.time(),
            }

        alert.acknowledged = True

        engine.emit_event(
            SimulationEventType.approval_granted,
            {
                "approvalId": approval_id,
                "approvedBy": body.approvedBy,
                "notes": body.notes,
                "alertMessage": alert.message[:100],
                "effect": "alert_acknowledged",
            },
        )

        logger.info(
            f"Alert {approval_id} acknowledged by {body.approvedBy}"
        )

        return {
            "success": True,
            "approvalId": approval_id,
            "effect": "alert_acknowledged",
            "approvedBy": body.approvedBy,
            "timestamp": time.time(),
        }

    raise HTTPException(
        status_code=404,
        detail=f"Approval item '{approval_id}' not found in pending queue or active alerts.",
    )


@router.post("/{approval_id}/reject")
async def reject_item(approval_id: str, body: RejectRequest) -> Dict[str, Any]:
    """
    Reject a pending approval item.

    For UiPath Action Center items: marks as rejected and triggers escalation.
    For critical alerts: escalates the alert to the next tier.
    """
    # Real Action Center task (Maestro Case) — complete it with a Reject outcome.
    if approval_id.startswith("ac-"):
        ok = await engine.uipath_client.complete_action_center_task(
            approval_id[3:], approved=False,
            data={"rejectedBy": body.rejectedBy, "reason": body.reason},
        )
        if not ok:
            raise HTTPException(status_code=502, detail="Failed to complete the Action Center task on UiPath.")
        engine.emit_event(SimulationEventType.escalation_triggered, {
            "approvalId": approval_id, "rejectedBy": body.rejectedBy, "reason": body.reason,
            "source": "action_center", "effect": "maestro_case_resumed",
        })
        engine.create_alert(
            severity=AlertSeverity.warning,
            message=f"ACTION CENTER: task rejected by {body.rejectedBy} — {body.reason}",
        )
        return {"success": True, "approvalId": approval_id, "effect": "maestro_case_resumed",
                "rejectedBy": body.rejectedBy, "reason": body.reason, "timestamp": time.time()}

    # Check UiPath approvals first
    approval = _get_approval_item(approval_id)
    if approval:
        # Remove from pending queue + record the human decision (never re-gate this
        # workflow; back off creating new approvals for a cooldown).
        del engine.uipath_client._pending_approvals[approval_id]
        engine.uipath_client._last_human_decision = time.time()
        if approval.workflowId:
            engine.uipath_client._resolved_workflows.add(approval.workflowId)
            # Rejecting a gated workflow escalates it: lift the pause and mark it
            # escalated rather than leaving it silently blocked forever.
            wf = next(
                (w for w in engine.workflow_engine.workflows if w.id == approval.workflowId),
                None,
            )
            if wf:
                wf.awaitingApproval = False
                wf.status = WorkflowStatus.escalated

        # Emit escalation event
        engine.emit_event(
            SimulationEventType.escalation_triggered,
            {
                "approvalId": approval_id,
                "rejectedBy": body.rejectedBy,
                "reason": body.reason,
                "title": approval.title,
                "requestedBy": approval.requestedBy,
                "effect": "workflow_escalated",
            },
        )

        # Warning alert to record rejection
        engine.create_alert(
            severity=AlertSeverity.warning,
            message=(
                f"APPROVAL REJECTED: '{approval.title}' rejected by {body.rejectedBy}. "
                f"Reason: {body.reason}. Escalating to next tier."
            ),
        )

        logger.info(
            f"Approval {approval_id} rejected by {body.rejectedBy}: {approval.title} — {body.reason}"
        )

        return {
            "success": True,
            "approvalId": approval_id,
            "title": approval.title,
            "effect": "workflow_escalated",
            "rejectedBy": body.rejectedBy,
            "reason": body.reason,
            "timestamp": time.time(),
        }

    # Check critical alert
    alert = next((a for a in engine.alerts if a.id == approval_id), None)
    if alert:
        # "Rejecting" an alert = escalate it (create a new higher-priority alert)
        engine.emit_event(
            SimulationEventType.escalation_triggered,
            {
                "originalAlertId": approval_id,
                "escalatedBy": body.rejectedBy,
                "reason": body.reason,
                "originalMessage": alert.message[:100],
                "effect": "alert_escalated",
            },
        )

        # Create an escalation alert
        engine.create_alert(
            severity=AlertSeverity.critical,
            message=(
                f"ESCALATED by {body.rejectedBy}: {alert.message[:80]} — {body.reason}"
            ),
            building_id=alert.buildingId,
            agent_id=alert.agentId,
        )

        # Mark original as acknowledged so it clears from the pending queue
        alert.acknowledged = True

        logger.info(
            f"Alert {approval_id} escalated by {body.rejectedBy}: {body.reason}"
        )

        return {
            "success": True,
            "approvalId": approval_id,
            "effect": "alert_escalated",
            "rejectedBy": body.rejectedBy,
            "reason": body.reason,
            "timestamp": time.time(),
        }

    raise HTTPException(
        status_code=404,
        detail=f"Approval item '{approval_id}' not found in pending queue or active alerts.",
    )


@router.post("/create-mock")
async def create_mock_approval() -> Dict[str, Any]:
    """
    Create a mock pending approval item for demo/testing purposes.
    Useful for showcasing the human-in-the-loop flow without a full incident.
    """
    approval_id = f"action-{uuid.uuid4().hex[:8]}"
    approval = UiPathApproval(
        id=approval_id,
        title="Emergency Medication Protocol Override",
        description=(
            f"VERITAS requires human approval to override standard dosage verification "
            f"protocol during active {engine.phase.value} phase. "
            f"Current stability: {engine.metrics.operationalStability:.0f}%. "
            "This action affects patient medication dispensing at Central Pharmacy. "
            "Approve to grant a 30-minute emergency waiver. Reject to escalate to Pharmacy Director."
        ),
        requestedBy="VERITAS (Compliance Agent)",
        severity=AlertSeverity.critical,
        createdAt=time.time(),
    )

    engine.uipath_client._pending_approvals[approval_id] = approval

    # Emit approval_required event
    engine.emit_event(
        SimulationEventType.approval_required,
        {
            "approvalId": approval_id,
            "title": approval.title,
            "requestedBy": approval.requestedBy,
            "severity": approval.severity.value,
        },
    )

    logger.info(f"Mock approval created: {approval_id}")

    return {
        "created": True,
        "approval": _serialize_approval(approval),
        "timestamp": time.time(),
    }
