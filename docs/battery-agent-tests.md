# Testing the battery warranty agents

**Everything here is done in the browser.** Open an agent (or its card under
**Tasks**), type the input into the chat box, read the answer. You are the test.

Four agents, three problems a battery maker's warranty team has:

| Agent | Skill | Problem |
|---|---|---|
| **No-Fault-Found Analyst** | `no-fault-found-analysis` | healthy batteries replaced under warranty |
| **Batch Quality Watch** | `early-batch-failure` | a manufacturing batch failing before its time |
| **Warranty Fraud Review** | `warranty-fraud-network` | leakage and organised abuse across claims |
| **Warranty Analyst** | all three | picks the skill a question needs |

Every case has a **counter-case**. The first is the obvious finding; the second
is the one a plausible-sounding model gets wrong. An agent that passes only the
first half of a pair has not been tested, it has been flattered.

**The data is synthetic.** It lives only in this repository's tool service
(`services/battery_population.py`, fixed seed, so these numbers do not move) and
reaches the agents through 17 read-only tools at `/battery`. Nothing is written
to the platform's database except the workspace, the tool definitions, the
skills and the agents.

## Before you start

1. **Workspace picker**, top left → **Battery Warranty Analytics**.
2. **Administration → API keys → Anthropic** — a key must be installed in *this*
   workspace (keys are not inherited).
3. **Tools** → 17 battery tools. **Tasks** → four agents.
4. The platform must be allowed to reach the demo service: on any deployment
   running it, set **Settings → Deployment → `egress_private_hosts`** to
   `mcp-tools` (the outbound-URL guard blocks internal addresses otherwise).

Set up from this repository:

```bash
PLATFORM_NETWORK=<platform network> docker compose up -d --build
docker compose exec mcp-tools python seeds/battery.py
```

The first run stops at "No usable model" in a new workspace: add the Anthropic
key (step 2) and run it again.

**Start a new chat for every input.** An agent sees the earlier turns in the same
chat, which quietly ruins a counter-case run after its case.

If a figure here disagrees with an agent, check the tool before blaming the
agent — `curl -s localhost:8304/battery/summary | python3 -m json.tool`.

## The population (as of 1 Oct 2026)

| | |
|---|---|
| Batteries sold | **114,385** (4 plants × 2 lines, Jan 2022 – Aug 2026, 10 cities, 300 dealers, 120 technicians) |
| Warranty claims | **4,659** |
| Replaced under warranty | **3,443**, of which **3,428** retested at the plant |
| No fault found (healthy) | **342** — **10.0%**, costing **₹21.28 lakh** |

---

## 1. No-Fault-Found Analyst

### 1a. "Why is our warranty cost high?"

**Correct answer contains:**
- Overall NFF 10.0% (342 of 3,428), ₹21.28 lakh.
- **Pune** is the outlier: **31.2% NFF (130 of 417)**, ₹8.69 lakh — about 40% of
  all NFF cost from one city. Nagpur (16.1%) is second.
- Inside Pune, two technicians: **TEC-PUN-009** (59 of 82, 72%) and
  **TEC-PUN-004** (61 of 91, 67%). They did **no load test** on most
  replacements (76 and 87 of them) and about **55% read OCV ≥ 12.4 V** —
  healthy-battery readings.
- Their Pune peers do a load test on ~72% of claims.
- Recommendation: load test + alternator check required before a replacement is
  approved; coaching for the two technicians; a supervisor check on replacements
  with OCV ≥ 12.4 V.

**Wrong answer it catches:** blaming Pune's *claim volume* or the technicians'
*honesty*. The skill forbids calling a technician dishonest.

### 1b. "Is Jaipur a no-fault-found problem? Claims there jumped this summer."

**This is the counter-case.** Jaipur's claims jumped in **April–June 2026** (80,
105 and 71 retests a month against ~10), but its NFF rate is **3.2%** overall
and **0–1.4%** in those months. The factory confirms grid corrosion and dry-out
— heat failures. **Correct:** it is real failure, not giveaways; heat, not
process. **Wrong:** "Jaipur's spike is an NFF problem" — more claims is not more
NFF.

### 1c. `CLM-PUN-24601` then `CLM-JAI-31877`

- **CLM-PUN-24601** — OCV **12.58 V**, load test **not done**, alternator **not
  checked**, all six cells 1.25–1.27; replaced by TEC-PUN-004; factory: **no fault
  found**. Correct: the replacement was not justified on the readings; a load test
  would have shown it.
- **CLM-JAI-31877** (counter) — OCV **11.62 V**, load test **failed**, cells low
  (1.19–1.24); factory: **grid corrosion**. Correct: justified. **Wrong:** treating
  it as NFF because it is another replaced battery.

### 1d. "How does TEC-PUN-003 compare?"

