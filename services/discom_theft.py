"""Anomaly screening across the metered base, for intelligence-led inspection.

Use case 3. Seven signals, one score, and a ranked inspection list — the point
being to stop inspecting at random.

Two design decisions carry most of the value here, and both are refusals.

**Feeder and DT loss never enter a consumer's score.** High loss on a feeder
tells you which area to look at; it says nothing about which consumer on it is
responsible, and letting it contribute means every consumer on a lossy feeder
inherits suspicion from their neighbours. It is returned as area context and
kept out of the arithmetic.

**A documented explanation suppresses the score.** A sanctioned load surrender,
an approved seasonal shutdown, a recorded meter change — these produce exactly
the consumption profile an anomaly model flags, and a screening run that cannot
see them sends enforcement teams to businesses that filed the right paperwork.
That is not a false positive to be tuned away later; it is the single most
damaging thing this system can do.

250,000 metered consumers — a division-scale screening run rather than the
whole utility, which is how these are operated in practice.
"""

from __future__ import annotations

import heapq
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

SEED = 20260903
POPULATION = 250_000
MATERIALISE = 20_000

# What an enforcement wing can actually inspect in a month. The whole argument
# for scoring is that this number is small against the base.
INSPECTION_CAPACITY_PER_MONTH = 1_800
INSPECTION_COST = 2_400.0

DIVISIONS = ["Pune East", "Pune West", "Pune Rural"]

CATEGORIES = {
    "LT-1 Domestic":     0.70,
    "LT-2 Commercial":   0.19,
    "HT Industrial":     0.02,
    "LT-5 Agricultural": 0.09,
}

# Reasons a consumption profile can look wrong and be entirely legitimate.
# Weighted so that most anomalies have no documented cause — if they all did,
# the screening would have nothing to find and the demo would prove nothing.
DOCUMENTED_REASONS = {
    None: 0.80,
    "sanctioned load surrender": 0.07,
    "approved seasonal shutdown": 0.05,
    "meter replaced on work order": 0.04,
    "tariff category change": 0.02,
    "premises vacant, notified": 0.02,
}

# Historical inspection outcomes, for the argument the client is making.
INSPECTION_HISTORY = [
    {"period": "2026-Q1", "method": "random", "inspections": 1_800,
     "theft_or_unauthorised_found": 121, "hit_rate": 0.067,
     "assessed_value": 14_800_000.0,
     "note": "Route-based selection. One inspection in fifteen found anything."},
    {"period": "2026-Q2", "method": "random", "inspections": 1_750,
     "theft_or_unauthorised_found": 108, "hit_rate": 0.062,
     "assessed_value": 12_100_000.0},
    {"period": "2026-Q3", "method": "score-led pilot", "inspections": 400,
     "theft_or_unauthorised_found": 143, "hit_rate": 0.358,
     "assessed_value": 21_400_000.0,
     "note": "Pilot on the top of the anomaly ranking. Hit rate rose from "
             "6.7% to 35.8%, and a quarter of the inspections produced more "
             "assessed value than a full quarter of random ones."},
]


@dataclass
class ScreenedConsumer:
    consumer_no: str
    division: str
    subdivision: str
    category: str
    connected_load_kw: float
    sanctioned_load_kw: float
    feeder: str
    # --- the seven signals -------------------------------------------------
    consumption_drop_pct: float          # sudden reduction
    load_factor_ratio: float             # consumption against connected load
    tamper_events_12m: int               # repeated meter tampering
    night_day_ratio: float               # unusual night/day pattern
    peer_deviation_pct: float            # against similar consumers
    bypass_indicator: bool               # physical, from a prior survey
    # --- context, deliberately not scored ----------------------------------
    feeder_loss_pct: float
    # --- what makes it innocent -------------------------------------------
    documented_reason: str | None
    anomaly_risk: int = 0
    # What the score would have been without the documented
    # explanation. Kept because it is the number that shows what the
    # check is worth: an inspection avoided at a business that filed
    # the right paperwork.
    risk_before_suppression: int = 0
    signals_fired: list[str] = field(default_factory=list)
    signal_scores: dict = field(default_factory=dict)
    recommended: str = ""
    suppressed_by: str | None = None


