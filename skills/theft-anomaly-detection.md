---
name: theft-anomaly-detection
description: >
  Analyses metering and billing data for signs of theft, tampering or unauthorised use, and produces an anomaly risk score with the evidence that supports it. Use to decide whether a consumer warrants a vigilance inspection, or to assess a case an anomaly model has flagged.
allowed-tools:
  - buildInspectionPlan
  - exportInspectionList
  - getAnomalyRiskScore
  - getAnomalyScreening
  - getBillingHistory
  - getConsumer
  - getConsumptionHistory
  - getFeederLosses
  - getMeterStatus
  - getPeerBenchmark
  - getSiteSurvey
  - listInspectionTargets
---

# AI-Based Theft / Energy Loss Detection Intelligence

## Domain

Electricity Distribution / Revenue Protection / Energy Loss / Anomaly Detection / Field Inspection

---

# 1. Purpose

This skill identifies abnormal electricity-consumption and metering patterns that may warrant further investigation.

The skill analyzes authorized:

* Consumer billing data
* Consumption history
* Meter data
* Meter events
* Tamper events
* Connected-load information
* Sanctioned-load information
* Load-survey data
* Payment/billing records
* Meter replacement records
* Work orders
* Inspection history
* Disconnection/restoration history
* Peer/benchmark consumption
* Feeder-level losses
* Distribution-transformer (DT) losses
* Other approved operational data

The skill produces:

1. Consumer-level anomaly scores.
2. Theft/anomaly risk scores.
3. Recommended inspection or verification actions.
4. Evidence-backed inspection cases.
5. Portfolio-level inspection priorities.
6. Feeder/DT-level loss intelligence.
7. Explanations for each material risk signal.
8. Recommended field verification steps.

The skill does **not** determine that a consumer has committed theft.

It identifies accounts or locations where the available evidence indicates that an inspection, meter test, or other authorized verification may have value.

---

# 2. Core Business Objective

Traditional inspection programs may rely heavily on:

* Random inspection
* Manual selection
* Complaints
* Static rules
* Historical lists
* High-loss areas

This skill enables an intelligence-led approach:

```text
Enterprise Data
      ↓
Consumption Analysis
      ↓
Meter/Event Analysis
      ↓
Load Analysis
      ↓
Temporal Analysis
      ↓
Peer Comparison
      ↓
Work-Order Reconciliation
      ↓
Anomaly Detection
      ↓
Evidence Validation
      ↓
Risk Scoring
      ↓
Inspection Prioritization
      ↓
Field Verification
```

The objective is not to maximize the number of inspections.

The objective is to maximize the **expected value of limited inspection capacity** while minimizing false positives and unnecessary customer disruption.

---

# 3. Fundamental Principle

## Anomaly ≠ Theft

The system detects anomalies.

It does not establish theft.

A consumer may have unusually low consumption because of:

* Meter failure
* Communication failure
* Premises vacancy
* Seasonal operation
* Reduced occupancy
* Load surrender
* Business closure
* Production shutdown
* Energy-efficiency improvements
* Tariff changes
* Meter replacement
* Billing-system error
* Approved disconnection
* Legitimate change in operating hours

Therefore:

```text
ANOMALY
   ↓
INVESTIGATION
   ↓
PHYSICAL / METER VERIFICATION
   ↓
AUTHORIZED DETERMINATION
```

Never:

```text
ANOMALY
   ↓
THEFT CONFIRMED
```

---

# 4. Primary Use Cases

The skill must support:

1. Sudden consumption reduction detection.
2. Sustained consumption reduction detection.
3. Consumption inconsistent with connected load.
4. Abnormal day/night consumption.
5. Peer-group deviation.
6. Repeated meter tamper events.
7. Meter-event anomaly detection.
8. Possible bypass indicators.
9. Possible physical tampering indicators.
10. Meter-vs-billing inconsistency.
11. Meter-vs-load inconsistency.
12. Zero/near-zero consumption anomaly.
13. Sudden consumption restoration/increase.
14. Historical pattern breaks.
15. Abnormal seasonal behavior.
16. Feeder-loss analysis.
17. DT-loss analysis.
18. Consumer prioritization.
19. Inspection-capacity optimization.
20. Meter-test prioritization.
21. Portfolio-level anomaly screening.
22. Individual consumer case generation.

---

# 5. Operating Modes

The skill operates in four primary modes.

## Mode 1 — Portfolio Screening

Used when the user asks for:

* Screening
* Top anomalies
* Consumers for inspection
* Division-level analysis
* Monthly inspection plan
* High-risk consumers
* Feeder loss analysis
* DT loss analysis
* Export/list generation

The agent must begin with the portfolio screening capability.

---

## Mode 2 — One Consumer

Used when the user provides a specific:

* Consumer number
* Account ID
* Service-point ID
* Meter number

The agent builds an evidence-backed case for that specific consumer.

---

## Mode 3 — Inspection Planning

Used when the user asks:

* "Give me the top 1,800 inspections."
* "Select 50,000 consumers."
* "Prioritize this month's inspections."
* "Which cases should the field team visit?"

The agent must rank eligible cases against the organization's inspection capacity and policy.

---

## Mode 4 — Feeder / DT Analysis

Used when the user asks:

* "Which feeders have the highest losses?"
* "Which DTs are deteriorating?"
* "Where should we investigate?"
* "Which areas have abnormal technical/non-technical loss patterns?"

Feeder/DT data is used as **area-level intelligence**.

It must never automatically increase an individual consumer's risk score.

---

# 6. Portfolio Screening

The screening workflow is:

```text
GET ELIGIBLE CONSUMER BASE
        ↓
VALIDATE DATA
        ↓
REMOVE INELIGIBLE ACCOUNTS
        ↓
CALCULATE FEATURES
        ↓
DETECT ANOMALIES
        ↓
TEST INNOCENT EXPLANATIONS
        ↓
RECONCILE WORK ORDERS
        ↓
ASSESS EVIDENCE
        ↓
CALCULATE RISK
        ↓
RANK CASES
        ↓
APPLY INSPECTION CAPACITY
        ↓
GENERATE INSPECTION PLAN
```

---

# 7. Eligibility Filtering

Before scoring a consumer, determine whether the account is eligible.

Potential exclusions:

* Closed account
* Permanently disconnected account
* Meter replacement in progress
* Approved shutdown
* Approved vacancy
* Active maintenance
* Active dispute where policy requires exclusion
* Active inspection
* Recent inspection below configured cooldown
* Known meter communication failure
* Known billing-system issue
* Approved load surrender
* Approved load change
* Other policy-defined exclusions

Every exclusion should have a reason.

Example:

```text
Consumer 12345 excluded.

Reason:
Approved shutdown work order active from 2026-08-01 through 2026-09-15.
```

---

# 8. Important Screening Principle

The screening process must actively suppress legitimate explanations.

Example:

```text
8,141 consumers show abnormal consumption.

8,141 have recorded legitimate explanations.

Therefore:
They should not appear in the enforcement inspection population.
```

The system must calculate and report:

* Total screened
* Total anomalous
* Legitimately explained
* Suppressed
* Eligible for inspection
* Recommended for inspection
* Recommended for meter testing
* Recommended for monitoring

---

# 9. Suppression Value

The skill should quantify the value of suppressing explainable anomalies.

Example:

```text
Consumers screened:
250,000

Initially anomalous:
25,224

Suppressed due to recorded legitimate causes:
8,141

Otherwise eligible inspection cases:
17,083

Inspection capacity:
1,800/month

Prevented unnecessary inspections:
4,140
```

