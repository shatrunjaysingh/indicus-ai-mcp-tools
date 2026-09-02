# Testing the DISCOM agents

**Everything here is done in the browser.** Open an agent, type the input into
the chat box, read the answer. There is nothing to run on a command line and no
test code — you are the test.

Ten agents, seventeen inputs. Each one names what to type, what a correct answer
contains, and — more usefully — **the wrong answer it is designed to catch**.

Every case ships with a counter-case. The first of each pair is the obvious
result; the second is the one a plausible-sounding model gets wrong, and it is
the one worth watching. An agent that passes only the first half of a pair has
not been tested, it has been flattered.

Budget roughly **$1** for a full pass of all ten. Individually they are a few
cents each; the copilot and the verdict-style agents cost more because they
make more tool calls.

## Before you start

Four things, all in the UI:

1. **Workspace picker**, top left → **DISCOM Operations**
2. **Administration → Anthropic** — a key must be installed here. Keys are per
   workspace and are not inherited from Default.
3. **Tools** → you should see 24.
4. **Agents** → you should see ten.

If the tools are missing, the seed has not been run against this deployment.
If the agents are missing but the tools are there, the seed ran before a key
was installed — re-running it builds them.

Then open an agent and use its **Chat** tab. Type each input exactly as given:
several of these turn on the agent deciding for itself what to look up, so
adding hints changes what is being tested.

**Read the whole answer, not the first line.** Most of these agents can produce
the right verdict for the wrong reason, and the reasoning is where that shows.

---

## 1. Revenue & Collection AI

**Type:** `DL-4471002`

**The record:** 19 of 24 cycles paid on time, 2 late, the last 3 unpaid.
₹7,632 outstanding. One SMS reminder sent, not responded to.

**Pass:**
- `PAYMENT_LIKELIHOOD: high` or `medium` — not `low`
- `RECOVERY_ACTION: CALL` or `REMIND`
- The report gives the counts (19/2/3), not adjectives
- A "what points the other way" section that is not empty

**Fail — the trap:** recommending `FIELD_VISIT` or `DISCONNECT` because the
balance is four figures. This consumer has paid reliably for two years and
stopped three months ago; that is a change of circumstances, and the cheapest
rung that has not yet been tried is a call. An agent that escalates here would,
at scale, send field teams to the utility's most reliable payers.

**Also check:** it must not recommend disconnection at all — only one reminder
has been served, so the statutory notice bar is not met, and the skill requires
it to say so.

---

## 2. TD Recovery Prediction

### 2a. `CM-8890145`

**Type:** `CM-8890145`

**The record:** ₹110,393, disconnected 419 days, survey says *occupied — shop
trading*, supply appears live.

**Pass:** `RECOVERY_PRIORITY` **above 80**, `FIELD_VISIT`. The report separates
recoverable amount from probability of recovery and states both.

### 2b. `DL-2245108` — the counter-case

**Type:** `DL-2245108`

**The record:** ₹12,678, disconnected 90 days, survey says *locked — no
occupancy, post uncollected, family relocated in May*.

**Pass:** `RECOVERY_PRIORITY` **below 35**, and `WRITE_OFF_REVIEW` or
`NOTICE` — not a field visit.

**Fail — the trap:** scoring 2b anywhere near 2a, or scoring on the arrears
alone. The whole point is recoverable amount **×** probability: an empty
premises with an untraceable occupier is not recoverable at any balance.
Watch also for the two scores landing within ten points of each other — a
scorer that clusters produces an arbitrary ranking, which the skill explicitly
forbids.

---

## 3. Theft/Anomaly Detection

### 3a. `CM-5561093`

**Type:** `CM-5561093`

**The record:** consumption fell from ~8,300 to ~3,000 kWh. Three tamper
events (two cover-open, one magnetic field) with **no work orders**.
Communication intermittent. Peer median 7,900 against subject 3,035.

**Pass:**
- `ANOMALY_RISK` **above 70**, `INSPECT_URGENT` or `INSPECT_ROUTINE`
- Leads on the **tamper events**, not the peer comparison
- An "innocent explanations tested" section
- A section telling an inspector what to look for on site

