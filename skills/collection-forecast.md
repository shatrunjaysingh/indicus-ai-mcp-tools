---
name: collection-forecast
description: >
  Forecast expected electricity-revenue collection for the coming month, quantify uncertainty and forecast bias, separate baseline collection from incremental campaign recovery, identify the factors most likely to change the result, and distinguish an achievable operational forecast from a management target. modes: * monthly_forecast * portfolio * segment_forecast * campaign_scenario * target_gap * forecast_quality * sensitivity_analysis * model_monitoring * export
allowed-tools:
  - buildCampaignList
  - getCollectionForecast
  - getCollectionPortfolio
---

# AI Expected Monthly Collection Forecast

## Purpose

Predict how much money the utility is likely to collect during the coming month.

The skill must answer four different questions separately:

1. **What is the baseline collection forecast?**
2. **How uncertain is that forecast?**
3. **How much incremental recovery could approved interventions add?**
4. **How does the forecast compare with the management target?**

Do not collapse these into one number.

The core output is:

> **Expected collection under stated assumptions, with uncertainty, bias, and target gap clearly separated.**

The forecast is an operational prediction.

It is **not** a promise, a target, or a statement of what the utility should collect.

---

# Core Principle

## Forecast what the book is likely to yield

The baseline forecast should represent expected collection under the current or explicitly stated collection environment.

Do not silently assume:

* additional field visits,
* additional calls,
* stronger enforcement,
* improved payment rates,
* a new campaign,
* reduced outages,
* improved billing,
* or management intervention.

If those actions are expected, model them as a separate scenario or incremental contribution.

---

# Baseline vs Campaign

Always maintain at least two numbers:

### Baseline collection

Expected collection from the existing book under the stated current-effort assumptions.

### Incremental campaign recovery

Additional recovery expected from a specified intervention.

For example:

```text
BASELINE_COLLECTION: ₹X cr
CAMPAIGN_INCREMENT: ₹Y cr
COMBINED_SCENARIO: ₹X + ₹Y cr
```

Do not present the combined number as the baseline forecast.

If campaign uplift has not been validated by an approved model:

> Campaign impact is not independently established; no incremental amount is included in the baseline forecast.

---

# Forecast Horizon

The default horizon is:

> **the next calendar month**

State:

* forecast month,
* forecast generation date,
* data cutoff date,
* collection window,
* billing/payment periods represented,
* model version,
* and forecast horizon.

Do not mix:

* next-month collection,
* lifetime recoverable collection,
* annual collection,
* and current-month receipts.

These are different forecasts.

---

# Within-Month Collection

The forecast must explicitly account for **when payments arrive**, not just whether an account eventually pays.

A consumer may pay:

* within the forecast month,
* after the forecast month,
* before the bill is due,
* after a reminder,
* after a field visit,
* or only after escalation.

Therefore:

> expected recovery over the life of the outstanding book ≠ expected collection during the coming month.

If the model historically captures a within-month payment share, report that assumption.

Example:

> 82% of modeled recoveries historically occur within the collection month; the remaining expected recovery falls outside the forecast window.

Do not include outside-window recovery in the monthly forecast merely because it is expected eventually.

---

# Forecast Construction

Use the approved collection forecasting model.

The model may incorporate:

* current outstanding/recoverable exposure,
* payment probability,
* payment timing,
* recent collection,
* historical collection,
* delinquency age,
* payment behavior,
* customer segment where operationally valid,
* billing calendar,
* seasonality,
* holidays/festivals,
* agricultural cycles,
* industrial billing patterns,
* planned collection activity,
* payment channels,
* recent tariff/billing changes,
* large-account events,
* temporary disconnections,
* permanent disconnections,
* and other approved operational drivers.

The AI does **not** independently calculate millions of consumer-level probabilities.

It interprets and validates the forecast produced by the approved forecasting system.

---

# Relationship to Payment Probability

The payment-probability model answers:

> Will this account pay in the current horizon?

The collection forecast answers:

> How much money will the entire book actually collect during the coming month?

These are related but not interchangeable.

At portfolio level, the forecast should aggregate approved account/segment predictions while accounting for:

* amount outstanding,
* payment timing,
* collection window,
* correlation,
* seasonality,
* campaign effects,
* and portfolio-level calibration.

Do not simply multiply total outstanding by an average payment probability unless that is the approved forecasting methodology.

---

# Expected Recovery

Where the approved methodology uses account-level expected recovery:

`expected recovery = recoverable amount × approved payment probability`

use the model's output rather than recomputing it.

At portfolio level:

`monthly collection forecast = approved aggregation of expected within-month recoveries`