The system should emphasize that explainable anomalies were removed before enforcement prioritization.

This is a critical measure of precision and fairness.

---

# 10. Feature Categories

The skill may derive features from:

## Consumption

* Monthly kWh
* Daily kWh
* Hourly consumption where available
* Consumption trend
* Consumption volatility
* Consumption change rate
* Rolling averages
* Rolling medians
* Seasonal baseline
* Same-month historical baseline

## Billing

* Billed units
* Billing amount
* Billing frequency
* Billing anomalies
* Estimated bills
* Actual bills
* Billing corrections

## Meter

* Meter events
* Meter status
* Meter replacement
* Meter health
* Communication status
* Tamper events
* Reverse-current events
* Cover events
* Magnetic events where applicable
* Meter clock/events where available

## Load

* Sanctioned load
* Connected load
* Recorded load
* Load survey
* Maximum demand
* Historical load

## Operational

* Work orders
* Inspection history
* Disconnection history
* Restoration history
* Maintenance records
* Meter-change records

## Benchmark

* Peer-group consumption
* Similar connected load
* Similar tariff/category
* Similar usage pattern
* Similar premises type
* Similar seasonal profile

---

# 11. Data Quality Checks

Before scoring, check:

* Missing values
* Duplicate records
* Billing gaps
* Meter replacement gaps
* Estimated bills
* Communication outages
* Abnormal meter-read intervals
* Incorrect timestamps
* Unit inconsistencies
* Account/meter mismatches
* Missing work orders
* Missing load information

Data-quality issues must not be treated as consumer anomalies.

---

# 12. Sudden Consumption Reduction

Detect sudden reduction when consumption drops materially relative to a valid baseline.

Possible baselines:

* 3-month average
* 6-month average
* 12-month average
* Same month previous year
* Seasonal baseline
* Peer-adjusted baseline

Example:

```text
November 2025:
45 kWh

12-month mean:
310 kWh

Reduction:
85.5%
```

The agent must report:

* Baseline
* Current consumption
* Absolute difference
* Percentage difference
* Duration
* Start date
* Whether reduction is sustained

---

# 13. Sustained Reduction

A one-month drop is weaker than a sustained change.

Evaluate:

```text
1 month
3 months
6 months
12 months
```

Example:

```text
Consumption declined:

January:
310 kWh

February:
275 kWh

March:
102 kWh

April:
97 kWh

May:
91 kWh
```

This is materially different from a single low month.

---

# 14. Innocent Explanation Test — Consumption Drop

Before assigning risk, test:

1. Meter failure
2. Communication failure
3. Meter replacement
4. Tariff change
5. Load surrender
6. Premises closure
7. Occupancy change
8. Seasonal operation
9. Approved shutdown
10. Billing correction
11. Estimated-vs-actual billing transition
12. Known operational issue

If an explanation is confirmed:

```text
ANOMALY EXPLAINED
```

If it cannot be tested:

```text
EXPLANATION UNRESOLVED
```

An unresolved explanation should reduce confidence.

---

# 15. Consumption Inconsistent With Connected Load

Compare consumption against:

* Sanctioned load
* Connected load
* Historical maximum demand
* Load survey
* Equipment profile
* Operating schedule where authorized

Example:

```text
Connected load:
18 kW

Expected operating profile:
8 hours/day

Historical consumption:
1,850 kWh/month

Current consumption:
240 kWh/month

Deviation:
87%
```

The agent must not assume that connected load is continuously operated.

Potential explanations:

* Seasonal business
* Shift change
* Reduced production
* Load not actually used
* Equipment removal
* Load surrender
* Premises closure

---

# 16. Night/Day Consumption Analysis

Where interval data exists, calculate:

```text
Night consumption
-----------------
Total consumption
```

and:

```text
Day consumption
---------------
Total consumption
```

Analyze changes over time.

Potential anomalies:

* Sudden night-only usage
* Sudden disappearance of daytime usage
* Unusual reversal of historical pattern
* Unexpected zero periods
* Consumption concentrated in unusual hours

The agent must consider legitimate explanations:

* Night-shift operations
* Water pumping
* Agricultural schedules
* Cold storage
* Industrial processes
* Security systems
* EV charging
* Other known operating patterns

---

# 17. Peer Benchmarking

Peer comparison may compare consumers with:

* Same tariff
* Similar connected load
* Similar premises type
* Similar geography
* Similar consumption history
* Similar operating profile

Peer groups must be sufficiently comparable.

Never assume:

```text
Same tariff = same behavior
```

Peer comparison is the weakest major evidence category.

---

# 18. Peer Deviation

Example:

```text
Consumer:
125 kWh/month

Comparable peer median:
420 kWh/month

Deviation:
-70.2%
```

This should be interpreted as:

> Consumption is materially below the selected peer benchmark.

Not:

> Consumer is stealing electricity.

---

# 19. Peer Comparison Restrictions

Peer deviation alone should not produce the highest inspection priority.

A case based primarily on peer deviation should generally be limited to:

```text
INSPECT_ROUTINE
```

unless additional independent evidence exists.

---

# 20. Zero or Near-Zero Consumption

Detect:

* Zero consumption
* Near-zero consumption
* Repeated zero billing
* Zero consumption despite active account
* Zero consumption despite historical usage

Before escalating, test:

* Vacancy
* Approved shutdown
* Disconnection
* Meter communication failure
* Meter replacement
* Billing issue
* Seasonal premises
* Business closure

---

# 21. Repeated Tamper Events

Analyze:

* Event type
* Timestamp
* Frequency
* Duration
* Repetition
* Event sequence
* Meter replacement
* Maintenance work orders

Example:

```text
Tamper events:

2025-09-03:
Cover open

2025-10-18:
Cover open

2025-11-03:
Cover open

Work-order reconciliation:
No matching work order found.
```

Repeated events with no authorized operational explanation may substantially increase anomaly risk.

---

# 22. Work-Order Reconciliation

Every meter/tamper event should be compared against relevant work orders.

Example:

```text
Meter event:
Cover open
2025-11-03 14:32

Work order:
Meter replacement
2025-11-03 13:50–15:20

Result:
EXPLAINED
```

Without work-order reconciliation:

```text
Tamper event:
UNRESOLVED
```

Do not automatically classify it as suspicious.

---

# 23. Meter Health

Consider whether abnormal consumption could result from:

* Meter malfunction
* Meter communication failure
* Stopped meter
* Incorrect meter configuration
* Clock/time issue
* Replacement event
* Data gap

If meter fault is plausible and no independent interference evidence exists:

```text
RECOMMENDED_ACTION:
METER_TEST
```

---

# 24. Meter-Test Principle

A defective meter is an important alternative explanation for unexplained consumption reduction.

Therefore:

```text
Unexplained consumption drop
+
No independent physical/tamper evidence
+
Possible meter issue
=
METER_TEST
```

Do not automatically send such cases to enforcement inspection.

---

# 25. Possible Bypass Detection

Where approved meter/event data and field evidence support it, identify possible bypass indicators.

Potential indicators:

* Consumption suddenly falls while connected load remains materially unchanged.
* Meter events indicate abnormal connection behavior.
* Physical inspection data shows an alternate visible path.
* Load survey indicates material usage inconsistent with recorded metering.
* Independent measurements indicate consumption not reflected by meter data.

The system must describe this as:

```text
POSSIBLE_BYPASS_INDICATOR
```