### 3b. `IN-7734021` — the counter-case, and the most important test here

**Type:** `IN-7734021`

**The record:** consumption fell from ~89,000 to ~36,000 kWh — a 60% drop,
larger than 3a's. But `getConsumptionHistory` carries a recorded **load
surrender** dated 2025-08-30, reference LS/2025/1188, 250 kW → 100 kW.

**Pass:** `ANOMALY_RISK` **below 25**, `NO_ACTION` or `MONITOR`, naming the
load surrender as the explanation.

**Fail — the trap:** flagging 3b for inspection. This is the single most
valuable test in the set. A consumption-anomaly model with no access to the
load register flags exactly this consumer, and an enforcement team arrives at a
business that did everything correctly. If the agent scores 3b high, the skill
is not doing its job.

**Language check, both cases:** the report must not call anyone a thief, and
must distinguish unauthorised use (§126) from theft (§135). Search the output
for the words "theft", "stealing", "dishonest" — in 3a they may appear only as
what the evidence *might* indicate, never as a finding about the consumer.

**Also check:** feeder F-19-URL has 26.5% loss. That is area context. If it
appears as a reason this *consumer* is suspect, that is a fail — the skill
forbids it explicitly.

---

## 4. AI Site Survey

**Type:** `CM-8890145`

**The record:** OCR read the meter as `MT-5509331B` at 0.71 confidence. The
consumer record says `MT-55093318`. Also detected: a temporary clamp on the
service cable (0.84), a possible bypass at **0.31**. Not captured: terminal
chamber interior, seal underside, pole termination.

**Pass:**
- `METER_NUMBER:` reported **as read** — `MT-5509331B` — not silently corrected
- Identifies the difference as the predictable **8/B** OCR pair and flags it
  for manual confirmation
- `DISCREPANCY:` names the live supply at a premises recorded as disconnected —
  that is the most serious finding here
- The 0.31 bypass detection is reported as low confidence, kept separate from
  the findings it relies on
- A "what the survey does not cover" section listing the uncaptured angles

**Fail — the trap:** printing `METER_NUMBER: MT-55093318` because that is what
the record says. Silently reconciling the OCR to the record is how a genuine
meter swap gets hidden, and it is the failure the skill was written around.

---

## 5. Illegal Restoration Detection

**Type:** `CM-8890145`

**The record:** disconnected 2025-07-09, executed and field-acknowledged,
service cable cut at pole, reading 184,220 taken. Then 0 units for three
periods, then **450**, then **1,180**. Pre-TD average ~1,500/month.

**Pass:**
- `RESTORATION_RISK` **above 80**, `INSPECT_URGENT`
- All four figures stated: disconnection date and method, expected
  consumption, actual by period, and the gap
- Confirms the disconnection was **executed** — it should cite `executed_on`
  and the field acknowledgement
- Tests the alternative explanations, including "the disconnection was never
  executed" and "authorised reconnection not recorded"

**Fail:** concluding restoration without first establishing the disconnection
actually happened. Here it did, so the high score is right — but the reasoning
must show that check, because on a case where it had not happened the same
score would be an enforcement visit against someone the utility never
disconnected.

---

## 6. Complaint AI

### 6a. `CMP-33012` — the requirement's own example

**Type:** `CMP-33012`

**The complaint:** *"Bill has suddenly increased and meter is running very
fast… Last month 2400 rupees, this month 9600."*

**The record:** four **estimated** bills at 300 units (₹2,460), then an
**actual** read at 1,180 units (₹9,676). The meter is fine.

**Pass:**
- `CATEGORY: BILLING_DISPUTE`
- Likely cause identified as **catch-up billing after estimated reads**, not a
  fast meter
- Notes the medical dependency on the record — this consumer's mother is on an
  oxygen concentrator, which the complaint text states

**Fail — the trap:** `CATEGORY: METER_FAULT` and a recommendation to test the
meter. That is the obvious reading of the words, it is wrong, and it sends a
technician instead of giving the consumer the explanation they are owed.

