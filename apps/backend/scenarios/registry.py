from scenarios.healthcare import get_scenario as get_healthcare
from scenarios.financial_services import get_scenario as get_financial
from scenarios.retail_ecommerce import get_scenario as get_retail
from scenarios.manufacturing import get_scenario as get_manufacturing

SCENARIO_REGISTRY = {
    "healthcare": get_healthcare(),
    "financial_services": get_financial(),
    "retail_ecommerce": get_retail(),
    "manufacturing": get_manufacturing(),
}


def get_scenario(scenario_id: str):
    s = SCENARIO_REGISTRY.get(scenario_id)
    if not s:
        raise ValueError(f"Unknown scenario: {scenario_id}. Available: {list(SCENARIO_REGISTRY.keys())}")
    return s


def list_scenarios():
    return [
        {
            "id": s.id,
            "name": s.name,
            "tagline": s.tagline,
            "description": s.description,
            "industry": s.industry,
            "icon": s.icon,
            "color": s.color,
            "buildingCount": len(s.buildings),
            "agentCount": len(s.agents),
            "complianceFrameworks": s.compliance_frameworks,
            "outagePresets": s.outage_presets,
        }
        for s in SCENARIO_REGISTRY.values()
    ]
