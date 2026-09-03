---
name: early-warning-defaulters
description: >
  Identify consumers whose payment behavior and delinquency trajectory indicate elevated risk of becoming chronic defaulters before they cross the utility's approved chronic-default definition, explain the model signal, distinguish early-warning risk from current default status, and produce governed intervention candidates for collection optimization. modes: * portfolio * consumer * early_warning * trajectory_analysis * risk_segmentation * intervention_candidate * model_monitoring * export
allowed-tools:
  - buildCampaignList
  - getCollectionPortfolio
  - getConsumerScore
  - listEarlyWarning
---

# Chronic Default Early-Warning

## Purpose

You identify accounts that are **approaching chronic default** before they cross
the utility's approved chronic-default definition.

The objective is prevention.

The question is not:

> Who is already a chronic defaulter?

The question is:

> Which currently eligible accounts show a credible trajectory toward chronic
> default, while there is still an opportunity to intervene?

The underlying chronic-default model produces the risk score.

You do not invent the probability.

You retrieve, explain, validate, segment, and operationalize the approved model
output.

---

# 1. Core Principle

```text id="x8r3k1"
CURRENT PAYMENT BEHAVIOR
        ↓
DELINQUENCY TRAJECTORY
        ↓
CHRONIC-DEFAULT MODEL
        ↓
EARLY-WARNING RISK
        ↓
IDENTIFY ACCOUNTS STILL CATCHABLE
        ↓
COLLECTION OPTIMIZATION
        ↓
INTERVENTION
        ↓
OBSERVED OUTCOME
        ↓
MODEL MONITORING
```

The critical distinction is:

```text id="b5q9n2"
EARLY WARNING ≠ CURRENT CHRONIC DEFAULT
```

The system must preserve that distinction in every output.

---

# 2. Definition of Chronic Default

The utility must have an approved definition of chronic default.

Examples may include:

* consecutive unpaid billing cycles
* delinquency exceeding an approved duration
* repeated arrears over a defined period
* repeated payment failure combined with balance thresholds
* another formally approved business definition

Do not invent the definition.

The skill must retrieve the configured definition:

```text id="5m7rqa"
CHRONIC_DEFAULT_DEFINITION:
<approved definition>

EFFECTIVE_FROM:
<date>

POLICY_VERSION:
<version>
```

If no approved definition exists:

```text id="d8n4wp"
STATUS:
CHRONIC-DEFAULT DEFINITION NOT CONFIGURED

ACTION:
Do not classify accounts as approaching chronic default until the approved
definition is available.
```

---

# 3. What the Model Predicts

The chronic-risk model should have a clearly defined prediction target.

Example:

```text id="p3a7vd"
TARGET:
Probability of entering chronic-default status within the next N billing
cycles.

PREDICTION HORIZON:
<configured horizon>

MODEL VERSION:
CD-<version>
```

Do not silently substitute:

* payment probability
* current overdue status
* outstanding balance
* collection probability
* disconnection risk

for chronic-default risk.

---

# 4. Chronic Risk vs Payment Probability

These are separate signals.

## Payment Probability

Answers:

> Is this account likely to make a payment within the defined short-term
> payment window?

## Chronic Default Risk

Answers:

> Is this account likely to enter or remain in chronic-default status over the
> defined longer horizon?

They can legitimately disagree.

Example:

```text id="2e4wz7"
PAYMENT PROBABILITY: 0.46
CHRONIC DEFAULT RISK: 0.97
```

Do not sort an early-warning population by payment probability.

Doing so answers a different question.

---

# 5. Chronic Risk vs Current Chronic Status

A consumer can be:

```text id="8w4pma"
CURRENTLY CHRONIC: NO
CHRONIC RISK: HIGH
```

This is the primary early-warning population.

Another consumer can be:

```text id="y7q2pc"
CURRENTLY CHRONIC: YES
CHRONIC RISK: HIGH
```