The aggregation method must be documented.

Do not assume that a portfolio forecast equals:

`total outstanding × average probability`

unless the model explicitly defines it that way.

---

# Forecast Distribution

For every monthly forecast, report the expected collection and, where supported, an uncertainty interval.

Example:

```text
EXPECTED_COLLECTION: ₹X cr
FORECAST_INTERVAL: ₹Y–₹Z cr
```

The interval is not a target range.

It represents forecast uncertainty under the stated assumptions.

If the model does not produce a validated interval, do not manufacture one.

Instead state:

> No validated forecast interval is available; confidence is based on historical forecast error and current data/model conditions.

---

# Forecast Confidence

Confidence should reflect forecast reliability, not whether the forecast number is high.

### High

Use when:

* recent forecast error is stable,
* bias is small or corrected,
* current portfolio resembles the training/reference population,
* data quality is strong,
* payment behavior is stable,
* no major structural changes are expected,
* and the forecast horizon is well covered.

### Medium

Use when:

* recent error is moderate,
* some assumptions are uncertain,
* seasonality or portfolio changes are material,
* or model coverage is incomplete.

### Low

Use when:

* recent forecasts have large or persistent errors,
* strong directional bias exists,
* portfolio composition changed materially,
* data quality is poor,
* large-account behavior is uncertain,
* payment timing changed,
* major operational events are expected,
* or the forecast is outside the model's validated operating range.

---

# Read the Shape of Forecast Error

Do not summarize forecast quality only as:

> "MAPE is 10%."

First determine the **direction and structure of error**.

Distinguish:

### Random error

Forecasts move above and below actuals.

Interpretation:

> The book contains substantial unpredictability.

### Persistent positive error

Forecast repeatedly exceeds actual collection.

Interpretation:

> The forecast is systematically optimistic.

### Persistent negative error

Forecast repeatedly falls below actual collection.

Interpretation:

> The forecast is systematically conservative.

### Seasonal error

Forecast performs differently during specific months or seasons.

### Peak/event error

Forecast is reasonable in ordinary months but misses:

* festival periods,
* agricultural cycles,
* major industrial billing events,
* tariff changes,
* or other known events.

### Structural error

Forecast deteriorates after a material change in:

* portfolio composition,
* billing process,
* payment channels,
* tariff,
* disconnection policy,
* meter coverage,
* or collection strategy.

Always report the error shape before reporting its magnitude.

---

# Bias Correction

If persistent bias exists:

1. identify the direction,
2. quantify the historical bias,
3. determine whether the bias is statistically/materially persistent,
4. apply the utility's approved bias-correction methodology,
5. then construct uncertainty around the corrected forecast.

Do not manually alter the forecast simply to make it match the management target.

A target is not evidence that the model is wrong.

---

# Target vs Forecast

Always separate:

```text
FORECAST: ₹X cr
MANAGEMENT_TARGET: ₹Y cr
GAP: ₹Y - ₹X cr
```

Then classify the gap.

### Forecast exceeds target

The target appears achievable under the forecast assumptions.

Do not guarantee achievement.

### Forecast approximately matches target

Target is broadly aligned with expected collection.

Still report uncertainty.

### Target exceeds forecast

The target requires additional collection performance.

Do not silently increase the forecast.

State:

> The current baseline forecast is below target by ₹X cr. Additional recovery or improved payment behavior is required to close the gap.

---

# Target Achievability

A management target is not automatically achievable because it was approved.

Assess the target against:

* historical collection,
* recent forecast accuracy,
* recoverable outstanding,
* expected payment behavior,
* collection capacity,
* planned campaigns,
* channel capacity,
* field capacity,
* statutory constraints,
* seasonal effects,
* and validated campaign uplift.

If no validated intervention scenario can close the gap, say so.

Example:

> The ₹50 cr target exceeds the baseline forecast by ₹6.2 cr. Approved campaign capacity is modeled to contribute ₹2.1 cr incremental recovery, leaving an estimated ₹4.1 cr gap.

Do not call the remaining gap impossible unless the evidence supports that conclusion.

---

# Campaign Scenarios

When the user asks:

> "How much can we collect if we run a campaign?"

Do not replace the baseline forecast.

Produce:

### Scenario A — Baseline

Expected collection under current effort.

### Scenario B — Campaign

Baseline plus validated incremental recovery.

### Scenario C — High/Low

Alternative scenarios using approved assumptions.

Example:

```text
BASELINE: ₹42.0 cr
CAMPAIGN_INCREMENT: +₹2.4 cr
CAMPAIGN_SCENARIO: ₹44.4 cr
TARGET: ₹46.0 cr
REMAINING_GAP: ₹1.6 cr
```

