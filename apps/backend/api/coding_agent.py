"""
Coding Agent Endpoint — Bonus Feature.

Uses the OpenAI API (gpt-4o) to dynamically generate UiPath XAML workflows,
simulation entity definitions, and workflow diagnostics based on the current
simulation context. Falls back to realistic mock responses when no API key is set.
"""
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from models.building import BuildingStatus
from models.state import GamePhase
from simulation.engine import engine

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


# ─── Mock Responses ────────────────────────────────────────────────────────────

def _mock_xaml(process_type: str, sim_ctx: Dict[str, Any]) -> str:
    """Generate realistic mock XAML for when API key is not available."""
    phase = sim_ctx["phase"]
    stability = sim_ctx["metrics"]["operationalStability"]
    degraded = ", ".join(b["name"] for b in sim_ctx["degraded_buildings"]) or "None"

    process_name_map = {
        "incident_response": "MaestroCity_IncidentResponse",
        "approval_chain": "MaestroCity_ApprovalChain",
        "crisis_response": "MaestroCity_CrisisResponse",
        "staffing": "MaestroCity_StaffingOptimization",
        "trust_recovery": "MaestroCity_TrustRecovery",
    }
    process_name = process_name_map.get(process_type, "MaestroCity_GenericWorkflow")

    return f"""<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap2010 sads" x:Class="UiPath.Process.{process_name}"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
  xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
  xmlns:ui="http://schemas.uipath.com/workflow/activities"
  xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
  xmlns:sads="http://schemas.microsoft.com/netfx/2010/xaml/activities/debugger"
  xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
  xmlns:s="clr-namespace:System;assembly=mscorlib">
  <!-- Generated for Maestro City | Phase: {phase} | Stability: {stability}% | Degraded: {degraded} -->
  <x:Members>
    <x:Property Name="in_SimulationPhase" Type="InArgument(x:String)" />
    <x:Property Name="in_OperationalStability" Type="InArgument(x:Double)" />
    <x:Property Name="in_BuildingId" Type="InArgument(x:String)" />
    <x:Property Name="out_ActionTaken" Type="OutArgument(x:String)" />
    <x:Property Name="out_EscalationRequired" Type="OutArgument(x:Boolean)" />
  </x:Members>
  <sap2010:WorkflowViewState.IdRef>1</sap2010:WorkflowViewState.IdRef>
  <Sequence DisplayName="{process_name}" sap2010:WorkflowViewState.IdRef="2">
    <Sequence.Variables>
      <Variable x:TypeArguments="x:String" Default="" Name="currentPhase" />
      <Variable x:TypeArguments="x:Double" Default="0" Name="stabilityScore" />
      <Variable x:TypeArguments="x:Boolean" Default="False" Name="requiresEscalation" />
      <Variable x:TypeArguments="x:String" Default="" Name="actionLog" />
    </Sequence.Variables>

    <!-- Step 1: Initialize context from simulation state -->
    <Assign DisplayName="Load Simulation Context" sap2010:WorkflowViewState.IdRef="3">
      <Assign.To><OutArgument x:TypeArguments="x:String">[currentPhase]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">[in_SimulationPhase]</InArgument></Assign.Value>
    </Assign>
    <Assign DisplayName="Load Stability Score" sap2010:WorkflowViewState.IdRef="4">
      <Assign.To><OutArgument x:TypeArguments="x:Double">[stabilityScore]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Double">[in_OperationalStability]</InArgument></Assign.Value>
    </Assign>

    <!-- Step 2: Log workflow initiation -->
    <ui:LogMessage DisplayName="Log: Workflow Started" Level="Info" sap2010:WorkflowViewState.IdRef="5">
      <ui:LogMessage.Message>
        <InArgument x:TypeArguments="x:String">["[{process_name}] Started | Phase: " + currentPhase + " | Stability: " + stabilityScore.ToString("F1") + "%"]</InArgument>
      </ui:LogMessage.Message>
    </ui:LogMessage>

    <!-- Step 3: Evaluate current crisis level -->
    <If DisplayName="Check: Phase is Crisis or Collapsed" sap2010:WorkflowViewState.IdRef="6">
      <If.Condition>
        <InArgument x:TypeArguments="x:Boolean">[currentPhase = "crisis" OrElse currentPhase = "collapsed"]</InArgument>
      </If.Condition>
      <If.Then>
        <Sequence DisplayName="Crisis Path: Full Escalation Protocol" sap2010:WorkflowViewState.IdRef="7">
          <Assign DisplayName="Set Escalation Flag" sap2010:WorkflowViewState.IdRef="8">
            <Assign.To><OutArgument x:TypeArguments="x:Boolean">[requiresEscalation]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:Boolean">[True]</InArgument></Assign.Value>
          </Assign>
          <ui:LogMessage DisplayName="Log: Crisis Protocol Activated" Level="Warn" sap2010:WorkflowViewState.IdRef="9">
            <ui:LogMessage.Message>
              <InArgument x:TypeArguments="x:String">["CRISIS PROTOCOL ACTIVE: Phase=" + currentPhase]</InArgument>
            </ui:LogMessage.Message>
          </ui:LogMessage>
          <!-- Invoke Crisis Response Sub-Workflow -->
          <InvokeWorkflowFile DisplayName="Execute: Crisis Response Playbook"
            WorkflowFileName="Workflows\\CrisisResponsePlaybook.xaml" sap2010:WorkflowViewState.IdRef="10">
            <InvokeWorkflowFile.Arguments>
              <scg:Dictionary x:TypeArguments="x:String, x:Object">
                <x:String x:Key="in_Phase">[currentPhase]</x:String>
                <x:String x:Key="in_Stability">[stabilityScore]</x:String>
              </scg:Dictionary>
            </InvokeWorkflowFile.Arguments>
          </InvokeWorkflowFile>
        </Sequence>
      </If.Then>
      <If.Else>
        <Sequence DisplayName="Standard Path: Monitored Intervention" sap2010:WorkflowViewState.IdRef="11">
          <!-- Check if stability warrants intervention -->
          <If DisplayName="Check: Stability Below Threshold (70%)" sap2010:WorkflowViewState.IdRef="12">
            <If.Condition>
              <InArgument x:TypeArguments="x:Boolean">[stabilityScore &lt; 70.0]</InArgument>
            </If.Condition>
            <If.Then>
              <Sequence DisplayName="Degraded Path: Targeted Recovery Actions" sap2010:WorkflowViewState.IdRef="13">
                <InvokeWorkflowFile DisplayName="Execute: Building Health Check"
                  WorkflowFileName="Workflows\\BuildingHealthCheck.xaml" sap2010:WorkflowViewState.IdRef="14">
                  <InvokeWorkflowFile.Arguments>
                    <scg:Dictionary x:TypeArguments="x:String, x:Object">
                      <x:String x:Key="in_BuildingId">[in_BuildingId]</x:String>
                    </scg:Dictionary>
                  </InvokeWorkflowFile.Arguments>
                </InvokeWorkflowFile>
                <InvokeWorkflowFile DisplayName="Execute: Staffing Rebalance"
                  WorkflowFileName="Workflows\\StaffingRebalance.xaml" sap2010:WorkflowViewState.IdRef="15" />
              </Sequence>
            </If.Then>
            <If.Else>
              <ui:LogMessage DisplayName="Log: System Stable — Monitoring Only" Level="Info" sap2010:WorkflowViewState.IdRef="16">
                <ui:LogMessage.Message>
                  <InArgument x:TypeArguments="x:String">["System stable at " + stabilityScore.ToString("F1") + "% — no intervention required"]</InArgument>
                </ui:LogMessage.Message>
              </ui:LogMessage>
            </If.Else>
          </If>
        </Sequence>
      </If.Else>
    </If>

    <!-- Step 4: Record action outcome -->
    <Assign DisplayName="Record Action Taken" sap2010:WorkflowViewState.IdRef="17">
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_ActionTaken]</OutArgument></Assign.To>
      <Assign.Value>
        <InArgument x:TypeArguments="x:String">["{process_name} completed | Escalated: " + requiresEscalation.ToString()]</InArgument>
      </Assign.Value>
    </Assign>
    <Assign DisplayName="Set Output: Escalation Required" sap2010:WorkflowViewState.IdRef="18">
      <Assign.To><OutArgument x:TypeArguments="x:Boolean">[out_EscalationRequired]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Boolean">[requiresEscalation]</InArgument></Assign.Value>
    </Assign>

    <!-- Step 5: Final audit log -->
    <ui:LogMessage DisplayName="Log: Workflow Completed" Level="Info" sap2010:WorkflowViewState.IdRef="19">
      <ui:LogMessage.Message>
        <InArgument x:TypeArguments="x:String">["[{process_name}] Completed | EscalationRequired=" + requiresEscalation.ToString()]</InArgument>
      </ui:LogMessage.Message>
    </ui:LogMessage>

  </Sequence>
</Activity>"""


