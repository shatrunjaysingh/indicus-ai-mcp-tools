---
name: collection-campaign-optimisation
description: >
  Plans and optimises a collection campaign against a finite channel capacity, using what previous campaigns returned. Use for campaign planning, targeting, and choosing between channels.
allowed-tools:
  - buildCampaignList
  - exportDefaulterList
  - getCampaignHistory
  - getCollectionPortfolio
  - getRecoveryChannels
  - listCollectionTargets
---

# Skill: Optimize Collection Campaigns

## Purpose

Allocate finite collection capacity to the accounts and channels where intervention is most likely to produce **incremental recoverable cash**, at acceptable cost and within policy.

The skill answers:

> **Who should we act on, through which channel, and why now?**

It does not simply identify the accounts with the largest balances or the lowest payment probabilities.

The objective is:

**incremental expected recovery ÷ intervention cost**, subject to capacity, eligibility, policy, service-level, and consumer-impact constraints.

---

# Core Decision

A collection campaign is a constrained optimization problem.

For each eligible account and available channel, estimate:

* recoverable outstanding amount
* probability of payment without intervention
* probability of payment with the proposed intervention
* incremental response attributable to the intervention
* expected timing of recovery
* intervention cost
* prior intervention history
* channel effectiveness for comparable accounts
* operational capacity
* statutory and policy eligibility
* consumer-impact constraints

Where an approved uplift / treatment-effect model exists:

> **Incremental Expected Recovery = Recoverable Amount × Incremental Response Probability**

Then:

> **Campaign Value = Incremental Expected Recovery − Intervention Cost**

And, where appropriate:

> **Efficiency = Incremental Expected Recovery ÷ Intervention Cost**

Do not substitute raw payment probability for incremental response.

An account with a 90% probability of paying without intervention may be a poor field-visit target even if its balance is large.

An account with a 45% baseline payment probability but a strong estimated response to a call may be a much better use of scarce call capacity.

---

# 1. Start With Campaign History

Call:

`getCampaignHistory`

**before designing the next campaign.**

Review:

* previous campaign objective
* target population
* selection rule
* channel
* capacity deployed
* accounts contacted
* recoverable amount targeted
* actual recovery
* recovery timing
* intervention cost
* cost per recovery
* response rate
* incremental recovery where measured
* segment/channel performance
* exclusions
* operational failure rates
* complaints or adverse outcomes
* reasons for non-recovery

Do not treat campaign history as a leaderboard alone.

Ask:

1. What worked?
2. For whom?
3. Through which channel?
4. At what scale?
5. Compared with what alternative?
6. Did the intervention actually cause additional recovery, or did the account pay anyway?

### Do not hard-code historical examples

If campaign history contains results such as:

* field campaign: 3.7× return
* call campaign: 121.8× return

use those figures only when the current campaign history actually contains them.

Do not present historical performance as a guaranteed future return.

---

# 2. Read Current Capacity

Call:

`getRecoveryChannels`

before selecting accounts.

Capture, for each channel:

* available capacity
* time period
* unit cost
* operating hours
* geography / operational constraints
* staffing
* SLA
* maximum campaign volume
* escalation requirements
* prerequisites

Typical channels may include:

* `SMS`
* `IVR`
* `CALL`
* `FIELD_VISIT`
* `NOTICE`
* `DISCONNECT`

Capacity is a hard constraint.

A plan requiring 8,000 field visits when only 5,000 are available is not an optimized campaign.

---

# 3. Establish the Campaign Objective

Before ranking accounts, establish what is being optimized.

Possible objectives include:

### Maximum incremental recovery

Maximize cash recovered during the campaign horizon.

### Maximum recovery per unit cost

Maximize:

`incremental expected recovery / intervention cost`

### Maximum recovery under fixed capacity

Example:

> 5,000 field visits available; allocate them to maximize incremental recoverable cash.

### Target achievement

Determine the lowest-cost campaign mix capable of closing an approved collection gap.

### Multi-channel optimization

