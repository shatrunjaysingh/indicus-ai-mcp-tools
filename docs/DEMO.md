# End-to-end demo

**Setup**

```bash
cd backend && ./.venv/bin/uvicorn app.main:app --port 8000 &
cd frontend && npx next dev -p 5173 &
cd backend && ./.venv/bin/python scripts/demo_seed.py
```

Sign in at `http://localhost:5173` as `demo@example.com` / `demo-password-1234`.

The seed creates a support-triage story: two connected systems, two skills, two
agents **on different vendors**, one pipeline, one catalog listing.

---

## 1. The promise — login screen (30s)

> "Run agents against your systems. Your data stays where it is."

The claim is on the door. Everything after this is evidence for it.

## 2. Overview — what is happening (1 min)

Land on **Overview**. Top banner is the data-residency verdict, computed from
two independent settings rather than asserted. Right now it reads **not
contained** — that is deliberate, we fix it in step 6.

Below: agents, pipelines, connections, spend. Recent activity underneath.

## 3. Connect — bring your own systems (1 min)

**Connect → Connections.** Two MCP servers, Jira and Zendesk, each with a key
stored encrypted — the UI shows `sk-…1234`, never the secret.

Points to make:
- The customer's credentials, reaching their systems
- Nothing is ingested; the data stays in Jira and Zendesk
- `stdio` transport is refused here — it would run a command on our host

Try adding one with transport `stdio` to show the refusal.

## 3b. Multi-provider, one engine (30s)

The seed puts **Ticket Triage on Gemini** and **Reply Drafter on Claude**, and
step 5's pipeline hands context from one to the other. Same cognitive engine,
same skills, same tools — the vendor is a per-agent setting.

A new workspace is onboarded with a model from every provider
(`claude-sonnet-5`, `claude-haiku-4-5`, `gemini-3-flash`, `gpt-5.1-mini`), so a
customer can compare vendors on their own traffic without filing a request. A
granted model with no key is refused at run time with an actionable message —
granting is policy, not spend.

## 4. Build — compose an agent (2 min)

**Build → Agents → Ticket Triage.** Three panels:

- **Left** — versions, change history, execution history, embed snippet
- **Centre** — the builder: agent type (simple/deep/indicus), model, system
  prompt, built-in tools, per-tool approval, MCP servers, skills with semver
  ranges, budgets
- **Right** — New chat, Playground, Assistant

Change the agent type from `simple` to `deep`. Note the badge: **unsaved
changes**, and the button reads **Save as v2**. Versions are immutable; editing
composes the next one.

Show the **Assistant** tab: describe a job in plain language, get a proposed
configuration constrained to what this workspace actually has — it cannot
propose a model the workspace is not granted.

## 5. Build — the pipeline (2 min)

**Build → Pipelines → Support triage.**

- Drag an agent from the left palette onto the canvas
- Drag between handles to connect
- Click an edge to open the **rule editor** — pick a source, an operator, a
  value; type a sample and it shows *edge taken* / *edge skipped* before running

The seeded pipeline: triage → if urgent, draft a reply; otherwise queue it.
The rule is JSONLogic, evaluated by the same JSON in the browser preview and on
the server, so the preview cannot drift from the executor.

**Assistant** tab: *"add a step that escalates to the on-call engineer"*. The
proposal is validated with the same parser the save path uses, then applied to
the canvas as unsaved edits.

**Playground** tab: run it. Each step shows **received** and **passed on** —
that is context flowing from one agent to the next.

## 6. The punchline — data residency (2 min)

**Settings → Data & residency.** Two settings, one verdict.

- **Retention** — `full` keeps everything; `metadata` writes no content here at
  all, only timings, token counts, and error types. Memory and resume keep
  working because their state goes to a bucket the customer controls.
- **Gateway** — `direct` sends prompts to the public API; `Bedrock` or `Vertex`
  keeps the call inside their own cloud.

Switch retention to **Metadata only** and gateway to **Amazon Bedrock**, region
`us-east-1`. Press Apply.

The banner turns jade: **"Your data stays inside your boundary."**

Then prove it rather than asserting it:

```bash
cd backend && ./.venv/bin/python -m pytest tests/ -q -k retention
```

`test_metadata_retention_persists_no_customer_content` runs an agent with a
marker string and sweeps all six content-bearing tables asserting its absence —
and asserts its *presence* under `full`, so the test cannot pass by failing to
look.

## 7. Distribution — the catalog (1 min)

**Discover → Agent catalog.** Each listing shows what it needs before you take
it: model, type, skills, MCP servers. Install reports what it could and could
not wire — MCP servers and knowledge bases cannot transfer, because they carry
per-workspace credentials, so they are reported rather than silently dropped.

---

## What to say when asked

**"Where does our data go?"** — Nowhere, if you configure it that way. Two
dials, both visible on one screen, and the platform computes the verdict rather
than us claiming it.

**"Can we self-host?"** — Yes; the same build runs in your VPC. Point the
gateway at Bedrock or Vertex in your account and no prompt leaves your cloud.

**"What do we give up with zero retention?"** — Trace replay and evaluations
over real traffic. You keep costs, timings, statuses, and error types. Memory
and resume keep working via your own storage.

## Known gaps — say these before you are asked

- Anthropic, OpenAI, and Gemini all dispatch correctly and each has been shown
  reaching its own vendor's API. Only Anthropic has ever completed a real call
  here — the other two were verified by their vendor rejecting a fake key.
- Bedrock and Vertex are wired and unit-tested, but no call has completed
  through either here; there are no cloud credentials on this machine.
- The deployment artifact is unverified. There is a Dockerfile and a compose
  file; neither has been run. No Helm chart.
- MCP OAuth is not built. Static tokens and API keys only, so Jira and Zendesk
  work with API tokens but not an OAuth app.
- The external memory document is read-modify-write on one object. Safe while a
  workspace's runs are serialised; it needs a lock before concurrent load.
