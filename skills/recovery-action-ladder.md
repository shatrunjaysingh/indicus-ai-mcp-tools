---
name: recovery-action-ladder
description: >
  Recommend the least-cost, proportionate, and policy-compliant recovery action for outstanding consumer accounts by combining payment likelihood, expected recovery, historical channel response, intervention cost, prior contact outcomes, arrears validity, and governed disconnection prerequisites. modes: * portfolio * consumer * action_recommendation * campaign_optimization * channel_effectiveness * disconnection_review * capacity_planning * model_monitoring * export
allowed-tools:
  - buildCampaignList
  - getBillingHistory
  - getCollectionPortfolio
  - getConsumer
  - getConsumptionHistory
  - getDisconnectionRecord
  - getNoticeHistory
  - getPaymentHistory
  - getRecoveryChannels
---

# AI Collection Action Recommendation

## Purpose

Choose the **best next recovery action** for an outstanding account:

`SMS → CALL → FIELD_VISIT → NOTICE → DISCONNECT`

The objective is not to maximize response rate.

The objective is to select the action that provides the best **incremental recovery outcome for the account**, subject to:

* payment likelihood,
* expected recoverable amount,
* historical response to each channel,
* incremental response from escalation,
* intervention cost,
* prior actions already attempted,
* arrears validity,
* customer/account status,
* statutory and utility policy constraints,
* channel capacity,
* proportionality,
* and disconnection-specific prerequisites.

The skill recommends an action.

It does **not** execute disconnection, change the ledger, issue a statutory notice, or make a legal finding.

---

# Core Decision Principle

## Choose the next action, not the strongest action

A higher recovery rate does not automatically make an action better.

For example:

* SMS may cost ₹0.35.
* A field visit may cost ₹260.
* Disconnection may produce a very high payment response.

A channel that produces slightly lower recovery but costs dramatically less can be the better intervention.

More importantly, an action can be **effective but disproportionate**.

A consumer who reliably pays after a reminder should not be escalated to a field visit merely because a field visit has a higher historical response rate.

The decision should therefore consider:

> **incremental expected recovery − intervention cost − escalation burden**

subject to policy and legal gates.

Do not reduce this to a single formula unless an approved decision model exists.

---

# Modes

## One consumer

When a consumer/account identifier is supplied:

1. Retrieve the current collection state.
2. Retrieve payment history.
3. Retrieve prior collection actions.
4. Retrieve notice history.
5. Retrieve outstanding and recoverable amounts.
6. Retrieve payment probability from the approved payment-scoring model.
7. Retrieve channel-specific response estimates where available.
8. Check all action prerequisites and exclusions.
9. Recommend exactly one next action.
10. Explain why that action is preferred over the next escalation.

Use the account-level tools, such as:

* `getConsumerScore`
* `getPaymentHistory`
* `getNoticeHistory`
* `getCollectionHistory`
* account/ledger validation tools

Use the exact tool names available in the connected utility system.

---

## Portfolio

When the request is for:

* collection action recommendations,
* campaign optimization,
* channel allocation,
* field campaign,
* disconnection review,
* recovery planning,
* or export,

start with:

`getCollectionPortfolio`

Then use the appropriate action-planning tool, such as:

`buildCampaignList`

or the utility's equivalent governed campaign-planning function.

For large lists:

`exportCollectionActionList`

Never paste an operational campaign containing hundreds or thousands of consumer rows into the conversational response.

---

# Required Distinctions

The agent must keep these concepts separate.

### Payment probability

> Will this account pay in the current collection horizon?

Provided by the approved payment-probability model.

### Expected recovery

> How much recoverable money is likely to be collected?

Typically related to:

`recoverable outstanding × payment probability`

but use the approved utility calculation rather than independently recomputing the model.

### Channel response

> How has this account or comparable approved segment historically responded to a specific intervention?

This is not the same as payment probability.

### Incremental channel effect

> How much additional recovery is expected from using this channel instead of the next-best lower-cost action?

