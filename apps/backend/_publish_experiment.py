"""
THROWAWAY experiment: build a UiPath .nupkg via API, upload, create a release,
and trigger a job — to test whether API-published processes actually run on the
serverless robot. Safe to delete. Writes artifacts (package + release) to the
MaestroCity folder on staging.
"""
import io
import os
import time
import uuid
import zipfile

import httpx
from dotenv import load_dotenv

load_dotenv("e:/Repos/uipath_simcity_enterprise/apps/backend/.env", override=True)
BASE = os.getenv("UIPATH_CLOUD_URL")
ORG = os.getenv("UIPATH_ORGANIZATION")
TEN = os.getenv("UIPATH_TENANT")
CID = os.getenv("UIPATH_CLIENT_ID")
SEC = os.getenv("UIPATH_CLIENT_SECRET")
FID = os.getenv("UIPATH_FOLDER_ID")
ORCH = f"{BASE}/{ORG}/{TEN}/orchestrator_"

# A deliberately MINIMAL, cross-platform-safe workflow: one LogMessage + set an output.
# Authored to maximize the chance the robot can actually run it.
MAIN_XAML = '''<Activity mc:Ignorable="sap sap2010 sap2020" x:Class="Main"
 xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
 xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
 xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities"
 xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
 xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
 xmlns:sap2020="http://schemas.microsoft.com/netfx/2020/xaml/activities/presentation"
 xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members>
    <x:Property Name="in_Message" Type="InArgument(x:String)" />
    <x:Property Name="out_Result" Type="OutArgument(x:String)" />
  </x:Members>
  <mva:VisualBasic.Settings>
    <mva:VisualBasicSettings>
      <mva:VisualBasicSettings.ImportedNamespaces>
        <mva:VisualBasicImportReference Assembly="mscorlib" Import="System" />
      </mva:VisualBasicSettings.ImportedNamespaces>
    </mva:VisualBasicSettings>
  </mva:VisualBasic.Settings>
  <Sequence DisplayName="Main">
    <WriteLine Text="[MaestroCity PipelineTest] ran ok" />
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_Result]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">["ok"]</InArgument></Assign.Value>
    </Assign>
  </Sequence>
</Activity>'''

PROJECT_JSON = '''{
  "name": "MaestroCity_PipelineTest",
  "description": "Minimal pipeline test published via API",
  "main": "Main.xaml",
  "dependencies": { "UiPath.System.Activities": "[22.10.4]" },
  "schemaVersion": "4.0",
  "studioVersion": "22.10.0.0",
  "projectVersion": "1.0.0",
  "runtimeOptions": { "autoDispose": false, "requiresUserInteraction": false, "supportsPersistence": false },
  "designOptions": { "projectProfile": "Development", "outputType": "Process", "libraryOptions": { "includeOriginalXaml": false }, "processOptions": {} },
  "expressionLanguage": "VisualBasic",
  "targetFramework": "Portable"
}'''

PKG_ID = "MaestroCity_PipelineTest"
PKG_VER = "1.0.1"


def build_nupkg() -> bytes:
    nuspec = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>{PKG_ID}</id>
    <version>{PKG_VER}</version>
    <title>{PKG_ID}</title>
    <authors>MaestroCity</authors>
    <owners>MaestroCity</owners>
    <description>Minimal pipeline test published via API</description>
  </metadata>
