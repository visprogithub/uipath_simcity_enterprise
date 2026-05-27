import json
import time
from typing import Dict, Any

from simulation.scenario_tracker import ScenarioTracker


class AfterActionReporter:
    def generate(self, tracker: ScenarioTracker, buildings_config: list) -> Dict[str, Any]:
        """Generate a complete after-action report."""

        if not tracker.snapshots:
            return {
                "reportId": f"aar-{tracker.scenario_id}",
                "generatedAt": time.time(),
                "scenarioId": tracker.scenario_id,
                "durationTicks": 0,
                "durationSeconds": 0,
                "executiveSummary": "Scenario has not yet started. Run the simulation and trigger an outage to generate a meaningful after-action report.",
                "outcomeStatus": "pending",
                "phaseTimeline": [],
                "worstPhaseReached": "healthy",
                "metrics": {"start": {}, "worst": {}, "end": {}, "recoveryRatePerTick": 0},
                "mostAffectedBuildings": [],
                "crisisTicks": 0,
                "estimatedCrisisWithoutAutomation": 0,
                "automationContributionPct": 0,
                "playerInterventionCount": 0,
                "agentInterventionCount": 0,
                "effectiveInterventions": [],
                "uipathJobs": [],
                "recommendations": ["Start the simulation, trigger a cloud outage from the right panel, let agents respond, then return here for a full report."],
            }

        first_snap = tracker.snapshots[0]
        last_snap = tracker.snapshots[-1]
        worst = tracker.worst_metrics or {}

        # Calculate automation vs player contribution to recovery
        agent_interventions = [i for i in tracker.interventions if i.source != 'player']
        player_interventions = [i for i in tracker.interventions if i.source == 'player']

        agent_stability_gain = sum(
            i.stability_delta for i in agent_interventions
            if i.stability_delta and i.stability_delta > 0
        )
        player_stability_gain = sum(
            i.stability_delta for i in player_interventions
            if i.stability_delta and i.stability_delta > 0
        )
        total_gain = agent_stability_gain + player_stability_gain
        automation_pct = (agent_stability_gain / total_gain * 100) if total_gain > 0 else 0

        # Estimate downtime without automation (simplified model):
        # Each agent intervention that improved stability by >5pts prevented ~3 extra crisis ticks
        prevented_crisis_ticks = sum(
            3 for i in agent_interventions
            if i.stability_delta and i.stability_delta > 5
        )
        est_without_automation_ticks = tracker.crisis_ticks + prevented_crisis_ticks

        # Most affected buildings
        affected = []
        for bid, name in {b['id']: b['name'] for b in buildings_config}.items():
            healths = [s.building_healths.get(bid, 100) for s in tracker.snapshots]
            min_health = min(healths)
            if min_health < 90:
                recovery_tick = next(
                    (i for i, h in enumerate(healths) if h > 70 and healths[i-1] <= 70),
                    None
                )
                affected.append({
                    "buildingId": bid,
                    "name": name,
                    "minHealth": round(min_health, 1),
                    "currentHealth": round(healths[-1], 1),
                    "recoveryTick": recovery_tick,
                })
        affected.sort(key=lambda x: x["minHealth"])

        # Effective interventions (those that improved stability ≥3pts)
        effective = [
            {
                "tick": i.tick,
                "source": i.source,
                "actionType": i.action_type,
                "description": i.description,
                "stabilityDelta": round(i.stability_delta or 0, 1),
                "targetBuilding": i.target_building_id,
            }
            for i in tracker.interventions
            if i.stability_delta and i.stability_delta >= 3
        ]

        # Build executive summary
        phase_reached = max(
            (t["phase"] for t in tracker.phase_transitions),
            key=lambda p: {"healthy": 0, "degrading": 1, "crisis": 2, "recovering": 3, "collapsed": 4}.get(p, 0),
            default="unknown"
        )

        if tracker.recovery_achieved:
            outcome_str = f"Full recovery achieved in {tracker.duration_ticks} ticks ({tracker.duration_ticks}s)."
        else:
            outcome_str = "System did not achieve stable recovery during this scenario."

        executive_summary = (
            f"Scenario reached {phase_reached} phase with operational stability dropping to "
            f"{worst.get('operationalStability', 100):.0f}%. "
            f"{outcome_str} "
            f"Automation contributed {automation_pct:.0f}% of recovery actions. "
            f"Crisis duration: {tracker.crisis_ticks} ticks vs estimated {est_without_automation_ticks} ticks without automation."
        )

        # Recommendations
        recommendations = []
        if worst.get('humanStrain', 0) > 75:
            recommendations.append(
                "Human strain peaked above 75% — pre-position additional on-call staff or increase "
                "ARIA (Operations Coordinator) autonomy to Level 3 to reduce manual intervention load."
            )
        if worst.get('systemTrust', 100) < 50:
            recommendations.append(
                "System trust dropped below 50% — implement a trust recovery protocol: "
                "reduce agent autonomy temporarily after trust drops, then gradually increase "
                "as agents demonstrate reliable decisions."
            )
        if len([j for j in tracker.uipath_jobs if j.final_state == 'Faulted']) > 0:
            recommendations.append(
                "UiPath automation faults detected — review process error handling in "
                "Incident_Escalation and Crisis_Response processes. Add retry logic with exponential backoff."
            )
        if tracker.crisis_ticks > 20:
            recommendations.append(
                f"Crisis phase lasted {tracker.crisis_ticks} ticks. Consider pre-activating "
                "failover infrastructure at the DEGRADING phase (stability < 60%) rather than waiting "
                "for full crisis. This alone could reduce crisis duration by 30-40%."
            )
        if automation_pct < 40:
            recommendations.append(
                "Automation contributed less than 40% of recovery. Increase agent autonomy levels "
                "(minimum Level 2 for incident response and operations coordinator) to reduce "
                "reliance on manual player intervention during real incidents."
            )
        if not recommendations:
            recommendations.append(
                "Scenario handled effectively. Consider running the same scenario with autonomy "
                "levels reduced by 1 to validate that automation is genuinely necessary rather than incidental."
            )

        # Recovery rate calculation
        worst_stability = worst.get("operationalStability", 100)
        worst_tick_idx = next(
            (i for i, s in enumerate(tracker.snapshots)
             if s.metrics["operationalStability"] == worst_stability),
            1
        )
        ticks_since_worst = max(1, tracker.duration_ticks - worst_tick_idx)
        recovery_rate = round(
            (last_snap.metrics["operationalStability"] - worst_stability) / ticks_since_worst,
            2
        )

        return {
            "reportId": f"aar-{tracker.scenario_id}",
            "generatedAt": time.time(),
            "scenarioId": tracker.scenario_id,
            "durationTicks": tracker.duration_ticks,
            "durationSeconds": round(time.time() - tracker.started_at, 1),
            "executiveSummary": executive_summary,
            "outcomeStatus": "recovered" if tracker.recovery_achieved else "degraded",
            "phaseTimeline": tracker.phase_transitions,
            "worstPhaseReached": phase_reached,
            "metrics": {
                "start": first_snap.metrics,
                "worst": worst,
                "end": last_snap.metrics,
                "recoveryRatePerTick": recovery_rate,
            },
            "mostAffectedBuildings": affected[:5],
            "crisisTicks": tracker.crisis_ticks,
            "estimatedCrisisWithoutAutomation": est_without_automation_ticks,
            "automationContributionPct": round(automation_pct, 1),
            "playerInterventionCount": len(player_interventions),
            "agentInterventionCount": len(agent_interventions),
            "effectiveInterventions": effective,
            "uipathJobs": [
                {
                    "jobId": j.job_id,
                    "processName": j.process_name,
                    "triggeredAtTick": j.triggered_at_tick,
                    "triggeredBy": j.triggered_by,
                    "state": j.final_state or "running",
                    "stabilityImpact": round(j.stability_impact or 0, 1),
                }
                for j in tracker.uipath_jobs
            ],
            "recommendations": recommendations,
        }