This is the most important quantity for action selection when an approved uplift model exists.

### Chronic-default risk

> Is the account approaching persistent/chronic default?

This comes from the separate chronic-default early-warning skill.

Do not recreate it here.

### Recovery action

> What should the utility do next?

This skill answers that question.

---

# Action Ladder

The normal ladder is:

1. `REMIND`
2. `CALL`
3. `FIELD_VISIT`
4. `NOTICE`
5. `DISCONNECT`
6. `HOLD`

The user-facing description may call the first action SMS.

Internally use the utility's approved action codes consistently.

---

# Action Semantics

## REMIND

Use for low-cost, low-intrusion intervention where there is evidence that a reminder can reasonably trigger payment.

Typical evidence:

* good recent payment history,
* high payment likelihood,
* prior successful response to SMS,
* recent missed/late payment without deterioration,
* small or moderate recoverable balance,
* no need for human clarification.

Do not escalate simply because the balance is large.

---

## CALL

Use where human contact is likely to add information or increase recovery beyond a reminder.

Examples:

* repeated late payment,
* payment arrangement may be appropriate,
* reminder has already failed,
* account requires clarification,
* payment intention is uncertain,
* prior calls produced useful commitments.

The recommendation should state what the caller should accomplish.

Examples:

* confirm payment date,
* establish an approved payment arrangement,
* resolve a billing question,
* explain the outstanding amount,
* identify why a previously successful payment pattern changed.

---

## FIELD_VISIT

Use when physical verification or in-person engagement provides meaningful incremental value.

Examples:

* repeated unsuccessful remote contact,
* material recoverable balance,
* strong evidence that the premises/contact route remains actionable,
* prior channel response suggests field intervention is effective,
* account requires physical verification,
* collection risk justifies the visit cost.

Do not recommend a field visit merely because the account owes a large amount.

A high balance increases financial exposure; it does not establish that a visit will work.

---

## NOTICE

Use when the statutory/policy process requires formal notice before a later action or when the approved recovery workflow calls for notice at this stage.

The agent must verify:

* applicable notice requirement,
* correct account and consumer,
* amount being pursued,
* validity of the arrears,
* applicable billing basis,
* service of notice where required,
* notice period,
* applicable exceptions or protections.

Do not treat `NOTICE` as simply a more aggressive version of a call.

It is a governed procedural step.

---

## DISCONNECT

Disconnection is a **gate**, not a ranked channel.

Never select `DISCONNECT` merely because:

* it has the highest historical response,
* the account has the largest balance,
* the consumer has ignored SMS,
* the consumer has ignored calls,
* or the expected recovery is high.

All applicable utility policy and statutory prerequisites must be satisfied.

At minimum, the recommendation must verify the configured requirements for:

* valid and undisputed recoverable arrears,
* actual-read billing where required,
* statutory notice served,
* notice period expired,
* no honoured instalment/payment arrangement,
* no applicable hold or protected status,
* recoverability within the applicable limitation rules,
* no unresolved ledger/payment posting issue,
* and any utility-specific approval requirement.

If any prerequisite fails:

`DISCONNECT` is unavailable.

Recommend the action that resolves the blocking condition.

---

# Disconnection Gate

Use:

`buildCampaignList(channel=disconnection)`

or the equivalent governed utility function.

The tool must return:

* eligible for disconnection,
* blocked by notice,
* blocked by notice period,
* blocked by disputed amount,
* blocked by estimated/non-compliant billing basis,
* blocked by payment arrangement,
* blocked by limitation/recoverability,
* blocked by account/ledger issue,
* blocked by protected/hold status,
* blocked for other policy reasons.

Report these counts in portfolio analysis.

Do not silently remove blocked accounts.

A blocked account is not necessarily unrecoverable.

Example:

> 4,210 accounts are otherwise candidates for escalation; 1,137 are blocked because statutory notice has not been served. Their next action is notice, not disconnection.

---

# Legal and Policy Controls

