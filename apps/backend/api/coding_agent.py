"""
Coding Agent Endpoint — Bonus Feature.

Dynamically generates UiPath XAML workflows, simulation entity definitions, and workflow
diagnostics from the current simulation context. Generation runs on the UiPath robot via
the 'coding_gen' coded agent (UiPath LLM gateway). No fallback — failures surface as HTTP errors.
"""
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.building import BuildingStatus
from models.state import GamePhase
from simulation.engine import engine
from orchestration.agent_invoker import invoke_agent_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/coding-agent", tags=["Coding Agent"])

# ─── Request Models ────────────────────────────────────────────────────────────

class GenerateWorkflowRequest(BaseModel):
    processType: str  # "incident_response" | "approval_chain" | "crisis_response" | "staffing" | "trust_recovery"
    context: Dict[str, Any] = {}


class GenerateEntitiesRequest(BaseModel):
    entityType: str = "building"  # "building" | "agent" | "workflow_type"
    count: int = 1
    context: Dict[str, Any] = {}


class DebugWorkflowRequest(BaseModel):
    workflow_id: str
    error_description: str


# ─── Simulation Context Builder ───────────────────────────────────────────────

def _build_simulation_context() -> Dict[str, Any]:
    """Snapshot the current simulation state for prompt injection."""
    degraded_buildings = [
        {
            "id": b.id,
            "name": b.name,
            "status": b.status.value,
            "health": round(b.health, 1),
            "type": b.type.value,
        }
        for b in engine.buildings
        if b.status in (BuildingStatus.degraded, BuildingStatus.critical, BuildingStatus.offline)
    ]

    metrics = engine.metrics
    return {
        "phase": engine.phase.value,
        "tick": engine.tick_count,
        "metrics": {
            "operationalStability": round(metrics.operationalStability, 1),
            "humanStrain": round(metrics.humanStrain, 1),
            "automationConfidence": round(metrics.automationConfidence, 1),
            "serviceAvailability": round(metrics.serviceAvailability, 1),
            "systemTrust": round(metrics.systemTrust, 1),
            "resourceCapacity": round(metrics.resourceCapacity, 1),
        },
        "degraded_buildings": degraded_buildings,
        "active_alerts_count": len([a for a in engine.alerts if not a.acknowledged]),
        "critical_alerts_count": len(
            [a for a in engine.alerts if not a.acknowledged and a.severity.value == "critical"]
        ),
    }


def _build_workflow_prompt(process_type: str, sim_ctx: Dict[str, Any]) -> str:
    """Build the Claude prompt for XAML workflow generation."""
    degraded_summary = (
        ", ".join(f"{b['name']} ({b['status']} {b['health']}%)" for b in sim_ctx["degraded_buildings"])
        or "None"
    )

    process_descriptions = {
        "incident_response": (
            "an automated incident response workflow that detects building health degradation, "
            "triggers appropriate recovery playbooks, notifies stakeholders, and logs actions "
            "to the compliance audit trail"
        ),
        "approval_chain": (
            "a human-in-the-loop approval chain workflow that routes high-risk medical or "
            "infrastructure decisions to the appropriate approver via UiPath Action Center, "
            "with timeout escalation logic"
        ),
        "crisis_response": (
            "a crisis response coordination workflow that orchestrates multi-agent actions, "
            "activates failover infrastructure, manages staffing emergency protocols, and "
            "provides real-time SITREP generation"
        ),
        "staffing": (
            "a staffing optimization workflow that analyzes department capacity, identifies "
            "understaffed areas, redistributes available staff, and requests additional resources "
            "when human strain exceeds threshold"
        ),
        "trust_recovery": (
            "a system trust recovery workflow that monitors automation confidence metrics, "
            "implements graduated re-engagement of automated processes after an incident, "
            "and validates system behavior before restoring full autonomy"
        ),
    }
    process_desc = process_descriptions.get(process_type, "a general healthcare enterprise automation workflow")

    return f"""You are a UiPath Studio expert generating production-ready XAML workflows for a healthcare enterprise simulation called Maestro City.

Current simulation context:
- Phase: {sim_ctx['phase']}
- Operational Stability: {sim_ctx['metrics']['operationalStability']}%
- Human Strain: {sim_ctx['metrics']['humanStrain']}%
- Service Availability: {sim_ctx['metrics']['serviceAvailability']}%
- System Trust: {sim_ctx['metrics']['systemTrust']}%
- Degraded/Offline Buildings: {degraded_summary}
- Active Critical Alerts: {sim_ctx['critical_alerts_count']}

Generate a complete, valid UiPath XAML workflow for: {process_desc}

The XAML must:
1. Use proper UiPath Studio namespaces:
   - xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
   - xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
   - xmlns:ui="http://schemas.uipath.com/workflow/activities"
   - xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
   - xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
2. Include Variables section with relevant typed arguments
3. Have a descriptive DisplayName and sap2010:WorkflowViewState.IdRef annotations
4. Include sequence activities with meaningful DisplayNames reflecting the healthcare context
5. Contain at least 8–12 meaningful activity nodes (Assign, If, InvokeWorkflowFile, WriteLine, etc.)
6. Reference the current simulation phase ({sim_ctx['phase']}) and degraded systems in activity names

Return ONLY the XAML — no markdown fences, no explanation."""


