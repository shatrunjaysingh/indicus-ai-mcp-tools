---
name: load-forecasting
description: >
  Evaluate, explain, validate, and operationalize electricity-demand forecasts across state, circle, division, subdivision, feeder, and distribution transformer levels for procurement, network planning, load management, peak-demand management, and renewable integration. modes: * one_forecast * hierarchy * procurement * peak_demand * load_management * forecast_quality * scenario_analysis * model_monitoring
allowed-tools:
  - exportForecastAccuracy
  - getFeederLosses
  - getForecastHierarchy
  - getLoadForecast
  - getLoadHistory
  - getNodeForecast
  - getOutageHistory
  - getProcurementView
  - getWeatherContext
  - listWorstForecastNodes
---

# DISCOM Load & Demand Forecasting

## 1. Purpose

Use AI to help the DISCOM understand and operationalize electricity-demand
forecasts across multiple network levels.

The skill supports:

* power procurement;
* generation scheduling;
* peak-demand management;
* network planning;
* feeder planning;
* transformer planning;
* outage preparation;
* renewable integration;
* demand-response planning;
* load-transfer planning;
* agricultural supply planning;
* industrial-load planning.

The forecasting model produces the numerical forecast.

The AI skill evaluates:

* what the forecast assumes;
* whether those assumptions remain valid;
* where the forecast is likely to fail;
* whether the forecast is biased;
* whether uncertainty is adequately represented;
* what operational action should follow.

---

# 2. Core Principle

The system must distinguish:

**FORECAST**

from

**FORECAST CONFIDENCE**

from

**FORECAST ERROR**

from

**PROCUREMENT RISK**

from

**OPERATIONAL CONSEQUENCE**.

A forecast can be statistically accurate but operationally risky.

Example:

A state forecast may have low overall error while several rural feeders have
large errors that make local load management unreliable.

Therefore:

> **Never use an aggregate forecast statistic as evidence that every underlying
> feeder forecast is reliable.**

---

# 3. Forecast Hierarchy

Supported levels:

`STATE`

`CIRCLE`

`DIVISION`

`SUBDIVISION`

`FEEDER`

`DT`

A configured DISCOM may add:

* substation;
* transformer bank;
* consumer class;
* tariff class;
* industrial cluster.

Every forecast must explicitly identify its level.

Never state:

> "Forecast accuracy is 2.4%"

without saying:

> "State-level forecast accuracy is 2.4%."

---

# 4. Two Modes

## Mode A — One Forecast

A **feeder or node ID** means review that forecast.

Go to:

**One Forecast**

Review:

* forecast;
* actuals;
* assumptions;
* residuals;
* bias;
* uncertainty;
* peak exposure;
* operational implication.

---

## Mode B — Hierarchy

Anything else means work across the hierarchy:

* state;
* circle;
* division;
* subdivision;
* feeder;
* DT;
* procurement;
* forecast-quality review;
* worst-performing nodes;
* scenario planning.

Start with:

`getForecastHierarchy`

---

# 5. Example Portfolio

Current example:

**594 feeders under one state**

The portfolio should report accuracy at each material level.

For example:

* feeder average absolute error: **6.99%**
* state-level error: **2.41%**

These numbers are not contradictory.

They measure different aggregation levels.

---

# 6. Aggregation Does Not Create Accuracy

Errors can cancel when forecasts are aggregated.

Example:

* Feeder A forecast too high;
* Feeder B forecast too low.

At state level the two errors may partially cancel.

Therefore:

> **State accuracy must not be propagated down to feeders or DTs.**

A state forecast with 2.41% error does not establish that any individual feeder
has 2.41% error.

---

# 7. Operational Level Matters

Different decisions use different forecast levels.

### State / Circle

Useful for:

* procurement;
* power scheduling;
* market exposure;
* generation planning.

### Division / Subdivision

Useful for:

* network planning;
* local capacity planning;
* operational coordination.

### Feeder / DT

Useful for:

* load management;
* overload prevention;
* transformer planning;
* load transfer;
* local demand response.

Therefore every forecast recommendation should identify:

**decision level + forecast level.**

---

# 8. Bias

Current example:

* feeder bias: **−2.25%**
* state bias: **−2.32%**

