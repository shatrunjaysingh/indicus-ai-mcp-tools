"""The temporarily disconnected book, scored for recovery priority.

Use case 2 combines ten inputs into one number — outstanding, days since
disconnection, payment history, meter status, site survey, restoration history,
consumption pattern, notices, category and location — and ranks a field
programme on it.

The number is **recoverable amount x recovery probability**, and both halves
matter. The client's own example makes the point: ₹85,000 at 420 days with a
suspected restoration scores 95, while ₹18,000 at 90 days with none scores 28.
Neither the balance nor the age gets you there on its own.

Recoverable amount is not the ledger balance. Statute-barred arrears under
§56(2), disputed amounts, and periods the premises was demonstrably empty come
off it first — a priority built on the ledger figure sends teams after money
the DISCOM cannot collect and, in the barred case, is not entitled to.

40,000 TD accounts, generated deterministically and cached like the collection
book. Individual accounts materialise; aggregates are exact.
"""

from __future__ import annotations

import heapq
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

SEED = 20260902
POPULATION = 40_000
MATERIALISE = 20_000

DIVISIONS = ["Pune East", "Pune West", "Pune Rural"]

# Field capacity for TD recovery specifically. Smaller than general collection
# visits: these are older cases needing a survey, not a doorstep reminder.
FIELD_CAPACITY_PER_MONTH = 2_500
FIELD_COST_PER_VISIT = 340.0

CATEGORIES = {
    "LT-1 Domestic":     {"share": 0.61, "mean_due": 14_000, "sd": 9_000},
    "LT-2 Commercial":   {"share": 0.24, "mean_due": 62_000, "sd": 48_000},
    "HT Industrial":     {"share": 0.03, "mean_due": 340_000, "sd": 260_000},
    "LT-5 Agricultural": {"share": 0.12, "mean_due": 21_000, "sd": 14_000},
}

# What a site survey found, and how often. `not_surveyed` is the largest group
# because most TD accounts have never been visited — which is the problem the
# ranking exists to fix.
SURVEY_OUTCOMES = {
    "not_surveyed":        0.52,
    "occupied_trading":    0.13,
    "occupied_residential": 0.16,
    "locked_vacant":       0.13,
    "premises_demolished": 0.06,
}

METER_STATES = {
    "in_situ_sealed": 0.44,
    "removed":        0.38,
    "burnt":          0.06,
    "tampered":       0.07,
    "missing":        0.05,
}


@dataclass
class TDAccount:
    consumer_no: str
    division: str
    subdivision: str
    category: str
    outstanding: float
    td_days: int
    executed_and_acknowledged: bool
    pre_td_on_time_ratio: float
    meter_status: str
    survey_finding: str
    consumption_after_td_kwh: int
    restoration_suspected: bool
    notices_served: int
    notices_responded: int
    statute_barred_amount: float
    disputed_amount: float
    recoverable_amount: float = 0.0
    recovery_probability: float = 0.0
    recovery_priority: int = 0
    factors: dict = field(default_factory=dict)
    pd_recommended: bool = False
    # --- illegal restoration (use case 5) ---------------------------------
    # Whether the consumption after disconnection is an actual meter read or a
    # provisional bill. A case built on estimated reads is not a case, and the
    # billing system generates them for disconnected consumers routinely.
    consumption_basis: str = "actual"
    restart_period: str | None = None
    pre_td_monthly_avg: int = 0
    payment_near_restart: bool = False
    restoration_risk: int = 0
    restoration_factors: dict = field(default_factory=dict)
    restoration_blocked_by: str | None = None


def _recoverable(a: TDAccount) -> float:
    """What can actually be collected, before any probability is applied.

    The ledger balance is the wrong starting point. Amounts first shown as due
    more than two years ago are barred from recovery as arrears under §56(2)
    of the Electricity Act 2003, disputed sums may be wrong, and a demolished
    premises has no occupier to bill for the period after it went.
    """
    net = a.outstanding - a.statute_barred_amount - a.disputed_amount
    if a.survey_finding == "premises_demolished":
        net *= 0.15  # only what predates the demolition is arguable
    return round(max(0.0, net), 2)


