---
name: early-warning-defaulters
description: >
  Identifies consumers heading for chronic default while they can still be
  caught, ranked on chronic risk, and sizes the intervention. Use when asked
  about high-risk defaulters, deterioration, or preventing chronic default.
allowed-tools:
  - listEarlyWarning
  - buildCampaignList
  - getConsumerScore
  - getCollectionPortfolio
---

## Instructions

You find the accounts about to tip into chronic default, before they do.

### Rank on chronic risk, not payment probability

These answer different questions and **disagree by construction**. Payment
probability is about collecting this month; chronic risk is about whether the
account is collectable next year. The top of the early-warning list sits around
0.46 on payment probability and 0.97 on chronic risk.

Sorting this list by payment probability surfaces the accounts that are already
safe. It is the single most likely error here.

### Identification without a list is not an answer

A collection manager cannot act on *"55,525 accounts are at risk"*.

Give the population and what it holds, **then the ranked accounts by name**
with their risk, balance and what drives each, **then the intervention sized to
a channel capacity** — `buildCampaignList(min_chronic_risk=…)` turns the same
population into a costed campaign.

For a list longer than a chat can carry, use `exportDefaulterList` and give
the link. Never put thousands of rows in a reply.

### Say why they are catchable

Accounts already chronic score zero — the question is who can **still** be
caught. Four cycles down and accelerating is closer to tipping than eight
cycles down and stabilised, and the first is the one where intervention changes
the outcome.

Note the balances. The accounts closest to tipping hold hundreds to a few
thousand rupees, not lakhs. That is the honest shape of this problem and it is
the opposite of what a balance-ranked list shows.

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
