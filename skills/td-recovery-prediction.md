---
name: td-recovery-prediction
description: >
  Scores a temporarily disconnected consumer for recovery priority, combining
  dues, days since disconnection, payment history, meter and site status, and
  restoration risk. Use when deciding where to send a recovery team, or whether
  a TD account should convert to permanent disconnection.
allowed-tools:
  - getTDPortfolio
  - listTDRecoveryPriority
  - getTDRecoveryScore
  - buildTDFieldPlan
  - exportTDRecoveryList
  - getConsumer
  - getDisconnectionRecord
  - getPaymentHistory
  - getBillingHistory
  - getConsumptionHistory
  - getMeterStatus
  - getSiteSurvey
  - getNoticeHistory
---

## Instructions

### Two modes

A **consumer number** means score that account — go to *One account* below.

Anything else — the TD book, a division, a field plan, a PD review, an export —
means work the whole book. Start with `getTDPortfolio`.

---

## Working the TD book

40,000 disconnected accounts against 2,500 visits a month. The client's own
framing is the test: *instead of sending field teams randomly, focus where
recovery probability × recoverable amount is highest.*

### The deliverable is the field list

`buildTDFieldPlan` produces it, sized to the real capacity. Open with the
headline:

> From 40,000 TD accounts, 2,500 selected for field recovery — ₹22.3 cr
> expected against ₹8.5 L of visits, priority band 94–100.

Then `exportTDRecoveryList` for the file the team actually works from. **Never
put the rows in your reply.**

### Recoverable is not the ledger balance

The book shows ₹149 cr outstanding and ₹135 cr recoverable. The ₹13 cr gap is
statute-barred arrears under §56(2), disputed sums, and post-demolition
periods. Rank on the recoverable figure and say what came off — a programme
built on the ledger chases money the DISCOM cannot collect, and in the barred
case is not entitled to.

### What the score already knows, and what it does not

`recovery_priority` is a percentile: 95 means work this before 95% of the book.
It combines all ten inputs the client listed. You do not recompute it.

What it cannot see is the thing worth saying: **20,817 of 40,000 have never
been surveyed.** Their probability carries no site evidence at all, so they sit
in the middle of the ranking by default — neither confirmed recoverable nor
confirmed gone. A field plan that only visits the top of the ranking never
resolves them, and they stay unresolved for years. Say what share of the plan
is confirmation versus collection.

### PD conversion is a decision, not an escalation

Accounts with nothing recoverable and nobody at the premises need a decision,
not a visit. Permanent disconnection ends the supply relationship and usually
ends any realistic prospect of recovery — so it is not a harsher recovery
action, it is an acknowledgement that the money has gone and the asset should
be released. Say that plainly, and give the count.

---

## One account

You rank one temporarily disconnected account against a finite number of field
visits. The DISCOM cannot visit everyone, so a score that is wrong in the
middle of the range is not a rounding error — it is a team sent to a premises
that was never going to pay while a recoverable ₹85,000 sits untouched.

### Output contract

First three lines, exactly:

    RECOVERY_PRIORITY: 0-100
    RECOMMENDED_ACTION: FIELD_VISIT | NOTICE | PD_CONVERSION | SETTLEMENT_OFFER | WRITE_OFF_REVIEW | NO_ACTION
    CONFIDENCE: high | medium | low

### What the score means

**Recovery priority is recoverable amount × probability of recovery.** Neither
alone. This is the whole idea, and it is where the intuitive ranking goes
wrong in both directions:

- ₹85,000 outstanding on a premises that is demolished and untraceable scores
  **low**, however large the number. There is nothing to recover.
- ₹18,000 on an operating shop with a live occupier and an illegal restoration
  scores **high**, because the money is collectable and the site is there.

State both factors separately before combining them. A report that gives a
score without saying what it estimated the recoverable amount to be, and how
likely recovery is, cannot be checked.

### The evidence, and what each is worth

**Recoverable amount** is not the ledger balance. Subtract what is
statute-barred, what is disputed, and what relates to a period the consumer
demonstrably did not occupy the premises. State the ledger figure and your
recoverable figure, and account for the difference.

**Days since disconnection cuts both ways.** Longer means more accrued dues and
a colder trail — but a long TD with *no* restoration and *no* consumption often
means the premises is vacant, which lowers recovery probability sharply. Never
treat TD age alone as a priority driver.

**Restoration risk is the strongest single positive signal.** Consumption after
a disconnection date means someone is there, using power, and has an incentive
to settle rather than face proceedings. Confirm it from `getConsumptionHistory`
and `getMeterStatus` yourself — do not take a restoration flag on trust.

**Site survey beats every desk record.** An occupied premises with a running
business is recoverable; a locked and stripped premises is not. Where a survey
exists, it outranks any inference you drew from consumption data, and where the
two conflict, say so explicitly rather than averaging them.

**Payment history before disconnection** tells you whether this is a consumer
who fell into difficulty or one who never paid. The first settles; the second
requires enforcement.

**Meter status.** A meter removed, burnt, or tampered changes both the recovery
route and the assessment basis, and a tampered meter moves the case toward
§126 assessment rather than plain arrears recovery.

### Scoring discipline

Bands, so that scores are comparable between cases:

| Band | Meaning |
|---|---|
| 85-100 | Large recoverable amount, occupier present, active or restored supply |
| 60-84 | Recoverable, occupier likely present, needs a visit to confirm |
| 35-59 | Either amount or probability is weak, not both |
| 15-34 | Small amount, or occupier probably gone |
| 0-14 | Nothing meaningfully recoverable, or already at PD |

**Do not cluster.** If every case you score lands between 70 and 80, the score
is carrying no information and the ranking it produces is arbitrary. Commit.

### PD conversion

Recommend `PD_CONVERSION` only when the TD has run beyond the period the
DISCOM's own policy allows, recovery probability is low, and the site survey
supports it. Permanent disconnection ends the supply relationship and usually
ends the realistic prospect of recovery, so it is not an escalation of severity
— it is a decision that the money is gone and the asset should be released.
Say that plainly when you recommend it.

Where the amount is large and the trail is cold, `WRITE_OFF_REVIEW` is the
honest recommendation. Recommending a field visit to protect a number on a
recovery report wastes the visit.

### Required sections

1. **The three-line header.**
2. **Recoverable amount** — ledger figure, deductions with reasons, and the
   figure you carried into the score.
3. **Recovery probability** — the site and behavioural evidence, each cited.
4. **How the score was reached** — the two factors and how they combined. A
   reviewer who disagrees must be able to see whether they disagree about the
   amount or about the probability.
5. **What would change it** — the one piece of missing information that would
   most move this score. Usually a site survey.

### Citations

`[TD 2025-06-15]`, `[survey 2026-01-20]`, `[consumption 2025-07: 450 kWh]`.
Every figure in the score carries its source.

### Tone

Neutral and specific. This account belongs to someone whose supply is already
off; the report should not read as though that has been decided against them
twice.
