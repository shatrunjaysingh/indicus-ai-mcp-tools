---
name: payment-behaviour-segmentation
description: >
  Segment electricity-consumer accounts according to observed payment behavior, delinquency trajectory, dispute and account status, and payment timing; quantify segment exposure and collection performance; identify transitions between behavioral states; and map each segment to an appropriate collection treatment. modes: * portfolio * consumer * segmentation * segment_analysis * migration_analysis * treatment_strategy * campaign_planning * segment_monitoring * export
allowed-tools:
  - getCollectionPortfolio
  - getConsumerScore
  - listCollectionTargets
---

# AI Payment Behavior Segmentation

## Purpose

Divide the collection book into **behaviorally meaningful account segments** and explain what should follow from each segment.

The segmentation answers:

> **What has this account's payment behavior looked like, how is that behavior changing, and what collection treatment is appropriate?**

It does not answer:

* what kind of person the consumer is,
* why the consumer behaves that way,
* what the consumer can afford,
* whether the consumer intends to pay,
* or whether the consumer is a "good" or "bad" customer.

A segment describes **account behavior**, not consumer identity or character.

---

# Core Principle

## A segmentation is useful only if treatment changes

Do not produce a table of segments and stop.

For every segment report:

1. definition,
2. eligibility rule,
3. account count,
4. recoverable exposure,
5. payment behavior,
6. payment probability where available,
7. recent collection performance,
8. trend,
9. recommended treatment,
10. treatment to avoid,
11. transition risk,
12. and evidence supporting the treatment.

The purpose of segmentation is operational.

> **Segment → understand behavior → choose treatment → measure outcome.**

---

# Segmentation Rules

Segments must be:

* behavior-based,
* reproducible,
* mutually exclusive within the defined segmentation population,
* collectively exhaustive unless an explicit `UNCLASSIFIED` segment exists,
* time-bounded,
* auditable,
* and based only on approved operational data.

Do not create a segment because it "looks useful" in one month's data.

Every segment must have a deterministic definition.

---

# Required Segmentation Population

Before assigning segments, establish:

* population included,
* population excluded,
* account status,
* data cutoff date,
* observation window,
* minimum payment-history requirement,
* treatment of new connections,
* treatment of disconnected accounts,
* treatment of closed accounts,
* treatment of disputed accounts,
* and model/segmentation version.

Example:

```text id="2b3d7j"
SEGMENTATION_DATE: 2026-09-01
OBSERVATION_WINDOW: previous 12 billing cycles
POPULATION: active collection accounts
MODEL_VERSION: PB-SEG-v3.1
```

Do not compare segment sizes across months without confirming that the underlying population definition remained stable.

---

# Canonical Behavioral Segments

The default segmentation should include the following behavioral states where the data supports them.

## 1. RELIABLE_BUT_SLOW

Definition:

* payment occurs in essentially every cycle,
* but payment consistently occurs after the normal due date or later in the cycle.

Treatment:

`REMIND`

Potential secondary treatment:

`NO_ACTION` if reminders do not materially improve payment timing.

Interpretation:

The account demonstrates a recurring late-payment pattern but does not necessarily demonstrate persistent non-payment.

Do not call the consumer:

* unreliable,
* unwilling,
* evasive,
* or delinquent as a character judgment.

The behavior is:

> **payments are consistently received, but later than the desired payment point.**

---

# 2. RECENTLY_DETERIORATED

Definition:

* historically regular payment behavior,
* followed by a material recent deterioration,
* such as newly missed or substantially delayed cycles.

The exact threshold must come from the approved segmentation configuration.

Treatment:

`CALL` or `REMIND`

depending on the approved collection-action model.

This is an important early-intervention segment because the behavior has changed recently.

The agent should report:

* prior payment performance,
* recent missed cycles,
* deterioration date,
* current recoverable amount,
* and whether the change is continuing.

Do not assume the reason for the deterioration.

---

# 3. CHRONIC_DEFAULT

Definition:

An account meeting the utility's approved chronic-default definition.

Do not hard-code:

> six missed cycles

unless six cycles is the utility's formally configured definition.

The chronic-default early-warning skill and this segmentation skill must use the **same governed definition**.

Treatment may include:

* `FIELD_VISIT`,
* `NOTICE`,
* or `DISCONNECT`

only when independently justified and policy-eligible.

Do not assume every chronic account should receive enforcement.

Consider:

* recoverable amount,
* payment probability,
* previous interventions,
* action effectiveness,
* cost,
* and legal/policy eligibility.

