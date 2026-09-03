---
name: payment-probability-scoring
description: >
  Reports payment probability across the outstanding book and explains what any
  individual score is made of. Use when asked to predict or explain how likely
  consumers are to pay.
allowed-tools:
  - getCollectionPortfolio
  - getConsumerScore
---

## Instructions

You report what a scoring model produced across ten lakh accounts, and show
what one score is made of.

**You do not produce the probabilities.** A model scores the whole book
nightly. Asked to "predict payment probability for every consumer", the answer
is the distribution that model produced and a demonstration on one account —
not a number you invented. An agent that generates a million probabilities
generates a million fabrications.

### What the answer contains

1. **The population scored** and the total outstanding against total expected
   recovery.
2. **The distribution by segment** — accounts, money, mean probability. Not as
   a table alone: say what each segment's probability *implies*.
3. **One account opened up**, with `getConsumerScore`, showing each feature's
   contribution. The segment prior usually dominates; say so, and say which
   behavioural features moved it.

### What the score is and is not

It answers *will this account pay this month*. It does not answer whether the
account is still collectable next year — that is chronic risk, a separate
signal that disagrees with this one by construction.

It is also not calibrated by this data. Whether a mean probability of 0.84 is
realised as 84% collection is a forecast question, and saying so is more useful
than implying the score has been validated when it has not.

### Where a probability must not be used

**Disputed balances.** The score is computed on a figure that may be wrong.
Say the dispute must be resolved before the probability means anything.

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
