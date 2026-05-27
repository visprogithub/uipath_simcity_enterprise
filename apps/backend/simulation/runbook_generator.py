import time
from typing import Dict, Any, List

from simulation.scenario_tracker import ScenarioTracker


class RunbookGenerator:
    def generate(self, tracker: ScenarioTracker, buildings_config: list) -> Dict[str, Any]:
        """Generate an operational runbook from scenario data."""

        if not tracker.snapshots:
            return {"error": "No scenario data to generate runbook from"}

        # Identify the primary failure event
        phase_transitions = tracker.phase_transitions
        first_crisis = next((t for t in phase_transitions if t["phase"] == "crisis"), None)

        # Identify trigger conditions (what metrics were at when crisis started)
        trigger_snap = None
        if first_crisis:
            trigger_snap = next(
                (s for s in tracker.snapshots if s.tick == first_crisis["tick"]), None
            )

        # Build trigger conditions
        trigger_conditions = []
        if trigger_snap:
            for metric, value in trigger_snap.metrics.items():
                if metric == "operationalStability" and value < 70:
                    trigger_conditions.append({
                        "metric": metric,
                        "threshold": "< 70",
                        "observedValue": round(value, 1),
                        "severity": "WARNING" if value > 50 else "CRITICAL",
                    })
                elif metric == "humanStrain" and value > 65:
                    trigger_conditions.append({
                        "metric": metric,
                        "threshold": "> 65",
                        "observedValue": round(value, 1),
                        "severity": "WARNING",
                    })
                elif metric == "serviceAvailability" and value < 60:
                    trigger_conditions.append({
                        "metric": metric,
                        "threshold": "< 60",
                        "observedValue": round(value, 1),
                        "severity": "CRITICAL",
                    })

        # Find most affected building for title
        affected_buildings = []
        for bconf in buildings_config:
            bid = bconf["id"]
            healths = [s.building_healths.get(bid, 100) for s in tracker.snapshots]
            if min(healths) < 50:
                affected_buildings.append(bconf["name"])

        title = f"{'Cloud Infrastructure' if 'CloudCore' in str(affected_buildings) else 'Enterprise'} Failure Response Runbook"
        if affected_buildings:
            title = f"{affected_buildings[0]} Failure Response Runbook"

        # Build action steps from effective interventions
        steps = []
        step_num = 1

        # Group effective interventions by time window
        effective = [
            i for i in tracker.interventions
            if i.stability_delta and i.stability_delta >= 2
        ]

        # Immediate actions (first 5 ticks of crisis)
        immediate = [i for i in effective if first_crisis and i.tick <= (first_crisis["tick"] + 5)]
        short_term = [i for i in effective if first_crisis and first_crisis["tick"] + 5 < i.tick <= first_crisis["tick"] + 20]
        recovery = [i for i in effective if first_crisis and i.tick > first_crisis["tick"] + 20]

        def make_step(intervention, urgency_label: str) -> Dict:
            nonlocal step_num
            action_descriptions = {
                "trigger_outage": "Acknowledge the outage alert",
                "activate_failover": "Activate failover infrastructure to restore service continuity",
                "set_staffing": "Increase staffing allocation to affected building",
                "set_autonomy": "Adjust agent autonomy level to accelerate automated response",
                "restore_building": "Initiate manual restoration procedure for affected system",
                "acknowledge_alert": "Acknowledge and triage incoming alert",
            }
            uipath_process_map = {
                "activate_failover": "Incident_Escalation",
                "set_autonomy": None,
                "set_staffing": "Emergency_Staffing",
                "restore_building": "Trust_Recovery_Protocol",
            }

            step = {
                "stepNumber": step_num,
                "urgency": urgency_label,
                "action": action_descriptions.get(intervention.action_type, intervention.description),
                "detail": intervention.description,
                "targetSystem": intervention.target_building_id,
                "performedBy": "automated" if intervention.source != "player" else "manual",
                "automatingAgent": intervention.source if intervention.source != "player" else None,
                "uipathProcess": uipath_process_map.get(intervention.action_type),
                "expectedEffect": f"+{intervention.stability_delta:.0f}% operational stability",
                "timeWindowMinutes": 2 if urgency_label == "IMMEDIATE" else (10 if urgency_label == "SHORT_TERM" else 30),
                "validatedInSimulation": True,
                "observedEffectTick": intervention.tick,
            }
            step_num += 1
            return step

        for i in immediate:
            steps.append(make_step(i, "IMMEDIATE"))
        for i in short_term:
            steps.append(make_step(i, "SHORT_TERM"))
        for i in recovery:
            steps.append(make_step(i, "RECOVERY"))

        # Escalation chain derived from UiPath jobs triggered
        escalation_chain = []
        seen_processes = set()
        for job in tracker.uipath_jobs:
            if job.process_name not in seen_processes:
                seen_processes.add(job.process_name)
                trigger_tick = job.triggered_at_tick
                trigger_snap_j = next((s for s in tracker.snapshots if s.tick >= trigger_tick), None)
                escalation_chain.append({
                    "level": len(escalation_chain) + 1,
                    "triggerCondition": (
                        f"operationalStability < {trigger_snap_j.metrics['operationalStability']:.0f}"
                        if trigger_snap_j else "system degradation detected"
                    ),
                    "action": f"Trigger UiPath process: {job.process_name}",
                    "uipathProcess": job.process_name,
                    "automatedBy": job.triggered_by,
                    "outcome": job.final_state or "pending",
                })

        # Recovery milestones
        milestones = []
        recovery_buildings = ["hospital", "pharmacy", "cloud_datacenter"]
        for bid in recovery_buildings:
            healths = [(s.tick, s.building_healths.get(bid, 100)) for s in tracker.snapshots]
            crash_tick = next((t for t, h in healths if h < 50), None)
            recovery_t = next((t for t, h in healths if h > 70 and t > (crash_tick or 0)), None)
            if crash_tick is not None:
                bname = next((b["name"] for b in buildings_config if b["id"] == bid), bid)
                milestones.append({
                    "milestone": f"{bname} restored",
                    "targetMinutes": 15,
                    "achievedTick": recovery_t,
                    "achievedMinutes": recovery_t if recovery_t else None,
                    "status": "achieved" if recovery_t else "not_achieved",
                })

        # Generate markdown text
        markdown = self._generate_markdown(title, trigger_conditions, steps, escalation_chain, milestones, tracker)

        return {
            "runbookId": f"rb-{tracker.scenario_id}",
            "title": title,
            "generatedAt": time.time(),
            "validated": tracker.recovery_achieved,
            "scenarioId": tracker.scenario_id,
            "triggerConditions": trigger_conditions,
            "immediateActions": [s for s in steps if s["urgency"] == "IMMEDIATE"],
            "shortTermActions": [s for s in steps if s["urgency"] == "SHORT_TERM"],
            "recoveryActions": [s for s in steps if s["urgency"] == "RECOVERY"],
            "escalationChain": escalation_chain,
            "recoveryMilestones": milestones,
            "estimatedRecoveryMinutes": tracker.crisis_ticks,
            "markdownContent": markdown,
        }

    def _generate_markdown(self, title, triggers, steps, escalation, milestones, tracker) -> str:
        lines = [
            f"# {title}",
            f"",
            f"> **Generated by Maestro City simulation — validated {'yes' if tracker.recovery_achieved else 'PARTIAL'}**  ",
            f"> Scenario: `{tracker.scenario_id}` | Duration: {tracker.duration_ticks} ticks | Crisis ticks: {tracker.crisis_ticks}",
            f"",
            f"## Trigger Conditions",
            f"",
        ]
        for t in triggers:
            lines.append(f"- `{t['metric']}` **{t['threshold']}** (observed: {t['observedValue']}) — Severity: **{t['severity']}**")

        if not triggers:
            lines.append("- No critical threshold breaches recorded during this scenario.")

        lines += ["", "## Escalation Chain", ""]
        for e in escalation:
            lines.append(f"### Level {e['level']}: {e['action']}")
            lines.append(f"- **Trigger**: `{e['triggerCondition']}`")
            lines.append(f"- **UiPath Process**: `{e['uipathProcess']}`")
            lines.append(f"- **Automated by**: {e['automatedBy']}")
            lines.append(f"- **Outcome in simulation**: {e['outcome']}")
            lines.append("")

        if not escalation:
            lines.append("- No UiPath automation processes were triggered during this scenario.")
            lines.append("")

        lines += ["## Response Steps", ""]
        for urgency in ["IMMEDIATE", "SHORT_TERM", "RECOVERY"]:
            urgency_steps = [s for s in steps if s["urgency"] == urgency]
            if urgency_steps:
                lines.append(f"### {urgency.replace('_', ' ').title()} Actions")
                lines.append("")
                for s in urgency_steps:
                    lines.append(f"**Step {s['stepNumber']}** — `{s['action']}`")
                    lines.append(f"- Target system: `{s['targetSystem'] or 'all'}`")
                    lines.append(f"- Performed by: {s['performedBy']}" + (f" ({s['automatingAgent']})" if s['automatingAgent'] else ""))
                    if s['uipathProcess']:
                        lines.append(f"- UiPath automation: `{s['uipathProcess']}`")
                    lines.append(f"- Expected effect: {s['expectedEffect']}")
                    lines.append(f"- Time window: {s['timeWindowMinutes']} minutes")
                    lines.append("")

        if not steps:
            lines.append("- No effective interventions recorded. Run scenario longer or trigger a crisis event.")
            lines.append("")

        lines += ["## Recovery Milestones", ""]
        for m in milestones:
            status_icon = "[ACHIEVED]" if m["status"] == "achieved" else "[NOT ACHIEVED]"
            lines.append(f"- {status_icon} **{m['milestone']}** — target: {m['targetMinutes']}min, achieved: {str(m['achievedMinutes']) + ' ticks' if m['achievedMinutes'] else 'NOT ACHIEVED'}")

        if not milestones:
            lines.append("- No tracked buildings reached critical health threshold during this scenario.")

        lines += ["", "---", f"*Generated by Maestro City | {title} | Not a substitute for incident commander judgment*"]
        return "\n".join(lines)
