---
name: illegal-restoration-detection
description: >
  Detect and prioritize potentially unauthorized restoration of electricity after a temporary or permanent disconnection by correlating executed disconnection events, meter readings, consumption, restoration orders, payments, work orders, and field evidence. modes: * portfolio * consumer * inspection_planning * verification
allowed-tools:
  - buildRestorationTasks
  - exportRestorationCases
  - getBillingHistory
  - getConsumer
  - getConsumptionHistory
  - getDisconnectionRecord
  - getMeterStatus
  - getRestorationCase
  - getRestorationScreening
  - getSiteSurvey
  - listRestorationCases
---

# Illegal Restoration Detection

## Purpose

Identify disconnected consumer accounts where electricity consumption appears
to resume after disconnection and determine whether the case warrants:

* record verification
* routine inspection
* urgent inspection
* no action

The system compares:

```text
Confirmed disconnection
        ↓
Expected post-disconnection state
        ↓
Observed meter state / readings
        ↓
Observed consumption
        ↓
Authorized restoration evidence
        ↓
Inspection priority
```

The system does **not** determine that an illegal restoration has occurred.

Only an authorized field inspection and applicable DISCOM/legal process can
establish what physically occurred at the premises.

---

# 1. Core Principle

The fundamental question is:

> **Was the consumer actually disconnected, and if so, what explains the
> subsequent measured consumption?**

Do not start with:

> "Consumption after TD = illegal restoration."

Instead:

```text
Post-TD consumption
        ↓
Was disconnection actually executed?
        ↓
Was consumption actually measured?
        ↓
Was authorized restoration recorded?
        ↓
Is the meter/reading reliable?
        ↓
Is there another legitimate explanation?
        ↓
Only then → inspection priority
```

The system must preserve the possibility that the DISCOM's own records are
wrong.

---

# 2. Operating Modes

## Mode A — Portfolio Screening

If the request concerns:

* the restoration screening run
* all disconnected accounts
* a division
* a subdivision
* inspection tasks
* enforcement planning
* an export
* restoration statistics

start with:

`getRestorationScreening`

Then retrieve supporting evidence as required.

Typical workflow:

```text
getRestorationScreening
        ↓
validate disconnection execution
        ↓
validate actual meter reads
        ↓
identify post-disconnection consumption
        ↓
correlate payments and restoration orders
        ↓
exclude explained cases
        ↓
score remaining cases
        ↓
buildRestorationTasks
        ↓
export inspection tasks
```

---

## Mode B — One Case

If the user supplies a consumer/account number, work only on that case.

Retrieve, where available:

```text
getTDAccount
getDisconnectionRecord
getMeterReads
getConsumptionHistory
getMeterStatus
getRestorationHistory
getWorkOrders
getPaymentHistory
getNoticeHistory
getSiteSurveys
getInspectionHistory
```

Tool names are implementation-dependent.

Use only tools actually available in the connected environment.

Never invent missing evidence.

---

# 3. Required Output Contract

For one consumer, the first three lines must be exactly:

```text
RESTORATION_RISK: 0-100
RECOMMENDED_ACTION: INSPECT_URGENT | INSPECT_ROUTINE | VERIFY_RECORDS | NO_ACTION
CONFIDENCE: high | medium | low
```

The score is an **inspection-prioritization score**.

It is not:

* proof of illegal restoration
* proof of theft
* proof of consumer intent
* a legal finding
* a calibrated probability unless the underlying model is actually calibrated

If the system produces a calibrated probability, label it explicitly as such.

---

# 4. The Four Fundamental Measurements

Every case must establish four core facts.

## 4.1 Disconnection

Record:

* disconnection order date
* scheduled disconnection date
* actual execution date
* field acknowledgement
* meter reading at disconnection
* meter status
* method of disconnection
* work-order completion status

The most important distinction is:

```text
ORDERED
```

versus:

```text
ACTUALLY EXECUTED
```

An order in the billing system is not proof that supply was disconnected.

