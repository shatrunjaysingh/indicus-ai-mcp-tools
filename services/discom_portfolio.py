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

24,000 consumers, generated deterministically. Not ten lakh — the architecture
is what scales, and a fixture that claims a scale it does not have is the kind
of thing a client checks.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

SEED = 20260901
POPULATION = 24_000

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
    segment: str = ""
    payment_probability: float = 0.0
    expected_recovery: float = 0.0
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


def _build() -> list[Account]:
    rng = random.Random(SEED)
    out: list[Account] = []
    cats = list(_MIX)
    weights = [_MIX[c]["share"] for c in cats]

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
        acc = Account(
            consumer_no=f"{'DL' if cat.startswith('LT-1') else 'CM' if cat.startswith('LT-2') else 'IN' if cat.startswith('HT') else 'AG'}-{700000 + i}",
            division=rng.choices(DIVISIONS, weights=[0.42, 0.33, 0.25])[0],
            category=cat,
            outstanding=round(due, 2),
            unpaid_cycles=unpaid,
            days_since_last_payment=min(900, unpaid * 30 + rng.randint(0, 45)),
            on_time_ratio=round(on_time, 3),
            notices_ignored=notices,
            broken_promises=broken,
            connection_age_months=age,
            has_open_dispute=rng.random() < 0.043,
            consumption_last_period=0 if vacated else rng.randint(40, 900),
        )
        acc.segment = _segment_for(acc)
        acc.payment_probability, acc.features = _score(acc)
        # The figure a campaign is actually ranked on. Neither probability nor
        # amount alone: a certain ₹800 and an unlikely ₹90,000 are both worth
        # less than a probable ₹40,000.
        acc.expected_recovery = round(acc.outstanding * acc.payment_probability, 2)
        out.append(acc)
    return out


BOOK: list[Account] = _build()
BY_NO: dict[str, Account] = {a.consumer_no: a for a in BOOK}


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
