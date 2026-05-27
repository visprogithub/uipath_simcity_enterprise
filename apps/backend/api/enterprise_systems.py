"""
Enterprise API Workflow Simulation Endpoints.

Simulates real enterprise systems (EHR, Pharmacy, Staffing, Infrastructure)
that UiPath would integrate with. All data is driven by the simulation engine state.
"""
import time
import uuid
import logging
import random
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from pydantic import BaseModel

from models.building import BuildingStatus
from models.state import AlertSeverity, GamePhase, SimulationEventType
from simulation.engine import engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/enterprise", tags=["Enterprise Systems"])


# ─── Request Models ────────────────────────────────────────────────────────────

class OutageNotification(BaseModel):
    system_id: str
    severity: str  # "low" | "medium" | "high" | "critical"
    message: str
    affected_services: List[str] = []


class EscalationNotification(BaseModel):
    escalation_id: str
    priority: str  # "p1" | "p2" | "p3" | "p4"
    assigned_to: str
    message: str


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _building_by_id(building_id: str):
    return next((b for b in engine.buildings if b.id == building_id), None)


def _is_crisis() -> bool:
    return engine.phase in (GamePhase.crisis, GamePhase.collapsed)


def _is_degraded() -> bool:
    return engine.phase in (GamePhase.degrading, GamePhase.crisis, GamePhase.collapsed)


def _jitter(base: float, spread: float = 5.0) -> float:
    """Add small random jitter to a value."""
    return round(max(0.0, min(100.0, base + random.uniform(-spread, spread))), 1)


# ─── EHR Availability ─────────────────────────────────────────────────────────

@router.get("/ehr/availability")
async def get_ehr_availability() -> Dict[str, Any]:
    """
    Returns EHR system availability status.
    Availability drops significantly during crisis phases.
    """
    hospital = _building_by_id("hospital")
    datacenter = _building_by_id("cloud_datacenter")

    # Base availability driven by hospital and datacenter health
    hosp_health = hospital.health if hospital else 100.0
    dc_health = datacenter.health if datacenter else 100.0
    base_availability = (hosp_health * 0.6 + dc_health * 0.4)

    # Crisis adjustment
    if _is_crisis():
        base_availability = min(base_availability, random.uniform(40.0, 60.0))
    elif engine.phase == GamePhase.degrading:
        base_availability = min(base_availability, random.uniform(65.0, 80.0))

    active_sessions = max(0, int(base_availability * 0.8 + random.randint(0, 20)))

    # Pending records spike in crisis
    base_pending = hospital.queueDepth if hospital else 5
    if _is_crisis():
        pending_records = base_pending * random.randint(8, 15)
    elif _is_degraded():
        pending_records = base_pending * random.randint(3, 6)
    else:
        pending_records = base_pending + random.randint(0, 10)

    # Degraded modules
    degraded_modules: List[str] = []
    if hospital and hospital.health < 70:
        degraded_modules.append("patient-records-sync")
    if datacenter and datacenter.health < 60:
        degraded_modules.extend(["real-time-alerts", "audit-log-export"])
    if _is_crisis():
        for mod in ["medication-reconciliation", "lab-results-integration"]:
            if mod not in degraded_modules:
                degraded_modules.append(mod)

    status = "operational"
    if base_availability < 40:
        status = "critical"
    elif base_availability < 70:
        status = "degraded"

    return {
        "systemId": "EHR-MAESTRO-001",
        "status": status,
        "availability_pct": round(base_availability, 1),
        "active_sessions": active_sessions,
        "pending_records": pending_records,
        "last_sync": time.time() - random.randint(5, 60),
        "degraded_modules": degraded_modules,
        "phase_context": engine.phase.value,
        "timestamp": time.time(),
    }


# ─── Pharmacy Inventory ────────────────────────────────────────────────────────

