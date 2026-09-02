"""The collection book: a population of outstanding consumers, scored.

Use case 1 is a portfolio problem — score every consumer, segment the book,
size a campaign, forecast the month. The per-consumer agent cannot do that: you
cannot hand a language model a million accounts, and asking it to produce a
probability per consumer gets you a number that was invented.

So the split is the one a real deployment uses:

    a scoring model   ->  payment probability for every account
    the agent         ->  which segments to work, with what channel, at what
                          capacity, and why — reviewable, arguable, explainable

`_score` below stands in for the trained model. It is a transparent weighted
function rather than a black box on purpose: the demo is about what the agent
does with a score, and a score whose derivation nobody can see makes every
downstream answer unfalsifiable. In a real deployment this is a gradient
boosting model over the same features, and everything above it is unchanged.

Ten lakh consumers, streamed rather than stored. The population is generated
deterministically and consumed as it goes: per-segment aggregates accumulate,
and a bounded heap keeps the highest expected-recovery accounts. Nothing holds
a million rows, and nothing needs to — the only accounts anyone works are the
ones at the top of the ranking, and the only thing anyone needs about the rest
is the totals.

That is also the shape of the real system. A scoring job runs over the whole
book nightly and writes a ranked working list; nobody loads ten lakh accounts
into anything interactive, least of all a language model.
"""

from __future__ import annotations

import heapq
import json
import random
from pathlib import Path
from dataclasses import asdict, dataclass, field

SEED = 20260901
POPULATION = 1_000_000

# How many top-ranked accounts to keep for the working list.
#
# Sized above the largest channel capacity (calls, 40,000) with headroom, so
# that a campaign on any channel can be filled from it after exclusions. At
# 6,000 a field campaign already exhausted the pool and a call campaign could
# never be sized at all — the ranking silently ran out, which looks identical
# to there being no more accounts worth working.
MATERIALISE = 60_000

# What counts as "at risk of becoming chronic" for the headline count. The
# score ranks the whole deteriorating segment; this is the band worth acting on
# this month. At 0.5 the count was 97% of the segment — true, and no use for
# targeting anything.
AT_RISK_THRESHOLD = 0.72

DIVISIONS = ["Pune East", "Pune West", "Pune Rural"]
CATEGORIES = ["LT-1 Domestic", "LT-2 Commercial", "HT Industrial", "LT-5 Agricultural"]

# Share of the book by category, and the mean arrears each carries. Commercial
# and industrial are a small share of accounts and a large share of the money,
# which is the whole reason a campaign targeted by value looks different from
# one targeted by count.
_MIX = {
    "LT-1 Domestic":     {"share": 0.72, "mean_due": 6_500,  "sd": 4_000},
    "LT-2 Commercial":   {"share": 0.17, "mean_due": 38_000, "sd": 30_000},
    "HT Industrial":     {"share": 0.02, "mean_due": 210_000, "sd": 160_000},
    "LT-5 Agricultural": {"share": 0.09, "mean_due": 11_000, "sd": 7_000},
}

