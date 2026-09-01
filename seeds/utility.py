"""Seed the Revenue Protection workspace — field visit review.

    docker compose up -d      # in indicus-ai-mcp-tools
    backend/.venv/bin/python scripts/utility_demo_seed.py

An electricity supplier finds a discrepancy on an account, sends a
representative to the property, and records the conversation. The question the
pipeline answers is whether the customer is at fault — and, just as often, that
they are not.

Three things shape the design:

* **The recording is transcribed, not assumed.** The first stage runs real
  speech-to-text over real audio. What the review sees is what came back,
  recognition errors included, because that is what it would see in
  production.

* **Intent is analysed apart from the evidence.** The intent stage is given the
  transcript and nothing else, and it runs on a branch of its own. If it could
  see the meter data it would reason backwards from the answer, and its
  signals would stop being independent of the thing they are meant to
  corroborate.

* **Only physical evidence can carry a finding of fault.** Demeanour, evasion
  and cooperation are all reported, and all explicitly subordinate to the
  seal, the diagnostics and the arithmetic. A confident manner has convicted
  nobody and should not start here.
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
UTILITY_API = os.environ.get("UTILITY_API_URL", f"http://{_DEMO_HOST}:8304/utility")
WORKSPACE_NAME = "Revenue Protection"
PIPELINE_NAME = "Field Visit Review"

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
SKILLS = [
    "visit-recording-intake",
    "consumption-anomaly-correlation",
    "customer-intent-signals",
    "field-visit-verdict",
]

TOOLS = [
    {
        "name": "listVisits",
        "description": "Field visits awaiting review, with the reason each was raised.",
        "method": "GET",
        "url_template": UTILITY_API + "/visits",
        "param_locations": {},
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "getVisit",
        "description": "One visit: account, meter, representative and why it was raised.",
        "method": "GET",
        "url_template": UTILITY_API + "/visits/{visit_id}",
        "param_locations": {"visit_id": "path"},
        "input_schema": {
            "type": "object",
            "properties": {"visit_id": {"type": "string",
                                        "description": "e.g. VISIT-4471"}},
            "required": ["visit_id"],
        },
    },
    {
        # Real speech-to-text over the recording. Slow by the standards of the
        # other tools — seconds, not milliseconds — hence the raised timeout.
        "name": "transcribeVisitRecording",
        "description": (
            "Transcribe the visit recording. Returns speaker-attributed turns "
            "with timestamps; speakers come from the recording's two channels. "
            "Takes several seconds."
        ),
        "method": "POST",
        "url_template": UTILITY_API + "/visits/{visit_id}/transcript",
        "param_locations": {"visit_id": "path"},
        "input_schema": {
            "type": "object",
            "properties": {"visit_id": {"type": "string"}},
            "required": ["visit_id"],
        },
        "timeout_seconds": 300,
    },
    {
        "name": "getAccount",
        "description": "Customer account: tariff, declared load, occupancy, payment history.",
        "method": "GET",
        "url_template": UTILITY_API + "/accounts/{account_id}",
        "param_locations": {"account_id": "path"},
        "input_schema": {
            "type": "object",
            "properties": {"account_id": {"type": "string",
                                          "description": "e.g. ACC-40192"}},
            "required": ["account_id"],
        },
    },
    {
        "name": "getBillingHistory",
        "description": (
            "Billed consumption by period, whether each was an actual or "
            "estimated read, and the longest run of consecutive estimates."
        ),
        "method": "GET",
        "url_template": UTILITY_API + "/accounts/{account_id}/billing",
        "param_locations": {"account_id": "path"},
        "input_schema": {
            "type": "object",
            "properties": {"account_id": {"type": "string"}},
            "required": ["account_id"],
        },
    },
    {
        "name": "getMeterReadings",
        "description": (
            "Register reads, meter diagnostics (cover-open events, "
            "reverse-running) and load profile notes."
        ),
        "method": "GET",
        "url_template": UTILITY_API + "/meters/{meter_id}/readings",
        "param_locations": {"meter_id": "path"},
        "input_schema": {
            "type": "object",
            "properties": {"meter_id": {"type": "string",
                                        "description": "e.g. MTR-88213"}},
            "required": ["meter_id"],
        },
    },
    {
        "name": "getFieldInspection",
        "description": "Physical inspection of the meter: seal status, findings, photographs.",
        "method": "GET",
        "url_template": UTILITY_API + "/meters/{meter_id}/inspection",
        "param_locations": {"meter_id": "path"},
        "input_schema": {
            "type": "object",
            "properties": {"meter_id": {"type": "string"}},
            "required": ["meter_id"],
        },
    },
    {
        "name": "getGridEvents",
        "description": "Outages, meter exchanges and billing corrections on the account.",
        "method": "GET",
        "url_template": UTILITY_API + "/accounts/{account_id}/grid-events",
        "param_locations": {"account_id": "path"},
        "input_schema": {
            "type": "object",
            "properties": {"account_id": {"type": "string"}},
            "required": ["account_id"],
        },
    },
]

TOOL_NAMES = {t["name"] for t in TOOLS}

COMMON = (
    "This review concerns a named person who may be entirely innocent, and "
    "what you write may be read back to them. Cite every factual claim to the "
    "transcript timestamp or the record it came from. Where something is not "
    "established, say so rather than filling the gap."
)

AGENTS = [
    (
        "intake", "Recording Intake", "fast", "simple",
        ["visit-recording-intake"],
        ["listVisits", "getVisit", "transcribeVisitRecording"],
        "You turn a recorded visit into an accurate record of what was said.\n\n"
        "Transcribe the recording and summarise the claims made, quoting each "
        "with its timestamp. The transcript is machine transcription of real "
        "audio and contains recognition errors — flag the ones that matter "
        "rather than silently correcting them.\n\n"
        "You do not judge. No adjectives about the customer's manner, no "
        "inference about what they might be hiding. If they contradict "
        "themselves, quote both lines and stop there.",
    ),
    (
        # Sonnet ("deep" tier) but direct execution: the plan/critic/retry
        # loop tripled the token count without changing the finding.
        "records", "Records Correlation", "deep", "simple",
        ["consumption-anomaly-correlation"],
        ["getAccount", "getBillingHistory", "getMeterReadings",
         "getFieldInspection", "getGridEvents"],
        "You establish what the meter and billing records actually show.\n\n"
        "Pull all five sources once, at the start. The same billing shape has "
        "both an innocent and a culpable cause, and only the meter "
        "diagnostics, the seal and the exchange history separate them.\n\n"
        "These records are historical and do not change while you work. If "
        "your answer comes back for correction the fault is in the reasoning, "
        "not the data: re-read what you already have and fix the argument. "
        "Re-fetching returns identical results and leaves the error "
        "untouched.\n\n"
        "Test the innocent explanations by name and first — estimation "
        "catch-up, mishandled meter exchange, tariff or occupancy change, "
        "grid event — before considering interference. Size a catch-up "
        "between two actual reads, never from the estimated ones, and show "
        "the arithmetic so a reviewer can check you.",
    ),
    (
        "intent", "Intent Signals", "fast", "simple",
        ["customer-intent-signals"],
        [],
        "You name behavioural signals in what the customer said, and nothing "
        "else.\n\n"
        "You are given the transcript alone, deliberately: you must not know "
        "what the meter data shows, because a signal that was chosen to fit a "
        "known answer corroborates nothing.\n\n"
        "Quote and timestamp every signal. State plainly that defensiveness "
        "is not guilt and cooperation is not innocence — an innocent person "
        "accused of theft in their own home reacts badly, and that is the "
        "normal case. Never output a verdict.",
    ),
    (
        # Likewise. The skill already prescribes the sections, the verdict
        # labels and the citation rules, so there is little for a planner to
        # decide — and its unsatisfiable acceptance criteria are what failed
        # this stage twice.
        "verdict", "Visit Verdict", "deep", "simple",
        ["field-visit-verdict"],
        # All five, not the two the finding rests on. The planner writes
        # acceptance criteria that check each ruled-out explanation against the
        # source that named it, so a verdict agent holding only the inspection
        # and the meter cannot satisfy its own criteria — it retries until the
        # run dies, with the critic reporting "tool unavailable". Verification
        # needs reach over everything it is verifying.
        ["getFieldInspection", "getMeterReadings", "getAccount",
         "getBillingHistory", "getGridEvents"],
        "You produce the finding a human will act on and may have to defend.\n\n"
        "Fault requires physical or metering evidence: a mismatched seal, a "
        "shunt, cover-open events with no work order, a load profile that "
        "contradicts the declared load. Confirm the inspection yourself "
        "rather than accepting a summary of it.\n\n"
        "Behaviour corroborates and never carries the verdict. If the intent "
        "signals point at the customer and the records do not, say so "
        "explicitly and find NO_CUSTOMER_FAULT or INCONCLUSIVE. INCONCLUSIVE "
        "is a real answer; reaching for a verdict because one is expected is "
        "the worst outcome available to you.",
    ),
]


def _body_only(markdown: str) -> str:
    text = markdown.lstrip()
    if not text.startswith("---"):
        return markdown.strip()
    end = text.find("\n---", 3)
    return markdown.strip() if end == -1 else text[end + 4 :].strip()


def _declared_tools(skill: str) -> list[str]:
    """Every tool the manifest must declare for this skill to publish.

    The platform rejects a bundle whose skill requests a tool the manifest does
    not permit, and the manifest used to be built from the connector list alone.
    A skill declaring anything else — `read`, or a tool from another service —
    failed validation with a message about the manifest, when the mismatch was
    the skill's own frontmatter.

    Union rather than replacement: the connectors are what the agents are wired
    to, and a skill that names none of them still runs beside those that do.
    """
    declared: list[str] = []
    inside = False
    for line in skill.splitlines():
        if line.startswith("allowed-tools:"):
            inside = True
            continue
        if inside:
            if line.startswith("  - "):
                declared.append(line[4:].strip())
                continue
            # Any other top-level key ends the list.
            if line and not line.startswith(" "):
                break
    return sorted(set(TOOL_NAMES) | set(declared))


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
        print("\n1. Registering the utility connectors")
        # Wait rather than fail. These services are started by the same
        # `up -d` that precedes this script, and a container reported "Started"
        # is not a socket that is listening yet.
        # Long, because this one pip-installs faster-whisper before
        # uvicorn starts: minutes on a small box, once per container.
        deadline = time.monotonic() + 420
        announced = False
        while True:
            try:
                if httpx.get(UTILITY_API + "/visits", timeout=10).status_code == 200:
                    break
            except httpx.RequestError:
                pass
            if time.monotonic() >= deadline:
                print(
                    f"   {UTILITY_API} did not come up within 420s.\n"
                    "   The demo services are a separate compose file:\n"
                    "     docker compose -f docker-compose.prod.yml \\\n"
                    "       -f deploy/demo/docker-compose.demo.yml up -d\n"
                    "   If it is running, its log says why it is not listening:\n"
                    "     docker compose logs --tail=40 utility-api\n"
                    "   Nothing was changed; re-running reuses the workspace above."
                )
                return
            if not announced:
                print(f"   waiting for {UTILITY_API} …")
                announced = True
            time.sleep(3)

        current = (await c.get("/custom-tools")).json()
        rows = current if isinstance(current, list) else current.get("tools", [])
        for tool in [t for t in rows if t["name"] in TOOL_NAMES]:
            await c.delete(f"/custom-tools/{tool['id']}")

        payload = [{"timeout_seconds": 60, **tool, "allowed_hosts": [_DEMO_HOST]}
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
                        print(f"   {slug:<34} unchanged at {prior['latest_version']}")
                        continue
            published = await c.post("/plugins/publish", json={
                "manifest": {"name": slug, "version": version,
                             "description": f"{slug} capability.",
                             "permissions": {"tools": _declared_tools(text)}},
                "skills": {slug: text},
                "changelog": f"{slug} {version}",
                "draft": False})
            if published.status_code != 201:
                print(f"   publish failed for {slug}:", published.text[:220])
                return
            plugin_ids[slug] = published.json()["plugin_id"]
            print(f"   {slug:<34} published {version}")

        # --- 3. agents ---
        models = (await c.get(f"/workspaces/{workspace}/models")).json()["models"]
        available = [m["id"] for m in models if m["available"]]
        if not available:
            print("\n   no usable model in this workspace")
            return
        fast = "claude-haiku-4-5" if "claude-haiku-4-5" in available else available[0]
        deep = "claude-sonnet-5" if "claude-sonnet-5" in available else available[0]
        print(f"\n3. Building the agents  (fast={fast}  deep={deep})")

        registry = {a["name"]: a["id"] for a in (await c.get("/agents")).json()}
        agent_ids: dict[str, str] = {}

        for key, name, tier, agent_type, skills, tool_names, purpose in AGENTS:
            config = {
                "agent_type": agent_type,
                "model": deep if tier == "deep" else fast,
                "system_prompt": f"{purpose}\n\n{COMMON}",
                "max_tokens": 16000 if agent_type == "deep" else 8192,
                "effort": "high" if agent_type == "deep" else "medium",
                "builtin_tools": [],
                "custom_tool_ids": [tools[t] for t in tool_names if t in tools],
                "skills": [
                    {"plugin_id": plugin_ids[s], "version_spec": "^1.0.0",
                     "skill_names": [s]}
                    for s in skills if s in plugin_ids
                ],
            }
            if agent_type == "deep":
                # 32, not 20. The critic can send a deep agent round again, and
                # the verdict stage is the one it most often does: it asks for
                # arithmetic to be recomputed before it will pass the finding.
                # At 20 the retry ran the run out of steps and the node failed
                # with "the agent run did not complete" — a stage that has done
                # the work correctly should not fail for lack of room to be
                # checked.
                config["max_steps"] = 32

            if name in registry:
                agent_id = registry[name]
                created = await c.post(f"/agents/{agent_id}/versions", json=config)
            else:
                created = await c.post("/agents", json={
                    "name": name,
                    "description": "Field visit review — "
                                   f"{name.lower()} stage.",
                    "config": config})
                agent_id = created.json().get("id") if created.status_code < 300 else None
            if created.status_code >= 300 or agent_id is None:
                print(f"   {name} failed:", created.text[:220])
                return
            latest = (await c.get(f"/agents/{agent_id}")).json().get("latest_version")
            await c.post(f"/agents/{agent_id}/deploy", json={"version": latest})
            agent_ids[key] = agent_id
            print(f"   {name:<22} {config['model']:<18} "
                  f"{len(config['skills'])} skill  "
                  f"{len(config['custom_tool_ids'])} tools")

        # --- 4. the pipeline ---
        #
        # A diamond, not a chain. Records and intent both hang off the
        # transcript and neither can see the other; the verdict is the only
        # place they meet. Making intent a link in a chain after records would
        # let it read the answer first, and its corroboration would be worth
        # nothing.
        print("\n4. Wiring the field visit review pipeline")
        nodes = [
            {"id": "start", "type": "start", "name": "Visit reference",
             "config": {"position": {"x": 40, "y": 240}}},
            {"id": "intake", "type": "agent", "name": "1 · Transcribe the visit",
             "config": {"agent_id": agent_ids["intake"],
                        "input": (
                            "Visit {{ input }}. Transcribe the recording and "
                            "report what was said: the reason for the visit, "
                            "every factual claim the customer made about "
                            "their own circumstances, anything they offered "
                            "to provide, and what the representative told "
                            "them was found. Quote with timestamps. End with "
                            "the claims that need checking against the "
                            "records."
                        ),
                        "position": {"x": 260, "y": 240}}},
            {"id": "records", "type": "agent", "name": "2a · Records",
             "config": {"agent_id": agent_ids["records"],
                        "input": (
                            "Visit {{ input }}.\n\n"
                            "Claims made in the conversation:\n\n"
                            "{{ nodes.intake.output }}\n\n"
                            "Establish what the billing and meter records "
                            "show. Test the innocent explanations by name "
                            "before considering interference, and show the "
                            "arithmetic."
                        ),
                        "position": {"x": 520, "y": 120}}},
            {"id": "intent", "type": "agent", "name": "2b · Intent signals",
             "config": {"agent_id": agent_ids["intent"],
                        "input": (
                            # The transcript and nothing else. This node's
                            # independence is the whole reason the graph
                            # forks here.
                            "Transcript of the visit:\n\n"
                            "{{ nodes.intake.output }}\n\n"
                            "Name the behavioural signals, quoted and "
                            "timestamped, and state what weight they carry. "
                            "You do not have the meter data and must not "
                            "guess at it."
                        ),
                        "position": {"x": 520, "y": 360}}},
            {"id": "verdict", "type": "agent", "name": "3 · Verdict",
             "config": {"agent_id": agent_ids["verdict"],
                        "input": (
                            "Visit {{ input }}.\n\n"
                            "=== What the records show ===\n\n"
                            "{{ nodes.records.output }}\n\n"
                            "=== Behavioural signals (corroboration only) ===\n\n"
                            "{{ nodes.intent.output }}\n\n"
                            "Produce the verdict. Confirm the inspection "
                            "yourself. Fault requires physical or metering "
                            "evidence; if the signals and the records "
                            "disagree, the records govern and you must say "
                            "so."
                        ),
                        "position": {"x": 800, "y": 240}}},
            {"id": "end", "type": "end", "name": "Reviewed",
             "config": {"position": {"x": 1060, "y": 240}}},
        ]
        edges = [
            {"source": "start", "target": "intake"},
            {"source": "intake", "target": "records"},
            {"source": "intake", "target": "intent"},
            {"source": "records", "target": "verdict"},
            {"source": "intent", "target": "verdict"},
            {"source": "verdict", "target": "end"},
        ]
        graph = {"nodes": nodes, "edges": edges,
                 "max_cost_usd": 4, "max_node_runs": 12}

        pipelines = {w["name"]: w["id"] for w in (await c.get("/workflows")).json()}
        if PIPELINE_NAME in pipelines:
            workflow_id = pipelines[PIPELINE_NAME]
            saved = await c.post(f"/workflows/{workflow_id}/versions", json=graph)
        else:
            made = await c.post("/workflows", json={
                "name": PIPELINE_NAME,
                "description": ("Transcribe a recorded field visit, correlate "
                                "it against billing and meter records, and "
                                "produce a cited verdict.")})
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
            print(f"  {name:<22} /agents/{agent_ids[key]}")
        print("\n  Run it with VISIT-4471 (interference) or VISIT-4472 "
              "(billing fault).")


if __name__ == "__main__":
    asyncio.run(main())
