---
name: early-batch-failure
description: >
  Watches early-life failure rates by manufacturing batch, line and plant, finds a batch failing faster than it should, and explains the likely cause from field readings, factory verdicts and the production record. Use when asked whether any batch or plant has a quality problem, to investigate a specific batch or serial, or to decide whether to contain stock.
allowed-tools:
  - getBatchFailureRates
  - getBatch
  - getProductionRecord
  - getBattery
  - listClaims
  - getClaim
  - getReference
  - getWarrantySummary
---

# Early batch failure

## Purpose

A manufacturing defect shows up months later as complaints scattered across
cities and dealers, and nobody connects them until the cost is large. Serials
encode where and when a battery was made (`EX-A2-2603-2-00117`: plant A, line 2,
March 2026, batch 2), so failures can be traced back to the batch that made
them. This skill raises a batch problem early, with the evidence a quality team
needs to decide whether to hold stock.

## Method

1. **Rates, not counts.** `getBatchFailureRates` (default: failures within 6
   months of sale, per 1,000 batteries sold, genuine failures only). Compare each
   batch with the **median**, and use the 95% interval: a batch is anomalous only
   if its *lower* bound sits clearly above the median. A batch with the most
   claims is often just the biggest or oldest one.
2. **Look around it.** Re-run grouped by `line` and `month_made`, and check the
   neighbouring batches from the same line and month. A defect that started at a
   point in production usually touches the batches either side.
3. **Read the failures.** `getBatch` for the suspect: months in service at failure
   (early-life failures cluster in the first months), the factory verdicts (is it
   one failure mode?), the reading profile (e.g. the same cell reading low), and
   where it was sold (spread across cities means it is the battery, not the
   region).
4. **Find the cause.** `getProductionRecord`: separator lot and supplier,
   formation temperature, QC notes. Check `other_batches_with_this_separator_lot`
   — those batteries carry the same risk even if they have not failed yet.
5. **Estimate exposure.** Units sold from the batch (and affected neighbours) that
   are still in warranty, times the observed early-failure rate.

## Evidence standard

- Always state the rate, the interval and the median together:
  *"178 per 1,000 (95%: 125–248) against a median of 7.5."*
- A cause is "likely", backed by at least two independent signals (e.g. one
  failure mode + a production change). Never certain from field data alone.

## What not to conclude

- **Do not flag the batch with the most claims** without its rate. Size and age
  produce claims.
- **Do not blame a plant for one batch.** Check the plant's and line's rate; one
  bad batch on a normal line is a batch problem.
- **Do not count no-fault-found claims as failures.** Healthy batteries returned
  are a service problem, not a manufacturing one.

## Output

1. **Alert** — the batch, its early-failure rate against the median, and confidence.
2. **Evidence** — failure mode, timing, cities, readings, example serials.
3. **Likely cause** — from the production record, and which other batches share it.
4. **Exposure** — batteries in the field at risk, and the estimated cost.
5. **Recommended containment** — e.g. hold unsold stock from the batch and
   same-lot batches, a proactive check-up for sold units, a separator-supplier
   review. Note what would confirm the cause (teardown of returned units).
