"""
Custom scenario generator. Turns a short user description into a fully fleshed-out
scenario spec by invoking the 'scenario_gen' coded agent on the UiPath robot (which is
entitled to UiPath's LLM gateway), via the Orchestrator Jobs API.

NO silent fallbacks: if UiPath isn't configured, the job faults, or the output is
malformed, this raises a real HTTP error the UI surfaces — so you always know whether
it actually worked end-to-end through UiPath.

Flow: POST /generate (description -> robot job -> preview spec)  ->  user edits  ->  POST /register.
"""
import asyncio
import json
import logging
import os
import re
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scenarios.factory import SLOT_ORDER, build_scenario
from scenarios.registry import SCENARIO_REGISTRY, register_custom_spec

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scenario", tags=["Scenario Generator"])

GEN_AGENT = "scenario_gen"            # published coded-agent release name
AGENT_ROLES = ["ops_coord", "incident_resp", "compliance", "comms", "exec_strategy"]
JOB_TIMEOUT_S = 150                   # robot spin-up + LLM call


class GenerateRequest(BaseModel):
    description: str


class RegisterRequest(BaseModel):
    spec: Dict[str, Any]


def _slugify(name: str, taken: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "custom_scenario"
    sid, i = base, 2
    while sid in taken:
        sid = f"{base}_{i}"
        i += 1
    return sid


def _coerce_spec(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a generated/edited spec: assign a unique id, defend missing keys.
    Runs only on a REAL agent response — not a substitute for a failed generation."""
    raw = dict(raw)
    raw["id"] = _slugify(raw.get("name", "custom"), set(SCENARIO_REGISTRY.keys()))
    raw.setdefault("color", "#6366F1")
    raw.setdefault("icon", "🏙️")
    for key in ("tagline", "description", "industry", "industry_context"):
        raw.setdefault(key, "")
    raw.setdefault("vocabulary", {})
    raw.setdefault("compliance_frameworks", [])
    raw.setdefault("uipath_processes", [])
    raw.setdefault("outage_presets", [])
    slots = raw.get("slots", {})
    for role in SLOT_ORDER:
        s = slots.get(role) or {}
        s.setdefault("id", role)
        s.setdefault("name", role.replace("_", " ").title())
        s.setdefault("icon", "🏢")
        slots[role] = s
    raw["slots"] = slots
    agents = raw.get("agents", {})
    for role in AGENT_ROLES:
        agents.setdefault(role, role.upper())
    raw["agents"] = agents
    return raw


def _uipath_cfg():
    cid, sec = os.getenv("UIPATH_CLIENT_ID"), os.getenv("UIPATH_CLIENT_SECRET")
    org, tenant = os.getenv("UIPATH_ORGANIZATION"), os.getenv("UIPATH_TENANT")
    base = os.getenv("UIPATH_CLOUD_URL", "https://cloud.uipath.com")
    fid = os.getenv("UIPATH_FOLDER_ID")
    placeholders = {None, "", "your-client-id", "your-client-secret", "your-org-name", "your-tenant-name", "your-folder-id"}
    if any(v in placeholders for v in (cid, sec, org, tenant, fid)):
        return None
    return {"cid": cid, "sec": sec, "org": org, "tenant": tenant, "base": base, "fid": fid,
            "orch": f"{base}/{org}/{tenant}/orchestrator_"}


async def _invoke_generator_agent(description: str) -> Dict[str, Any]:
    """Run the scenario_gen coded agent on the robot and return the parsed spec. Raises on failure."""
    cfg = _uipath_cfg()
    if not cfg:
        raise HTTPException(status_code=503, detail="UiPath is not configured — set UiPath credentials in the backend .env.")

    async with httpx.AsyncClient(timeout=30.0) as c:
        tok_resp = await c.post(f"{cfg['base']}/identity_/connect/token", data={
            "grant_type": "client_credentials", "client_id": cfg["cid"], "client_secret": cfg["sec"],
            "scope": "OR.Jobs OR.Jobs.Write OR.Execution OR.Folders OR.Tasks OR.Administration",
        })
        if tok_resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"UiPath auth failed: {tok_resp.status_code}")
        token = tok_resp.json()["access_token"]
        HF = {"Authorization": f"Bearer {token}", "X-UIPATH-OrganizationUnitId": str(cfg["fid"]), "Content-Type": "application/json"}

        rels = (await c.get(f"{cfg['orch']}/odata/Releases?$filter=ProcessKey eq '{GEN_AGENT}'", headers=HF)).json().get("value", [])
        if not rels:
            raise HTTPException(status_code=502, detail=f"Scenario generator agent '{GEN_AGENT}' is not published to the MaestroCity folder.")
        release_key = rels[0]["Key"]

        start = await c.post(
            f"{cfg['orch']}/odata/Jobs/UiPath.Server.Configuration.OData.StartJobs", headers=HF,
            json={"startInfo": {"ReleaseKey": release_key, "Strategy": "ModernJobsCount", "JobsCount": 1,
                                "RuntimeType": "Serverless", "InputArguments": json.dumps({"description": description.strip()})}},
        )
        if start.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"Could not start generator job: {start.text[:200]}")
        job_id = start.json()["value"][0]["Id"]

    # Poll for completion
    waited = 0
    async with httpx.AsyncClient(timeout=20.0) as c:
        while waited < JOB_TIMEOUT_S:
            await asyncio.sleep(5)
            waited += 5
            st = (await c.get(f"{cfg['orch']}/odata/Jobs({job_id})", headers=HF)).json()
            state = st.get("State")
            if state == "Successful":
                out_raw = st.get("OutputArguments")
                if not out_raw:
                    raise HTTPException(status_code=502, detail="Generator job returned no output.")
                try:
                    spec_str = json.loads(out_raw).get("spec", "")
                    return json.loads(spec_str)
                except (json.JSONDecodeError, TypeError) as e:
                    raise HTTPException(status_code=502, detail=f"Generator returned invalid JSON: {e}")
            if state in ("Faulted", "Stopped"):
                raise HTTPException(status_code=502, detail=f"UiPath generator job {state.lower()}: {(st.get('Info') or '')[:300]}")
    raise HTTPException(status_code=504, detail=f"UiPath generator job timed out after {JOB_TIMEOUT_S}s.")


@router.post("/generate")
async def generate_scenario(req: GenerateRequest) -> Dict[str, Any]:
    """Generate a preview spec by running the scenario_gen agent on UiPath. No fallback."""
    if not req.description.strip():
        raise HTTPException(status_code=400, detail="Please enter a description.")

    raw = await _invoke_generator_agent(req.description)  # raises HTTPException on any failure
    spec = _coerce_spec(raw)
    try:
        build_scenario(spec)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Generated scenario was malformed: {e}")
    return {"spec": spec, "generatedBy": f"UiPath robot · {GEN_AGENT} agent"}


@router.post("/register")
async def register_scenario(req: RegisterRequest) -> Dict[str, Any]:
    """Register a (possibly user-edited) spec as a live, selectable scenario."""
    try:
        spec = _coerce_spec(req.spec)
        definition = register_custom_spec(spec)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid scenario spec: {e}")
    return {"id": definition.id, "name": definition.name, "registered": True}