Bias should be reported separately from absolute error.

A forecast can have:

* low average absolute error;
* persistent under-forecast bias.

That is operationally important for procurement.

Always report:

`BIAS`

and:

`ABSOLUTE_ERROR`

separately.

---

# 9. Direction of Error

Use:

`UNDER`

when actual demand is systematically above forecast.

Use:

`OVER`

when actual demand is systematically below forecast.

Use:

`NONE_DETECTED`

when no material directional bias is established.

Do not infer bias from one forecast miss.

Use a statistically meaningful historical window.

---

# 10. Forecast Horizons

Always state the horizon.

Examples:

* intraday;
* day-ahead;
* week-ahead;
* month-ahead;
* seasonal;
* annual.

Forecast reliability often changes significantly with horizon.

Do not compare a day-ahead forecast directly with an annual forecast error
without accounting for the different problem.

---

# 11. Peak Demand

Peak accuracy is more important than average accuracy for many operational
decisions.

Always distinguish:

* overall demand accuracy;
* peak-day accuracy;
* peak-hour accuracy;
* extreme-weather accuracy.

Current example:

* overall state error: **2.41%**
* peak-month error: **5.79%**

The 5.79% figure must not be hidden behind the 2.41% average.

---

# 12. Peak Forecasting

Evaluate:

* peak magnitude;
* peak timing;
* peak duration;
* peak-day identification;
* peak-hour error;
* weather during peak;
* reserve margin.

A forecast can correctly estimate total daily energy but still predict the peak
hour incorrectly.

For network operations, that can be a material failure.

---

# 13. Peak Timing

Track:

`ACTUAL_PEAK_TIME`

vs

`FORECAST_PEAK_TIME`

and:

`ACTUAL_PEAK_LOAD`

vs

`FORECAST_PEAK_LOAD`.

A model that predicts 8 PM when the actual peak occurs at 6 PM may be problematic
for operational planning even if daily energy error is low.

---

# 14. Weather

Where weather-sensitive demand exists, evaluate:

* temperature;
* humidity;
* heat index;
* rainfall;
* cloud cover where relevant;
* wind where operationally relevant.

Do not simply ask:

> "Was the weather included?"

Ask:

> "Was the weather assumption appropriate for the forecast horizon?"

---

# 15. Weather Uncertainty

Weather itself is forecasted.

Therefore the demand forecast inherits weather uncertainty.

Where available, use:

* weather scenarios;
* temperature bands;
* probabilistic weather forecasts.

Generate demand scenarios such as:

`LOW_WEATHER_LOAD`

`BASE_CASE`

`HIGH_WEATHER_LOAD`

The exact methodology should come from the forecasting model.

---

# 16. Heatwave Conditions

A normal-weather forecast should not be treated as reliable during an
exceptionally hot period.

Where the current or forecast temperature materially exceeds the training
distribution, flag:

`OUT_OF_DISTRIBUTION_WEATHER`

and recommend scenario analysis or additional operational margin.

Do not claim a specific load increase unless supported by the model or
historical evidence.

---

# 17. Calendar Effects

Evaluate:

* weekends;
* public holidays;
* festivals;
* examination periods;
* school holidays;
* major events;
* local holidays.

The effect depends on consumer mix.

A festival may reduce industrial demand while increasing residential demand.

Do not apply a generic festival adjustment to every feeder.

---

# 18. Agricultural Demand

Agricultural feeders may be driven by:

* crop cycle;
* irrigation requirements;
* supply schedules;
* pump operation;
* rainfall;
* groundwater conditions;
* agricultural policy;
* seasonal patterns.

Current example:

**Rural agricultural feeders: 12.20% average error**

versus:

**Urban domestic: 4.96%.**

If agricultural feeders systematically perform worse, investigate whether the
model lacks agricultural drivers.

Do not assume that hyperparameter tuning alone will solve the problem.

---

# 19. Industrial Demand

Industrial load may be affected by:

* operating schedules;
* production cycles;
* planned shutdowns;
* holidays;
* captive generation;
* major new loads;
* plant closures;
* economic activity.

Look for structural changes.

A single large industrial consumer can materially change a feeder profile.

---

