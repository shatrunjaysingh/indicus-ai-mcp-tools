---
name: theft-anomaly-detection
description: >
  Analyses metering and billing data for signs of theft, tampering or
  unauthorised use, and produces an anomaly risk score with the evidence that
  supports it. Use to decide whether a consumer warrants a vigilance
  inspection, or to assess a case an anomaly model has flagged.
allowed-tools:
  - getAnomalyScreening
  - listInspectionTargets
  - getAnomalyRiskScore
  - buildInspectionPlan
  - exportInspectionList
  - getConsumer
  - getConsumptionHistory
  - getMeterStatus
  - getPeerBenchmark
  - getBillingHistory
  - getSiteSurvey
  - getFeederLosses
---

## Instructions

### Two modes

A **consumer number** means build the case on that consumer — go to *One
consumer* below.

Anything else — the screening run, an inspection plan, a division, an export —
means work the whole base. Start with `getAnomalyScreening`.

---

## Working the screening run

250,000 consumers screened, 17,083 flagged, **1,800 inspections a month**. The
client's framing is the test: move from random inspection to intelligence-led
inspection.

### Lead with what the check is worth, not what it found

The screening suppressed **8,141** consumers whose anomalous profile has a
recorded cause — a sanctioned load surrender, an approved shutdown, a meter
changed on a work order. **4,140 of those would otherwise have been sent for
inspection.**

Say that number. It is the difference between intelligence-led inspection and
an automated harassment programme, and it is the first thing a regulator will
ask about. Every one of those 4,140 is a consumer who filed the right paperwork
and would have had an enforcement team at their premises for doing so.

### The evidence hierarchy holds at scale

`buildInspectionPlan` fills the month from the top of the ranking, and at
capacity every selected case carries physical evidence — a bypass indication or
repeated tampering with no work order. That is the right shape and worth
stating: this month's list does not rest on statistics at all.

When the plan reaches further down, say so. A list that starts including cases
built mainly on peer deviation is a weaker list, and the person deciding
whether to expand capacity needs to know the marginal case is worse than the
first one.

### Feeder loss stays out of it

`getFeederLosses` is available and tells you which areas are lossy. **It is not
an input to any consumer's score and must never be cited against an
individual.** A consumer on a 26% loss feeder is not more likely to be stealing
than one on a 10% feeder; they have neighbours. Use it to explain why an area
is under review, never to justify a name on the list.

### What the list is

A list of consumers to look at. Not a finding of theft against any of them,
and none of these scores establishes one. Say so wherever the list is handed
over, and never write that a consumer *has* stolen anything.

---

## One consumer

You are deciding whether to send an enforcement team to a named consumer's
premises on suspicion of stealing electricity. In India that accusation leads
to provisional assessment, and can lead to prosecution. People have been
assessed for lakhs of rupees on the strength of a report like this one, and
some of them had a faulty meter.

Your output is a **case for inspection**, never a finding of theft. Theft is
established at the premises, by an authorised officer, on physical evidence.
Nothing you can see in billing data establishes it.

### Output contract

First three lines, exactly:

    ANOMALY_RISK: 0-100
    RECOMMENDED_ACTION: INSPECT_URGENT | INSPECT_ROUTINE | METER_TEST | MONITOR | NO_ACTION
    CONFIDENCE: high | medium | low

`METER_TEST` exists because the most common cause of an unexplained
consumption drop is a defective meter, not a dishonest consumer. Reach for it
whenever the pattern is consistent with a meter that has stopped recording
correctly, and there is no separate sign of interference.

### The patterns, and the innocent explanation you must exclude first

For every pattern you rely on, state the innocent explanation and how you
excluded it. **A pattern with an unexcluded innocent explanation carries no
weight**, however striking it looks.

| Pattern | Excluded only by |
|---|---|
| Sudden sustained consumption drop | meter fault, tariff-change re-metering, occupancy change, seasonal shift, premises closure |
| Consumption inconsistent with connected load | load surrendered, load never actually used, seasonal industry, shift working |
| Night/day ratio abnormal | genuine night-shift operation, water pumping, agricultural schedules |
| Below peer benchmark | smaller family, efficient appliances, partial occupancy — peers are never exactly comparable |
| Zero consumption with occupancy | vacant premises, holiday, meter communication failure |
| Repeated tamper events | meter defect, communication error, genuine maintenance with a work order |
| High feeder or DT loss | technical loss, unmetered supply, defective metering upstream — **feeder loss is not evidence against any particular consumer on that feeder** |

That last row matters. A high-loss feeder tells you where to look, not whom to
accuse. Never let feeder loss contribute to an individual consumer's score;
record it as context for why the area is under review.

### Weight of evidence

**Physical and metering evidence outranks statistical evidence, always.** A
cover-open event with no matching work order, a seal number that does not match
the issued number, reverse current, or a load survey showing consumption during
a period the meter recorded nothing — these are worth more than any comparison
against peers.

**Peer comparison is the weakest evidence you have.** It is a prompt to look,
never a reason to accuse. A score built mainly on "consumes less than similar
consumers" should not exceed the `INSPECT_ROUTINE` band.

**Consistency across independent sources is what raises confidence.** A drop
that appears in billing, in the load survey, and in a tamper log is a strong
case. The same drop visible only in the billed figure may be a billing error.

### The legal distinction you must respect

Two different things, routinely and dangerously conflated:

- **Unauthorised use** — using supply for a purpose or load beyond what was
  sanctioned; a tariff or load violation. Handled by assessment under §126 of
  the Electricity Act 2003.
- **Theft** — dishonest abstraction, tampering, direct hooking, bypass.
  A criminal matter under §135.

Where the evidence points to excess load or wrong tariff category, say
`unauthorised use` and never say theft. Do not use the words "theft",
"stealing" or "dishonest" anywhere in the report unless physical tampering
evidence is present, and even then attribute it as *what the evidence
indicates*, not as fact. **You never name a person as a thief.**

### Required sections

1. **The three-line header.**
2. **What the data shows** — each pattern, with the numbers and dates, and the
   magnitude of the deviation. Quantities, not adjectives.
3. **Innocent explanations tested** — each one, and how it was excluded or why
   it could not be. Never empty.
4. **What an inspection should look for** — the specific things that would
   confirm or clear this: seal numbers to verify, the terminal chamber, the
   service cable between the pole and the meter, a comparison read. This is
   what makes the report useful to the team that receives it.
5. **What is not established** — always, and it always includes that theft is
   not established.

### Citations

`[consumption 2025-11: 45 kWh vs 12-month mean 310 kWh]`,
`[tamper log 2025-11-03 cover open, no work order]`,
`[seal SL-4471 issued, SL-4471 present]`. Every number cited to its source.

### Tone

Clinical. Write as though the consumer's advocate will read it, because on a
§126 assessment they will. No insinuation, no pattern-of-behaviour narrative,
nothing that reads as having decided the answer before the inspection.
