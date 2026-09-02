"""Seed the DISCOM workspace: tools, ten skills, ten agents.

    docker compose exec mcp-tools python seeds/discom.py

Ten independent cases from a distribution utility's operations — collection,
disconnection recovery, theft, site survey, illegal restoration, complaints,
call centre, asset maintenance, load forecasting, and an employee copilot.

Each is a single-purpose agent holding exactly one skill and only the tools
that skill declares. They are deliberately not wired into a pipeline: several
of them are decisions a human signs, and chaining them before each has been
exercised on its own would hide which stage produced a wrong answer.
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
DISCOM_API = os.environ.get("DISCOM_API_URL", f"http://{_DEMO_HOST}:8304/discom")

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
WORKSPACE_NAME = "DISCOM Operations"


def _get(name: str, desc: str, path: str, params: dict[str, str] | None = None,
         query: dict[str, str] | None = None) -> dict:
    """One GET tool. `params` are path parameters, `query` are query parameters."""
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
        "url_template": DISCOM_API + path,
        "param_locations": locations,
        "input_schema": {"type": "object", "properties": props,
                         "required": list((params or {}).keys())},
    }


_C = {"consumer_no": "e.g. DL-4471002, CM-8890145"}

TOOLS = [
    _get("getConsumer",
         "Consumer record: category, connected and sanctioned load, tariff, "
         "feeder and DT, supply status, outstanding with its breakdown.",
         "/consumers/{consumer_no}", _C),
    _get("getBillingHistory",
         "Billed periods with units, amount, and whether the read was actual "
         "or estimated. Includes how many estimated periods precede the last "
         "actual read — the figure that separates catch-up billing from a "
         "meter fault.",
         "/consumers/{consumer_no}/billing", _C),
    _get("getPaymentHistory",
         "Payment status by period with totals, consecutive unpaid count, "
         "promises to pay and whether they were kept, and receipts.",
         "/consumers/{consumer_no}/payments", _C),
    _get("getConsumptionHistory",
         "Metered units by period with basis, mean of actual reads, connected "
         "load, and any recorded load changes.",
         "/consumers/{consumer_no}/consumption", _C),
    _get("getNoticeHistory",
         "Notices and reminders served, whether delivered, and whether the "
         "consumer responded.",
         "/consumers/{consumer_no}/notices", _C),
    _get("getDisconnectionRecord",
         "TD/PD record: date, method, whether the disconnection was actually "
         "executed and acknowledged in the field, reading taken, restorations.",
         "/consumers/{consumer_no}/disconnection", _C),
    _get("getMeterStatus",
         "Meter type, last read, communication state, issued seal number and "
         "the tamper event log with work-order references.",
         "/meters/{meter_no}", {"meter_no": "e.g. MT-66210984"}),
    _get("getSiteSurvey",
         "Field surveyor's findings at the premises: occupancy, observations, "
         "whether supply appears live.",
         "/consumers/{consumer_no}/survey", _C),
    _get("getSurveyImageAnalysis",
         "Image-analysis detections and OCR from survey photographs, each with "
         "a confidence, plus what the images did not capture.",
         "/surveys/{consumer_no}/images", _C),
    _get("getPeerBenchmark",
         "Consumption of comparable consumers as a distribution with cohort "
         "size — the weakest evidence in an anomaly case, returned so its "
         "spread stays visible.",
         "/consumers/{consumer_no}/peers", _C),
    _get("getDTHealth",
         "Distribution asset condition: rating, loading trend, oil temperature "
         "against ambient, phase imbalance, maintenance, failures and trips.",
         "/assets/{asset_id}", {"asset_id": "e.g. DT-4587"}),
    _get("getLoadHistory",
         "Monthly peak loading as a percentage of rating, and phase imbalance.",
         "/assets/{asset_id}/load", {"asset_id": "e.g. DT-4587"}),
    _get("getMaintenanceHistory",
         "Maintenance cycle and last attendance, failures, trips including "
         "no-fault-found restorations, consumers served, critical loads and "
         "whether an alternative feed exists.",
         "/assets/{asset_id}/maintenance", {"asset_id": "e.g. DT-4587"}),
    _get("getFeederLosses",
         "Energy in against energy billed for a feeder. Locates an area worth "
         "investigating; never evidence against an individual consumer.",
         "/feeders/{feeder_id}/losses", {"feeder_id": "e.g. F-07-HDP"}),
    _get("getOutageHistory",
         "Recorded outages on a feeder with cause where one was captured.",
         "/feeders/{feeder_id}/outages", {"feeder_id": "e.g. F-19-URL"}),
    _get("getLoadForecast",
         "Demand forecast for a feeder with its assumptions and recent "
         "forecast-versus-actual, unaggregated so the shape of the error shows.",
         "/feeders/{feeder_id}/forecast", {"feeder_id": "e.g. F-07-HDP"}),
    _get("getWeatherContext",
         "Temperature outlook against the normal-year mean, and festivals and "
         "holidays in the horizon.",
         "/weather/{area}", {"area": "e.g. Pune East"}),
    _get("getComplaint", "One complaint with its text, channel and status.",
         "/complaints/{complaint_id}", {"complaint_id": "e.g. CMP-33012"}),
    _get("listComplaints", "Complaints in the queue.", "/complaints", None,
         {"status": "open | closed"}),
    _get("getComplaintHistory",
         "Prior complaints for a consumer and how each was closed — including "
         "closures with no site visit recorded.",
         "/consumers/{consumer_no}/complaints", _C),
    _get("getCallTranscript",
         "Call-centre transcript, turn by turn, with timestamps for citation.",
         "/calls/{call_id}", {"call_id": "e.g. CALL-77201"}),
    _get("listTDConsumers",
         "Temporarily disconnected consumers filtered by dues, TD age and "
         "division. Echoes the filters and their boundary rules.",
         "/td-consumers", None,
         {"min_outstanding": "rupees, inclusive",
          "min_td_days": "days since disconnection",
          "division": "e.g. Pune East"}),
    _get("getDivisionSummary",
         "Division rollup with consumers, TD count, PD conversions, collection "
         "and losses, plus notes on what makes comparisons invalid.",
         "/divisions/{division}", {"division": "e.g. Pune Rural"}),
    _get("listDivisions", "Every division with denominators included.",
         "/divisions"),
    _get("getCollectionPortfolio",
         "The outstanding book segmented by payment behaviour, with expected "
         "recovery, mean probability and historical response by channel for "
         "each segment.",
         "/portfolio", None, {"division": "e.g. Pune East; omit for all"}),
    _get("listCollectionTargets",
         "Accounts ranked by expected recovery (outstanding x probability), "
         "filterable by segment, division, balance and probability. Returns "
         "the matched count and total separately from the rows shown.",
         "/portfolio/accounts", None,
         {"segment": "e.g. recent_deterioration",
          "division": "e.g. Pune East",
          "min_outstanding": "rupees, inclusive",
          "min_probability": "0-1, inclusive",
          "limit": "rows to return, max 100"}),
    _get("getConsumerScore",
         "One account's payment probability with the contribution of each "
         "feature behind it, so the score can be explained rather than "
         "asserted.",
         "/portfolio/consumers/{consumer_no}/score",
         {"consumer_no": "e.g. DL-700123"}),
    _get("buildCampaignList",
         "Selects the top N accounts for a channel from the whole book, sized "
         "to that channel's monthly capacity, with the segments excluded, the "
         "expected recovery, the cost and a sample of the list. This is the "
         "working list a field team receives.",
         "/portfolio/campaign", None,
         {"channel": "field_visit | call | sms | notice | disconnection",
          "capacity": "accounts to select; defaults to the channel's monthly capacity",
          "exclude_disputed": "true | false, default true",
          "exclude_vacated": "true | false, default true",
          "min_outstanding": "rupees, inclusive",
          "min_chronic_risk": "0-1; use to build a campaign against the "
                              "early-warning population",
          "division": "e.g. Pune East"}),
    _get("listEarlyWarning",
         "Accounts most likely to become chronic defaulters, ranked on chronic "
         "risk rather than payment probability. Accounts already chronic score "
         "zero — the point is who can still be caught.",
         "/portfolio/early-warning", None,
         {"limit": "rows to return, max 100",
          "min_risk": "0-1, inclusive",
          "division": "e.g. Pune East"}),
    _get("getRecoveryChannels",
         "Cost per account and monthly capacity of each recovery channel. "
         "Field capacity is the binding constraint on any campaign.",
         "/portfolio/channels"),
    _get("getCampaignHistory",
         "Past collection campaigns with the segments they hit, cost, "
         "recovery and return per rupee spent.",
         "/portfolio/campaigns"),
    _get("getCollectionForecast",
         "Expected collection for the coming month at current effort, with "
         "the last six forecasts against actuals.",
         "/portfolio/forecast", None,
         {"division": "e.g. Pune East; omit for all"}),
]

TOOL_NAMES = {t["name"] for t in TOOLS}

# (key, agent name, model tier, skill, tools, system prompt)
AGENTS = [
    (
        "payment", "Revenue & Collection AI", "deep", "revenue-collection-ai",
        ["getCollectionPortfolio", "buildCampaignList", "listEarlyWarning",
         "listCollectionTargets", "getConsumerScore",
         "getRecoveryChannels", "getCampaignHistory", "getCollectionForecast",
         "getConsumer", "getBillingHistory", "getPaymentHistory",
         "getConsumptionHistory", "getNoticeHistory", "getDisconnectionRecord"],
        "You decide where a DISCOM spends its collection effort.\n\n"
        "A consumer number means assess that one account. Anything else — a "
        "segment, a division, a campaign, a forecast — means work the book, "
        "starting with getCollectionPortfolio.\n\n"
        "Rank on expected recovery, which is outstanding multiplied by payment "
        "probability, never on the balance alone. The segment holding the most "
        "money returns the least of it in almost every book, and a campaign "
        "built on the balance column sends field teams to people who were "
        "never going to pay.\n\n"
        "Check getRecoveryChannels before proposing anything: field capacity "
        "is finite and a plan that exceeds it is not a plan. Say what the "
        "capacity would otherwise have done. Read getCampaignHistory before "
        "recommending a campaign that resembles one already run.\n\n"
        "Exclude disputed balances and vacated premises before ranking, and "
        "give their counts — excluding them is a recommendation, not an "
        "omission.\n\n"
        "When asked to plan a campaign, call buildCampaignList to produce "
        "the actual working list, and open with the headline: from the "
        "population, how many accounts were selected, on what channel, and "
        "what they are expected to recover.\n\n"
        "Read the payment behaviour before the balance. A large arrear on a "
        "consumer who has paid 19 of 24 cycles is a different problem from a "
        "small one on a consumer who has never paid without a notice, and the "
        "balance alone cannot tell them apart.\n\n"
        "Check getNoticeHistory before recommending a rung: never propose an "
        "action that has already been tried and failed twice. Where a bill is "
        "disputed, the answer is HOLD.",
    ),
    (
        "recovery", "TD Recovery Prediction", "deep",
        "td-recovery-prediction",
        ["getConsumer", "getDisconnectionRecord", "getPaymentHistory",
         "getBillingHistory", "getConsumptionHistory", "getMeterStatus",
         "getSiteSurvey", "getNoticeHistory"],
        "You rank one disconnected account against a finite number of field "
        "visits.\n\n"
        "Recovery priority is recoverable amount multiplied by probability of "
        "recovery. State both separately before combining them. A large sum "
        "owed by an untraceable occupier of a stripped premises scores low; a "
        "modest sum owed by a trading shop with a live connection scores high. "
        "Where a site survey exists it outranks anything you inferred from "
        "consumption data.",
    ),
    (
        "theft", "Theft/Anomaly Detection", "deep", "theft-anomaly-detection",
        ["getConsumer", "getConsumptionHistory", "getMeterStatus",
         "getPeerBenchmark", "getBillingHistory", "getSiteSurvey",
         "getFeederLosses"],
        "You build a case for inspection, never a finding of theft.\n\n"
        "For every pattern you rely on, name the innocent explanation and say "
        "how you excluded it. Check getConsumptionHistory for a recorded load "
        "change before treating any drop as suspicious — a documented load "
        "surrender produces exactly the profile a theft model flags.\n\n"
        "Physical and metering evidence outranks statistical comparison. Peer "
        "benchmarks are a prompt to look, never a reason to accuse. Feeder "
        "loss is context for the area and must not contribute to an individual "
        "consumer's score. Distinguish unauthorised use under section 126 from "
        "theft under section 135, and never name a person as a thief.",
    ),
    (
        "survey", "AI Site Survey", "fast", "ai-site-survey",
        ["getSiteSurvey", "getSurveyImageAnalysis", "getConsumer",
         "getMeterStatus", "getDisconnectionRecord", "getConsumptionHistory"],
        "You review detections, not photographs. Every label from the image "
        "analysis is a claim with a confidence attached; never restate one as "
        "something you observed.\n\n"
        "The meter number is the anchor and an OCR misread moves the whole "
        "case onto another consumer's account. Report it exactly as read, "
        "compare it with the record, and where they differ by one of the "
        "predictable OCR pairs — 0/O, 1/7, 5/S, 8/B, 6/G — say it is probably "
        "an artefact and mark it for manual confirmation. Never silently "
        "correct it to match.\n\n"
        "Distinguish 'not present' from 'not visible in the images provided' "
        "every time.",
    ),
    (
        "restoration", "Illegal Restoration Detection", "deep",
        "illegal-restoration-detection",
        ["getConsumer", "getDisconnectionRecord", "getConsumptionHistory",
         "getMeterStatus", "getSiteSurvey", "getBillingHistory"],
        "You decide whether post-disconnection consumption is unauthorised "
        "restoration or the utility's own record being wrong.\n\n"
        "Give four figures every time: disconnection date and method, expected "
        "consumption, actual consumption by period, and the gap.\n\n"
        "Before concluding restoration, establish that the disconnection was "
        "actually executed — check executed_on and field_acknowledgement. An "
        "order raised and closed in the system with no field record is a "
        "process failure, not an offence, and caps your risk score. Only "
        "actual meter reads count; a case built on estimated reads is not a "
        "case.",
    ),
    (
        "complaint", "Complaint AI", "fast", "complaint-ai",
        ["getComplaint", "listComplaints", "getComplaintHistory", "getConsumer",
         "getConsumptionHistory", "getBillingHistory", "getOutageHistory"],
        "You route one complaint.\n\n"
        "Read it for danger before you categorise it. Sparking, burning smell, "
        "shock, a fallen conductor — that is CRITICAL_SAFETY whatever else the "
        "complaint is about, and safety wording is often buried inside a "
        "billing query.\n\n"
        "Before assigning a cause, check the billing history. A run of "
        "estimated bills followed by one actual read produces the classic "
        "'bill jumped and the meter is running fast' complaint, and the cause "
        "is catch-up billing, not a fast meter. A repeat complaint is never "
        "LOW priority.",
    ),
    (
        "call", "Call Centre AI", "deep", "call-centre-ai",
        ["getCallTranscript", "getConsumer", "getBillingHistory",
         "getComplaintHistory", "getDisconnectionRecord", "getOutageHistory"],
        "You establish what a caller needed, whether they got it, and what "
        "must happen next.\n\n"
        "Intent is what they needed, not what they said first: 'why is my bill "
        "so high' is very often a payment-arrangement call the consumer is "
        "working up to. Resolution is judged on outcome, not on courtesy.\n\n"
        "Verify what was said against the records — an agent who told a "
        "consumer their payment was not received, where the ledger shows it "
        "was, is the finding of the call. Look for agent misconduct as hard as "
        "you look for consumer misconduct.",
    ),
    (
        "asset", "Predictive Maintenance", "deep", "predictive-maintenance",
        ["getDTHealth", "getLoadHistory", "getMaintenanceHistory",
         "getOutageHistory", "getFeederLosses"],
        "You decide which asset a maintenance crew attends next.\n\n"
        "Trend beats level. State the current value and its direction over a "
        "stated window, always. Rising oil temperature at constant or falling "
        "ambient and constant load is the degradation signature and should "
        "move the risk sharply.\n\n"
        "Repeat trips recorded as 'restored, no fault found' are not a clean "
        "record — they are the signature of an intermittent developing fault.\n\n"
        "Keep failure risk and consequence separate. A low-risk asset feeding "
        "a hospital with no alternative supply may be attended first, and you "
        "say that as a ranking recommendation — never by inflating the risk "
        "band.",
    ),
    (
        "forecast", "Load Forecasting", "deep",
        "load-forecasting",
        ["getLoadForecast", "getLoadHistory", "getWeatherContext",
         "getOutageHistory", "getFeederLosses"],
        "You review a forecast that power will be bought against; you do not "
        "produce it.\n\n"
        "Check the assumptions before the number. Compare the forecast's "
        "temperature assumption against the outlook, and check the calendar in "
        "the horizon for festivals and holidays the model may not have "
        "accounted for.\n\n"
        "Judge the model by the shape of its residuals, not their average. A "
        "consistent one-directional miss is far more dangerous than the same "
        "magnitude of scatter, and it is invisible in a mean absolute error.",
    ),
    (
        "copilot", "AI Employee Copilot", "deep", "ai-employee-copilot",
        ["listTDConsumers", "getDivisionSummary", "listDivisions",
         "getConsumer", "getBillingHistory", "getPaymentHistory",
         "getDisconnectionRecord", "getConsumptionHistory", "getFeederLosses"],
        "You answer operational questions for people who run a distribution "
        "utility, and your answers reach management reviews.\n\n"
        "State the filters and boundary rules you applied. Give denominators "
        "with every rate. Check whether the latest period is complete before "
        "comparing it with full ones, and read the period notes for boundary "
        "revisions — a division that gained 11,200 consumers mid-year cannot "
        "be compared month on month across that date.\n\n"
        "On 'why' questions: decompose before explaining, check the boring "
        "explanation first, and label every cause as a hypothesis with the "
        "check that would confirm it. Never present a hypothesis as a finding.",
    ),
]


def _body_only(text: str) -> str:
    """The skill body, without frontmatter — for comparing against what is
    published, so an unchanged skill is not republished as a new version."""
    if not text.startswith("---"):
        return text.strip()
    end = text.find("\n---", 3)
    return text.strip() if end == -1 else text[end + 4:].strip()


def _declared_tools(skill: str) -> list[str]:
    """Every tool the manifest must declare for this skill to publish.

    The platform rejects a bundle whose skill requests a tool the manifest does
    not permit. Built from the connector list unioned with whatever the skill's
    own frontmatter declares, so a skill naming something outside the list
    cannot fail validation with a message about the manifest.
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
            if line and not line.startswith(" "):
                break
    return sorted(set(TOOL_NAMES) | set(declared))


