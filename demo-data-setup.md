# Demo data and tool onboarding

What tools IndicusAI can call, what this repository provides, and how to wire
them up by hand. Written to be followed start to finish.

If you only want the demos working, `DEPLOYMENT.md` is shorter — the seeds do
all of this for you. Read this when you want to add your own tools, understand
what the seeds did, or build the agents and pipelines by hand (§7).

---

## 1. The three kinds of tool

An agent's tool list is assembled from three sources. They differ in who hosts
the code, who can add them, and what happens when they break.

| | Built-in | Custom HTTP | MCP |
|---|---|---|---|
| **What** | file and shell primitives | your REST endpoints | a tool server |
| **Runs** | in the run sandbox | your service | your service |
| **Added** | already there — tick a box | import an OpenAPI spec | add a connector URL |
| **Scope** | per agent | per workspace | per workspace |
| **Granularity** | individual | one tool per operation | every tool on the server |
| **Where in the UI** | agent editor | Tools | Connections |

### Built-in tools

Six, and they are the same on every deployment:

| | |
|---|---|
| `read` | read a UTF-8 file from the run workspace |
| `write` | write a file, creating parent directories |
| `edit` | replace an exact string in a file |
| `glob` | list files matching a pattern, e.g. `**/*.csv` |
| `grep` | search file contents by regular expression |
| `bash` | run a shell command in the run workspace |

They operate on the **run workspace** — a scratch directory belonging to one
run, not your machine and not the container's filesystem at large. An agent
that reads a CSV, filters it and writes a report uses these and nothing else.

`bash` is the one to think about before ticking. Where it executes is the
`EXECUTION_BACKEND` setting: `inprocess` (the platform's own process — fine
locally, refused in production), `docker` (a container per run), or
`kubernetes` (a pod per run). The demo box runs `docker`.

A knowledge base attached to an agent adds a **search tool** of its own, named
after the base. That is a fourth source, and it appears automatically once a
base is bound — nothing to onboard.

### Custom HTTP tools

Your own REST endpoints, imported from an OpenAPI specification. One tool per
operation, so you choose exactly which operations an agent may call. Each is
pinned to an `allowed_hosts` list, and a call to anything else is refused
before it is made.

### MCP tools

One connector carrying every tool its server exposes. You add a URL once and
the tool list is discovered at connect time — a tool added to the server later
appears without touching IndicusAI.

---

## 2. What this repository provides

**35 operations, over both surfaces.** The same functions, the same fixtures,
reachable either as custom HTTP tools or through MCP:

| Service | Operations | REST | MCP names |
|---|---|---|---|
| Security operations | 5 | `/soc` | `soc_getAlert`, `soc_listAlerts`, `soc_getIndicatorReputation`, `soc_getAsset`, `soc_getIdentity` |
| Utility revenue protection | 8 | `/utility` | `utility_listVisits`, `utility_getVisit`, `utility_transcribeVisitRecording`, `utility_getAccount`, `utility_getBillingHistory`, `utility_getMeterReadings`, `utility_getFieldInspection`, `utility_getGridEvents` |
| Dental revenue cycle | 3 | `/payer` | `payer_getClaim`, `payer_listClaims`, `payer_getEligibility` |
| IAM certification | 19 | `/iam` | `iam_getCertificationScope`, `iam_getServiceAccount`, `iam_sendTeamsMessage`, … |

That duplication is deliberate. A demo comparing built-in custom tools against
MCP proves nothing if the two run on different data, because any difference in
the result could be blamed on the fixtures. Here it cannot.

Check what is live at any time:

```bash
curl -s http://localhost:8304/health | python3 -m json.tool
```

---

## 3. Onboarding, three ways

### Path A — the seeds (what the demos use)

The fastest route, and the one `DEPLOYMENT.md` documents. Registers the
connectors, publishes the skills, and builds agents and a pipeline wired to
them:

```bash
docker compose exec mcp-tools python seeds/soc.py
docker compose exec mcp-tools python seeds/utility.py
```

They register **custom HTTP tools**, not MCP. Skip to §4 if that is all you
need.

### Path B — custom HTTP tools by hand

Do this to onboard your own API, or to see what the seeds automate.

1. **Get the spec URL.** Every service here publishes one:

   | Service | Spec |
   |---|---|
   | SOC | `http://mcp-tools:8304/soc/openapi.json` |
   | Utility | `http://mcp-tools:8304/utility/openapi.json` |
   | Payer | `http://mcp-tools:8304/payer/openapi.json` |
   | IAM | `http://mcp-tools:8304/iam/openapi.json` |

   Use the `mcp-tools` hostname, not `localhost` — the platform fetches this
   from inside its own container, where `localhost` is the platform.

2. **Tools → Import from OpenAPI.** Paste the spec URL.

3. **Set the base URL** to `http://mcp-tools:8304`. These specs declare a
   *relative* server (`{"servers": [{"url": "/soc"}]}`), so there is no host in
   the document for the platform to infer.

