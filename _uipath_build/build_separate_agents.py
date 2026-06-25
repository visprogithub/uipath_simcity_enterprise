"""Publish the 5 Maestro City operational agents as SEPARATE named coded-agent packages
(so each shows distinctly in the Maestro agent picker). Generates a project per agent,
compiles/publishes via the uipath CLI, and creates a release in the MaestroCity folder."""
import glob
import os
import subprocess

import httpx
from dotenv import dotenv_values

V = dotenv_values("e:/Repos/uipath_simcity_enterprise/apps/backend/.env")
BASE = "https://staging.uipath.com"
ORG, TEN, FID = V["UIPATH_ORGANIZATION"], V["UIPATH_TENANT"], V["UIPATH_FOLDER_ID"]
ORCH = f"{BASE}/{ORG}/{TEN}/orchestrator_"
TOKEN = httpx.post(f"{BASE}/identity_/connect/token", data={
    "grant_type": "client_credentials", "client_id": V["UIPATH_CLIENT_ID"],
    "client_secret": V["UIPATH_CLIENT_SECRET"],
    "scope": "OR.Jobs OR.Jobs.Write OR.Execution OR.Folders OR.Tasks OR.Administration"}, timeout=30).json()["access_token"]

# agent package name -> (display label, system prompt, task hint)
AGENTS = {
    "apex": ("APEX — Executive Strategy",
             "You are APEX, the AI Executive Strategy agent for Maestro City. Synthesize the situation, declare a crisis level (1 Elevated / 2 Crisis / 3 Emergency) based on operational stability and degraded systems, and decide enterprise response. Always route >$500K-impact or patient-system-offline decisions to a human.",
             "Assess the situation, declare a crisis level, and give the executive decision."),
    "sentinel": ("SENTINEL — Incident Response",
                 "You are SENTINEL, the AI Incident Response agent for Maestro City. Triage incidents by priority (P1 patient-facing within 2 min), pick a recovery playbook (Restart_EHR_Service, Activate_Backup_Datacenter, Emergency_Pharmacy_Reroute, Cascade_Isolation), and request VERITAS sign-off before touching medication records.",
                 "Triage the incident and give the recovery action."),
    "veritas": ("VERITAS — Compliance & Audit",
                "You are VERITAS, the AI Compliance agent for Maestro City. Enforce HIPAA/SOC2/Joint Commission. Gate high-risk actions: medication-record or dosage changes and bulk EHR exports require human approval via Action Center. Autonomy 1 — never approve your own high/critical-risk waivers.",
                "Assess compliance risk and state whether human approval is required."),
    "echo": ("ECHO — Communications",
             "You are ECHO, the AI Communications agent for Maestro City. Route alerts by severity/department, deduplicate, translate technical alerts to plain language for clinical staff, and activate fallback channels (SMS/PA/pager) if comms degrade. Keep messages under 160 chars with an impact score.",
             "Give the alert routing / communication action."),
    "aria": ("ARIA — Operations Coordinator",
             "You are ARIA, the AI Operations Coordinator for Maestro City. Maintain operational stability: monitor health/queues, reroute workflows, adjust staffing, and activate failover (only if backup health > 40%). Prefer minimal-impact actions first; escalate to APEX/SENTINEL when stability < 70%.",
             "Give your single highest-priority operational recommendation."),
}

MAIN = '''from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph, END
from uipath_langchain.chat import UiPathAzureChatOpenAI
from pydantic import BaseModel

SYSTEM = """{prompt}"""
HINT = "{hint}"

class GraphState(BaseModel):
    agentId: str = "{name}"
    context: str = "{{}}"
    phase: str = "unknown"
    tick: int = 0

class GraphOutput(BaseModel):
    recommendation: str
    escalate: bool

async def run_agent(state: GraphState) -> GraphOutput:
    llm = UiPathAzureChatOpenAI(model="gpt-4.1-mini-2025-04-14")
    human = f"Phase: {{state.phase}} (tick {{state.tick}}). Context (JSON): {{state.context}}\\n\\n" + HINT + " Be concise (2-3 sentences). State explicitly whether this must be escalated."
    res = await llm.ainvoke([SystemMessage(SYSTEM), HumanMessage(human)])
    text = res.content if isinstance(res.content, str) else str(res.content)
    return GraphOutput(recommendation=text, escalate=("escalat" in text.lower()))

builder = StateGraph(GraphState, output=GraphOutput)
builder.add_node("run_agent", run_agent)
builder.add_edge(START, "run_agent"); builder.add_edge("run_agent", END)
graph = builder.compile()
'''

PYPROJECT = '''[project]
name = "{name}"
version = "1.0.0"
description = "{label}"
authors = [{{ name = "Maestro City", email = "djbobbysocks@gmail.com" }}]
dependencies = [ "uipath-langchain>=0.13.0, <0.14.0" ]
requires-python = ">=3.11"
'''

VER = "1.0.2"  # > existing aria bundle (1.0.0) to avoid version collision

env = dict(os.environ)
env["UIPATH_URL"] = f"{BASE}/{ORG}/{TEN}"
env["UIPATH_ACCESS_TOKEN"] = TOKEN
HF = {"Authorization": f"Bearer {TOKEN}", "X-UIPATH-OrganizationUnitId": str(FID), "Content-Type": "application/json"}

for name, (label, prompt, hint) in AGENTS.items():
    d = f"agents_sep/{name}"
    os.makedirs(d, exist_ok=True)
    open(f"{d}/main.py", "w", encoding="utf-8").write(MAIN.format(prompt=prompt.replace('"', "'"), hint=hint.replace('"', "'"), name=name))
    open(f"{d}/langgraph.json", "w", encoding="utf-8").write('{"graphs": {"%s": "./main.py:graph"}}' % name)
    open(f"{d}/pyproject.toml", "w", encoding="utf-8").write(PYPROJECT.format(name=name, label=label).replace('version = "1.0.0"', f'version = "{VER}"'))
    subprocess.run(["uipath", "init"], cwd=d, env=env, capture_output=True, text=True)
    subprocess.run(["uipath", "pack"], cwd=d, env=env, capture_output=True, text=True)
    pub = subprocess.run(["uipath", "publish", "--tenant"], cwd=d, env=env, capture_output=True, text=True)
    ok = "successfully" in (pub.stdout + pub.stderr).lower()
    ex = httpx.get(f"{ORCH}/odata/Releases?$filter=ProcessKey eq '{name}'", headers=HF, timeout=20).json().get("value", [])
    if ex:
        httpx.patch(f"{ORCH}/odata/Releases({ex[0]['Id']})", headers=HF, json={"ProcessVersion": VER}, timeout=30)
    else:
        httpx.post(f"{ORCH}/odata/Releases", headers=HF, json={"Name": name, "ProcessKey": name, "ProcessVersion": VER}, timeout=30)
    print(f"[{name}] publish ok={ok}, release ready")

print("done")
