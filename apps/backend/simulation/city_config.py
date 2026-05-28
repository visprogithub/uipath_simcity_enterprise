"""
City configuration delegate for Maestro City simulation.
Delegates to the active scenario definition in the scenarios registry.
"""
import os
from typing import List

from scenarios.registry import get_scenario as _get_scenario


def get_initial_buildings(scenario_id: str = "healthcare"):
    scenario = _get_scenario(scenario_id)
    from models.building import Building, BuildingPosition, BuildingType, BuildingStatus
    buildings = []
    for b in scenario.buildings:
        data = dict(b)
        # Convert nested pos dict to BuildingPosition
        if isinstance(data.get("pos"), dict):
            data["pos"] = BuildingPosition(**data["pos"])
        buildings.append(Building(**data))
    return buildings


def get_initial_agents(scenario_id: str = "healthcare"):
    scenario = _get_scenario(scenario_id)
    from models.agent import Agent, AgentType, AgentStatus, AutonomyLevel
    return [Agent(**a) for a in scenario.agents]


def get_initial_workflows(scenario_id: str = "healthcare"):
    scenario = _get_scenario(scenario_id)
    from models.workflow import Workflow, WorkflowStatus, WorkflowPriority, WorkflowType
    return [Workflow(**w) for w in scenario.workflows]


def get_dependency_edges(scenario_id: str = "healthcare"):
    scenario = _get_scenario(scenario_id)
    return scenario.dependency_edges


def get_scenario_definition(scenario_id: str = "healthcare"):
    return _get_scenario(scenario_id)