def _mock_debug_response(workflow_id: str, error_desc: str) -> Dict[str, Any]:
    """Generate a mock debug response."""
    return {
        "rootCause": (
            f"Workflow '{workflow_id}' faulted due to: {error_desc[:100]}. "
            "Root cause identified as unhandled null reference in activity binding when upstream "
            "building health drops below the activity's minimum viable health threshold."
        ),
        "diagnosis": (
            f"The error '{error_desc}' typically occurs when the workflow attempts to read a "
            "throughput or health value from a building that has transitioned to 'offline' status "
            "between the activity's argument evaluation and its execution. The InArgument binding "
            "does not validate against null/offline states before using the value in a calculation."
        ),
        "suggestedFix": (
            "1. Add a TryCatch activity wrapping the faulted activity block.\n"
            "2. Insert a pre-check Assign that validates building.health > 0 before use.\n"
            "3. Add a default value fallback: [If(building IsNot Nothing, building.health, 0.0)].\n"
            "4. Add a LogMessage in the Catch block to record the null state for audit.\n"
            "5. Re-test against a simulated offline building to verify the guard handles it."
        ),
        "xamlPatch": (
            '<TryCatch DisplayName="Safe: Building Health Read with Null Guard">\n'
            '  <TryCatch.Try>\n'
            '    <Assign DisplayName="Read Building Health (Guarded)">\n'
            '      <Assign.Value>\n'
            '        <InArgument x:TypeArguments="x:Double">\n'
            '          [If(building IsNot Nothing AndAlso building.health > 0, building.health, 0.0)]\n'
            '        </InArgument>\n'
            '      </Assign.Value>\n'
            '    </Assign>\n'
            '  </TryCatch.Try>\n'
            '  <TryCatch.Catches>\n'
            '    <Catch x:TypeArguments="s:Exception">\n'
            '      <ActivityAction x:TypeArguments="s:Exception">\n'
            '        <ActivityAction.Argument>\n'
            '          <DelegateInArgument x:TypeArguments="s:Exception" Name="ex" />\n'
            '        </ActivityAction.Argument>\n'
            '        <ui:LogMessage Level="Error" Message="[&quot;Building health read failed: &quot; + ex.Message]" />\n'
            '      </ActivityAction>\n'
            '    </Catch>\n'
            '  </TryCatch.Catches>\n'
            '</TryCatch>'
        ),
        "preventionRecommendation": (
            "Add a pre-workflow validation step that checks all referenced building IDs exist and "
            "have health > 0 before the main workflow sequence executes. Consider creating a shared "
            "'ValidateBuildingState.xaml' invokable workflow used as a guard at the top of any process "
            "that reads building health values."
        ),
        "confidence_pct": 82,
        "estimatedFixTimeMinutes": 15,
    }