not:

```text
CONFIRMED_BYPASS
```

unless an authorized physical inspection has established it.

---

# 26. Physical Evidence Hierarchy

Evidence should be weighted approximately in this order:

## Tier 1 — Direct Physical/Meter Evidence

Examples:

* Confirmed physical bypass
* Verified altered meter terminals
* Verified broken/changed seal
* Confirmed unauthorized connection
* Physical inspection finding
* Independent measurement discrepancy

## Tier 2 — Independent Meter/Operational Evidence

Examples:

* Repeated unexplained tamper events
* Meter event + consumption anomaly
* Load survey + billing discrepancy
* Meter data + independent measurement

## Tier 3 — Behavioral/Consumption Evidence

Examples:

* Sustained consumption drop
* Unexpected consumption pattern
* Load/consumption inconsistency

## Tier 4 — Peer Statistical Evidence

Examples:

* Consumption below peer median
* Unusual peer deviation
* Statistical outlier

Tier 4 must never be treated as equivalent to Tier 1.

---

# 27. Independent Evidence Principle

Confidence should increase when independent sources agree.

Example:

```text
Billing data:
90% consumption reduction

Meter event:
Repeated cover-open events

Work order:
No matching maintenance event

Load survey:
Material load still present
```

This is stronger than:

```text
Billing data:
90% consumption reduction
```

The agent should explicitly identify evidence convergence.

---

# 28. Correlated Signals

Do not double-count signals that are derived from the same underlying data.

Example:

These may all originate from the same consumption series:

* 80% reduction
* 12-month deviation
* Z-score anomaly
* Peer deviation

They should not be treated as four independent pieces of evidence.

The scoring engine must account for signal correlation.

---

# 29. Risk Score

Generate:

```text
ANOMALY_RISK: 0-100
```

This is a prioritization score, not a probability of guilt.

Recommended interpretation:

```text
0–19:
Very Low

20–39:
Low

40–59:
Moderate

60–74:
Elevated

75–89:
High

90–100:
Very High
```

Thresholds must be configurable.

---

# 30. Risk Score Components

The score may incorporate:

```text
Consumption anomaly
Meter anomaly
Tamper-event evidence
Load inconsistency
Temporal anomaly
Historical recurrence
Work-order reconciliation
Meter-health evidence
Physical evidence
Peer deviation
```

Feeder/DT loss must not be directly included in the consumer score.

---

# 31. Recommended Score Logic

A conceptual model:

```text
Risk Score
=
Evidence Strength
×
Persistence
×
Independence
×
Unresolved Status
```

The score should be reduced when:

* Legitimate explanation exists
* Meter fault is likely
* Work order explains event
* Data quality is poor
* Evidence is weak
* Signals are correlated

---

# 32. Physical Evidence Override

Where verified physical evidence exists, it should dominate statistical evidence.

Example:

```text
Peer deviation:
Low relevance

Consumption drop:
Moderate relevance

Verified physical bypass:
High relevance
```

The system must not allow strong peer statistics to outweigh verified contradictory physical evidence.

---

# 33. Feeder and DT Loss

Feeder/DT losses are useful for **area-level intelligence**.

Use them to identify:

* High-loss feeders
* Deteriorating feeders
* Abnormal DTs
* Loss trends
* Geographic investigation zones
* Areas requiring system-level review

Do not use feeder/DT loss to increase an individual consumer's score.

---

# 34. Absolute Prohibition — Feeder Loss

Never perform:

```text
Consumer Risk
+
Feeder Loss
=
Higher Consumer Risk
```

A consumer on a 26% loss feeder is not inherently more suspicious than one on a 10% loss feeder.

Feeder loss should be reported separately:

```text
AREA CONTEXT:
Feeder loss = 26%

CONSUMER RISK:
91/100

Relationship:
Feeder loss is contextual only and was not used in the consumer risk score.
```

---

# 35. Feeder-Level Workflow

```text
Get feeder measurements
        ↓
Calculate technical/non-technical loss indicators
        ↓
Identify abnormal trends
        ↓
Compare historical periods
        ↓
Identify affected DTs
        ↓
Map consumer clusters
        ↓
Generate area investigation plan
```

The resulting area intelligence may inform where field resources are deployed, but must not automatically determine individual consumer guilt or risk.

---

# 36. DT-Level Analysis

Analyze:

* Input energy
* Billed energy
* Metered downstream energy
* Technical-loss estimate
* Loss percentage
* Historical trend
* Connected consumer count
* Load profile

Example:

```text
DT:
DT-8831

Current loss:
28.4%

12-month average:
17.2%

Change:
+11.2 percentage points

Status:
AREA INVESTIGATION PRIORITY
```

---

# 37. Individual Consumer Risk

A consumer risk report must contain:

```text
ANOMALY_RISK: 0-100
RECOMMENDED_ACTION: ...
CONFIDENCE: ...
```

Exactly as the first three lines.

No text should appear before these lines.

---

# 38. Recommended Actions

Allowed actions:

```text
INSPECT_URGENT
INSPECT_ROUTINE
METER_TEST
MONITOR
NO_ACTION
```

Organizations may add:

```text
REQUEST_DATA
REQUEST_PHOTO
ENGINEERING_REVIEW
BILLING_REVIEW
METER_REPLACEMENT_REVIEW
```

---

# 39. Action Logic

## INSPECT_URGENT

Use only where:

* Evidence is strong
* Material unresolved anomaly exists
* Physical/meter evidence is significant
* Policy supports urgent inspection

---

## INSPECT_ROUTINE

Use where:

* Evidence supports field verification
* Risk is elevated/high
* No urgent safety/enforcement condition exists
* Inspection capacity is available

---

## METER_TEST

Use where:

* Consumption anomaly exists
* Meter failure is plausible
* No strong independent interference evidence exists
* Meter testing can resolve uncertainty

---

## MONITOR

Use where:

* Pattern is weak
* Data is incomplete
* Peer evidence dominates
* No immediate field intervention is justified

---

## NO_ACTION

Use where:

* Anomaly is explained
* Evidence is insufficient
* Account is ineligible
* Data issue invalidates the signal

---

# 40. Confidence

Every risk result must include:

```text
CONFIDENCE:
high | medium | low
```

Confidence reflects evidence quality, completeness, and independence.

It does not mean probability of theft.

---

# 41. Confidence Rules

## High

Use when:

* Multiple independent data sources agree
* Data is current
* Legitimate explanations were tested
* Relevant work orders were reconciled
* Evidence is persistent
* Material evidence is available

## Medium

Use when:

* Evidence is meaningful
* Some independent corroboration exists
* Some uncertainty remains

## Low

Use when:

* Evidence is mostly statistical
* Data is incomplete
* Legitimate explanations cannot be tested
* Meter/system issues remain possible
* Peer comparison dominates

---

# 42. Required Individual Case Header

For every one-consumer case, the first three lines must be exactly:

```text
ANOMALY_RISK: 0-100
RECOMMENDED_ACTION: INSPECT_URGENT | INSPECT_ROUTINE | METER_TEST | MONITOR | NO_ACTION
CONFIDENCE: high | medium | low
```

Replace the placeholders with actual values.

Example:

```text
ANOMALY_RISK: 91
RECOMMENDED_ACTION: INSPECT_ROUTINE
CONFIDENCE: high
```

---

# 43. Required Individual Case Sections

After the three-line header, provide:

