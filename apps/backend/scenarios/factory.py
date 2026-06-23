"""
Scenario factory: builds a full ScenarioDefinition from a compact spec.

All scenarios share the same STRUCTURE — 7 building slots (fixed positions, sprite
types, and canonical stats), 5 agent roles, a standard workflow graph, and standard
dependency edges. A scenario spec only supplies the *distinctive* data: per-slot id +
display name + icon, agent names, vocabulary, compliance, processes, and outage presets.

This means a structural change (e.g. building positions) is a ONE-FILE edit here, not
a change across every scenario — and an LLM can produce a spec to create new scenarios.
"""
from typing import Any, Dict, List

from scenarios.base import ScenarioDefinition

# ─── Slot definitions: role -> sprite type, grid position, canonical stats ──────────
# Positions are spread across the 4 quadrants (roads at y9-10 / x15-16).
SLOT_ORDER = ["primary", "secondary", "infra", "comms", "orchestration", "support", "failover"]

SLOT_META: Dict[str, Dict[str, Any]] = {
    "primary":       {"type": "hospital",             "pos": {"x": 2,  "y": 2,  "w": 4, "h": 4}, "throughput": 85, "staffingLevel": 75, "trustLevel": 90, "queueDepth": 12, "recoveryCapacity": 60},
    "secondary":     {"type": "pharmacy",             "pos": {"x": 9,  "y": 2,  "w": 4, "h": 4}, "throughput": 90, "staffingLevel": 80, "trustLevel": 88, "queueDepth": 8,  "recoveryCapacity": 70},
    "infra":         {"type": "cloud_datacenter",     "pos": {"x": 19, "y": 2,  "w": 4, "h": 4}, "throughput": 95, "staffingLevel": 60, "trustLevel": 95, "queueDepth": 0,  "recoveryCapacity": 100},
    "comms":         {"type": "comms_hub",            "pos": {"x": 26, "y": 2,  "w": 4, "h": 4}, "throughput": 88, "staffingLevel": 65, "trustLevel": 92, "queueDepth": 5,  "recoveryCapacity": 80},
    "orchestration": {"type": "orchestration_center", "pos": {"x": 2,  "y": 12, "w": 4, "h": 4}, "throughput": 92, "staffingLevel": 70, "trustLevel": 94, "queueDepth": 3,  "recoveryCapacity": 85},
    "support":       {"type": "staffing_hr",          "pos": {"x": 9,  "y": 12, "w": 4, "h": 4}, "throughput": 78, "staffingLevel": 85, "trustLevel": 80, "queueDepth": 15, "recoveryCapacity": 50},
    "failover":      {"type": "backup_infra",         "pos": {"x": 19, "y": 12, "w": 4, "h": 4}, "throughput": 40, "staffingLevel": 50, "trustLevel": 85, "queueDepth": 0,  "recoveryCapacity": 100},
}

# ─── Agent roles: fixed id + type + defaults; home references a slot role ───────────
AGENT_META: List[Dict[str, Any]] = [
    {"id": "ops_coord",     "type": "operations_coordinator", "autonomyLevel": 2, "trustScore": 85.0, "home": "orchestration", "lastAction": "Monitoring queue depths"},
    {"id": "incident_resp", "type": "incident_response",      "autonomyLevel": 2, "trustScore": 90.0, "home": "infra",         "lastAction": "All systems nominal"},
    {"id": "compliance",    "type": "compliance",             "autonomyLevel": 1, "trustScore": 78.0, "home": "primary",       "lastAction": "Compliance checks passed"},
    {"id": "comms",         "type": "communications",         "autonomyLevel": 2, "trustScore": 82.0, "home": "comms",         "lastAction": "Alerts synchronized"},
    {"id": "exec_strategy", "type": "executive_strategy",     "autonomyLevel": 1, "trustScore": 88.0, "home": "orchestration", "lastAction": "KPIs within targets"},
]