Every number must be sourced.

---

# Campaign Double Counting

Avoid counting the same recovery twice.

For example:

* payment probability already incorporates ordinary SMS reminders;
* the campaign model also estimates SMS recovery.

Do not add both as independent effects unless the model explicitly accounts for the overlap.

Similarly, do not add:

* field campaign recovery,
* payment-probability recovery,
* and chronic-default intervention recovery

without determining whether they refer to the same accounts and same payment events.

---

# Seasonality

Evaluate month-specific collection patterns.

Consider:

* historical month-of-year collection,
* billing cycles,
* holidays,
* festivals,
* agricultural cycles,
* monsoon/rainfall effects where relevant,
* industrial shutdowns,
* school/exam periods where relevant,
* government payment cycles,
* salary cycles where supported,
* and other documented operational patterns.

Do not infer personal financial circumstances from seasonal payment behavior.

---

# Agricultural Collection

Where agricultural consumers materially affect the book, evaluate:

* crop cycles,
* irrigation periods,
* supply schedules,
* rainfall,
* agricultural payment patterns,
* policy changes,
* and seasonal arrears.

Agricultural behavior can create systematic forecast error.

Do not assume the same collection curve applies to agricultural and non-agricultural loads/accounts.

Use category only where it is operationally and legally relevant.

---

# Industrial and Large Accounts

Large consumers can materially move monthly collection.

Check for:

* major industrial accounts,
* large payment commitments,
* shutdowns,
* production changes,
* captive generation,
* payment arrangements,
* disputes,
* delayed payments,
* new large connections,
* account closure,
* and extraordinary one-time receipts.

Do not let a single large-account event silently distort the entire forecast.

Report its contribution separately where material.

Example:

> Three large accounts represent 11% of the portfolio's expected collection; one has an unresolved payment commitment, creating material downside uncertainty.

---

# Structural Changes

Explicitly check for:

* tariff changes,
* billing-system migration,
* meter replacement,
* AMI rollout,
* new payment channels,
* changed due dates,
* changed disconnection policy,
* new collection agency,
* account transfers,
* portfolio acquisition,
* major customer onboarding,
* customer migration,
* or changes in bill-generation timing.

Historical collection patterns may not apply after a structural change.

---

# Outstanding Exposure

Track:

* opening outstanding,
* new billed amount,
* recoverable outstanding,
* expected collection,
* expected closing outstanding.

A useful portfolio identity is:

`closing exposure ≈ opening exposure + new billings − collections − valid adjustments`

Use the utility's approved accounting definition.

Do not interpret a fall in outstanding as collection success without checking:

* write-offs,
* billing corrections,
* reversals,
* account closure,
* transfers,
* and other non-cash movements.

---

# Cash vs Accounting Movement

The collection forecast should represent actual cash/receipt collection where that is the defined target.

Separate:

* cash receipts,
* ledger adjustments,
* write-offs,
* reversals,
* transfers,
* credits,
* and accounting reclassifications.

A ₹5 cr reduction in outstanding is not necessarily ₹5 cr collected.

---

# Data Quality

Before trusting the forecast, check:

* missing payment records,
* delayed receipt posting,
* unapplied receipts,
* duplicate receipts,
* billing delays,
* estimated bills,
* meter communication gaps,
* account transfers,
* closed accounts,
* duplicate consumers,
* abnormal billing,
* tariff changes,
* payment-channel outages,
* and data-cutoff inconsistencies.

If material data quality issues exist, lower confidence and identify their likely direction of impact where possible.

---

# Collection Timing

The forecast must distinguish:

* billed but not yet due,
* currently due,
* overdue,
* long-overdue,
* under arrangement,
* disputed,
* and otherwise recoverable balances.

A large outstanding amount that is not yet due should not be treated as equivalent to overdue arrears.

---

# Forecast Reconciliation

Where forecasts exist at multiple levels:

* state,
* circle,
* division,
* subdivision,
* feeder/customer segment,

ensure that approved forecasts reconcile where required.

Do not independently sum overlapping forecasts.

Do not silently modify lower-level forecasts to force reconciliation.

If reconciliation is required, use the approved forecasting/reconciliation process and report that adjustment.

---

# Error Metrics

Monitor at minimum:

* MAE,
* RMSE,
* MAPE where meaningful,
* WAPE,
* bias,
* median absolute error,
* forecast interval coverage,
* forecast interval width,
* month-of-year error,
* segment error,
* large-account error,
* and within-month timing error.

Do not rely on MAPE alone when actual collection can approach zero.

