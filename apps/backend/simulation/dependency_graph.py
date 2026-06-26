"""
NetworkX-based dependency graph for cascade failure propagation.
"""
import logging
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from models.building import Building

logger = logging.getLogger(__name__)

# Attenuation factors by hop distance
_HOP_ATTENUATION = {
    1: 0.60,  # direct dependency: 60% of health reduction
    2: 0.35,  # 2 hops away: 35%
    3: 0.15,  # 3 hops: 15%
}
_MAX_HOP_PROPAGATION = 3
_PROPAGATION_THRESHOLD = 50.0  # only propagates if failing building health < 50


class DependencyGraph:
    """
    Directed graph where an edge (A -> B) means A depends on B.
    If B fails, all buildings that depend on B (directly or transitively) are affected.
    """

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()

    def build_graph(self, buildings: List[Building]) -> None:
        """Create directed graph from building dependencies."""
        self._graph.clear()
        for b in buildings:
            self._graph.add_node(b.id)

        for b in buildings:
            for dep_id in b.dependencies:
                # Edge: b.id -> dep_id (b depends on dep_id)
                self._graph.add_edge(b.id, dep_id)

    def get_dependents(self, building_id: str) -> Set[str]:
        """
        Return all buildings that directly depend on building_id.
        (i.e., nodes that have an edge pointing TO building_id)
        """
        return set(self._graph.predecessors(building_id))

    def get_downstream_affected(self, building_id: str) -> Dict[str, int]:
        """
        Return all buildings affected if building_id fails,
        along with their hop distance from the failing building.
        Uses reverse traversal: find everything that depends on building_id.
        """
        affected: Dict[str, int] = {}
        # We need to find nodes that transitively depend on building_id.
        # In our graph, A->B means A depends on B.
        # So we traverse reverse edges from building_id to find dependents.
        reverse_graph = self._graph.reverse(copy=False)

        # BFS from building_id in the reverse graph
        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(building_id, 0)]

        while queue:
            current, depth = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            if current != building_id and depth <= _MAX_HOP_PROPAGATION:
                affected[current] = depth

            if depth < _MAX_HOP_PROPAGATION:
                for neighbor in reverse_graph.successors(current):
                    if neighbor not in visited:
                        queue.append((neighbor, depth + 1))

        return affected

    def get_health_propagation(
        self, building_id: str, health_reduction: float
    ) -> Dict[str, float]:
        """
        Calculate cascading health reduction for each downstream building.
        Returns dict of building_id -> health_reduction_amount.
        Attenuated by hop distance. Only propagates if health_reduction is significant.
        """
        downstream = self.get_downstream_affected(building_id)
        result: Dict[str, float] = {}

        for dep_id, hops in downstream.items():
            attenuation = _HOP_ATTENUATION.get(hops, 0.0)
            result[dep_id] = health_reduction * attenuation

        return result

    def calculate_outage_impact(
        self, failed_id: str, current_buildings: List[Building]
    ) -> Dict[str, float]:
        """
        Given a failing building, calculate the new health for each affected building.
        Returns dict of building_id -> new_health_value.
        """
        building_map: Dict[str, Building] = {b.id: b for b in current_buildings}
        failing_building = building_map.get(failed_id)

        if not failing_building:
            return {}

        # Only propagate if the failing building is truly failing
        if failing_building.health >= _PROPAGATION_THRESHOLD:
            return {}

        health_reduction = 100.0 - failing_building.health
        propagation = self.get_health_propagation(failed_id, health_reduction)

        result: Dict[str, float] = {}
        for bid, reduction in propagation.items():
            b = building_map.get(bid)
            if b:
                result[bid] = max(0.0, b.health - reduction)

        return result

    def propagate_failures(
        self, buildings: List[Building], failover_active: bool = False,
        coordination: float = 0.0,
    ) -> List[str]:
        """
        For all buildings currently in a failing state (health < threshold),
        propagate health reductions to their dependents.
        Modifies buildings in place. Returns list of affected building IDs.

        Cascade pressure is held back by PEOPLE, not infrastructure: staffing
        absorbs some, and multi-agent coordination (agents at high autonomy working
        the incident) absorbs more. Failover deliberately does NOT dampen here — its
        job is to revive the dead hub (see recovery), not to shield dependents. So
        failover alone revives the root but the rest of the grid still crumbles unless
        staff and coordinated agents hold the line: recovery needs the combination.
        """
        self.build_graph(buildings)
        building_map: Dict[str, Building] = {b.id: b for b in buildings}
        affected_ids: Set[str] = set()

        # Identify failing buildings
        failing = [b for b in buildings if b.health < _PROPAGATION_THRESHOLD]

        for failing_b in failing:
            health_reduction = (100.0 - failing_b.health)
            propagation = self.get_health_propagation(failing_b.id, health_reduction)

            for dep_id, reduction in propagation.items():
                dep = building_map.get(dep_id)
                if dep and dep != failing_b:
                    # Per-tick reduction. Strong enough that an unaddressed hub
                    # outage drags dependents below the propagation threshold and the
                    # cascade snowballs (collapse is a real threat, not a slow drift).
                    tick_reduction = reduction * 0.05
                    # Support absorbs cascade pressure. Staffing contributes only a
                    # little (it's maxed by default, so it must NOT neuter the cascade
                    # on its own); multi-agent coordination matters only when several
                    # agents are working the incident together.
                    support = 0.20 * (dep.staffingLevel / 100.0) + 0.50 * coordination
                    tick_reduction *= max(0.1, 1.0 - support)
                    dep.health = max(0.0, dep.health - tick_reduction)
                    dep.throughput = max(0.0, dep.throughput - tick_reduction * 0.5)
                    dep.clamp()
                    affected_ids.add(dep_id)

        return list(affected_ids)

    def has_path(self, source_id: str, dest_id: str) -> bool:
        """Check if there's a dependency path between two buildings."""
        try:
            return nx.has_path(self._graph, source_id, dest_id)
        except nx.NodeNotFound:
            return False

    def get_redundancy_factor(self, building_id: str, buildings: List[Building]) -> float:
        """
        Calculate redundancy factor for a building.
        Higher redundancy means cascade effects are attenuated further.
        Returns 0.0 (no redundancy) to 1.0 (full redundancy).
        """
        dependents = self.get_dependents(building_id)
        if not dependents:
            return 0.0

        building_map = {b.id: b for b in buildings}
        healthy_alternates = 0

        for dep_id in dependents:
            dep = building_map.get(dep_id)
            if dep and dep.health > 60:
                healthy_alternates += 1

        return min(1.0, healthy_alternates / max(1, len(dependents)))
