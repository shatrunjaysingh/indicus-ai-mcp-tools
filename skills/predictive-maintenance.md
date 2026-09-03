---
name: predictive-maintenance
description: >
  Detect developing equipment deterioration, interpret condition-monitoring evidence, validate predictive-maintenance signals, prioritize inspections, and build capacity-constrained preventive-maintenance plans for DISCOM distribution assets. modes: * one_asset * fleet * maintenance_planning * failure_review * condition_monitoring * inspection_planning * asset_health
allowed-tools:
  - buildMaintenancePlan
  - exportAssetRiskList
  - getAssetFleet
  - getAssetRisk
  - getDTHealth
  - getFailureReview
  - getFeederLosses
  - getLoadHistory
  - getMaintenanceHistory
  - getOutageHistory
  - listAssetsByRisk
---

# DISCOM Predictive Maintenance

## 1. Purpose

Use AI and condition-monitoring data to identify distribution assets showing
evidence of deterioration before failure occurs.

The objective is to move from:

**FAILURE → EMERGENCY REPAIR**

toward:

**DETECTION → DIAGNOSIS → INSPECTION → PREVENTIVE ACTION → VERIFIED CONDITION**

The skill supports:

* transformers;
* distribution transformers (DTs);
* feeders;
* breakers;
* switches;
* substations;
* capacitor banks;
* protection equipment;
* cables;
* other configurable distribution assets.

The skill may analyze:

* SCADA;
* smart-meter aggregates;
* load;
* phase loading;
* voltage;
* current;
* temperature;
* oil temperature;
* ambient temperature;
* oil condition;
* dissolved-gas analysis where available;
* vibration;
* breaker operations;
* protection trips;
* outage history;
* maintenance history;
* asset age;
* inspection history;
* historical failures;
* work orders;
* environmental conditions.

The skill must distinguish:

**prediction**

from

**diagnosis**

from

**inspection**

from

**confirmed failure**.

A prediction is not a failure finding.

---

# 2. Core Operating Principle

The AI should answer:

> **Which assets deserve attention first, why, what evidence supports that
> conclusion, what should the crew inspect, and what remains unknown?**

It should not claim:

> "This transformer will fail."

unless a separately validated predictive model and its applicable confidence
standard support that statement.

The preferred language is:

> "The asset shows conditions associated with elevated failure risk and should
> be inspected within X days."

---

# 3. Two Primary Modes

## Mode A — One Asset

An **asset ID** means assess that asset.

Go to:

**One Asset**

The assessment should use all available evidence for that asset.

---

## Mode B — Fleet

Anything else means work the fleet:

* monthly maintenance plan;
* asset-health review;
* failure review;
* inspection planning;
* fleet screening;
* telemetry gap analysis;
* consequence analysis;
* export.

Start with:

`getAssetFleet`

Do not build a fleet ranking from a handful of individual assets.

---

# 4. Example Fleet

Current operating example:

**8,500 assets**

**752 require attention**

**320 crew visits available**

The system therefore has a constrained optimization problem.

The question is not:

> "Which 752 assets are risky?"

It is:

> "Which 320 interventions provide the greatest justified maintenance value,
> given risk, evidence quality, consequence, work type, geography, crew
> capacity, and operational constraints?"

---

# 5. Failure Review

`getFailureReview` contains the previous year's failure history.

Current example:

* 214 failures;
* 137 had identifiable warning indicators;
* 77 did not;
* median warning lead time for the 137 was 34 days;
* 61 assets had no telemetry;
* 16 failures were genuinely sudden.

The 137 failures support preventive-monitoring potential.

The remaining failures must remain visible.

Do not report:

> "137 of 214 failures were predictable"

as though the model itself predicted them unless a prospective model validation
actually demonstrates that.

Historical hindsight is not the same as prospective predictive performance.

---

# 6. Avoid the Hindsight Trap

A warning indicator discovered after a failure is not automatically a
successful prediction.

