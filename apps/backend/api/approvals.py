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


def _serialize_critical_alert(alert) -> Dict[str, Any]:
    """Convert a critical alert to an approval-like item for human acknowledgment."""
    timeout_seconds = 3 * 60  # 3-minute acknowledgment window for critical alerts
    return {
        "id": alert.id,
        "title": f"Critical Alert: {alert.message[:80]}",
        "description": alert.message,
        "severity": alert.severity.value,
        "requestedBy": "SENTINEL (Incident Response)",
        "createdAt": alert.timestamp,
        "timeoutAt": alert.timestamp + timeout_seconds,
        "isOverdue": time.time() > (alert.timestamp + timeout_seconds),
        "buildingId": alert.buildingId,
        "agentId": alert.agentId,
        "source": "critical_alert",
    }


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/pending")
async def get_pending_approvals() -> Dict[str, Any]:
    """
    Returns all pending approval items from the UiPath Action Center queue,
    plus any unacknowledged critical-severity alerts that need human attention.
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

    # UiPath Action Center approvals
    uipath_items = [
        _serialize_approval(approval)
        for approval in engine.uipath_client._pending_approvals.values()
    ]

    # Critical unacknowledged alerts as acknowledgment items
    critical_alert_items = [
        _serialize_critical_alert(alert)
        for alert in engine.alerts
        if not alert.acknowledged and alert.severity == AlertSeverity.critical
    ]

    all_items = uipath_items + critical_alert_items

    # Sort by createdAt descending (newest first), then by overdue flag
    all_items.sort(key=lambda x: (-int(x["isOverdue"]), -x["createdAt"]))

    overdue_count = sum(1 for item in all_items if item["isOverdue"])

    return {
        "items": all_items,
        "count": len(all_items),
        "uipathApprovalCount": len(uipath_items),
        "criticalAlertCount": len(critical_alert_items),
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
    # Check UiPath approvals first
    approval = _get_approval_item(approval_id)
    if approval:
        # Remove from pending queue
        del engine.uipath_client._pending_approvals[approval_id]

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
    # Check UiPath approvals first
    approval = _get_approval_item(approval_id)
    if approval:
        # Remove from pending queue
        del engine.uipath_client._pending_approvals[approval_id]

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