The skill must use the utility's configured legal-policy rules rather than inventing thresholds.

For Indian utilities, limitation and disconnection requirements may depend on the applicable statutory provision, regulations, tariff/order, and utility procedure.

Do not present a legal conclusion unless the governing rule is available in the system.

Where the system is configured to apply a specific rule, cite the rule/version used.

For example, if the utility has configured the Electricity Act, 2003 limitation treatment under Section 56(2), report the configured rule and its applicability rather than silently applying a generic two-year rule.

Never state:

> "The consumer can legally be disconnected."

Prefer:

> "DISCONNECT is eligible under the configured policy gate: [policy/version], subject to required human authorization."

---

# Payment History

## Read behavior over balance

Evaluate:

* on-time payment cycles,
* late payment cycles,
* unpaid cycles,
* days-to-payment,
* partial payments,
* payment arrangement adherence,
* recent deterioration,
* previous recovery after intervention,
* payment before previous disconnection/notice,
* and consistency over time.

A consumer who consistently pays shortly after a reminder is not necessarily a candidate for stronger escalation.

---

# Deterioration Matters

A change in behavior can be more important than the absolute debt.

Example:

> The account paid on time in 11 of the previous 12 cycles but has missed the last two.

This may justify a call even if the outstanding amount is modest.

Conversely:

> The account routinely pays late but has remained stable for 18 cycles.

Do not automatically classify it as deteriorating.

Use the observed payment trajectory.

---

# Prior Action History

Retrieve prior actions using:

`getNoticeHistory`

and the utility's collection-contact history.

Determine:

* what action was attempted,
* when it was attempted,
* whether it reached the consumer,
* whether payment followed,
* how much was recovered,
* whether the same action has failed repeatedly,
* whether the failure was caused by the channel or by an unrelated ledger/account issue.

Do not interpret an unsuccessful SMS as evidence that the consumer will not respond to a call.

Do not interpret an unsuccessful field visit as evidence that escalation is futile without examining why the visit failed.

---

# Do Not Repeat Failed Interventions Blindly

If an action has already failed twice without meaningful response, do not recommend the same rung again unless there is a documented reason to retry.

Examples of legitimate reasons:

* contact information changed,
* new billing event occurred,
* prior message failed delivery,
* the consumer requested another contact,
* a payment arrangement expired,
* a material account correction changed the amount due.

The agent should explain the reason for any repeat action.

---

# Ledger Reconciliation

Before recommending recovery action:

1. Confirm the outstanding amount.
2. Confirm the recoverable amount.
3. Reconcile recent receipts.
4. Check unapplied payments.
5. Check reversals.
6. Check credit adjustments.
7. Check disputes.
8. Check billing corrections.
9. Check payment arrangements.
10. Check account closure/transfer status.

If a payment has been received but not posted correctly:

`RECOVERY_ACTION: HOLD`

Do not pursue recovery until the ledger is corrected or the discrepancy is resolved.

---

# Outstanding vs Recoverable

Never rank action solely on ledger outstanding.

Use:

> **recoverable amount**

where the utility has a validated recoverability calculation.

Separate:

* total ledger outstanding,
* recoverable outstanding,
* disputed amount,
* barred/unrecoverable amount,
* amount under arrangement,
* amount subject to correction.

An account with ₹10 lakh ledger outstanding may have only ₹2 lakh recoverable.

The action decision should not treat the full ₹10 lakh as collectible exposure.

---

# Channel Economics

Channel choice must consider intervention cost.

Example:

| Action      |        Example utility cost | Typical role                     |
| ----------- | --------------------------: | -------------------------------- |
| SMS         |                       ₹0.35 | Low-cost reminder                |
| Call        |             configured cost | Human clarification/escalation   |
| Field visit |                        ₹260 | Physical engagement/verification |
| Notice      |             configured cost | Formal process                   |
| Disconnect  | configured operational cost | Last-resort governed action      |

These are illustrative values only.

Every figure must come from the utility's current cost configuration or cited campaign record.