Allocate capacity across SMS, calls, field visits and other approved channels rather than optimizing each channel independently.

Never assume the objective.

If the request is ambiguous, state the optimization objective being used.

---

# 4. Define the Eligible Population

Before ranking, establish:

* as-of date
* campaign horizon
* account population
* recoverable exposure
* minimum history requirement
* payment-data freshness
* channel availability
* policy eligibility
* statutory eligibility
* existing treatment status

Distinguish:

**Outstanding balance**

from:

**Recoverable amount**

and from:

**Expected incremental recovery.**

A large ledger balance is not automatically a large collection opportunity.

---

# 5. Apply Hard Exclusions Before Ranking

Do not rank accounts that cannot appropriately receive the proposed intervention.

At minimum evaluate:

### Disputed balance

If the balance is under an active, unresolved billing or ledger dispute:

**HOLD**

Do not optimize recovery against a balance whose validity is unresolved.

### Premises vacated

Where reliable operational evidence establishes that the premises are vacant:

exclude from ordinary occupier collection campaigns and route to the appropriate account-resolution process.

Do not infer vacancy merely from:

* zero consumption
* low consumption
* repeated non-payment
* failed contact

### Statutory / policy ineligibility

Exclude accounts where the proposed action is not currently permitted because, for example:

* required notice has not been served
* required notice period has not expired
* an approved arrangement is being honoured
* a policy hold applies
* a required prerequisite has not been satisfied

Do not claim an account is legally eligible unless the relevant system data establishes it.

### Ledger uncertainty

If there is an unresolved:

* unapplied payment
* duplicate charge
* billing correction
* meter replacement adjustment
* account transfer
* settlement
* reversal

place the account on:

**HOLD / RECONCILIATION**

rather than treating the balance as collection opportunity.

### Closed / transferred accounts

Route according to the configured recovery process rather than ordinary active-consumer campaigns.

---

# 6. Separate Eligibility From Priority

This distinction is mandatory.

### Eligibility asks:

> **Can we act on this account through this channel now?**

### Priority asks:

> **Among eligible accounts, where does scarce capacity produce the most incremental recovery?**

Do not allow a high-value account to bypass an eligibility gate.

---

# 7. Build the Opportunity Score

For each eligible account × channel combination, calculate or retrieve the approved decision inputs.

A conceptual score is:

```text
OPPORTUNITY =
    Recoverable Amount
    × Incremental Response Probability
    × Timely Recovery Factor
    − Intervention Cost
```

Where approved models support it.

If an uplift model is unavailable, do **not** invent one.

Instead use the strongest approved evidence available, such as:

* historical channel response
* segment-level response
* controlled campaign results
* payment probability
* historical treatment outcomes

Clearly label the result as an approximation where causal uplift has not been established.

---

# 8. Payment Probability Is Not Treatment Effect

Use the payment-probability model for:

> **Will this account pay?**

Use an approved uplift / treatment-response model for:

> **Will this account pay because we intervened?**

These are different questions.

Example:

| Account | Balance | Baseline payment probability | Call response | Campaign value |
| ------- | ------: | ---------------------------: | ------------: | -------------: |
| A       |   ₹10 L |                          92% |           Low |            Low |
| B       |    ₹6 L |                          48% |          High |           High |
| C       |   ₹20 L |                          30% |        Medium |           High |

The largest balance does not automatically win.

The lowest payment probability does not automatically win.

The best campaign target is the account where the intervention creates the greatest **incremental recoverable value**, subject to cost and constraints.

---

# 9. Optimize Across Channels

Do not optimize each channel independently and then combine the lists.

The same account may be eligible for:

* SMS
* call
* field visit

The optimization should compare the alternatives.

Example:

```text
Account A
SMS → ₹800 incremental recovery
CALL → ₹1,900 incremental recovery
FIELD → ₹2,200 incremental recovery

Account B
SMS → ₹300
CALL → ₹2,100
FIELD → ₹900
```

