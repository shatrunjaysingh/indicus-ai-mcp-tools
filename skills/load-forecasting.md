---
name: load-forecasting
description: >
  Reviews a demand forecast for a feeder, subdivision, division or circle —
  what it assumes, how it has performed against actuals, where it is most
  likely wrong, and what it means for procurement and load management. Use
  before acting on a forecast, or to explain a forecast miss after the fact.
allowed-tools:
  - getForecastHierarchy
  - getNodeForecast
  - listWorstForecastNodes
  - getProcurementView
  - exportForecastAccuracy
  - getLoadForecast
  - getLoadHistory
  - getWeatherContext
  - getOutageHistory
  - getFeederLosses
---

## Instructions

### Two modes

A **feeder or node id** means review that forecast — go to *One forecast*
below.

Anything else — the hierarchy, procurement, where the forecasting is worst —
means work across levels. Start with `getForecastHierarchy`.

---

## Working the hierarchy

State, circle, division, subdivision, feeder. **594 feeders under one state.**

### The aggregate number is not the accuracy

**Feeders average 6.99% absolute error. The state comes out at 2.41%.** Same
forecasts. A feeder that ran high and one that ran low net out on the way up,
so the aggregate looks three times better than anything underneath it.

Load management and shedding are decided at feeder and DT level. Procurement is
decided at circle and state. So the accuracy quoted in a procurement meeting is
genuinely good and genuinely irrelevant to the people switching load — **state
which level a figure belongs to, every time, and never carry an aggregate
confidence downward.**

### Bias does not cancel, and absolute error hides it

Bias is **−2.25% at feeder level and −2.32% at state level.** Random error
cancels upward; a systematic under-forecast survives intact.

This is the finding that matters most for procurement, and no absolute-error
measure will show it — a mean absolute percentage error of 2.41% looks
excellent and is consistent with being short every single month. Report bias
separately from scatter, always.

### Peak accuracy is the accuracy that counts

**State error is 2.41% overall and 5.79% in peak months.** A model that is good
in ordinary conditions and poor in April to June is not a good model for
procurement, because those are the months the power has to be bought.

Say the peak figure whenever you say the overall one.

### Correct the bias before adding a margin

`getProcurementView` does this in the right order. A forecast short by 2.3%
every month is corrected upward first, and *then* given a margin. Putting a
symmetric margin on a biased forecast prices the same error twice on one side
and not at all on the other.

Say which way you weighted the band. The two errors do not cost the same:
over-procured power is paid for and wasted, under-procured power is bought at
peak rates or shed, and shedding in an Indian summer is a serious harm.

### Where the effort goes

`listWorstForecastNodes` takes a metric, and the three identify different nodes
with different fixes: **scatter** usually means a driver the model does not
have, **bias** usually means retraining, and a **peak-only** failure means it
was fitted on ordinary conditions.

**Rural agricultural feeders average 12.20% against urban domestic at 4.96%.**
Their demand follows the crop calendar and the supply schedule rather than
temperature, so a temperature-driven model has little to work with. That is a
model-selection problem, not a tuning one.

---

## One forecast

You review a demand forecast that power will be bought against. Over-procured
power is paid for and wasted; under-procured means purchase at peak rates, or
load shedding, and load shedding in an Indian summer is a serious harm.

**You do not produce the forecast.** A time-series model does that. You
establish what it assumed, whether those assumptions hold, where it is most
likely to be wrong, and what the planner should do about the uncertainty. A
forecast without that review is a number with unknown reliability.

### Output contract

First three lines, exactly:

    FORECAST_CONFIDENCE: high | medium | low
    LIKELY_BIAS: UNDER | OVER | NONE_DETECTED
    KEY_RISK: <the one factor most likely to break this forecast>

`LIKELY_BIAS` is the most useful line for a procurement planner: knowing *which
direction* a forecast tends to miss in is worth more than a confidence band,
because the two errors have different costs.

### Check the assumptions before the number

- **Weather.** Demand is dominated by temperature in most Indian distribution
  areas. Establish which temperature assumption the forecast used and how it
  compares with the current outlook. A forecast built on a normal-year
  temperature profile is wrong before it starts in a heatwave year, and the
  error is large — a few degrees of sustained excess moves residential cooling
  load substantially.
- **The calendar.** Festivals, holidays, and examination periods move demand
  and move it differently by area and consumer mix. A forecast that treats a
  festival week as an ordinary week will be wrong in both directions on
  different days. Name the calendar events in the horizon and say whether the
  forecast accounts for them.
- **Agricultural demand** follows the crop calendar and the supply schedule,
  not the weather alone, and is often the largest swing factor in a rural
  subdivision. Check whether the feeder mix is agricultural before trusting a
  temperature-driven forecast on it.
- **Industrial demand** follows working patterns and the economic cycle, and a
  single large consumer starting, stopping, or shifting to captive generation
  can move a feeder's entire profile. Look for step changes, not trends.
- **Structural change** — new connections, solar rooftop growth, electric
  vehicle charging, load transferred between feeders during network changes.
  **Feeder reconfiguration is the most common cause of a forecast looking
  badly wrong when it is actually fine**: the load did not disappear, it moved.
  Check for it before reporting a miss.

### Judge the model by its residuals

Compare recent forecasts against what actually happened. What matters is not
the average error but its shape:

- **Is the error biased?** Consistent under-forecasting is far more dangerous
  than the same magnitude of scatter, and it is invisible in a mean-absolute
  measure.
- **Where does it concentrate?** Errors bunched on peak days, weekends, or
  extreme temperatures mean the model is fine in ordinary conditions and fails
  exactly when the forecast matters most. Say so plainly — a model with good
  average accuracy and bad peak accuracy is not a good model for procurement.
- **Has it drifted?** Accuracy degrading over recent months means the
  relationships the model learnt have changed and it needs retraining.

### Aggregation

Forecasts at circle level hide what happens at feeder level: errors at feeder
level partially cancel when summed, so a circle forecast can look accurate
while individual feeders are badly wrong. Load management decisions are taken
at feeder and DT level, so state which level your confidence applies to, and
never carry a circle-level confidence down to a feeder.

### Required sections

1. **The three-line header.**
2. **What the forecast assumes** — each assumption and whether it holds.
3. **Track record** — recent forecast versus actual, with the bias and where
   errors concentrate. Figures.
4. **Where this forecast is most likely wrong** — the specific days, feeders or
   conditions, not a general disclaimer.
5. **What the planner should do** — the procurement or load-management
   implication, including the margin the uncertainty justifies.

### Tone

Quantitative and direct about uncertainty. A reviewer who overstates confidence
here causes either wasted money or load shedding.
