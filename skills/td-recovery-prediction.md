---
name: td-recovery-prediction
description: >
  Prioritize temporarily disconnected consumer accounts for field recovery, notices, settlement, permanent disconnection, or write-off review using recoverable amount and probability of recovery, while respecting field capacity, evidence quality, regulatory controls, and auditability. modes: * portfolio * consumer * field_planning * pd_review
allowed-tools:
  - buildTDFieldPlan
  - exportTDRecoveryList
  - getBillingHistory
  - getConsumer
  - getConsumptionHistory
  - getDisconnectionRecord
  - getMeterStatus
  - getNoticeHistory
  - getPaymentHistory
  - getSiteSurvey
  - getTDPortfolio
  - getTDRecoveryScore
  - listTDRecoveryPriority
---

# Temporary Disconnection → Permanent Disconnection / Recovery

## Purpose

Use AI to convert a large Temporary Disconnection (TD) book into an
intelligence-led recovery programme.

The objective is **not** to maximize the amount of outstanding debt on paper.

The objective is:

> **Prioritize cases where the amount that can realistically be recovered is
> high and the probability of successful recovery is high.**

The system combines, where available:

* outstanding amount
* legally/reasonably recoverable amount
* days since disconnection
* payment history
* meter status
* site-survey findings
* restoration history
* post-disconnection consumption
* previous notices
* consumer category
* premises/occupancy evidence
* geographic/operational context
* prior field outcomes
* dispute/status information

The primary output is a:

**RECOVERY PRIORITY SCORE: 0–100**

The score is a **field-prioritization aid**, not a determination that money is
legally recoverable and not a substitute for authorized DISCOM decisions.

---

# 1. Operating Modes

## Mode A — Portfolio

If the request concerns:

* the TD book
* a division
* a subdivision
* a field plan
* monthly visit capacity
* recovery targets
* PD review
* portfolio statistics
* export
* prioritization

work across the portfolio.

Start with:

`getTDPortfolio`

Then retrieve supporting information as required.

Typical workflow:

```text
getTDPortfolio
      ↓
validate data quality
      ↓
identify legally / operationally recoverable balance
      ↓
identify suppressed / explained accounts
      ↓
evaluate recovery probability
      ↓
rank TD accounts
      ↓
apply field capacity and operational constraints
      ↓
buildTDFieldPlan
      ↓
exportTDRecoveryList
```

---

## Mode B — One Account

If the user provides a consumer/account number, work only on that account.

Retrieve all relevant evidence before scoring.

Preferred evidence sources:

```text
getTDAccount
getBillingHistory
getPaymentHistory
getConsumptionHistory
getMeterStatus
getSiteSurveys
getRestorationHistory
getNoticeHistory
getConsumerCategory
getDisputeStatus
getInspectionHistory
```

Only use tools that actually exist in the connected DISCOM environment.

Never fabricate unavailable information.

---

# 2. Core Principle

The system must keep two concepts separate:

### A. Recoverable Amount

How much money can realistically and legitimately be pursued through the
available recovery route?

### B. Recovery Probability

How likely is successful recovery if the DISCOM takes the recommended action?

The final priority is a function of both.

Conceptually:

```text
Recovery Priority
    ≈
Recoverable Amount
×
Probability of Recovery
×
Actionability
```

The implementation may use a calibrated scoring model rather than literally
multiplying the three values.

The important rule is:

> **A large debt with almost no realistic recovery prospect must not automatically
> outrank a smaller debt that is highly recoverable.**

---

# 3. Do Not Confuse Ledger Balance With Recoverable Balance

The ledger balance is only the starting point.

Before ranking an account, identify amounts that may require separate treatment,
including where applicable:

* disputed amounts
* amounts subject to legal restrictions
* statute-barred amounts
* duplicate postings
* reversed bills
* billing corrections
* amounts associated with a period when the consumer demonstrably did not
  occupy the premises
* amounts already settled
* amounts under an approved payment arrangement
* amounts already referred to another recovery process
* post-demolition amounts that are not realistically collectible
* amounts under active adjudication
* other DISCOM-defined exclusions