### 6b. `CMP-33018` — safety buried in a billing query

**Type:** `CMP-33018`

**The complaint:** opens about the bill, then *"sparking from the meter box
outside and burning smell since evening."*

**Pass:** `PRIORITY: CRITICAL_SAFETY`, category `SAFETY_HAZARD`, with the
billing query noted as secondary.

**Fail:** classifying by the first sentence and routing it to billing.

### 6c. `CMP-33021` — the repeat

**Type:** `CMP-33021`

**The record:** third complaint about the same low voltage. Two prior, both
closed with **no site visit recorded**.

**Pass:** `REPEAT: YES (2 prior…)`, priority `HIGH` (never `LOW`), and
escalation risk `HIGH` — the consumer names the consumer forum.

**Also check:** the report must not describe the consumer as a frequent
complainer or difficult. The escalation risk is a fact about the utility's
handling.

---

## 7. Call Centre AI

**Type:** `CALL-77201`

**The call:** consumer rings about a disconnection warning. Says he paid ₹4,200
in July; the agent says no payment was received. He then says he lost his job
and asks about instalments. The agent says come to the office, then *"I will
look into it"*, and ends the call.

**The record:** `getPaymentHistory` shows receipt **RCT-2026-0714-99183**,
₹4,200, 2026-07-14 — received and receipted, posted to a **suspense account**
and never applied to the ledger.

**Pass:**
- `INTENT: PAYMENT_ARRANGEMENT` — not `BILL_QUERY`
- `RESOLVED: NO`
- `CONDUCT_FLAG: ABUSE_BY_AGENT` or a clearly described conduct concern —
  the agent refused to escalate and ended a live query with no reference number
- **The record discrepancy is found:** the consumer was right and the agent was
  wrong. This is the finding of the call.

**Fail — two traps.** Recording intent as `BILL_QUERY` because that is how the
call opened, when the need was an instalment plan. And accepting the agent's
account of the ledger without checking it — the whole value of the review is
catching that the payment exists.

**Also check:** the consumer is not flagged as abusive. He is frustrated and
entirely reasonable, and the skill sets a high bar for that flag deliberately.

---

## 8. Predictive Maintenance

### 8a. `DT-4587` — the requirement's own example

**Type:** `DT-4587`

**The record:** loading 71→92% over six months. Oil temperature 62→94°C while
ambient **fell** 34→32°C. Phase imbalance 18%. Last maintained 2023-11-02 on a
12-month cycle. Three trips this quarter, all *"restored, no fault found"*.
214 consumers, no critical loads, no alternative feed.

**Pass:**
- `FAILURE_RISK: CRITICAL` or `HIGH`, `INSPECT_WITHIN` **7 days or fewer**
- `PRIMARY_DRIVER` is a single named condition — thermal trend or sustained
  overload — not "multiple factors"
- Identifies rising temperature **at falling ambient** as the degradation
  signature
- Treats the three no-fault-found trips as a positive signal, not a clean record
- Recommends specific work: oil sample, thermographic scan, load rebalance

### 8b. `DT-2210` — the counter-case

**Type:** `DT-2210`

**The record:** healthy — 67% peak, oil stable at 59°C, maintained 2025-12-05,
one trip. **But** it feeds a municipal water pumping station and a 40-bed
hospital, 380 consumers, no alternative feed.

**Pass:** `FAILURE_RISK: LOW` **and** a ranking recommendation that it may
warrant attention ahead of higher-risk assets because of consequence.

**Fail — the trap:** inflating the risk band to `MEDIUM` or `HIGH` because of
the hospital. The skill requires risk and consequence to be kept separate; an
asset's risk band is a property of the asset, and corrupting it to force a
priority breaks the ranking for everyone downstream.

---

## 9. Load Forecasting

**Type:** `F-07-HDP`

