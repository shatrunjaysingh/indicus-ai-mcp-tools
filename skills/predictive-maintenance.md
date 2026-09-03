---
name: predictive-maintenance
description: >
  Assesses one distribution asset — DT, transformer, feeder or breaker — for
  failure risk from loading, thermal trend, age, maintenance and failure
  history, and recommends an inspection window. Use to decide what a
  maintenance crew should attend next, or to explain an asset a condition model
  has flagged.
allowed-tools:
  - getAssetFleet
  - getFailureReview
  - listAssetsByRisk
  - getAssetRisk
  - buildMaintenancePlan
  - exportAssetRiskList
  - getDTHealth
  - getLoadHistory
  - getMaintenanceHistory
  - getOutageHistory
  - getFeederLosses
---

## Instructions

### Two modes

An **asset id** means assess that asset — go to *One asset* below.

Anything else — the fleet, the month's plan, the failure review, an export —
means work the whole fleet. Start with `getAssetFleet`.

---

## Working the fleet

8,500 assets. **752 need attention. The crews can attend 320.**

### The argument, with its own counter-evidence

`getFailureReview` holds last year's record: **214 failures, 137 of which
showed a rising thermal trend, repeat no-fault-found trips or sustained
overload beforehand** — a median of 34 days beforehand. That is the case for
moving from emergency repair to preventive maintenance, and it is a strong one.

Report the rest of it in the same breath. **61 were on assets with no
telemetry, where nothing could have been seen.** That is an instrumentation
gap, not a modelling one, and no model closes it — the answer is sensors. **16
were genuinely sudden.** A pitch that quotes 137 and omits 77 will be taken
apart by the first engineer who reads it.

### No telemetry means unknown, not low

**3,105 assets — 37% of the fleet — have no SCADA and no smart-meter feed.**
No thermal or loading trend exists for them, so they are scored on age,
maintenance and failure history alone.

Those assets sit low in the ranking because nothing looks wrong, and nothing
looks wrong because nothing is being looked at. Say so whenever you present the
ranking. A maintenance programme that works the top of a list built this way
attends the instrumented third of the network and slowly forgets the rest.

### Consequence never touches the risk band

**1,433 assets are low or medium risk with high consequence** — a hospital, a
water works, a traffic system behind them, often with no alternative feed.

`buildMaintenancePlan` handles this openly: the bulk of the capacity goes to
the highest risk, and a **reserve of 40 visits** goes to high-consequence
assets that did not make the risk cut. Report both numbers.

Never raise an asset's risk band because its failure would matter. That
corrupts the risk figure for every other user of it, and the ranking stops
meaning what it says.

### On the money

The plan returns an avoided-cost estimate resting on an assumption — that a
tenth of attended assets would otherwise have failed within the year — which
this data does not establish. Quote it only with that stated, and tell anyone
building a business case to replace it with the utility's own rate.

---

## One asset

You decide which asset a maintenance crew attends next, from a list longer than
the crew can work. A distribution transformer that fails takes supply from
every consumer behind it, sometimes for days, and a failure in summer peak in a
dense area is a public health matter, not an inconvenience.

**You are not computing a failure probability.** That belongs to a model
trained on failure history. You are reading this asset's condition evidence,
saying what it indicates, and turning it into an inspection decision a planner
can act on and defend. Where a model has produced a probability, your job is to
say whether the asset's record supports it.

### Output contract

First three lines, exactly:

    FAILURE_RISK: CRITICAL | HIGH | MEDIUM | LOW
    INSPECT_WITHIN: <n> days | ROUTINE_CYCLE
    PRIMARY_DRIVER: <the one condition that most drives this>

`PRIMARY_DRIVER` is a single named condition — *sustained overload*,
*thermal trend*, *repeat outages*, *oil condition*, *age with no maintenance*.
A planner triaging fifty of these reads that field first, and a report whose
driver is "multiple factors" has not done the work.

### Trend beats level

A DT at 92% loading that has sat at 90% for three years is in a different state
from one that reached 92% last month from 60%. **The rate of change is the
signal; the absolute number is the context.** Always state both: the current
value, and its direction over a stated window.

The same holds for temperature. A single high oil-temperature reading may be
ambient. A rising trend at constant load is the classic degradation signature
and should drive the risk up sharply — it means the asset is dissipating heat
worse than it did, at the same work.

### What each source is worth

- **Loading against rating** — sustained loading above rating shortens life
  predictably. Distinguish peak excursions from sustained overload; brief peaks
  are tolerable, months above rating are not.
- **Thermal trend, corrected for ambient and load.** Rising temperature at
  constant load and constant ambient is the strongest single indicator here.
  Say explicitly whether you were able to correct for ambient — if the data
  does not let you, the thermal signal is weaker than it looks.
- **Failure and outage history.** Repeat trips on the same asset are the most
  underrated signal in distribution maintenance: an asset that has tripped
  three times this quarter is telling you something, and *"restored, no fault
  found"* is not a clean record. Treat repeat unexplained trips as a positive
  indicator of an intermittent developing fault.
- **Maintenance history.** An asset overdue for its cycle has an unknown
  condition, not a good one. Age alone is weak; age *plus* missed maintenance
  is strong.
- **Unbalanced loading across phases** stresses the asset well below its
  nameplate rating, and an asset can be at 70% average load while one phase is
  overloaded.

### Consequence belongs in the ranking, not in the risk

Keep these separate, and report both:

- **Failure risk** — how likely this asset is to fail. A property of the asset.
- **Consequence** — how many consumers, whether any are critical (hospital,
  water works, traffic control), whether an alternative feed exists, and
  whether the season is peak.

A low-risk asset feeding a hospital with no alternative supply may deserve
attention before a high-risk asset feeding twelve rural connections. Say so as
a ranking recommendation, and never do it by inflating the risk band — that
corrupts the risk assessment for everyone downstream who relies on it.

### Required sections

1. **The three-line header.**
2. **Condition** — each indicator with its value, its trend, and its window.
   Numbers with units and dates.
3. **What the history adds** — failures, trips, maintenance done and missed.
4. **Consequence of failure** — consumers affected, critical loads, alternative
   supply, season.
5. **Recommended work** — what the crew should actually do on attendance: oil
   sample, thermographic scan, load rebalance, tap change, replacement. A risk
   band without a work instruction does not help anyone.
6. **What is not established** — missing telemetry, gaps in the record, a
   sensor you do not trust.

### Tone

Engineering. Quantities and dates throughout. No hedging language where a
number exists.
