# Client demo — dental revenue cycle

The five-minute version, against the seeded dental RCM workspace. Read this one
while presenting; `DEMO.md` and `DEMO-WALKTHROUGH.md` teach you how to build the
pieces from scratch and are too slow for a client.

---

## Preflight

Three things must be up. Check them in this order — each takes seconds and all
three have failed in rehearsal at least once.

```bash
curl -s localhost:8000/health                      # API
curl -s 127.0.0.1:8300/claims/CLM-88421 | head -c 60   # payer API
curl -s -o /dev/null -w '%{http_code}\n' localhost:5173 # UI
```

The payer API runs under launchd and restarts itself, so it should already be
answering. If it is not: `demo/install-payer-agent.sh`.

Log in as `demo@example.com`. Confirm **Tasks** shows three agents.

---

## Run Denial Analyst

It is the only one that demonstrates the whole platform in a single interaction:
it picks two skills, calls two tools, reasons across both, and reaches a
conclusion nobody asked it for. The other two do a subset of the same thing.

### 1 · Tasks → Denial Analyst → Use me

Ask it to work the claim:

> Claim CLM-88421 came back denied. Work it and tell me exactly what to do next.

Let the trace stream so they watch it call `getClaim`, then decide on its own to
call `getEligibility`.

**The payoff:** prior authorisation was missing, *but* the patient was inside a
12-month waiting period — so winning the appeal still loses the claim. Point out
that no one told it to check eligibility.

It also counts the remaining appeal window from the EOB date in the record —
about 13 days — which is the kind of thing a biller misses on a Friday afternoon.

Roughly 38 seconds. Do not fill the silence; the streaming trace is the product.

### 2 · Activity

Show the run: **$0.066**, 38 seconds, full trace. Open it so they see every model
call, every tool call, and the token counts behind the number.

This is where cost stops being a worry and becomes a line item. If they ask what
that means at scale: 200 denials a month is about **$16**.

### 3 · Settings → Data & residency

The retention argument, with a real run sitting behind it. Switch the workspace
to `metadata` and show that the content is gone while the run, its cost and its
shape remain.

The sentence that lands: *nothing you just watched was retained, and the same
guarantee holds whether we run it or you run it in your own VPC.*

---

## The second claim, if they want one

`CLM-88503` is the strongest contrast — **$0.052**, and the answer is *don't
appeal, bill the patient*.

> Claim CLM-88503 was denied. Work it and tell me exactly what to do next.

It shows the agent declining to fight a correctly-applied frequency limit, which
is the opposite instinct to the first claim. Good if the audience is billing
staff who will assume an AI just appeals everything.

`CLM-88710` is a paid claim with a contractual adjustment, if someone wants to
see it handle a non-problem.

---

## Do not run all three agents

Keep **Eligibility Checker** and **AR Assistant** visible on the Tasks screen as
evidence of a library, and only open them if someone asks. Three near-identical
demos in a row costs you the room.

---

## If it breaks in front of them

| Symptom | Cause | Say |
|---|---|---|
| Tool call fails, agent escalates instead of answering | Payer API down | "That is the agent refusing to invent a denial reason — which is the behaviour you want." Then fix it after. |
| Run fails on authentication | Stale workspace credential overriding the platform key | Skip to the retention screen; do not debug live. |
| Answer is vague or malformed | Agent switched to the `local` model | Check the model on the agent page. Local is for smoke tests, not demos. |

The first one is worth rehearsing deliberately — an agent that says "I have zero
data on this claim, everything below would be fabricated" is a better trust
argument than any slide.

---

## Questions you will get

**"Where does our data go?"** Nowhere. The agent calls your system with your
credentials and uses the answer in the moment. Under `metadata` retention the
content is never written to our database — show them the screen.

**"What does it cost?"** About $0.07 for a claim like this one, $0.05 for a
simpler one. Every agent carries a per-run ceiling enforced during execution, so
a runaway stops rather than billing silently. See *What a run costs* in the
README.

**"Can it do our payer/PMS?"** That payer API is connected through an OpenAPI
import — the same path any REST system takes, about two minutes. MCP servers
connect the same way for systems that speak it.

**"Is it just calling ChatGPT?"** No. The planning, routing, verification and
memory are ours; the model is swappable, and the same agent runs on Anthropic,
OpenAI or Google, or inside your own cloud through Bedrock or Vertex.

---

## Known gaps — say these before you are asked

- Skill scripts run in-process; sandboxed execution is specified but not built,
  so the catalog is not open to third-party plugins.
- Runs are in-process asyncio tasks and do not survive an API restart.
- `owner` and `admin` currently hold the same permissions.
