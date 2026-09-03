---
name: payment-behaviour-segmentation
description: >
  Describes the outstanding book's behavioural segments and what each implies
  for treatment. Use when asked to segment consumers, or to explain what a
  segment means.
allowed-tools:
  - getCollectionPortfolio
  - listCollectionTargets
  - getConsumerScore
---

## Instructions

You describe how the book divides by payment behaviour, and what follows from
each division.

### A table is not an answer

Every segment gets its definition, its size, its money, its mean probability —
**and what it implies for treatment**. Without the last, this is a report the
client could produce themselves.

- **Reliable but slow** — pays every cycle, always late. Managing cash, not
  avoiding payment. A reminder. The most over-served segment in most DISCOMs.
- **Recently deteriorated** — long clean record, then two to four missed
  cycles. A change of circumstances. Where intervention still changes the
  outcome.
- **Chronic defaulter** — six or more unpaid, notices ignored, promises broken.
  Enforcement only where the amount justifies the cost.
- **Disputed** — resolve the dispute before any recovery action. The balance
  may be wrong, and pursuing it generates complaints and regulatory exposure.
- **Premises vacated** — nobody to collect from. The largest single waste in
  most collection programmes, precisely because these carry real balances and
  look like targets.
- **New connection, early arrears** — often a billing setup problem rather than
  a payment problem. Check the tariff and meter before treating as recovery.

### The number that makes the point

**The segment holding the most money returns the least of it.** Chronic
defaulters hold the largest balance in the book and yield a fraction of it,
while reliable-but-slow holds less and yields nearly all of it. Give both
columns side by side; that contrast is the argument for segmenting at all.

### Segments are behaviour, not people

A segment describes what an account has done, not what kind of person holds it.
Do not describe segments in terms of consumer character, means or intent.
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
