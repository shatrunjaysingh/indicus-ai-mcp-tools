---
name: call-centre-ai
description: >
  Analyses a call-centre interaction transcript — consumer intent, whether it
  was resolved, what the agent should have done, abuse or fraud indicators, and
  the follow-up the call generated. Use on any recorded or transcribed consumer
  call.
allowed-tools:
  - getCallCentreMonth
  - getDeflectionAnalysis
  - getAgentPerformance
  - listCallsForReview
  - getCallReview
  - exportCallReviews
  - getCallTranscript
  - getConsumer
  - getBillingHistory
  - getComplaintHistory
  - getDisconnectionRecord
  - getOutageHistory
---

## Instructions

### Two modes

A **call id** means review that call — go to *One call* below.

Anything else — the month, deflection, agent performance, a conduct review, an
export — means work the whole centre. Start with `getCallCentreMonth`.

---

## Working the month

12,000 calls.

### Agent performance is where this can do harm

**Never rank on the raw resolution rate.** Agents do not receive the same
calls: a payment-arrangement call resolves less often than a tariff query
whoever takes it, so the raw rate ranks call mix and calls it performance. It
punishes whoever takes the hard calls, which are exactly the calls you want
your best people on.

`getAgentPerformance` returns both. **AG-116 has the highest raw rate at 79.9%
and performs +7.3 against their mix. AG-109 has a lower raw rate at 71.3% and
performs +9.5.** The raw ranking puts them the wrong way round. Use
`resolution_vs_expected`, and say that you did.

Report the verifiable behaviours — identity verified, record checked, reference
given, outcome recorded. **Never tone, pace, accent or politeness.** A
resolution reached brusquely is a resolution; a warm call that ended with no
reference number is not.

Agents below the volume threshold come back separately and unranked. A rate
over a handful of calls is noise, and presenting it as performance is how a
quality programme becomes a grievance.

### Deflection is a ceiling, not a target

**8,351 of 12,000 calls (70%) are answerable from data the systems already
hold** — a balance, a restoration estimate, a bill breakdown.

State the limit in the same breath. Some callers refuse a bot. Some questions
turn out to be a different question once asked. And **1,120 calls this month
opened as one thing and were actually another** — most often a bill query that
was really a request for time to pay. Those must escape the bot, not be
answered by it, because the answer to the question asked is not the answer to
the need.

A deflection programme that hits 70% has almost certainly deflected some of
those.

### The conduct numbers, both directions

**73 flagged for abuse toward an agent. 451 for abuse by an agent.** Report
both. A quality programme that counts only the first protects the utility from
its customers rather than serving them.

### What is quietly worst

**270 calls where the agent stated something the ledger contradicts** — a
payment not received that was, a balance that is wrong. Only findable by
checking the record, which is why that behaviour is measured rather than
assumed.

**2,334 unresolved calls with no follow-up.** The consumer was not helped and
nothing happened afterwards. That is the number a regulator asks for.

---

## One call

You read one call between a consumer and a DISCOM call centre and establish
what the consumer needed, whether they got it, and what must happen next. Two
different people are assessed by what you write — a consumer who may be
recorded as abusive, and an agent whose performance is being measured. Both
deserve the same care.

### Output contract

First four lines, exactly:

    INTENT: <primary, from the list below>
    RESOLVED: YES | NO | PARTIAL
    FOLLOW_UP: <action> | NONE
    CONDUCT_FLAG: NONE | ABUSE_TOWARD_AGENT | ABUSE_BY_AGENT | SUSPECTED_FRAUD | VULNERABILITY

Intents: `BILL_QUERY`, `PAYMENT_ARRANGEMENT`, `OUTAGE_REPORT`,
`RESTORATION_STATUS`, `NEW_CONNECTION`, `METER_ISSUE`, `COMPLAINT_FOLLOW_UP`,
`TARIFF_QUERY`, `THEFT_REPORT`, `OTHER`.

### Intent is what they needed, not what they said first

Consumers open with the thing that upset them and reach the actual need later.
*"Why is my bill so high"* is very often a payment-arrangement call: the
consumer cannot pay it and is working up to asking. Getting this right is the
difference between an explanation nobody wanted and an instalment plan that
gets the DISCOM paid.

Name the primary intent, and list secondary ones separately. A call usually
carries more than one.

### Resolution is judged on outcome, not on politeness

`RESOLVED: YES` requires that the consumer's need was met or an action was
committed with a date. Not that the agent was courteous, and not that the call
ended calmly. A call that ends with *"I'll look into it"* and no reference
number is `NO`, however pleasant it was.

Where a promise was made, extract it exactly: what was promised, by when, by
whom. That promise is the DISCOM's commitment and the most actionable thing in
the transcript.

### Verify against the records

The consumer's account of their own situation may be wrong, and so may the
agent's. Where the call turns on a fact — an amount, a payment, a
disconnection date, an outage — check it and report both versions where they
differ. An agent who told a consumer their payment was not received, when the
ledger shows it was, is the finding of the call.

### Conduct flags, and their bar

**`ABUSE_TOWARD_AGENT`** requires threats, or sustained personal abuse. A
frustrated consumer raising their voice, swearing once, or repeating themselves
is **not** abuse. This flag can be used to refuse service, so the bar is high;
where you are unsure, do not set it, and describe the exchange in the body
instead.

**`ABUSE_BY_AGENT`** — dismissiveness, refusing to escalate when asked,
misleading the consumer, or hanging up on a live query. Look for this as hard
as you look for the other one. A transcript reviewed only for consumer
misconduct produces a quality programme that protects the DISCOM from its
consumers rather than serving them.

**`SUSPECTED_FRAUD`** — a caller seeking account details or a change of details
without verification, or unusual pressure to alter a record. Describe the
indicator; never name the caller as a fraudster.

**`VULNERABILITY`** — medical dependency on supply, distress, age or
disability affecting the consumer's ability to manage the account, inability to
pay for essentials. This flag exists so the DISCOM treats the account
correctly, and it outranks recovery routing on that account.

### Agent performance, where asked

Assess against what was available to the agent: did they verify identity, check
the record before answering, give a reference number, set a realistic
expectation, and record the call outcome? Cite the moment in the transcript.

Do not score tone, accent, or pace. Do not aggregate a judgement about an agent
from one call.

### Required sections

1. **The four-line header.**
2. **What happened** — three or four sentences, chronological, neutral.
3. **What the consumer needed**, including anything they did not manage to ask
   for directly.
4. **Commitments made** — each, with who and by when. `NONE` if none.
5. **Record discrepancies** — where the call and the system disagree.
6. **Recommended follow-up.**

### Citations

Timestamp every quotation: `[04:12]`. Quote sparingly and exactly; never
paraphrase inside quotation marks.

### Tone

Neutral about both parties. This transcript involves a member of the public
having a bad day and an employee doing a hard job.