Never silently subtract anything.

Show:

```text
Ledger outstanding:       ₹X
Less: disputed:           ₹Y
Less: barred:             ₹Z
Less: other exclusions:   ₹A
--------------------------------
Recoverable amount:       ₹B
```

Every deduction must have a source and reason.

If legal recoverability cannot be determined from the available data:

> Do not invent a legal conclusion.

Mark the amount:

`RECOVERABILITY_REVIEW_REQUIRED`

---

# 4. Recovery Probability

Recovery probability estimates whether a meaningful recovery action is likely
to produce payment.

It should use evidence such as:

### Strong positive evidence

* confirmed occupied premises
* operating business
* recent payment activity
* previous successful settlement
* active consumer engagement
* recent restoration followed by payment
* current consumption after supposed disconnection
* recent contact with the consumer
* successful historical recovery at the same premises
* valid contact/address information
* site survey confirming an active premises
* consumer responding to notices

### Strong negative evidence

* demolished premises
* permanently vacant premises confirmed by survey
* premises untraceable
* meter removed and no active premises
* repeated failed visits
* no occupancy evidence for a prolonged period
* deceased consumer where no successor/occupancy information exists
* business permanently closed
* site survey confirms premises no longer exists
* long TD period combined with no consumption and no occupancy evidence
* unresolved identity/address problem

Do not infer vacancy merely because consumption is zero.

Zero consumption can also result from:

* meter communication failure
* defective meter
* supply interruption
* meter removal
* billing-system issue
* seasonal occupancy
* temporary closure
* legitimate non-use

The system must distinguish:

**observed absence of consumption**

from

**confirmed absence of premises/occupancy.**

---

# 5. Evidence Hierarchy

When evidence conflicts, use the following hierarchy.

## Tier 1 — Physical/site evidence

Highest priority:

* site survey
* premises status
* meter physically present/removed
* current occupancy
* business operating status
* demolition
* physical restoration
* field photographs where authorized
* authorized inspection findings

## Tier 2 — Meter and network evidence

* meter status
* meter reads
* restoration events
* post-TD consumption
* meter replacement
* communication status
* tamper events where relevant
* service status

## Tier 3 — Transactional evidence

* payments
* settlements
* notices
* disputes
* previous recovery actions
* payment arrangements

## Tier 4 — Account/master data

* consumer category
* sanctioned load
* address
* connection status
* billing information

## Tier 5 — Statistical inference

* behavioral patterns
* peer comparisons
* geographic patterns
* inferred probability

Statistical evidence must never override strong contradictory physical
evidence.

---

# 6. Days Since Disconnection

TD age is an important feature but must never dominate the decision.

Long TD duration has two competing effects:

### Potentially positive

* larger accumulated balance
* more incentive for formal recovery action

### Potentially negative

* premises may have become vacant
* business may have closed
* consumer may have relocated
* recovery trail may have gone cold
* asset/premises condition may have changed

Therefore:

> **TD age is not equivalent to recovery probability.**

Examples:

```text
420 days TD + occupied shop + recent consumption
→ potentially high priority

420 days TD + demolished premises + no occupant
→ potentially very low recovery priority

90 days TD + active business + strong payment history
→ potentially high priority
```

---

# 7. Restoration Risk

Restoration after TD is an important signal.

However, restoration must be independently verified.

Do not rely solely on a field such as:

`RESTORED = YES`

Check, where available:

* meter status
* consumption history
* restoration records
* work orders
* meter reads
* authorized reconnection records
* billing events

A post-TD consumption signal may indicate that the premises is active, but it
does not by itself establish unauthorized restoration.

If unauthorized restoration is suspected:

* state what the data shows
* identify the evidence
* recommend the appropriate authorized verification
* do not declare an offense based solely on consumption data

---

# 8. Payment History

Payment history before TD should inform probability.

Useful features include:

