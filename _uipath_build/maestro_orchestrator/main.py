"""Maestro Case orchestrator — a UiPath coded agent that runs the multi-agent crisis
response ON the platform.

When the Maestro Case starts, this agent fans out to the five operational coded agents
(aria, sentinel, veritas, echo, apex) as REAL Orchestrator jobs, waits for each one's
recommendation (produced via the UiPath LLM Gateway), and aggregates them into a single
coordinated directive. Every agent call is a real serverless job — this is the
orchestration layer executing on UiPath, not a stub.

Child agents are started with the same StartJobs (ModernJobsCount / Serverless) pattern the
backend uses, then polled to completion. URL/token/folder come from the robot-injected
environment (with MaestroCity defaults for local runs).
"""
import asyncio
import json
import os

import httpx
from langgraph.graph import START, StateGraph, END
from pydantic import BaseModel

AGENTS = ["aria", "sentinel", "veritas", "echo", "apex"]

_URL = os.environ.get("UIPATH_URL", "https://staging.uipath.com/hackathon26_313/DefaultTenant").rstrip("/")
_ORCH = f"{_URL}/orchestrator_"
_FOLDER_ID = (os.environ.get("UIPATH_FOLDER_ID")
              or os.environ.get("UIPATH_ORGANIZATION_UNIT_ID")
              or "3084969")  # MaestroCity folder
_POLL_SECONDS = 5
_POLL_TRIES = 24  # ~120s per agent (they run in parallel)


class CaseInput(BaseModel):
    context: str = "{}"
    phase: str = "unknown"
    tick: int = 0


class CaseOutput(BaseModel):
    directive: str
    escalated: bool
    invokedAgents: int
    agentResults: str  # JSON: [{agent, recommendation, escalate, ok, jobId}]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ.get('UIPATH_ACCESS_TOKEN', '')}",
        "X-UIPATH-OrganizationUnitId": str(_FOLDER_ID),
        "Content-Type": "application/json",
    }


async def _invoke_agent(client: httpx.AsyncClient, name: str, args: dict) -> dict:
    """Start one coded agent as a real serverless job, poll to completion, return its output."""
    res = {"agent": name, "recommendation": "", "escalate": False, "ok": False, "jobId": None}
    try:
        rel = (await client.get(
            f"{_ORCH}/odata/Releases", params={"$filter": f"ProcessKey eq '{name}'"},
            headers=_headers())).json().get("value", [])
        if not rel:
            res["recommendation"] = "(release not found)"
            return res
        start = await client.post(
            f"{_ORCH}/odata/Jobs/UiPath.Server.Configuration.OData.StartJobs",
            headers=_headers(),
            json={"startInfo": {"ReleaseKey": rel[0]["Key"], "Strategy": "ModernJobsCount",
                                "RuntimeType": "Serverless", "JobsCount": 1,
                                "InputArguments": json.dumps(args)}})
        jid = start.json()["value"][0]["Id"]
        res["jobId"] = jid
        for _ in range(_POLL_TRIES):
            await asyncio.sleep(_POLL_SECONDS)
            st = (await client.get(f"{_ORCH}/odata/Jobs({jid})", headers=_headers())).json()
            state = st.get("State")
            if state in ("Successful", "Faulted", "Stopped"):
                out = st.get("OutputArguments")
                data = json.loads(out) if isinstance(out, str) and out else {}
                res["recommendation"] = str(data.get("recommendation", ""))[:500]
                res["escalate"] = bool(data.get("escalate", False))
                res["ok"] = state == "Successful"
                return res
        res["recommendation"] = "(timed out)"
        return res
    except Exception as e:  # noqa: BLE001 — fail soft per-agent; never fail the whole Case
        res["recommendation"] = f"(error: {str(e)[:140]})"
        return res


async def run_case(state: CaseInput) -> CaseOutput:
    args = {"context": state.context, "phase": state.phase, "tick": state.tick}
    async with httpx.AsyncClient(timeout=30.0) as client:
        results = await asyncio.gather(
            *[_invoke_agent(client, name, {**args, "agentId": name}) for name in AGENTS]
        )

    escalating = [r for r in results if r["escalate"]]
    ok = [r for r in results if r["ok"] and r["recommendation"]]
    head = (f"{len(escalating)}/5 agents flagged escalation. " if escalating
            else "Coordinated response — no escalation flagged. ")
    body = "  ".join(f"[{r['agent'].upper()}] {r['recommendation']}" for r in ok)
    directive = (head + body)[:1500] or "No agent recommendations returned."

    return CaseOutput(
        directive=directive,
        escalated=bool(escalating),
        invokedAgents=sum(1 for r in results if r["ok"]),
        agentResults=json.dumps(results),
    )


builder = StateGraph(CaseInput, output=CaseOutput)
builder.add_node("run_case", run_case)
builder.add_edge(START, "run_case")
builder.add_edge("run_case", END)
graph = builder.compile()