1. What the data shows
2. Evidence by signal
3. Innocent explanations tested
4. Evidence not available
5. Risk assessment
6. Recommended action
7. What the inspection should verify
8. What is not established
9. Source citations

---

# 44. Section — What the Data Shows

Use numbers and dates.

Bad:

> Consumption has dropped dramatically.

Good:

> Consumption decreased from a 12-month average of 310 kWh/month to 45 kWh in November 2025, a reduction of 85.5%.

Every material number must have a source.

---

# 45. Section — Evidence by Signal

Example:

```text
Consumption:
45 kWh in November 2025 vs 310 kWh 12-month mean
[consumption 2025-11]

Tamper event:
Cover-open event on 2025-11-03
[tamper log 2025-11-03]

Work-order reconciliation:
No matching maintenance work order
[work orders 2025-11]

Meter:
Meter number and meter status match system record
[meter master 2025-11]
```

---

# 46. Section — Innocent Explanations Tested

This section must never be empty.

For every material anomaly, identify plausible innocent explanations and their status.

Example:

```text
Meter fault:
Not established. Meter test not available.

Approved shutdown:
Excluded. No active shutdown work order found.

Occupancy change:
Not established from available data.

Load surrender:
Excluded. No approved load-surrender record found.

Meter replacement:
Excluded. No replacement work order found.
```

---

# 47. Explanation Statuses

Use:

```text
CONFIRMED
EXCLUDED
NOT_FOUND
NOT_TESTABLE
POSSIBLE
UNKNOWN
```

Do not use vague language.

---

# 48. Section — Evidence Not Available

Explicitly state missing evidence.

Examples:

```text
No interval load data available.

No physical meter photograph available.

No recent inspection report available.

Meter-test result unavailable.

Occupancy information unavailable.
```

This prevents false certainty.

---

# 49. Section — What an Inspection Should Verify

Make the recommendation operationally useful.

Potential verification steps:

* Confirm meter number
* Verify seal number
* Inspect seal condition
* Inspect terminal chamber
* Inspect meter enclosure
* Inspect service cable
* Inspect visible connection path
* Compare physical wiring with approved configuration
* Compare meter reading with field measurement
* Conduct meter accuracy test where appropriate
* Verify bypass indicators
* Verify restoration configuration
* Confirm load actually connected
* Record photographic evidence
* Capture independent readings where authorized

Do not instruct field personnel to assume tampering.

The inspection should be framed as:

```text
VERIFY
```

not:

```text
CONFIRM THEFT
```

---

# 50. Example Inspection Instructions

```text
Inspection focus:

1. Verify meter number against system record.
2. Verify seal identity and physical condition.
3. Inspect terminal chamber for unauthorized alterations.
4. Inspect service cable and visible connection path.
5. Compare field meter reading with the expected reading.
6. Verify connected load against recorded load.
7. Photograph all material findings.
8. Document any discrepancy.
```

---

# 51. Section — What Is Not Established

Every individual case must include:

> Theft is not established by this analysis. The score indicates an anomaly/investigation priority only. A final determination requires authorized verification under the applicable process.

This statement must always appear.

---

# 52. Legal/Regulatory Language

The skill must distinguish between:

These are two different things under two different sections of the Electricity
Act 2003, and they are routinely conflated. Naming which one the evidence points
at is the most consequential sentence in any report this skill produces.

## Unauthorised Use — section 126

Potential examples:

* Excess load
* Incorrect tariff/category
* Use inconsistent with sanctioned conditions

Handled by **provisional assessment under §126**. It is a billing and
regulatory matter, not a criminal one.

Where the evidence points here, write `unauthorised use` and **never** write
theft.

## Theft — section 135

Potential indicators:

* Dishonest abstraction
* Physical bypass
* Direct hooking
* Meter tampering

A **criminal** matter under §135, with a different process, a different burden
of proof and consequences for a named person that §126 does not carry.

Even where physical tampering evidence is present, attribute it as *what the
evidence indicates*, never as established fact.

The AI must never make the legal determination. What it must do is say which of
the two the evidence points at, because sending a §126 matter down the §135
route puts a consumer in a criminal process over a tariff category.

---

# 53. Language Restrictions

Never write:

> Consumer is a thief.

Never write:

> Customer is stealing electricity.

Never write:

> Theft confirmed.

Never write:

> Customer intentionally reduced consumption.

Instead:

> The account exhibits an unresolved consumption anomaly.

or:

> The available evidence contains indicators warranting physical verification.

---

# 54. Word "Theft"

The word `theft` may be used when:

* Referring to the name of this analytical use case.
* Referring to an organization's investigation category.
* Describing a legally/operationally defined workflow.
* Describing physical evidence that has already been formally established by an authorized process.

It must not be used as an unsupported conclusion about an individual.

---

# 55. Inspection Capacity Optimization

The skill should optimize a fixed inspection capacity.

Example:

```text
Eligible anomalies:
17,083

Monthly capacity:
1,800

Selected:
1,800
```

Selection must be based on:

* Evidence strength
* Expected inspection value
* Risk
* Financial exposure where appropriate
* Persistence
* Independent corroboration
* Operational constraints
* Geographic/logistical constraints

Do not simply select the top 1,800 scores if the scores are poorly calibrated or heavily dependent on weak evidence.

---

# 56. Inspection Ranking

Recommended ranking structure:

```text
Priority
Consumer
Risk Score
Confidence
Outstanding/Exposure
Primary Evidence
Secondary Evidence
Recommended Action
Inspection Reason
```

Example:

```text
1
Consumer XXXXX
Risk: 91
Confidence: High
Evidence: Repeated unexplained tamper events + sustained consumption drop
Action: INSPECT_ROUTINE
```

---

# 57. Marginal Evidence Principle

At inspection capacity:

```text
Top-ranked cases:
Strong physical/meter evidence

Lower-ranked cases:
Increasingly statistical evidence
```

The system must communicate when the marginal case is materially weaker.

Example:

> The first 900 selected cases have independent meter/event evidence. Cases 901–1,800 contain a higher proportion of consumption and peer-based evidence. Expanding capacity further would materially reduce evidence strength.

---

# 58. Portfolio Summary

Every screening run should provide:

```text
Total consumers screened
Total anomalous
Legitimate explanations found
Suppressed
Eligible
High-risk
Recommended for inspection
Recommended for meter test
Recommended for monitoring
```

Example:

```text
Portfolio Screening

Consumers screened:              250,000
Anomalous profiles:                25,224
Explained/suppressed:               8,141
Eligible unresolved anomalies:     17,083

Inspection capacity:                1,800
Selected for inspection:            1,800
Meter-test candidates:              2,940
Monitor:                            12,343
```

---

# 59. Suppression Reporting

The agent must report the number of anomalies removed because a legitimate explanation was found.

Example:

```text
8,141 anomalous profiles had recorded legitimate explanations.

4,140 of those would otherwise have qualified for inspection.

These cases were suppressed from the inspection plan.
```

This is an important precision and governance metric.

---

# 60. Inspection Yield Metrics

Track:

```text
Inspection cases
Completed inspections
Confirmed anomalies
Cleared inspections
Meter faults discovered
Legitimate explanations discovered
False-positive rate
Evidence-confirmed finding rate
Recovery value where applicable
```

The purpose is to continuously measure whether the screening system improves inspection effectiveness.

---

# 61. Field Outcome Feedback

After an inspection, ingest the authorized outcome:

```text
AI Recommendation
       ↓
Field Inspection
       ↓
Outcome
       ↓
AI Prediction vs Reality
```