def _build_entities_prompt(entity_type: str, count: int, sim_ctx: Dict[str, Any]) -> str:
    """Build the Claude prompt for entity definition generation."""
    return f"""You are a simulation designer for Maestro City, a healthcare enterprise simulation powered by UiPath automation.

Current simulation phase: {sim_ctx['phase']}
Current metrics: stability={sim_ctx['metrics']['operationalStability']}%, strain={sim_ctx['metrics']['humanStrain']}%

Generate {count} new {entity_type} definition(s) in JSON format that would fit naturally into the Maestro City simulation.

For entity type '{entity_type}':
- building: Include id, type (new custom type), name, description, dependencies (list of existing building IDs), healthImpactOnDependents, recoveryCapacity, staffingRequirement
- agent: Include id, type, name, role, autonomyLevel, specialization, triggerConditions, tools list
- workflow_type: Include id, name, description, typicalRisk, automationEligibility, complianceRequirements

Return a JSON array of {count} entity definition(s). Be creative but realistic for a healthcare operations context.
Return ONLY the JSON array, no markdown."""


def _build_debug_prompt(workflow_id: str, error_desc: str, sim_ctx: Dict[str, Any]) -> str:
    """Build the Claude prompt for workflow debugging."""
    return f"""You are a UiPath Studio expert debugging a faulted healthcare automation workflow.

Faulted workflow: {workflow_id}
Error description: {error_desc}

Current simulation context when fault occurred:
- Phase: {sim_ctx['phase']}
- Operational Stability: {sim_ctx['metrics']['operationalStability']}%
- Human Strain: {sim_ctx['metrics']['humanStrain']}%
- Degraded systems: {[b['name'] for b in sim_ctx['degraded_buildings']]}

Provide a structured diagnosis and fix. Return JSON with these exact fields:
{{
  "rootCause": "string — what caused the fault",
  "diagnosis": "string — detailed analysis of the error in context",
  "suggestedFix": "string — step-by-step remediation",
  "xamlPatch": "string — a minimal XAML fragment showing the corrected activity sequence",
  "preventionRecommendation": "string — how to prevent recurrence",
  "confidence_pct": number (0-100),
  "estimatedFixTimeMinutes": number
}}

Return ONLY the JSON object."""


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate-workflow")
async def generate_workflow(request: GenerateWorkflowRequest) -> Dict[str, Any]:
    """
    Generate a UiPath XAML workflow from the current simulation context, via the
    'coding_gen' robot agent (UiPath LLM gateway). No fallback.
    """
    start_time = time.time()
    sim_ctx = _build_simulation_context()
    process_type = request.processType

    # Generate on the UiPath robot (coding_gen agent uses UiPath's LLM). No fallback.
    prompt = _build_workflow_prompt(process_type, sim_ctx)
    out = await invoke_agent_job("coding_gen", {"system": "", "user": prompt})
    xaml = (out.get("text") or "").strip()
    if xaml.startswith("```"):
        xaml = xaml.split("```")[1]
        if xaml.startswith("xml"):
            xaml = xaml[3:]
        xaml = xaml.strip()
    badge = "GENERATED ON UIPATH ROBOT"
    model_used = "coding_gen agent"

    process_name_map = {
        "incident_response": "MaestroCity_IncidentResponse",
        "approval_chain": "MaestroCity_ApprovalChain",
        "crisis_response": "MaestroCity_CrisisResponse",
        "staffing": "MaestroCity_StaffingOptimization",
        "trust_recovery": "MaestroCity_TrustRecovery",
    }
    process_name = process_name_map.get(process_type, "MaestroCity_GenericWorkflow")

    generation_time_ms = int((time.time() - start_time) * 1000)

    return {
        "generatedBy": f"UiPath robot · {model_used}",
        "processName": process_name,
        "processType": process_type,
        "xaml": xaml,
        "projectJson": {
            "name": process_name,
            "description": f"Auto-generated by Maestro City Coding Agent | Phase: {sim_ctx['phase']}",
            "main": "Main.xaml",
            "outputType": "Process",
            "supportedPlatforms": ["Windows-Legacy", "Windows"],
            "targetFramework": "Portable",
            "studioVersion": "23.10.0",
            "dependencies": {
                "UiPath.System.Activities": "[23.10.0, )",
                "UiPath.UIAutomation.Activities": "[23.10.0, )",
            },
            "generatedAt": time.time(),
            "simulationPhase": sim_ctx["phase"],
        },
        "generationContext": {
            "phase": sim_ctx["phase"],
            "buildings_down": [b["name"] for b in sim_ctx["degraded_buildings"]],
            "metrics_summary": sim_ctx["metrics"],
            "tick": sim_ctx["tick"],
        },
        "generationTimeMs": generation_time_ms,
        "badge": badge,
    }