* number of payments
* payment frequency
* average payment amount
* most recent payment
* payment regularity
* history of partial settlement
* history of broken payment arrangements
* previous successful recovery
* arrears accumulation pattern

Do not make simplistic assumptions such as:

> "Never paid before = will never pay."

Instead, treat it as one evidence component.

A consumer with a history of regular payment followed by a sudden financial
shock may have a different recovery probability from a consumer with years of
non-payment.

---

# 9. Site Survey

Site survey evidence is one of the most valuable inputs.

Possible survey states:

```text
OCCUPIED
OPERATING_BUSINESS
RESIDENTIAL_OCCUPIED
VACANT
LOCKED
DEMOLISHED
PREMISES_NOT_FOUND
BUSINESS_CLOSED
UNDER_CONSTRUCTION
UNKNOWN
```

Do not convert `UNKNOWN` into `VACANT`.

Where a survey is old, reduce confidence.

Example:

```text
Survey date: 2024-06-10
Current date: 2026-09-02
Status: OCCUPIED
```

This is historical evidence, not proof of current occupancy.

The skill should explicitly state:

> The older the survey, the less confidence it provides about present
> recoverability.

---

# 10. Consumer Category

Consumer category may influence expected recovery mechanics.

Examples:

* domestic
* commercial
* industrial
* agricultural
* institutional
* temporary
* public service
* other DISCOM-defined classes

Category should be used only where it has a demonstrable operational relationship
to recovery.

Never assume that one consumer category is inherently dishonest, unwilling to
pay, or less deserving of service.

Category is a recovery-planning feature, not a character judgment.

---

# 11. Geographic Information

Geography can be useful for:

* field routing
* visit batching
* travel cost
* subdivision workload
* local operational planning
* identifying areas with unusually high unresolved TD cases

But geography must not become an unsupported proxy for individual willingness to
pay.

### Important rule

Do not increase an individual's recovery probability merely because:

* the area has high arrears
* nearby consumers have low recovery
* the locality historically performs poorly
* the feeder has high losses

Area statistics may help plan field operations.

They should not be treated as evidence about an individual's intent or
character.

---

# 12. Field Capacity Optimization

The field team has finite capacity.

Example:

```text
TD portfolio:        40,000
Monthly capacity:     2,500
```

Do not simply select the 2,500 highest raw scores if operational constraints
make that inefficient.

The field plan should consider:

* recovery priority
* recoverable amount
* recovery probability
* action required
* geographic clustering
* travel time
* duplicate visits
* recent unsuccessful visits
* statutory/service deadlines
* survey requirements
* field-team specialization
* consumer contact requirements
* safety constraints
* inspection capacity

The objective is:

> **Maximize expected recovery and decision value per field visit.**

A visit can create value even when payment is not immediately collected if it
resolves whether an account should move to:

* PD conversion
* write-off review
* settlement
* further recovery
* address correction
* meter investigation

Therefore distinguish:

### COLLECTION VISIT

Primary objective is payment/recovery.

### CONFIRMATION VISIT

Primary objective is determining whether the premises/consumer remains
recoverable.

### PD REVIEW VISIT

Primary objective is confirming that the conditions for permanent disconnection
are satisfied.

---

# 13. Field Plan Composition

Where the portfolio contains many accounts with no recent survey, do not allocate
100% of field capacity to the highest-confidence recovery cases.

The plan may contain a controlled mix:

```text
High-confidence recovery
+
High-value uncertain cases
+
Confirmation cases
+
PD confirmation cases
```

The exact mix should be configurable by the DISCOM.

Example:

```text
2,500 monthly visits

1,700 collection-focused
  500 confirmation
  300 PD/recovery-status verification
```

The system must explain the allocation.

---

# 14. Scoring Model

The exact production model should be calibrated against historical outcomes.

The score must not be presented as a mathematically precise probability unless
the model has actually been calibrated to produce probabilities.

A recommended conceptual structure is:

```text
Recovery Priority
    |
    +-- Recoverable amount
    |
    +-- Recovery probability
    |
    +-- Evidence quality
    |
    +-- Actionability
    |
    +-- Time sensitivity
```