Counter for "it's Pune": **TEC-PUN-003** does a load test on **88%** of claims and
its NFF rate is **3.6%** — the problem is two technicians' practice, not the city.

---

## 2. Batch Quality Watch

### 2a. "Is any batch failing early?"

**Correct answer contains:**
- **A2-2603-2** (Ahmednagar, line 2, made March 2026): **26 early failures out of
  146 sold — 178 per 1,000 (95%: 125–248)** against a median of **7.5**. Roughly
  24× normal.
- Failure mode: **cell short** (19 of 20 retested), **cell 3** reads low on 24 of
  26; most fail in the **first one or two months**; sold across many cities
  (Pune, Mumbai, Hyderabad, Nagpur…) — it is the battery, not a region.
- Neighbour **A2-2603-1** is up too (45 per 1,000, 5 cell shorts).
- Production record: separator lot **SEP-2603-09** from **NewSep Industries (first
  lot)**, and a **formation temperature excursion (53.4 °C)** on line 2, 11–12 Mar.
  A2-2603-1 shares the separator lot.
- Likely cause, stated as likely: the new separator lot (and/or the formation
  excursion). Containment: hold unsold stock from both batches, proactive check
  for sold units still in warranty, separator supplier review, teardown to confirm.
- The **line** (A2) is barely above others (10.0 vs ~8) — this is a batch, not a line.

**Wrong answer it catches:** blaming the whole Ahmednagar plant or line 2.

### 2b. "H1-2201-1 has more claims than any other batch. Is it bad?"

**Counter-case.** **H1-2201-1** has **28 claims** — the most of any batch — but it
is **three times the usual size (390 units)** and the **oldest** (Jan 2022); its
claims come late in life (11 of them at 24 months) and its early-failure rate is
about **2.6 per 1,000**, below the median. **Correct:** no — size and age, normal
rate. **Wrong:** "H1-2201-1 is the worst batch".

### 2c. `EX-A2-2603-2-00001`

A serial from the bad batch: the agent should read the batch out of the serial
and say this unit is in an affected batch, whatever its own claim history.

---

## 3. Warranty Fraud Review

### 3a. "Which dealers should we audit?"

**Correct answer contains:**
- **DLR-NGP-021** (Nagpur): replaces **91% of 55 claims** against a Nagpur median
  of **75%** (about 9 excess replacements); **60% of its replacements tested
  healthy** (30 of 50, ₹1.07 lakh); **17 of 55 claims (31%) filed in the last 10
  days of warranty** against a norm of **0.45%**; one technician, **TEC-NGP-007**,
  handled **35** of its claims.
- The same label photo **ph_7d1c09e2** appears on **three claims for three
  different batteries** — two at DLR-NGP-021, one at DLR-NGP-018.
- Recommendation: audit DLR-NGP-021's claims and TEC-NGP-007's work, hold its
  pending claims, add a photo-hash check and supervisor approval for claims in the
  last 30 days of warranty. Risk, not guilt.

### 3b. "DLR-JAI-012 approves 84% of claims. Is it suspicious?"

**Counter-case.** DLR-JAI-012 replaces **84% of 50 claims**, but only **1 of 42**
retested batteries was healthy; the rest are grid corrosion, dry-out and
sulphation — Jaipur heat. **Correct:** not suspicious; real failures. **Wrong:**
flagging it on approval rate alone.

### 3c. `+919820155443` then `+919822077110`

- **+919820155443** — **6 batteries, 6 claims, three Mumbai dealers** (DLR-MUM-007,
  019, 026), July–August 2026; **not the registered owner** of the batteries; **4
  of 6** retested healthy. Correct: high risk — a claim ring; audit.
- **+919822077110** (counter) — **9 batteries**, but it is **Sai Cabs Pvt Ltd, fleet
  account FL-0042**, the registered owner of all of them, one dealer
  (DLR-MUM-012), and **none** tested healthy. Correct: legitimate fleet. **Wrong:**
  flagging the phone with the most batteries.

---

## 4. Warranty Analyst (all three skills)

### 4a. "Where are we losing warranty money?"

Should use the NFF skill first (₹21.28 lakh of healthy batteries, Pune's two
technicians), mention the fraud signals at DLR-NGP-021, and the batch problem
A2-2603-2 as a quality cost — each briefly, with the agent to ask for detail.
Check **Runs** to see which skills were selected.

### 4b. "Any quality problems I should know about before month end?"

Should pick the **early-batch-failure** skill only and lead with A2-2603-2.

---

## What a good answer looks like, every time

- Rates come with counts ("72% — 59 of 82").
- The innocent explanation is named and checked before a problem is.
- People are not accused; claims, dealers and technicians are recommended for
  audit or coaching.
- The answer leads with the finding, then the evidence, then the action.