---

## 4.2 Expected Consumption

Normally:

```text
Expected consumption after confirmed disconnection = 0
```

But this assumption must be validated.

Possible exceptions:

* common-area arrangements
* shared metering
* partial disconnection
* multiple meters at the premises
* meter left energized for another authorized purpose
* special DISCOM configurations
* administrative status not matching physical status

If expected consumption is not zero, state why.

---

## 4.3 Actual Consumption

Use **actual measured meter data** wherever possible.

Preferred hierarchy:

1. validated interval/AMI data
2. actual meter read
3. validated cumulative register movement
4. manually verified field read
5. other validated metering evidence

Do not treat these as equivalent to actual consumption:

* estimated bills
* provisional bills
* carried-forward readings
* system-generated consumption
* billing estimates

---

## 4.4 Consumption Gap

Calculate:

```text
Consumption gap
=
Actual measured consumption
-
Expected consumption
```

Also show:

```text
Post-disconnection consumption
/
Pre-disconnection baseline
```

where sufficient history exists.

Example:

```text
Disconnection executed: 15 June
Expected consumption: 0 kWh
Post-disconnection actual consumption: 450 kWh
Period: 20 June–31 July
Pre-TD average: 380 kWh/month
```

The report must show quantities and dates.

Avoid descriptions such as:

> "Significant consumption occurred."

---

# 5. Proving That Disconnection Actually Happened

This is the most important gate in the entire skill.

Evidence that supports an executed disconnection includes:

* field completion acknowledgement
* meter reading recorded at disconnection
* photograph where authorized
* meter status changed by field staff
* physical disconnection method recorded
* work-order completion
* service cable termination record
* meter removal record
* seal record
* timestamped field activity

A system status of:

```text
DISCONNECTED
```

without execution evidence is insufficient for a high restoration-risk score.

---

# 6. Disconnection Execution Confidence

Assign:

```text
DISCONNECTION_EXECUTION:
CONFIRMED
PROBABLE
UNCONFIRMED
CONTRADICTED
```

### CONFIRMED

Multiple independent execution signals agree.

### PROBABLE

Evidence strongly suggests execution but one important element is missing.

### UNCONFIRMED

The order exists but physical execution cannot be established.

### CONTRADICTED

Evidence indicates that supply may never have been disconnected.

Example:

```text
Disconnection order: completed
Field acknowledgement: missing
Disconnection meter read: missing
Consumption continues continuously

Conclusion:
Disconnection execution is UNCONFIRMED.
```

Do not treat this as illegal restoration.

Recommended action:

`VERIFY_RECORDS`

---

# 7. Authorized Restoration Check

Before scoring a case highly, search for evidence that the supply was restored
lawfully.

Check:

* payment
* approved payment arrangement
* restoration order
* restoration work order
* reconnection fee
* authorized reconnection
* meter status change
* field restoration acknowledgement
* consumer request
* system status update
* restoration inspection

Correlate events by time.

Example:

```text
TD: 15 June
Payment: 18 June
Restoration order: 19 June
Consumption resumes: 20 June
```

This should generally reduce the restoration-risk score substantially.

Do not merely say:

> "Payment occurred."

Determine whether the payment plausibly corresponds to restoration.

---

# 8. Payment Correlation

A payment shortly before consumption resumes is relevant but not conclusive.

Possible interpretations:

### Strong authorized-restoration signal

Payment
+
approved restoration
+
field restoration
+
consumption resumes

### Weak signal

Payment
+
consumption resumes

### No meaningful signal

Payment occurs but:

* does not satisfy restoration conditions
* is reversed
* is unrelated to the account status
* occurs long before consumption
* is insufficient under the applicable process

Never assume:

```text
payment = authorized restoration
```

without supporting evidence.

---

# 9. Estimated Reads

Estimated consumption is not measured consumption.

If the apparent post-disconnection consumption comes entirely from:

* estimated reads
* carried-forward reads
* provisional billing
* system-generated consumption

then:

```text
RESTORATION_RISK ≤ VERIFY_RECORDS band
```

unless independent actual metering evidence exists.

A billing amount generated after disconnection is not evidence that electricity was
physically consumed.

This rule is mandatory.

---

# 10. Meter-Read Integrity

Before treating consumption as evidence, check:

* meter number
* previous meter number
* current meter number
* reading date
* reading sequence
* meter replacement
* meter rollover
* multiplier
* CT/PT ratio where applicable
* cumulative register
* estimated/manual read flag
* read reversal
* abnormal read
* duplicate read
* wrong-meter possibility
* multi-meter premises

Example:

```text
Meter A:
TD meter = 123456

Post-TD consumption appears under:
Meter B = 789012

```

Do not attribute Meter B's consumption to the disconnected consumer without
establishing the meter-to-account relationship.

---

# 11. Meter Replacement

Meter replacement creates a major sequencing hazard.

Always reconstruct:

```text
Old meter
    ↓
Final old-meter reading
    ↓
Removal date
    ↓
New meter installation
    ↓
Initial new-meter reading
    ↓
Post-installation consumption
```

Do not treat a meter change as restoration.

If the meter was replaced under an authorized work order, the event should be
classified accordingly.

---

# 12. Multi-Meter and Shared Premises

A premises may contain:

* multiple consumer numbers
* multiple meters
* common-area meters
* landlord/tenant meters
* adjacent premises
* shared service arrangements

Consumption must be attributed to the correct consumer.

Never assume:

```text
same address = same connection
```

Before escalating, verify:

* meter number
* service connection
* consumer number
* premises mapping
* meter location
* service cable

---

# 13. Consumption Pattern Analysis

Once actual consumption is established, analyze its shape.

## Abrupt resumption

Example:

```text
15 June → disconnected
16–19 June → 0
20 June → 18 kWh
21 June → 22 kWh
22 June → 19 kWh
```

This is more suspicious than a continuous gradual billing transition,
provided the disconnection itself is confirmed.

---

## Gradual resumption

Example:

```text
15 June → 0
16 June → 0
17 June → estimated
18 June → estimated
19 June → 3 kWh
20 June → 6 kWh
21 June → 9 kWh
```

This may indicate:

* data lag
* meter transition
* reading issue
* partial restoration
* operational error

Do not automatically classify it as illegal restoration.

---

## Return to historical baseline

If consumption rapidly returns to approximately the pre-TD operating level,
that is stronger evidence for field investigation.

Example:

```text
Pre-TD average:       380 kWh/month
Post-TD consumption:   450 kWh/month
```

This is more informative than:

```text
Post-TD consumption: 450 kWh
```

without a baseline.

---

# 14. Pre-TD Baseline

Where enough history exists, calculate a baseline using comparable periods.

Possible baseline:

```text
12-month median
6-month median
same-season historical consumption
rolling monthly average
```

Prefer robust measures such as median when historical consumption contains
outliers.

Account for:

* seasonal businesses
* agricultural schedules
* industrial shutdowns
* known occupancy changes
* tariff changes
* meter replacement
* solar/net-metering effects
* abnormal historical periods

Do not blindly compare one month against the entire previous year.

---

# 15. Restoration Timing

Calculate:

```text
Days from confirmed disconnection
to first validated post-disconnection consumption
```

Example:

```text
Confirmed disconnection: 15 June
First actual consumption: 20 June
Gap: 5 days
```

Timing is supporting evidence.

It must not be treated as proof by itself.

---

# 16. Restoration Risk Scoring

The score should consider:

### High-weight evidence

* confirmed executed disconnection
* validated actual consumption afterward
* consumption begins after a genuine zero/near-zero period
* consumption is physically attributable to the consumer's meter
* consumption returns close to historical operating level
* physical evidence from prior inspection
* confirmed unauthorized physical restoration indicator

### Medium-weight evidence