def _score(c: ScreenedConsumer) -> tuple[int, list[str], dict, str, str | None, int]:
    """Anomaly risk 0-100, the signals that fired, and what each contributed.

    Weighted so that physical and metering evidence outranks statistical
    comparison. A case built mainly on "consumes less than similar consumers"
    cannot reach the inspection band on its own, because peer cohorts are never
    truly comparable and a score that lets them dominate produces inspections
    at the homes of people with small families and efficient appliances.
    """
    parts: dict[str, float] = {}
    fired: list[str] = []

    # Physical evidence. Worth the most, and rare.
    if c.bypass_indicator:
        parts["bypass_indicator"] = 34.0
        fired.append("possible bypass seen at a previous visit")
    if c.tamper_events_12m >= 3:
        parts["repeated_tampering"] = 26.0
        fired.append(f"{c.tamper_events_12m} tamper events with no work order")
    elif c.tamper_events_12m == 2:
        parts["repeated_tampering"] = 15.0
        fired.append("2 tamper events with no work order")
    elif c.tamper_events_12m == 1:
        parts["repeated_tampering"] = 6.0
        fired.append("1 tamper event with no work order")

    # Metering patterns.
    if c.consumption_drop_pct >= 55:
        parts["sudden_drop"] = 22.0
        fired.append(f"consumption down {c.consumption_drop_pct:.0f}%")
    elif c.consumption_drop_pct >= 35:
        parts["sudden_drop"] = 13.0
        fired.append(f"consumption down {c.consumption_drop_pct:.0f}%")

    if c.load_factor_ratio <= 0.18:
        parts["load_inconsistency"] = 16.0
        fired.append(
            f"consumption implies {c.load_factor_ratio:.2f} of connected load")
    elif c.load_factor_ratio <= 0.30:
        parts["load_inconsistency"] = 8.0
        fired.append("consumption low against connected load")

    if c.night_day_ratio >= 2.4:
        parts["night_day"] = 10.0
        fired.append(f"night/day ratio {c.night_day_ratio:.1f}")

    # The weakest signal, deliberately capped low. A prompt to look, never a
    # reason to accuse.
    if c.peer_deviation_pct <= -55:
        parts["peer_deviation"] = 9.0
        fired.append(f"{abs(c.peer_deviation_pct):.0f}% below cohort median")
    elif c.peer_deviation_pct <= -35:
        parts["peer_deviation"] = 5.0
        fired.append("below cohort median")

    # Unauthorised excess load is a §126 matter, not theft, and is scored
    # separately so the report can say which it is.
    if c.connected_load_kw > c.sanctioned_load_kw * 1.25:
        parts["excess_load"] = 7.0
        fired.append(
            f"{c.connected_load_kw:.0f} kW connected against "
            f"{c.sanctioned_load_kw:.0f} kW sanctioned")

    before = int(round(min(100.0, sum(parts.values()))))
    raw = min(100.0, sum(parts.values()))

    # A documented explanation removes the signals it explains rather than
    # discounting the total, so the remaining score reflects what is still
    # unexplained.
    suppressed = None
    if c.documented_reason:
        explains = {
            "sanctioned load surrender": ("sudden_drop", "load_inconsistency",
                                          "peer_deviation", "excess_load"),
            "approved seasonal shutdown": ("sudden_drop", "peer_deviation",
                                           "night_day"),
            "meter replaced on work order": ("repeated_tampering", "sudden_drop"),
            "tariff category change": ("peer_deviation", "excess_load"),
            "premises vacant, notified": ("sudden_drop", "load_inconsistency",
                                          "peer_deviation"),
        }[c.documented_reason]
        removed = [k for k in parts if k in explains]
        if removed:
            suppressed = c.documented_reason
            for k in removed:
                parts.pop(k)
            fired = [f for f in fired] + [f"explained: {c.documented_reason}"]
            raw = min(100.0, sum(parts.values()))

    score = int(round(raw))
    if score >= 70:
        action = "INSPECT_URGENT"
    elif score >= 45:
        action = "INSPECT_ROUTINE"
    elif score >= 25:
        action = "METER_TEST"
    elif score >= 10:
        action = "MONITOR"
    else:
        action = "NO_ACTION"
    return (score, fired, {k: round(v, 1) for k, v in parts.items()},
            action, suppressed, before)