async def main() -> None:
    async with httpx.AsyncClient(base_url=API, timeout=240) as c:
        login = await c.post("/auth/login", json={
            "email": "demo@example.com", "password": "demo-password-1234"})
        if login.status_code != 200:
            print("Could not log in as demo@example.com.")
            print("Create it first, from the platform repository:")
            print("  docker compose -f docker-compose.prod.yml exec api "
                  "python scripts/seed.py")
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
        print("\n1. Registering the DISCOM connectors")
        deadline = time.monotonic() + 90
        announced = False
        while True:
            try:
                if httpx.get(DISCOM_API + "/divisions", timeout=10).status_code == 200:
                    break
            except httpx.RequestError:
                pass
            if time.monotonic() >= deadline:
                print(
                    f"   {DISCOM_API} did not come up within 90s.\n"
                    "   Start the demo services:\n"
                    "     docker compose up -d\n"
                    "   If it is running, its log says why it is not listening:\n"
                    "     docker compose logs --tail=40 mcp-tools\n"
                    "   Nothing was changed; re-running reuses the workspace."
                )
                return
            if not announced:
                print(f"   waiting for {DISCOM_API} …")
                announced = True
            time.sleep(3)

        current = (await c.get("/custom-tools")).json()
        rows = current if isinstance(current, list) else current.get("tools", [])
        for tool in [t for t in rows if t["name"] in TOOL_NAMES]:
            await c.delete(f"/custom-tools/{tool['id']}")

        payload = [{"timeout_seconds": 30, **tool, "allowed_hosts": [_DEMO_HOST]}
                   for tool in TOOLS]
        await c.post("/custom-tools/import", json={"tools": payload})
        rows = (await c.get("/custom-tools")).json()
        rows = rows if isinstance(rows, list) else rows.get("tools", [])
        tools = {t["name"]: t["id"] for t in rows if t["name"] in TOOL_NAMES}
        live_tool_ids = set(tools.values())
        print(f"   {len(tools)} of {len(TOOL_NAMES)} tools registered")

        # --- 2. skills ---
        print("\n2. Publishing the skills")
        catalogue = {p["name"]: p for p in (await c.get("/plugins")).json()}
        plugin_ids: dict[str, str] = {}
        for _key, _name, _tier, slug, _tool_names, _prompt in AGENTS:
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
                "changelog": f"{slug} {version}", "draft": False})
            if published.status_code != 201:
                print(f"   publish failed for {slug}:", published.text[:220])
                return
            plugin_ids[slug] = published.json()["plugin_id"]
            print(f"   {slug:<34} published {version}")

        # --- 3. agents ---
        models = (await c.get(f"/workspaces/{workspace}/models")).json()["models"]
        available = [m["id"] for m in models if m["available"]]
        if not available:
            print("\n   No usable model in this workspace. Why, per model:")
            for m in models[:6]:
                print(f"     {m['id']:<28} "
                      f"{m.get('unavailable_reason') or 'unavailable'}")
            print(
                "\n   A model needs BOTH a grant and a provider key, and the key\n"
                "   is per workspace — it is not inherited from another one.\n"
                "   Sign in as the owner, switch to this workspace, then:\n"
                "     Administration -> Anthropic   (paste the key)\n"
                "     Administration -> Models      (grant, if the reason says so)\n"
                "   Then re-run this seed; it reuses everything above."
            )
            return
        fast = "claude-haiku-4-5" if "claude-haiku-4-5" in available else available[0]
        deep = "claude-sonnet-5" if "claude-sonnet-5" in available else available[0]
        print(f"\n3. Building the agents  (fast={fast}  deep={deep})")

        registry = {a["name"]: a["id"] for a in (await c.get("/agents")).json()}
        for _key, name, tier, slug, tool_names, prompt in AGENTS:
            config = {
                # `simple` throughout: each of these is one model call with
                # tools against one subject. A plan-and-critique loop tripled
                # the cost on the earlier demos and changed no answer.
                "agent_type": "simple",
                "model": deep if tier == "deep" else fast,
                "system_prompt": prompt,
                "builtin_tools": [],
                "custom_tool_ids": [tools[t] for t in tool_names if t in tools],
                "skills": [
                    {"plugin_id": plugin_ids[slug], "skill_names": [slug]}
                ] if slug in plugin_ids else [],
            }
            missing = [t for t in tool_names if t not in tools]
            if missing:
                print(f"   {name}: tools not registered: {', '.join(missing)}")
                continue
            if name in registry:
                # Agent versions are immutable, so there is no PATCH: an edit
                # is a new version plus a deploy. The seed used to call
                # PATCH /agents/{id} and ignore the response — the endpoint
                # does not exist, so every re-run printed "updated" while
                # changing nothing, and the agents kept tool ids that the
                # re-import below had already deleted.
                agent_id = registry[name]
                made = await c.post(f"/agents/{agent_id}/versions", json=config)
                if made.status_code != 201:
                    print(f"   {name} version failed:", made.text[:200])
                    continue
                deployed = await c.post(f"/agents/{agent_id}/deploy", json={})
                if deployed.status_code not in (200, 201):
                    print(f"   {name} deploy failed:", deployed.text[:200])
                    continue
                action = f"updated to v{made.json()['version']}"
            else:
                created = await c.post("/agents", json={
                    "name": name,
                    "description": f"DISCOM operations — {slug}.",
                    "config": config})
                if created.status_code not in (200, 201):
                    print(f"   {name} failed:", created.text[:200])
                    continue
                action = "created"

            # Read back rather than trusting what was sent. Everything above
            # can report success and leave an agent pointing at tools that no
            # longer exist, which is exactly what happened.
            check = (await c.get(f"/agents/{agent_id if name in registry else created.json()['id']}")).json()
            stored = check.get("config", {}).get("custom_tool_ids", [])
            live = [t for t in stored if t in live_tool_ids]
            flag = "" if len(live) == len(config["custom_tool_ids"]) else "  <-- MISMATCH"
            print(f"   {name:<30} {action:<16} {len(live)} tools, "
                  f"{len(check.get('skill_bindings', []))} skill{flag}")

        print(f"\nDone. Workspace: {WORKSPACE_NAME}")
        print("\nTry each agent in chat:")
        # Built from AGENTS rather than written out, so a renamed agent cannot
        # leave this list pointing at a name that no longer exists.
        cases = {
            "payment": "'Plan next month's field campaign'  |  DL-4471002",
            "recovery": "CM-8890145   then DL-2245108",
            "theft": "CM-5561093   then IN-7734021",
            "survey": "CM-8890145",
            "restoration": "CM-8890145",
            "complaint": "CMP-33012, CMP-33018, CMP-33021",
            "call": "CALL-77201",
            "asset": "DT-4587      then DT-2210",
            "forecast": "F-07-HDP",
            "copilot": "'TD consumers above 50000 over 180 days'",
        }
        for line in [f"  {name:<30} {cases.get(key, '')}"
                     for key, name, *_ in AGENTS]:
            print(line)
        print("\nEach pair is a case and its counter-case: the second is the one")
        print("a naive model gets wrong.")


if __name__ == "__main__":
    asyncio.run(main())
