---
name: recovery-action-ladder
description: >
  Chooses the recovery action for a consumer or a segment — reminder, call,
  field visit, notice, disconnection — matching the channel to the segment's
  response rather than to the size of the debt. Use for "what should we do
  about this account" and for choosing between channels.
allowed-tools:
  - getRecoveryChannels
  - getCollectionPortfolio
  - buildCampaignList
  - getConsumer
  - getBillingHistory
  - getPaymentHistory
  - getConsumptionHistory
  - getNoticeHistory
  - getDisconnectionRecord
---

## Instructions

The ladder is SMS → call → field visit → notice → disconnection. You choose the
rung.

### Match the channel to the response, not to the debt

An SMS costs ₹0.35 and a field visit ₹260. A segment that responds to SMS
should never receive visits, however much it owes.
`getCollectionPortfolio` returns each segment's historical response by
channel; that settles the choice, not the balance.

### The highest response rate is not the best action

**Disconnection has the highest response rate against every segment that can
pay** — reliable-slow responds at 0.94, because people pay immediately when
their supply is cut. It is the most effective action available and, against
that segment, the least defensible: they pay every cycle already.

The ordering by effectiveness is close to the reverse of the ordering by
proportionality. A recommendation reading only the response column always
arrives at disconnection. Say what each rung costs the consumer as well as the
utility.

### Disconnection is gated, not ranked

Every other channel can be pointed at the highest-value accounts. This one
cannot. `buildCampaignList(channel=disconnection)` applies the precondition —
notice served, notice period expired, undisputed, billed on actual reads — and
returns the counts blocked by each reason.

Report those counts. An account blocked for want of a served notice is not a
dead end; it is an account whose next action is the notice.

---

## One account

    PAYMENT_LIKELIHOOD: high | medium | low
    RECOVERY_ACTION: REMIND | CALL | FIELD_VISIT | NOTICE | DISCONNECT | HOLD
    CONFIDENCE: high | medium | low

**Read the payment behaviour, not the balance.** Count the cycles: paid on
time, paid late, unpaid. A consumer who always pays in the last week before
disconnection is *reliable*, not delinquent.

**A deteriorating trend beats a large balance.** Three missed cycles after
years of payment is a change of circumstances and the strongest early-default
signal available.

**Check what has already been tried.** `getNoticeHistory` records it. Never
recommend a rung that has already failed twice.

**Reconcile the arrears before acting on them.** `getPaymentHistory` returns
receipts as well as periods. A receipted payment never applied to the ledger
means the consumer is being pursued for money they have paid — the action is
`HOLD` and a correction, not recovery.

**Bars on DISCONNECT**, all of which must hold and each of which must be
stated: undisputed and billed on actual reads, not a run of estimates;
statutory notice served and expired; no instalment arrangement being honoured;
and within the recovery limitation period — amounts first shown as due more
than two years ago are barred under §56(2) of the Electricity Act 2003 unless
continuously shown as recoverable. Where supply is life-critical on a
registered medical need, escalate to a human rather than recommending
disconnection.

Then: **basis** with counts, **what points the other way** (never empty),
**expected outcome** and the next rung if it fails, and **what is not
established**.
## Across every collection decision

**Rank on expected recovery: outstanding × payment probability.** Neither alone.
The segment holding the most money returns the least of it in almost every
book, and a decision built on the balance column works the accounts least
likely to pay.

**You do not compute payment probability.** A scoring model does that for every
account. `getConsumerScore` returns the features behind any one of them, so a
score can be explained rather than asserted.

**Category and locality are not risk factors.** A domestic consumer in a rural
subdivision is not a worse payer for being either, and treating them so
produces a programme that concentrates on the poor and misses the large
commercial defaulters. Use category only where it changes the legal route or
the arithmetic.

**Cite every figure.** `[segment chronic_defaulter: 329,770 accounts, ₹559 cr]`,
`[CAM-2026-03: 5,000 visits, ₹48.2 L recovered]`. A figure without a source
does not go in.

**Tone.** These reports concern named people and businesses and are read in
reviews where performance is assessed. No characterisation of consumers as
types, and no inference about anyone's means or intentions beyond what the
payment record shows.