4. **Pick the operations.** Nothing is pre-selected on purpose: a forty
   operation spec should not become forty tools because someone clicked
   through. Choose what the agent actually needs.

5. **Import.** Each operation becomes one tool, named after its `operationId` —
   `getAlert`, `listAlerts`. Note these are *unprefixed*, unlike the MCP names.

### Path C — the MCP connector

One connector, all 35 tools.

1. **Connections → add an MCP server.**
2. Transport **`http`**, URL **`http://mcp-tools:8304/mcp`**.
3. **Probe it.** A healthy probe lists every tool. Two failures matter:
   - **`Not Found`** — the URL is missing `/mcp`, or has it twice.
   - **could not be reached** — the container is not on the platform's compose
     network, or is being reached by a hostname the server does not answer to.
     MCP's DNS rebinding protection admits only the names in `ALLOWED_HOSTS`.
4. Tools appear as `{service}_{operationId}`. The prefix is not decoration: MCP
   names are flat across a server while `operationId`s are unique only within a
   service, and SOC and IAM both define `getIdentity`.

---

## 4. Wiring tools to an agent

Registering a tool does not give it to anyone. Open the agent, and:

- **Built-in tools** — tick the ones it needs. Fewer is better: every tool is
  described to the model on every step, and a tool it will never call is
  tokens spent on every request.
- **Custom tools** — select from what the workspace has imported.
- **MCP tools** — available once the connector is added; the agent may be
  restricted to a subset.

Two failure modes worth knowing, both seen on this platform:

**A skill that names a tool the agent does not hold.** The skill instructs the
model to call `getGridEvents`, the agent was given two tools, and the run fails
at the step that needed the third. The skill's frontmatter under
`allowed-tools` is what to check.

**Too many tools.** A verdict step given every tool in the workspace has more
ways to go wrong and costs more per step. Give a step what it needs.

---

## 5. Verifying

**The service answers, from where the platform sits:**

```bash
docker compose -f docker-compose.prod.yml exec api python -c \
  "import urllib.request as u; print(u.urlopen('http://mcp-tools:8304/health').status)"
```

That is the check that matters — `curl localhost:8304` from the box proves the
container is up, not that the platform can reach it.

**The tools are registered:** Tools lists them; Connections shows the MCP
server with a tool count after a probe.

**End to end:** open the agent, chat, ask for something that needs a tool
("Triage ALT-2291"). The run detail shows each tool call and its result — the
only view that proves the whole chain, since a tool can be registered, granted
and still fail on the call.

---

## 6. Which to use

**Custom HTTP tools** when you want per-operation control, an audit trail of
exactly what was imported, and a host pin. Adding an operation means importing
again.

**MCP** when the server is the unit — you want everything it offers, and you
want tools added there to appear without an import. One URL, and the tool list
follows the server.

For a client demo, showing both against the same fixtures is the point of this
repository being built the way it is.

---

## 7. Building the demos by hand, in the UI

The seeds create these in seconds. Build one by hand once and the pipeline
editor stops being a mystery — and if you are demoing to someone technical,
building a node live is a better answer than showing a finished graph.

Everything below assumes §3 is done: tools registered, and a provider key on
the workspace.

### 7a. The agents

**Agents → New agent**, once per row. Every one of these is **agent type
`simple`** — a single model call with tools, no planner and no critic. The
demos use it deliberately: for a step whose job is "call two tools and write a
paragraph", a plan-and-critique loop roughly tripled the cost and changed
nothing about the answer.

**Security Operations** — model `claude-sonnet-5` for all four:

| Agent | Skill | Custom tools |
|---|---|---|
| Alert Triage | `alert-triage` | `getAlert`, `listAlerts` |
| IOC Enrichment | `ioc-enrichment` | `getAlert`, `getIndicatorReputation`, `getAsset`, `getIdentity` |
| Incident Response | `incident-response` | `getAlert`, `getAsset`, `getIdentity` |
| Detection Tuning | `detection-tuning` | `getAlert`, `getIdentity` |

**Revenue Protection**:

| Agent | Model | Skill | Custom tools |
|---|---|---|---|
| Recording Intake | `claude-haiku-4-5` | `visit-recording-intake` | `listVisits`, `getVisit`, `transcribeVisitRecording` |
| Records Correlation | `claude-sonnet-5` | `consumption-anomaly-correlation` | `getAccount`, `getBillingHistory`, `getMeterReadings`, `getFieldInspection`, `getGridEvents` |
| Intent Signals | `claude-haiku-4-5` | `customer-intent-signals` | *(none)* |
| Visit Verdict | `claude-sonnet-5` | `field-visit-verdict` | `getFieldInspection`, `getMeterReadings`, `getAccount`, `getBillingHistory`, `getGridEvents` |

Two of those rows are the result of getting it wrong here first.

**Intent Signals holds no tools on purpose.** It reads the transcript the
previous node produced and names behavioural signals in it. Giving it lookups
invites it to fetch records and start arguing about the meter, which is a
different node's job.