Do not hard-code costs if a current cost table exists.

---

# Response Rate Is Not Enough

Suppose historical response is:

| Segment       |  SMS | Call | Field | Disconnect |
| ------------- | ---: | ---: | ----: | ---------: |
| Reliable-slow | 0.81 | 0.86 |  0.90 |       0.94 |

It would be incorrect to conclude that every reliable-slow account should be disconnected.

The relevant question is:

> How much additional recovery does escalation produce relative to the lower-cost action?

If SMS already produces most of the achievable recovery, escalation may destroy proportionality without materially improving net recovery.

---

# Incremental Recovery

Where an approved channel-uplift model exists, prefer:

`incremental expected recovery`

over raw channel response.

Conceptually:

`Expected incremental recovery = recoverable amount × incremental response probability`

Then account for intervention cost and applicable constraints.

Do not calculate this independently if the utility already provides an approved model.

If no uplift model exists, explicitly state that historical response is being used as a proxy and that causal incremental impact is not established.

---

# Consumer Impact

The utility cost is not the only cost.

Escalation can impose consequences on the consumer:

* inconvenience,
* loss of electricity supply,
* additional travel/engagement burden,
* formal collection consequences,
* potential impact on essential electricity use.

The agent must therefore prefer the **least intrusive action that has a credible probability of achieving the recovery objective**, subject to policy.

Never optimize collection by maximizing pressure.

---

# Special Conditions

Check for:

* active payment arrangement,
* recent payment,
* dispute,
* billing correction,
* estimated readings,
* meter replacement,
* meter fault investigation,
* temporary disconnection,
* permanent disconnection,
* account transfer,
* closure,
* legal hold,
* court/regulatory matter,
* approved exemption,
* registered critical-use/medical protection where the utility policy recognizes it,
* vulnerable-customer protections where legally and operationally applicable.

Do not infer vulnerability from:

* locality,
* tariff category,
* surname,
* occupation,
* spending,
* property,
* neighborhood,
* language,
* caste,
* religion,
* gender,
* or other protected/proxy attributes.

Use only explicitly recorded operational eligibility where permitted.

---

# Interaction With Other Revenue Skills

This skill should consume outputs from the other revenue models rather than recreate them.

## Payment Probability

Use:

`getConsumerScore`

for the approved current-payment model.

Question:

> Will the consumer pay in the current horizon?

## Chronic Default Early Warning

Use:

`getChronicRisk`

or equivalent.

Question:

> Is the account approaching persistent/chronic default?

## Collection Action Optimization

This skill asks:

> Given what we know, what should the utility do next?

The models therefore form a chain:

```text
PAYMENT PROBABILITY
        +
CHRONIC DEFAULT RISK
        +
RECOVERABLE AMOUNT
        +
CHANNEL RESPONSE / UPLIFT
        +
ACTION COST
        +
POLICY GATES
        ↓
COLLECTION ACTION
        ↓
PAYMENT / NO PAYMENT
        ↓
OUTCOME FEEDBACK
```

Do not merge these scores into an unexplained composite score.

---

# One Account Output Contract

For one account, begin with exactly:

```text
PAYMENT_LIKELIHOOD: high | medium | low
RECOVERY_ACTION: REMIND | CALL | FIELD_VISIT | NOTICE | DISCONNECT | HOLD
CONFIDENCE: high | medium | low
```

Then provide:

## Current position

State:

* recoverable outstanding,
* payment likelihood,
* current delinquency,
* recent payment trajectory,
* current collection stage.

## Why this action

Give the specific evidence supporting the selected action.

Include:

* payment cycles,
* recent deterioration,
* historical response to prior actions,
* expected incremental value where available,
* action cost where material,
* relevant policy status.

## What points the other way

This section is mandatory.

Never leave it empty.

Examples:

* high balance argues for escalation, but SMS response has historically been strong;
* two failed reminders argue for a call, but a recent payment is still pending posting;
* field visit has historically worked, but the account is currently under an honoured arrangement;
* disconnection appears effective, but the statutory notice prerequisite is incomplete.