@router.post("/generate-entities")
async def generate_entities(request: GenerateEntitiesRequest) -> Dict[str, Any]:
    """
    Generate simulation entity definitions via the 'coding_gen' robot agent (UiPath LLM).
    Returns new building types, agent configs, or workflow type specs.
    """
    start_time = time.time()
    sim_ctx = _build_simulation_context()

    # Generate on the UiPath robot (coding_gen agent). No fallback.
    prompt = _build_entities_prompt(request.entityType, request.count, sim_ctx)
    out = await invoke_agent_job("coding_gen", {"system": "", "user": prompt})
    raw = (out.get("text") or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        entities = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"coding_gen returned invalid entity JSON: {e}")
    badge = "GENERATED ON UIPATH ROBOT"
    model_used = "coding_gen agent"

    generation_time_ms = int((time.time() - start_time) * 1000)

    return {
        "generatedBy": f"UiPath robot · {model_used}",
        "entityType": request.entityType,
        "count": len(entities),
        "entities": entities,
        "generationContext": {
            "phase": sim_ctx["phase"],
            "metrics_summary": sim_ctx["metrics"],
        },
        "generationTimeMs": generation_time_ms,
        "badge": badge,
    }


@router.post("/debug-workflow")
async def debug_workflow(request: DebugWorkflowRequest) -> Dict[str, Any]:
    """
    Diagnose a faulted UiPath workflow via the 'coding_gen' robot agent (UiPath LLM).
    """
    start_time = time.time()
    sim_ctx = _build_simulation_context()

    # Diagnose on the UiPath robot (coding_gen agent). No fallback.
    prompt = _build_debug_prompt(request.workflow_id, request.error_description, sim_ctx)
    out = await invoke_agent_job("coding_gen", {"system": "", "user": prompt})
    raw = (out.get("text") or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        debug_result = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"coding_gen returned invalid debug JSON: {e}")
    badge = "DEBUGGED ON UIPATH ROBOT"
    model_used = "coding_gen agent"

    generation_time_ms = int((time.time() - start_time) * 1000)

    return {
        "generatedBy": f"UiPath robot · {model_used}",
        "workflowId": request.workflow_id,
        "errorDescription": request.error_description,
        "diagnosis": debug_result.get("diagnosis", ""),
        "rootCause": debug_result.get("rootCause", ""),
        "suggestedFix": debug_result.get("suggestedFix", ""),
        "xamlPatch": debug_result.get("xamlPatch", ""),
        "preventionRecommendation": debug_result.get("preventionRecommendation", ""),
        "confidence_pct": debug_result.get("confidence_pct", 0),
        "estimatedFixTimeMinutes": debug_result.get("estimatedFixTimeMinutes", 0),
        "simulationContext": {
            "phase": sim_ctx["phase"],
            "degraded_buildings": [b["name"] for b in sim_ctx["degraded_buildings"]],
        },
        "generationTimeMs": generation_time_ms,
        "badge": badge,
    }