# Behavioural segments. `p_base` is the payment probability before the
# account's own history moves it, and `response` is how each segment has
# historically responded to each channel — the numbers a campaign is optimised
# against.
SEGMENTS: dict[str, dict] = {
    "reliable_slow": {
        "label": "Reliable but slow",
        "definition": "Pays every cycle, consistently after the due date. "
                      "Manages cash rather than avoiding payment.",
        "p_base": 0.88,
        "response": {"sms": 0.62, "call": 0.71, "field_visit": 0.74,
                     "notice": 0.76},
        "note": "The most over-served segment in most DISCOMs. A field visit "
                "here recovers what an SMS would have.",
    },
    "recent_deterioration": {
        "label": "Recently deteriorated",
        "definition": "Long clean record, then two to four missed cycles. A "
                      "change of circumstances, not a payment habit.",
        "p_base": 0.63,
        "response": {"sms": 0.28, "call": 0.55, "field_visit": 0.61,
                     "notice": 0.58},
        "note": "The segment where early intervention changes the outcome. "
                "Left alone these become chronic within two quarters.",
    },
    "chronic_defaulter": {
        "label": "Chronic defaulter",
        "definition": "Six or more unpaid cycles, multiple notices ignored, "
                      "broken promises to pay.",
        "p_base": 0.17,
        "response": {"sms": 0.03, "call": 0.07, "field_visit": 0.24,
                     "notice": 0.19},
        "note": "Low probability, high value. Worth working only where the "
                "amount justifies the visit.",
    },
    "disputed": {
        "label": "Disputed balance",
        "definition": "An open complaint or billing dispute on the amount.",
        "p_base": 0.35,
        "response": {"sms": 0.05, "call": 0.31, "field_visit": 0.12,
                     "notice": 0.08},
        "note": "Recovery action on a disputed balance generates complaints "
                "and regulatory exposure. Resolve the dispute first.",
    },
    "gone_away": {
        "label": "Premises vacated",
        "definition": "No consumption, undelivered notices, no contact.",
        "p_base": 0.06,
        "response": {"sms": 0.01, "call": 0.02, "field_visit": 0.09,
                     "notice": 0.02},
        "note": "Nothing to recover from the occupier. Field visits here are "
                "the largest single waste in most collection programmes.",
    },
    "new_connection_arrears": {
        "label": "New connection, early arrears",
        "definition": "Connected within 12 months, already behind. Often a "
                      "billing setup problem rather than a payment problem.",
        "p_base": 0.54,
        "response": {"sms": 0.41, "call": 0.63, "field_visit": 0.48,
                     "notice": 0.44},
        "note": "Check the tariff and meter setup before treating as recovery.",
    },
}

# What each channel costs to execute per account, and what it consumes of a
# finite capacity. Field capacity is the binding constraint in every real
# collection programme, which is what makes this an optimisation rather than a
# ranking.
CHANNELS = {
    "sms":         {"cost_per_account": 0.35, "capacity_per_month": 1_000_000},
    "call":        {"cost_per_account": 12.0, "capacity_per_month": 40_000},
    "field_visit": {"cost_per_account": 260.0, "capacity_per_month": 6_000},
    "notice":      {"cost_per_account": 45.0, "capacity_per_month": 25_000},
    # The last rung. Cheaper per account than a visit because the crew is
    # already doing rounds, and capacity-limited for the same reason. Unlike
    # every other channel this one has a legal precondition, so an account
    # being high-value is not enough to put it on the list — see `dc_eligible`.
    "disconnection": {"cost_per_account": 180.0, "capacity_per_month": 3_000},
}


@dataclass
class Account:
    consumer_no: str
    division: str
    category: str
    outstanding: float
    unpaid_cycles: int
    days_since_last_payment: int
    on_time_ratio: float
    notices_ignored: int
    broken_promises: int
    connection_age_months: int
    has_open_dispute: bool
    consumption_last_period: int
    notice_served: bool = False
    notice_expired: bool = False
    billed_on_actual_reads: bool = True
    segment: str = ""
    payment_probability: float = 0.0
    expected_recovery: float = 0.0
    # Probability of becoming a chronic defaulter within two quarters, for
    # accounts that are not chronic yet. This is the "catch them before they
    # tip" signal; it is deliberately separate from payment probability, which
    # answers a different question — one is about this month's collection, the
    # other about next year's book.
    chronic_risk: float = 0.0
    dc_eligible: bool = False
    dc_blocked_by: str = ""
    features: dict = field(default_factory=dict)


def _segment_for(a: Account) -> str:
    """Behavioural segment. Order matters: the first match wins, and the
    exclusions at the top are the ones that must not be worked as recovery."""
    if a.has_open_dispute:
        return "disputed"
    if a.consumption_last_period == 0 and a.notices_ignored >= 2:
        return "gone_away"
    if a.connection_age_months <= 12:
        return "new_connection_arrears"
    if a.unpaid_cycles >= 6 and (a.notices_ignored >= 2 or a.broken_promises >= 1):
        return "chronic_defaulter"
    if a.unpaid_cycles <= 4 and a.on_time_ratio >= 0.75:
        return "recent_deterioration"
    if a.on_time_ratio >= 0.6:
        return "reliable_slow"
    return "chronic_defaulter"