@router.get("/pharmacy/inventory")
async def get_pharmacy_inventory() -> Dict[str, Any]:
    """
    Pharmacy inventory and fulfillment status.
    Fill rate drops and critical shortages appear during crisis/collapsed phases.
    """
    pharmacy = _building_by_id("pharmacy")
    pharm_health = pharmacy.health if pharmacy else 100.0
    pharm_throughput = pharmacy.throughput if pharmacy else 90.0

    base_fill_rate = (pharm_health * 0.5 + pharm_throughput * 0.5)

    if engine.phase == GamePhase.collapsed:
        base_fill_rate = min(base_fill_rate, random.uniform(15.0, 35.0))
    elif engine.phase == GamePhase.crisis:
        base_fill_rate = min(base_fill_rate, random.uniform(35.0, 55.0))
    elif engine.phase == GamePhase.degrading:
        base_fill_rate = min(base_fill_rate, random.uniform(60.0, 78.0))

    queue_depth = pharmacy.queueDepth if pharmacy else 8
    if _is_crisis():
        queue_depth = queue_depth * random.randint(5, 12)
    elif _is_degraded():
        queue_depth = queue_depth * random.randint(2, 4)

    processing_time_ms = int(200 + (100 - base_fill_rate) * 30 + random.randint(-50, 100))

    # Critical shortages appear when things are bad
    critical_shortages: List[str] = []
    if engine.phase == GamePhase.collapsed:
        critical_shortages = [
            "Epinephrine 1mg/mL",
            "Norepinephrine Bitartrate",
            "Propofol 200mg/20mL",
            "Fentanyl 250mcg/5mL",
        ]
    elif engine.phase == GamePhase.crisis:
        if pharm_health < 50:
            critical_shortages = ["Epinephrine 1mg/mL", "Norepinephrine Bitartrate"]
        elif pharm_health < 70:
            critical_shortages = ["Propofol 200mg/20mL"]
    elif engine.phase == GamePhase.degrading and pharm_health < 60:
        critical_shortages = ["Epinephrine 1mg/mL"]

    status = "operational"
    if base_fill_rate < 40 or len(critical_shortages) >= 3:
        status = "critical"
    elif base_fill_rate < 70 or len(critical_shortages) >= 1:
        status = "degraded"

    return {
        "systemId": "PHARM-CENTRAL-001",
        "status": status,
        "fill_rate_pct": round(base_fill_rate, 1),
        "queue_depth": max(0, queue_depth),
        "critical_shortages": critical_shortages,
        "processing_time_ms": max(100, processing_time_ms),
        "last_restock": time.time() - random.randint(1800, 7200),
        "phase_context": engine.phase.value,
        "timestamp": time.time(),
    }


# ─── Staffing Status ───────────────────────────────────────────────────────────

@router.get("/staffing/status")
async def get_staffing_status() -> Dict[str, Any]:
    """
    On-call staff availability from staffing DB.
    Driven by engine.metrics.humanStrain.
    """
    staffing_bldg = _building_by_id("staffing_hr")
    hospital = _building_by_id("hospital")

    human_strain = engine.metrics.humanStrain  # 0–100, higher = more strained
    base_capacity = 100.0 - human_strain

    # Each department's available vs capacity
    hosp_staffing = hospital.staffingLevel if hospital else 75.0
    hr_staffing = staffing_bldg.staffingLevel if staffing_bldg else 85.0

    def _staff_count(base_staffing: float, max_staff: int) -> int:
        return max(1, int(base_staffing / 100.0 * max_staff))

    departments = [
        {
            "name": "Emergency Medicine",
            "available": _staff_count(max(0, hosp_staffing - human_strain * 0.3), 24),
            "capacity": 24,
            "on_break": random.randint(1, 3),
        },
        {
            "name": "Intensive Care Unit",
            "available": _staff_count(max(0, hosp_staffing - human_strain * 0.25), 18),
            "capacity": 18,
            "on_break": random.randint(0, 2),
        },
        {
            "name": "Pharmacy Operations",
            "available": _staff_count(
                max(0, (staffing_bldg.staffingLevel if staffing_bldg else 80) - human_strain * 0.2), 12
            ),
            "capacity": 12,
            "on_break": random.randint(0, 2),
        },
        {
            "name": "IT Infrastructure",
            "available": _staff_count(max(0, hr_staffing - human_strain * 0.15), 8),
            "capacity": 8,
            "on_break": random.randint(0, 1),
        },
        {
            "name": "Administrative",
            "available": _staff_count(max(0, hr_staffing - human_strain * 0.1), 16),
            "capacity": 16,
            "on_break": random.randint(1, 3),
        },
    ]

    available_staff = sum(d["available"] for d in departments)
    total_capacity = sum(d["capacity"] for d in departments)
    on_call_staff = max(0, int((100.0 - human_strain) / 100.0 * 15))

    overload_threshold = 85  # % capacity at which overload triggers
    current_load_pct = round((1 - available_staff / max(1, total_capacity)) * 100, 1)

    if human_strain >= 80:
        alert_level = "critical"
    elif human_strain >= 60:
        alert_level = "warning"
    elif human_strain >= 35:
        alert_level = "elevated"
    else:
        alert_level = "normal"

    return {
        "systemId": "STAFFING-OPS-001",
        "available_staff": available_staff,
        "total_capacity": total_capacity,
        "on_call_staff": on_call_staff,
        "current_load_pct": current_load_pct,
        "overload_threshold": overload_threshold,
        "departments": departments,
        "alert_level": alert_level,
        "human_strain": round(human_strain, 1),
        "phase_context": engine.phase.value,
        "timestamp": time.time(),
    }