Distinguish:

### Retrospective signal

The data shows that a condition existed before the historical failure.

### Prospective prediction

The deployed model identified an asset before failure using only information
available at the prediction time.

### Confirmed prediction

The predicted asset subsequently failed within the defined prediction window.

Use these separately in model-performance reporting.

---

# 7. Telemetry Gap

Current example:

**3,105 assets — 37% of the fleet — have no SCADA or smart-meter feed.**

For these assets:

* loading trends may be unavailable;
* thermal trends may be unavailable;
* event histories may be incomplete.

Therefore:

> **No telemetry means unknown, not low risk.**

Assets without telemetry may still be assessed using:

* age;
* maintenance history;
* failure history;
* inspection history;
* asset class;
* installation environment.

But their condition confidence should be lower.

---

# 8. Instrumentation Strategy

Do not treat missing telemetry only as a modelling problem.

Where the business case supports it, identify assets where additional sensing could
materially improve maintenance decisions.

Examples:

* temperature sensors;
* load monitoring;
* transformer oil monitoring;
* smart-meter aggregation;
* breaker operation monitoring;
* vibration monitoring.

The AI should be able to recommend:

`INSTALL_SENSOR`

where appropriate.

A sensor recommendation should identify:

* asset;
* missing signal;
* expected diagnostic value;
* reason;
* proposed monitoring period.

---

# 9. One Asset Output Contract

First three lines, exactly:

```
FAILURE_RISK: CRITICAL | HIGH | MEDIUM | LOW
INSPECT_WITHIN: <n> days | ROUTINE_CYCLE
PRIMARY_DRIVER: <the one condition that most drives this>
```

`PRIMARY_DRIVER` must contain one principal condition.

Examples:

* sustained overload;
* abnormal thermal trend;
* repeated unexplained trips;
* oil-condition deterioration;
* phase imbalance;
* age plus missed maintenance;
* abnormal breaker operation;
* insulation indicator;
* other configured condition.

Do not use:

> `PRIMARY_DRIVER: Multiple factors`

when the evidence supports a dominant driver.

---

# 10. Risk Is Not Consequence

Maintain separate dimensions:

### Failure risk

Likelihood that the asset will experience the defined failure mode within a
specified time horizon.

### Consequence

Impact if that failure occurs.

Consequence may include:

* consumers affected;
* critical facilities;
* hospitals;
* water infrastructure;
* traffic systems;
* industrial customers;
* alternative-feed availability;
* restoration difficulty;
* season;
* weather exposure.

Never increase the failure-risk category merely because consequence is high.

---

# 11. Risk + Consequence for Prioritization

The maintenance ranking may combine:

* failure risk;
* consequence;
* evidence confidence;
* expected maintenance value;
* crew constraints.

But preserve the components.

Example:

> **Failure risk: MEDIUM**
> **Consequence: HIGH**
> **Priority: HIGH**

This is much more useful than incorrectly calling the asset "high failure
risk."

---

# 12. Trend Beats Snapshot

Always distinguish:

### Current level

What is the asset experiencing now?

### Trend

How rapidly is the condition changing?

### Duration

How long has the condition persisted?

### Baseline

How does it compare with the asset's normal behaviour?

A DT at 92% loading for three years is different from one that increased from
60% to 92% over several weeks.

The system should therefore report:

* current value;
* previous value;
* change;
* time window;
* duration;
* relevant baseline.

---

# 13. Loading Analysis

Evaluate:

* average loading;
* peak loading;
* sustained loading;
* overload duration;
* number of overload events;
* seasonal pattern;
* phase loading;
* historical loading trend.

Distinguish:

`BRIEF_PEAK`

from

`SUSTAINED_OVERLOAD`

and:

`RECENT_CHANGE`

from

`LONG_STANDING_CONDITION`.

A short peak should not automatically receive the same risk interpretation as
months of sustained overload.

---

# 14. Phase Imbalance

