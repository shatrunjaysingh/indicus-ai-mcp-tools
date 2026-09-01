"""Seed the Security Operations workspace — SOC alert response.

    docker compose up -d      # in indicus-ai-mcp-tools
    backend/.venv/bin/python scripts/soc_demo_seed.py

This workspace was built by hand through the UI and existed only in one
developer's database — the API was in version control, everything that made it
a demo was not. The skills have been exported to `demo/skills/` and this script
rebuilds the rest, so the demo survives a fresh install.

The pipeline branches, which is the point of it. Two alerts fire the *same*
detection rule — "Encoded PowerShell spawned by Office process" — and only
enrichment separates them. ALT-2291 is a real intrusion and routes to incident
response. ALT-2288 is an SCCM agent running a patch-inventory query and routes
to detection tuning, because the right answer to a false positive is to stop it
firing rather than to escalate it.

The branch reads the *enrichment* output rather than a later verdict on
purpose: the stage that looked at the evidence is the one that gets to say
whether it was benign.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# The platform, not the demo services. Overridable for the same reason
# DEMO_HOST is: inside a container 127.0.0.1 is that container, so the
# default is correct only when seeding from a laptop.
API = os.environ.get("PLATFORM_API_URL", "http://127.0.0.1:8000/api/v1")
# Overridable so the same script works on a laptop and in a deployment.
# Inside a container 127.0.0.1 is that container, not the demo service, so a
# deployment sets DEMO_HOST to the compose service name ("mcp-tools").
_DEMO_HOST = os.environ.get("DEMO_HOST", "127.0.0.1")
SOC_API = os.environ.get("SOC_API_URL", f"http://{_DEMO_HOST}:8304/soc")
WORKSPACE_NAME = "Security Operations"
PIPELINE_NAME = "SOC Alert Response"

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
SKILLS = ["alert-triage", "ioc-enrichment", "incident-response", "detection-tuning"]

TOOLS = [
    {
        "name": "getAlert",
        "description": (
            "One alert with its raw telemetry: process tree, decoded "
            "command, network connections and file hashes."
        ),
        "method": "GET",
        "url_template": SOC_API + "/alerts/{alert_id}",
        "param_locations": {"alert_id": "path"},
        "input_schema": {
            "type": "object",
            "properties": {"alert_id": {"type": "string", "description": "e.g. ALT-2291"}},
            "required": ["alert_id"],
        },
    },
    {
        "name": "listAlerts",
        "description": "Alerts in the triage queue.",
        "method": "GET",
        "url_template": SOC_API + "/alerts",
        "param_locations": {},
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "getIndicatorReputation",
        "description": "Reputation for an IP, domain or file hash.",
        "method": "GET",
        "url_template": SOC_API + "/ioc/{indicator}",
        "param_locations": {"indicator": "path"},
        "input_schema": {
            "type": "object",
            "properties": {"indicator": {"type": "string"}},
            "required": ["indicator"],
        },
    },
    {
        "name": "getAsset",
        "description": "Asset inventory for a host: segment, criticality, data classification.",
        "method": "GET",
        "url_template": SOC_API + "/assets/{hostname}",
        "param_locations": {"hostname": "path"},
        "input_schema": {
            "type": "object",
            "properties": {"hostname": {"type": "string"}},
            "required": ["hostname"],
        },
    },
    {
        "name": "getIdentity",
        "description": (
            "Identity context for a user or service account. Most false positives "
            "resolve here: a service account doing exactly its job looks alarming "
            "until you know what the account is for."
        ),
        "method": "GET",
        "url_template": SOC_API + "/identity/{username}",
        "param_locations": {"username": "path"},
        "input_schema": {
            "type": "object",
            "properties": {"username": {"type": "string"}},
            "required": ["username"],
        },
    },
]

TOOL_NAMES = {t["name"] for t in TOOLS}

COMMON = (
    "Cite the field you read for every claim. An alert is evidence about a real "
    "host and a real person, and a containment action taken on a misreading has "
    "a cost of its own."
)

AGENTS = [
    (
        "triage", "Alert Triage",
        ["alert-triage"], ["getAlert", "listAlerts"],
        "You are a tier-1 SOC analyst triaging a detection.\n\n"
        "Pull the alert with getAlert before saying anything about it. Read the "
        "process tree, decode the command line, and read the raw log — never "
        "reason from the rule name alone, because the same rule fires on an "
        "attack and on a patch-inventory script, and the name cannot tell them "
        "apart.\n\n"
        "You do not reach a verdict. List what must be enriched before anyone "
        "can.",
    ),
    (
        "enrich", "IOC Enrichment",
        ["ioc-enrichment"],
        ["getAlert", "getIndicatorReputation", "getAsset", "getIdentity"],
        "You are a SOC analyst deciding whether an alert is real.\n\n"
        "Look up every external indicator with getIndicatorReputation, the host "
        "with getAsset, and the account with getIdentity. Most false positives "
        "are resolved by identity context: a service account doing exactly what "
        "it exists to do looks alarming until you know what the account is "
        "for.\n\n"
        "End with exactly one line: 'VERDICT: malicious', 'VERDICT: suspicious' "
        "or 'VERDICT: benign'. The pipeline branches on that line, so it must be "
        "the literal text and nothing else.",
    ),
    (
        "respond", "Incident Response",
        ["incident-response"], ["getAlert", "getAsset", "getIdentity"],
        "You are an incident responder. An alert has been enriched and judged "
        "malicious or suspicious, and you produce the response plan.\n\n"
        "Sequence matters more than completeness: preserve volatile evidence "
        "before containing, isolate rather than power off, revoke sessions "
        "rather than only resetting a password. State blast radius from the "
        "asset record rather than assuming it.\n\n"
        "Never borrow indicators from another case. If the telemetry for this "
        "alert is missing, say so and stop — a plan aimed at a host you inferred "
        "is worse than no plan.",
    ),
    (
        "tune", "Detection Tuning",
        ["detection-tuning"], ["getAlert", "getIdentity"],
        "You tune detections. An alert has been enriched and judged benign, and "
        "you write the rule change so it stops firing.\n\n"
        "Name the specific clause that matched and the specific legitimate "
        "activity that matched it. Then write an exclusion narrow enough that an "
        "attacker cannot live inside it — scoped to the account, the parent "
        "process and the destination, not to the rule as a whole.\n\n"
        "If the exclusion you would need is wide enough to hide an attack, say "
        "that instead of writing it.",
    ),
]


def _body_only(markdown: str) -> str:
    text = markdown.lstrip()
    if not text.startswith("---"):
        return markdown.strip()
    end = text.find("\n---", 3)
    return markdown.strip() if end == -1 else text[end + 4 :].strip()


async def main() -> None:
    async with httpx.AsyncClient(base_url=API, timeout=240) as c:
        login = await c.post("/auth/login", json={
            "email": "demo@example.com", "password": "demo-password-1234"})
        if login.status_code != 200:
            print("Could not log in — is the API running?")
            return
        data = login.json()
        c.headers.update({"Authorization": f"Bearer {data['access_token']}"})
        c.headers["X-Workspace-Id"] = data["default_workspace_id"]

        # --- 0. workspace ---
        existing = (await c.get("/workspaces")).json()
        found = next((w for w in existing if w["name"] == WORKSPACE_NAME), None)
        if found:
            workspace = found["id"]
            print(f"0. Reusing workspace '{WORKSPACE_NAME}'")
        else:
            created = await c.post("/workspaces", json={"name": WORKSPACE_NAME})
            if created.status_code >= 300:
                print("   could not create workspace:", created.text[:200])
                return
            workspace = created.json()["id"]
            print(f"0. Created workspace '{WORKSPACE_NAME}'")
        c.headers["X-Workspace-Id"] = workspace

        # --- 1. tools ---
        print("\n1. Registering the SOC connectors")
        # Wait rather than fail. These services are started by the same
        # `up -d` that precedes this script, and a container reported "Started"
        # is not a socket that is listening yet.
        deadline = time.monotonic() + 90
        announced = False
        while True:
            try:
                if httpx.get(SOC_API + "/alerts", timeout=10).status_code == 200:
                    break
            except httpx.RequestError:
                pass
            if time.monotonic() >= deadline:
                print(
                    f"   {SOC_API} did not come up within 90s.\n"
                    "   The demo services are a separate compose file:\n"
                    "     docker compose -f docker-compose.prod.yml \\\n"
                    "       -f deploy/demo/docker-compose.demo.yml up -d\n"
                    "   If it is running, its log says why it is not listening:\n"
                    "     docker compose logs --tail=40 soc-api\n"
                    "   Nothing was changed; re-running reuses the workspace above."
                )
                return
            if not announced:
                print(f"   waiting for {SOC_API} …")
                announced = True
            time.sleep(3)

        current = (await c.get("/custom-tools")).json()
        rows = current if isinstance(current, list) else current.get("tools", [])
        for tool in [t for t in rows if t["name"] in TOOL_NAMES]:
            await c.delete(f"/custom-tools/{tool['id']}")

        payload = [{"timeout_seconds": 30, **tool, "allowed_hosts": [_DEMO_HOST]}
                   for tool in TOOLS]
        imported = await c.post("/custom-tools/import", json={"tools": payload})
        if imported.status_code != 201:
            print("   import failed:", imported.text[:300])
            return
        rows = (await c.get("/custom-tools")).json()
        rows = rows if isinstance(rows, list) else rows.get("tools", [])
        tools = {t["name"]: t["id"] for t in rows if t["name"] in TOOL_NAMES}
        print(f"   {len(tools)} of {len(TOOL_NAMES)} tools registered")

        # --- 2. skills ---
        print("\n2. Publishing the skills")
        catalogue = {p["name"]: p for p in (await c.get("/plugins")).json()}
        plugin_ids: dict[str, str] = {}

        for slug in SKILLS:
            path = SKILLS_DIR / f"{slug}.md"
            if not path.exists():
                print(f"   {slug}: {path} not found")
                return
            text = path.read_text()
            prior = catalogue.get(slug)
            version = "1.0.0"
            if prior and prior.get("latest_version"):
                major, minor, _patch = prior["latest_version"].split(".")
                version = f"{major}.{int(minor) + 1}.0"
                detail = await c.get(f"/plugins/{prior['id']}/detail")
                if detail.status_code == 200:
                    latest = next((v for v in detail.json().get("versions", [])
                                   if v["version"] == prior["latest_version"]), None)
                    shipped = {s["name"]: s.get("body")
                               for s in (latest or {}).get("skills", [])}
                    if (shipped.get(slug) or "").strip() == _body_only(text):
                        plugin_ids[slug] = prior["id"]
                        print(f"   {slug:<22} unchanged at {prior['latest_version']}")
                        continue
            published = await c.post("/plugins/publish", json={
                "manifest": {"name": slug, "version": version,
                             "description": f"{slug} capability.",
                             "permissions": {"tools": sorted(TOOL_NAMES)}},
                "skills": {slug: text},
                "changelog": f"{slug} {version}",
                "draft": False})
            if published.status_code != 201:
                print(f"   publish failed for {slug}:", published.text[:220])
                return
            plugin_ids[slug] = published.json()["plugin_id"]
            print(f"   {slug:<22} published {version}")

        # --- 3. agents ---
        models = (await c.get(f"/workspaces/{workspace}/models")).json()["models"]
        available = [m["id"] for m in models if m["available"]]
        if not available:
            print("\n   no usable model in this workspace — add a provider key first")
            return
        model = "claude-sonnet-5" if "claude-sonnet-5" in available else available[0]
        print(f"\n3. Building the agents  (model={model})")

        registry = {a["name"]: a["id"] for a in (await c.get("/agents")).json()}
        agent_ids: dict[str, str] = {}

        for key, name, skills, tool_names, purpose in AGENTS:
            config = {
                # Simple, not deep. Each stage does one bounded job against a
                # small set of tools, and the plan/critic loop tripled the cost
                # of comparable stages elsewhere without changing the finding.
                "agent_type": "simple",
                "model": model,
                "system_prompt": f"{purpose}\n\n{COMMON}",
                "max_tokens": 8192,
                "effort": "medium",
                "builtin_tools": [],
                "custom_tool_ids": [tools[t] for t in tool_names if t in tools],
                "skills": [
                    {"plugin_id": plugin_ids[s], "version_spec": "^1.0.0",
                     "skill_names": [s]}
                    for s in skills if s in plugin_ids
                ],
            }
            if name in registry:
                agent_id = registry[name]
                created = await c.post(f"/agents/{agent_id}/versions", json=config)
            else:
                created = await c.post("/agents", json={
                    "name": name,
                    "description": f"SOC alert response — {name.lower()} stage.",
                    "config": config})
                agent_id = created.json().get("id") if created.status_code < 300 else None
            if created.status_code >= 300 or agent_id is None:
                print(f"   {name} failed:", created.text[:220])
                return
            latest = (await c.get(f"/agents/{agent_id}")).json().get("latest_version")
            await c.post(f"/agents/{agent_id}/deploy", json={"version": latest})
            agent_ids[key] = agent_id
            print(f"   {name:<20} {len(config['skills'])} skill  "
                  f"{len(config['custom_tool_ids'])} tools")

        # --- 4. the pipeline ---
        print("\n4. Wiring the SOC alert response pipeline")
        nodes = [
            {"id": "start", "type": "start", "name": "Alert",
             "config": {"position": {"x": 40, "y": 240}}},
            {"id": "triage", "type": "agent", "name": "1 · Triage",
             "config": {"agent_id": agent_ids["triage"],
                        "input": (
                            "{{ input }}\n\nIf no alert was named above, call "
                            "listAlerts and work the single most urgent one, "
                            "saying which you picked and why. Exactly one alert."
                        ),
                        "position": {"x": 260, "y": 240}}},
            {"id": "enrich", "type": "agent", "name": "2 · Enrich",
             "config": {"agent_id": agent_ids["enrich"],
                        "input": (
                            "A tier-1 analyst triaged this alert:\n\n"
                            "{{ nodes.triage.output }}\n\n"
                            "Enrich every indicator and state the verdict."
                        ),
                        "position": {"x": 500, "y": 240}}},
            {"id": "verdict", "type": "branch", "name": "Real or benign?",
             "config": {"position": {"x": 730, "y": 240}}},
            {"id": "respond", "type": "agent", "name": "3a · Respond",
             "config": {"agent_id": agent_ids["respond"],
                        "input": (
                            "This alert was judged a real incident. Enrichment "
                            "findings:\n\n{{ nodes.enrich.output }}\n\n"
                            "Produce the response plan."
                        ),
                        "position": {"x": 950, "y": 120}}},
            {"id": "tune", "type": "agent", "name": "3b · Tune the rule",
             "config": {"agent_id": agent_ids["tune"],
                        "input": (
                            "This alert was judged a false positive. Enrichment "
                            "findings:\n\n{{ nodes.enrich.output }}\n\n"
                            "Explain why it fired and write the rule change."
                        ),
                        "position": {"x": 950, "y": 360}}},
            {"id": "end", "type": "end", "name": "Closed",
             "config": {"position": {"x": 1190, "y": 240}}},
        ]

        # Branches on the enrichment output, not on a later stage: the step that
        # read the evidence is the one entitled to say it was benign. Anything
        # not explicitly benign goes to incident response — the safe direction
        # for a misread is a wasted response, not a missed intrusion.
        benign = {"left": "{{ nodes.enrich.output }}", "operator": "contains",
                  "right": "VERDICT: benign"}
        not_benign = {"left": "{{ nodes.enrich.output }}", "operator": "not_contains",
                      "right": "VERDICT: benign"}
        edges = [
            {"source": "start", "target": "triage"},
            {"source": "triage", "target": "enrich"},
            {"source": "enrich", "target": "verdict"},
            {"source": "verdict", "target": "respond", "when": not_benign},
            {"source": "verdict", "target": "tune", "when": benign},
            {"source": "respond", "target": "end"},
            {"source": "tune", "target": "end"},
        ]
        graph = {"nodes": nodes, "edges": edges, "max_cost_usd": 4, "max_node_runs": 12}

        pipelines = {w["name"]: w["id"] for w in (await c.get("/workflows")).json()}
        if PIPELINE_NAME in pipelines:
            workflow_id = pipelines[PIPELINE_NAME]
            saved = await c.post(f"/workflows/{workflow_id}/versions", json=graph)
        else:
            made = await c.post("/workflows", json={
                "name": PIPELINE_NAME,
                "description": ("Triage, enrich, then either respond or tune the "
                                "detection — decided by the evidence.")})
            if made.status_code >= 300:
                print("   pipeline failed:", made.text[:220])
                return
            workflow_id = made.json()["id"]
            saved = await c.post(f"/workflows/{workflow_id}/versions", json=graph)
        if saved.status_code >= 300:
            print("   graph rejected:", saved.text[:300])
            return
        print(f"   {saved.status_code}  {len(nodes)} nodes, {len(edges)} edges")

        print("\n" + "─" * 66)
        print(f"  Workspace : {WORKSPACE_NAME}")
        print(f"  Pipeline  : /workflows/{workflow_id}")
        for key, name, *_ in AGENTS:
            print(f"  {name:<20} /agents/{agent_ids[key]}")
        print("\n  ALT-2291 is a real intrusion and should route to Respond.")
        print("  ALT-2288 is a false positive and should route to Tune.")


if __name__ == "__main__":
    asyncio.run(main())