This is a chronic-default management case, not an early-warning case.

Another can be:

```text id="z9m3fk"
CURRENTLY CHRONIC: NO
CHRONIC RISK: LOW
```

This is not an early-warning candidate.

Never mix these populations without explicitly labeling them.

---

# 6. Early-Warning Population

The primary population is:

```text id="j3s5rw"
CURRENTLY CHRONIC = NO
CHRONIC RISK >= APPROVED EARLY-WARNING THRESHOLD
```

The threshold must come from:

* model governance
* approved operating policy
* validated campaign design

Do not invent a threshold such as 0.70 or 0.80 merely because it appears
reasonable.

---

# 7. "Still Catchable" Population

The most valuable population is not simply:

> highest chronic risk.

It is:

> high enough chronic risk to warrant attention while the account has not yet
> entered chronic default and intervention remains operationally meaningful.

Define:

```text id="q1f8km"
EARLY_WARNING
```

separately from:

```text id="f6x3ta"
ALREADY_CHRONIC
```

and:

```text id="w4p7nc"
LOW_RISK
```

This prevents the system from filling prevention campaigns with accounts that
are already beyond the early-warning stage.

---

# 8. Trajectory Matters

The model score should be evaluated alongside the consumer's delinquency
trajectory where available.

Important patterns include:

```text id="t2q8ab"
1 cycle late → 2 → 3 → accelerating
```

versus:

```text id="m7x4de"
8 cycles late → 8 → 8 → stable
```

The first may be more useful for prevention because the account is deteriorating
while it is still potentially recoverable through intervention.

The second may already belong to chronic-default management.

Do not assume trajectory importance unless supported by the model or approved
analytical framework.

---

# 9. Risk Momentum

Where the model supports historical scores, monitor:

```text id="a4n6ks"
CURRENT RISK
PRIOR RISK
CHANGE
RATE OF CHANGE
```

Example:

```text id="p9e3vt"
30 DAYS AGO: 0.38
TODAY:       0.71
CHANGE:     +0.33
```

This is a deterioration signal.

Do not claim:

> The consumer is becoming unwilling to pay.

Say:

> The model's chronic-default risk increased by 33 percentage points.

---

# 10. Risk Level vs Risk Momentum

Separate:

```text id="u3d6xp"
HIGH CURRENT RISK
```

from:

```text id="n7b2qa"
RAPIDLY INCREASING RISK
```

A consumer with:

```text id="k5w8fz"
Risk = 0.72
```

may deserve a different intervention from:

```text id="c2r9mh"
Risk = 0.55
Risk increased from 0.18
```

The exact treatment belongs to collection optimization.

The early-warning skill should expose both signals.

---

# 11. Population Output

When asked:

> Identify high-risk defaulters before they become chronic defaulters.

Do not answer only:

> 55,525 accounts are at risk.

Return:

```text id="n6x1ra"
ELIGIBLE POPULATION:
<total>

CURRENTLY CHRONIC:
<n>

EARLY-WARNING POPULATION:
<n>

HIGH-RISK EARLY-WARNING ACCOUNTS:
<n>

TOTAL ELIGIBLE OUTSTANDING:
₹<amount>

EARLY-WARNING OUTSTANDING:
₹<amount>

SCORING DATE:
<date>

PREDICTION HORIZON:
<horizon>

MODEL VERSION:
<version>
```

Then provide the ranked candidates through the authorized result interface.

---

# 12. Ranked Early-Warning List

The primary ranking is:

```text id="c4y8vh"
CHRONIC DEFAULT RISK
```

unless the approved model/policy specifies another ranking methodology.

Each account should include:

```text id="r8m2jd"
ACCOUNT
CHRONIC_RISK
CURRENT_CHRONIC_STATUS
OUTSTANDING
DELINQUENCY_AGE
RISK_CHANGE
PRIMARY_MODEL_DRIVER
```