---

# 4. DISPUTED

Definition:

An account has an active validated dispute or unresolved billing/ledger issue that affects the amount being pursued.

Treatment:

`HOLD`

until the dispute is resolved or the undisputed portion is separately established and eligible for collection.

Do not include disputed balances as ordinary collectible exposure without qualification.

The segment exists because the **data/amount being pursued may not be reliable**, not because the consumer is refusing to pay.

---

# 5. PREMISES_VACATED

Definition:

The utility has a sufficiently reliable operational indication that the premises are vacant and there is no current party/presence from whom ordinary collection can reasonably be pursued.

Treatment may include:

* account verification,
* field verification where economically justified,
* recovery from the responsible party where legally applicable,
* account closure/transfer workflow,
* write-off review where appropriate.

Do not infer vacancy from:

* low consumption,
* zero consumption alone,
* locality,
* property type,
* or payment behavior.

Vacancy requires an approved operational indicator.

---

# 6. NEW_CONNECTION_EARLY_ARREARS

Definition:

A recently connected account that has entered arrears during the early billing cycles.

Before treating it as ordinary collection risk, check:

* tariff assignment,
* meter installation,
* meter multiplier,
* first bill,
* billing dates,
* prorated billing,
* security deposit,
* connection charges,
* reading validity,
* meter commissioning,
* and account setup.

Treatment:

`VERIFY_RECORDS` / `CALL` / `REMIND`

depending on the detected issue.

A first-period arrear may be a setup or billing problem rather than an established payment pattern.

---

# Additional Useful Segments

Where the utility's data supports them, consider:

## STABLE_ON_TIME

Pays consistently within the desired payment window.

Treatment:

`NO_ACTION` or low-cost reminder only where justified.

Do not spend collection resources on this segment merely because it has an outstanding bill.

---

## INTERMITTENT

Alternates between paid, late, and unpaid cycles without a clear persistent trajectory.

Treatment depends on:

* current delinquency,
* payment likelihood,
* recoverable amount,
* and recent behavior.

---

## RECOVERING

Previously delinquent but showing sustained improvement.

Treatment:

avoid unnecessary escalation.

Monitor whether improvement persists.

Do not keep an account in an enforcement workflow merely because of historical delinquency if current behavior has materially improved.

---

## ARRANGEMENT_ADHERENT

Account is under an approved payment arrangement and is meeting its commitments.

Treatment:

`NO_ACTION` or arrangement monitoring.

Do not treat scheduled instalments as missed payments.

---

## ARRANGEMENT_BROKEN

Account has materially failed an approved payment arrangement.

Treatment:

follow the utility's arrangement-escalation workflow.

Do not automatically jump to disconnection.

---

## DISCONNECTED

Supply is already disconnected.

This is an account-state segment rather than a pure payment-behavior segment.

Do not mix it into active-consumer payment behavior unless the segmentation model explicitly supports multiple dimensions.

---

# Segment Priority

Do not rank segments solely by:

* number of accounts,
* total outstanding,
* or average payment probability.

At minimum show:

```text id="l7v0hr"
ACCOUNTS
RECOVERABLE_EXPOSURE
MEAN_PAYMENT_PROBABILITY
ACTUAL_COLLECTION_RATE
AVERAGE_DAYS_TO_PAYMENT
RECENT_TREND
RECOMMENDED_TREATMENT
```

This prevents the largest-balance segment from automatically becoming the highest-priority segment.

---

# The Number That Makes Segmentation Useful

Always compare:

> **money held by the segment**

against:

> **money historically collected from the segment**

Example:

| Segment                      | Accounts | Recoverable exposure | Collection performance | Treatment           |
| ---------------------------- | -------: | -------------------: | ---------------------: | ------------------- |
| Reliable but slow            |  sourced |              sourced |                sourced | Reminder            |
| Recently deteriorated        |  sourced |              sourced |                sourced | Early intervention  |
| Chronic default              |  sourced |              sourced |                sourced | Targeted escalation |
| Disputed                     |  sourced |              sourced |                sourced | Resolve first       |
| Premises vacated             |  sourced |              sourced |                sourced | Verify/resolve      |
| New connection early arrears |  sourced |              sourced |                sourced | Billing/setup check |

Every figure must have a source.

The important finding may be:

> The chronic-default segment contains the largest recoverable balance but produces materially lower collection than reliable-but-slow accounts. Escalating the entire chronic segment would therefore consume resources without proportionate recovery.

Do not assume this result.

The actual data must establish it.