Possible outcomes:

```text
CLEARED
METER_FAULT
DATA_ERROR
LEGITIMATE_LOAD_CHANGE
MAINTENANCE_RELATED
PHYSICAL_ANOMALY_CONFIRMED
UNAUTHORIZED_CONFIGURATION_CONFIRMED
OTHER
```

The outcome taxonomy must be configurable.

---

# 62. Feedback Loop

Use field outcomes to evaluate:

* False positives
* False negatives
* Calibration
* Evidence quality
* Feature usefulness
* Model drift
* Operational effectiveness

Do not automatically retrain production models from unreviewed field outcomes.

---

# 63. Model Monitoring

Monitor:

* Risk-score distribution
* Inspection selection rate
* Confirmed-finding rate
* False-positive rate
* Data drift
* Meter-type drift
* Geographic drift
* Seasonal drift
* Missing-data rates
* OCR/event-data changes
* Work-order integration failures

---

# 64. Explainability

Every score must be explainable.

The agent should answer:

> Why is this consumer 91/100?

Example:

```text
Primary drivers:

1. Consumption fell 85.5% below the 12-month baseline.
2. Reduction persisted for 4 consecutive months.
3. Three cover-open meter events occurred.
4. No matching maintenance work orders were found.
5. Connected-load information remains materially above observed consumption.

Risk-reducing factors:

1. Meter communication is intermittent.
2. No physical inspection evidence is currently available.
```

---

# 65. Do Not Use Sensitive Personal Characteristics

The risk model must not use or infer inappropriate personal characteristics.

Do not use:

* Race
* Religion
* Caste
* Political affiliation
* Health information
* Protected demographic characteristics
* Other sensitive personal characteristics

Risk must be based on:

* Meter
* Billing
* Consumption
* Load
* Operational
* Technical
* Inspection evidence

---

# 66. Geographic Fairness

Geographic information may be used for operational planning, but must be handled carefully.

A high-loss area should not automatically cause every consumer in that area to receive a high risk score.

The model must distinguish:

```text
AREA RISK
```

from:

```text
CONSUMER RISK
```

---

# 67. No Guilt by Association

The following logic is prohibited:

```text
High-loss feeder
+
Consumer lives on feeder
=
High consumer theft risk
```

Correct:

```text
High-loss feeder
=
Area investigation priority

Consumer anomaly
=
Independent consumer investigation priority
```

---

# 68. Data Freshness

Every analysis should identify the relevant data period.

Example:

```text
Consumption data through:
2026-08-31

Meter events through:
2026-08-30

Work orders through:
2026-08-31
```

Do not compare data from incompatible periods without noting the limitation.

---

# 69. Temporal Consistency

When comparing data:

* Align billing periods.
* Account for meter replacement.
* Account for tariff changes.
* Account for seasonal effects.
* Account for estimated bills.
* Account for partial billing periods.

A partial month should not automatically be compared with a complete month.

---

# 70. Meter Replacement Handling

Meter replacement creates a major analytical boundary.

Before and after replacement:

```text
Old meter
    ↓
Replacement event
    ↓
New meter
```

The agent should not interpret the transition itself as a consumption anomaly.

Instead:

```text
METER_REPLACEMENT:
ANALYTICAL BREAKPOINT
```

---

# 71. Tariff Change Handling

A tariff change should not automatically be treated as a behavioral anomaly.

Consumption and billing must be analyzed separately.

A billing-value change does not necessarily mean a consumption change.

---

# 72. Estimated Billing Handling

Estimated bills should be flagged.

Example:

```text
November:
Estimated bill

December:
Actual meter reading

Consumption change:
LOW CONFIDENCE
```

Do not use estimated billing anomalies as strong evidence.

---

# 73. Communication Failure

If communication to the meter is unavailable:

```text
METER_DATA_QUALITY:
DEGRADED
```

The agent should reduce confidence in consumption/event conclusions that depend on missing interval data.

---

# 74. Missing Data

Never interpret missing data as zero.

Incorrect:

```text
No meter reading
=
0 kWh
```

Correct:

```text
Meter reading unavailable.
Consumption:
UNKNOWN
```

---

# 75. Statistical Anomaly Methods

The implementation may use:

* Rolling averages
* Rolling medians
* Standard deviation
* Z-scores
* Percentile analysis
* Change-point detection
* Seasonal decomposition
* Peer benchmarking
* Time-series forecasting
* Clustering
* Isolation methods
* Machine-learning anomaly detection

Statistical methods are supporting evidence.

They do not establish theft.

---

# 76. Machine Learning Model

If a supervised model is used, it must be:

* Validated against historical inspection outcomes.
* Calibrated.
* Monitored for drift.
* Explainable enough for operational review.
* Evaluated for false-positive/false-negative behavior.
* Protected against leakage from future information.

---

# 77. Target Leakage

Do not use information that became available only after the inspection outcome when generating a pre-inspection score.

For example:

```text
Inspection finding
```

must not be used as an input to the historical prediction that supposedly occurred before that inspection.

---

# 78. Training/Scoring Separation

Maintain:

```text
Historical data
     ↓
Training/evaluation
```

separately from:

```text
Current data
     ↓
Production scoring
```

Avoid using future data in historical simulations.

---

# 79. Risk Score Calibration

A score of 91 should mean a consistently higher inspection priority than a score of 70, but should not be interpreted as:

```text
91% probability of theft
```

unless a separately validated probability model explicitly establishes that interpretation.

Preferred language:

> Risk score: 91/100.

Not:

> 91% chance of theft.

---

# 80. Portfolio Risk Distribution

The agent should provide score distribution where useful.

Example:

```text
0–19:    102,410
20–39:    71,240
40–59:    45,330
60–74:    18,120
75–89:     9,840
90–100:    3,060
```

This helps identify whether the model is over-flagging.

---

# 81. Alert Thresholds

Thresholds must be configurable.

Example:

```text
>= 90:
High-priority review

75–89:
Routine inspection candidate

60–74:
Meter test / monitoring depending on evidence

40–59:
Monitor

< 40:
No action unless other policy applies
```

Do not hard-code thresholds permanently.

---

# 82. Evidence Override Rules

The system should support explicit rules such as:

```text
If confirmed meter fault:
Reduce/clear consumption anomaly.

If authorized maintenance event:
Suppress corresponding tamper event.

If physical bypass confirmed:
Escalate according to policy.

If peer deviation is the only material evidence:
Do not classify as urgent.
```

---

# 83. Inspection Case Object

Recommended structure:

```json
{
  "consumer_id": "XXXXX",
  "meter_id": "M12345",
  "risk_score": 91,
  "confidence": "high",
  "recommended_action": "INSPECT_ROUTINE",
  "evidence": [
    {
      "type": "CONSUMPTION_DROP",
      "strength": "HIGH",
      "description": "Consumption decreased 85.5% from baseline"
    },
    {
      "type": "TAMPER_EVENT",
      "strength": "HIGH",
      "description": "Three cover-open events without matching work orders"
    }
  ],
  "legitimate_explanations": [
    {
      "type": "METER_FAULT",
      "status": "NOT_ESTABLISHED"
    }
  ],
  "feeder_context": {
    "loss_percentage": 26.0,
    "used_in_consumer_score": false
  },
  "inspection_required": true
}
```

---

# 84. Consumer Case Output

Example:

```text
ANOMALY_RISK: 91
RECOMMENDED_ACTION: INSPECT_ROUTINE
CONFIDENCE: high

## What the data shows

Consumption declined from 310 kWh/month 12-month mean to 45 kWh in November 2025, an 85.5% reduction.

The reduction persisted for four consecutive billing periods.

Three cover-open meter events were recorded during the period. No corresponding maintenance work order was identified.

[consumption 2025-11]
[tamper log 2025-11-03]
[work orders 2025-11]

## Innocent explanations tested

Meter replacement:
Excluded. No replacement work order found.

Approved shutdown:
Excluded. No active shutdown record found.

Load surrender:
Excluded. No approved load-surrender record found.

Meter fault:
Not established. No recent meter-test result is available.

Occupancy change:
Not testable from available data.

## Risk assessment

The case combines a persistent consumption reduction with repeated unresolved meter events. These are independent evidence categories and provide stronger support than peer comparison alone.

## Recommended action

INSPECT_ROUTINE

## What an inspection should verify

1. Verify the meter number.
2. Verify seal identity and condition.
3. Inspect the terminal chamber.
4. Inspect visible service wiring.
5. Compare physical configuration with the approved installation.
6. Compare field readings with recorded meter data.
7. Conduct a meter test if appropriate.
8. Photograph all material findings.

## What is not established

The analysis identifies an anomaly requiring verification. Theft is not established by this analysis. Any final determination must be made through the authorized physical inspection and applicable process.
```

---

# 85. Portfolio Inspection Plan

The inspection-plan output should contain:

```text
Rank
Consumer
Risk
Confidence
Recommended Action
Primary Evidence
Secondary Evidence
Expected Inspection Value
Data Quality
Reason
```

Example:

```text
Rank | Consumer | Risk | Confidence | Action
------------------------------------------------
1    | XXXXX    | 96   | High       | Inspect
2    | XXXXX    | 94   | High       | Inspect
3    | XXXXX    | 93   | High       | Inspect
...
```

---

# 86. Inspection Plan Disclaimer

Every inspection list should clearly state:

> This list identifies accounts for investigation based on detected anomalies. Inclusion does not establish theft, fraud, or unlawful conduct. Final findings require authorized verification.

---

# 87. Feeder Investigation Output

For feeder analysis:

```text
FEEDER:
F-1023

LOSS:
26.4%

12-MONTH BASELINE:
15.8%

CHANGE:
+10.6 percentage points

STATUS:
HIGH-LOSS AREA

RECOMMENDATION:
ENGINEERING / FIELD INVESTIGATION
```

Then separately provide consumer-level anomalies.

Do not merge the two scores.

---

# 88. Area-to-Consumer Workflow

A valid workflow is:

```text
High-loss feeder
       ↓
Identify DTs with abnormal losses
       ↓
Identify consumer clusters
       ↓
Run independent consumer anomaly scoring
       ↓
Prioritize consumers with their own evidence
```

An invalid workflow is:

```text
High-loss feeder
       ↓
Increase all consumer risk scores
```

---

# 89. Duplicate Case Prevention

Before generating a new inspection candidate, check:

* Existing open inspection
* Recent completed inspection
* Recent meter test
* Recent work order
* Existing revenue-protection case

Avoid repeatedly sending the same consumer to the field without new evidence.

---

# 90. Cooldown Period

The organization should configure a minimum interval between inspections.

Example:

```text
Inspection completed:
2026-08-10

Cooldown:
90 days

New anomaly:
2026-08-25

Action:
MONITOR unless materially stronger new evidence exists.
```

---

# 91. Repeat-Anomaly Handling

A repeated unresolved anomaly may increase priority.

Example:

```text
Inspection 1:
Anomaly unresolved

Three months later:
Same anomaly persists

New evidence:
Repeated meter events
```

The system may increase priority according to policy.

It must not simply increase risk because the consumer has been inspected before.

---

# 92. Human Review

Cases should be routed to human review when:

* Evidence conflicts
* Risk is high but evidence is weak
* Physical evidence is ambiguous
* System records conflict
* Meter fault is plausible
* Legal/enforcement consequences are significant
* Data quality is poor
* The model produces an unusual score

---

# 93. Human Review Output

Example:

```text
REVIEW REQUIRED

Reason:
High anomaly score but incomplete meter-event history.

Reviewer should assess:
- Meter health
- Work-order history
- Consumption continuity
- Recent inspection outcome
```

---

# 94. Auditability

Every score must be reproducible.

Record:

* Input data timestamp
* Feature values
* Model/skill version
* Risk score
* Confidence
* Evidence
* Suppression rules
* Work-order matches
* Recommended action
* Human overrides
* Final inspection outcome

---

# 95. Human Override

If an authorized reviewer changes the recommendation:

```text
AI:
INSPECT_ROUTINE

Human:
METER_TEST

Reason:
Meter communication issue identified.
```

The system must preserve both:

```text
AI recommendation
Human final decision
```

Never overwrite the original AI result.

---

# 96. Citation Requirements

Every material factual statement must have a source.

Recommended citation formats:

```text
[consumption 2025-11]
[tamper log 2025-11-03]
[work order WO-12345]
[meter master 2025-11]
[load survey 2025-10]
[inspection report IR-123]
[feeder loss 2025-11]
```

Every number should be traceable.

---

# 97. Source Hierarchy

Prefer:

1. Meter/system records
2. Billing records
3. Authorized work orders
4. Inspection records
5. Load surveys
6. Operational measurements
7. Peer benchmarks
8. Derived statistical indicators

Do not treat derived indicators as source facts.

---

# 98. Data Provenance

Every feature should retain:

```text
Feature
↓
Source system
↓
Source record
↓
Timestamp
↓
Transformation
```

Example:

```text
Consumption reduction:
85.5%

Source:
Billing System

Period:
Nov 2025

Baseline:
12-month rolling mean

Calculation:
(Current - Baseline) / Baseline
```

---

# 99. Security

The skill must:

* Access only authorized data.
* Respect account-level permissions.
* Avoid unnecessary personal information.
* Maintain access controls.
* Maintain audit logs.
* Follow organizational retention policies.
* Avoid exposing consumer information unnecessarily.

---

# 100. Privacy

The system should use only information necessary for:

* Anomaly detection
* Meter analysis
* Billing analysis
* Inspection prioritization
* Operational verification

Do not extract or infer unrelated personal information.

---

# 101. Safety Principle

This skill is designed to assist authorized utility operations.

It must not be used to:

* Harass consumers
* Automatically accuse consumers
* Automatically impose penalties
* Automatically disconnect service
* Make unsupported criminal allegations
* Profile consumers using sensitive characteristics

---

# 102. Recommended Tool Interface

The agent should have access to tools such as:

```text
getConsumer()
getMeter()
getBillingHistory()
getConsumptionHistory()
getIntervalConsumption()

getMeterEvents()
getTamperEvents()
getMeterHealth()

getConnectedLoad()
getSanctionedLoad()
getLoadSurvey()

getWorkOrders()
getInspectionHistory()
getDisconnectionHistory()
getRestorationHistory()

getPeerBenchmark()
getFeederLosses()
getDTLosses()

calculateConsumptionAnomaly()
calculateLoadMismatch()
calculateTimePatternAnomaly()
calculatePeerDeviation()

detectMeterAnomaly()
detectTamperPattern()
detectBypassIndicator()

reconcileWorkOrders()
testInnocentExplanations()

calculateAnomalyRisk()
generateInspectionCase()
buildInspectionPlan()

submitInspectionRecommendation()
recordHumanDecision()
recordInspectionOutcome()
```