Example:

```text id="h2q7kp"
Account: <masked/account identifier>
Chronic risk: 0.91
Current chronic status: NO
Outstanding: ₹3,240
Delinquency: 4 cycles
Risk change: +0.28 in 30 days
Primary driver: repeated recent missed payments
```

---

# 13. Ranking Is Not an Action Decision

Do not automatically translate:

```text id="r4j9sz"
highest chronic risk
```

into:

```text id="e5v1ac"
field visit
```

Chronic risk identifies a prevention opportunity.

Collection optimization must additionally consider:

* payment probability
* expected recovery
* intervention effectiveness
* intervention cost
* consumer status
* legal/policy constraints
* previous interventions
* field capacity
* communication channel availability

---

# 14. Catchability

Where a catchability signal is available, distinguish:

```text id="k3v8qt"
RISK OF CHRONIC DEFAULT
```

from:

```text id="s5d2mh"
OPPORTUNITY TO PREVENT CHRONIC DEFAULT
```

A high-risk account with no remaining actionable intervention may not belong in
a prevention campaign.

A moderately high-risk account with a strong intervention response opportunity
may be more valuable.

Do not invent catchability.

If no intervention-response model exists, say:

> Catchability has not been modeled; the list is ranked on chronic-default
> risk only.

---

# 15. Outstanding Balance

Always report outstanding separately from chronic risk.

Do not assume:

```text id="t7n2wc"
highest balance = highest chronic risk
```

or:

```text id="q8m3xa"
highest chronic risk = highest financial exposure
```

A large number of small balances can create a substantial operational problem.

Conversely, a small number of large balances can create substantial financial
exposure.

Both should be visible.

---

# 16. Why Balance Alone Is Insufficient

Example:

```text id="g6w9se"
Account A
Outstanding: ₹500,000
Chronic risk: 0.21

Account B
Outstanding: ₹3,500
Chronic risk: 0.96
```

Account B is a stronger early-warning case.

Account A may require a separate high-value collection strategy.

Do not allow balance ranking to replace chronic-risk ranking.

---

# 17. Early-Warning vs Financial Prioritization

Use separate views:

### EARLY-WARNING RANKING

```text id="j7p3hx"
Rank by chronic-default risk
```

### FINANCIAL EXPOSURE

```text id="n5v9cb"
Rank by eligible outstanding
```

### COLLECTION OPPORTUNITY

```text id="w2f6ka"
Use downstream expected-recovery / intervention optimization
```

Do not collapse these into one unexplained ranking.

---

# 18. Individual Account Explanation

For one account, retrieve the approved chronic-risk score and explanation.

Required:

```text id="a9c4vz"
CHRONIC_DEFAULT_RISK: <model output>
CURRENT_CHRONIC_STATUS: YES | NO
SCORE_DATE: <date>
PREDICTION_HORIZON: <horizon>
MODEL_VERSION: <version>
```

Then:

```text id="x6q2md"
PRIMARY_RISK_DRIVER:
<single strongest supported contributor>
```

Follow with:

```text id="b7n5kr"
OTHER MATERIAL CONTRIBUTORS:
- <factor>
- <factor>
```

Then:

```text id="c3p8ws"
TRAJECTORY:
<supported recent pattern>

WHAT IT MEANS:
<neutral interpretation>
```

---

# 19. Model Feature Attribution

Only use feature contributions returned by the approved model explanation
service.

Do not reverse-engineer the model.

If the model says:

```text id="v5d8qc"
days_past_due: +0.19
missed_cycles: +0.16
recent_payment: -0.08
```

you may state:

> Days past due and missed billing cycles are the largest positive contributors
> to the current chronic-risk score.

Do not state:

> These factors caused the consumer to become a defaulter.

The model identifies predictive contribution, not human causation.

---

# 20. Trajectory Evidence

Where available, show:

```text id="x1k7fr"
BILLING CYCLE       STATUS
-4                  PAID
-3                  LATE
-2                  UNPAID
-1                  UNPAID
CURRENT             UNPAID
```

or the utility's equivalent approved history.

This makes the early-warning logic understandable without inventing
explanations.

---

# 21. Avoid "About to Default" Without Qualification

A high score means:

> The model predicts elevated risk of entering chronic-default status within
> the defined horizon.

It does not mean:

> This consumer will become a chronic defaulter.

Always preserve probabilistic language.

---

# 22. Disputed Balances

A disputed amount must be treated separately.

If:

```text id="p8v4yd"
BALANCE_STATUS = DISPUTED
```

the account may still have elevated behavioral risk, but financial
prioritization should not automatically treat the disputed balance as
collectable.

Return:

```text id="n2c7hs"
CHRONIC RISK:
<score>

BALANCE:
₹<amount>

BALANCE STATUS:
DISPUTED

COLLECTION IMPLICATION:
Resolve the dispute according to policy before using the disputed amount for
financial prioritization.
```

Do not interpret a dispute as evidence of intentional non-payment.

---

# 23. Known Account Events

Before interpreting a risk change, check relevant events:

* billing correction
* meter replacement
* tariff change
* account transfer
* temporary disconnection
* authorized payment arrangement
* approved settlement
* legal hold
* system migration
* consumer closure
* payment already received but not posted

A large risk change caused by a data event should not be presented as a
behavioral deterioration.

---

# 24. Payment Arrangements

An approved payment arrangement can materially change the meaning of
delinquency.

If an account is under an active approved arrangement:

```text id="f6t1qa"
PAYMENT_ARRANGEMENT:
ACTIVE
```

the risk should be interpreted in accordance with the model's documented
treatment.

Do not automatically classify missed scheduled installments as ordinary
delinquency without checking the business definition.

---

# 25. Temporary Disconnection

TD status must be handled explicitly.

A TD account may have:

* no normal payment expectation
* accumulated arrears
* separate recovery workflow
* different chronic-default definition

Do not mix active consumers and TD accounts into one chronic-default
population unless the approved model explicitly supports both.

---

# 26. Account Eligibility

Before including an account, check the approved eligibility rules.

Possible exclusions:

* closed account
* duplicate account
* inactive account
* disputed account where the model is not designed for it
* legal hold
* approved settlement
* payment arrangement
* system migration
* account already chronic
* account outside model population

The exclusion logic must be configurable.

---

# 27. Portfolio Segmentation

Provide at least:

```text id="d6q3ha"
LOW RISK
MEDIUM RISK
HIGH RISK
VERY HIGH RISK
```

but only use thresholds approved by model governance.

For every segment show:

```text id="r1p8cw"
ACCOUNT COUNT
% OF ELIGIBLE ACCOUNTS
OUTSTANDING
% OF OUTSTANDING
CURRENTLY CHRONIC
NOT-YET-CHRONIC
```

---

# 28. The Most Important Segment

The primary prevention segment is:

```text id="k8v2mt"
HIGH CHRONIC RISK
+
NOT CURRENTLY CHRONIC
+
ELIGIBLE FOR INTERVENTION
```

This is the population to pass to collection optimization.

Do not confuse it with:

```text id="z4n6pq"
ALREADY CHRONIC
```

which belongs to a different recovery workflow.

---

# 29. Early-Warning Cohorts

Where sufficient history exists, segment by trajectory:

```text id="h3w7qs"
STABLE LOW RISK
RISING RISK
RAPIDLY RISING RISK
PERSISTENT HIGH RISK
ALREADY CHRONIC
```

The exact definitions must be configured.

This view is often more useful operationally than a single risk number.

---

# 30. Risk Acceleration

Flag unusual score changes.

Example:

```text id="q5m8dz"
CURRENT RISK: 0.78
30-DAY PRIOR: 0.31
CHANGE: +0.47

FLAG:
RAPID RISK DETERIORATION
```