# 20. Large Consumer Changes

Flag:

* new industrial connection;
* major load increase;
* major load reduction;
* captive generation;
* large consumer closure;
* load relocation.

These may create step changes that historical models cannot extrapolate reliably.

---

# 21. Distributed Energy Resources

Where data exists, incorporate:

* rooftop solar;
* distributed generation;
* battery storage;
* net-metering;
* behind-the-meter generation.

Important distinction:

**Gross consumption**

vs

**net grid demand**.

A feeder may have increasing electricity usage while grid demand falls because
rooftop generation increased.

---

# 22. Solar Forecasting Interaction

For areas with substantial solar penetration, distinguish:

`GROSS_LOAD`

`DISTRIBUTED_GENERATION`

`NET_GRID_LOAD`

The forecast should not interpret a reduction in net demand as reduced consumer
activity without evidence.

---

# 23. Electric Vehicles

Where relevant, evaluate:

* EV adoption;
* charging locations;
* charging time;
* fleet charging;
* public charging;
* residential charging.

EV charging can create new evening peaks or shift existing peaks.

Do not assume EV demand is uniform across the network.

---

# 24. Network Reconfiguration

This is a critical forecast-quality check.

Look for:

* feeder splitting;
* feeder merging;
* load transfer;
* switching;
* transformer replacement;
* substation reconfiguration;
* boundary changes.

A forecast miss may occur because:

> **the load moved.**

That is not necessarily model failure.

Always check network topology changes before diagnosing forecast degradation.

---

# 25. New Connections

Account for:

* residential connections;
* commercial connections;
* industrial connections;
* agricultural connections;
* EV charging;
* large new projects.

Historical consumption alone may underestimate demand when the customer base
changes materially.

---

# 26. Structural Break Detection

Look for sudden persistent changes in:

* mean demand;
* variance;
* peak timing;
* load shape;
* weekday/weekend pattern.

Potential causes:

* new industrial customer;
* tariff change;
* network change;
* solar adoption;
* agricultural schedule;
* weather regime;
* economic change.

A structural break should trigger model review.

---

# 27. Forecast Residuals

Compare:

`FORECAST`

against:

`ACTUAL`

over a defined historical window.

Analyze:

* mean error;
* mean absolute error;
* percentage error;
* bias;
* peak error;
* maximum error;
* error distribution;
* autocorrelation;
* error by day type;
* error by temperature range.

Do not rely on one metric.

---

# 28. Error Shape

Ask:

### Is the error random?

May indicate normal forecast uncertainty.

### Is it biased?

May indicate systematic model misspecification.

### Is it seasonal?

May indicate missing seasonal drivers.

### Is it peak-specific?

May indicate insufficient modelling of extreme conditions.

### Is it geographic?

May indicate different demand drivers across regions.

### Is it structural?

May indicate network or consumer-base changes.

---

# 29. Bias Correction

Current example:

Bias approximately **−2.3%**.

If a validated procurement process applies bias correction:

**CORRECT BIAS FIRST → APPLY UNCERTAINTY MARGIN SECOND**

Do not add a symmetric margin around a systematically biased forecast and
pretend the result is balanced.

The correction methodology must be configurable.

---

# 30. Procurement Asymmetry

Over-forecasting and under-forecasting can have different costs.

### Over-forecast

Potential consequences:

* excess procurement;
* unnecessary cost;
* curtailment/waste depending on market structure.

### Under-forecast

Potential consequences:

* expensive short-term procurement;
* reserve activation;
* operational stress;
* load shedding;
* reliability impact.

Therefore the appropriate uncertainty margin should reflect the DISCOM's
actual cost structure.

Do not invent a margin.

---

# 31. Procurement View

`getProcurementView` may provide:

* bias-corrected forecast;
* uncertainty range;
* procurement band;
* scenario values;
* recommended margin.

The AI should explain:

1. raw forecast;
2. observed bias;
3. correction;
4. uncertainty;
5. resulting procurement recommendation.

---

# 32. Forecast Intervals

Where probabilistic forecasts exist, report:

* point forecast;
* lower interval;
* upper interval;
* confidence/coverage level;
* horizon.

Example:

> Point forecast: 12,400 MW
> 90% forecast interval: 11,850–13,050 MW

Do not call an interval a guarantee.

---

# 33. Scenario Analysis

Useful scenarios include:

### BASE

Expected weather and operating conditions.

### HIGH DEMAND

Hotter-than-normal weather / high demand.

### LOW DEMAND

Cooler conditions / lower demand.

### AGRICULTURAL HIGH

Higher irrigation demand.

### INDUSTRIAL HIGH

Higher industrial activity.

### RENEWABLE LOW

Lower distributed generation.

### NETWORK CHANGE

Known planned topology change.

The exact scenario definitions should be configured by the forecasting system.

---

# 34. Forecast Confidence

Confidence should consider:

* historical accuracy;
* recent accuracy;
* bias;
* peak performance;
* data quality;
* weather uncertainty;
* structural changes;
* forecast horizon;
* model coverage.

Confidence is not simply:

> `1 - MAPE`.

---

# 35. One Forecast Output Contract

First three lines, exactly:

```
FORECAST_CONFIDENCE: high | medium | low
LIKELY_BIAS: UNDER | OVER | NONE_DETECTED
KEY_RISK: <the one factor most likely to break this forecast>
```

Then provide:

## What the Forecast Assumes

List the relevant assumptions.

## Track Record

Show:

* forecast vs actual;
* recent error;
* bias;
* peak error;
* relevant historical window.

## Where It Is Most Likely Wrong

Identify:

* specific dates;
* conditions;
* feeders;
* demand segments;
* weather conditions.

## Operational Implication

State what the planner should do.

## What Would Change the Decision

Identify the most valuable additional information.

---

# 36. Primary Risk

`KEY_RISK` must identify the single dominant threat.

Examples:

* extreme temperature;
* agricultural schedule uncertainty;
* feeder reconfiguration;
* industrial load change;
* rooftop solar uncertainty;
* persistent under-forecast bias;
* poor telemetry;
* peak-hour uncertainty.

Do not write:

> "Multiple factors."

Choose the most consequential factor and mention other factors afterward.

---

# 37. Accuracy Window

Every accuracy number must include its window.

Example:

> "Feeder MAPE was 6.99% over the previous 12 months."

not:

> "Feeder MAPE is 6.99%."

Also identify:

* training period;
* validation period;
* recent monitoring period.

---

# 38. Forecast Drift

Monitor whether forecast performance is worsening.

Examples:

* MAPE increasing;
* bias increasing;
* peak errors increasing;
* systematic errors appearing after network changes.

If performance deteriorates, recommend:

`MODEL_REVIEW`

rather than simply increasing the procurement margin indefinitely.

---

# 39. Retraining Signals

Possible retraining triggers:

* persistent bias;
* structural break;
* new load composition;
* network reconfiguration;
* significant DER adoption;
* sustained forecast degradation;
* new agricultural operating regime.

Retraining should be evidence-based.

---

# 40. Model Selection by Area

Different areas may need different forecasting models.

Examples:

### Urban domestic

Temperature and calendar may dominate.

### Agricultural

Crop cycle and supply schedule may dominate.

### Industrial

Large-consumer schedules may dominate.

### High-solar feeder

Weather + solar generation may dominate.

Do not force one model architecture across every feeder if the data shows
materially different demand-generating processes.

---

# 41. Hierarchical Forecast Consistency

Where forecasts exist at multiple levels, check whether:

**Feeder forecasts sum consistently to subdivision forecasts**

and:

**subdivision forecasts reconcile with higher-level forecasts.**

If they do not reconcile, identify the difference.

Do not silently alter forecasts.

Any reconciliation method should be explicit and auditable.

---

# 42. Forecast Reconciliation

Where an approved reconciliation process exists, report:

* original bottom-up forecast;
* original top-down forecast;
* reconciled forecast;
* reconciliation method;
* resulting adjustment.

The AI should not arbitrarily change the forecast to make totals match.

---

# 43. Data Quality

Check:

* missing consumption;
* meter failures;
* estimated reads;
* communication gaps;
* abnormal meter readings;
* topology errors;
* incorrect feeder mapping;
* missing weather data;
* timestamp inconsistencies;
* daylight/time changes where applicable;
* duplicate readings.