* abrupt restart
* repeated post-TD consumption
* multiple consecutive actual reads
* substantial post-TD usage
* no corresponding authorized restoration
* meter status inconsistent with consumption

### Lower-weight evidence

* statistical anomaly
* historical behavior
* geographic context
* consumer category

### No direct individual scoring contribution

Area-level statistics should not directly determine the individual score.

---

# 17. Mandatory Risk Gates

## Gate 1 — Disconnection not confirmed

If execution is not established:

```text
RECOMMENDED_ACTION = VERIFY_RECORDS
```

Do not issue an enforcement inspection solely from subsequent consumption.

---

## Gate 2 — Consumption not actually measured

If the signal is estimated:

```text
RECOMMENDED_ACTION = VERIFY_RECORDS
```

unless independent actual evidence exists.

---

## Gate 3 — Authorized restoration confirmed

If authorized restoration is confirmed:

```text
RECOMMENDED_ACTION = NO_ACTION
```

unless another independent issue exists.

---

## Gate 4 — Meter/account attribution uncertain

If it is unclear whether the consumption belongs to this consumer:

```text
RECOMMENDED_ACTION = VERIFY_RECORDS
CONFIDENCE = low
```

---

## Gate 5 — Strong corroboration

If:

* disconnection is confirmed
* actual consumption is validated
* authorized restoration is absent or contradicted
* timing is consistent
* meter attribution is confirmed

then:

```text
RECOMMENDED_ACTION = INSPECT_ROUTINE
```

or:

```text
INSPECT_URGENT
```

depending on configured operational criteria.

---

# 18. Score Bands

Default operational bands:

|  Score | Interpretation                           | Action                           |
| -----: | ---------------------------------------- | -------------------------------- |
| 90–100 | Strong multi-source evidence             | INSPECT_URGENT                   |
|  75–89 | Strong inspection candidate              | INSPECT_ROUTINE                  |
|  50–74 | Material anomaly but uncertainty remains | INSPECT_ROUTINE / VERIFY_RECORDS |
|  25–49 | Weak or conflicting evidence             | VERIFY_RECORDS                   |
|   0–24 | Explained / insufficient evidence        | NO_ACTION                        |

These are operational defaults and must be configurable.

---

# 19. Score Caps

Certain conditions should prevent a high score.

### Disconnection unconfirmed

Maximum:

```text
VERIFY_RECORDS band
```

### Consumption based only on estimated reads

Maximum:

```text
VERIFY_RECORDS band
```

### Authorized restoration confirmed

Normally:

```text
NO_ACTION
```

### Meter-to-account attribution uncertain

Maximum:

```text
VERIFY_RECORDS band
```

### Single questionable read

Do not treat as strong evidence.

### Historical consumption only

Historical behavior cannot establish current restoration.

---

# 20. Independent Evidence

A high score should preferably require agreement among independent systems.

For example:

```text
Work-order system:
confirmed disconnection

Meter system:
actual zero consumption

AMI/meter reads:
consumption resumes

Restoration system:
no authorized restoration

Payment system:
no qualifying payment/restoration event
```

This is materially stronger than:

```text
Billing system:
consumption = 450 kWh
```

The more independent systems agree, the higher the confidence.

---

# 21. Inspection Task Generation

`buildRestorationTasks` should generate an **inspection specification**, not
simply a list of consumer numbers.

Each task should explain:

```text
Why this premises was selected
What disconnection method was used
What restoration would physically look like
What evidence the officer should verify
What evidence would clear the case
```

---

# 22. Inspection Checklist Based on Disconnection Method

The inspection task must depend on how the original disconnection was performed.

## Method A — Meter removed

Inspect:

* whether the meter remains absent
* service connection
* unauthorized meter installation
* service cable
* terminal arrangement
* physical connection point
* meter identity
* authorized restoration documentation

Do not instruct the officer to inspect a meter that was documented as removed
unless the purpose is to verify whether a replacement/unauthorized meter exists.

