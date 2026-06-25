Good question — that was me overcomplicating it. "(+ aria)" meant putting two agent tasks in the Respond stage (SENTINEL and ARIA). You don't need to — it's cleaner to give each agent its own stage.

Here's the simpler, cleaner mapping — one agent per stage:

#	Stage	Agent	What it does
1	Detect & Assess	apex	assess situation, declare crisis level
2	Respond	sentinel	triage incident, run recovery
3	Stabilize Operations	aria	reroute workflows, adjust staffing
4	Compliance Gate	veritas + Human approval task	flag risk → human approves (Action Center)
5	Communicate & Resolve	echo	notify stakeholders, close case
★ Insight ─────────────────────────────────────

One agent per stage reads as a clean case lifecycle: detect → respond → stabilize → approve → communicate. Each of your 5 agents gets a clear job, and stage 4's human-approval task is the case-management handoff that defines Track 1. Much easier to demo than two agents crammed in one stage.
─────────────────────────────────────────────────
So: this first stage (Detect & Assess) → bind apex. Then add 4 more stages and bind sentinel / aria / veritas / echo in order, plus the human-approval task in the Compliance Gate stage.

Go ahead and rebind this stage to apex (Refresh → remove aria → pick apex), then add the next stage. Screenshot when you've got apex bound + are ready to add stage 2, and I'll keep you moving.