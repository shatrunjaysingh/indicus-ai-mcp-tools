"""Seed the Battery Warranty Analytics workspace: tools, three skills, four agents.

    docker compose exec mcp-tools python seeds/battery.py      # on a deployment
    .venv/bin/python seeds/battery.py                          # on a laptop

Three problems a battery maker's warranty team has, each a single-purpose
agent holding one skill and only the tools that skill declares:

  1  No-fault-found analysis — healthy batteries replaced under warranty.
  2  Early batch failure — a manufacturing batch failing before its time.
  3  Warranty fraud network — leakage and organised abuse across claims.

plus a Warranty Analyst holding all three skills, to show the platform picking
the right skill for a question.

The data is synthetic and lives only in this repository's tool service
(services/battery_population.py). This seed writes nothing but the workspace,
the tool definitions, the skills and the agents into the platform — no
batteries, claims or customers. Same shape as seeds/discom.py.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

API = os.environ.get("PLATFORM_API_URL", "http://127.0.0.1:8000/api/v1")
_DEMO_HOST = os.environ.get("DEMO_HOST", "127.0.0.1")
BATTERY_API = os.environ.get("BATTERY_API_URL", f"http://{_DEMO_HOST}:8304/battery")

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
WORKSPACE_NAME = "Battery Warranty Analytics"


def _get(name: str, desc: str, path: str, params: dict[str, str] | None = None,
         query: dict[str, str] | None = None, required: list[str] | None = None) -> dict:
    """One read-only GET tool. `params` are path parameters, `query` query ones."""
    props: dict[str, dict] = {}
    locations: dict[str, str] = {}
    for key, hint in (params or {}).items():
        props[key] = {"type": "string", "description": hint}
        locations[key] = "path"
    for key, hint in (query or {}).items():
        props[key] = {"type": "string", "description": hint}
        locations[key] = "query"
    return {
        "name": name, "description": desc, "method": "GET",
        "url_template": BATTERY_API + path,
        "param_locations": locations,
        "input_schema": {"type": "object", "properties": props,
                         "required": list((params or {}).keys()) + (required or [])},
    }


TOOLS = [
    _get("getWarrantySummary",
         "The warranty programme at a glance: batteries sold, claims, replacements, factory "
         "verdicts, the no-fault-found rate and its cost, by city. Start here.", "/summary"),
    _get("listClaims", "Warranty claims filtered by city, dealer, technician, batch, model, factory "
         "verdict, outcome or date, newest first, with readings and verdicts.", "/claims",
         query={"city": "e.g. Pune", "dealer_id": "e.g. DLR-NGP-021", "technician_id": "e.g. TEC-PUN-004",
                "batch_id": "e.g. A2-2603-2", "model": "e.g. EXC-35L",
                "verdict": "factory verdict: no_fault_found, cell_short, sulphation, ...",
                "outcome": "replaced_under_warranty | rejected | recharged_returned",
                "since": "YYYY-MM-DD", "until": "YYYY-MM-DD", "limit": "max rows, default 50"}),
    _get("getClaim", "One claim: the technician's readings, the decision, the factory verdict, the "
         "battery, and other claims on the same serial.", "/claims/{claim_id}",
         params={"claim_id": "e.g. CLM-PUN-24601"}),
    _get("getBattery", "One battery by serial: plant, line, batch, model, sale, dealer, owner, and "
         "every claim on it.", "/batteries/{serial}", params={"serial": "e.g. EX-A2-2603-2-00117"}),
    _get("getFactoryRetest", "The factory's retest verdict for a returned battery, with the field "
         "readings taken before it was replaced.", "/claims/{claim_id}/retest",
         params={"claim_id": "e.g. CLM-PUN-24601"}),
    _get("getNoFaultFoundAnalysis", "No-fault-found rate with 95% interval and the readings taken "
         "before replacing, grouped by city, technician, dealer, model, segment or month.",
         "/analysis/no-fault-found",
         query={"group_by": "city | technician | dealer | model | segment | month",
                "city": "limit to one city, e.g. Pune",
                "min_retested": "leave out groups with fewer retests (default 10)"}),
    _get("getTechnicianProfile", "A technician's testing habits (load test, alternator check), "
         "replacement rate and no-fault-found rate, against city peers.",
         "/technicians/{technician_id}", params={"technician_id": "e.g. TEC-PUN-004"}),
    _get("getBatchFailureRates", "Early-life failures per 1,000 sold by batch, line, plant, model or "
         "month made, with 95% intervals and the median; worst first.", "/analysis/batch-failures",
         query={"group_by": "batch | line | plant | model | month_made",
                "within_months": "failures within this many months of sale (default 6)",
                "min_units": "leave out smaller groups (default 60)",
                "genuine_only": "true to drop no-fault-found claims (default true)",
                "top": "rows to return (default 20)"}),
    _get("getBatch", "One batch: units sold, claims by months in service, readings, factory "
         "verdicts, cities sold in.", "/batches/{batch_id}", params={"batch_id": "e.g. A2-2603-2"}),
    _get("getProductionRecord", "The plant's record for a batch: separator lot and supplier, "
         "formation temperature, QC notes, other batches sharing the separator lot.",
         "/batches/{batch_id}/production", params={"batch_id": "e.g. A2-2603-2"}),
    _get("getDealerBenchmark", "Dealers ranked by excess replacements against their city's median, "
         "with no-fault-found rate, late-warranty claims and technician concentration.",
         "/dealers/benchmark",
         query={"city": "limit to one city", "min_claims": "default 15", "top": "default 20"}),
    _get("getDealerProfile", "One dealer: claims, replacement and no-fault-found rates, technicians "
         "used, timing against warranty end, readings.", "/dealers/{dealer_id}",
         params={"dealer_id": "e.g. DLR-NGP-021"}),
    _get("findSharedClaimants", "Phones that claimed on several different batteries, with dealers, "
         "dates, verdicts and whether a fleet account explains it.", "/fraud/shared-claimants",
         query={"min_batteries": "default 3"}),
    _get("findReusedPhotos", "Label photos attached to claims for different batteries.",
         "/fraud/reused-photos"),
    _get("getExpiryTiming", "Share of each dealer's claims filed in the last 10 days of warranty, "
         "against the norm.", "/fraud/expiry-timing", query={"min_claims": "default 15", "top": "default 15"}),
    _get("getClaimLinks", "Every claim, phone, dealer, technician and photo linked to one phone, "
         "dealer, technician or photo — one hop of the network.", "/fraud/links",
         query={"kind": "phone | dealer | technician | photo", "value": "e.g. +919820155443"},
         required=["kind", "value"]),
    _get("getReference", "Plants, models, warranty periods, the serial format, what each factory "
         "verdict means, and what a healthy battery reads.", "/reference"),
]
TOOL_NAMES = {t["name"] for t in TOOLS}

NFF_TOOLS = ["getWarrantySummary", "getNoFaultFoundAnalysis", "getTechnicianProfile", "listClaims",
             "getClaim", "getFactoryRetest", "getBattery", "getReference"]
BATCH_TOOLS = ["getBatchFailureRates", "getBatch", "getProductionRecord", "getBattery", "listClaims",
               "getClaim", "getReference", "getWarrantySummary"]
FRAUD_TOOLS = ["getDealerBenchmark", "getDealerProfile", "getExpiryTiming", "findSharedClaimants",
               "findReusedPhotos", "getClaimLinks", "getTechnicianProfile", "getClaim", "getFactoryRetest",
               "getBattery", "listClaims", "getWarrantySummary"]

AGENTS = [
    ("nff", "No-Fault-Found Analyst", "deep", "no-fault-found-analysis", NFF_TOOLS,
     "You analyse a battery maker's warranty replacements to find where healthy batteries are being "
     "replaced (no fault found at the factory retest), explain why from the technicians' readings, "
     "and recommend what to change. Use the tools for every number; never estimate a figure you can "
     "look up. Give each rate with its count. Rule out the innocent explanation before naming a "
     "problem. Never call a person dishonest: recommend process fixes and coaching. Be concise and "
     "lead with the answer."),
    ("batch", "Batch Quality Watch", "deep", "early-batch-failure", BATCH_TOOLS,
     "You watch a battery maker's early-life failure rates by manufacturing batch, line and plant, "
     "and raise a batch problem early with the evidence a quality team needs. Compare rates, not "
     "counts, against the median with their intervals; check neighbouring batches and the production "
     "record; separate manufacturing failures from batteries that tested healthy. State a cause as "
     "likely, never certain, and recommend containment. Lead with the answer."),
    ("fraud", "Warranty Fraud Review", "deep", "warranty-fraud-network", FRAUD_TOOLS,
     "You review a battery maker's warranty claims for leakage and organised abuse by finding links "
     "between claims: shared phones, a dealer replacing far above its peers, claims timed just before "
     "warranty ends, reused label photos, one technician carrying a dealer. Weigh every signal against "
     "its innocent explanation (fleet owners, hot regions where batteries really fail) before flagging "
     "it. Report risk and recommend audits — never accuse a person. Lead with the answer."),
    ("analyst", "Warranty Analyst", "deep",
     ["no-fault-found-analysis", "early-batch-failure", "warranty-fraud-network"],
     sorted(set(NFF_TOOLS + BATCH_TOOLS + FRAUD_TOOLS)),
     "You are a warranty analyst for a battery maker. Answer questions about warranty cost, healthy "
     "batteries replaced, batch quality and fraud, using the tools for every number and the skill that "
     "fits the question. Give rates with counts, rule out innocent explanations, report risk rather "
     "than guilt, and lead with the answer."),
]


def _body_only(text: str) -> str:
    """The skill body without frontmatter, to compare with what is published."""
    if not text.startswith("---"):
        return text.strip()
    end = text.find("\n---", 3)
    return text.strip() if end == -1 else text[end + 4:].strip()


def _declared_tools(skill: str) -> list[str]:
    """The tools a skill's frontmatter declares — exactly what its manifest may permit."""
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
            if line and not line.startswith(" "):
                break
    return sorted(set(declared))


