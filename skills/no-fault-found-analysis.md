---
name: no-fault-found-analysis
description: >
  Finds where warranty replacements are going to batteries that were not faulty ("no fault found" at the factory retest), explains why from the technicians' field readings, and says what to change. Use when asked why warranty cost is high, which cities, technicians or dealers replace healthy batteries, or whether a specific replacement was justified.
allowed-tools:
  - getWarrantySummary
  - getNoFaultFoundAnalysis
  - getTechnicianProfile
  - listClaims
  - getClaim
  - getFactoryRetest
  - getBattery
  - getReference
---

# No-fault-found analysis

## Purpose

Every battery replaced under warranty is sent back and retested at the plant.
When the plant finds it healthy — **no fault found (NFF)** — the replacement was
given away. Across a battery maker that is often the largest avoidable warranty
cost. This skill finds where NFF concentrates, explains it from what the
technician measured *before* replacing, and recommends a fix that a service
manager can act on this week.

## What "healthy" looks like

A battery that has rested shows **OCV 12.4 V or more**, **passes a load test**,
and its **six cell gravities sit within 1.24–1.28** and within 0.05 of each
other. A battery brought in flat is not necessarily faulty: a weak alternator
(undercharging) or a parasitic drain empties a good battery overnight. That is
why a **load test after charging** and an **alternator check** are the two
readings that separate a dead battery from a dead vehicle.

## Method

1. **Size it.** `getWarrantySummary` — overall NFF rate, retested count, cost of
   NFF in rupees, and the NFF rate by city. Name the overall rate as the baseline.
2. **Find where it concentrates.** `getNoFaultFoundAnalysis` grouped by `city`,
   then by `technician` (and `dealer`) inside any city well above baseline. Use
   the 95% interval: a group is only "high" if its interval sits above the
   baseline, not if one point estimate does.
3. **Explain it from the readings.** For the high groups, read `before_replacing`:
   share of OCV ≥ 12.4 V, load tests not done, alternator not checked. Then
   `getTechnicianProfile` for named technicians to compare with their city peers.
4. **Check the counter-explanation.** A city whose claims rose is not an NFF
   problem if the factory confirms the failures. Run `getNoFaultFoundAnalysis`
   with `group_by=month` for that city: a seasonal rise with a *low* NFF rate is
   real failure (e.g. heat: grid corrosion, dry-out), not giveaways.
5. **Spot-check.** Open two or three claims (`getClaim`, `getFactoryRetest`) that
   represent the pattern, and quote their readings.

## Evidence standard

- Every rate comes with its count ("72% — 59 of 82 retested"), never alone.
- Name the pattern in the technicians' readings, not just the rate:
  *"In Pune, 85% of the replacements by TEC-PUN-004 had no load test; 66% came
  back healthy."*
- Say what it cost in rupees (`cost_of_no_fault_found_rupees`).

## What not to conclude

- **Do not call a technician dishonest.** Replacing without testing is a process
  failure until shown otherwise; recommend coaching and a mandatory load test,
  and leave misconduct to the fraud review.
- **Do not treat more claims as more NFF.** Claim volume rises for real reasons
  (season, age, a bad batch). Only the factory verdict says a battery was healthy.
- **Do not rank groups with few retests.** Under ~10 retests, say the sample is
  too small.

## Output

1. **Headline** — the NFF rate, what it cost, and where it concentrates.
2. **Why** — the reading pattern behind it, with two or three example claims.
3. **What is not the problem** — the counter-explanation you checked and why it
   is ruled out (or in).
4. **What to do** — specific: e.g. load test and alternator check required before
   any replacement is approved; coaching for named technicians; a supervisor
   check on replacements with OCV ≥ 12.4 V.
5. **Saving** — NFF cost that the change would avoid at the current rate.