For three-phase assets, evaluate:

* phase currents;
* phase loading;
* imbalance;
* duration;
* trend.

A transformer may show acceptable average loading while one phase is materially
overloaded.

Therefore:

**average load alone is insufficient for three-phase asset assessment.**

Where phase data is unavailable, explicitly state that limitation.

---

# 15. Temperature Analysis

Temperature should be interpreted with:

* ambient temperature;
* loading;
* time of day;
* season;
* historical baseline.

A single high temperature reading is weaker evidence than a sustained abnormal
trend.

Where possible, evaluate:

**temperature relative to expected temperature at comparable load and ambient
conditions.**

---

# 16. Thermal Trend

The strongest thermal signal may be:

> temperature increasing while load and ambient conditions remain broadly
> comparable.

This can indicate changing thermal performance.

However, do not diagnose the physical cause solely from temperature.

Possible causes may include:

* overload;
* ambient conditions;
* cooling degradation;
* sensor problem;
* oil condition;
* connection problem;
* phase imbalance;
* other equipment condition.

The inspection recommendation should therefore test the plausible causes.

---

# 17. Sensor Reliability

A sensor should not automatically be treated as ground truth.

Check:

* calibration status;
* missing values;
* impossible values;
* sudden discontinuities;
* sensor replacement;
* communication loss;
* stale readings;
* disagreement with independent measurements.

If a temperature sensor suddenly reports an extreme value while all other
signals remain normal, consider:

`VERIFY_SENSOR`

before declaring asset deterioration.

---

# 18. Independent Evidence

Confidence should increase when independent sources agree.

Examples:

* SCADA loading + smart-meter aggregate;
* temperature + load;
* temperature + oil condition;
* repeated trips + maintenance inspection;
* breaker operations + protection events.

One anomalous sensor should carry less weight than several independent,
consistent signals.

---

# 19. Failure and Trip History

Analyze:

* previous failures;
* protection trips;
* breaker trips;
* repeated outages;
* no-fault-found events;
* temporary faults;
* restoration events;
* repeat incidents.

Repeated unexplained trips should be treated as meaningful evidence.

A record of:

> "Restored — no fault found"

does not necessarily mean:

> "No underlying problem."

It may indicate an intermittent or unresolved condition.

---

# 20. Maintenance History

Evaluate:

* maintenance frequency;
* overdue maintenance;
* last inspection;
* last repair;
* repeat repair;
* unresolved work orders;
* inspection findings;
* replacement history.

An overdue maintenance cycle means:

**condition uncertainty**

not:

**healthy condition**.

Age alone should generally be a weak signal.

Age combined with:

* missed maintenance;
* repeated trips;
* deteriorating condition;

is much stronger.

---

# 21. Asset Age

Use age as context.

Do not assume:

> old = failing.

Instead evaluate:

* age;
* asset class;
* duty cycle;
* maintenance history;
* environment;
* failure history;
* current condition.

An older well-maintained asset with stable telemetry may be lower priority than
a younger asset showing rapid deterioration.

---

# 22. Historical Failure Model

Where a validated predictive model exists, it may provide:

* failure probability;
* prediction horizon;
* failure mode;
* confidence;
* model version;
* calibration information.

The AI should report the model output rather than recreate it from intuition.

Example:

**Model-estimated 90-day failure probability: 18%**

Then explain the supporting evidence.

Do not state:

> "AI calculated an 18% probability"

if the number came from a separate model.

---

# 23. Model Governance

Every predictive score should be traceable to:

* model name;
* model version;
* training period;
* prediction date;
* prediction horizon;
* asset population;
* applicable asset classes;
* input-data freshness;
* confidence/calibration information.

If the model is unavailable or stale, do not fabricate a probability.

---

# 24. Model Drift

Monitor whether relationships change over time.

Potential causes:

* equipment replacement;
* climate changes;
* operating-pattern changes;
* new protection settings;
* sensor changes;
* maintenance policy changes;
* network reconfiguration.

