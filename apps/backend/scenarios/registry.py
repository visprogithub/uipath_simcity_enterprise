"""Scenario registry. Built scenarios come from compact specs via the factory.
Custom (AI-generated) scenarios can be registered at runtime with register_custom_spec()."""
from typing import Any, Dict, List

from scenarios.factory import build_scenario
from scenarios.specs import SPECS

# Build all default scenarios from their specs
SCENARIO_REGISTRY = {spec["id"]: build_scenario(spec) for spec in SPECS}

# Track which scenario ids were user-created (vs built-in defaults)
_CUSTOM_IDS: set = set()


def get_scenario(scenario_id: str):
    s = SCENARIO_REGISTRY.get(scenario_id)
    if not s:
        raise ValueError(f"Unknown scenario: {scenario_id}. Available: {list(SCENARIO_REGISTRY.keys())}")
    return s


def register_custom_spec(spec: Dict[str, Any]):
    """Validate + build a custom scenario spec and register it live. Returns the definition."""
    definition = build_scenario(spec)  # raises if the spec is malformed
    SCENARIO_REGISTRY[definition.id] = definition
    _CUSTOM_IDS.add(definition.id)
    return definition


def _card(s) -> Dict[str, Any]:
    return {
        "id": s.id, "name": s.name, "tagline": s.tagline, "description": s.description,
        "industry": s.industry, "icon": s.icon, "color": s.color,
        "buildingCount": len(s.buildings), "agentCount": len(s.agents),
        "complianceFrameworks": s.compliance_frameworks, "outagePresets": s.outage_presets,
        "custom": s.id in _CUSTOM_IDS,
    }


def list_scenarios() -> List[Dict[str, Any]]:
    return [_card(s) for s in SCENARIO_REGISTRY.values()]
