import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class TickSnapshot:
    tick: int
    timestamp: float
    phase: str
    metrics: Dict[str, float]              # all 6 metric values
    building_healths: Dict[str, float]     # id -> health
    building_statuses: Dict[str, str]      # id -> status
    active_workflows: int
    blocked_workflows: int
    active_agents: int                     # agents NOT idle

@dataclass
class InterventionRecord:
    tick: int
    timestamp: float
    source: str                            # 'player' | agent_id (e.g. 'ops_coord')
    action_type: str                       # e.g. 'set_autonomy', 'activate_failover'
    description: str                       # human readable
    target_building_id: Optional[str]
    target_agent_id: Optional[str]
    metrics_before: Dict[str, float]
    metrics_after: Optional[Dict[str, float]] = None  # filled in next tick
    stability_delta: Optional[float] = None            # positive = improved
    successful: bool = True

@dataclass
class UiPathJobRecord:
    job_id: str
    process_name: str
    triggered_at_tick: int
    triggered_by: str                      # agent id or 'player'
    input_args: Dict[str, Any]
    completed_at_tick: Optional[int] = None
    final_state: Optional[str] = None     # 'Successful' | 'Faulted'
    output_args: Optional[Dict[str, Any]] = None
    stability_impact: Optional[float] = None  # delta in operationalStability after completion

class ScenarioTracker:
    def __init__(self):
        self.scenario_id: str = ""
        self.started_at: float = 0.0
        self.snapshots: List[TickSnapshot] = []
        self.interventions: List[InterventionRecord] = []
        self.uipath_jobs: List[UiPathJobRecord] = []
        self._pending_interventions: Dict[str, InterventionRecord] = {}  # action_id -> record
        self._scenario_active: bool = False

    def start_scenario(self, scenario_id: str = None):
        """Begin tracking a new scenario."""
        import uuid
        self.scenario_id = scenario_id or f"scenario-{uuid.uuid4().hex[:8]}"
        self.started_at = time.time()
        self.snapshots.clear()
        self.interventions.clear()
        self.uipath_jobs.clear()
        self._pending_interventions.clear()
        self._scenario_active = True

    def record_tick(self, tick, buildings, metrics, phase, workflows, agents):
        """Called every tick to snapshot current state."""
        # Fill in metrics_after for previous tick's pending interventions
        for record in self._pending_interventions.values():
            if record.metrics_after is None:
                record.metrics_after = self._metrics_dict(metrics)
                record.stability_delta = (
                    record.metrics_after["operationalStability"] -
                    record.metrics_before["operationalStability"]
                )
        self._pending_interventions.clear()

        snap = TickSnapshot(
            tick=tick,
            timestamp=time.time(),
            phase=phase.value if hasattr(phase, 'value') else str(phase),
            metrics=self._metrics_dict(metrics),
            building_healths={b.id: b.health for b in buildings},
            building_statuses={b.id: b.status.value if hasattr(b.status, 'value') else str(b.status) for b in buildings},
            active_workflows=len(workflows),
            blocked_workflows=sum(1 for w in workflows if w.status.value in ('blocked', 'failed')),
            active_agents=sum(1 for a in agents if a.status.value != 'idle'),
        )
        self.snapshots.append(snap)
        # Keep memory bounded
        if len(self.snapshots) > 3600:  # 1 hour at 1s ticks
            self.snapshots = self.snapshots[-3600:]

    def record_intervention(self, action_type: str, description: str,
                           source: str, current_metrics,
                           target_building_id=None, target_agent_id=None,
                           action_id: str = None):
        """Record a player or agent intervention."""
        import uuid
        record = InterventionRecord(
            tick=len(self.snapshots),
            timestamp=time.time(),
            source=source,
            action_type=action_type,
            description=description,
            target_building_id=target_building_id,
            target_agent_id=target_agent_id,
            metrics_before=self._metrics_dict(current_metrics),
        )
        self.interventions.append(record)
        # Register as pending so next tick fills in metrics_after
        aid = action_id or str(uuid.uuid4())[:8]
        self._pending_interventions[aid] = record
        return record

    def record_uipath_job(self, job_id: str, process_name: str, tick: int,
                         triggered_by: str, input_args: dict):
        record = UiPathJobRecord(
            job_id=job_id,
            process_name=process_name,
            triggered_at_tick=tick,
            triggered_by=triggered_by,
            input_args=input_args,
        )
        self.uipath_jobs.append(record)
        return record

    def complete_uipath_job(self, job_id: str, state: str, output_args: dict,
                           tick: int, current_metrics):
        for job in self.uipath_jobs:
            if job.job_id == job_id and job.completed_at_tick is None:
                job.completed_at_tick = tick
                job.final_state = state
                job.output_args = output_args
                if self.snapshots and len(self.snapshots) >= 2:
                    before_idx = max(0, self.snapshots.index(
                        next((s for s in self.snapshots if s.tick >= job.triggered_at_tick), self.snapshots[0])
                    ))
                    job.stability_impact = (
                        self._metrics_dict(current_metrics)["operationalStability"] -
                        self.snapshots[before_idx].metrics["operationalStability"]
                    )
                break

    def _metrics_dict(self, metrics) -> Dict[str, float]:
        if isinstance(metrics, dict):
            return metrics
        return {
            "operationalStability": metrics.operationalStability,
            "humanStrain": metrics.humanStrain,
            "automationConfidence": metrics.automationConfidence,
            "serviceAvailability": metrics.serviceAvailability,
            "systemTrust": metrics.systemTrust,
            "resourceCapacity": metrics.resourceCapacity,
        }

    @property
    def duration_ticks(self) -> int:
        return len(self.snapshots)

    @property
    def crisis_ticks(self) -> int:
        return sum(1 for s in self.snapshots if s.phase == 'crisis')

    @property
    def worst_metrics(self) -> Optional[Dict[str, float]]:
        if not self.snapshots:
            return None
        return min(self.snapshots, key=lambda s: s.metrics["operationalStability"]).metrics

    @property
    def recovery_achieved(self) -> bool:
        if not self.snapshots:
            return False
        last_5 = self.snapshots[-5:]
        return all(s.metrics["operationalStability"] > 60 for s in last_5)

    @property
    def phase_transitions(self) -> List[Dict]:
        transitions = []
        prev_phase = None
        for s in self.snapshots:
            if s.phase != prev_phase:
                transitions.append({"tick": s.tick, "phase": s.phase})
                prev_phase = s.phase
        return transitions
