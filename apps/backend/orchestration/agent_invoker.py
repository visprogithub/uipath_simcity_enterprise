"""
Shared helper to invoke a published UiPath coded agent on the robot via the Jobs API
and return its parsed OutputArguments. Used by the scenario generator and the coding agent.

NO fallback: any failure (UiPath unconfigured, auth, job fault, timeout, bad output)
raises an HTTPException that surfaces in the UI — so you always know whether it really ran.
"""
import asyncio
import json
import os

import httpx
from fastapi import HTTPException


def _cfg():
    cid, sec = os.getenv("UIPATH_CLIENT_ID"), os.getenv("UIPATH_CLIENT_SECRET")
    org, tenant = os.getenv("UIPATH_ORGANIZATION"), os.getenv("UIPATH_TENANT")
    base = os.getenv("UIPATH_CLOUD_URL", "https://cloud.uipath.com")
    fid = os.getenv("UIPATH_FOLDER_ID")
    ph = {None, "", "your-client-id", "your-client-secret", "your-org-name", "your-tenant-name", "your-folder-id"}
    if any(v in ph for v in (cid, sec, org, tenant, fid)):
        return None
    return {"cid": cid, "sec": sec, "fid": fid,
            "base": base, "orch": f"{base}/{org}/{tenant}/orchestrator_"}


async def invoke_agent_job(release_name: str, input_args: dict, timeout_s: int = 150) -> dict:
    """Start the named coded-agent release on a serverless robot, wait, return its output dict."""
    cfg = _cfg()
    if not cfg:
        raise HTTPException(status_code=503, detail="UiPath is not configured — set UiPath credentials in the backend .env.")

    async with httpx.AsyncClient(timeout=30.0) as c:
        tr = await c.post(f"{cfg['base']}/identity_/connect/token", data={
            "grant_type": "client_credentials", "client_id": cfg["cid"], "client_secret": cfg["sec"],
            "scope": "OR.Jobs OR.Jobs.Write OR.Execution OR.Folders OR.Tasks OR.Administration"})
        if tr.status_code != 200:
            raise HTTPException(status_code=502, detail=f"UiPath auth failed: HTTP {tr.status_code}")
        token = tr.json()["access_token"]
        HF = {"Authorization": f"Bearer {token}", "X-UIPATH-OrganizationUnitId": str(cfg["fid"]), "Content-Type": "application/json"}

        rels = (await c.get(f"{cfg['orch']}/odata/Releases?$filter=ProcessKey eq '{release_name}'", headers=HF)).json().get("value", [])
        if not rels:
            raise HTTPException(status_code=502, detail=f"Agent '{release_name}' is not published to the MaestroCity folder.")
        key = rels[0]["Key"]

        start = await c.post(f"{cfg['orch']}/odata/Jobs/UiPath.Server.Configuration.OData.StartJobs", headers=HF,
                             json={"startInfo": {"ReleaseKey": key, "Strategy": "ModernJobsCount", "JobsCount": 1,
                                                 "RuntimeType": "Serverless", "InputArguments": json.dumps(input_args)}})
        if start.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"Could not start '{release_name}' job: {start.text[:200]}")
        job_id = start.json()["value"][0]["Id"]

    waited = 0
    async with httpx.AsyncClient(timeout=20.0) as c:
        while waited < timeout_s:
            await asyncio.sleep(5)
            waited += 5
            st = (await c.get(f"{cfg['orch']}/odata/Jobs({job_id})", headers=HF)).json()
            state = st.get("State")
            if state == "Successful":
                out = st.get("OutputArguments")
                if not out:
                    raise HTTPException(status_code=502, detail=f"'{release_name}' returned no output.")
                try:
                    return json.loads(out)
                except (json.JSONDecodeError, TypeError) as e:
                    raise HTTPException(status_code=502, detail=f"'{release_name}' returned invalid output: {e}")
            if state in ("Faulted", "Stopped"):
                raise HTTPException(status_code=502, detail=f"UiPath '{release_name}' job {state.lower()}: {(st.get('Info') or '')[:300]}")
    raise HTTPException(status_code=504, detail=f"UiPath '{release_name}' job timed out after {timeout_s}s.")