## Expected outcome

State the expected operational result if an approved model provides it.

Do not fabricate a probability.

Where no approved outcome model exists:

> Expected outcome is qualitative; no validated channel-uplift estimate is available.

## Next rung if it fails

Specify the next governed action.

Example:

`REMIND → CALL`

or:

`CALL → FIELD_VISIT`

For `DISCONNECT`, do not propose another escalation unless the policy workflow specifies one.

## What is not established

Explicitly state what the evidence does not prove.

Examples:

* non-payment does not establish unwillingness to pay;
* a high balance does not establish ability to pay;
* a failed SMS does not establish that the consumer received or read it;
* a predicted response does not guarantee payment;
* a collection score does not establish fraud;
* eligibility for disconnection does not itself authorize execution.

---

# Portfolio Output

For portfolio requests report:

### Population

* accounts evaluated,
* total outstanding,
* total recoverable amount,
* scoring date,
* payment-model version,
* channel-response model/version,
* policy version.

### Recommended actions

Show counts and recoverable amount by:

* REMIND,
* CALL,
* FIELD_VISIT,
* NOTICE,
* DISCONNECT,
* HOLD.

Example:

| Recommended action | Accounts | Recoverable amount | Primary reason               |
| ------------------ | -------: | -----------------: | ---------------------------- |
| REMIND             |  sourced |            sourced | strong low-cost response     |
| CALL               |  sourced |            sourced | remote reminder insufficient |
| FIELD_VISIT        |  sourced |            sourced | incremental field value      |
| NOTICE             |  sourced |            sourced | formal process required      |
| DISCONNECT         |  sourced |            sourced | all policy gates satisfied   |
| HOLD               |  sourced |            sourced | ledger/policy issue          |

Every figure must have a source.

---

# Capacity-Constrained Campaigns

If the utility can make only:

* 10,000 calls,
* 2,500 field visits,
* 5,000 notices,

do not simply select accounts with the largest balances.

Optimize the available capacity against expected incremental recovery and governed eligibility.

For example:

> 18,400 accounts are eligible for field intervention, but only 2,500 visits are available. The field list should prioritize the accounts with the greatest expected incremental recoverable amount per visit, subject to policy and geographic/route constraints.

If the utility has a route optimizer, use it after the recovery candidates are selected.

Do not let geographic convenience become the primary collection criterion.

---

# Field Visit Economics

Where field capacity is constrained, consider:

`expected incremental recovery / visit cost`

and, where available:

`expected incremental recovery / field-hour`

Use operational route constraints only after customer-impact and recovery priorities have been established.

Do not optimize field teams purely on number of visits.

A 100-visit target can produce worse recovery than 60 carefully selected visits.

---

# Disconnection Portfolio

For disconnection analysis, report at least:

1. total accounts reviewed,
2. accounts otherwise eligible,
3. accounts blocked,
4. block reason,
5. recoverable amount,
6. required next action.

Example:

> 22,800 accounts were reviewed. 4,920 satisfy the configured disconnection gate. 17,880 are blocked. The largest blocking condition is missing/expired notice status, affecting 6,140 accounts; those accounts should enter the notice workflow rather than the disconnection queue.

Do not describe blocked accounts as "not recoverable" unless that is independently established.

---

# Action Quality Monitoring

Measure the recommendation system using outcomes, not recommendation volume.

Track:

* payment rate after recommendation,
* recovery amount,
* incremental recovery,
* recovery per intervention,
* recovery per rupee of intervention cost,
* recovery per field visit,
* time-to-payment,
* repeat intervention rate,
* escalation rate,
* false escalation rate,
* unnecessary field visits,
* unnecessary disconnections prevented,
* accounts placed on HOLD because of ledger errors,
* campaign capacity utilization,
* policy-gate failure rate.

For each channel compare:

`recommended channel` vs `actual outcome`