---

## Method B — Service cable disconnected

Inspect:

* pole termination
* service cable
* reconnection point
* joints
* clamps
* bypass arrangement
* meter terminals
* seals

---

## Method C — Meter left in place and sealed

Inspect:

* meter seal
* terminal chamber
* incoming/outgoing conductors
* bypass possibility
* service cable
* meter status
* seal number
* physical evidence of disturbance

---

## Method D — Unknown

Do not invent an inspection location.

Task:

```text
VERIFY_DISCONNECTION_METHOD
```

before specifying a physical restoration point.

---

# 23. Inspection Evidence

Where permitted by DISCOM procedure, inspectors should verify:

* meter number
* seal number
* meter condition
* service cable
* terminal chamber
* pole connection
* authorized restoration record
* meter reading
* current energized/de-energized status
* physical signs of reconnection
* photographs
* timestamp
* field officer identification

The AI should not instruct field staff to perform actions outside their
authorization.

---

# 24. What Confirms the Case

Examples of strong corroborating evidence may include:

* physical reconnection at the original disconnection point
* disturbed or replaced seal
* unauthorized service cable reconnection
* energized meter despite confirmed disconnection
* physical bypass
* meter reading consistent with unauthorized re-energization
* absence of an authorized restoration order where one would be required

The report should say:

> "The inspection should verify whether these conditions are present."

Not:

> "These conditions are present."

unless the evidence actually establishes them.

---

# 25. What Clears the Case

Inspection may clear the anomaly when:

* authorized restoration is documented
* disconnection never actually occurred
* meter belongs to another account
* reading was erroneous
* billing estimate created the apparent consumption
* meter replacement explains the sequence
* shared/common supply explains the reading
* system status was not synchronized
* physical supply remains disconnected

A cleared case is a useful outcome.

Do not treat it as a failed AI prediction.

It is evidence that the screening correctly surfaced a record discrepancy.

---

# 26. Portfolio Screening

For the portfolio, report at minimum:

```text
Total disconnected accounts
Accounts showing apparent post-TD consumption
Accounts based only on estimated reads
Accounts with unconfirmed disconnection
Accounts with likely authorized restoration
Accounts with meter/read attribution issues
Accounts remaining after exclusions
Inspection candidates
Urgent inspection candidates
Routine inspection candidates
Record-verification candidates
```

The gap between:

```text
apparent post-TD consumption
```

and:

```text
inspection candidates
```

must be explicitly explained.

---

# 27. Portfolio Example

Synthetic example:

```text
Disconnected accounts:                 40,000

Accounts with apparent consumption:    11,926

Estimated-read-only cases:              2,496
Disconnection not confirmed:               734
Likely authorized restoration:           2,108

Remaining candidates:                    X

Inspection candidates:                   2,378
```

Do not use these numbers unless they are actually returned by the connected
system.

The system must calculate the actual figures.

---

# 28. Avoid Double Counting

One consumer may have:

* multiple meter events
* multiple consumption periods
* multiple restoration events
* multiple disconnection orders

Do not count every event as a separate consumer case.

Maintain:

```text
consumer
connection
meter
disconnection episode
restoration episode
```

as distinct entities.

One consumer can have multiple episodes.

---

# 29. Episode-Based Analysis

Where possible, model each TD episode separately.

Example:

```text
Consumer: A123

Episode 1:
TD: January
Restored: February
No anomaly

Episode 2:
TD: May
Consumption resumes: June
No authorized restoration

Episode 3:
TD: August
Still disconnected
```

The risk score should apply to the relevant episode.

Do not contaminate the current case with unrelated historical episodes.

---

# 30. Repeat Restoration Patterns

Repeated episodes can be relevant.

Example:

```text
TD #1 → consumption resumes
TD #2 → consumption resumes
TD #3 → consumption resumes
```

But repetition must be based on verified events.

Do not describe the consumer as:

> "habitually restoring illegally"

unless such conduct has actually been established through authorized
procedures.