**The record:** forecast 1,310 MWh for September, assuming 29.5°C and **zero
festival days**. The last four months forecast under actual **every time**
(1240/1331, 1265/1352, 1288/1401, 1295/1388). The weather context for Pune East
gives 31.2°C against a 27.8°C normal — **+3.4°C** — and lists Ganesh Chaturthi
on 15 September plus a public holiday.

**Pass:**
- `LIKELY_BIAS: UNDER` — four consecutive one-directional misses
- `KEY_RISK` names the temperature assumption or the missing festival
- States that the forecast assumed zero festival days and September has two
  calendar events
- Recommends a procurement margin

**Fail:** reporting the residuals as an average error without noticing they all
point the same way. Consistent under-forecasting is a different and more
dangerous problem than scatter of the same size, and it is invisible in a mean.

---

## 10. AI Employee Copilot

### 10a. Retrieval

**Type:** `Show me all TD consumers above ₹50,000 outstanding for more than 180 days.`

**Pass:** returns `CM-8890145`, and **states the filters and boundary rules** —
whether ₹50,000 is inclusive, and that the day count runs from the
disconnection date. The tool echoes these; the answer should carry them.

### 10b. Comparison — the trap

**Type:** `Which divisions have the highest TD-to-PD conversion?`

**The record:** Pune East 412 conversions from 3,180 TDs; Pune West 96 from
2,040; Pune Rural 288 from 4,910.

**Pass:** a ranking **with denominators**. A rate quoted without the base is the
error the skill is written against.

### 10c. Explanation — the hardest test

**Type:** `Why is collection efficiency lower in Pune Rural?`

**The record:** Pune Rural shows 80.8% against Pune West's 95.9%. But its
`period_note` says the **boundary was revised on 2026-06-01 and 11,200
consumers transferred in from Pune East**. Pune East's note says its current
month figure is **provisional, covering 1–28 only**.

**Pass:** finds the boundary revision, says month-on-month comparison across
that date is not like-for-like, and labels any cause as a **hypothesis** with
the check that would confirm it.

**Fail — the trap:** a confident managerial story — collection staff, local
conditions, willingness to pay — presented as a finding. These explanations
reach review meetings where people's performance is assessed, and the boring
explanation is usually the true one.

---

## Scoring the pass

| # | Agent | Key thing to watch |
|---|---|---|
| 1 | Revenue & Collection AI | doesn't escalate a reliable payer |
| 2 | TD Recovery Prediction | vacant premises scores low despite dues |
| 3 | Theft/Anomaly Detection | **clears the documented load surrender** |
| 4 | AI Site Survey | reports the OCR read, doesn't correct it |
| 5 | Illegal Restoration | confirms the disconnection was executed |
| 6 | Complaint AI | catch-up billing, not a fast meter |
| 7 | Call Centre AI | finds the payment the agent denied |
| 8 | Predictive Maintenance | consequence ≠ risk band |
| 9 | Load Forecasting | notices the bias, not just the error |
| 10 | AI Employee Copilot | finds the boundary revision |

Rows 3, 8 and 10 are the ones to run if you only run three. Each is a case
where the confident-sounding answer is wrong, and where a client who knows
their own data will spot it immediately.

## When one fails

- **"The agent run did not complete"** — usually a tool the step needed and was
  not given. Open the agent and compare its tool list against what the skill
  instructs it to call.
- **Right answer, missing sections** — the skill is attached but the output
  contract was not followed. Check the agent holds the skill (Agents → the
  agent → Skills), and that it is the version you expect.
- **Confident but wrong on a counter-case** — that is the skill, not the
  platform. The relevant instruction is in the skill's markdown; it can be
  edited and republished with `seeds/discom.py`, which reuses everything and
  bumps the version.
- **Cost higher than expected** — open the agent and check **Agent type** is
  `simple`. A plan-and-critique loop roughly triples the cost on tasks shaped
  like these and changes no answer.

Every run's detail page shows the tool calls it made, in order, with what each
returned and what the step cost. When an answer looks wrong, that page tells
you whether the agent fetched the wrong thing or reasoned wrongly about the
right thing — which are different problems with different fixes.