If field capacity is scarce, Account A may receive the field visit while Account B receives the call.

The output is therefore:

**account × recommended channel**

not merely:

**account ranking.**

---

# 10. Respect the Escalation Ladder

Collection should generally use the least intrusive effective intervention.

A typical ladder is:

```text
REMINDER
   ↓
CALL
   ↓
FIELD_VISIT / NOTICE
   ↓
DISCONNECT
```

But the ladder is not automatic.

Historical response may justify:

* repeating a successful low-cost intervention
* skipping an ineffective channel
* escalating earlier where policy permits
* holding where account conditions changed

If the same intervention failed repeatedly, do not repeat it automatically.

Require evidence explaining why the next attempt is expected to perform differently.

---

# 11. Disconnection Is a Gate, Not a Score

Never allow `DISCONNECT` to win simply because its expected recovery score is high.

Before including an account in a disconnection campaign, independently verify the configured prerequisites, such as:

* recoverable arrears are valid
* required billing conditions are satisfied
* required notice was served
* required period has expired
* no honoured arrangement exists
* no policy hold exists
* no unresolved ledger issue exists
* required approval is present

The optimizer determines **priority among eligible cases**.

It does not manufacture legal eligibility.

---

# 12. Detect Over-Serving

After generating the candidate ranking, inspect the composition.

Report:

* segment mix
* channel mix
* account count
* recoverable exposure
* expected incremental recovery
* average payment probability
* expected intervention cost

Look specifically for:

> **Accounts that are likely to pay without intervention.**

If a scarce field campaign is dominated by reliable-but-slow accounts, compare those accounts with cheaper alternatives such as reminders or calls.

Do not assume the ranking is wrong; demonstrate the opportunity cost.

---

# 13. Campaign Allocation

Use the actual capacity.

For a capacity-constrained campaign:

```text
AVAILABLE_CAPACITY
        ↓
ELIGIBILITY FILTER
        ↓
ACCOUNT × CHANNEL OPPORTUNITIES
        ↓
INCREMENTAL VALUE
        ↓
COST / CAPACITY OPTIMIZATION
        ↓
POLICY / OPERATIONAL CHECK
        ↓
FINAL CAMPAIGN LIST
```

If multiple channels compete for the same accounts, optimize jointly.

Example:

> 6,000 field visits are available. Allocate them against 41,000 eligible accounts, while retaining cheaper call/SMS treatments for accounts where field intervention does not provide sufficient incremental value.

The campaign should explicitly state the alternative allocation rejected.

---

# 14. Always State the Opportunity Cost

Every constrained campaign should answer:

> **What are we not doing because we chose this?**

Examples:

* 6,000 field visits allocated to recently deteriorated accounts rather than reliable-but-slow accounts.
* 20,000 calls allocated to medium-balance high-uplift accounts rather than the top 20,000 balances.
* SMS capacity retained for reliable-but-slow accounts while field capacity is reserved for accounts where physical intervention has higher incremental value.

A recommendation without an alternative is not a capacity decision.

---

# 15. Build the Campaign List

Use:

`buildCampaignList`

with:

* campaign objective
* channel
* capacity
* eligibility rules
* optimization criterion
* campaign horizon
* required exclusions
* approved model/version

The resulting list should be sized to actual capacity.

Do not return tens of thousands of account rows in the conversational response.

Use:

`exportDefaulterList`

or the configured campaign-export mechanism for the operational file.

The conversation should contain the decision summary, not the raw account dump.

---

# 16. Campaign Headline

Open a campaign recommendation with:

> **From `<population>` outstanding consumers, `<selected>` accounts selected for `<channel>` intervention — `<recoverable amount>` recoverable exposure and `<expected incremental recovery>` expected incremental recovery against `<campaign cost>` intervention cost.**

All figures must be sourced.

Do not call expected recovery “actual recovery.”

Do not call projected return “realized return.”

---

# 17. Show the Exclusions

Every campaign must explicitly report what was removed before ranking.

Example:

```text
EXCLUDED BEFORE RANKING

DISPUTED: 2,140 accounts | ₹8.7 cr
VACATED: 1,820 accounts | ₹5.1 cr
STATUTORY / POLICY HOLD: 3,210 accounts | ₹11.4 cr
LEDGER RECONCILIATION: 740 accounts | ₹1.8 cr
```

Then explain where appropriate:

> These accounts were not treated as campaign opportunities because the proposed intervention is currently inappropriate or the recoverable balance is not sufficiently established.

Never silently exclude them.

---

# 18. Measure Campaign Quality

After the campaign, compare:

### Financial

* gross recovery
* incremental recovery
* recoverable exposure
* intervention cost
* net recovery
* recovery per unit cost

### Operational

* accounts contacted
* successful contacts
* visits completed
* failed visits
* notices served
* actions completed
* capacity utilization

### Behavioral

* payment probability before intervention
* payment probability after intervention where appropriate
* days to payment
* promise-to-pay adherence
* repeat default
* migration between behavioral segments

### Model performance

* predicted incremental recovery vs actual
* predicted response vs actual response
* calibration
* ranking lift
* precision at campaign capacity
* treatment-effect accuracy where measurable

### Consumer impact

Monitor:

* complaints
* erroneous actions
* inappropriate escalation
* disputed-account contacts
* policy violations

Campaign success is not simply:

> money collected ÷ accounts contacted.

---

# 19. Distinguish Gross From Incremental Recovery

A campaign can produce substantial gross collections while generating little incremental recovery.

For example:

> 1,000 contacted accounts generated ₹1 cr in payments.

That does **not** establish that the campaign caused ₹1 cr of additional recovery.

Where a valid control group or uplift model exists, estimate:

> **Incremental recovery attributable to the intervention.**

If no causal estimate exists, say:

> “Gross recovery observed; incremental recovery not established.”

Do not manufacture causality.

---

# 20. Test for Cannibalization

If multiple campaigns run simultaneously, avoid double counting.

An account may receive:

* SMS
* call
* field visit

and eventually pay.

The system must distinguish:

* payment following any intervention
* payment attributable to the selected intervention
* payment that would probably have occurred anyway

Where causal attribution is unavailable, label the result accordingly.

---

# 21. Monitor Campaign Saturation

The top-ranked 1,000 accounts are not necessarily representative of the next 10,000.

As capacity expands:

* marginal opportunity generally changes
* expected recovery per intervention may fall
* channel mix may change
* segment mix may change
* operational failure may increase

Therefore report:

* top-N expected value
* marginal expected value
* cumulative expected value
* expected recovery per additional unit of capacity

Do not extrapolate the return of the extreme top of the ranking to the full campaign.

---

# 22. Segment-Aware Optimization

Use behavioral segments as inputs, not as automatic treatment decisions.

For example:

| Behavioral state      | Typical opportunity           | Likely treatment                      |
| --------------------- | ----------------------------- | ------------------------------------- |
| Stable on-time        | Low incremental value         | No intervention                       |
| Reliable but slow     | Low-cost timing reminder      | SMS / reminder                        |
| Intermittent          | Moderate                      | Call / reminder                       |
| Recently deteriorated | High intervention opportunity | Call / field                          |
| Recovering            | Avoid unnecessary escalation  | Reminder / monitor                    |
| Chronic default       | High-value targeted recovery  | Field / notice / eligible enforcement |

The final action must still be determined by the action-optimization skill and applicable policy.

---

# 23. Behavioral Change Matters

A static ranking can miss the most valuable intervention opportunity.

Monitor:

* payment regularity
* missed cycles
* days late
* outstanding growth
* recent payment deterioration
* promise-to-pay behavior
* response to prior interventions

A recently deteriorated account may be more intervention-sensitive than an account that has been chronically delinquent for years.

---

# 24. Account-Level Output

When asked why a specific account is included in a campaign, return exactly:

```text
CAMPAIGN_ELIGIBILITY: ELIGIBLE | INELIGIBLE | HOLD
RECOMMENDED_CHANNEL: SMS | CALL | FIELD_VISIT | NOTICE | DISCONNECT | NONE
CAMPAIGN_PRIORITY: high | medium | low
CONFIDENCE: high | medium | low
```

Then provide:

### Current position

* recoverable amount
* delinquency status
* recent payment behavior
* prior interventions

### Why selected

Identify the evidence supporting the incremental opportunity.

### Why this channel

Compare the selected channel with credible alternatives.

### What points the other way

State the strongest reason not to select the account or channel.

### Expected outcome

State expected incremental recovery only when supported by an approved model or methodology.

### What would change the decision

Examples:

* payment received
* dispute opened
* arrangement honoured
* account status changed
* capacity changed
* model score materially changed

### What is not established

Do not infer:

* inability to pay
* unwillingness to pay
* consumer character
* intent
* protected characteristics

---

# 25. Portfolio Campaign Output

For a campaign request, return:

```text
CAMPAIGN_OBJECTIVE: <objective>
CAMPAIGN_HORIZON: <period>
ELIGIBLE_POPULATION: <count>
SELECTED_ACCOUNTS: <count>
SELECTED_RECOVERABLE_EXPOSURE: <amount>
EXPECTED_INCREMENTAL_RECOVERY: <amount>
ESTIMATED_CAMPAIGN_COST: <amount>
EXPECTED_NET_RECOVERY: <amount>
PRIMARY_CHANNEL: <channel>
CONFIDENCE: high | medium | low
```

Then show:

### Allocation

| Channel | Capacity | Selected | Recoverable Exposure | Expected Incremental Recovery | Cost |
| ------- | -------: | -------: | -------------------: | ----------------------------: | ---: |

### Exclusions

| Reason | Accounts | Recoverable Exposure |
| ------ | -------: | -------------------: |

### Segment mix

| Segment | Accounts | Exposure | Expected Incremental Recovery | Primary Channel |
| ------- | -------: | -------: | ----------------------------: | --------------- |

### Decision narrative

Explain:

1. where capacity was allocated
2. why those accounts won
3. what alternative was rejected
4. which groups were excluded
5. why cheaper channels were or were not preferred
6. what assumption is most likely to break the plan

---

# 26. The One Assumption Most Likely to Break the Plan

Every campaign must identify one.

Examples:

> **Primary risk:** The estimated call uplift is based on the last two campaigns, but response may fall as the campaign expands beyond the previously tested population.

Or:

> **Primary risk:** Recoverable balances may be overstated because recent ledger reconciliation is incomplete.

Or:

> **Primary risk:** Field capacity may be lower than nominal because of failed visits and travel time.

Then state what would confirm or invalidate the assumption.

---

# 27. Data Quality Gates

Before campaign generation, check:

* payment freshness
* billing freshness
* recoverable-balance validity
* duplicate accounts
* account status
* premises status
* dispute status
* arrangement status
* notice status
* prior campaign status
* contactability
* field-serviceability
* model coverage
* model version
* intervention history

If a critical field is unavailable, do not silently treat missing information as eligible.

Use:

**UNKNOWN / HOLD**

where appropriate.

---

# 28. Model Governance

Every campaign recommendation should record:

* model name
* model version
* score date
* feature snapshot / data cutoff
* campaign horizon
* optimization objective
* capacity assumption
* eligibility rules
* exclusions
* treatment-response methodology
* selection algorithm
* operator overrides

If the model is outside its validated population, reduce confidence or block automated selection according to governance policy.

---

# 29. Fairness and Consumer Protection

Do not rank consumers using protected characteristics or inappropriate proxies.

Do not infer:

* income
* poverty
* education
* religion
* caste
* ethnicity
* health status
* family circumstances
* intent
* moral character

Category and locality are not inherent payment-risk factors.

Use them only where they legitimately affect:

* statutory route
* operational feasibility
* tariff / billing arithmetic
* service rules
* geography-dependent intervention cost