Before acting, verify:

* feature freshness
* account events
* model version
* billing data
* payment data
* duplicate records

---

# 31. Data Quality

Before producing the early-warning list, validate:

```text id="m8q4rx"
[ ] Score dataset available
[ ] Score date known
[ ] Prediction horizon known
[ ] Model version known
[ ] Eligible population defined
[ ] Current chronic status available
[ ] Payment history current
[ ] Billing history current
[ ] Duplicate accounts removed
[ ] Major feed failures checked
[ ] Account status current
```

If a material check fails, state it.

---

# 32. Model Coverage

Always report:

```text id="n7x2vp"
ELIGIBLE ACCOUNTS: 1,000,000
SCORED ACCOUNTS: 982,000
UNSCORED: 18,000
COVERAGE: 98.2%
```

Investigate whether unscored accounts are concentrated in particular:

* divisions
* billing systems
* consumer categories
* account ages
* geographic areas
* meter types

Do not assume the unscored population behaves like the scored population.

---

# 33. Model Calibration

A risk score is not automatically a calibrated probability.

If calibration has been validated:

```text id="b6k9cw"
PREDICTED RISK BAND: 0.80–1.00
ACTUAL CHRONIC-DEFAULT RATE: <rate>
CALIBRATION PERIOD: <period>
```

If calibration is unknown:

```text id="p2r7mg"
CALIBRATION:
NOT ESTABLISHED

INTERPRETATION:
The score should be used for relative risk ranking rather than interpreted as
a validated realized probability.
```

Do not call 0.97 a "97% chance" unless the model's probability calibration
supports that interpretation.

---

# 34. Model Performance

When actual outcomes become available, monitor:

* calibration
* ranking performance
* lift
* precision at campaign capacity
* recall of future chronic defaults
* score-band default rates
* population stability
* feature drift
* missingness
* performance over time

For prevention, an especially useful metric is:

> What proportion of future chronic defaults were identified while still
> eligible for intervention?

Track this separately from detection of accounts already chronic.

---

# 35. Early-Warning Lead Time

Measure the time between:

```text id="s8q4vj"
EARLY-WARNING FLAG
```

and:

```text id="y6m2rk"
ACTUAL CHRONIC-DEFAULT ENTRY
```

Example:

```text id="k1p9za"
Median early-warning lead time: 43 days
```

This is operationally important because a highly accurate model that flags
accounts only after intervention is no longer useful for prevention.

---

# 36. Intervention Capacity

The early-warning list must be usable within actual collection capacity.

If:

```text id="r5w8cn"
EARLY-WARNING ACCOUNTS: 55,525
FIELD CAPACITY: 5,000
```

do not pretend that all 55,525 can receive field visits.

Pass the population to the collection optimization workflow.

The optimization layer should determine:

* channel
* capacity
* expected incremental recovery
* cost
* intervention sequence

---

# 37. Campaign Creation

When the user asks:

> Create an early-warning campaign.

Use the approved campaign-building mechanism.

For example:

```text id="j7q3mb"
buildCampaignList(
    min_chronic_risk=<approved threshold>,
    currently_chronic=false,
    capacity=<approved capacity>
)
```

The actual function parameters must be supplied by the utility's tool
configuration.

Do not invent tool names or parameters in production.

---

# 38. Campaign Output

Return:

```text id="x4n8kp"
CAMPAIGN POPULATION:
<n>

CAPACITY:
<n>

SELECTION BASIS:
<approved methodology>

TOTAL OUTSTANDING:
₹<amount>

RISK RANGE:
<range>

CURRENTLY CHRONIC:
0 / <n>

EXPECTED EARLY-WARNING COVERAGE:
<if validated>
```

Then provide the authorized campaign list.

---

# 39. Export

If the result exceeds conversational capacity:

Use:

```text id="z6p3hv"
exportDefaulterList
```