# ─── Workflow graph template: (type, source role, dest role, priority, risk, progress) ─
_WF = [
    ("ehr_record", "primary", "secondary", "high", 0.15, 0.10),
    ("ehr_record", "primary", "secondary", "high", 0.20, 0.40),
    ("ehr_record", "primary", "secondary", "medium", 0.10, 0.70),
    ("ehr_record", "primary", "secondary", "critical", 0.30, 0.05),
    ("prescription", "secondary", "primary", "high", 0.25, 0.20),
    ("prescription", "secondary", "primary", "critical", 0.35, 0.55),
    ("prescription", "secondary", "primary", "medium", 0.15, 0.80),
    ("comm_packet", "comms", "primary", "medium", 0.05, 0.30),
    ("comm_packet", "comms", "primary", "low", 0.05, 0.60),
    ("comm_packet", "comms", "secondary", "low", 0.05, 0.15),
    ("comm_packet", "comms", "orchestration", "medium", 0.08, 0.45),
    ("approval_request", "primary", "orchestration", "high", 0.60, 0.25),
    ("approval_request", "secondary", "orchestration", "medium", 0.55, 0.50),
    ("staffing_request", "primary", "support", "medium", 0.10, 0.35),
    ("staffing_request", "primary", "support", "high", 0.20, 0.65),
    ("staffing_request", "secondary", "support", "low", 0.10, 0.10),
    ("escalation", "orchestration", "infra", "high", 0.40, 0.20),
    ("failover_cmd", "failover", "infra", "low", 0.05, 0.90),
    ("ehr_record", "primary", "orchestration", "medium", 0.18, 0.50),
    ("comm_packet", "comms", "support", "low", 0.05, 0.75),
    ("prescription", "secondary", "orchestration", "high", 0.28, 0.12),
    ("approval_request", "primary", "support", "medium", 0.45, 0.38),
    ("ehr_record", "primary", "secondary", "high", 0.22, 0.85),
    ("comm_packet", "comms", "primary", "medium", 0.06, 0.22),
]

# ─── Dependency edges template (source role, dest role) ─────────────────────────────
_EDGES = [
    ("primary", "infra"), ("primary", "orchestration"), ("primary", "support"),
    ("secondary", "infra"), ("secondary", "primary"), ("secondary", "orchestration"),
    ("comms", "infra"), ("orchestration", "infra"), ("orchestration", "comms"),
    ("support", "comms"),
]


def build_scenario(spec: Dict[str, Any]) -> ScenarioDefinition:
    """Expand a compact spec into a full ScenarioDefinition using shared structure."""
    slots = spec["slots"]                 # role -> {id, name, icon}
    rid = {role: slots[role]["id"] for role in SLOT_ORDER}   # role -> scenario building id

    buildings = []
    for role in SLOT_ORDER:
        meta = SLOT_META[role]
        s = slots[role]
        # dependencies = edges originating from this role
        deps = [rid[d] for (srole, d) in _EDGES if srole == role]
        buildings.append({
            "id": s["id"], "type": meta["type"], "name": s["name"], "icon": s.get("icon", ""),
            "pos": dict(meta["pos"]), "status": "operational", "health": 100.0,
            "throughput": float(meta["throughput"]), "staffingLevel": float(meta["staffingLevel"]),
            "trustLevel": float(meta["trustLevel"]), "dependencies": deps,
            "queueDepth": meta["queueDepth"], "recoveryCapacity": float(meta["recoveryCapacity"]),
        })

    agents = []
    for a in AGENT_META:
        agents.append({
            "id": a["id"], "type": a["type"], "name": spec["agents"][a["id"]],
            "autonomyLevel": a["autonomyLevel"], "trustScore": a["trustScore"], "status": "idle",
            "lastAction": a["lastAction"], "lastActionAt": 0.0, "actionsThisTick": 0,
            "currentBuildingId": rid[a["home"]], "targetBuildingId": None,
        })

    workflows = []
    for i, (wtype, src, dst, prio, risk, prog) in enumerate(_WF, start=1):
        workflows.append({
            "id": f"wf-{i:03d}", "type": wtype, "sourceId": rid[src], "destId": rid[dst],
            "priority": prio, "status": "flowing", "automationEligible": True,
            "risk": risk, "progress": prog,
        })

    edges = [(rid[s], rid[d]) for (s, d) in _EDGES]

    return ScenarioDefinition(
        id=spec["id"], name=spec["name"], tagline=spec["tagline"], description=spec["description"],
        industry=spec["industry"], icon=spec["icon"], color=spec["color"],
        buildings=buildings, agents=agents, workflows=workflows, dependency_edges=edges,
        vocabulary=spec.get("vocabulary", {}),
        compliance_frameworks=spec.get("compliance_frameworks", []),
        industry_context=spec.get("industry_context", ""),
        uipath_processes=spec.get("uipath_processes", []),
        outage_presets=spec.get("outage_presets", []),
    )