# ─── Infrastructure Status ─────────────────────────────────────────────────────

@router.get("/infrastructure/status")
async def get_infrastructure_status() -> Dict[str, Any]:
    """
    Data center and cloud infrastructure health.
    Driven by cloud_datacenter and backup_infra buildings.
    """
    datacenter = _building_by_id("cloud_datacenter")
    backup = _building_by_id("backup_infra")
    comms = _building_by_id("comms_hub")
    orchestration = _building_by_id("orchestration_center")

    def _region_from_building(
        region_id: str,
        region_name: str,
        building,
        is_primary: bool = True,
    ) -> Dict[str, Any]:
        if building is None:
            return {
                "id": region_id,
                "name": region_name,
                "status": "unknown",
                "latency_ms": 999,
                "load_pct": 0.0,
                "is_primary": is_primary,
            }
        health = building.health
        throughput = building.throughput

        if health >= 70:
            region_status = "healthy"
        elif health >= 40:
            region_status = "degraded"
        elif health >= 15:
            region_status = "critical"
        else:
            region_status = "offline"

        # Latency inversely related to health
        base_latency = 20 if is_primary else 35
        latency = int(base_latency + (100 - health) * 2.5 + random.randint(-5, 20))
        load_pct = round(100.0 - (throughput * 0.8) + random.uniform(-3, 3), 1)
        load_pct = max(0.0, min(100.0, load_pct))

        return {
            "id": region_id,
            "name": region_name,
            "status": region_status,
            "latency_ms": max(5, latency),
            "load_pct": load_pct,
            "is_primary": is_primary,
            "health": round(health, 1),
        }

    regions = [
        _region_from_building("us-east-1", "US East (Primary)", datacenter, is_primary=True),
        _region_from_building("us-west-2", "US West (Backup)", backup, is_primary=False),
        _region_from_building("eu-west-1", "EU West (Comms)", comms, is_primary=False),
        _region_from_building(
            "maestro-orch", "Maestro Orchestration", orchestration, is_primary=False
        ),
    ]

    healthy_regions = [r for r in regions if r["status"] == "healthy"]
    global_health_pct = round(len(healthy_regions) / len(regions) * 100, 1)

    # Use datacenter and backup health for global
    dc_health = datacenter.health if datacenter else 50.0
    backup_health = backup.health if backup else 50.0
    global_health_pct = round((dc_health * 0.6 + backup_health * 0.4), 1)

    # Active incidents from current alerts
    active_incidents = []
    for alert in engine.alerts[-10:]:
        if not alert.acknowledged and alert.severity.value in ("critical", "warning"):
            active_incidents.append({
                "id": alert.id,
                "severity": alert.severity.value,
                "summary": alert.message[:120],
                "buildingId": alert.buildingId,
                "timestamp": alert.timestamp,
            })

    return {
        "systemId": "INFRA-CLOUD-001",
        "regions": regions,
        "global_health_pct": global_health_pct,
        "active_incidents": active_incidents[:5],
        "phase_context": engine.phase.value,
        "timestamp": time.time(),
    }


# ─── Outage Notification ───────────────────────────────────────────────────────

