from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class ScenarioDefinition:
    id: str
    name: str
    tagline: str            # 1 sentence shown on selection card
    description: str        # 2-3 sentences for the detail panel
    industry: str
    icon: str               # emoji
    color: str              # hex accent color e.g. "#3B82F6"

    # Simulation entity configs (plain dicts matching the Pydantic models)
    buildings: List[Dict[str, Any]]
    agents: List[Dict[str, Any]]
    workflows: List[Dict[str, Any]]
    dependency_edges: List[tuple]  # (from_id, to_id) pairs

    # Report vocabulary: maps generic metric labels to scenario-specific terms
    # Used in after-action reports and runbooks
    vocabulary: Dict[str, str] = field(default_factory=dict)
    # e.g. {"service_unit": "patient", "primary_system": "Trading Floor",
    #        "secondary_system": "Risk Management", "workflow_type_primary": "transaction"}

    # Compliance frameworks for reports
    compliance_frameworks: List[str] = field(default_factory=list)

    # Industry context paragraph for executive summary
    industry_context: str = ""

    # UiPath process names for this scenario (shown in runbooks + process templates)
    uipath_processes: List[str] = field(default_factory=list)

    # Named outage presets for the "Trigger Outage" panel
    outage_presets: List[Dict[str, Any]] = field(default_factory=list)
    # e.g. [{"id": "cloud_outage", "name": "Cloud Outage", "buildingId": "cloud_datacenter", "severity": "full", "description": "..."}]