Do not use segmentation to disguise discriminatory targeting.

---

# 30. Audit Trail

Every campaign must be reproducible.

Record:

```text
CAMPAIGN_ID
RUN_TIMESTAMP
DATA_AS_OF
MODEL_VERSION
OPTIMIZATION_OBJECTIVE
CAPACITY_AVAILABLE
ELIGIBILITY_RULES
EXCLUSION_RULES
SELECTED_CHANNELS
SELECTION_METHOD
OVERRIDES
SELECTED_ACCOUNT_COUNT
SELECTED_EXPOSURE
EXPECTED_INCREMENTAL_RECOVERY
ESTIMATED_COST
```

If an operator overrides the ranking, record:

* account
* original rank
* new rank
* reason
* approver
* timestamp

---

# 31. Never Do These

### Never rank only on outstanding balance

Large balance does not mean large incremental opportunity.

### Never rank only on payment probability

High payment probability may mean the consumer will pay without intervention.

### Never assume chronic defaulters should receive every expensive intervention

Chronic status is a risk/state indicator, not an automatic channel recommendation.

### Never exceed channel capacity

Capacity is part of the optimization problem.

### Never silently exclude accounts

Show exclusions and reasons.

### Never treat gross recovery as incremental recovery

Causality must be established or clearly qualified.

### Never allow `DISCONNECT` to bypass eligibility

Enforcement is gated independently.

### Never repeat failed treatment blindly

Require evidence that circumstances or treatment have changed.

### Never optimize against disputed balances

Resolve validity first.

### Never infer consumer intent or means

Payment behavior is evidence of payment behavior—not character.

### Never fabricate campaign returns

Every forecasted recovery and cost must have a source or approved methodology.

---

# 32. Operational Workflow

```text
Campaign Request
      ↓
Define Objective + Horizon
      ↓
Read Campaign History
      ↓
Read Channel Capacity
      ↓
Establish Population + Recoverable Exposure
      ↓
Eligibility / Policy / Statutory Gates
      ↓
Exclude Disputes / Vacated / Holds / Ledger Issues
      ↓
Generate Account × Channel Opportunities
      ↓
Payment Probability + Treatment Response
      ↓
Incremental Expected Recovery
      ↓
Cost + Capacity Optimization
      ↓
Check Segment Mix + Opportunity Cost
      ↓
Build Campaign List
      ↓
Human / Policy Approval
      ↓
Execute Campaign
      ↓
Measure Gross + Incremental Recovery
      ↓
Measure Cost + Consumer Impact
      ↓
Feed Results Back to Campaign History
      ↓
Recalibrate Optimization
```

---

# 33. Relationship to Other Collection Skills

This skill is the **allocation layer**.

```text
Payment Probability
        │
        ├── Will the account pay?
        │
Chronic Default Risk
        │
        ├── Is the account approaching chronic default?
        │
Payment Behavior Segmentation
        │
        ├── What behavioral state is the account in?
        │
Collection Action Optimization
        │
        ├── What is the appropriate next action?
        │
Collection Campaign Optimization
        │
        └── Where should scarce capacity be deployed?
                    ↓
              Campaign Execution
                    ↓
              Actual Recovery
                    ↓
              Outcome Feedback
```

The skills must not duplicate one another.

**Payment probability** predicts payment.

**Chronic-risk scoring** predicts future chronic default.

**Behavior segmentation** describes payment behavior.

**Action optimization** chooses the appropriate next action.

**Campaign optimization** allocates scarce intervention capacity across eligible accounts and channels.

---

# 34. Final Principle

> **Do not send the most expensive collection action to the account with the largest balance. Send the scarce intervention to the account where it creates the greatest incremental recoverable value, subject to eligibility, capacity, cost, policy, and consumer-impact constraints.**

The optimization chain is:

**Valid recoverable exposure → eligibility → baseline payment probability → treatment response → incremental recovery → channel cost → capacity → campaign allocation → execution → measured incremental recovery → feedback.**