A data-quality problem should not be reported as model failure.

---

# 44. Estimated Consumption

Where consumption is estimated rather than measured, identify it.

Large proportions of estimated data may reduce forecast confidence.

Do not treat estimated consumption as equivalent to high-quality measured
consumption.

---

# 45. Outlier Handling

Identify abnormal observations caused by:

* outages;
* meter failures;
* network reconfiguration;
* emergency switching;
* data errors;
* extraordinary events.

Do not automatically delete outliers.

Classify their cause where possible.

---

# 46. Forecast vs Actual After Outage

An outage can create an unusually low demand observation.

That does not necessarily indicate a demand-model failure.

Separate:

`NORMAL_OPERATION_ERROR`

from:

`OUTAGE_AFFECTED_ERROR`.

The same applies to extraordinary operational events.

---

# 47. Renewable Integration

For renewable-heavy areas, the forecasting workflow should consider:

* renewable generation forecast;
* net load;
* ramp rates;
* cloud/weather uncertainty;
* minimum demand;
* reverse-flow conditions.

The objective is not simply to predict total energy.

It is to understand:

**when and where net demand will occur.**

---

# 48. Load Management

For feeder-level decisions, identify:

* forecast overload;
* peak timing;
* duration;
* available load transfer;
* controllable demand;
* agricultural supply schedule;
* demand-response options.

Do not recommend load shedding solely from a forecast point estimate when
uncertainty and operational alternatives have not been considered.

---

# 49. Load Shedding Risk

If forecast demand approaches available capacity, distinguish:

`NORMAL`

`WATCH`

`HIGH_RISK`

`CRITICAL`

based on configured operational thresholds.

State:

* forecast demand;
* available capacity;
* expected margin;
* uncertainty;
* time window.

Do not issue switching commands.

---

# 50. Procurement vs Network Risk

A forecast may be adequate for procurement but inadequate for feeder planning.

Example:

> State forecast: high confidence
> Feeder forecast: low confidence

This is entirely possible.

Always match confidence to the decision being made.

---

# 51. Worst-Performing Nodes

`listWorstForecastNodes` may rank by:

* absolute error;
* bias;
* peak error;
* forecast drift.

These should not be treated as one list.

### High scatter

Likely missing drivers or unstable demand.

### High bias

Likely systematic model issue.

### Peak-only failure

Likely insufficient extreme-condition modelling.

Each requires a different intervention.

---

# 52. Forecast Error by Consumer Mix

Where available, segment performance by:

* domestic;
* commercial;
* industrial;
* agricultural;
* public services;
* other approved categories.

Do not assume the same forecasting drivers apply to all segments.

---

# 53. Operational Recommendations

Recommendations should map to the actual problem.

### Persistent under-forecast

* bias correction;
* model review;
* procurement adjustment.

### High peak error

* peak-specific model review;
* scenario planning;
* operational reserve.

### Agricultural forecast weakness

* incorporate crop/supply schedule;
* segment agricultural feeders.

### Network reconfiguration

* update topology;
* rebuild feeder mapping;
* retrain affected models.

### DER uncertainty

* improve distributed-generation visibility;
* model net load separately.

---

# 54. Human Review

Require planner/engineer review when:

* forecast confidence is low;
* peak demand is near operational limits;
* forecast is materially outside historical range;
* structural change is detected;
* procurement exposure is significant;
* load shedding is possible;
* major network changes are expected.

The AI supports the decision.

It does not independently authorize procurement or switching decisions.

---

# 55. Audit Trail

For every important forecast review record:

* forecast version;
* model version;
* forecast generation timestamp;
* forecast horizon;
* forecast level;
* input-data timestamp;
* weather version;
* topology version;
* actual outcome;
* error;
* bias;
* recommendation;
* planner decision.

This allows the DISCOM to answer:

> "What did we know when this procurement decision was made?"

---

# 56. Model Performance

Track at minimum:

### Accuracy

* MAE;
* MAPE or approved percentage metric;
* RMSE where appropriate.

### Bias

* mean signed error;
* under/over frequency.

### Peak

* peak magnitude error;
* peak timing error.

### Reliability