WAPE or another approved portfolio metric may be more informative.

---

# Forecast Quality by Segment

Evaluate forecast error separately for materially different portfolios.

Examples:

* domestic,
* commercial,
* industrial,
* agricultural,
* government,
* high-value accounts,
* chronic-default accounts,
* early-warning accounts.

Do not assume a portfolio-wide error rate applies uniformly to every segment.

A segment with 5% error can coexist with another segment at 15%.

---

# Forecast vs Actual Feedback

After the month closes:

1. capture actual collection,
2. reconcile cash receipts,
3. compare actual vs forecast,
4. calculate error,
5. classify error shape,
6. identify drivers,
7. determine whether bias is persistent,
8. update the forecasting model through the approved model-development process.

Store:

```text
FORECAST
→ ASSUMPTIONS
→ ACTUAL COLLECTION
→ ERROR
→ ERROR TYPE
→ DRIVER
→ MODEL UPDATE
```

Do not overwrite the original forecast.

Historical forecasts must remain auditable.

---

# Early-Within-Month Updating

If the system supports forecast updates during the month, distinguish:

* original forecast,
* revised forecast,
* actual-to-date collection,
* remaining-month forecast.

Example:

```text
ORIGINAL_FORECAST: ₹42.0 cr
COLLECTED_TO_DATE: ₹19.5 cr
REVISED_REMAINING: ₹21.2 cr
REVISED_MONTH_FORECAST: ₹40.7 cr
```

Do not compare the revised forecast against actual using the original forecast's data cutoff.

---

# Sensitivity Analysis

Where appropriate, show what could materially move the forecast.

Examples:

* payment probability +5%,
* payment probability −5%,
* campaign uplift achieved,
* campaign uplift missed,
* large-account payment delayed,
* agricultural collection below historical seasonal level,
* industrial payment delayed,
* payment-channel outage,
* unusually high/low seasonal behavior.

Use approved scenario assumptions.

Do not manufacture arbitrary percentages.

---

# Forecast Drivers

For every forecast, identify the major drivers.

Examples:

* recoverable outstanding,
* recent payment trend,
* within-month payment timing,
* seasonal collection pattern,
* large-account commitments,
* campaign activity,
* chronic-default exposure,
* or data-quality uncertainty.

Do not produce a generic list of every possible driver.

Identify the factors actually supported by the forecast model.

---

# One Forecast Output Contract

For a single monthly forecast, begin with exactly:

```text
EXPECTED_COLLECTION: <amount>
FORECAST_CONFIDENCE: high | medium | low
PRIMARY_RISK: <the one factor most likely to make the forecast wrong>
```

Then provide:

## Forecast basis

State:

* forecast month,
* data cutoff,
* model version,
* baseline assumptions,
* expected collection,
* forecast interval if available.

## Error history

State:

* recent forecast errors,
* direction,
* whether the error is random or biased,
* and the most relevant historical comparison.

## Baseline vs campaign

If a campaign is requested:

```text
BASELINE_COLLECTION: <amount>
CAMPAIGN_INCREMENT: <amount>
COMBINED_SCENARIO: <amount>
```

If no validated campaign uplift exists, say so.

## Target comparison

If a target exists:

```text
FORECAST: <amount>
TARGET: <amount>
GAP: <amount>
```

Then explain whether the gap can plausibly be closed under approved scenarios.

## What could change the forecast

Identify the two or three material sensitivities.

## What is not established

State explicitly:

* forecast is not a guarantee,
* target is not evidence of forecastability,
* historical correlation is not necessarily causal,
* campaign uplift is not guaranteed,
* expected recovery is not the same as cash already collected.

---

# Portfolio Output

For portfolio requests report:

| Measure                      |                        Value |
| ---------------------------- | ---------------------------: |
| Forecast month               |                      sourced |
| Baseline expected collection |                      sourced |
| Forecast interval            |                      sourced |
| Opening recoverable exposure |                      sourced |
| Expected new billings        |                      sourced |
| Expected closing exposure    |                      sourced |
| Management target            |                      sourced |
| Target gap                   | derived from sourced figures |
| Campaign increment           |             sourced/modelled |
| Forecast confidence          |             model assessment |

Then provide the primary reasons for the forecast.

---

# Management View

When presenting to management, use this sequence:

### 1. What will we probably collect?

Baseline forecast.

### 2. How much should we trust it?

Confidence + uncertainty + historical error.

### 3. Is the model biased?

Direction and magnitude of recent error.

### 4. Are we above or below target?

Forecast vs target.

### 5. What can management change?

Validated campaign/scenario increments.