def _score(a: Account) -> tuple[float, dict]:
    """Payment probability, and the features that produced it.

    Stands in for a trained model. Returned with its inputs so the agent can
    explain a score rather than assert one — an unexplainable score is not
    usable in a collection review, because the first question anyone asks is
    why this account and not that one.
    """
    base = SEGMENTS[a.segment]["p_base"]
    contribs = {}

    # Each term is bounded, so no single feature can swamp the segment prior.
    contribs["payment_regularity"] = round((a.on_time_ratio - 0.5) * 0.30, 4)
    contribs["arrears_age"] = round(-min(a.unpaid_cycles, 12) * 0.022, 4)
    contribs["contact_silence"] = round(-min(a.days_since_last_payment, 540) / 540 * 0.14, 4)
    contribs["ignored_notices"] = round(-min(a.notices_ignored, 4) * 0.035, 4)
    contribs["broken_promises"] = round(-min(a.broken_promises, 3) * 0.06, 4)
    # A live connection still consuming is someone who is there and has
    # something to lose. The strongest positive signal after regularity.
    contribs["active_consumption"] = round(0.09 if a.consumption_last_period > 0 else -0.11, 4)

    p = base + sum(contribs.values())
    p = max(0.01, min(0.97, p))
    return round(p, 4), {"segment_prior": base, **contribs}


def _chronic_risk(a: Account) -> float:
    """How likely this account is to be chronic in two quarters.

    Trajectory, not level. An account four cycles down and accelerating is
    closer to chronic than one eight cycles down that has stabilised.

    The segment sets the base rate, because the segmentation already encodes
    the trajectory: `recent_deterioration` *is* the population in the act of
    tipping, and a signal that does not rank it highest is measuring something
    else. An earlier version subtracted a protective term for a good payment
    history, which inverted the whole thing — a long clean record followed by
    missed cycles is the alarming case, not the reassuring one. It ranked
    reliable payers above the deteriorating segment.

    Zero for accounts already chronic, vacated, or disputed. The question is
    who can still be caught.
    """
    base = {
        "recent_deterioration": 0.55,
        "new_connection_arrears": 0.34,
        "reliable_slow": 0.08,
    }.get(a.segment)
    if base is None:
        return 0.0

    risk = base
    # Distance to the six-cycle chronic threshold.
    risk += 0.26 * (min(a.unpaid_cycles, 6) / 6.0)
    risk += 0.16 * (min(a.notices_ignored, 3) / 3.0)
    risk += 0.14 * (min(a.broken_promises, 2) / 2.0)
    risk += 0.10 * (min(a.days_since_last_payment, 365) / 365.0)
    if a.consumption_last_period == 0:
        risk += 0.08
    # Still paying most cycles is the one genuinely protective fact, and it is
    # worth far less than the trajectory terms above.
    risk -= 0.12 * a.on_time_ratio
    return round(max(0.0, min(0.99, risk)), 4)


def _disconnection_eligibility(a: Account) -> tuple[bool, str]:
    """Whether this account may lawfully be disconnected, and what blocks it.

    Not a ranking input — a gate. Every other channel can be pointed at the
    highest-value accounts; this one cannot, and an eligible-but-small account
    outranks a large one that has had no notice. The reason is returned so a
    blocked account can be routed to the step that unblocks it rather than
    silently dropped.
    """
    if a.has_open_dispute:
        return False, "balance disputed"
    if not a.billed_on_actual_reads:
        return False, "billed on estimated reads"
    if not a.notice_served:
        return False, "no statutory notice served"
    if not a.notice_expired:
        return False, "notice period not expired"
    return True, ""