**Visit Verdict holds five.** It was built with two, and the verdict step
failed twice — the skill's criteria require checking grid events and the
account, and an agent cannot call a tool it was not given. The failure surfaced
as "the agent run did not complete", which says nothing about a missing tool.
**If a step fails, check its tool list against what its skill actually
instructs it to call.**

Paste each agent's system prompt from `seeds/soc.py` or `seeds/utility.py` —
the `AGENTS` list at the top holds the exact text.

### 7b. The SOC pipeline — branching

**Workflows → New**, name it **`SOC Alert Response`**. Seven nodes:

```
start ──▶ 1·Triage ──▶ 2·Enrich ──▶ ◆ Real or benign?
                                      │
                              not benign ──▶ 3a·Respond ──┐
                                      │                    ├──▶ end
                                  benign ──▶ 3b·Tune ──────┘
```

| Node | Type | Agent |
|---|---|---|
| Alert | start | — |
| 1 · Triage | agent | Alert Triage |
| 2 · Enrich | agent | IOC Enrichment |
| Real or benign? | **branch** | — |
| 3a · Respond | agent | Incident Response |
| 3b · Tune the rule | agent | Detection Tuning |
| Closed | end | — |

**Node inputs.** Each agent node takes an input template; `{{ input }}` is what
was submitted to the run, and `{{ nodes.<id>.output }}` is an earlier node's
result.

- **1 · Triage** —
  `{{ input }}` followed by: *If no alert was named above, call listAlerts and
  work the single most urgent one, saying which you picked and why. Exactly one
  alert.*
- **2 · Enrich** — *A tier-1 analyst triaged this alert:* `{{ nodes.triage.output }}`
  *Enrich every indicator and state the verdict.*
- **3a / 3b** — both read `{{ nodes.enrich.output }}`, one told it was a real
  incident, the other a false positive.

**The branch conditions**, which are the interesting part:

| Edge | Condition |
|---|---|
| → 3a · Respond | `{{ nodes.enrich.output }}` **not_contains** `VERDICT: benign` |
| → 3b · Tune | `{{ nodes.enrich.output }}` **contains** `VERDICT: benign` |

Two decisions worth copying. It branches on **enrichment**, not on a later
node: the step that read the evidence is the one entitled to say it was benign.
And the default direction is *respond* — anything not explicitly benign is
treated as real, so a misread costs a wasted response rather than a missed
intrusion.

Set **max cost $4** and **max node runs 12** on the pipeline.

**Run it with `ALT-2291`** (a real intrusion — takes 3a) or **`ALT-2288`** (an
SCCM patch query — takes 3b). Both fire the same detection rule, which is the
whole point: the rule name cannot separate them and the enrichment can.

### 7c. The Revenue Protection pipeline — parallel

**Workflows → New**, name it **`Field Visit Review`**. Six nodes:

```
start ──▶ 1·Transcribe ──┬──▶ 2a·Records ──┬──▶ 3·Verdict ──▶ end
                         └──▶ 2b·Intent ───┘
```

| Node | Type | Agent |
|---|---|---|
| Visit reference | start | — |
| 1 · Transcribe the visit | agent | Recording Intake |
| 2a · Records | agent | Records Correlation |
| 2b · Intent signals | agent | Intent Signals |
| 3 · Verdict | agent | Visit Verdict |
| Reviewed | end | — |

Six edges. **Two leave `intake`** — to `records` and to `intent` — and **two
arrive at `verdict`**. That fan-out and fan-in is the shape: the two middle
nodes run in parallel and neither sees the other's output, so the intent read
cannot be coloured by the meter evidence or the other way round. The verdict is
the first step to see both.

`3 · Verdict` reads `{{ nodes.records.output }}` **and**
`{{ nodes.intent.output }}` in its input template.

**Run it with `VISIT-4471`** or **`VISIT-4472`** — one customer at fault, one
not. This pipeline needs the visit recordings present; see `DEPLOYMENT.md`.

### 7d. If a run fails

- **"The agent run did not complete"** — usually a tool the step needed and was
  not given. Compare the agent's tool list to what its skill instructs.
- **A branch always going one way** — the condition is a literal string match.
  If the agent stopped emitting `VERDICT: benign` exactly, every alert takes
  the default edge.
- **Cost ceiling hit** — `max_cost_usd` on the pipeline, and each agent has its
  own ceiling. The run detail shows the spend per node.

---

## 8. What is not covered here

- **Adding a tool to this repository** — `DEPLOYMENT.md`, "Adding a tool". One
  decorated function becomes both a REST endpoint and an MCP tool.
- **Authenticated MCP servers** — bearer, custom header, and OAuth are
  supported per connection; this one is unauthenticated because it is a demo on
  a private network.
- **stdio MCP servers** — supported, but restricted to platform-operated
  connections, because the transport spawns a process on the platform host.