### 6. What could break the forecast?

Primary downside/upside risks.

This prevents the forecast from becoming a disguised target.

---

# Guardrails

Never:

* increase the forecast merely to match the target,
* call a target a forecast,
* include campaign recovery in baseline without disclosure,
* count the same campaign recovery twice,
* treat accounting adjustments as cash collection,
* treat lifetime recovery as within-month collection,
* fabricate forecast intervals,
* invent campaign uplift,
* use raw outstanding instead of validated recoverable exposure,
* infer ability to pay,
* infer willingness to pay,
* characterize consumers by socioeconomic status,
* use protected attributes or their proxies,
* or present a forecast as guaranteed.

---

# Source Discipline

Every numerical statement must have a source.

Preferred format:

```text
[collection_forecast:v4.2: ₹42.0 cr]
[forecast_error: Apr–Sep 2026: +8.5% to +11.7%]
[portfolio: 10,00,000 accounts, ₹135 cr recoverable]
[CAM-2026-03: 5,000 visits, ₹48.2 L recovered]
[target: FY2026-27 monthly target ₹46.0 cr]
```

A number without a source does not go in.

Derived arithmetic should identify its inputs.

Example:

> Target gap = ₹46.0 cr − ₹42.0 cr = ₹4.0 cr, based on the forecast and target above.

---

# Human Review

Human review is required when:

* forecast materially changes from the prior forecast,
* target gap is material,
* forecast is outside validated model range,
* a large-account event materially affects the result,
* a structural portfolio change occurred,
* campaign uplift is being used for management commitment,
* or data quality materially affects the forecast.

The AI supports planning.

It does not set the official collection target.

---

# Quality Gate

Before returning the forecast, verify:

* [ ] Forecast month is explicit.
* [ ] Data cutoff is explicit.
* [ ] Baseline and campaign recovery are separated.
* [ ] Expected collection is sourced from the approved forecast model.
* [ ] Forecast uncertainty is reported where available.
* [ ] Historical error direction is examined.
* [ ] Persistent bias is distinguished from random error.
* [ ] Within-month collection timing is accounted for.
* [ ] Recoverable exposure is distinguished from ledger outstanding.
* [ ] Cash collection is distinguished from accounting movements.
* [ ] Seasonality has been considered where material.
* [ ] Large-account effects have been checked.
* [ ] Structural changes have been checked.
* [ ] Data quality has been checked.
* [ ] Target and forecast are separate.
* [ ] Campaign uplift is not double-counted.
* [ ] No unsupported campaign benefit is claimed.
* [ ] No protected attributes or socioeconomic inference is used.
* [ ] Every figure has a source.
* [ ] Forecast is not represented as a guarantee.
* [ ] Original forecasts remain auditable after revisions.

---

# Architecture

```text
CONSUMER / BILLING / PAYMENT DATA
              │
              ├── RECOVERABLE EXPOSURE
              ├── PAYMENT HISTORY
              ├── PAYMENT PROBABILITY
              ├── PAYMENT TIMING
              ├── BILLING CALENDAR
              └── ACCOUNT EVENTS
                       │
                       ▼
              COLLECTION FORECAST MODEL
                       │
          ┌────────────┼─────────────┐
          ▼            ▼             ▼
       BASELINE      UNCERTAINTY   BIAS MONITOR
          │            │             │
          └────────────┼─────────────┘
                       ▼
              FORECAST VALIDATION
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
     TARGET GAP              CAMPAIGN SCENARIO
          │                         │
          └────────────┬────────────┘
                       ▼
                MANAGEMENT VIEW
                       │
                       ▼
                ACTUAL COLLECTION
                       │
                       ▼
              FORECAST-VS-ACTUAL
                       │
                       ▼
                 MODEL FEEDBACK
```

The architectural boundary is:

> **Payment probability predicts account behavior. Collection forecasting predicts portfolio cash collection. Campaign optimization estimates incremental intervention recovery. Management targets define desired performance.**

These four concepts must remain separate.

---

# Final Principle

A useful monthly collection forecast does not merely answer:

> **"How much will we collect?"**

It answers:

> **"How much will we probably collect, how reliable is that estimate, is the model systematically biased, what is already assumed in the baseline, what additional recovery is actually supported by intervention scenarios, and how does that compare with the target?"**

The operating sequence is:

> **RECOVERABLE EXPOSURE → PAYMENT/TIMING MODEL → BASELINE FORECAST → UNCERTAINTY → BIAS CHECK → CAMPAIGN INCREMENT → TARGET GAP → MANAGEMENT ACTION → ACTUAL COLLECTION → FEEDBACK**