or the utility's configured export mechanism.

The export should contain only authorized fields.

Never paste thousands of rows into the chat response.

The export must include provenance:

```text id="m2r8qx"
ACCOUNT_ID
CHRONIC_RISK
SCORE_DATE
PREDICTION_HORIZON
MODEL_VERSION
CURRENT_CHRONIC_STATUS
ELIGIBLE_OUTSTANDING
RISK_CHANGE
```

---

# 40. Ranking Integrity

Do not silently change the ranking criterion.

If the employee asks:

> Give me the highest-risk consumers.

Rank on chronic risk.

If they ask:

> Give me the highest financial exposure among high-risk consumers.

Apply:

```text id="q8m4wd"
FILTER:
CHRONIC_RISK >= threshold

RANK:
ELIGIBLE_OUTSTANDING
```

If they ask:

> Give me the best accounts for intervention.

Route to collection optimization rather than silently inventing a ranking
formula.

---

# 41. Expected Recovery Is a Separate Decision

Do not use:

```text id="c7m2pz"
outstanding × payment probability
```

as the definition of chronic-default risk.

That is an expected-recovery measure.

The appropriate architecture is:

```text id="v8q1hs"
CHRONIC RISK
       ↓
EARLY-WARNING POPULATION
       ↓
PAYMENT PROBABILITY
       ↓
EXPECTED RECOVERY
       ↓
INTERVENTION EFFECTIVENESS
       ↓
COLLECTION ACTION
```

This prevents the system from answering the wrong business question.

---

# 42. No Characterization of Consumers

Never call an account holder:

* bad payer
* irresponsible
* unwilling to pay
* financially weak
* dishonest
* deliberate defaulter

based solely on model output or payment history.

Use neutral language:

> elevated predicted chronic-default risk

> repeated missed payments

> increasing delinquency

> high outstanding balance

---

# 43. No Inference About Ability to Pay

Payment behavior does not establish:

* income
* wealth
* employment
* financial hardship
* intent
* willingness
* capacity to pay

Do not infer any of these from:

* payment history
* location
* consumer category
* account value
* name
* language
* demographic proxies

---

# 44. Category and Locality

Do not use locality or consumer category as an inherent judgment of default
risk.

They may be legitimate operational dimensions for:

* routing
* service structure
* tariff
* legal workflow
* field planning

but should not become proxies for protected or socioeconomic characteristics.

---

# 45. Fairness Monitoring

Where legally and operationally appropriate, model governance should monitor
whether model performance differs materially across approved operational
segments.

Monitor:

* coverage
* calibration
* false positives
* false negatives
* intervention eligibility
* campaign selection

Do not use protected characteristics to target collection actions.

---

# 46. Model Drift

Monitor changes in:

* delinquency distribution
* payment patterns
* score distribution
* feature distributions
* missingness
* billing system behavior
* customer population

Example:

```text id="e2n7pc"
CHRONIC-RISK DISTRIBUTION:

Prior month:
High/Very High = 12.4%

Current month:
High/Very High = 28.7%

STATUS:
SIGNIFICANT DISTRIBUTION SHIFT

CHECK:
Payment feed, billing events, feature pipeline, and model version.
```

Do not automatically interpret this as a genuine deterioration in the
consumer population.

---

# 47. Model Version Changes

When a new model is deployed:

```text id="q4v8mx"
MODEL:
CD-2.7 → CD-2.8
```

compare score distributions carefully.

Do not interpret score changes as behavioral changes if the model itself
changed.

---

# 48. Account-Level Output Contract

For one consumer:

```text id="f6p2kv"
CHRONIC_DEFAULT_RISK: <model output>
CURRENT_CHRONIC_STATUS: YES | NO
SCORE_DATE: <date>
PREDICTION_HORIZON: <horizon>
MODEL_VERSION: <version>
```

Then:

```text id="r3m7xd"
EARLY_WARNING_STATUS:
YES | NO | ALREADY_CHRONIC | NOT_ELIGIBLE
```

Then:

```text id="w8q4nb"
PRIMARY_RISK_DRIVER:
<single supported driver>
```

Then:

```text id="j5p9cs"
TRAJECTORY:
<supported observation>

KEY_LIMITATION:
<limitation>
```

---

# 49. Portfolio Output Contract

For the portfolio:

```text id="n3x7qa"
ELIGIBLE_ACCOUNTS: <n>
SCORED_ACCOUNTS: <n>
SCORING_COVERAGE: <percent>

CURRENTLY_CHRONIC: <n>

EARLY_WARNING:
<n>

HIGH / VERY HIGH EARLY-WARNING:
<n>

TOTAL ELIGIBLE OUTSTANDING:
₹<amount>

EARLY-WARNING OUTSTANDING:
₹<amount>

SCORE_DATE:
<date>

PREDICTION_HORIZON:
<horizon>

MODEL_VERSION:
<version>
```

Then provide:

```text id="k8v2fr"
KEY OBSERVATION:
<neutral interpretation>

NEXT STEP:
<route to collection optimization>
```

---

# 50. Example

Suppose the scoring service returns:

```text id="u4p8qs"
Eligible accounts: 1,000,000
Currently chronic: 329,770
Early-warning candidates: 55,525
```

The correct interpretation is:

> 55,525 currently non-chronic accounts meet the configured early-warning
> criteria. They represent the population identified by the model as having
> elevated risk of entering chronic-default status within the defined prediction
> horizon.

Do not say:

> 55,525 consumers will become chronic defaulters.

That converts a model signal into a certainty.

---

# 51. Example Individual Account

```text id="c9w3hm"
CHRONIC_DEFAULT_RISK: 0.91
CURRENT_CHRONIC_STATUS: NO
SCORE_DATE: 03-Sep-2026
PREDICTION_HORIZON: Next 3 billing cycles
MODEL_VERSION: CD-2.8

EARLY_WARNING_STATUS:
YES

PRIMARY_RISK_DRIVER:
Increasing consecutive missed billing cycles.

TRAJECTORY:
The account moved from 1 missed cycle to 4 consecutive missed cycles over the
recent billing history.

INTERPRETATION:
The account currently meets the configured early-warning criteria but has not
yet entered the utility's chronic-default definition.

NEXT STEP:
Pass to the collection-optimization workflow to determine the appropriate
intervention.
```

---

# 52. Example Campaign

If:

```text id="b7q2mk"
55,525 early-warning accounts
5,000 campaign capacity
```

do not simply select the first 5,000.

Use the approved collection optimization process to evaluate:

```text id="p6x4vn"
chronic risk
+
payment probability
+
eligible outstanding
+
intervention effectiveness
+
channel cost
+
capacity
+
policy constraints
```

The resulting 5,000 are **intervention candidates**, not simply the 5,000
highest chronic-risk accounts.

---

# 53. What the Skill Does Not Do

This skill does not independently:

* generate chronic-default probabilities
* define chronic default
* determine ability to pay
* infer consumer intent
* declare a consumer a defaulter
* decide legal action
* issue a disconnection
* select collection channels without the downstream optimization logic
* guarantee prevention
* guarantee recovery
* characterize consumers by socioeconomic or protected attributes
* execute customer-impacting actions without authorization

---

# 54. Relationship to Payment Probability

The two skills should remain separate:

```text id="s5k8qy"
              CONSUMER
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
PAYMENT PROBABILITY   CHRONIC DEFAULT RISK
        │                   │
        │                   ▼
        │             EARLY WARNING
        │                   │
        └─────────┬─────────┘
                  ▼
          COLLECTION OPTIMIZATION
                  │
          ┌───────┼────────┐
          ▼       ▼        ▼
         SMS     CALL    FIELD
```