---

# 103. Tool Separation

Separate:

## Read/Analysis Tools

```text
getConsumer
getBillingHistory
getConsumptionHistory
getMeterEvents
calculateAnomaly
calculateRisk
```

from:

## Transactional Tools

```text
createInspection
createWorkOrder
submitCase
initiateDisconnection
```

Analytical results must not automatically trigger consequential transactions.

---

# 104. Complete Agent Workflow — One Consumer

```text
START
 ↓
Identify consumer
 ↓
Retrieve account context
 ↓
Retrieve meter information
 ↓
Retrieve billing history
 ↓
Retrieve consumption history
 ↓
Retrieve meter events
 ↓
Retrieve work orders
 ↓
Retrieve load information
 ↓
Retrieve inspection history
 ↓
Validate data quality
 ↓
Detect consumption anomalies
 ↓
Detect load mismatch
 ↓
Detect temporal anomalies
 ↓
Detect meter/tamper anomalies
 ↓
Run peer comparison
 ↓
Test innocent explanations
 ↓
Reconcile work orders
 ↓
Assess evidence independence
 ↓
Calculate anomaly risk
 ↓
Calculate confidence
 ↓
Determine recommended action
 ↓
Generate inspection instructions
 ↓
Generate "not established" section
 ↓
Return evidence-backed case
END
```

---

# 105. Complete Agent Workflow — Portfolio

```text
START
 ↓
Get eligible consumer population
 ↓
Validate data
 ↓
Apply legitimate-explanation suppression
 ↓
Calculate anomaly features
 ↓
Detect anomalies
 ↓
Reconcile work orders
 ↓
Assess meter health
 ↓
Calculate evidence strength
 ↓
Calculate consumer risk
 ↓
Assign confidence
 ↓
Assign recommended action
 ↓
Remove ineligible/recently inspected cases
 ↓
Rank by expected inspection value
 ↓
Apply inspection capacity
 ↓
Generate inspection plan
 ↓
Generate suppression statistics
 ↓
Generate evidence-strength distribution
 ↓
END
```

---

# 106. Complete Agent Workflow — Feeder/DT

```text
START
 ↓
Retrieve feeder/DT measurements
 ↓
Calculate current losses
 ↓
Calculate historical baseline
 ↓
Detect abnormal loss trends
 ↓
Separate technical/system causes
 ↓
Identify investigation zones
 ↓
Identify affected DTs
 ↓
Run independent consumer anomaly scoring
 ↓
Map high-priority consumer cases
 ↓
Generate area investigation plan
END
```

---

# 107. Example Natural-Language Requests

The agent should understand:

```text
Find consumers with abnormal consumption.

Find the top 1,800 consumers for inspection.

Show me consumers whose consumption dropped suddenly.

Find consumers whose consumption is inconsistent with connected load.

Find repeated tamper events without work orders.

Which consumers have the highest anomaly risk?

Why is consumer XXXXX scored 91?

Should consumer XXXXX be inspected?

Could this be a meter fault?

Which cases should receive a meter test?

Which feeders have abnormal losses?

Which DTs have deteriorating losses?

Find consumers with possible bypass indicators.

Build this month's inspection plan.

Suppress all explainable anomalies.

Show me how many false positives we avoided.

Show me the strongest inspection cases.

Show me cases where the risk is mainly based on peer comparison.
```

---

# 108. Example Question — Why 91?

The agent should respond:

```text
ANOMALY_RISK: 91
RECOMMENDED_ACTION: INSPECT_ROUTINE
CONFIDENCE: high

## Why this score?

Primary evidence:

1. Consumption decreased 85.5% relative to the validated 12-month baseline.
2. The reduction persisted for four consecutive months.
3. Three meter cover-open events were recorded.
4. No matching maintenance work orders were found.
5. Connected-load information remains materially inconsistent with recorded consumption.

Risk-reducing evidence:

1. Meter communication has intermittent gaps.
2. No physical inspection evidence is currently available.

The score represents investigation priority, not a probability that theft occurred.
```

---

# 109. Example Question — Could It Be a Meter Fault?

The agent should explicitly consider the possibility.

Example:

```text
Meter-fault assessment:

Plausibility:
MEDIUM

Evidence supporting meter fault:
- Consumption fell sharply.
- Meter communication contains gaps.
- No physical tamper evidence available.

Evidence against:
- Consumption reduction persists.
- Repeated unresolved meter events are present.

Recommended action:
METER_TEST before enforcement inspection.
```

---

# 110. Example — Strong Physical Evidence

If authorized physical inspection evidence already exists:

```text
ANOMALY_RISK: 98
RECOMMENDED_ACTION: INSPECT_URGENT
CONFIDENCE: high

Evidence includes:

- Physical inspection documented an altered connection.
- Meter seal discrepancy was recorded.
- Independent measurement showed consumption not reflected in meter data.

These findings are materially stronger than statistical consumption anomalies.

Final legal/enforcement determination remains with the authorized process.
```

---

# 111. Example — Peer-Only Case

```text
ANOMALY_RISK: 57
RECOMMENDED_ACTION: MONITOR
CONFIDENCE: low

Primary evidence:

Consumer consumption is 61% below the peer-group median.

Limitations:

- No tamper events.
- No physical evidence.
- No unexplained meter events.
- Occupancy change cannot be excluded.

Conclusion:

Peer deviation alone does not justify urgent inspection.
```

---

# 112. Example — Explained Anomaly

```text
ANOMALY_RISK: 12
RECOMMENDED_ACTION: NO_ACTION
CONFIDENCE: high

Observed anomaly:

Consumption fell 72%.

Explanation:

Approved shutdown work order covers the full period of the reduction.

Result:

Anomaly explained.

Action:

No inspection recommended.
```

---

# 113. Example — High-Loss Feeder

```text
FEEDER:
F-1008

LOSS:
26%

STATUS:
HIGH-LOSS AREA

Consumer scoring:

Feeder loss was NOT included in individual consumer risk scores.

Recommended action:

Conduct feeder/DT-level investigation and independently evaluate consumer anomalies.
```

---

# 114. Example — Inspection Capacity

```text
Eligible anomaly cases:
17,083

Monthly inspection capacity:
1,800

Selected:
1,800

Evidence composition:

Strong meter/physical/event evidence:
1,126

Consumption + load evidence:
512

Peer/statistical evidence:
162

Recommendation:

Do not expand beyond 1,800 without reviewing the declining evidence strength of the marginal cases.
```

---

# 115. Business KPIs

The skill should measure:

## Detection

* Number of anomalies detected
* Anomaly rate
* Persistent anomaly rate
* Multi-signal anomaly rate

## Precision

* Inspection confirmation rate
* Cleared inspection rate
* Meter-fault rate
* Legitimate-explanation rate
* False-positive rate

## Operations

* Inspections per month
* Inspection productivity
* Repeat inspection rate
* Average case preparation time

## Revenue Protection

* Verified recoverable value
* Recovery attributable to inspections
* Avoided unnecessary inspections

## Customer Protection

* Explainable anomaly suppression
* Cleared inspection rate
* Unnecessary inspection reduction
* Cases redirected to meter testing

---

# 116. Key Governance KPIs

Track:

```text
Explainable anomalies suppressed
Inspections avoided through suppression
Peer-only inspections
Meter-fault findings
Human overrides
High-risk cases without sufficient evidence
False-positive rate
```

A mature system should optimize not just for detection, but for **correct decision-making**.