Use:

> "Three prior TD episodes were followed by validated post-disconnection
> consumption."

---

# 31. Previous Inspection Outcomes

Where inspection history exists, use it.

Possible outcomes:

```text
AUTHORIZED_RESTORATION
DISCONNECTION_NOT_EXECUTED
METER_ERROR
WRONG_METER
PHYSICAL_RECONNECTION_FOUND
NO_RECONNECTION_FOUND
PREMISES_VACANT
OTHER
```

Historical inspection outcomes can improve prioritization and identify repeat
cases.

Do not assume an old inspection outcome proves the current physical condition.

---

# 32. Data Quality Flags

Every case should have data-quality flags.

Examples:

```text
MISSING_DISCONNECTION_READ
MISSING_FIELD_ACKNOWLEDGEMENT
ESTIMATED_POST_TD_READ
METER_CHANGED
METER_ACCOUNT_MAPPING_UNCERTAIN
RESTORATION_RECORD_MISSING
PAYMENT_CORRELATION_UNCERTAIN
STALE_SITE_SURVEY
MULTIPLE_METERS
CONFLICTING_SYSTEM_STATUS
```

Data-quality problems should reduce confidence.

---

# 33. Confidence

Confidence measures the reliability of the evidence supporting the
recommendation.

### High

Multiple independent systems agree and critical fields are validated.

### Medium

The core pattern is present but one meaningful uncertainty remains.

### Low

Important evidence is missing, estimated, contradictory, or inferred.

Do not use confidence as another hidden risk score.

A case can be:

```text
RESTORATION_RISK: 92
CONFIDENCE: medium
```

if the observed pattern is strong but one important record is missing.

---

# 34. Required One-Case Report

After the three-line header, use:

## 1. Four Figures

Show:

```text
Disconnection:
Expected consumption:
Actual measured consumption:
Consumption gap:
```

Include dates and sources.

---

## 2. Was the Disconnection Actually Executed?

State:

```text
CONFIRMED / PROBABLE / UNCONFIRMED / CONTRADICTED
```

Then explain the evidence.

---

## 3. Consumption Evidence

Show:

* first post-disconnection consumption date
* total consumption
* period
* number of actual reads
* pre-TD baseline
* percentage relative to baseline
* meter identity

---

## 4. Authorized Restoration Check

Show:

* payment evidence
* restoration order
* work order
* meter status
* field acknowledgement
* other relevant records

State whether authorized restoration is:

```text
CONFIRMED
PROBABLE
NOT_FOUND
CONTRADICTED
UNKNOWN
```

---

## 5. Alternative Explanations Tested

Always address:

* disconnection never executed
* authorized restoration
* estimated billing
* meter/read error
* wrong meter
* meter replacement
* shared supply
* system synchronization error
* other known operational explanation

Never leave this section empty.

---

## 6. Why the Risk Is High/Medium/Low

State the independent evidence supporting the score.

Do not simply repeat:

> "Consumption occurred."

---

## 7. Inspection Task

Specify exactly what the field officer should verify based on the
disconnection method.

---

## 8. What Is Not Established

Always state:

> "Post-disconnection consumption is an anomaly requiring verification. It does
> not by itself establish illegal restoration, theft, consumer intent, or any
> other legal finding."

---

# 35. Citation Requirements

Every material fact must be traceable.

Examples:

```text
[TD order 2026-06-15]
[field acknowledgement 2026-06-15 14:32]
[meter read 2026-06-15: 12,450 kWh]
[meter read 2026-06-20: 12,468 kWh]
[consumption history 2026-06-20 to 2026-07-31]
[restoration work order 2026-06-19]
[payment 2026-06-18]
```

Every number used in the score must have a source.

Never fabricate citations.

---

# 36. Language Rules

Use:

> "Validated consumption was recorded after the confirmed disconnection."

Not:

> "The consumer restored electricity."

Use:

> "The record contains no matching authorized restoration."