def _probability(a: TDAccount) -> tuple[float, dict]:
    """Probability of recovering the recoverable amount, and what drove it.

    Returned with the factors because a field programme ranked on an opaque
    score cannot be argued with, and the first question at a recovery review is
    always why this consumer and not that one.
    """
    f: dict[str, float] = {}

    # A live connection after a confirmed disconnection is the strongest
    # positive signal in this whole model: someone is there, using power, with
    # something to lose by not settling.
    f["restoration_suspected"] = 0.30 if a.restoration_suspected else 0.0

    # The survey outranks every desk inference. An empty premises is not
    # recoverable at any balance, and this is where a balance-ranked programme
    # wastes most of its visits.
    f["site_survey"] = {
        "occupied_trading": 0.26,
        "occupied_residential": 0.18,
        "not_surveyed": 0.0,
        "locked_vacant": -0.30,
        "premises_demolished": -0.45,
    }[a.survey_finding]

    # Whether they paid before the disconnection separates a consumer who fell
    # into difficulty from one who never paid.
    f["pre_td_payment_history"] = round((a.pre_td_on_time_ratio - 0.45) * 0.34, 4)

    # Age cuts both ways and is weaker than either of the two above. Long TD
    # with no restoration and no consumption usually means the premises emptied.
    f["td_age"] = round(-min(a.td_days, 900) / 900 * 0.20, 4)

    f["notice_response"] = round(
        (a.notices_responded / a.notices_served - 0.5) * 0.14, 4
    ) if a.notices_served else 0.0

    f["meter_status"] = {
        "in_situ_sealed": 0.04, "removed": -0.02, "burnt": -0.06,
        "tampered": 0.05,  # tampering means someone was there and is assessable
        "missing": -0.08,
    }[a.meter_status]

    if not a.executed_and_acknowledged:
        # The disconnection may never have happened, so consumption after it
        # proves nothing and the case may not exist.
        f["execution_unproven"] = -0.18

    p = 0.34 + sum(f.values())
    return round(max(0.01, min(0.96, p)), 4), f


# Expected-recovery cut-points of the book, filled once the population exists.
# Priority is a percentile against these, not an absolute rupee scale.
_PERCENTILES: list[float] = []


def _priority(recoverable: float, probability: float) -> int:
    """Recovery priority, 0-100, as a percentile of the book.

    An absolute rupee scale was tried first and does not survive contact with
    the client's own example: their ₹85,000 case scores 95 and their ₹18,000
    vacant case scores 28, which are not positions on a rupee axis — they are
    positions in a queue. 95 means "work this before 95% of the book", and that
    is what a field programme actually needs, because the question is never how
    much an account is worth in the abstract but whether it beats the next one.

    A percentile also self-calibrates. A DISCOM whose TD book is ten times
    larger gets the same 0-100 spread rather than everything pinning at 100.
    """
    expected = recoverable * probability
    if not _PERCENTILES:
        return 0
    lo, hi = 0, len(_PERCENTILES)
    while lo < hi:
        mid = (lo + hi) // 2
        if _PERCENTILES[mid] < expected:
            lo = mid + 1
        else:
            hi = mid
    return int(round(lo / len(_PERCENTILES) * 100))


def _restoration_risk(a: TDAccount) -> tuple[int, dict, str | None]:
    """Risk that supply was restored without authorisation, 0-100.

    The four figures the case rests on are the disconnection date, the expected
    consumption, the actual consumption after it, and the gap. Everything below
    is about what could explain that gap other than someone reconnecting.

    Two conditions cap the score outright rather than reducing it, because they
    do not make restoration less likely — they make the *case* unavailable:

    A disconnection with no field acknowledgement may never have happened. Then
    consumption afterwards proves nothing, there is no offence, and the finding
    is a process failure in the DISCOM's own records.

    Consumption on estimated reads is not consumption. The billing system
    generates provisional bills for disconnected consumers, and a screening run
    that counts them accuses people of using power that nobody measured.
    """
    if a.consumption_after_td_kwh <= 0:
        return 0, {}, None

    blocked = None
    if not a.executed_and_acknowledged:
        blocked = "disconnection not confirmed executed in the field"
    elif a.consumption_basis == "estimated":
        blocked = "consumption is provisional billing, not an actual read"

    f: dict[str, float] = {}
    # Size of the gap against what the premises used before. Resuming at close
    # to the old level is the signature of a physical reconnection; a trickle
    # is more consistent with a metering or reading error.
    if a.pre_td_monthly_avg > 0:
        ratio = a.consumption_after_td_kwh / a.pre_td_monthly_avg
        f["consumption_vs_pre_td"] = round(min(1.0, ratio) * 46, 1)
    else:
        f["consumption_vs_pre_td"] = 20.0

    f["confirmed_execution"] = 18.0 if a.executed_and_acknowledged else 0.0
    f["actual_read"] = 14.0 if a.consumption_basis == "actual" else 0.0

    f["site_evidence"] = {
        "occupied_trading": 16.0, "occupied_residential": 12.0,
        "not_surveyed": 0.0, "locked_vacant": -14.0,
        "premises_demolished": -20.0,
    }[a.survey_finding]

    # Meter removed at disconnection and consumption recorded since is close to
    # impossible without interference; in-situ metering can drift or be misread.
    f["meter_state"] = {"removed": 10.0, "missing": 8.0, "tampered": 9.0,
                        "burnt": 2.0, "in_situ_sealed": 0.0}[a.meter_status]

    # A payment just before consumption resumes points hard at an authorised
    # restoration the ledger has not caught up with.
    if a.payment_near_restart:
        f["payment_before_restart"] = -34.0

    score = int(round(max(0.0, min(100.0, sum(f.values())))))
    if blocked:
        # Capped, not zeroed: it is still worth looking at, but it cannot carry
        # an enforcement action until the blocking fact is resolved.
        score = min(score, 30)
    return score, {k: v for k, v in f.items() if v}, blocked