def _generate() -> tuple[list[Account], list[Account], dict, dict]:
    """Stream the book once: accumulate aggregates, keep the top accounts.

    A heap rather than a sort, because sorting a million rows to take six
    thousand of them costs the memory this is written to avoid.
    """
    rng = random.Random(SEED)
    cats = list(_MIX)
    weights = [_MIX[c]["share"] for c in cats]

    heap: list[tuple[float, int, Account]] = []
    # A second heap on chronic risk. The value heap cannot serve the
    # early-warning question: the accounts closest to tipping are not the
    # largest balances, so filtering a value-ranked pool by risk returns the
    # big accounts that happen to be at risk and misses the rest — which is
    # the balance-driven error this whole skill exists to avoid.
    risk_heap: list[tuple[float, int, Account]] = []
    agg: dict[str, dict] = {
        name: {"accounts": 0, "outstanding": 0.0, "expected": 0.0,
               "p_sum": 0.0, "at_risk": 0, "at_risk_outstanding": 0.0,
               "dc_eligible": 0}
        for name in SEGMENTS
    }
    by_division: dict[str, dict] = {
        d: {"accounts": 0, "outstanding": 0.0, "expected": 0.0} for d in DIVISIONS
    }

    for i in range(POPULATION):
        cat = rng.choices(cats, weights=weights)[0]
        mix = _MIX[cat]
        due = max(500.0, rng.gauss(mix["mean_due"], mix["sd"]))
        on_time = min(1.0, max(0.0, rng.betavariate(3.4, 1.5)))
        unpaid = rng.choices([1, 2, 3, 4, 5, 6, 8, 10, 14],
                             weights=[22, 18, 14, 11, 9, 8, 7, 6, 5])[0]
        age = rng.choices([4, 9, 18, 40, 90, 160],
                          weights=[3, 4, 14, 30, 30, 19])[0]
        notices = rng.choices([0, 1, 2, 3, 4], weights=[38, 27, 18, 11, 6])[0]
        broken = rng.choices([0, 1, 2], weights=[82, 14, 4])[0]
        vacated = rng.random() < 0.055
        division = rng.choices(DIVISIONS, weights=[0.42, 0.33, 0.25])[0]

        acc = Account(
            consumer_no=f"{'DL' if cat.startswith('LT-1') else 'CM' if cat.startswith('LT-2') else 'IN' if cat.startswith('HT') else 'AG'}-{700000 + i}",
            division=division, category=cat, outstanding=round(due, 2),
            unpaid_cycles=unpaid,
            days_since_last_payment=min(900, unpaid * 30 + rng.randint(0, 45)),
            on_time_ratio=round(on_time, 3), notices_ignored=notices,
            broken_promises=broken, connection_age_months=age,
            has_open_dispute=rng.random() < 0.043,
            consumption_last_period=0 if vacated else rng.randint(40, 900),
            # Notice practice tracks how far down the account is: nobody serves
            # a statutory notice on a single missed cycle.
            notice_served=notices > 0 or unpaid >= 4,
            notice_expired=notices > 0 and unpaid >= 5,
            billed_on_actual_reads=rng.random() > 0.07,
        )
        acc.segment = _segment_for(acc)
        acc.payment_probability, acc.features = _score(acc)
        acc.expected_recovery = round(acc.outstanding * acc.payment_probability, 2)
        acc.chronic_risk = _chronic_risk(acc)
        acc.dc_eligible, acc.dc_blocked_by = _disconnection_eligibility(acc)

        a = agg[acc.segment]
        a["accounts"] += 1
        a["outstanding"] += acc.outstanding
        a["expected"] += acc.expected_recovery
        a["p_sum"] += acc.payment_probability
        if acc.chronic_risk >= AT_RISK_THRESHOLD:
            a["at_risk"] += 1
            a["at_risk_outstanding"] += acc.outstanding
        if acc.dc_eligible:
            a["dc_eligible"] += 1
        d = by_division[division]
        d["accounts"] += 1
        d["outstanding"] += acc.outstanding
        d["expected"] += acc.expected_recovery

        if len(heap) < MATERIALISE:
            heapq.heappush(heap, (acc.expected_recovery, i, acc))
        elif acc.expected_recovery > heap[0][0]:
            heapq.heapreplace(heap, (acc.expected_recovery, i, acc))

        if acc.chronic_risk > 0:
            if len(risk_heap) < MATERIALISE:
                heapq.heappush(risk_heap, (acc.chronic_risk, i, acc))
            elif acc.chronic_risk > risk_heap[0][0]:
                heapq.heapreplace(risk_heap, (acc.chronic_risk, i, acc))

    top = [a for _e, _i, a in sorted(heap, key=lambda t: -t[0])]
    at_risk = [a for _r, _i, a in sorted(risk_heap, key=lambda t: -t[0])]
    return top, at_risk, agg, by_division