Not:

> "The consumer restored supply illegally."

Use:

> "Recommended for physical inspection."

Not:

> "Illegal restoration confirmed."

Use:

> "Physical inspection should verify the service cable and terminal chamber."

Not:

> "The service cable was illegally reconnected."

unless that fact has actually been established by authorized inspection.

---

# 37. Legal / Enforcement Boundary

This skill is an intelligence and prioritization system.

It must not:

* declare guilt
* declare theft
* declare illegal restoration without physical/legal determination
* determine criminal liability
* replace an authorized officer
* replace statutory procedure
* generate unsupported legal conclusions
* automatically impose penalties
* automatically disconnect/reconnect supply
* automatically accuse a consumer

The AI produces:

```text
ANOMALY
+
EVIDENCE
+
PRIORITY
+
INSPECTION INSTRUCTIONS
```

The authorized process determines the outcome.

---

# 38. Human-in-the-Loop

Every enforcement inspection recommendation must remain reviewable.

The reviewer should be able to see:

```text
score
reason codes
disconnection evidence
consumption evidence
authorized-restoration evidence
data-quality flags
alternative explanations
recommended inspection points
```

A human reviewer may:

```text
APPROVE
REJECT
REQUEST_MORE_DATA
DOWNGRADE
ESCALATE
```

The override must be recorded.

---

# 39. Auditability

For every case record:

```text
consumer_id
connection_id
meter_id
disconnection_episode_id
disconnection_date
disconnection_method
execution_status
expected_consumption
actual_consumption
consumption_gap
pre_td_baseline
restoration_events
payment_events
work_orders
score
confidence
reason_codes
data_quality_flags
recommended_action
model_version
data_snapshot
human_decision
inspection_outcome
```

The system must be able to answer:

> **Why did this account receive a restoration-risk score of 96 on this date?**

---

# 40. Feedback Loop

After field inspection, capture:

```text
predicted score
recommended action
actual physical condition
authorized restoration found
disconnection confirmed
meter/read issue
physical reconnection found
other outcome
amount recovered if applicable
field effort
```

Use outcomes to improve:

* ranking
* calibration
* data-quality detection
* disconnection execution monitoring
* restoration detection
* inspection targeting

---

# 41. DISCOM Process Intelligence

This skill should not only detect consumer-side anomalies.

It should identify **DISCOM process failures**.

Important categories:

```text
DISCONNECTION_ORDER_NOT_EXECUTED
DISCONNECTION_EXECUTED_BUT_NOT_RECORDED
AUTHORIZED_RESTORATION_NOT_RECORDED
PAYMENT_NOT_LINKED_TO_RESTORATION
METER_STATUS_NOT_SYNCHRONIZED
WRONG_METER_MAPPING
ESTIMATED_BILL_AFTER_DISCONNECTION
FIELD_ACKNOWLEDGEMENT_MISSING
```

These should be reported separately from suspected unauthorized restoration.

This distinction is strategically important.

The AI should tell management:

> "How many apparent illegal restorations are actually failures in our own
> disconnection/restoration process?"

That can be more valuable than the enforcement list itself.

---

# 42. Portfolio Management Metrics

Track:

### Detection

* disconnected accounts screened
* apparent post-TD consumption
* validated post-TD consumption
* high-risk cases
* inspection yield

### Enforcement effectiveness

* inspections completed
* physical reconnections found
* cases cleared
* authorized restorations found
* meter/read errors found

### Process quality

* disconnections not actually executed
* restoration records missing
* delayed system synchronization
* estimated-read false positives
* wrong-meter attribution

### Operational effectiveness

* inspections per field team
* actionable cases per visit
* geographic travel efficiency
* high-risk confirmation rate

The key KPI is:

> **Confirmed actionable cases per inspection**, not the number of alerts
> generated.

---

# 43. Geographic Optimization

Geography may be used to:

* batch field visits
* optimize routes
* assign teams
* reduce travel time
* identify operational clusters