---

# Payment Probability

Where available, display the approved payment probability for the segment.

Do not calculate it independently.

Use:

`getConsumerScore`

for account-level explanation and the approved portfolio scoring output for segment-level values.

Payment probability should answer:

> How likely is payment in the defined forecast horizon?

It should not be presented as:

* ability to pay,
* willingness to pay,
* consumer quality,
* or moral reliability.

---

# Expected Recovery

For collection decisions, use the approved expected-recovery methodology.

Conceptually:

`expected recovery = recoverable exposure × payment probability`

But use the utility's approved calculation.

Do not rank segments solely on probability.

A small segment with a high payment probability may recover less money than a larger segment with a moderate probability.

---

# Behavioral Trajectory

A static segment can hide important movement.

Track:

* previous segment,
* current segment,
* direction of movement,
* time spent in segment,
* and transition frequency.

Example:

```text id="z90a6e"
STABLE_ON_TIME
      ↓
RELIABLE_BUT_SLOW
      ↓
RECENTLY_DETERIORATED
      ↓
CHRONIC_DEFAULT
```

The reverse direction is also important:

```text id="2f0s3c"
CHRONIC_DEFAULT
      ↓
RECOVERING
      ↓
RELIABLE_BUT_SLOW
```

Do not assume movement is irreversible.

---

# Segment Transition Monitoring

Report:

* accounts entering each segment,
* accounts leaving each segment,
* transition rates,
* average time before transition,
* and transition to chronic default.

The key operational metric is often not:

> "How many accounts are chronic?"

but:

> **"How many accounts are moving toward chronic default, and how early can we intervene?"**

This connects directly to the Chronic Default Early-Warning skill.

---

# Recently Deteriorated vs Chronic

These must remain separate.

`RECENTLY_DETERIORATED` asks:

> Has payment behavior recently worsened?

`CHRONIC_DEFAULT` asks:

> Has the account crossed the utility's chronic-default definition?

An account can have:

* high chronic risk,
* but not yet be chronic.

That account belongs in early warning, not the chronic segment.

---

# Segment Treatment

Treatment should come from the Collection Action Optimization skill where available.

This skill should not recreate the action optimizer.

Architecture:

```text id="h4s9cy"
PAYMENT HISTORY
      +
ACCOUNT STATUS
      +
BILLING / LEDGER
      +
PAYMENT PROBABILITY
      ↓
PAYMENT BEHAVIOR SEGMENTATION
      ↓
BEHAVIORAL STATE
      ↓
COLLECTION ACTION OPTIMIZER
      ↓
REMIND / CALL / FIELD / NOTICE / DISCONNECT / HOLD
```

Segmentation describes the state.

Action optimization chooses the intervention.

---

# Treatment Matrix

Maintain an approved treatment matrix.

Example:

| Segment                      | Default treatment    | Avoid                             |
| ---------------------------- | -------------------- | --------------------------------- |
| Stable on-time               | No action            | Field visit                       |
| Reliable but slow            | Reminder             | Disconnection                     |
| Recently deteriorated        | Reminder/call        | Immediate enforcement             |
| Intermittent                 | Model-driven         | Blanket treatment                 |
| Chronic default              | Targeted escalation  | Automatic disconnection           |
| Disputed                     | Resolve dispute      | Recovery escalation               |
| Premises vacated             | Verify/resolve       | Repeated remote reminders         |
| New connection early arrears | Verify billing/setup | Treating as chronic               |
| Arrangement adherent         | Monitor arrangement  | Duplicate collection              |
| Arrangement broken           | Arrangement workflow | Ignoring commitment failure       |
| Recovering                   | Monitor              | Re-escalation solely from history |

This matrix is a starting configuration.

The actual treatment must come from approved utility policy and current evidence.

---

# Cost-to-Serve

Segment treatment should consider intervention economics.

Track:

* SMS cost,
* call cost,
* field-visit cost,
* notice cost,
* disconnection/reconnection cost,
* expected recovery,
* and incremental recovery.

A segment should not receive expensive interventions simply because its balance is large.

The correct question is:

> **Which treatment produces the most appropriate incremental recovery for the cost and customer impact?**

Use the Collection Action Optimization skill for the final action decision.

---

# Segment-Level Campaign Planning

When planning a campaign:

1. identify eligible segments,
2. estimate available recoverable exposure,
3. estimate payment behavior,
4. estimate channel response,
5. calculate expected incremental recovery where validated,
6. apply intervention capacity,
7. apply policy gates,
8. select candidates,
9. measure actual outcomes.