</package>'''
    content_types = '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />
  <Default Extension="psmdcp" ContentType="application/vnd.openxmlformats-package.core-properties+xml" />
  <Default Extension="nuspec" ContentType="application/octet" />
  <Default Extension="xaml" ContentType="application/octet" />
  <Default Extension="json" ContentType="application/octet" />
</Types>'''
    psmdcp_name = f"package/services/metadata/core-properties/{uuid.uuid4().hex}.psmdcp"
    psmdcp = f'''<?xml version="1.0" encoding="utf-8"?>
<coreProperties xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns="http://schemas.openxmlformats.org/package/2006/metadata/core-properties">
  <dc:creator>MaestroCity</dc:creator>
  <dc:description>Minimal pipeline test</dc:description>
  <dc:identifier>{PKG_ID}</dc:identifier>
  <version>{PKG_VER}</version>
</coreProperties>'''
    rels = f'''<?xml version="1.0" encoding="utf-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Type="http://schemas.microsoft.com/packaging/2010/07/manifest" Target="/{PKG_ID}.nuspec" Id="Re0" />
  <Relationship Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="/{psmdcp_name}" Id="Re1" />
</Relationships>'''
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr(psmdcp_name, psmdcp)
        z.writestr(f"{PKG_ID}.nuspec", nuspec)
        z.writestr("content/project.json", PROJECT_JSON)
        z.writestr("content/Main.xaml", MAIN_XAML)
    return buf.getvalue()


def main():
    tok = httpx.post(
        f"{BASE}/identity_/connect/token",
        data={"grant_type": "client_credentials", "client_id": CID, "client_secret": SEC,
              "scope": "OR.Jobs OR.Jobs.Write OR.Execution OR.Folders OR.Tasks OR.Administration OR.Machines.Write"},
        timeout=30,
    ).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    HF = dict(H); HF["X-UIPATH-OrganizationUnitId"] = str(FID)

    nupkg = build_nupkg()
    print(f"[1] built nupkg: {len(nupkg)} bytes")

    # Upload to tenant feed
    up = httpx.post(
        f"{ORCH}/odata/Processes/UiPath.Server.Configuration.OData.UploadPackage()",
        headers=H,
        files={"file": (f"{PKG_ID}.{PKG_VER}.nupkg", nupkg, "application/octet-stream")},
        timeout=60,
    )
    print(f"[2] upload status: {up.status_code} {up.text[:300]}")
    if up.status_code not in (200, 201):
        return

    # Find existing release or create it, then point it at the new version
    existing = httpx.get(
        f"{ORCH}/odata/Releases?$filter=Name eq '{PKG_ID}'", headers=HF, timeout=20
    ).json().get("value", [])
    if existing:
        rid = existing[0]["Id"]
        patch = httpx.patch(
            f"{ORCH}/odata/Releases({rid})",
            headers={**HF, "Content-Type": "application/json"},
            json={"ProcessVersion": PKG_VER}, timeout=30,
        )
        print(f"[3] update release {rid} -> {PKG_VER}: {patch.status_code}")
        release_key = existing[0]["Key"]
    else:
        rel = httpx.post(
            f"{ORCH}/odata/Releases",
            headers={**HF, "Content-Type": "application/json"},
            json={"Name": PKG_ID, "ProcessKey": PKG_ID, "ProcessVersion": PKG_VER},
            timeout=30,
        )
        print(f"[3] create release: {rel.status_code} {rel.text[:200]}")
        if rel.status_code not in (200, 201):
            return
        release_key = rel.json().get("Key")
    print(f"    release key: {release_key}")

    # Start a job (modern serverless)
    job = httpx.post(
        f"{ORCH}/odata/Jobs/UiPath.Server.Configuration.OData.StartJobs",
        headers={**HF, "Content-Type": "application/json"},
        json={"startInfo": {"ReleaseKey": release_key, "Strategy": "ModernJobsCount",
                            "JobsCount": 1, "RuntimeType": "Serverless",
                            "InputArguments": '{"in_Message":"hello"}'}},
        timeout=30,
    )
    print(f"[4] start job: {job.status_code} {job.text[:400]}")
    if job.status_code not in (200, 201):
        return
    jid = job.json()["value"][0]["Id"]
    print(f"    job id: {jid}")

    # Poll
    for i in range(20):
        time.sleep(5)
        st = httpx.get(f"{ORCH}/odata/Jobs({jid})", headers=HF, timeout=20).json()
        state = st.get("State")
        print(f"    poll {i}: {state}")
        if state in ("Successful", "Faulted", "Stopped"):
            print(f"[5] FINAL: {state} | info: {st.get('Info')}")
            break


if __name__ == "__main__":
    main()