def _load() -> tuple[list[Account], list[Account], dict, dict]:
    """Generate once, then load from cache.

    Streaming ten lakh accounts takes about twenty seconds. Paying that on
    every import would mean paying it on every container start and in every
    test collection, for a population that is deterministic and never changes.
    The cache key is the seed and the population size, so editing either
    regenerates rather than silently serving a stale book.
    """
    # Every input that changes what is stored belongs in the key. The
    # threshold was left out once and the cache went on serving counts
    # computed at the old value — the tool reported the new threshold
    # beside the old number, which is worse than either alone.
    key = f"{SEED}-{POPULATION}-{MATERIALISE}-{AT_RISK_THRESHOLD}-v2"
    cache = Path(__file__).resolve().parent / "_portfolio_cache.json"
    if cache.exists():
        try:
            blob = json.loads(cache.read_text())
            if blob.get("key") == key:
                top = [Account(**a) for a in blob["top"]]
                at_risk = [Account(**a) for a in blob["at_risk"]]
                return top, at_risk, blob["segments"], blob["divisions"]
        except (json.JSONDecodeError, TypeError, KeyError):
            pass  # regenerate rather than fail on a cache written by older code

    top, at_risk, segments, divisions = _generate()
    try:
        cache.write_text(json.dumps({
            "key": key,
            "top": [asdict(a) for a in top],
            "at_risk": [asdict(a) for a in at_risk],
            "segments": segments, "divisions": divisions,
        }))
    except OSError:
        # A read-only image is fine; it just pays the generation each start.
        pass
    return top, at_risk, segments, divisions


TOP, AT_RISK, SEGMENT_TOTALS, DIVISION_TOTALS = _load()
# Lookup spans both pools, so a consumer surfaced by either list can be scored.
BY_NO: dict[str, Account] = {a.consumer_no: a for a in (*TOP, *AT_RISK)}


# --- what has already been tried -------------------------------------------
# The most common collection mistake is re-running a campaign that did not
# work. The March field campaign below is the case: it targeted the largest
# balances, which put teams in front of chronic defaulters and gone-away
# premises, and returned 11 paise per rupee of cost.

CAMPAIGNS: list[dict] = [
    {"campaign": "CAM-2026-03", "month": "2026-03", "channel": "field_visit",
     "targeted_on": "largest outstanding balance",
     "segments_hit": {"chronic_defaulter": 3_900, "gone_away": 410,
                      "reliable_slow": 690},
     "accounts": 5_000, "cost": 1_300_000.0, "recovered": 4_820_000.0,
     "recovered_per_rupee_cost": 3.71,
     "note": "Targeted by balance. Half the visits were to accounts with a "
             "payment probability below 0.1."},
    {"campaign": "CAM-2026-05", "month": "2026-05", "channel": "sms",
     "targeted_on": "all outstanding accounts",
     "segments_hit": {"reliable_slow": 6_800, "recent_deterioration": 5_900,
                      "chronic_defaulter": 7_700, "gone_away": 420},
     "accounts": 21_000, "cost": 7_350.0, "recovered": 8_910_000.0,
     "recovered_per_rupee_cost": 1212.2,
     "note": "Untargeted SMS. Cheap enough that poor targeting did not matter; "
             "almost all of the recovery came from reliable_slow."},
    {"campaign": "CAM-2026-07", "month": "2026-07", "channel": "call",
     "targeted_on": "recent_deterioration segment",
     "segments_hit": {"recent_deterioration": 4_200},
     "accounts": 4_200, "cost": 50_400.0, "recovered": 6_140_000.0,
     "recovered_per_rupee_cost": 121.8,
     "note": "The best-returning targeted campaign run so far."},
]

# Six months of forecast against actual. Consistently over — the target being
# set each month is not reachable at current effort, which is a different
# finding from the forecast being noisy.
FORECAST_HISTORY: list[dict] = [
    {"month": "2026-03", "forecast": 21_400_000, "actual": 18_900_000},
    {"month": "2026-04", "forecast": 21_900_000, "actual": 19_400_000},
    {"month": "2026-05", "forecast": 22_600_000, "actual": 20_100_000},
    {"month": "2026-06", "forecast": 22_100_000, "actual": 19_600_000},
    {"month": "2026-07", "forecast": 23_000_000, "actual": 21_050_000},
    {"month": "2026-08", "forecast": 22_800_000, "actual": 20_400_000},
]