and, where possible:

`recommended channel` vs approved control/baseline.

---

# Model Monitoring

Monitor:

* payment-score calibration,
* channel-response drift,
* channel-uplift drift,
* segment response changes,
* intervention-cost changes,
* policy-rule changes,
* customer communication delivery rates,
* field completion rates,
* seasonal effects,
* campaign saturation,
* and population stability.

A historical response rate is not permanently valid.

If SMS response falls from 0.81 to 0.62, the action optimizer must not continue using 0.81 merely because it was historically observed.

---

# Feedback Loop

Every completed action should generate an outcome record:

```text
ACCOUNT
→ RECOMMENDED ACTION
→ ACTION EXECUTED
→ ACTION DELIVERED / COMPLETED
→ CONSUMER RESPONSE
→ PAYMENT
→ AMOUNT RECOVERED
→ TIME TO PAYMENT
→ NEXT ACTION
```

Distinguish:

* recommendation,
* execution,
* delivery,
* response,
* payment.

An SMS recommendation is not an SMS delivery.

A field-visit assignment is not a completed visit.

A completed visit is not a successful collection.

---

# Confidence

Confidence should reflect evidence quality, not action aggressiveness.

### High

Use when:

* payment score is reliable and current,
* channel-response evidence is strong,
* prior actions are known,
* recoverable amount is validated,
* account status is current,
* policy prerequisites are clear,
* and the recommended action has strong historical/approved support.

### Medium

Use when:

* some inputs are stale,
* channel-response evidence is limited,
* or the action depends on moderate uncertainty.

### Low

Use when:

* ledger status is uncertain,
* payment history is incomplete,
* model coverage is poor,
* channel history is sparse,
* account status is ambiguous,
* or policy prerequisites cannot be verified.

When confidence is low because of an unresolved ledger issue, prefer:

`HOLD`

rather than an aggressive action.

---

# Action Selection Guardrails

Never recommend:

* DISCONNECT solely because balance is high,
* FIELD_VISIT solely because balance is high,
* NOTICE solely because payment probability is low,
* repeated SMS after documented repeated failure without justification,
* recovery action against a receipted but unapplied payment,
* action based on locality or protected characteristics,
* action based on inferred income or ability to pay,
* action based on predicted intent,
* action that violates a configured legal/policy gate.

Never state that a consumer is:

* unwilling to pay,
* deliberately avoiding payment,
* financially incapable,
* fraudulent,
* dishonest,

unless the statement is independently established and legally appropriate.

Payment behavior is evidence of payment behavior.

It is not evidence of character or motive.

---

# Human Approval

Human approval is required before customer-impacting actions where utility policy requires it, particularly:

* statutory notices,
* disconnection,
* exceptions,
* disputed accounts,
* protected accounts,
* unusual/high-value cases,
* and cases with conflicting records.

The AI recommendation must remain auditable.

Store:

* input snapshot,
* model versions,
* feature values used,
* recommendation,
* policy gates,
* blocking conditions,
* timestamp,
* confidence,
* human decision,
* executed action,
* and eventual outcome.

---

# Auditability

For every recommendation, preserve enough information to answer:

1. What did the system know?
2. What did the payment model predict?
3. What channel evidence was available?
4. What actions had already been attempted?
5. What amount was considered recoverable?
6. Which policy gates were evaluated?
7. Why was this action selected?
8. Why was a stronger action rejected?
9. Who approved the action where required?
10. What happened afterward?

Do not overwrite historical recommendations when models or policies change.

---

# Source Discipline

Every numeric claim must have a source.

Preferred evidence format:

```text
[collection_portfolio: 10,000 accounts, ₹42.1 cr recoverable]
[channel_response: SMS 0.81, call 0.86, field 0.90]
[CAM-2026-03: 5,000 field visits, ₹48.2 L recovered]
[payment_model:v4.2: account score 0.72]
[policy:DISCOM-COL-2026-04]
```

Do not invent:

* response rates,
* intervention costs,
* recovery amounts,
* campaign sizes,
* statutory thresholds,
* notice periods,
* or disconnection eligibility.

If the system does not provide the number, say that it is unavailable.

---

# Required Portfolio Decision Framework

For each recommended action, answer:

### 1. Can the account pay?

Use the approved payment-probability model.

### 2. How much is actually recoverable?

Use validated recoverable amount, not raw ledger outstanding.

### 3. What has already been tried?

Review prior collection actions.

### 4. What channel is likely to add value?

Use approved channel-response or uplift evidence.

### 5. What does the action cost?

Use current configured intervention cost.

### 6. Is the action proportionate?

Prefer the least intrusive action with credible recovery value.

### 7. Is the action legally/policy eligible?

Especially for NOTICE and DISCONNECT.

### 8. Is there capacity?

Apply campaign and field constraints.

### 9. What happens if it fails?

Specify the next governed rung.

---

# Quality Gate

Before returning a recommendation, verify:

* [ ] Payment likelihood comes from the approved model.
* [ ] Chronic-default risk is not substituted for payment likelihood.
* [ ] Recoverable amount is distinguished from ledger outstanding.
* [ ] Payment history was checked.
* [ ] Prior collection actions were checked.
* [ ] Channel response evidence was checked.
* [ ] Incremental effect is used where an approved model exists.
* [ ] Intervention cost is considered.
* [ ] Stronger escalation is not selected merely because it has higher response.
* [ ] DISCONNECT prerequisites are explicitly checked.
* [ ] Blocked disconnection cases are assigned their next appropriate action.
* [ ] Ledger/payment discrepancies produce HOLD.
* [ ] Customer-impacting actions follow human approval requirements.
* [ ] Protected attributes and proxies are not used.
* [ ] Every numeric figure has a source.
* [ ] Confidence reflects evidence quality.
* [ ] The recommendation is auditable.
* [ ] No unsupported inference about consumer intent or ability to pay is made.

---

# Architecture

```text
CONSUMER DATA
     │
     ├── PAYMENT HISTORY
     ├── LEDGER / RECOVERABLE AMOUNT
     ├── PRIOR COLLECTION ACTIONS
     ├── ACCOUNT STATUS
     └── POLICY / ELIGIBILITY
            │
            ▼
   PAYMENT PROBABILITY MODEL
            │
            ├──────────────┐
            ▼              ▼
 CHRONIC DEFAULT RISK   CHANNEL RESPONSE /
                        UPLIFT MODEL
            │              │
            └──────┬───────┘
                   ▼
        COLLECTION ACTION OPTIMIZER
                   │
          ┌────────┼─────────┐
          ▼        ▼         ▼
       COST     CAPACITY   POLICY GATES
          │        │         │
          └────────┼─────────┘
                   ▼
          RECOMMENDED ACTION
                   │
       ┌───────────┼────────────┐
       ▼           ▼            ▼
      SMS         CALL       FIELD VISIT
                                │
                                ▼
                              NOTICE
                                │
                          DISCONNECT GATE
                                │
                                ▼
                          HUMAN APPROVAL
                                │
                                ▼
                         ACTUAL OUTCOME
                                │
                                ▼
                         MODEL FEEDBACK
```

The architectural boundary is important:

> **Payment model predicts likelihood. Chronic-risk model predicts trajectory. Action optimizer chooses the next intervention.**

Do not make one model silently perform all three jobs.

---

# Final Principle

The best collection action is **not the strongest action and not the action with the highest response rate**.

It is the **least intrusive, policy-compliant action with the strongest evidence of incremental recovery relative to its cost and alternatives**.

The operating sequence is:

> **PAYMENT LIKELIHOOD → RECOVERABLE EXPOSURE → INCREMENTAL CHANNEL VALUE → COST → POLICY GATE → CAPACITY → ACTION → OUTCOME**

And for disconnection specifically:

> **DISCONNECT IS A GATE, NOT A RANK.**