---
name: collection-campaign-optimisation
description: >
  Plans and optimises a collection campaign against a finite channel capacity,
  using what previous campaigns returned. Use for campaign planning, targeting,
  and choosing between channels.
allowed-tools:
  - getCampaignHistory
  - buildCampaignList
  - getCollectionPortfolio
  - getRecoveryChannels
  - listCollectionTargets
  - exportDefaulterList
---

## Instructions

You decide where a finite amount of collection effort goes.

### Read what has already been tried, first

`getCampaignHistory` before anything else. Repeating an approach that returned
poorly, without saying why this time differs, is the most common failure in
collection planning — and the record of it is usually in a spreadsheet nobody
consults before the next campaign.

A field campaign targeted on largest balance returned **3.7×** cost. A call
campaign targeted on the deteriorating segment returned **121.8×**. Any
recommendation that does not engage with those two numbers has skipped the
evidence it was handed.

### Capacity is the constraint

Check `getRecoveryChannels`. A plan needing more field visits than exist in a
month is not a plan.

Every campaign is therefore a choice against an alternative. **Name it** —
*"6,000 visits to X rather than Y, because…"*. A plan reading as though
capacity were unlimited has not made the decision it was asked to make.

### Exclude before you rank

Three groups come out before ranking, each named with its count:

- **Disputed balances** — the amount may be wrong; recovery action generates
  complaints and regulatory exposure.
- **Vacated premises** — no occupier to collect from.
- **Anything where the statutory route is unavailable** — no notice served, the
  period unexpired, an instalment arrangement being honoured.

Excluding a segment is a recommendation, not an omission. Say what you excluded
and why, or the reader assumes you missed it.

### The deliverable is a list

`buildCampaignList` produces it, sized to the channel's real capacity. Open
with the headline in this shape:

> From 10,00,000 outstanding consumers, 6,000 accounts selected for field
> intervention — ₹156 cr expected recovery against ₹15.6 L of visits.

Population, then the number selected, then what it is worth. Then
`exportDefaulterList` for the file the team works from. **Never put the rows
in your reply** — fifty thousand accounts is about two million tokens and does
not fit.

### Check the mix you were handed

A mechanical top-N ranks on expected recovery and will be dominated by accounts
that would have paid anyway. If the selection is mostly reliable-slow, a notice
or SMS reaches them at a fraction of the cost with equal or better response,
and the scarce channel should be re-pointed at the segment where it changes the
outcome. Say so when you see it.

### Then say what would break the plan

The one assumption most likely to be wrong, and what would confirm it. A return
figure computed on the extreme top of a book will not hold as the campaign
scales down the ranking.
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
