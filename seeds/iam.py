"""Seed the IAM access-review demo: five skills, five agents, one pipeline.

Replaces a manual PAR/PPAR and Service Account Review process — the work three
people currently do by hand across readiness, pre-validation, certification,
post-certification and SAR.

The architecture follows the proposal's five agents. What differs is the
orchestrator: the proposal assumes LangGraph, and this platform already *is*
the state graph — pipeline nodes, shared context between steps, a governor
enforcing budgets. So the agents are built here rather than in a second
framework alongside.

Model tiering is kept exactly as specified, because it is the cost argument:
Haiku where the work is API orchestration and classification, Sonnet only where
judgment is needed — delta reasoning over revoked access, vault gap risk, and
audit narrative.

Idempotent: re-running replaces the previous agents and pipeline rather than
leaving another differently-named copy beside them.

    docker compose up -d      # in indicus-ai-mcp-tools   # data
    backend/.venv/bin/python scripts/iam_demo_seed.py                  # seed
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

API = "http://127.0.0.1:8000/api/v1"
WORKSPACE_NAME = "IAM Access Review"
PIPELINE_NAME = "IAM Access Review"
PLUGIN_NAME = "iam-access-review"
AGENT_NAMES = {
    "IAM Readiness",
    "SME Pre-Validation",
    "Certification Monitor",
    "Post-Certification Analyst",
    "Service Account Review",
    "IAM Copilot",
}
# Skills live as markdown beside the demo data rather than as string constants
# in here. They are content an IAM lead should be able to read and edit without
# opening a Python file, and reviewing a SKILL.md inside a triple-quoted string
# is how wording mistakes survive.
SKILL_DIR = Path(__file__).resolve().parents[1] / "skills"
_DEMO_HOST = os.environ.get("DEMO_HOST", "127.0.0.1")
IAM_API = os.environ.get("IAM_API_URL", f"http://{_DEMO_HOST}:8304/iam")

# Only the operations an agent actually needs. Every tool description sits in
# context on every request, so importing all fifteen would spend tokens on
# capability the pipeline never uses.
# Tools that read the platform's own campaign engine rather than the identity
# source. Declared here rather than imported from an OpenAPI document because
# they need a service credential, and a key that can write to campaigns should
# be created deliberately and scoped to one workspace, not swept up by a
# bulk import.
PLATFORM_API = "http://127.0.0.1:8000/api/v1"

CAMPAIGN_TOOLS = [
    {
        "name": "getCampaignProgress",
        "description": (
            "Real completion for a certification campaign: items decided, "
            "approved and revoked, which reviewers are outstanding, and how "
            "many items have no reviewer at all. Takes the campaign id."
        ),
        "method": "GET",
        "url_template": PLATFORM_API + "/campaigns/{campaign_id}/progress",
        "param_locations": {"campaign_id": "path"},
        "input_schema": {
            "type": "object",
            "required": ["campaign_id"],
            "properties": {"campaign_id": {"type": "string",
                                           "description": "Campaign UUID"}},
        },
    },
    {
        "name": "getCampaignDecisions",
        "description": (
            "The decisions reviewers actually recorded — who decided, what "
            "they decided, and the justification they gave. Filter with "
            "decision=revoked to see only removals."
        ),
        "method": "GET",
        "url_template": PLATFORM_API + "/campaigns/{campaign_id}/decisions",
        "param_locations": {"campaign_id": "path", "decision": "query",
                            "offset": "query", "limit": "query"},
        "input_schema": {
            "type": "object",
            "required": ["campaign_id"],
            "properties": {
                "campaign_id": {"type": "string", "description": "Campaign UUID"},
                "decision": {"type": "string", "description": "approved | revoked"},
                "offset": {"type": "integer", "description": "Rows to skip"},
                "limit": {"type": "integer", "description": "Max rows, up to 1000"},
            },
        },
    },
    {
        "name": "getCampaignRemediation",
        "description": (
            "Revocations a campaign ordered and whether they happened. open = "
            "nobody actioned it; closed = somebody says they did; verified = "
            "the access was re-read and is gone; failed = it is still there."
        ),
        "method": "GET",
        "url_template": PLATFORM_API + "/campaigns/{campaign_id}/remediation",
        "param_locations": {"campaign_id": "path", "status": "query"},
        "input_schema": {
            "type": "object",
            "required": ["campaign_id"],
            "properties": {
                "campaign_id": {"type": "string", "description": "Campaign UUID"},
                "status": {"type": "string",
                           "description": "open | closed | verified | failed"},
            },
        },
    },
    {
        "name": "verifyCampaignRemediation",
        "description": (
            "Re-read the estate and check revoked access is actually gone. "
            "Returns what is still present — access a reviewer ordered removed "
            "that is live again."
        ),
        "method": "POST",
        "url_template": PLATFORM_API + "/campaigns/{campaign_id}/verify-remediation",
        "param_locations": {"campaign_id": "path"},
        "input_schema": {
            "type": "object",
            "required": ["campaign_id"],
            "properties": {"campaign_id": {"type": "string",
                                           "description": "Campaign UUID"}},
        },
    },
]
CAMPAIGN_TOOL_NAMES = {t["name"] for t in CAMPAIGN_TOOLS}



WANTED = {
    "getCertificationScope",
    "getEntitlementQuality",
    "getUncorrelatedAccounts",
    "getInactiveUsersWithAccess",
    "getSmeValidationStatus",
    "sendTeamsMessage",
    "sendOutlookEmail",
    "getSentMessages",
    "getIdentity",
    "getCertificationProgress",
    "getCertificationDecisions",
    "getReinstatedAccess",
    "getRemediationGaps",
    "getServiceAccount",
    "getServiceAccountInventory",
    "getVaultOnboardingGaps",
    "getServiceAccountDelta",
    "getVaultRecord",
    "getEnvironmentSummary",
}


def _body_only(markdown: str) -> str:
    """The SKILL.md with its frontmatter removed.

    The platform parses the frontmatter into columns and stores only what
    follows, so a published skill's body never equals the file on disk. An
    unchanged-content check that compares the two therefore always reports a
    difference — and republishes every run, which is the churn it exists to
    prevent.
    """
    text = markdown.lstrip()
    if not text.startswith("---"):
        return markdown.strip()
    end = text.find("\n---", 3)
    if end == -1:
        return markdown.strip()
    return text[end + 4 :].strip()


def _summary(body: str) -> str:
    """The skill's own description line, for the bundle that carries it.

    Taken from the SKILL.md frontmatter rather than written twice: the card in
    the UI and the skill itself should not be able to disagree about what the
    skill is for.
    """
    lines = body.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    out: list[str] = []
    collecting = False
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            collecting = True
            rest = line.split(":", 1)[1].strip()
            if rest and rest != ">":
                out.append(rest)
            continue
        if collecting:
            if line[:1] not in (" ", "\t"):
                break
            out.append(line.strip())
    return " ".join(out).strip()


async def main() -> None:
    async with httpx.AsyncClient(base_url=API, timeout=180) as c:
        login = await c.post(
            "/auth/login",
            json={"email": "demo@example.com", "password": "demo-password-1234"},
        )
        if login.status_code != 200:
            print("Could not log in as demo@example.com — is the API running?")
            return
        data = login.json()
        c.headers.update({"Authorization": f"Bearer {data['access_token']}"})

        # A workspace of its own, not the default one.
        #
        # Everything in this platform is workspace-scoped — agents, skills,
        # tools, pipelines, runs — so a dedicated workspace is what keeps the
        # access review separable from whatever else is in the account. It is
        # also what makes the demo honest: an IAM team would be given their own
        # workspace, not a shared one with somebody else's agents in the list.
        #
        # Reused if it already exists, so re-running does not accumulate a new
        # workspace each time.
        c.headers["X-Workspace-Id"] = data["default_workspace_id"]
        existing = (await c.get("/workspaces")).json()
        match = next(
            (w for w in existing if w["name"] == WORKSPACE_NAME), None
        )
        if match:
            workspace = match["id"]
            print(f"Reusing workspace '{WORKSPACE_NAME}' ({workspace})")
        else:
            created = await c.post(
                "/workspaces",
                json={
                    "name": WORKSPACE_NAME,
                    "description": (
                        "Access certification and service account review. "
                        "PAR/PPAR and SAR, end to end."
                    ),
                },
            )
            if created.status_code != 201:
                print("Could not create the workspace:", created.text[:200])
                return
            workspace = created.json()["id"]
            print(f"Created workspace '{WORKSPACE_NAME}' ({workspace})")

        c.headers["X-Workspace-Id"] = workspace

        print()

        # --- 0a. what already exists here -----------------------------------
        #
        # Reused, not replaced. `DELETE /agents/{id}` archives rather than
        # removes, and an archived agent keeps its slug — so deleting and
        # recreating under the same name collides on (workspace_id, slug) and
        # the create fails. That is the real reason the original demo script
        # tagged every name with random hex: it sidesteps the collision, at the
        # cost of leaving "IAM Access Review 6dfd" beside "IAM Access Review
        # 8ec8" in a demo somebody is watching.
        #
        # Agents are versioned, so the honest way to re-seed is to add a version
        # to the agent that is already there. Names stay clean, nothing
        # accumulates, and the edit history is visible where it belongs.
        existing_agents = {
            a["name"]: a["id"] for a in (await c.get("/agents")).json()
        }
        existing_pipelines = {
            w["name"]: w["id"] for w in (await c.get("/workflows")).json()
        }
        if existing_agents or existing_pipelines:
            print(
                f"Found {len(existing_agents)} agent(s) and "
                f"{len(existing_pipelines)} pipeline(s) already here — "
                "adding versions rather than duplicates"
            )

        # --- 0. how much data the demo is actually working over -------------
        async with httpx.AsyncClient(timeout=30) as raw:
            try:
                summary = (await raw.get(f"{IAM_API}/summary")).json()
            except Exception:
                print(f"The IAM API is not running on {IAM_API}.")
                print("Start it:  docker compose up -d      # in indicus-ai-mcp-tools")
                return

        print("0. The environment under review")
        print(f"   {summary['total_records']:,} records — {summary['identities']} identities, "
              f"{summary['accounts']} accounts, {summary['entitlements']} entitlements")
        for name, count in summary["findings"].items():
            print(f"   {count:>4}  {name.replace('_', ' ')}")

        # --- 1. connect the customer's systems ------------------------------
        print("\n1. Importing the IAM systems as tools (their API, their credentials)")
        preview = await c.post(
            "/custom-tools/preview",
            json={"spec_url": f"{IAM_API}/openapi.json", "base_url": IAM_API},
        )
        if preview.status_code != 200:
            print("   preview failed:", preview.text[:300])
            return

        operations = [
            op for op in preview.json()["operations"]
            if op.get("source_operation_id") in WANTED or op.get("name") in WANTED
        ]
        for op in operations:
            # Pinned: a tool that can be pointed at any host is an exfiltration
            # path, not an integration.
            op["allowed_hosts"] = ["127.0.0.1"]

        # Delete any earlier copies first.
        #
        # A tool is a snapshot of the spec taken at import time, and import
        # skips names that already exist. So a tool imported before an endpoint
        # gained a parameter keeps the old schema forever — and the model cannot
        # pass an argument it cannot see. The failure is silent and looks like
        # the model ignoring an instruction, which is where the time goes.
        current = (await c.get("/custom-tools")).json()
        current_rows = current if isinstance(current, list) else current.get("tools", [])
        stale = [t for t in current_rows if t["name"] in WANTED]
        for tool in stale:
            await c.delete(f"/custom-tools/{tool['id']}")
        if stale:
            print(f"   removed {len(stale)} previously imported copies")

        imported = await c.post("/custom-tools/import", json={"tools": operations})
        if imported.status_code != 201:
            print("   import failed:", imported.text[:300])
            return
        result = imported.json()
        print(f"   {imported.status_code}  {len(result.get('created', []))} imported, "
              f"{len(result.get('skipped', []))} already present — pinned to 127.0.0.1")

        # `created` is a list of names, so ids come from the tool list. Reading
        # them back also covers a re-run, where everything was skipped as a
        # duplicate and nothing would otherwise be bound to the agents.
        # --- 1b. the platform's own campaign engine ------------------------
        #
        # Separate from the identity source: these read decisions that real
        # reviewers recorded, not the generated history the demo data carries.
        # Without them the analysis phase reasons about a certification nobody
        # performed, which is a convincing demo of nothing.
        print("\n1b. Wiring the campaign engine as tools (real decisions)")
        current = (await c.get("/custom-tools")).json()
        current_rows = current if isinstance(current, list) else current.get("tools", [])
        for tool in [t for t in current_rows
                     if t["name"] in CAMPAIGN_TOOL_NAMES]:
            await c.delete(f"/custom-tools/{tool['id']}")

        key_response = await c.post(
            "/api-keys",
            json={
                "name": "IAM pipeline — campaign access",
                # Admin because verify-remediation writes. Scoped to this one
                # workspace, and worth narrowing to an automation role before a
                # customer deployment rather than left as a standing grant.
                "role": "admin",
                "workspace_id": workspace,
            },
        )
        if key_response.status_code >= 300:
            print("   could not mint a service key:", key_response.text[:200])
            return
        key_body = key_response.json()
        service_key = key_body.get("key") or key_body.get("api_key") or key_body.get("token")
        print(f"   service key {key_body.get('prefix')}… (admin, this workspace only)")

        campaign_payload = [
            {**tool, "allowed_hosts": ["127.0.0.1"], "auth_scheme": "bearer",
             "secret": service_key, "timeout_seconds": 60}
            for tool in CAMPAIGN_TOOLS
        ]
        wired = await c.post("/custom-tools/import", json={"tools": campaign_payload})
        if wired.status_code != 201:
            print("   campaign tool import failed:", wired.text[:300])
            return
        print(f"   {len(wired.json().get('created', []))} campaign tools registered")

        existing = (await c.get("/custom-tools")).json()
        rows = existing if isinstance(existing, list) else existing.get("tools", [])
        bindable = WANTED | CAMPAIGN_TOOL_NAMES
        tools = {t["name"]: t["id"] for t in rows if t["name"] in bindable}
        print(f"   {len(tools)} of {len(bindable)} tools available to bind")

        # --- 2. skills -------------------------------------------------------
        #
        # One bundle per skill, not one bundle holding five.
        #
        # A version number is only useful if it says what changed. Across the
        # combined bundle's first fourteen versions, five publishes altered any
        # content at all and every one of them touched exactly one skill —
        # never two together. Meanwhile the readiness skill, whose text has
        # never once been edited, was dragged through all fourteen. Splitting
        # gives each skill a version that moves when, and only when, that skill
        # moves: a rollback affects one agent, a bad publish breaks one phase,
        # and the number in the UI answers "what changed?" on its own.
        #
        # The cost is that a publish is no longer atomic across all five. They
        # have never needed to change together, so that risk stays theoretical.
        print("\n2. Publishing the skills — one bundle per phase")
        skill_bodies = {
            path.stem: path.read_text() for path in sorted(SKILL_DIR.glob("*.md"))
        }
        if not skill_bodies:
            print(f"   no skills found in {SKILL_DIR}")
            return

        catalogue = {p["name"]: p for p in (await c.get("/plugins")).json()}
        plugin_ids: dict[str, str] = {}
        # The exact version each agent will be pinned to. A caret range would
        # let a client's agents adopt the next skill we publish without anyone
        # deciding to — the opposite of shipping a tested pipeline.
        skill_pins: dict[str, str] = {}

        for skill_name, body in skill_bodies.items():
            existing = catalogue.get(skill_name)
            version = "1.0.0"
            if existing and existing.get("latest_version"):
                # Published versions are immutable, correctly — a skill an
                # agent is bound to must not change underneath it. Re-seeding
                # publishes the next version and the agents' `^1.0.0` picks
                # it up.
                major, minor, _patch = existing["latest_version"].split(".")
                version = f"{major}.{int(minor) + 1}.0"

            # Unchanged content is not a new version. Fourteen versions for
            # five real edits is noise that makes the number meaningless, and
            # it is the reason three of these skills had a release history at
            # all.
            if existing and version != "1.0.0":
                detail = await c.get(f"/plugins/{existing['id']}/detail")
                if detail.status_code == 200:
                    latest = next(
                        (
                            v
                            for v in detail.json().get("versions", [])
                            if v["version"] == existing["latest_version"]
                        ),
                        None,
                    )
                    shipped = {
                        sk["name"]: sk.get("body")
                        for sk in (latest or {}).get("skills", [])
                    }
                    if (shipped.get(skill_name) or "").strip() == _body_only(body):
                        plugin_ids[skill_name] = existing["id"]
                        skill_pins[skill_name] = existing["latest_version"]
                        print(f"   {skill_name:<30} unchanged at "
                              f"{existing['latest_version']}")
                        continue

            published = await c.post(
                "/plugins/publish",
                json={
                    "manifest": {
                        "name": skill_name,
                        "version": version,
                        "description": _summary(body) or skill_name,
                        "permissions": {"tools": sorted(WANTED | CAMPAIGN_TOOL_NAMES)},
                    },
                    "skills": {skill_name: body},
                    "changelog": f"{skill_name} {version}",
                    # Published, not draft. A draft cannot be bound to an
                    # agent — nothing may depend on an unregistered skill,
                    # which is the right default and the wrong one for a seed
                    # that builds the agents immediately afterwards.
                    "draft": False,
                },
            )
            if published.status_code != 201:
                print(f"   publish failed for {skill_name}:",
                      published.text[:200])
                return
            plugin_ids[skill_name] = published.json()["plugin_id"]
            skill_pins[skill_name] = version
            print(f"   {skill_name:<30} published {version}")

        # --- 3. agents -------------------------------------------------------
        models = (await c.get(f"/workspaces/{workspace}/models")).json()["models"]
        by_id = {m["id"]: m for m in models}
        available = [m["id"] for m in models if m["available"]]
        if not available:
            print("\n   No usable model in this workspace — install a provider key first.")
            return

        def pick(preferred: str) -> str:
            spec = by_id.get(preferred)
            return preferred if spec and spec["available"] else available[0]

        # The cost argument from the proposal, kept intact: Haiku for
        # orchestration and classification, Sonnet only where judgment is
        # needed. Sonnet on all five would multiply the per-cycle cost for no
        # better answer on the mechanical steps.
        fast = pick("claude-haiku-4-5")
        deep = pick("claude-sonnet-5")

        print(f"\n3. Building the five agents  (fast={fast}  deep={deep})")
        # (key, name, model, type, tools, prompt, skill)
        agent_specs = [
            ("readiness", "IAM Readiness", fast, "simple",
             ["getCertificationScope", "getEntitlementQuality",
              "getUncorrelatedAccounts", "getInactiveUsersWithAccess"],
             "You establish whether a certification campaign can safely launch. "
             "Be decisive and brief. Distinguish what blocks a launch from what is "
             "merely untidy.",
             "access-review-readiness"),
            ("validation", "SME Pre-Validation", fast, "simple",
             ["getSmeValidationStatus", "getIdentity", "sendTeamsMessage",
              "sendOutlookEmail", "getSentMessages"],
             "You track SME pre-validation. Report who is outstanding. Never "
             "invent a response that was not given.\n\n"
             "You may chase. Send a Teams message only to an SME who has had "
             "two follow-ups and still not responded — one message each, "
             "naming their application and what you need. Do not chase anyone "
             "on their first or second follow-up; the automation is still "
             "handling those and a third reminder from a different sender "
             "reads as noise.\n\n"
             "Escalate by email, not by a second chat. Where an application's "
             "expert has left, or where a chase has already been sent and the "
             "review still cannot proceed, use sendOutlookEmail with "
             "cc_manager true — mail is the medium that leaves a record their "
             "manager can act on, and copying the manager keeps the original "
             "recipient visible rather than quietly reassigning the work.\n\n"
             "If sendTeamsMessage refuses because the person has left, do not "
             "retry and do not message anyone else in their place. Report them "
             "for manager escalation: an unowned application is a different "
             "problem from a slow reviewer, and quietly redirecting the chase "
             "hides it.",
             "sme-prevalidation"),
            ("certification", "Certification Monitor", fast, "simple",
             ["getCertificationProgress", "getIdentity"],
             "You report campaign progress. This step is mechanical — report the "
             "numbers and stop.",
             "certification-monitor"),
            ("postcert", "Post-Certification Analyst", deep, "deep",
             # Reads the campaign engine, not the generated history. The
             # decisions it analyses were recorded by named reviewers with
             # justifications, and verifyCampaignRemediation re-reads the
             # estate rather than trusting a ticket.
             ["getCampaignProgress", "getCampaignDecisions",
              "getCampaignRemediation", "verifyCampaignRemediation",
              "getIdentity"],
             "You establish what actually happened after a certification "
             "closed. You are given a campaign id; every figure comes from "
             "that campaign, not from memory.\n\n"
             "Access a reviewer ordered removed that is still live is the most "
             "serious thing you can find. verifyCampaignRemediation re-reads "
             "the estate and tells you exactly that — run it, and lead with "
             "what it returns. Write for an auditor.\n\n"
             "Produce a summary, never an inventory. Report counts, then itemise "
             "only the exceptions — reinstatements, missing tickets, tickets "
             "still open. Never list every revocation individually; there are "
             "over a hundred and listing them buries the findings.",
             "post-certification-analysis"),
            # Not part of the pipeline. The pipeline answers "has the
            # quarterly review been done, and can we prove it"; this answers
            # "what is the state of X right now", which is the question people
            # actually ask between cycles.
            ("copilot", "IAM Copilot", deep, "simple",
             sorted(WANTED),
             "You answer questions about the identity estate. Someone is "
             "waiting, so reply at the length the question deserves and stop. "
             "Every figure comes from a tool call — never from memory, and "
             "never from earlier in this conversation, because the estate "
             "changes between questions.\n\n"
             "You can send Teams messages and email, but only when asked. A "
             "question about who has not responded is not an instruction to "
             "chase them. Before sending, name the recipients in your reply so "
             "the approval prompt is a confirmation of something already "
             "stated rather than a surprise.\n\n"
             "You do not run certification campaigns. Asked for a full access "
             "review, point at the IAM Access Review pipeline instead of "
             "performing it turn by turn.",
             "iam-copilot",
             {
                 # A conversation, not a report: short answers, and enough
                 # steps to follow a question across two or three lookups
                 # without the planning overhead a deep agent pays per turn.
                 "max_tokens": 4096,
                 "max_steps": 16,
                 "effort": "medium",
                 # Sending is the one irreversible thing it can do, and a
                 # person is already present to approve — which is exactly the
                 # case the approval gate suits and the unattended pipeline
                 # does not.
                 "approval_required_tools": ["sendTeamsMessage",
                                             "sendOutlookEmail"],
             }),
            ("sar", "Service Account Review", deep, "deep",
             # getServiceAccount first: a review names the accounts it needs
             # answered, and resolving one by name is what the other three
             # cannot do. Without it the agent pages an inventory it cannot
             # reach the end of, then fails its own acceptance criteria.
             ["getServiceAccount", "getServiceAccountInventory",
              "getVaultOnboardingGaps", "getServiceAccountDelta",
              "getIdentity"],
             "You review non-human accounts. Rank by real exposure: privileged, "
             "interactive and ownerless is the worst case. Never guess an owner."
             "\n\n"
             "Scope: the accounts named in the findings you were given, plus "
             "what the population-level tools return on their own — vault "
             "gaps, the new-since-last-cycle delta, and the counts by type. "
             "Resolve the named accounts with getServiceAccount, passing them "
             "together in batches of up to 50, not one per call.\n\n"
             "Do not attempt to classify all 474 non-human accounts "
             "individually. The inventory is capped and cannot be enumerated "
             "to the end, so a plan that requires per-account classification "
             "of the whole population cannot be satisfied and the run will "
             "exhaust its retries. Report population figures as counts from "
             "the aggregate tools, and itemise only the accounts that carry a "
             "finding.",
             "service-account-review"),
        ]

        agents: dict[str, str] = {}
        for spec in agent_specs:
            key, name, model_id, agent_type, tool_names, prompt, skill = spec[:7]
            # Seventh element onwards is optional per-agent config. Most agents
            # take the preset for their type; the copilot does not, and a
            # special case for one agent would be worse than a slot for any.
            overrides = spec[7] if len(spec) > 7 else {}
            bound = [tools[t] for t in tool_names if t in tools]
            body = {
                    "name": name,
                    "description": f"{name} for the access certification cycle.",
                    "config": {
                        "agent_type": agent_type,
                        "model": model_id,
                        "system_prompt": prompt,
                        # Extended thinking spends this budget too, so a
                        # deep agent asked to itemise ~90 exceptions can burn
                        # the whole allowance reasoning and emit no text at
                        # all — which the critic reads as "no output" and
                        # retries, three times, at full cost. The three simple
                        # agents answer in a paragraph and do not need it.
                        "max_tokens": 32000 if agent_type == "deep" else 8192,
                        # Adaptive thinking scales with effort, and this work
                        # is look-up-and-tabulate rather than open reasoning:
                        # at "high" the service-account review spent 550 of its
                        # 770 seconds thinking, against 5 seconds of actual
                        # tool time. Post-certification keeps "high" — it is
                        # cross-referencing three sources and earns it.
                        "effort": "medium" if key == "sar" else "high",
                        "builtin_tools": ["read"],
                        "custom_tool_ids": bound,
                        # One skill, named. An empty list binds the whole
                        # bundle, so every agent was carrying all five — the
                        # readiness agent holding the service-account skill and
                        # so on. Every skill description sits in context on
                        # every request, so that is four descriptions of work
                        # the agent will never do, on every call, plus four
                        # more candidates for the router to rule out.
                        **overrides,
                        "skills": [
                            {"plugin_id": plugin_ids[skill],
                             # Exact, not a range: this agent runs the skill
                             # that was tested with it, until someone changes
                             # this line on purpose.
                             "version_spec": skill_pins[skill],
                             "skill_names": [skill]}
                        ],
                    },
            }

            if name in existing_agents:
                agent_id = existing_agents[name]
                r = await c.post(f"/agents/{agent_id}/versions", json=body["config"])
                ok = r.status_code in (200, 201)
            else:
                r = await c.post("/agents", json=body)
                ok = r.status_code == 201
                if ok:
                    agent_id = r.json()["id"]

            if not ok:
                print(f"   {r.status_code} {name}: {r.text[:200]}")
                continue
            agents[key] = agent_id
            await c.post(
                f"/agents/{agents[key]}/deploy",
                json={"environment": "production", "triggers": ["chat", "api"]},
            )
            print(f"   {name:28} {model_id:18} {len(bound)} tools")

        if len(agents) < 5:
            print("\n   Not all agents were created; stopping before the pipeline.")
            return

        # --- 4. the pipeline --------------------------------------------------
        print("\n4. Wiring the pipeline — the five phases in order")
        nodes = [
            {"id": "start", "type": "start", "name": "Cycle start",
             "config": {"position": {"x": 40, "y": 220}}},
            {"id": "readiness", "type": "agent", "name": "1 · Readiness",
             "config": {"agent_id": agents["readiness"],
                        "input": (
                            "Assess readiness for campaign {{ input }}. "
                            "Pass campaign={{ input }} to getCertificationScope."
                        ),
                        "position": {"x": 250, "y": 220}}},
            {"id": "gate", "type": "branch", "name": "Safe to launch?",
             "config": {"position": {"x": 480, "y": 220}}},
            {"id": "blocked", "type": "transform", "name": "Hold — fix data first",
             "config": {
                 "template": (
                     "CYCLE HELD. Readiness did not pass, so the campaign was not "
                     "launched.\n\n{{ nodes.readiness.output }}"
                 ),
                 "position": {"x": 700, "y": 60}}},
            {"id": "validation", "type": "agent", "name": "2 · Pre-validation",
             "config": {"agent_id": agents["validation"],
                        "input": ("Readiness reported:\n\n{{ nodes.readiness.output }}\n\n"
                                  "Report SME pre-validation status."),
                        "position": {"x": 700, "y": 300}}},
            {"id": "certification", "type": "agent", "name": "3 · Certification",
             "config": {"agent_id": agents["certification"],
                        "input": ("Pre-validation reported:\n\n{{ nodes.validation.output }}\n\n"
                                  "Report progress for campaign {{ input }}."),
                        "position": {"x": 940, "y": 300}}},
            {"id": "postcert", "type": "agent", "name": "4 · Post-certification",
             "config": {"agent_id": agents["postcert"],
                        "input": ("The campaign has closed:\n\n{{ nodes.certification.output }}\n\n"
                                  "Analyse {{ input }}: what was revoked, what was "
                                  "actually removed, and what came back."),
                        "position": {"x": 1180, "y": 300}}},
            {"id": "sar", "type": "agent", "name": "5 · Service accounts",
             "config": {"agent_id": agents["sar"],
                        "input": ("Post-certification found:\n\n{{ nodes.postcert.output }}\n\n"
                                  "Now review the service account population."),
                        "position": {"x": 1420, "y": 300}}},
            {"id": "end", "type": "end", "name": "Cycle complete",
             "config": {"position": {"x": 1660, "y": 220}}},
        ]

        # Readiness gates the rest. A campaign staged over bad data is the
        # failure mode the readiness phase exists to prevent, so the pipeline
        # must be able to stop rather than press on.
        blocked = {"in": ["READINESS: blocked", {"var": "nodes.readiness.output"}]}
        edges = [
            {"source": "start", "target": "readiness"},
            {"source": "readiness", "target": "gate"},
            {"source": "gate", "target": "blocked", "when": {"rule": blocked}},
            {"source": "gate", "target": "validation", "when": {"rule": {"!": blocked}}},
            {"source": "validation", "target": "certification"},
            {"source": "certification", "target": "postcert"},
            {"source": "postcert", "target": "sar"},
            {"source": "sar", "target": "end"},
            {"source": "blocked", "target": "end"},
        ]

        graph = {"nodes": nodes, "edges": edges, "max_cost_usd": 5, "max_node_runs": 20}
        check = await c.post("/workflows/validate", json=graph)
        print(f"   validate -> {check.json()}")

        if PIPELINE_NAME in existing_pipelines:
            workflow_id = existing_pipelines[PIPELINE_NAME]
            ver = await c.post(f"/workflows/{workflow_id}/versions", json=graph)
            print(f"   {ver.status_code}  {PIPELINE_NAME}  (new version)")
            print(f"\nSeeded into '{WORKSPACE_NAME}'. Open http://localhost:5173")
            print("  Switch workspace in the sidebar picker before looking for these.")
            print(f"  Pipeline : /workflows/{workflow_id}")
            for _name, _pid in sorted(plugin_ids.items()):
                print(f"  Skill    : /skills/{_pid}  ({_name})")
            print("\n  Run it with input:  CERT-2026-Q2")
            return

        wf = await c.post(
            "/workflows",
            json={
                "name": PIPELINE_NAME,
                "description": (
                    "Readiness, pre-validation, certification, post-certification "
                    "and service account review — one cycle."
                ),
                "graph": graph,
            },
        )
        if wf.status_code != 201:
            print("   pipeline failed:", wf.text[:300])
            return
        workflow_id = wf.json()["id"]
        print(f"   {wf.status_code}  {PIPELINE_NAME}  ({wf.json()['node_count']} nodes)")

        print(f"\nSeeded into '{WORKSPACE_NAME}'. Open http://localhost:5173")
        print("  Switch workspace in the sidebar picker before looking for these.")
        print(f"  Pipeline : /workflows/{workflow_id}")
        for _name, _pid in sorted(plugin_ids.items()):
            print(f"  Skill    : /skills/{_pid}  ({_name})")
        print("\n  Run it with input:  CERT-2026-Q2")


if __name__ == "__main__":
    asyncio.run(main())