def _generate() -> tuple[list[ScreenedConsumer], dict]:
    rng = random.Random(SEED)
    cats = list(CATEGORIES)
    cat_w = list(CATEGORIES.values())
    reasons = list(DOCUMENTED_REASONS)
    reason_w = list(DOCUMENTED_REASONS.values())

    heap: list[tuple[int, int, ScreenedConsumer]] = []
    agg = {
        "screened": 0,
        "by_action": {"INSPECT_URGENT": 0, "INSPECT_ROUTINE": 0,
                      "METER_TEST": 0, "MONITOR": 0, "NO_ACTION": 0},
        "suppressed_by_documentation": 0,
        "would_have_been_flagged": 0,
        "bypass_indicator": 0,
        "repeated_tampering": 0,
        "by_division": {d: {"screened": 0, "inspect": 0} for d in DIVISIONS},
    }

    for i in range(POPULATION):
        cat = rng.choices(cats, weights=cat_w)[0]
        sanctioned = {"LT-1 Domestic": rng.choice([1.0, 2.0, 3.0, 4.0, 5.0]),
                      "LT-2 Commercial": rng.choice([8.0, 15.0, 30.0, 45.0]),
                      "HT Industrial": rng.choice([100.0, 250.0, 500.0]),
                      "LT-5 Agricultural": rng.choice([5.0, 7.5, 10.0])}[cat]
        excess = rng.random() < 0.08
        connected = sanctioned * (rng.uniform(1.3, 1.9) if excess else
                                  rng.uniform(0.85, 1.05))
        anomalous = rng.random() < 0.11
        c = ScreenedConsumer(
            consumer_no=f"MS-{800000 + i}",
            division=rng.choices(DIVISIONS, weights=[0.40, 0.32, 0.28])[0],
            subdivision=rng.choice(["Kharadi", "Hadapsar", "Wanowrie", "Baner",
                                    "Uruli", "Ranjangaon"]),
            category=cat,
            connected_load_kw=round(connected, 1),
            sanctioned_load_kw=sanctioned,
            feeder=f"F-{rng.randint(1, 28):02d}",
            consumption_drop_pct=round(
                rng.uniform(35, 85) if anomalous else rng.uniform(-15, 25), 1),
            load_factor_ratio=round(
                rng.uniform(0.05, 0.28) if anomalous else rng.uniform(0.3, 0.9), 3),
            tamper_events_12m=rng.choices(
                [0, 1, 2, 3, 4],
                weights=[88, 7, 3, 1.5, 0.5] if not anomalous
                else [40, 22, 20, 12, 6])[0],
            night_day_ratio=round(
                rng.uniform(1.8, 3.4) if anomalous else rng.uniform(0.4, 1.6), 2),
            peer_deviation_pct=round(
                rng.uniform(-75, -30) if anomalous else rng.uniform(-30, 40), 1),
            bypass_indicator=anomalous and rng.random() < 0.06,
            feeder_loss_pct=round(rng.uniform(8, 31), 1),
            documented_reason=rng.choices(reasons, weights=reason_w)[0],
        )
        (c.anomaly_risk, c.signals_fired, c.signal_scores,
         c.recommended, c.suppressed_by, c.risk_before_suppression) = _score(c)

        agg["screened"] += 1
        agg["by_action"][c.recommended] += 1
        agg["bypass_indicator"] += int(c.bypass_indicator)
        agg["repeated_tampering"] += int(c.tamper_events_12m >= 2)
        if c.suppressed_by:
            agg["suppressed_by_documentation"] += 1
            if c.risk_before_suppression >= 45:
                agg["would_have_been_flagged"] += 1
        d = agg["by_division"][c.division]
        d["screened"] += 1
        if c.recommended.startswith("INSPECT"):
            d["inspect"] += 1

        if len(heap) < MATERIALISE:
            heapq.heappush(heap, (c.anomaly_risk, i, c))
        elif c.anomaly_risk > heap[0][0]:
            heapq.heapreplace(heap, (c.anomaly_risk, i, c))

    ranked = [x for _s, _i, x in sorted(heap, key=lambda t: (-t[0], t[1]))]
    return ranked, agg


def _load() -> tuple[list[ScreenedConsumer], dict]:
    key = f"{SEED}-{POPULATION}-{MATERIALISE}-v2"
    cache = Path(__file__).resolve().parent / "_theft_cache.json"
    if cache.exists():
        try:
            blob = json.loads(cache.read_text())
            if blob.get("key") == key:
                return [ScreenedConsumer(**a) for a in blob["ranked"]], blob["agg"]
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    ranked, agg = _generate()
    try:
        cache.write_text(json.dumps({
            "key": key, "ranked": [asdict(a) for a in ranked], "agg": agg}))
    except OSError:
        pass
    return ranked, agg


RANKED, TOTALS = _load()
BY_NO: dict[str, ScreenedConsumer] = {a.consumer_no: a for a in RANKED}


def stream_book():
    ranked, _ = _generate()
    yield from ranked
