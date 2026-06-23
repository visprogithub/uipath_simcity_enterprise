"""
Build, compile (uipcli), and publish all 5 Maestro City agent processes to the
MaestroCity Orchestrator folder via API. Repeatable. Run from _uipath_build/.

Each process accepts the input arguments the app's invoke_agent() sends:
  in_AgentId (String), in_Context (String), in_SimulationTick (Int32), in_Phase (String)
and returns out_Status (String).
"""
import glob
import os
import subprocess
import time

import httpx
from dotenv import load_dotenv

load_dotenv("e:/Repos/uipath_simcity_enterprise/apps/backend/.env", override=True)
BASE = os.getenv("UIPATH_CLOUD_URL"); ORG = os.getenv("UIPATH_ORGANIZATION")
TEN = os.getenv("UIPATH_TENANT"); CID = os.getenv("UIPATH_CLIENT_ID")
SEC = os.getenv("UIPATH_CLIENT_SECRET"); FID = os.getenv("UIPATH_FOLDER_ID")
ORCH = f"{BASE}/{ORG}/{TEN}/orchestrator_"
SCOPE = "OR.Jobs OR.Jobs.Write OR.Execution OR.Folders OR.Tasks OR.Administration"
VER = "1.0.0"

# process name (must match .env / agent_builder.py) -> human label for logging
PROCESSES = {
    "ARIA_Operations_Coordinator": "ARIA Operations Coordinator",
    "SENTINEL_Incident_Response": "SENTINEL Incident Response",
    "VERITAS_Compliance": "VERITAS Compliance",
    "ECHO_Communications": "ECHO Communications",
    "APEX_Executive_Strategy": "APEX Executive Strategy",
}

PROJECT_JSON = """{{
  "name": "{name}",
  "description": "Maestro City agent process: {label}",
  "main": "Main.xaml",
  "dependencies": {{ "UiPath.System.Activities": "[24.10.4]" }},
  "webServices": [], "entitiesStores": [],
  "schemaVersion": "4.0", "studioVersion": "24.10.0.0", "projectVersion": "{ver}",
  "runtimeOptions": {{ "autoDispose": false, "requiresUserInteraction": false, "supportsPersistence": false, "executionType": "Workflow" }},
  "designOptions": {{ "outputType": "Process", "libraryOptions": {{ "includeOriginalXaml": false, "privateWorkflows": [] }}, "processOptions": {{ "ignoredFiles": [] }}, "fileInfoCollection": [] }},
  "expressionLanguage": "VisualBasic",
  "entryPoints": [ {{ "filePath": "Main.xaml", "uniqueId": "b1a1c1d1-0001-0001-0001-000000000001", "input": [], "output": [] }} ],
  "isTemplate": false, "targetFramework": "Portable"
}}"""

MAIN_XAML = """<Activity mc:Ignorable="sap sap2010 sap2020" x:Class="Main"
 xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
 xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
 xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
 xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
 xmlns:sap2020="http://schemas.microsoft.com/netfx/2020/xaml/activities/presentation"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members>
    <x:Property Name="in_AgentId" Type="InArgument(x:String)" />
    <x:Property Name="in_Context" Type="InArgument(x:String)" />
    <x:Property Name="in_SimulationTick" Type="InArgument(x:Int32)" />
    <x:Property Name="in_Phase" Type="InArgument(x:String)" />
  </x:Members>
  <Sequence DisplayName="Main" sap2010:WorkflowViewState.IdRef="Sequence_1">
    <WriteLine Text="{label} invoked by Maestro City Orchestrator" sap2010:WorkflowViewState.IdRef="WriteLine_1" />
  </Sequence>
</Activity>"""


def compile_one(name, label):
    d = f"build/{name}"
    os.makedirs(d, exist_ok=True)
    with open(f"{d}/project.json", "w", encoding="utf-8") as f:
        f.write(PROJECT_JSON.format(name=name, label=label, ver=VER))
    with open(f"{d}/Main.xaml", "w", encoding="utf-8") as f:
        f.write(MAIN_XAML.format(name=name, label=label))
    env = dict(os.environ)  # .NET 8 installed -> no roll-forward needed
    r = subprocess.run(
        ["uipcli", "package", "pack", f"{d}/project.json", "-o", f"out/{name}", "--skipAnalyze", "-v", VER],
        capture_output=True, text=True, env=env,
    )
    pkgs = glob.glob(f"out/{name}/*.nupkg")
    ok = r.returncode == 0 and pkgs
    if not ok:
        tail = (r.stdout + r.stderr)
        print(f"  COMPILE FAIL {name}: {[l for l in tail.splitlines() if 'rror' in l][:2]}")
    return pkgs[0] if pkgs else None


def publish_one(token, name, nupkg):
    H = {"Authorization": f"Bearer {token}"}
    HF = {**H, "X-UIPATH-OrganizationUnitId": str(FID)}
    with open(nupkg, "rb") as f:
        up = httpx.post(f"{ORCH}/odata/Processes/UiPath.Server.Configuration.OData.UploadPackage()",
                        headers=H, files={"file": (os.path.basename(nupkg), f.read(), "application/octet-stream")}, timeout=120)
    existing = httpx.get(f"{ORCH}/odata/Releases?$filter=Name eq '{name}'", headers=HF, timeout=20).json().get("value", [])
    if existing:
        httpx.patch(f"{ORCH}/odata/Releases({existing[0]['Id']})", headers={**HF, "Content-Type": "application/json"},
                    json={"ProcessVersion": VER}, timeout=30)
    else:
        httpx.post(f"{ORCH}/odata/Releases", headers={**HF, "Content-Type": "application/json"},
                   json={"Name": name, "ProcessKey": name, "ProcessVersion": VER}, timeout=30)
    return up.status_code


def main():
    token = httpx.post(f"{BASE}/identity_/connect/token",
                       data={"grant_type": "client_credentials", "client_id": CID, "client_secret": SEC, "scope": SCOPE},
                       timeout=30).json()["access_token"]
    for name, label in PROCESSES.items():
        print(f"[{name}] compiling...")
        nupkg = compile_one(name, label)
        if not nupkg:
            continue
        code = publish_one(token, name, nupkg)
        print(f"[{name}] published (upload {code}) + release ready")
    # Verify
    HF = {"Authorization": f"Bearer {token}", "X-UIPATH-OrganizationUnitId": str(FID)}
    rels = httpx.get(f"{ORCH}/odata/Releases", headers=HF, timeout=20).json().get("value", [])
    print("\nReleases now in MaestroCity:", sorted(r["Name"] for r in rels))


if __name__ == "__main__":
    main()