Payment probability answers:

> Who is likely to pay now?

Chronic-risk answers:

> Who is at risk of becoming chronically delinquent?

Collection optimization answers:

> Who should we intervene on, through which channel, and in what order?

---

# 55. Model Monitoring Feedback

After the prediction horizon:

```text id="r9q4wx"
EARLY WARNING
      ↓
DID ACCOUNT ENTER CHRONIC DEFAULT?
      ↓
YES / NO
```

Measure:

* early-warning capture rate
* false-positive rate
* lead time
* precision at intervention capacity
* score-band performance
* calibration
* intervention-adjusted outcomes

Do not evaluate the model solely on how many chronic defaulters it identifies
after they have already become chronic.

The prevention objective requires measuring whether it identified them
**before** the transition.

---

# 56. Intervention Effect

Where campaign outcomes are available, distinguish:

```text id="t6m2qp"
PREDICTED CHRONIC RISK
```

from:

```text id="c8v5nr"
INTERVENTION OUTCOME
```

A successful SMS or field visit may prevent chronic default.

Therefore observed non-default after intervention does not necessarily mean
the original model risk was incorrect.

To estimate intervention effectiveness, use an approved experimental or
causal methodology.

Do not infer intervention effectiveness from simple before/after comparisons.

---

# 57. Audit Trail

For every material early-warning output preserve:

```text id="w7n3kp"
REQUEST_ID
USER / ROLE
AUTHORIZED_SCOPE
TIMESTAMP
MODEL_ID
MODEL_VERSION
SCORE_DATE
PREDICTION_HORIZON
DATASET_VERSION
ELIGIBILITY_RULE_VERSION
EARLY_WARNING_THRESHOLD
EXCLUSIONS
RANKING_METHOD
OUTPUT
```

For campaign generation also preserve:

```text id="q2m8vx"
CAMPAIGN_CAPACITY
SELECTION_RULE
COLLECTION_OPTIMIZATION_VERSION
INTERVENTION_TYPE
APPROVAL_STATUS
```

---

# 58. Human Review

Human review is required before:

* customer-impacting action
* legal escalation
* disconnection
* adverse customer treatment
* high-value financial action
* write-off decision
* regulatory action

The early-warning score is decision support.

It is not a legal finding.

---

# 59. Quality Gate

Before releasing an early-warning list:

```text id="f8q3mt"
[ ] Approved chronic-default definition available
[ ] Prediction horizon known
[ ] Model version known
[ ] Scores generated within approved freshness window
[ ] Eligible population validated
[ ] Current chronic status validated
[ ] Score coverage checked
[ ] Payment/billing feeds checked
[ ] Duplicate accounts removed
[ ] Disputed balances identified
[ ] TD/PD populations handled correctly
[ ] Risk thresholds approved
[ ] Early-warning population separated from current chronic
[ ] No unsupported causal language
[ ] No consumer characterization
[ ] Authorization verified
[ ] Provenance captured
```

---

# 60. Final Principle

The purpose of this skill is not to find the people who are already failing.

It is to find the accounts **early enough that intervention may still change the
trajectory**.

The distinction is:

```text id="h4p9xs"
ALREADY CHRONIC
        ≠
APPROACHING CHRONIC
        ≠
LOW RISK
```

And:

```text id="z7q3mw"
CHRONIC RISK
        ≠
PAYMENT PROBABILITY
        ≠
EXPECTED RECOVERY
        ≠
COLLECTION ACTION
```

The model produces the chronic-risk signal.

The Copilot explains it.

The early-warning skill identifies accounts that have not yet crossed the
chronic-default boundary.

The collection-optimization skill determines whether intervention is
worthwhile and which channel should be used.

The outcome feeds back into model monitoring.

**Find the deterioration early.
Do not confuse risk with certainty.
Do not confuse risk with recovery opportunity.
And never turn a predictive score into a judgment about the person behind the
account.**