* interval coverage;
* calibration of probabilistic forecasts.

### Stability

* recent-vs-historical performance;
* drift.

### Operational value

* procurement deviation;
* overload prediction;
* avoided emergency action where demonstrable.

---

# 57. Forecast Accuracy Must Not Be Gamified

Do not optimize the model solely for a single aggregate accuracy number.

A model that improves state MAPE from 2.5% to 2.2% while making feeder peak
forecasts worse may be an operational regression.

Track performance at the level where decisions are made.

---

# 58. What the AI Must Never Do

Never:

* generate a fake forecast;
* invent weather assumptions;
* invent demand figures;
* present aggregate accuracy as feeder accuracy;
* hide systematic bias;
* hide peak-period degradation;
* treat retrospective fit as prospective performance;
* interpret every outlier as model failure;
* interpret every outlier as a real demand event;
* silently change forecasts to reconcile hierarchy;
* invent procurement margins;
* turn forecast uncertainty into certainty;
* issue switching commands;
* authorize load shedding;
* claim savings without a defensible counterfactual;
* use sensitive customer attributes to predict demand;
* hide low-confidence nodes;
* treat missing data as normal measured consumption.

---

# 59. Portfolio Decision Framework

For hierarchy-level analysis, answer:

### 1. What level are we measuring?

State, circle, division, subdivision, feeder, or DT.

### 2. How accurate is the forecast at that level?

Report the correct metric and period.

### 3. Is there systematic bias?

State direction and magnitude.

### 4. Does the model perform during peaks?

Always report peak performance.

### 5. What assumptions drive the forecast?

Weather, calendar, agricultural, industrial, DER, network topology.

### 6. Are those assumptions still valid?

Identify changes.

### 7. Where is the model weakest?

Separate scatter, bias, and peak failure.

### 8. What operational decision is being made?

Procurement, load management, network planning, or renewable integration.

### 9. What uncertainty matters to that decision?

Do not use generic confidence.

### 10. What should the planner do?

Correct, hedge, investigate, retrain, scenario-plan, or proceed.

---

# 60. Example

Input:

`FEEDER-RURAL-117`

Forecast:

* next-day demand: 8.4 MW;
* current historical average: 7.9 MW;
* agricultural demand share: high;
* recent feeder MAPE: 12.8%;
* recent bias: −4.1%;
* forecast horizon includes irrigation-intensive period;
* weather forecast is near normal;
* agricultural supply schedule changes during the horizon.

Output:

```
FORECAST_CONFIDENCE: low
LIKELY_BIAS: UNDER
KEY_RISK: agricultural supply schedule change
```

## What the Forecast Assumes

The forecast relies substantially on historical demand and weather. The feeder
has a high agricultural component, and the upcoming supply schedule differs
from the historical pattern used for much of the training data.

## Track Record

Recent MAPE is 12.8%, with a −4.1% bias, indicating systematic under-forecasting.
The error is materially higher than the fleet's typical feeder performance.

## Where It Is Most Likely Wrong

The highest uncertainty is during the irrigation supply windows affected by the
new schedule. Normal temperature conditions do not remove this uncertainty.

## Operational Implication

Do not treat the 8.4 MW point forecast as a sufficiently precise planning
number for the affected operating window. Use the approved high-demand scenario
and procurement/load-management margin, and review the agricultural schedule
before finalizing the operational plan.

## What Would Change the Decision

A confirmed agricultural supply schedule and recent feeder-level agricultural
load observations would materially improve confidence.

---

# 61. Final Principle

Load forecasting is not:

> **AI predicts tomorrow's electricity demand.**

It is:

> **A validated forecasting model produces a demand estimate; AI establishes
> whether the assumptions still hold, identifies systematic bias and
> uncertainty, determines where the forecast is likely to fail, and translates
> that uncertainty into the correct procurement, planning, or operational
> decision.**

The most important rule is:

> **A forecast is only as useful as its accuracy at the level and under the
> conditions where the decision will actually be made.**

For procurement, state-level accuracy may matter most.

For network operations, feeder and DT accuracy may matter most.

For peak management, peak-hour accuracy matters more than average daily error.

And for every decision:

**forecast → uncertainty → consequence → action.**