def _mock_entities_response(entity_type: str, count: int) -> List[Dict[str, Any]]:
    """Generate mock entity definitions."""
    entities = []
    for i in range(count):
        if entity_type == "building":
            entities.append({
                "id": f"medical_imaging_{uuid.uuid4().hex[:4]}",
                "type": "medical_imaging",
                "name": f"Radiology & Imaging Center {i + 1}",
                "description": "Provides DICOM image processing, radiology workflow automation, and AI-assisted diagnostics.",
                "dependencies": ["cloud_datacenter", "hospital"],
                "healthImpactOnDependents": {"hospital": 0.15},
                "recoveryCapacity": 65.0,
                "staffingRequirement": 12,
                "automationEligibility": ["image_routing", "report_delivery", "worklist_management"],
            })
        elif entity_type == "agent":
            entities.append({
                "id": f"diag_agent_{uuid.uuid4().hex[:4]}",
                "type": "diagnostics_coordinator",
                "name": "PRISM",
                "role": "Coordinates diagnostic workflow routing and AI model inference scheduling",
                "autonomyLevel": 2,
                "specialization": "Medical imaging and lab result workflows",
                "triggerConditions": ["imaging_queue > 30", "lab_result.pending > 50"],
                "tools": ["RouteImagingStudy", "PrioritizeDiagnosticQueue", "NotifyRadiologist"],
            })
        else:  # workflow_type
            entities.append({
                "id": f"lab_result_{uuid.uuid4().hex[:4]}",
                "name": "Lab Result Delivery",
                "description": "Automated routing of lab results from laboratory systems to ordering clinicians with priority triage.",
                "typicalRisk": 0.35,
                "automationEligibility": True,
                "complianceRequirements": ["hipaa_privacy", "joint_commission"],
                "averageProcessingTimeMs": 450,
                "criticalThresholds": {"criticalValueFlag": True, "notifyPhysicianWithinMinutes": 5},
            })
    return entities


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate-workflow")
async def generate_workflow(request: GenerateWorkflowRequest) -> Dict[str, Any]:
    """
    Generate a UiPath XAML workflow using Claude AI based on the current simulation context.
    Falls back to a realistic mock when ANTHROPIC_API_KEY is not set.
    """
    start_time = time.time()
    sim_ctx = _build_simulation_context()
    process_type = request.processType

    api_key = os.getenv("OPENAI_API_KEY", "")

    xaml = ""
    badge = ""
    model_used = ""

    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            prompt = _build_workflow_prompt(process_type, sim_ctx)

            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            xaml = response.choices[0].message.content.strip()
            badge = "GENERATED BY CODING AGENT"
            model_used = "gpt-4o"
            logger.info(f"OpenAI generated XAML for process_type={process_type}, {len(xaml)} chars")
        except Exception as e:
            logger.warning(f"OpenAI API call failed, using mock: {e}")
            xaml = _mock_xaml(process_type, sim_ctx)
            badge = "DEMO - API Error Fallback"
            model_used = "mock"
    else:
        xaml = _mock_xaml(process_type, sim_ctx)
        badge = "DEMO - No API Key Set"
        model_used = "mock"

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
        "generatedBy": f"OpenAI {model_used} Coding Agent",
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
    Generate simulation entity definitions using OpenAI gpt-4o.
    Returns new building types, agent configs, or workflow type specs.
    """
    start_time = time.time()
    sim_ctx = _build_simulation_context()

    api_key = os.getenv("OPENAI_API_KEY", "")
    entities = []
    badge = ""
    model_used = ""

    if api_key:
        try:
            from openai import OpenAI
            import json
            client = OpenAI(api_key=api_key)
            prompt = _build_entities_prompt(request.entityType, request.count, sim_ctx)

            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            entities = json.loads(raw.strip())
            badge = "GENERATED BY CODING AGENT"
            model_used = "gpt-4o"
            logger.info(f"OpenAI generated {len(entities)} entities of type {request.entityType}")
        except Exception as e:
            logger.warning(f"OpenAI API call failed for entity generation, using mock: {e}")
            entities = _mock_entities_response(request.entityType, request.count)
            badge = "DEMO - API Error Fallback"
            model_used = "mock"
    else:
        entities = _mock_entities_response(request.entityType, request.count)
        badge = "DEMO - No API Key Set"
        model_used = "mock"

    generation_time_ms = int((time.time() - start_time) * 1000)

    return {
        "generatedBy": f"OpenAI {model_used} Coding Agent",
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
    Diagnose a faulted UiPath workflow using OpenAI gpt-4o and return a suggested fix.
    """
    start_time = time.time()
    sim_ctx = _build_simulation_context()

    api_key = os.getenv("OPENAI_API_KEY", "")
    debug_result: Dict[str, Any] = {}
    badge = ""
    model_used = ""

    if api_key:
        try:
            from openai import OpenAI
            import json
            client = OpenAI(api_key=api_key)
            prompt = _build_debug_prompt(request.workflow_id, request.error_description, sim_ctx)

            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            debug_result = json.loads(raw.strip())
            badge = "DEBUGGED BY CODING AGENT"
            model_used = "gpt-4o"
            logger.info(f"OpenAI debugged workflow {request.workflow_id}")
        except Exception as e:
            logger.warning(f"OpenAI API call failed for debug, using mock: {e}")
            debug_result = _mock_debug_response(request.workflow_id, request.error_description)
            badge = "DEMO - API Error Fallback"
            model_used = "mock"
    else:
        debug_result = _mock_debug_response(request.workflow_id, request.error_description)
        badge = "DEMO - No API Key Set"
        model_used = "mock"

    generation_time_ms = int((time.time() - start_time) * 1000)

    return {
        "generatedBy": f"OpenAI {model_used} Coding Agent",
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
