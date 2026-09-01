---
name: consumption-anomaly-correlation
description: >
  Establishes what the meter and billing records actually show for a disputed
  account — step changes, estimated-then-corrected billing, meter diagnostics,
  seal status and grid events. Use when asked whether a consumption anomaly has
  an innocent explanation, or to check a customer's account of events against
  the record.
allowed-tools:
  - getAccount
  - getBillingHistory
  - getMeterReadings
  - getFieldInspection
  - getGridEvents
---

## Instructions

You establish the physical and billing facts. This is the evidence the verdict
rests on; the conversation is corroboration, not proof.

1. **Pull all five once, at the start.** `getAccount`, `getBillingHistory`,
   `getMeterReadings`, `getFieldInspection` and `getGridEvents`. A conclusion
   drawn from billing alone is the specific failure this review exists to
   prevent — the same billing shape has both an innocent and a culpable cause,
   and only the other four separate them.

   **Once.** These records are historical and do not change while you are
   working. If your answer is sent back for correction, the fault is in the
   reasoning, not in the data — re-read what you already have and fix the
   argument. Fetching the same five sources again returns byte-identical
   results, costs a full set of calls, and leaves the original error in place.

2. **Characterise the anomaly precisely.** A step change down, a step change
   up, a single-period spike, or a drift. State when it began, by how much,
   and against what baseline. Give the figures.

3. **Test the innocent explanations first, by name.** Do not skip to
   interference because it fits.
   - **Estimation catch-up.** Check `estimated_period_count` and
     `longest_estimated_run`. A run of identical estimated bills followed by
     one large actual read is a billing artefact: the consumption accrued over
     the whole run and was billed into one period. The spike is arithmetic,
     not usage.

     To size it, work between two *actual* reads: the last one before the
     estimated run began and the first one after it ended. Real consumption is
     the difference between them; the catch-up is that figure minus what was
     billed as estimate over the same periods. Never extrapolate a baseline
     from the estimated reads themselves — they are the very numbers under
     suspicion, and a baseline invented from them will reconcile to whatever
     you assumed. If no actual read anchors the start of the window, say so
     and report the catch-up as un-computable rather than estimating it.

     Where a meter was exchanged mid-window, the reads carry `role`:
     `closing` is the removed meter's final register and `opening` is the
     replacement's start. They share a date; do not confuse them.
   - **Meter exchange.** Check `getGridEvents` and the reads for an exchange.
     A final read not carried over, or an opening read entered wrongly,
     produces a large false balance with no consumption behind it.
   - **Tariff or occupancy change.** Check the account's declared load and
     tariff dates against when the anomaly began.
   - **Outage or grid work.** Check whether an event covers the period.

4. **Then test the culpable explanation.** Meter diagnostics are the strongest
   signal available: cover-open events with no corresponding work order,
   reverse-running, and a load profile that contradicts the declared load.
   Seal status from `getFieldInspection` is the physical check — a seal whose
   number does not match the one issued at installation is a finding, not an
   ambiguity.

5. **Compare the load profile to what the account says it should be.** An
   account with a notified EV charge point and an off-peak tariff granted for
   overnight charging should show an overnight signature. Its absence, while
   consumption falls, is a substantive finding. Say what the profile shows and
   what the account declares.

6. **Report the arithmetic.** Where the numbers can be reconciled — a
   catch-up amount that matches the accrued under-estimate, or a drop that
   cannot be accounted for by any declared change — show the working. A
   reviewer must be able to check you.

If a record is missing or a tool fails, say which one and treat its question as
open. Do not infer the answer from the records that did return: an unread
inspection is not a clean inspection.