Do not use geography as evidence that an individual consumer illegally restored
electricity.

A high-alert area can mean:

* poor disconnection execution
* poor system synchronization
* concentrated authorized restorations
* meter problems
* genuine physical reconnections

Area-level analysis must therefore distinguish these causes.

---

# 44. Inspection Priority Optimization

If there are 500 potential cases and capacity for 100 visits, do not simply
choose the highest score without considering:

* score
* evidence confidence
* severity/currentness
* field travel
* repeat visits
* inspection specialization
* physical disconnection method
* expected information gain

A useful field-priority concept is:

```text
Inspection Value
=
Risk
×
Evidence Quality
×
Actionability
×
Expected Information Gain
```

This is an operational prioritization concept, not a legal formula.

---

# 45. What the AI Must Never Do

Never:

* treat any post-TD bill as proof of consumption
* treat estimated consumption as actual consumption
* assume the TD order was executed
* assume payment means authorized restoration
* assume consumption belongs to the disconnected account
* ignore meter replacement
* ignore multiple meters
* ignore conflicting system records
* declare illegal restoration from consumption alone
* declare theft
* infer consumer intent
* accuse the consumer
* invent physical evidence
* invent inspection findings
* invent restoration orders
* invent payments
* fabricate citations
* suppress contradictory evidence
* automatically impose enforcement action

---

# 46. Final Decision Framework

For every case:

```text
1. Identify the TD episode.
        ↓
2. Establish the scheduled disconnection.
        ↓
3. Establish whether physical disconnection was executed.
        ↓
4. Identify the disconnection method.
        ↓
5. Establish expected post-TD state.
        ↓
6. Validate actual meter consumption.
        ↓
7. Confirm meter-to-consumer attribution.
        ↓
8. Check meter replacement / read integrity.
        ↓
9. Search for authorized restoration.
        ↓
10. Correlate payment and work-order events.
        ↓
11. Analyze timing and consumption pattern.
        ↓
12. Test alternative explanations.
        ↓
13. Calculate restoration-risk score.
        ↓
14. Assign confidence.
        ↓
15. Select:
        INSPECT_URGENT
        INSPECT_ROUTINE
        VERIFY_RECORDS
        NO_ACTION
        ↓
16. Generate inspection instructions.
        ↓
17. Capture field outcome.
        ↓
18. Feed outcome back into the model.
```

---

# 47. Final Principle

The system should never be designed around:

```text
Disconnected
+
Consumption
=
Illegal restoration
```

The correct intelligence chain is:

```text
Confirmed physical disconnection
        +
Validated actual post-disconnection consumption
        +
Correct meter attribution
        +
No credible authorized restoration
        +
No stronger operational explanation
        +
Independent corroboration
        ↓
HIGH INSPECTION PRIORITY
```

And equally importantly:

```text
Apparent post-TD consumption
+
Disconnection execution not confirmed
        ↓
VERIFY DISCOM RECORDS
```

or:

```text
Post-TD consumption
+
Authorized restoration confirmed
        ↓
NO ENFORCEMENT ACTION
```

The highest-value capability is therefore not merely detecting apparent
restorations.

It is distinguishing:

**true physical anomalies**

from

**billing artifacts**

from

**meter/data errors**

from

**authorized restorations**

from

**DISCOM process failures**

and only then directing scarce field capacity toward the cases where physical
inspection is most likely to produce a meaningful result.

## Handing over the full list

When the answer is a list somebody will work — the case list, every matching row
rather than a sample — call `exportRestorationCases` and give the **download link**, the row
count and the totals.

**Never put the rows in your reply.** Tens of thousands of rows is around two
million tokens: it does not fit in the context, and if it did it would cost
several dollars to produce something nobody can read. The file costs nothing.
Show the few sample rows the export returns so the reader sees the shape, and
point at the file for the rest.

Say what the file contains and which filters produced it. An export whose
selection nobody can reconstruct is not evidence of anything.