async def main() -> None:
    async with httpx.AsyncClient(base_url=API, timeout=240) as c:
        login = await c.post("/auth/login", json={
            "email": "demo@example.com", "password": "demo-password-1234"})
        if login.status_code != 200:
            print("Could not log in as demo@example.com — create it first (platform repo: scripts/seed.py).")
            return
        auth = login.json()
        c.headers.update({"Authorization": f"Bearer {auth['access_token']}"})
        c.headers["X-Workspace-Id"] = auth["default_workspace_id"]

        # --- 0. workspace ---
        existing = (await c.get("/workspaces")).json()
        found = next((w for w in existing if w["name"] == WORKSPACE_NAME), None)
        if found:
            workspace = found["id"]
            print(f"0. Reusing workspace '{WORKSPACE_NAME}'")
        else:
            created = await c.post("/workspaces", json={"name": WORKSPACE_NAME})
            if created.status_code not in (200, 201):
                print("   could not create the workspace:", created.text[:200])
                return
            workspace = created.json()["id"]
            print(f"0. Created workspace '{WORKSPACE_NAME}'")
        c.headers["X-Workspace-Id"] = workspace

        # --- 1. tools ---
        print("\n1. Registering the battery tools")
        deadline = time.monotonic() + 120  # first start builds the data (~15 s)
        while True:
            try:
                if httpx.get(BATTERY_API + "/reference", timeout=30).status_code == 200:
                    break
            except httpx.RequestError:
                pass
            if time.monotonic() >= deadline:
                print(f"   {BATTERY_API} did not answer within 120s. Start the demo services "
                      "(docker compose up -d) and see `docker compose logs mcp-tools`.")
                return
            time.sleep(3)

        current = (await c.get("/custom-tools")).json()
        rows = current if isinstance(current, list) else current.get("tools", [])
        for tool in [t for t in rows if t["name"] in TOOL_NAMES]:
            await c.delete(f"/custom-tools/{tool['id']}")
        payload = [{"timeout_seconds": 30, **tool, "allowed_hosts": [_DEMO_HOST]} for tool in TOOLS]
        imported = await c.post("/custom-tools/import", json={"tools": payload})
        if imported.status_code not in (200, 201):
            print("   import failed:", imported.text[:300])
            return
        rows = (await c.get("/custom-tools")).json()
        rows = rows if isinstance(rows, list) else rows.get("tools", [])
        tools = {t["name"]: t["id"] for t in rows if t["name"] in TOOL_NAMES}
        live_tool_ids = set(tools.values())
        print(f"   {len(tools)} of {len(TOOL_NAMES)} tools registered")

        # --- 2. skills ---
        print("\n2. Publishing the skills")
        catalogue = {p["name"]: p for p in (await c.get("/plugins")).json()}
        plugin_ids: dict[str, str] = {}
        slugs_needed: list[str] = []
        for _key, _name, _tier, slugs, _tools, _prompt in AGENTS:
            for slug in ([slugs] if isinstance(slugs, str) else slugs):
                if slug not in slugs_needed:
                    slugs_needed.append(slug)
        for slug in slugs_needed:
            path = SKILLS_DIR / f"{slug}.md"
            if not path.exists():
                print(f"   {slug}: {path} not found")
                return
            text = path.read_text()
            prior = catalogue.get(slug)
            version = "1.0.0"
            if prior and prior.get("latest_version"):
                detail = (await c.get(f"/plugins/{prior['id']}/detail")).json()
                versions = detail.get("versions", [])
                latest = next((v for v in versions if v["version"] == prior["latest_version"]), None)
                shipped = {s["name"]: s.get("body") for s in (latest or {}).get("skills", [])}
                live_tools = set(((latest or {}).get("manifest") or {}).get("permissions", {}).get("tools") or [])
                if (shipped.get(slug) or "").strip() == _body_only(text) and live_tools == set(_declared_tools(text)):
                    plugin_ids[slug] = prior["id"]
                    print(f"   {slug:<28} unchanged at {prior['latest_version']}")
                    continue
                major, minor, _patch = prior["latest_version"].split(".")
                taken = {v["version"] for v in versions}
                minor = int(minor)
                while f"{major}.{minor + 1}.0" in taken:
                    minor += 1
                version = f"{major}.{minor + 1}.0"
            published = await c.post("/plugins/publish", json={
                "manifest": {"name": slug, "version": version, "description": f"{slug} capability.",
                             "permissions": {"tools": _declared_tools(text)}},
                "skills": {slug: text}, "changelog": f"{slug} {version}", "draft": False})
            if published.status_code != 201:
                print(f"   publish failed for {slug}:", published.text[:220])
                return
            plugin_ids[slug] = published.json()["plugin_id"]
            print(f"   {slug:<28} published {version}")

        # --- 3. agents ---
        models = (await c.get(f"/workspaces/{workspace}/models")).json()["models"]
        available = [m["id"] for m in models if m["available"]]
        if not available:
            print("\n   No usable model in this workspace. A model needs a grant AND a provider key,\n"
                  "   and keys are per workspace. Sign in as the owner, switch to this workspace,\n"
                  "   add the key under Administration -> API keys, then re-run this seed.")
            return
        fast = "claude-haiku-4-5" if "claude-haiku-4-5" in available else available[0]
        deep = "claude-sonnet-5" if "claude-sonnet-5" in available else available[0]
        print(f"\n3. Building the agents  (fast={fast}  deep={deep})")

        registry = {a["name"]: a["id"] for a in (await c.get("/agents")).json()}
        for _key, name, tier, slugs, tool_names, prompt in AGENTS:
            slug_list = [slugs] if isinstance(slugs, str) else slugs
            missing = [t for t in tool_names if t not in tools]
            if missing:
                print(f"   {name}: tools not registered: {', '.join(missing)}")
                continue
            config = {
                "agent_type": "simple",
                "model": deep if tier == "deep" else fast,
                "system_prompt": prompt,
                "builtin_tools": [],
                "custom_tool_ids": [tools[t] for t in tool_names],
                "skills": [{"plugin_id": plugin_ids[sl], "skill_names": [sl]} for sl in slug_list],
            }
            if name in registry:
                agent_id = registry[name]
                made = await c.post(f"/agents/{agent_id}/versions", json=config)
                if made.status_code != 201:
                    print(f"   {name} version failed:", made.text[:200])
                    continue
                action = f"updated to v{made.json()['version']}"
            else:
                created = await c.post("/agents", json={
                    "name": name, "description": f"Battery warranty — {slug_list[0]}.", "config": config})
                if created.status_code not in (200, 201):
                    print(f"   {name} failed:", created.text[:200])
                    continue
                agent_id = created.json()["id"]
                action = "created"
            # Deploying is what puts an agent under Tasks.
            deployed = await c.post(f"/agents/{agent_id}/deploy", json={})
            if deployed.status_code not in (200, 201):
                print(f"   {name} deploy failed:", deployed.text[:200])
                continue
            check = (await c.get(f"/agents/{agent_id}")).json()
            stored = check.get("config", {}).get("custom_tool_ids", [])
            live = [t for t in stored if t in live_tool_ids]
            flag = "" if len(live) == len(config["custom_tool_ids"]) else "  <-- MISMATCH"
            bound = len(check.get("skill_bindings", []))
            print(f"   {name:<26} {action + ' + deployed':<26} {len(live)} tools, "
                  f"{bound} skill{'s' if bound != 1 else ''}{flag}")

        print(f"\nDone. Workspace: {WORKSPACE_NAME}")
        print("\nTry each agent in chat (see battery-agent-tests.md):")
        cases = {
            "nff": "'Why is our warranty cost high?'   then CLM-PUN-24601 vs CLM-JAI-31877",
            "batch": "'Is any batch failing early?'   then H1-2201-1",
            "fraud": "'Which dealers should we audit?'   then +919822077110",
            "analyst": "'Where are we losing warranty money?'",
        }
        for key, name, *_ in AGENTS:
            print(f"  {name:<26} {cases.get(key, '')}")


if __name__ == "__main__":
    asyncio.run(main())