Track:

* prediction accuracy;
* false-positive rate;
* missed-failure rate;
* calibration;
* drift by asset class;
* drift by geography.

---

# 25. False Positives

A maintenance recommendation that repeatedly finds no problem should not simply
be ignored.

Track outcomes:

* confirmed deterioration;
* maintenance required;
* sensor fault;
* no fault found;
* normal condition;
* unrelated issue;
* asset failure before inspection.

Use outcomes to improve the model and inspection rules.

---

# 26. False Negatives

The most important model failure may be an asset that:

1. was considered low risk;
2. was not inspected;
3. subsequently failed.

Track these explicitly.

Review:

* available signals;
* telemetry gaps;
* model score;
* consequence;
* maintenance status;
* whether a warning signal was present.

---

# 27. Recommended Inspection

A risk score without a work instruction is incomplete.

The skill should recommend what the crew should actually inspect.

Examples:

### Thermal anomaly

* thermographic scan;
* verify temperature sensor;
* inspect connections;
* compare phases;
* check cooling condition.

### Sustained overload

* verify loading;
* inspect phase balance;
* assess load transfer;
* evaluate capacity upgrade.

### Oil-condition concern

* oil sample;
* dissolved-gas analysis where applicable;
* moisture testing;
* inspect leakage/cooling.

### Repeated trips

* inspect protection events;
* examine trip history;
* inspect connections;
* test protection equipment;
* investigate intermittent fault.

---

# 28. Maintenance Action Categories

Use configurable actions such as:

`INSPECT`

`THERMOGRAPHIC_SCAN`

`OIL_TEST`

`LOAD_REBALANCE`

`PROTECTION_TEST`

`SENSOR_VERIFY`

`INSTALL_SENSOR`

`REPAIR`

`REPLACE`

`LOAD_TRANSFER`

`CAPACITY_UPGRADE`

`MONITOR`

`NO_ACTION`

The final action must remain consistent with the available evidence.

---

# 29. Inspection Is Not Replacement

High risk does not automatically mean replacement.

The workflow should distinguish:

**observe → inspect → diagnose → repair/replace**

A model indicating elevated failure risk may justify an inspection without
justifying immediate replacement.

Replacement should require additional evidence or an approved engineering rule.

---

# 30. Maintenance Plan

`buildMaintenancePlan` should optimize the available crew capacity.

Current example:

* 752 assets needing attention;
* 320 visits available.

The plan should identify:

* selected assets;
* deferred assets;
* reason for selection;
* risk;
* consequence;
* evidence confidence;
* recommended work;
* estimated effort;
* geographic/crew constraints.

---

# 31. Capacity Allocation

Do not spend all capacity on the highest model scores automatically.

A robust plan may contain:

### Primary capacity

Highest justified maintenance priorities.

### Reserve capacity

High-consequence assets that did not enter the risk cut.

### Instrumentation capacity

Assets where sensing would materially improve future decisions.

### Reactive reserve

Where required for emerging failures.

The allocation percentages should be configurable.

---

# 32. High Consequence

Current example:

**1,433 assets have low/medium failure risk but high consequence.**

These should be separately identified.

Example:

> Failure risk: MEDIUM
> Consequence: HIGH
> No alternate feed
> Recommendation: include in consequence reserve.

Do not relabel it:

> HIGH failure risk.

That would make the risk score misleading.

---

# 33. Critical Loads

Where authorized asset-to-load mapping exists, identify:

* hospitals;
* water facilities;
* emergency services;
* transportation infrastructure;
* other designated critical loads.

Do not infer criticality from customer names alone.

Use the DISCOM's approved critical-load registry.

---

# 34. Seasonal Risk

Maintenance planning should consider operating season.

Examples:

* summer peak;
* monsoon;
* extreme heat;
* high wind;
* wildfire exposure where relevant;
* planned high-demand periods.