def _generate() -> tuple[list[TDAccount], dict]:
    rng = random.Random(SEED)
    cats = list(CATEGORIES)
    cat_w = [CATEGORIES[c]["share"] for c in cats]
    surveys = list(SURVEY_OUTCOMES)
    survey_w = list(SURVEY_OUTCOMES.values())
    meters = list(METER_STATES)
    meter_w = list(METER_STATES.values())

    heap: list[tuple[int, int, TDAccount]] = []
    built: list[TDAccount] = []
    agg = {
        "accounts": 0, "outstanding": 0.0, "recoverable": 0.0, "expected": 0.0,
        "restoration_suspected": 0, "never_surveyed": 0, "pd_recommended": 0,
        "by_band": {"85-100": 0, "60-84": 0, "35-59": 0, "15-34": 0, "0-14": 0},
        "restoration": {"with_consumption": 0, "risk_70_plus": 0,
                        "blocked_execution": 0, "blocked_estimated": 0,
                        "payment_near_restart": 0},
        "by_division": {d: {"accounts": 0, "recoverable": 0.0, "expected": 0.0}
                        for d in DIVISIONS},
    }

    for i in range(POPULATION):
        cat = rng.choices(cats, weights=cat_w)[0]
        spec = CATEGORIES[cat]
        due = max(2_000.0, rng.gauss(spec["mean_due"], spec["sd"]))
        td_days = rng.choices(
            [45, 90, 150, 240, 330, 420, 560, 720, 880],
            weights=[14, 16, 15, 14, 12, 10, 8, 6, 5])[0]
        survey = rng.choices(surveys, weights=survey_w)[0]
        meter = rng.choices(meters, weights=meter_w)[0]
        executed = rng.random() > 0.09
        # Restoration is only meaningful where the disconnection actually
        # happened and the premises is not empty.
        occupied = survey in ("occupied_trading", "occupied_residential")
        restored = executed and rng.random() < (0.34 if occupied else 0.06)
        consumption = rng.randint(120, 1400) if restored else (
            rng.randint(0, 40) if rng.random() < 0.2 else 0)
        notices = rng.choices([0, 1, 2, 3, 4], weights=[18, 24, 26, 20, 12])[0]
        responded = rng.randint(0, notices) if notices and rng.random() < 0.4 else 0
        # Older than two years and the earliest slice falls outside §56(2).
        barred = round(due * rng.uniform(0.25, 0.6), 2) if td_days > 730 else 0.0
        disputed = round(due * rng.uniform(0.1, 0.5), 2) if rng.random() < 0.06 else 0.0

        a = TDAccount(
            consumer_no=f"TD-{500000 + i}",
            division=rng.choices(DIVISIONS, weights=[0.38, 0.29, 0.33])[0],
            subdivision=rng.choice(["Kharadi", "Hadapsar", "Wanowrie", "Baner",
                                    "Uruli", "Ranjangaon"]),
            category=cat, outstanding=round(due, 2), td_days=td_days,
            executed_and_acknowledged=executed,
            pre_td_on_time_ratio=round(min(1.0, max(0.0, rng.betavariate(2.4, 2.0))), 3),
            meter_status=meter, survey_finding=survey,
            consumption_after_td_kwh=consumption,
            restoration_suspected=restored,
            notices_served=notices, notices_responded=responded,
            statute_barred_amount=barred, disputed_amount=disputed,
        )
        a.pre_td_monthly_avg = rng.randint(180, 1600)
        a.consumption_basis = (
            "estimated" if consumption > 0 and rng.random() < 0.22 else "actual")
        a.restart_period = (
            f"2026-{rng.randint(1, 8):02d}" if consumption > 0 else None)
        # An authorised reconnection whose ledger entry lagged. Common enough
        # that a screening run which ignores it accuses paying consumers.
        a.payment_near_restart = consumption > 0 and rng.random() < 0.17
        a.recoverable_amount = _recoverable(a)
        a.recovery_probability, a.factors = _probability(a)
        (a.restoration_risk, a.restoration_factors,
         a.restoration_blocked_by) = _restoration_risk(a)
        built.append(a)

    # The distribution has to exist before anything can be a percentile of it.
    global _PERCENTILES
    _PERCENTILES = sorted(x.recoverable_amount * x.recovery_probability
                          for x in built)

    for i, a in enumerate(built):
        a.recovery_priority = _priority(a.recoverable_amount, a.recovery_probability)
        # PD conversion: nothing worth recovering and nobody there.
        a.pd_recommended = (
            a.recovery_priority < 15
            and a.survey_finding in ("locked_vacant", "premises_demolished")
            and a.td_days > 365
        )

        agg["accounts"] += 1
        agg["outstanding"] += a.outstanding
        agg["recoverable"] += a.recoverable_amount
        agg["expected"] += a.recoverable_amount * a.recovery_probability
        agg["restoration_suspected"] += int(a.restoration_suspected)
        agg["never_surveyed"] += int(a.survey_finding == "not_surveyed")
        agg["pd_recommended"] += int(a.pd_recommended)
        band = ("85-100" if a.recovery_priority >= 85 else
                "60-84" if a.recovery_priority >= 60 else
                "35-59" if a.recovery_priority >= 35 else
                "15-34" if a.recovery_priority >= 15 else "0-14")
        agg["by_band"][band] += 1
        if a.consumption_after_td_kwh > 0:
            r = agg["restoration"]
            r["with_consumption"] += 1
            if a.restoration_risk >= 70:
                r["risk_70_plus"] += 1
            if a.restoration_blocked_by and "executed" in a.restoration_blocked_by:
                r["blocked_execution"] += 1
            if a.restoration_blocked_by and "provisional" in a.restoration_blocked_by:
                r["blocked_estimated"] += 1
            if a.payment_near_restart:
                r["payment_near_restart"] += 1
        d = agg["by_division"][a.division]
        d["accounts"] += 1
        d["recoverable"] += a.recoverable_amount
        d["expected"] += a.recoverable_amount * a.recovery_probability

        if len(heap) < MATERIALISE:
            heapq.heappush(heap, (a.recovery_priority, i, a))
        elif a.recovery_priority > heap[0][0]:
            heapq.heapreplace(heap, (a.recovery_priority, i, a))

    ranked = [x for _p, _i, x in sorted(heap, key=lambda t: (-t[0], t[1]))]
    return ranked, agg


def _load() -> tuple[list[TDAccount], dict]:
    key = f"{SEED}-{POPULATION}-{MATERIALISE}-v3-restoration"
    cache = Path(__file__).resolve().parent / "_td_cache.json"
    if cache.exists():
        try:
            blob = json.loads(cache.read_text())
            if blob.get("key") == key:
                global _PERCENTILES
                _PERCENTILES = blob["percentiles"]
                return [TDAccount(**a) for a in blob["ranked"]], blob["agg"]
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    ranked, agg = _generate()
    try:
        cache.write_text(json.dumps({
            "key": key, "ranked": [asdict(a) for a in ranked], "agg": agg,
            # Sampled: forty thousand cut-points is a large cache for a
            # resolution nobody uses. Every 20th preserves percentile accuracy
            # to well under one point.
            "percentiles": _PERCENTILES[::20]}))
    except OSError:
        pass
    return ranked, agg


RANKED, TOTALS = _load()
BY_NO: dict[str, TDAccount] = {a.consumer_no: a for a in RANKED}


def stream_book():
    """Regenerate the whole TD book for a complete export."""
    ranked, _ = _generate()
    yield from ranked