Possible feature groups:

| Feature                   | Role                     |
| ------------------------- | ------------------------ |
| Recoverable amount        | Economic value           |
| Site occupancy            | Recovery probability     |
| Operating status          | Recovery probability     |
| Payment history           | Recovery probability     |
| Restoration evidence      | Activity/recovery signal |
| Post-TD consumption       | Premises activity signal |
| Survey recency            | Evidence quality         |
| Notice response           | Engagement               |
| Previous recovery success | Behavioral evidence      |
| TD age                    | Time/context             |
| Consumer category         | Operational context      |
| Geography                 | Routing/context          |
| Dispute status            | Actionability            |
| Data quality              | Confidence adjustment    |

---

# 15. Score Bands

Use the following as default operational bands.

|  Score | Interpretation                    | Typical action                   |
| -----: | --------------------------------- | -------------------------------- |
| 85–100 | Very high recovery priority       | FIELD_VISIT                      |
|  70–84 | High recovery priority            | FIELD_VISIT / NOTICE             |
|  50–69 | Moderate / uncertain              | NOTICE / CONFIRMATION            |
|  30–49 | Low recovery probability or value | MONITOR / PD_REVIEW              |
|  15–29 | Very low recovery prospect        | PD_CONVERSION / WRITE_OFF_REVIEW |
|   0–14 | No meaningful recovery prospect   | WRITE_OFF_REVIEW / NO_ACTION     |

These bands are **operational defaults**, not legal thresholds.

They should be configurable.

---

# 16. Score Caps and Guardrails

The following controls are mandatory.

## No evidence

If critical evidence is missing:

```text
CONFIDENCE = low
```

Do not create false precision.

## No site evidence

A case with no site evidence can still rank highly, but the report must say:

> Recovery probability is inferred rather than site-confirmed.

## Very old survey

If the only occupancy evidence is stale:

```text
reduce confidence
```

Do not automatically classify the premises as vacant.

## Large amount alone

A large ledger balance cannot produce a high recovery score by itself.

## TD age alone

TD age cannot produce a high score by itself.

## Zero consumption alone

Zero consumption cannot establish vacancy.

## Geography alone

Geography cannot establish recovery likelihood.

## Consumer category alone

Category cannot produce a high or low recovery probability.

---

# 17. PD Conversion

`PD_CONVERSION` is a decision state, not simply a more aggressive recovery action.

Recommend PD conversion only when the available evidence supports:

1. TD duration has reached the applicable DISCOM policy threshold.
2. Recovery probability is sufficiently low.
3. Site/premises evidence supports the conclusion.
4. Required notices/processes have been completed.
5. There is no active dispute or process that prevents conversion.
6. The account is not merely suffering from missing or poor-quality data.

If these conditions cannot be established:

```text
PD_CONVERSION = NOT_READY
```

Do not recommend PD merely because the account is old.

---

# 18. Write-Off Review

A large balance with a cold recovery trail should not automatically receive a
field visit.

Recommend:

`WRITE_OFF_REVIEW`

when:

* recoverable amount is uncertain or low
* recovery probability is very low
* premises is confirmed gone/untraceable
* recovery actions have been exhausted
* applicable policy allows review
* further field activity is unlikely to create sufficient value

A write-off recommendation must never mean:

> "The debt is legally uncollectible."

Unless the system has authoritative evidence establishing that fact.

Use:

> "Recommended for write-off review under applicable DISCOM policy."

---

# 19. Notices

A notice may be more efficient than a field visit where:

* the consumer is contactable
* address is valid
* recovery probability is moderate
* amount is material
* physical verification is not yet necessary
* policy permits notice-first recovery

The system should explain why:

```text
NOTICE
because contactability is high,
recoverable amount is ₹X,
and physical evidence does not currently justify a field visit.
```

---

# 20. Settlement Offers

Recommend:

`SETTLEMENT_OFFER`

only where:

* the DISCOM policy supports settlement
* the account is eligible
* the amount is eligible
* there is no blocking dispute/process
* the consumer has demonstrated engagement or payment ability
* the proposed route is authorized

Never invent a discount or settlement percentage.

---

# 21. Required One-Account Output

The first three lines must be exactly:

```text
RECOVERY_PRIORITY: 0-100
RECOMMENDED_ACTION: FIELD_VISIT | NOTICE | PD_CONVERSION | SETTLEMENT_OFFER | WRITE_OFF_REVIEW | NO_ACTION
CONFIDENCE: high | medium | low
```

Then provide:

## Recoverable Amount

Show:

* ledger outstanding
* deductions
* reason for every deduction
* recoverable amount used in ranking
* date of balance

Example:

```text
Ledger outstanding: ₹85,000
Disputed amount: ₹5,000
Other excluded amount: ₹0
Recoverable amount used: ₹80,000
```

Every number must have a source.

---

## Recovery Probability

State the evidence supporting the recovery assessment.

Separate:

```text
Evidence supporting recovery
Evidence reducing recovery probability
Evidence that is unknown
```

Never hide uncertainty.

---

## How the Score Was Reached

Always show:

```text
Recoverable amount: ₹X
Estimated recovery probability: Y
Evidence quality: HIGH/MEDIUM/LOW
Actionability: HIGH/MEDIUM/LOW

Final recovery priority: Z/100
```

If the underlying model does not produce a calibrated probability, say:

> "Recovery probability is a model-derived likelihood score and should not be
> interpreted as a calibrated percentage."

Do not call `0.82` an "82% probability" unless the model is actually calibrated.

---

## Recommended Action

State one primary action.

Then explain:

* why this action is preferred
* what evidence supports it
* why the next-best action was not selected

Example:

```text
Recommended: FIELD_VISIT

Reason:
₹80,000 is recoverable, the premises was confirmed occupied recently,
post-TD consumption indicates continued activity, and the consumer has
previously made partial payments.

A field visit is preferred over PD conversion because current evidence
supports continued recovery potential.
```

---

## What Would Change the Decision

Identify the single missing fact that would most affect the ranking.

Examples:

* current site survey
* current occupancy status
* confirmation of demolition
* dispute resolution
* current meter status
* current payment arrangement
* verification of post-TD consumption
* confirmation of premises identity

Do not simply list every missing field.

Identify the **highest-value missing evidence**.

---

# 22. Portfolio Output

For portfolio requests, provide:

## Portfolio Headline

Example:

```text
40,000 TD accounts reviewed.
2,500 visits available this month.
₹X recoverable balance represented in the proposed field plan.
Expected recovery opportunity: ₹Y.
```

Do not invent these numbers.

Retrieve them from the portfolio tools.

---

## Portfolio Breakdown

Report:

* total TD accounts
* total ledger outstanding
* total recoverable amount
* accounts with unresolved recoverability
* accounts with recent site evidence
* accounts with stale/no site evidence
* high-priority accounts
* medium-priority accounts
* low-priority accounts
* PD candidates
* write-off-review candidates
* notice candidates
* settlement candidates

---

# 23. Field Plan Quality

When `buildTDFieldPlan` is available, use it.

The field plan should include:

* consumer/account number
* priority
* recommended action
* recoverable amount
* recovery probability / model likelihood where valid
* evidence confidence
* reason codes
* latest survey date
* latest relevant payment
* TD date
* geographic routing information
* required field activity

Do not reproduce the entire field list in the conversational response.

Use:

`exportTDRecoveryList`

for the operational file.

---

# 24. Field Plan Selection Logic

When selecting a finite number of visits:

```text
1. Remove accounts that are not actionable.
2. Remove accounts already resolved.
3. Remove accounts blocked by active process/dispute.
4. Separate collection, confirmation, and PD-review cases.
5. Rank by expected recovery value and decision value.
6. Apply field capacity.
7. Optimize geographic batching.
8. Avoid unnecessary repeat visits.
9. Verify mandatory operational constraints.
10. Produce the final field plan.
```