Do not send the entire segment through the same channel merely because the segment label is the same.

Within-segment heterogeneity matters.

---

# Segment Purity

A segment should be internally coherent enough to justify differentiated treatment.

Monitor:

* within-segment payment-rate variance,
* payment-probability variance,
* delinquency-age variance,
* collection-response variance,
* and action-response variance.

If a segment contains highly heterogeneous behavior, split it or stop using it for differentiated treatment.

---

# Segment Stability

Monitor segment composition over time.

A sudden increase in:

`RECENTLY_DETERIORATED`

could indicate:

* real behavioral deterioration,
* billing-system changes,
* payment-channel problems,
* data migration,
* altered due dates,
* or segmentation/model drift.

Do not assume a population shift is consumer behavior until operational causes are checked.

---

# Data Quality

Check:

* missing payment receipts,
* delayed receipt posting,
* unapplied payments,
* duplicate receipts,
* billing corrections,
* estimated reads,
* meter replacement,
* account migration,
* tariff changes,
* account transfers,
* connection dates,
* disconnection dates,
* dispute status,
* arrangement status,
* vacancy indicators,
* and closed-account status.

A bad ledger can create a false behavioral segment.

---

# New Accounts

Do not assign strong behavioral conclusions to accounts with insufficient history.

For new connections:

* identify them separately,
* state observation length,
* avoid comparing them directly with mature accounts,
* and check setup/billing integrity first.

Use:

`INSUFFICIENT_HISTORY`

where appropriate.

Do not force every account into a behavioral category.

---

# Vacated Premises

Vacancy is an operational account condition, not a payment-behavior conclusion.

If an account shows:

* zero consumption,
* zero visits,
* no contact,
* and a large balance,

do not automatically label it vacant.

Require approved evidence such as:

* field verification,
* closure request,
* meter removal,
* occupancy status,
* demolition record,
* or another trusted operational source.

---

# Disputes

A disputed account should not be treated as an ordinary payment-behavior segment if the amount due itself is uncertain.

Separate:

* undisputed recoverable amount,
* disputed amount,
* and total ledger balance.

Where the undisputed portion is independently valid and policy permits collection, it may be handled separately.

---

# Segment Leakage

Prevent information from the future from entering the current segment.

For a segmentation dated September 1:

Do not use payment behavior occurring after September 1 to determine the September 1 segment.

This is critical for measuring whether a segment predicts future behavior.

---

# Evaluation

Evaluate whether segments actually predict different outcomes.

Measure:

* future payment rate,
* future collection rate,
* average days to payment,
* future chronic-default rate,
* recovery after intervention,
* response by channel,
* transition probability,
* and incremental recovery.

A segment is valuable only if it produces a measurable operational distinction.

---

# Segment Lift

Compare segment outcomes against the overall portfolio.

For example:

> `RECENTLY_DETERIORATED` accounts have a future chronic-default rate of X% versus Y% for the eligible portfolio.

Use sourced figures.

Do not call a segment "high risk" merely because its average balance is high.

---

# Treatment Effectiveness

After a segment receives an intervention, measure:

* payment after treatment,
* amount recovered,
* time to payment,
* escalation avoided,
* repeat intervention,
* and incremental recovery where a control group or approved uplift methodology exists.

Do not claim that a segment "responds to calls" solely because payments followed calls.

Temporal association is not causal evidence.

---

# Segment Migration and Early Warning

The segmentation system should feed the chronic-default early-warning system.

Example:

```text id="b1qzax"
RECENTLY_DETERIORATED
        +
RISING CHRONIC-RISK SCORE
        +
MATERIAL RECOVERABLE BALANCE
        ↓
EARLY-WARNING CANDIDATE
```

Do not use the segment alone to predict chronic default.

Use the approved chronic-risk model.

---

# Segment Monitoring

Monitor:

* segment size,
* recoverable exposure,
* payment probability,
* collection rate,
* transition rate,
* chronic-default conversion,
* treatment response,
* channel cost,
* model drift,
* data quality,
* and segment stability.

Alert when:

* segment size changes materially,
* segment payment behavior changes materially,
* response to treatment changes,
* or a segment's historical treatment is no longer effective.

---

# Consumer-Level Output

When a single account is requested, return:

```text id="8x5h1v"
PAYMENT_BEHAVIOR_SEGMENT: <segment>
SEGMENT_CONFIDENCE: high | medium | low
SEGMENT_TREND: IMPROVING | STABLE | DETERIORATING | INSUFFICIENT_HISTORY
RECOMMENDED_TREATMENT: <action>
```