Seasonality affects:

* loading;
* ambient temperature;
* failure consequence;
* crew accessibility;
* restoration difficulty.

Do not silently modify failure probability because of season unless the model
explicitly incorporates it.

---

# 35. Geographic Optimization

When multiple high-priority assets are nearby, the planner may optimize crew routing
provided that:

**geographic efficiency never overrides a materially higher-risk or
higher-consequence asset without explanation.**

Report when geographic bundling changes the ranking.

---

# 36. Deferred Work

Every deferred high-priority asset should have a reason.

Examples:

* crew capacity;
* unavailable access;
* outage constraint;
* specialist required;
* safety restriction;
* duplicate work order;
* insufficient evidence requiring telemetry;
* lower expected maintenance value than selected assets.

Never silently drop assets from the plan.

---

# 37. Avoided-Cost Estimates

If an avoided-failure-cost model is used, expose its assumptions.

Current example:

The plan contains an avoided-cost estimate assuming that **10% of attended
assets would otherwise have failed within the year**.

That assumption is not established merely by the current data.

Therefore report:

> "Estimated avoided cost uses a 10% counterfactual failure assumption and
> should be replaced with the utility's validated failure rate for business-case
> use."

Do not present an assumed value as measured savings.

---

# 38. Maintenance Economics

Where cost data exists, compare:

* inspection cost;
* preventive repair cost;
* replacement cost;
* emergency repair cost;
* outage cost;
* customer impact;
* expected avoided failure cost.

The economic recommendation should remain separate from the physical
condition assessment.

---

# 39. Evidence Hierarchy

Generally prefer:

1. confirmed physical inspection;
2. validated condition-monitoring measurement;
3. independent corroborating sensor evidence;
4. repeated operational events;
5. sustained loading/thermal trend;
6. maintenance history;
7. asset age;
8. peer comparison.

Peer comparison should not independently justify an urgent maintenance action
without stronger evidence.

---

# 40. Peer Comparison

Peer benchmarking can compare an asset with:

* similar transformer class;
* similar capacity;
* similar age;
* similar operating environment;
* similar load profile.

But:

> **Being different from peers does not establish that the asset is failing.**

Use peer deviation to generate investigation hypotheses.

---

# 41. Missing Data

For every important missing signal, state its effect.

Examples:

> "No temperature telemetry; thermal condition cannot be assessed."

> "No phase-level current; phase imbalance cannot be evaluated."

> "No recent maintenance record; current physical condition is uncertain."

Do not convert missing evidence into a low-risk assumption.

---

# 42. Data Quality Controls

Check:

* timestamp continuity;
* stale telemetry;
* missing readings;
* sensor calibration;
* asset-to-sensor mapping;
* asset-to-feeder mapping;
* asset replacement;
* duplicate assets;
* incorrect ratings;
* incorrect commissioning dates;
* SCADA communication gaps.

An incorrect asset rating can create a false overload signal.

---

# 43. Asset Identity

Before analysis confirm:

* asset ID;
* asset type;
* location;
* rating;
* phase configuration;
* commissioning date;
* current operational status.

Do not combine data from two similarly named assets.

---

# 44. Work-Order Suppression

Suppress or adjust alerts when a known work order already explains the condition.

Examples:

* planned transformer replacement;
* sanctioned load transfer;
* planned outage;
* equipment testing;
* meter/SCADA maintenance;
* temporary operational configuration.

The suppression reason must be visible.

Never silently suppress an alert.

---

# 45. Duplicate Alert Suppression

If multiple signals describe the same event, consolidate them.

Example:

* high load;
* high temperature;
* thermal alarm.

These may represent one underlying condition.

The report should avoid making one problem look like three independent failures.

---

# 46. One Asset Required Sections

After the three-line header:

## Condition

Report:

* current value;
* trend;
* duration;
* comparison baseline;
* dates;
* units.

## What the History Adds

Report:

* failures;
* trips;
* outages;
* maintenance;
* previous inspection findings.

## Consequence of Failure

Report:

* consumers affected;
* critical loads;
* alternative supply;
* expected operational impact.

## Recommended Work

Specify the actual inspection or maintenance task.

## Why This Priority

Explain:

* risk;
* consequence;
* evidence confidence;
* capacity context where relevant.

## What Is Not Established

State:

* missing telemetry;
* sensor uncertainty;
* incomplete maintenance history;
* unresolved data conflict;
* limitations of the predictive model.

---

# 47. Example One-Asset Assessment

Input:

`DT-4587`

Current conditions:

* load: 92%;
* loading increased from 68% to 92% over 30 days;
* oil temperature rising over the same period;
* ambient temperature approximately stable;
* two unexplained trips in the last quarter;
* maintenance last completed 31 months ago;
* no current replacement work order.

Output:

```
FAILURE_RISK: HIGH
INSPECT_WITHIN: 7 days
PRIMARY_DRIVER: abnormal thermal trend
```

### Condition

Current loading is 92% of rating and has increased from 68% over the previous
30 days. Oil temperature has also increased during the same period while
ambient conditions were broadly stable. The combination is more concerning than
the 92% snapshot alone.

### What the History Adds

The asset has recorded two unexplained trips during the previous quarter.
Maintenance was last completed 31 months ago.

### Consequence of Failure

The asset serves the mapped consumers and critical loads recorded in the asset
registry. No alternate feed is recorded / alternate feed is available, as
applicable.

### Recommended Work

Within seven days:

1. perform thermographic inspection;
2. verify temperature-sensor accuracy;
3. inspect phase loading;
4. inspect connections;
5. review protection/trip history;
6. assess cooling and oil condition;
7. determine whether load transfer or corrective maintenance is required.

### What Is Not Established

The evidence indicates elevated failure risk but does not establish that the
transformer is about to fail. Physical inspection is required to determine the
underlying condition.

---

# 48. Fleet Output

For a fleet request, report:

### Fleet condition

* total assets;
* high-risk assets;
* medium-risk assets;
* low-risk assets;
* unknown-condition assets.

### Telemetry coverage

* monitored;
* partially monitored;
* unmonitored.

### Failure history

* total failures;
* failures with retrospective warning signals;
* sudden failures;
* failures occurring on uninstrumented assets.

### Maintenance capacity

* assets requiring attention;
* crew capacity;
* selected;
* deferred.

### Consequence reserve

Report separately.

### Instrumentation opportunity

Identify high-value assets where telemetry would materially improve visibility.

### Top maintenance drivers

Examples:

* thermal deterioration;
* overload;
* repeated trips;
* oil condition;
* phase imbalance;
* maintenance overdue.

---

# 49. Fleet Ranking

Each ranked asset should expose:

| Asset | Failure Risk | Consequence | Confidence | Primary Driver | Recommended Work |
| ----- | ------------ | ----------- | ---------- | -------------- | ---------------- |

Do not show only a single opaque score.

The planner should be able to understand why an asset appears where it does.

---

# 50. Maintenance Plan Explainability

For every selected asset, record:

* why selected;
* risk;
* consequence;
* confidence;
* evidence;
* recommended work;
* estimated effort;
* crew/specialist requirement.

For every major deferred asset:

* why deferred;
* what would change the decision;
* next review date.

---

# 51. What Would Change the Decision?

Every important recommendation should identify the most valuable next evidence.

Examples:

* temperature sensor verification;
* physical inspection;
* oil test;
* updated load measurement;
* phase-current measurement;
* protection-event review;
* maintenance record correction.

This turns the system from a ranking engine into a decision-support system.

---

# 52. Human Engineering Review

Require engineering review for:

* critical-risk assets;
* immediate replacement recommendations;
* protection changes;
* load-transfer decisions;
* major capital expenditure;
* safety-critical interventions;
* model anomalies;
* contradictory sensor evidence.

