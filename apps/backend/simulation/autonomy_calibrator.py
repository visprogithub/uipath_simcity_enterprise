import time
from typing import Dict, Any, List

from simulation.scenario_tracker import ScenarioTracker

AGENT_NAMES = {
    "ops_coord": "ARIA (Operations Coordinator)",
    "incident_resp": "SENTINEL (Incident Response)",
    "compliance": "VERITAS (Compliance)",
    "comms": "ECHO (Communications)",
    "exec_strategy": "APEX (Executive Strategy)",
}

AGENT_ROLES = {
    "ops_coord": "Workflow routing and queue management",
    "incident_resp": "Outage detection and escalation",
    "compliance": "Approval gating and audit",
    "comms": "Alert management and notifications",
    "exec_strategy": "KPI monitoring and strategic resource allocation",
}


class AutonomyCalibrator:
    def __init__(self):
        self._scenario_history: List[Dict] = []

    def record_scenario_result(self, tracker: ScenarioTracker, agents_snapshot: list):
        """Record the outcome of a completed scenario for calibration."""
        self._scenario_history.append({
            "scenario_id": tracker.scenario_id,
            "recovery_achieved": tracker.recovery_achieved,
            "crisis_ticks": tracker.crisis_ticks,
            "duration_ticks": tracker.duration_ticks,
            "worst_stability": tracker.worst_metrics.get("operationalStability", 100) if tracker.worst_metrics else 100,
            "agents": {a.id: {
                "autonomyLevel": a.autonomyLevel,
                "trustScore": a.trustScore,
                "actionsThisTick": a.actionsThisTick,
            } for a in agents_snapshot},
            "agent_interventions_by_id": {},
            "timestamp": time.time(),
        })

    def generate_calibration(self, tracker: ScenarioTracker, agents: list) -> Dict[str, Any]:
        """Generate autonomy calibration certificate from scenario data."""

        agent_results = {}

        for agent in agents:
            aid = agent.id
            # Gather this agent's interventions
            agent_interventions = [i for i in tracker.interventions if i.source == aid]

            positive = [i for i in agent_interventions if i.stability_delta and i.stability_delta > 2]
            negative = [i for i in agent_interventions if i.stability_delta and i.stability_delta < -2]
            neutral = [i for i in agent_interventions
                      if i not in positive and i not in negative]

            total = len(agent_interventions)
            accuracy = (len(positive) / total * 100) if total > 0 else 100.0

            # Current level
            current_level = agent.autonomyLevel
            current_trust = agent.trustScore

            # Recommend level based on performance
            if total == 0:
                recommended_level = current_level
                rationale = f"No autonomous actions taken at Level {current_level}. Insufficient data to recommend change."
            elif accuracy >= 85 and current_trust >= 80 and len(positive) >= 3:
                recommended_level = min(4, current_level + 1)
                rationale = (
                    f"{AGENT_NAMES.get(aid, aid)} achieved {accuracy:.0f}% action accuracy across {total} interventions "
                    f"(+{len(positive)} effective, {len(negative)} counterproductive). "
                    f"Trust score {current_trust:.0f}/100. Evidence supports upgrading to Level {recommended_level}."
                )
            elif accuracy < 60 or current_trust < 50:
                recommended_level = max(0, current_level - 1)
                rationale = (
                    f"{AGENT_NAMES.get(aid, aid)} action accuracy at {accuracy:.0f}% with trust score {current_trust:.0f}/100. "
                    f"Reducing to Level {recommended_level} until accuracy exceeds 75% over 3 scenarios."
                )
            else:
                recommended_level = current_level
                rationale = (
                    f"{AGENT_NAMES.get(aid, aid)} performing adequately at Level {current_level} "
                    f"({accuracy:.0f}% accuracy, {total} actions). Maintain current level."
                )

            agent_results[aid] = {
                "agentId": aid,
                "agentName": AGENT_NAMES.get(aid, aid),
                "role": AGENT_ROLES.get(aid, ""),
                "currentLevel": current_level,
                "recommendedLevel": recommended_level,
                "trustScore": round(current_trust, 1),
                "totalActions": total,
                "effectiveActions": len(positive),
                "counterproductiveActions": len(negative),
                "accuracyPct": round(accuracy, 1),
                "stabilityContribution": round(
                    sum(i.stability_delta for i in positive if i.stability_delta), 1
                ),
                "rationale": rationale,
                "readyForUpgrade": recommended_level > current_level,
                "requiresDowngrade": recommended_level < current_level,
            }

        # Overall org readiness
        avg_accuracy = sum(r["accuracyPct"] for r in agent_results.values()) / max(1, len(agent_results))
        avg_trust = sum(r["trustScore"] for r in agent_results.values()) / max(1, len(agent_results))

        ready_for_upgrade = [aid for aid, r in agent_results.items() if r["readyForUpgrade"]]
        requires_downgrade = [aid for aid, r in agent_results.items() if r["requiresDowngrade"]]

        # Determine overall org level
        levels = [r["recommendedLevel"] for r in agent_results.values()]
        min_level = min(levels) if levels else 0
        max_level = max(levels) if levels else 0

        if min_level == max_level:
            overall_recommendation = f"Uniform Level {min_level} across all agents"
        else:
            overall_recommendation = f"Differentiated: Level {min_level}-{max_level} depending on agent role"

        # Overall assessment
        if avg_accuracy >= 80 and tracker.recovery_achieved and avg_trust >= 75:
            overall_assessment = "READY_FOR_EXPANDED_AUTOMATION"
            assessment_label = "Ready for Expanded Automation"
            assessment_color = "success"
        elif avg_accuracy >= 65 and tracker.recovery_achieved:
            overall_assessment = "ADEQUATE_WITH_MONITORING"
            assessment_label = "Adequate — Continue with Monitoring"
            assessment_color = "warning"
        else:
            overall_assessment = "REQUIRES_HUMAN_OVERSIGHT"
            assessment_label = "Requires Increased Human Oversight"
            assessment_color = "danger"

        # Build evidence trail
        evidence = []
        if tracker.recovery_achieved:
            evidence.append(f"Recovery achieved within {tracker.duration_ticks} ticks")
        else:
            evidence.append(f"Recovery not achieved — {tracker.crisis_ticks} ticks in crisis")

        uipath_successes = sum(1 for j in tracker.uipath_jobs if j.final_state == "Successful")
        if tracker.uipath_jobs:
            evidence.append(f"{uipath_successes}/{len(tracker.uipath_jobs)} UiPath automation jobs completed successfully")

        agent_interventions_total = sum(r["totalActions"] for r in agent_results.values())
        if agent_interventions_total > 0:
            evidence.append(f"{agent_interventions_total} total autonomous actions, {avg_accuracy:.0f}% effective")

        return {
            "certificateId": f"cal-{tracker.scenario_id}",
            "generatedAt": time.time(),
            "scenarioId": tracker.scenario_id,
            "overallAssessment": overall_assessment,
            "assessmentLabel": assessment_label,
            "assessmentColor": assessment_color,
            "averageAccuracyPct": round(avg_accuracy, 1),
            "averageTrustScore": round(avg_trust, 1),
            "overallRecommendation": overall_recommendation,
            "agentsReadyForUpgrade": ready_for_upgrade,
            "agentsRequiringDowngrade": requires_downgrade,
            "agentCalibrations": list(agent_results.values()),
            "evidenceTrail": evidence,
            "scenarioOutcome": "recovered" if tracker.recovery_achieved else "degraded",
            "crisisTicks": tracker.crisis_ticks,
            "validForScenarios": 1,
            "nextReviewRecommendedAfterScenarios": 3,
            "note": (
                "This calibration is based on a single scenario run. "
                "For production autonomy decisions, run 5+ scenarios across different crisis types. "
                "This certificate documents simulation-validated readiness, not production certification."
            ),
        }