Then provide:

## Evidence

State:

* observation window,
* payment cycles,
* on-time payments,
* late payments,
* unpaid cycles,
* recent trajectory,
* current account status,
* and relevant dispute/arrangement information.

Use counts and dates.

## Why this segment

Explain which behavioral rule caused the assignment.

Do not provide a vague narrative.

Example:

> 10 of the last 12 bills were paid, with payment occurring after the due date in 9 cycles. The account therefore meets the configured RELIABLE_BUT_SLOW definition.

## What points the other way

Mandatory.

Examples:

* recent missed cycle,
* recent payment improvement,
* incomplete history,
* active dispute,
* or inconsistent account-status evidence.

## Recommended treatment

Use the approved collection-action recommendation where available.

## What is not established

State what the segment does not prove.

Examples:

* payment behavior does not establish ability to pay;
* late payment does not establish unwillingness to pay;
* a chronic segment does not establish intent;
* vacancy cannot be inferred from low consumption alone.

---

# Portfolio Output

For portfolio segmentation, begin with:

```text id="l0z8gq"
SEGMENTATION_DATE: <date>
POPULATION: <accounts>
SEGMENTATION_VERSION: <version>
```

Then provide the segment breakdown.

For each segment include:

* accounts,
* recoverable exposure,
* mean payment probability,
* collection performance,
* recent trend,
* recommended treatment,
* and operational implication.

Example:

| Segment               | Accounts | Recoverable exposure | Mean payment probability | Trend                | Treatment           |
| --------------------- | -------: | -------------------: | -----------------------: | -------------------- | ------------------- |
| Stable on-time        |  sourced |              sourced |                  sourced | Stable               | No action           |
| Reliable but slow     |  sourced |              sourced |                  sourced | Stable               | Reminder            |
| Recently deteriorated |  sourced |              sourced |                  sourced | Deteriorating        | Early intervention  |
| Chronic default       |  sourced |              sourced |                  sourced | Stable/Deteriorating | Targeted escalation |
| Disputed              |  sourced |              sourced |                  sourced | N/A                  | Resolve             |
| Premises vacated      |  sourced |              sourced |                  sourced | N/A                  | Verify/resolve      |
| New connection        |  sourced |              sourced |                  sourced | Insufficient         | Verify setup        |

Every number must be sourced.

---

# Required Portfolio Narrative

After the table, answer:

### Where is the money?

Which segments hold the greatest recoverable exposure?

### Where is the recoverability?

Which segments historically convert the greatest share of exposure into collection?

### Where is behavior changing?

Which segments are growing or deteriorating?

### Where is intervention most valuable?

Which segments contain accounts for which intervention is likely to change the outcome?

### Where should the utility avoid spending?

Which segments are receiving expensive treatment despite little evidence of incremental benefit?

---

# Segmentation and Expected Recovery

For campaign decisions, do not rank segments solely by:

`recoverable exposure`

or:

`payment probability`.

Use the approved expected-recovery framework.

Conceptually:

`expected recovery = recoverable exposure × payment probability`

Then, where available:

`incremental campaign recovery = approved uplift × recoverable exposure`

The action optimizer should incorporate intervention cost and constraints.

---

# Protected Attributes and Proxy Controls

Segmentation must not use:

* caste,
* religion,
* gender,
* ethnicity,
* disability,
* health status,
* political affiliation,
* or other protected characteristics.

Do not use obvious proxies for these attributes.

Do not use locality as a proxy for:

* income,
* socioeconomic status,
* ethnicity,
* caste,
* or presumed ability to pay.

Category may be used only where it has a legitimate operational, legal, or arithmetic role.

---

# No Character Labels

Never describe segments as:

* good consumers,
* bad consumers,
* irresponsible consumers,
* poor consumers,
* wealthy consumers,
* unwilling payers,
* dishonest consumers,
* difficult customers.

Use behavioral language:

* paid late,
* missed two cycles,
* payment behavior deteriorated,
* arrangement was not maintained,
* dispute remains unresolved.

The account is being classified.

The person is not.

---

# Source Discipline

Every numerical claim must have a source.

Preferred format:

```text id="8m1zqk"
[segment chronic_default: 329,770 accounts, ₹559 cr recoverable]
[segment reliable_but_slow: sourced]
[payment_model:v4.2: mean probability 0.84]
[collection_campaign: CAM-2026-03: 5,000 visits, ₹48.2 L recovered]
[segmentation:PB-SEG-v3.1]
```