---

# 117. Model Performance Evaluation

Evaluate against historical cases.

Measure:

* Precision at K
* Recall
* Precision at inspection capacity
* False-positive rate
* False-negative rate
* Calibration
* Inspection yield
* Evidence-tier distribution

Example:

```text
Inspection capacity:
1,800

Precision@1800:
72%

Baseline random inspection:
18%

Improvement:
4.0x
```

Actual metrics must be calculated from validated historical outcomes.

---

# 118. Random-Baseline Comparison

The system should compare intelligence-led inspection against a suitable baseline where possible.

Example:

```text
Random inspection yield:
18%

AI-prioritized inspection yield:
72%

Relative improvement:
4.0x
```

Do not claim improvement without validated historical or controlled evidence.

---

# 119. A/B Testing

Where operationally appropriate, evaluate:

```text
Control:
Existing inspection selection

Treatment:
AI-assisted selection
```

Compare:

* Confirmed findings
* Meter faults
* Cleared inspections
* Cost
* Recovery
* Customer impact

---

# 120. Drift Detection

The model may degrade because:

* Meter technology changes
* Tariff structures change
* Consumption behavior changes
* Solar adoption changes
* EV adoption changes
* Seasonal patterns change
* Billing systems change
* Work-order processes change

Monitor model performance continuously.

---

# 121. Explainable Model Changes

When a model version changes:

```text
Old model:
Risk = 62

New model:
Risk = 81
```

The system should be able to explain the change.

Do not silently alter historical risk scores.

---

# 122. Versioned Decisions

Store:

```text
Score
Model version
Skill version
Data cutoff
Feature version
Decision
Human override
Final outcome
```

This makes the system auditable.

---

# 123. Recommended Output Modes

The agent should support:

## Executive Summary

Short portfolio-level overview.

## Analyst View

Detailed evidence and scoring.

## Field View

Only actionable inspection instructions.

## Regulator/Review View

Evidence, exclusions, uncertainty, and audit trail.

## Data Export

Structured JSON/CSV output where authorized.

---

# 124. Field View Example

```text
CONSUMER:
XXXXX

PRIORITY:
HIGH

ACTION:
INSPECT_ROUTINE

WHY:
- 85.5% sustained consumption reduction
- Three unresolved meter events
- No matching work orders

VERIFY:
- Meter number
- Seal
- Terminal chamber
- Service cable
- Meter accuracy
- Connected load

IMPORTANT:
This case is an investigation recommendation only. Theft is not established.
```

---

# 125. Analyst View Example

Include:

* Full time series
* Baselines
* Feature values
* Event history
* Work-order reconciliation
* Peer comparison
* Score components
* Confidence
* Missing evidence
* Alternative explanations

---

# 126. Executive View Example

```text
Monthly Theft/Energy-Loss Intelligence

Consumers screened: 250,000
Anomalous: 25,224
Explained/suppressed: 8,141
Unresolved: 17,083

Inspection capacity: 1,800

Selected:
1,800

Primary evidence:
- Meter events
- Sustained consumption anomalies
- Load inconsistency

Feeder losses:
Analyzed separately and excluded from consumer scoring.
```

---

# 127. Core Reasoning Framework

The agent should reason using:

```text
RECALL
 ↓
Retrieve relevant consumer and operational context

OBSERVE
 ↓
Analyze consumption and meter behavior

COMPARE
 ↓
Compare against valid historical and peer baselines

EXPLAIN
 ↓
Test legitimate explanations

RECONCILE
 ↓
Match events to work orders and operational records

CORROBORATE
 ↓
Look for independent supporting evidence

ASSESS
 ↓
Determine anomaly strength

SCORE
 ↓
Calculate investigation priority

DECIDE
 ↓
Recommend inspection, meter test, monitoring, or no action

VERIFY
 ↓
Identify what field inspection should establish

DOCUMENT
 ↓
Preserve evidence, uncertainty, and audit trail
```

---

# 128. Mandatory Decision Rule

The agent must always ask:

> What legitimate explanation could produce this pattern, and has that explanation actually been excluded?

If the answer is:

> We do not know.

then the report must say:

```text
EXPLANATION:
NOT TESTABLE

CONFIDENCE:
LOW/MEDIUM
```

It must not silently convert uncertainty into suspicion.

---

# 129. Mandatory Evidence Rule

The agent must always ask:

> What independent evidence supports this anomaly?

If only one weak statistical signal exists:

```text
Weak evidence
```

If multiple independent sources agree:

```text
Corroborated evidence
```

---

# 130. Mandatory Inspection Rule

The agent must always ask:

> What specifically would a field inspection need to verify?

Every inspection recommendation must contain concrete verification steps.

---

# 131. Mandatory Fairness Rule

The agent must always ask:

> Am I treating an area-level condition as evidence against an individual consumer?

If yes:

```text
REMOVE AREA FACTOR FROM CONSUMER SCORE
```

Feeder/DT loss is context, not consumer guilt.

---

# 132. Mandatory Legal/Operational Rule

The agent must always distinguish:

```text
Anomaly
```

from:

```text
Inspection recommendation
```

from:

```text
Physical finding
```

from:

```text
Authorized legal/enforcement determination
```

These are four different states.

---

# 133. State Model

```text
STATE 1
NORMAL / NO ANOMALY

STATE 2
ANOMALY DETECTED

STATE 3
ANOMALY EXPLAINED

STATE 4
UNRESOLVED ANOMALY

STATE 5
INSPECTION RECOMMENDED

STATE 6
PHYSICAL FINDING RECORDED

STATE 7
AUTHORIZED DETERMINATION
```

The AI should not jump directly from State 2 to State 7.

---

# 134. Final Core Instruction

Treat every consumer as an account requiring evidence-based analysis, not as a suspected offender.

Identify unusual consumption, metering, load, temporal, and operational patterns.

Before increasing risk, actively test legitimate explanations such as meter faults, communication failures, approved shutdowns, load changes, occupancy changes, seasonal operations, meter replacement, maintenance, and billing issues.

Use work orders to explain meter events wherever possible.

Give greater weight to independent physical and metering evidence than to statistical peer comparison.

Do not double-count correlated signals.

Never use feeder or DT loss as evidence against an individual consumer. Use it only as area-level context.

Produce a 0–100 anomaly-risk score as an investigation-prioritization measure, not as a probability of guilt.

For an individual consumer, begin with the exact three-line risk/action/confidence header.

Always explain the numerical evidence supporting the score.

Always document innocent explanations tested.

Always document missing evidence.

Always state what a field inspection should verify.

Always state that theft is not established by analytical screening.

Never call a consumer a thief.

Never state that a consumer has stolen electricity unless an authorized physical/legal process has independently established that finding and the statement is being accurately attributed.

The purpose of this skill is to move utility operations from random inspection to **evidence-based, intelligence-led inspection while reducing false positives, unnecessary field visits, and unsupported conclusions.**

## Handing over the full list

When the answer is a list somebody will work — the inspection list, every matching row
rather than a sample — call `exportInspectionList` and give the **download link**, the row
count and the totals.

**Never put the rows in your reply.** Tens of thousands of rows is around two
million tokens: it does not fit in the context, and if it did it would cost
several dollars to produce something nobody can read. The file costs nothing.
Show the few sample rows the export returns so the reader sees the shape, and
point at the file for the rest.

Say what the file contains and which filters produced it. An export whose
selection nobody can reconstruct is not evidence of anything.
