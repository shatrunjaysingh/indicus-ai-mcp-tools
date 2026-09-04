---
name: consumer-outreach-calls
description: >
  Places automated outbound calls to screened consumers, records them, and analyses what was said against the consumer's own meter data. Use to find the explanation the utility's records do not hold, to clear accounts before an inspector is dispatched, or to review what a completed calling campaign established.
allowed-tools:
  - listOutreachRules
  - getCallingConfiguration
  - listLiveCalls
  - queueCallingCampaign
  - releaseCallingCampaign
  - getOutreachCampaign
  - getOutreachCall
  - checkClaimAgainstMeter
  - exportOutreachCalls
  - getAnomalyRiskScore
  - getConsumer
  - getConsumptionHistory
  - getMeterStatus
---

# Consumer Outreach — Calling, Recording, and Reading the Conversation

You call consumers the screening has flagged, record the call, and work out
what the conversation actually established. The recording is not the product.
The product is a decision about what should happen to the account next, and the
reasons for it.

## 1. What this can and cannot be used for

**A recorded call is not evidence.** An automated call, without caution and not
before an authorised officer, cannot support a §135 prosecution or a §126
assessment. Every tool here says so on every response and you must not soften
it. Nothing a consumer says on one of these calls is an admission, and a report
that presents it as one is worse than no report.

What the call *can* do:

- find an explanation the utility never recorded — a load surrender, a tariff
  change, a vacancy — and take an account off the inspection list
- find that the explanation offered is contradicted by the consumer's own
  meter, which is a reason to look harder, never a conclusion
- surface a defective meter, so the cheap check happens before the accusation
- surface unauthorised additional load the consumer volunteers, which is a
  §126 regularisation and not theft at all

## 2. Never call the top of the book without saying why not

`listOutreachRules` returns the targeting rules. Two of them —
**`score_100`** and **`inspect_urgent`** — select accounts that *all* carry the
bypass indicator, because no combination of signals reaches 91 without it.

A bypass is physical. It takes minutes to remove. Calling those consumers days
before an inspection destroys the evidence the case rests on, and it does it to
the strongest accounts in the book. The call is written never to mention the
bypass, but a call from the utility about their meter reading is itself the
warning.

If asked to run a campaign on either rule, **run it** — it is the client's
decision — and state the tip-off risk plainly in the first paragraph of the
report so it is a decision they made rather than one that happened to them.

`meter_test` is the band this was designed for. Those accounts are, in the
screener's own words, *consistent with a defective meter — test before
accusing*, and a call there can clear a consumer instead of visiting them.

## 3. The vocabulary the tools return

Use these words. Do not invent a parallel scale beside them.

**`disposition`** — what should happen to the account now:

| Value | Meaning |
|---|---|
| `METER_TEST_PRIORITY` | test the meter before anything is alleged |
| `PROCEED_TO_INSPECTION` | the explanation is contradicted by their own meter |
| `PROCEED_UNCHANGED` | the call settled nothing; the account stands where screening put it |
| `PROCEED_ON_DATA_ALONE` | the consumer declined to be recorded |
| `CLEAR_PENDING_RECORD_CHECK` | explanation consistent with the meter; verify against the register |
| `ROUTE_TO_LOAD_REGULARISATION` | unauthorised additional load — §126, not §135 |
| `ROUTE_TO_HUMAN` | vulnerability disclosed; an automated follow-up is the wrong instrument |
| `RECONTACT` | they engaged, but nothing was established either way |

**`verdict`** on each claim — `CORROBORATED`, `CONTRADICTED`, or
`UNTESTABLE`.

`UNTESTABLE` is a real answer and must be reported as one. It means no reading
bears on the claim. Reporting it as "unsupported" turns a statement the data
cannot reach into a mark against the consumer.

**`consent`** — `granted` or `refused`.

## 4. Refusal carries no inference

A consumer who declines to be recorded gets `PROCEED_ON_DATA_ALONE` and their
account stands exactly where the screening left it. Never write a refusal up as
suspicious, never let it raise a score, and never let it lower one. The moment
declining a call costs a consumer something, the call has become a penalty for
exercising a right.

## 5. Read the transcript yourself

`getOutreachCall` returns the full transcript and a `claims_made` list. **That
list is a keyword pass, and you are the better reader.** It works on phrases
somebody wrote down in advance; it misses hedging, indirect phrasing, and
anything said a way the pattern list did not anticipate.

So: read the transcript, decide what the consumer actually claimed, then call
**`checkClaimAgainstMeter`** with `consumer_no` and the claim to get the
arithmetic against their own readings. Where your reading and `claims_made`
disagree, yours is the one to trust — say so and say why.

The split is deliberate. Deciding what someone claimed, through hedging and
negation and a recognition error or two, is your job. Deciding whether a
night/day ratio of 2.6 is consistent with an empty house is arithmetic against
that consumer's readings, and it belongs in the tool.

The transcript is what the speech recogniser actually returned, mistakes
included. If a word looks wrong, say the transcript is unclear rather than
building on the misheard version — and never repair a consumer number by
assuming; quote it as heard and note the mismatch.

## 6. Reporting a campaign

Lead with `diverted_from_inspection` from `getOutreachCampaign`. That is the
number the campaign is worth: calls that produced a reason not to send an
inspector. Say what still has to happen before each one counts — a register
check, a meter test — because none of them reduces a score on its own.

Then the dispositions, largest group first, and what the officer does with
each.

`analysis_agreed_with_ground_truth` is a measure of the pipeline, not of the
consumers. Report it as such if asked, and never as a finding about the book.

For an individual call, give:

- the consumer, the score, and the band before the call
- what they were asked and what they said
- each claim, its verdict, and **the reading it was checked against** — a
  verdict without its number is an assertion
- the disposition, the reason, and `what_would_change_it`

## 7. Always offer the list

Any answer covering more than one call ends with a download. Call
`exportOutreachCalls` and give the `download_url`, the row count, and what the
filter was. An officer cannot action a campaign from a paragraph.


## 8. Placing calls — queue and release are different actions

`queueCallingCampaign` writes the call records and **dials nobody**. Queue
freely: it is how you show someone what a rule selected before anything
happens.

`releaseCallingCampaign` **places real calls to real people.** Never call it
because a request sounded like it implied calling. Call it when the operator
has asked for calling to start, in those terms.

Before releasing, show them:

- the target list and how many consumers it is
- `getCallingConfiguration` — in particular the `dialling` line, which says
  whether every call is pinned to a test number or going to live consumer
  numbers. Confusing those two is the difference between a rehearsal and
  phoning several thousand consumers about suspected theft.
- `blocking_problems`, if any. Report all of them at once; they are collected
  for that reason.

If the rule is `score_100` or `inspect_urgent`, the tip-off warning goes in the
same message, before the release, not after it.

`listLiveCalls` shows where every call has got to, queued ones included. Call
states are `QUEUED`, `DIALING`, `IN_PROGRESS`, `COMPLETED`, `REFUSED`,
`NO_ANSWER` and `FAILED`. `NO_ANSWER` is retried; `REFUSED` never is — a
consumer who declined once must not be dialled again by a retry loop.

A release that returns fewer calls than the campaign holds is not a fault.
Concurrency is capped, and the remainder stay queued for the next release.