AI should recommend.

Authorized engineering personnel approve high-impact actions.

---

# 53. Auditability

For every maintenance recommendation record:

* asset ID;
* analysis timestamp;
* model version;
* data sources;
* data timestamps;
* relevant readings;
* prediction horizon;
* risk output;
* confidence;
* recommendation;
* human decision;
* final inspection outcome.

This allows later review of:

> "Why was this asset selected?"

and:

> "Was the recommendation correct?"

---

# 54. Learning Loop

After each inspection, capture the outcome:

`NORMAL`

`SENSOR_FAULT`

`MINOR_DETERIORATION`

`SIGNIFICANT_DETERIORATION`

`REPAIR_REQUIRED`

`REPLACEMENT_REQUIRED`

`LOAD_TRANSFER_REQUIRED`

`NO_FAULT_FOUND`

`FAILURE_CONFIRMED`

`OTHER`

Feed these outcomes back into:

* model validation;
* threshold tuning;
* inspection prioritization;
* sensor strategy;
* maintenance planning.

---

# 55. Model Performance Metrics

Track:

### Detection

* precision;
* recall;
* false-positive rate;
* missed-failure rate.

### Timing

* median warning lead time;
* percentage detected >7 days ahead;
* percentage detected >30 days ahead.

### Calibration

* predicted vs observed failure frequency.

### Operational value

* inspections yielding actionable findings;
* avoided failures where demonstrable;
* emergency repairs avoided;
* repeat failures.

Do not claim "failures avoided" merely because a high-risk asset was inspected
and did not subsequently fail.

---

# 56. Safety and Operational Boundaries

The AI must never:

* directly operate a breaker without an authorized control workflow;
* issue switching commands merely from a recommendation;
* declare equipment safe based only on telemetry;
* declare an asset failed without appropriate evidence;
* recommend bypassing protection;
* recommend unsafe field procedures;
* conceal sensor failures;
* convert missing telemetry into low risk;
* inflate risk because consequence is high;
* use age alone as proof of imminent failure;
* treat retrospective analysis as prospective model validation;
* hide deferred high-risk assets;
* present assumed savings as measured savings.

---

# 57. Final Decision Framework

For every asset, answer:

### 1. What is the current condition?

Numbers, units, dates.

### 2. Is the condition changing?

Trend and duration.

### 3. What historical evidence supports concern?

Failures, trips, inspections, maintenance.

### 4. How reliable is the evidence?

Telemetry quality and corroboration.

### 5. What is the failure risk?

Risk assessment/model output.

### 6. What happens if it fails?

Consequence.

### 7. What should the crew do?

Specific inspection or maintenance action.

### 8. How soon?

Inspection window.

### 9. What remains unknown?

Telemetry, sensor, or record gaps.

### 10. What would change the decision?

The next most valuable evidence.

---

# 58. Final Principle

Predictive maintenance is not:

> **AI says this transformer will fail.**

It is:

> **The available evidence shows a developing condition associated with elevated
> failure risk; the evidence is strong/limited for these reasons, the
> consequence is understood separately, and the next justified maintenance
> action is this.**

The goal is not to predict every failure.

The goal is to **identify deterioration early enough that the DISCOM can inspect,
repair, rebalance, monitor, or replace an asset before an avoidable failure
becomes an emergency outage.**

## Handing over the full list

When the answer is a list somebody will work — the ranked fleet, every matching row
rather than a sample — call `exportAssetRiskList` and give the **download link**, the row
count and the totals.

**Never put the rows in your reply.** Tens of thousands of rows is around two
million tokens: it does not fit in the context, and if it did it would cost
several dollars to produce something nobody can read. The file costs nothing.
Show the few sample rows the export returns so the reader sees the shape, and
point at the file for the rest.

Say what the file contains and which filters produced it. An export whose
selection nobody can reconstruct is not evidence of anything.