Do not invent:

* segment counts,
* balances,
* probabilities,
* response rates,
* treatment costs,
* transition rates,
* or recovery amounts.

---

# Audit Trail

For every segment assignment retain:

* account identifier,
* segmentation timestamp,
* observation window,
* source data snapshot/version,
* segment definition/version,
* features used,
* segment assigned,
* confidence,
* prior segment,
* treatment recommendation,
* downstream action,
* and eventual outcome.

Segment assignments should be reproducible.

---

# Model and Rule Governance

If the segmentation is deterministic, version the rules.

If machine-learned, version:

* model,
* training population,
* feature definitions,
* thresholds,
* validation period,
* and deployment date.

Changes in segment definitions must not silently rewrite historical segment assignments.

---

# Human Review

Human review is appropriate when:

* account status is contradictory,
* dispute status is unclear,
* vacancy evidence conflicts,
* a new account has a billing anomaly,
* a segment assignment would trigger significant customer-impacting action,
* or the model/rules have low confidence.

The segmentation itself may be automated.

Customer-impacting enforcement remains governed by the utility's approved workflow.

---

# Quality Gate

Before returning a segmentation result, verify:

* [ ] Population and cutoff date are explicit.
* [ ] Observation window is explicit.
* [ ] Segment definitions are deterministic.
* [ ] Segments are mutually exclusive unless explicitly multi-label.
* [ ] Insufficient-history accounts are not forced into mature behavior segments.
* [ ] Payment behavior is separated from consumer characteristics.
* [ ] Disputes are separated from ordinary delinquency.
* [ ] Vacancy requires operational evidence.
* [ ] New-connection arrears are checked for billing/setup issues.
* [ ] Chronic-default definition comes from governed policy.
* [ ] Chronic-risk early warning is not confused with current chronic status.
* [ ] Payment probability comes from the approved model.
* [ ] Segment treatment is connected to the action optimizer.
* [ ] Expensive interventions are not assigned solely because of balance.
* [ ] Segment transitions are monitored.
* [ ] Treatment outcomes are measured.
* [ ] Future information does not leak into historical segmentation.
* [ ] Protected attributes and proxies are excluded.
* [ ] Every numerical figure has a source.
* [ ] Segment assignments are auditable and versioned.
* [ ] Customer-impacting actions remain subject to required human/policy controls.

---

# Architecture

```text id="8d6k4m"
BILLING / PAYMENT / ACCOUNT DATA
              │
              ├── PAYMENT HISTORY
              ├── PAYMENT TIMING
              ├── DELINQUENCY
              ├── DISPUTES
              ├── ARRANGEMENTS
              ├── CONNECTION STATUS
              └── ACCOUNT EVENTS
                       │
                       ▼
             DATA QUALITY / VALIDATION
                       │
                       ▼
           PAYMENT BEHAVIOR SEGMENTER
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
   BEHAVIORAL       ACCOUNT STATE    TRAJECTORY
     STATE              │                │
       │                │                │
       └────────────────┼────────────────┘
                        ▼
               SEGMENT PROFILE
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
     CHRONIC-RISK MODEL     PAYMENT PROBABILITY
             │                     │
             └──────────┬──────────┘
                        ▼
             COLLECTION ACTION
                 OPTIMIZATION
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
           REMIND      CALL       FIELD
                                   │
                                   ▼
                                 NOTICE
                                   │
                              DISCONNECT
                                   │
                                   ▼
                              COLLECTION
                                   │
                                   ▼
                          OUTCOME / MIGRATION
                                   │
                                   ▼
                         SEGMENT MONITORING
```

The architectural boundary is:

> **Segmentation describes observed payment behavior. Payment probability predicts near-term payment. Chronic-risk modeling predicts persistent-default risk. Action optimization chooses the intervention.**

Do not turn segmentation into a hidden collection score.

---

# Final Principle

The value of segmentation is not knowing that:

> "329,770 accounts are chronic defaulters."

The value is knowing:

> **which accounts behave similarly, which behaviors are changing, how much recoverable money sits in each behavioral state, what treatment historically works for that state, where expensive intervention is being wasted, and which accounts are moving toward a worse state before they get there.**

The operating sequence is:

> **OBSERVE BEHAVIOR → SEGMENT → DETECT TRANSITION → PREDICT PAYMENT/CHRONIC RISK → SELECT TREATMENT → MEASURE RECOVERY → UPDATE SEGMENT**