@router.post("/outage/notify")
async def notify_outage(notification: OutageNotification) -> Dict[str, Any]:
    """
    Receives an outage notification from an external monitoring system.
    Matches system_id to building type and triggers the appropriate simulation outage.
    """
    notification_id = f"notif-{uuid.uuid4().hex[:8]}"

    # Map system_id keywords to building ids
    system_to_building = {
        "ehr": "hospital",
        "hospital": "hospital",
        "pharmacy": "pharmacy",
        "pharm": "pharmacy",
        "datacenter": "cloud_datacenter",
        "cloud": "cloud_datacenter",
        "dc": "cloud_datacenter",
        "comms": "comms_hub",
        "communications": "comms_hub",
        "orchestration": "orchestration_center",
        "maestro": "orchestration_center",
        "staffing": "staffing_hr",
        "hr": "staffing_hr",
        "backup": "backup_infra",
        "failover": "backup_infra",
    }

    # Find matching building
    matched_building_id = None
    sid_lower = notification.system_id.lower()
    for keyword, building_id in system_to_building.items():
        if keyword in sid_lower:
            matched_building_id = building_id
            break

    actions_triggered: List[str] = []

    if matched_building_id:
        building = _building_by_id(matched_building_id)
        if building:
            # Apply severity-based health reduction
            severity_map = {
                "critical": 0.0,
                "high": 20.0,
                "medium": 45.0,
                "low": 65.0,
            }
            target_health = severity_map.get(notification.severity.lower(), 50.0)
            if building.health > target_health:
                building.health = target_health
                building.clamp()
                actions_triggered.append(
                    f"Applied {notification.severity} outage to {building.name}"
                )

            # Create alert
            sev = AlertSeverity.critical if notification.severity in ("critical", "high") else AlertSeverity.warning
            engine.create_alert(
                severity=sev,
                message=f"EXTERNAL NOTIFICATION [{notification.system_id}]: {notification.message}",
                building_id=matched_building_id,
            )
            actions_triggered.append(f"Alert created for building {matched_building_id}")

            # Emit event
            engine.emit_event(
                SimulationEventType.outage_started,
                {
                    "source": "external_notification",
                    "notificationId": notification_id,
                    "systemId": notification.system_id,
                    "severity": notification.severity,
                    "buildingId": matched_building_id,
                    "affectedServices": notification.affected_services,
                },
            )
            actions_triggered.append("Simulation event emitted")

    # Fire Integration Service API Trigger so the UiPath outage-notification workflow runs
    import os
    trigger_slug = os.getenv("UIPATH_TRIGGER_OUTAGE_SLUG", "outage-notification")
    uipath_result = await engine.uipath_client.trigger_api_workflow(
        trigger_slug,
        {
            "notificationId": notification_id,
            "systemId": notification.system_id,
            "severity": notification.severity,
            "matchedBuildingId": matched_building_id,
            "affectedServices": notification.affected_services,
            "message": notification.message,
        },
    )
    if uipath_result:
        actions_triggered.append(
            f"UiPath API Trigger '{trigger_slug}' fired"
            + (" (simulated)" if uipath_result.get("simulated") else "")
        )

    logger.info(
        f"Outage notification received: {notification.system_id} "
        f"severity={notification.severity} -> building={matched_building_id}"
    )

    return {
        "notificationId": notification_id,
        "acknowledged": True,
        "matchedBuildingId": matched_building_id,
        "actions_triggered": actions_triggered,
        "uipathTriggerResult": uipath_result,
        "timestamp": time.time(),
    }


# ─── Escalation Notification ───────────────────────────────────────────────────

@router.post("/escalation/notify")
async def notify_escalation(notification: EscalationNotification) -> Dict[str, Any]:
    """
    Receives an escalation notification and adds an alert to the engine.
    """
    priority_to_severity = {
        "p1": AlertSeverity.critical,
        "p2": AlertSeverity.critical,
        "p3": AlertSeverity.warning,
        "p4": AlertSeverity.info,
    }
    severity = priority_to_severity.get(notification.priority.lower(), AlertSeverity.warning)

    alert = engine.create_alert(
        severity=severity,
        message=(
            f"ESCALATION [{notification.escalation_id}] "
            f"→ {notification.assigned_to}: {notification.message}"
        ),
    )

    engine.emit_event(
        SimulationEventType.escalation_triggered,
        {
            "escalationId": notification.escalation_id,
            "priority": notification.priority,
            "assignedTo": notification.assigned_to,
            "message": notification.message,
            "alertId": alert.id,
        },
    )

    # Fire Integration Service API Trigger for escalation
    import os
    trigger_slug = os.getenv("UIPATH_TRIGGER_ESCALATION_SLUG", "escalation-notify")
    uipath_result = await engine.uipath_client.trigger_api_workflow(
        trigger_slug,
        {
            "escalationId": notification.escalation_id,
            "priority": notification.priority,
            "assignedTo": notification.assigned_to,
            "message": notification.message,
            "alertId": alert.id,
        },
    )

    logger.info(
        f"Escalation received: {notification.escalation_id} "
        f"priority={notification.priority} assigned_to={notification.assigned_to}"
    )

    return {
        "received": True,
        "alertId": alert.id,
        "severity": severity.value,
        "uipathTriggerResult": uipath_result,
        "timestamp": time.time(),
    }