Do not equate:

```text
highest score = automatically first visit
```

when operational constraints materially change the expected value.

---

# 25. Explainability / Reason Codes

Every scored account should have machine-readable reason codes.

Examples:

```text
HIGH_RECOVERABLE_BALANCE
RECENT_OCCUPANCY_CONFIRMED
POST_TD_CONSUMPTION
RECENT_PAYMENT_HISTORY
RECENT_SUCCESSFUL_RECOVERY
STALE_SITE_SURVEY
NO_OCCUPANCY_EVIDENCE
DEMOLISHED_PREMISES
LONG_TD_DURATION
ACTIVE_DISPUTE
METER_STATUS_UNCERTAIN
```

Reason codes must describe evidence, not conclusions.

Good:

```text
POST_TD_CONSUMPTION_DETECTED
```

Bad:

```text
CONSUMER_ILLEGALLY_USING_POWER
```

unless that fact has actually been established through an authorized process.

---

# 26. Data Quality

Before scoring, check:

### Account integrity

* duplicate account
* incorrect TD date
* inconsistent status
* closed account
* merged account
* transferred account

### Billing integrity

* estimated bills
* duplicate bills
* reversed bills
* abnormal billing cycle
* meter replacement
* meter multiplier changes

### Consumption integrity

* missing intervals
* communication outages
* zero reads
* meter rollover
* estimated reads
* restoration timing mismatch

### Survey integrity

* missing survey
* stale survey
* conflicting survey results
* unidentified premises

### Payment integrity

* reversed payment
* pending payment
* settlement adjustment
* duplicate transaction

If data quality is poor enough to affect the decision:

```text
CONFIDENCE = low
```

and state what must be corrected.

---

# 27. Contradictory Evidence

Never average contradictory evidence into a meaningless score.

Example:

```text
Billing system: TD
Meter system: active consumption
Site survey: premises occupied
Work order: authorized restoration
```

Do not conclude:

> "High restoration risk."

Instead:

> "Consumption after the TD date is present, but an authorized restoration
> work order exists. The post-TD consumption therefore cannot be treated as
> evidence of unauthorized restoration."

The contradiction itself is valuable.

---

# 28. Historical Outcomes

Where inspection/recovery outcomes are available, use them for model
calibration.

Useful outcomes include:

```text
PAYMENT_COLLECTED
PARTIAL_PAYMENT
SETTLEMENT
CONSUMER_UNAVAILABLE
PREMISES_VACANT
PREMISES_DEMOLISHED
ACCOUNT_NOT_FOUND
METER_ISSUE
DISPUTE_CONFIRMED
PD_COMPLETED
WRITE_OFF_REVIEW
NO_RECOVERY
OTHER
```

Do not treat historical outcomes as automatically correct labels.

Where outcomes were recorded inconsistently, flag label quality.

---

# 29. Feedback Loop

After every field action, capture:

```text
predicted priority
recommended action
actual field outcome
amount recovered
visit cost/time
premises status
consumer engagement
new evidence
final account disposition
```

Use this information to:

* calibrate recovery probability
* measure precision
* identify false positives
* identify missed high-value cases
* improve field routing
* improve survey targeting
* detect model drift

The model should learn from outcomes.

---

# 30. Key Performance Indicators

Track:

### Recovery

* recovery amount
* recovery rate
* recovery per visit
* recovery per field-hour
* recovery per ₹ of field cost

### Prioritization

* top-decile recovery yield
* top-quartile recovery yield
* precision of high-priority cases
* percentage of visits producing actionable outcomes

### PD

* number of PD conversions
* percentage subsequently recovered
* number of inappropriate PD recommendations

### Data quality

* percentage with recent survey
* percentage with missing meter data
* percentage with unresolved account status
* percentage with low-confidence scores

### Model quality

* calibration
* ranking quality
* false-positive rate
* false-negative rate
* drift over time

The most important business KPI is not:

> "How many accounts did AI rank?"

It is:

> **"How much additional recoverable value did intelligence-led field activity
> generate compared with the previous allocation method?"**

---

# 31. Fairness and Consumer Protection

Do not use protected or sensitive personal characteristics to estimate
willingness to pay or recovery probability.

Do not use:

* religion
* caste
* race/ethnicity
* political affiliation
* health information
* disability
* other protected/sensitive characteristics

as recovery predictors.

Geography and consumer category must be used only for legitimate operational
purposes and must not become hidden proxies for protected characteristics.

The system must not produce statements such as:

```text
Consumer is unlikely to pay because of the neighborhood.
```

or:

```text
This consumer category is historically dishonest.
```

The system predicts operational recovery likelihood, not personal character.

---

# 32. Privacy and Security

Use the minimum consumer information necessary.

Do not expose unnecessary:

* personal identifiers
* phone numbers
* addresses
* payment details
* identity documents

in narrative output.

Operational exports should follow the DISCOM's access controls.

Every scoring decision should be auditable.

---

# 33. Audit Trail

For every recommendation record:

```text
account_id
score
recommended_action
confidence
model_version
data_snapshot_date
feature_values
reason_codes
recoverable_amount
recovery_probability_or_model_score
evidence_sources
suppression_rules
human_override
final_action
field_outcome
```

A later reviewer must be able to reconstruct:

> **Why did this account receive this score on this date?**

---

# 34. Suppression Rules

Do not send an account to field recovery when it is already resolved.

Suppress or route separately:

* paid accounts
* settled accounts
* closed accounts
* active disputes where field recovery is inappropriate
* accounts already under an approved recovery process
* duplicate accounts
* accounts already visited within the configured cooldown period
* accounts with completed PD
* accounts already referred to another authorized process

Every suppression should have a reason.

Example:

```text
SUPPRESSED:
Approved payment arrangement active.
Next review date: 2026-10-15.
```

---

# 35. Portfolio Insight: Unknown Is a Segment

Do not hide uncertainty.

If:

```text
20,817 / 40,000
```

have never been surveyed, report it prominently.

These accounts are not:

* high recovery
* low recovery
* vacant
* unrecoverable

They are:

> **UNRESOLVED RECOVERABILITY**

The field programme should consider whether some capacity should be dedicated
to resolving this uncertainty.

This creates a second optimization objective:

```text
COLLECT MONEY
+
REDUCE UNCERTAINTY
```

A confirmation visit that changes an account from "unknown" to "demolished" can
prevent years of unnecessary recovery effort.

---

# 36. Example

Synthetic example only:

```text
RECOVERY_PRIORITY: 91
RECOMMENDED_ACTION: FIELD_VISIT
CONFIDENCE: high

## Recoverable Amount

Ledger outstanding: ₹85,000
Disputed amount: ₹0
Other excluded amount: ₹0
Recoverable amount: ₹85,000

Source:
[ledger 2026-08-31]

## Recovery Probability

Evidence supporting recovery:

- Premises confirmed occupied in recent survey.
- Consumer made payments before TD.
- Consumption detected after the TD date.
- No completed PD process.

Sources:
[survey 2026-07-14]
[payment history 2025-01 to 2026-03]
[consumption 2026-06 to 2026-08]
[TD record 2026-03-02]

Evidence reducing recovery probability:

- TD has remained unresolved for 184 days.

## How the Score Was Reached

Recoverable amount: ₹85,000
Recovery likelihood: high
Evidence quality: high
Actionability: high

Final recovery priority: 91/100

## Recommended Action

FIELD_VISIT.

The account combines a material recoverable balance with recent evidence that
the premises remains active. A field visit is expected to have greater recovery
value than passive monitoring.

## What Would Change It

A current site survey confirming that the premises is vacant or demolished would
materially reduce the recovery priority.
```

---

# 37. Portfolio Example

Synthetic example:

```text
TD PORTFOLIO

Accounts:                    40,000
Monthly field capacity:       2,500
Ledger outstanding:           ₹149 cr
Recoverable balance:          ₹135 cr

High-priority recovery cases:  X
Confirmation cases:            Y
PD-review cases:               Z
Write-off-review cases:        A

Proposed field plan:           2,500
Expected recovery opportunity: ₹X
```

The system must retrieve the actual figures.

Never use the example values as defaults.

---

# 38. What the AI Must Never Do

Never:

* invent a recovery probability
* invent a site survey
* infer vacancy from zero consumption alone
* treat TD age as proof of recoverability
* treat ledger balance as recoverable balance
* declare a consumer unwilling to pay without evidence
* use neighborhood as evidence of individual behavior
* use protected characteristics
* recommend PD solely because an account is old
* recommend a field visit solely because the balance is large
* declare an unauthorized restoration without supporting evidence
* invent settlement terms
* invent legal conclusions
* hide uncertainty
* fabricate citations
* fabricate tool results
* silently ignore conflicting evidence
* overwrite a human decision without authorization

---

# 39. Language Rules

Use:

> "Recovery probability is high based on..."

Not:

> "The consumer will pay."

Use:

> "The premises was recorded as occupied."

Not:

> "The consumer definitely lives there."

Use:

> "Post-TD consumption was observed."

Not:

> "The consumer illegally restored supply."

Use:

> "Recommended for PD conversion review."

Not:

> "The debt is gone."

Use:

> "Recoverable amount estimated at ₹X based on the available account data."

Not:

> "₹X is definitely collectible."

The report should be written as though:

> **the consumer, regulator, auditor, and DISCOM legal team may all read it.**

---

# 40. Final Decision Framework

For every account, reason through this sequence:

```text
1. Is the account genuinely TD?
        ↓
2. What is the ledger balance?
        ↓
3. What portion is reasonably/actionably recoverable?
        ↓
4. Is the premises still present?
        ↓
5. Is the premises occupied/operating?
        ↓
6. Is there evidence of current activity?
        ↓
7. What does payment history show?
        ↓
8. What does the site survey show?
        ↓
9. Are there disputes or process blockers?
        ↓
10. What is the evidence quality?
        ↓
11. What is the recovery likelihood?
        ↓
12. What is the expected value of a field action?
        ↓
13. Is field capacity available?
        ↓
14. Should the account be:
       FIELD_VISIT
       NOTICE
       SETTLEMENT_OFFER
       PD_CONVERSION
       WRITE_OFF_REVIEW
       NO_ACTION
```

---

# 41. Final Principle

The purpose of this skill is not to create a bigger recovery list.

It is to create a **better recovery list**.

The AI should help the DISCOM answer four questions:

> **How much can we realistically recover?**

> **How likely are we to recover it?**

> **What action has the highest expected value?**

> **Which limited field visit should happen first?**

The ideal output is therefore not:

```text
₹85,000 outstanding → visit
```

It is:

```text
₹85,000 recoverable
+
high evidence-backed recovery likelihood
+
active premises
+
actionable field opportunity
=
HIGH RECOVERY PRIORITY
```

And equally importantly:

```text
₹4,00,000 ledger balance
+
demolished premises
+
no occupant
+
no realistic recovery path
=
LOW FIELD PRIORITY
→ PD / WRITE-OFF REVIEW
```

The system's value comes from making that distinction consistently,
transparently, and at portfolio scale.

## Why recoverable is not the ledger balance

`getTDRecoveryScore` returns a deduction called `statute_barred_56_2`, and it
is not a modelling adjustment.

Amounts first shown as due more than two years ago are **barred from recovery
as arrears under §56(2) of the Electricity Act 2003**, unless they have been
continuously shown as recoverable. That money is not unlikely to be collected —
the utility is **not entitled to pursue it**.

Rank on the recoverable figure, and say what came off and why. A programme
built on the ledger balance sends recovery teams after money that cannot
lawfully be demanded, and every one of those visits is a complaint waiting to
be made.

Disputed amounts come off for a different reason: the figure itself may be
wrong, and recovery action on a disputed balance generates regulatory exposure.
