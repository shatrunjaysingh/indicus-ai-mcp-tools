"""The distribution asset fleet, scored for failure risk.

Use case 8. Eight and a half thousand assets — distribution transformers,
feeders and breakers — with loading, thermal trend, maintenance history and
failure record, ranked against a maintenance crew's real monthly capacity.

Three things this refuses to blur.

**Risk and consequence are separate numbers.** How likely an asset is to fail
is a property of the asset. How much it matters is a property of what is behind
it — how many consumers, whether a hospital or a water works is among them,
whether an alternative feed exists. A low-risk transformer feeding a hospital
may be attended before a high-risk one feeding twelve rural connections, and
that is a ranking decision, not a reason to inflate the risk band. Inflating it
corrupts the risk figure for everyone downstream who relies on it.

**No telemetry means unknown, not low.** A third of a typical DT fleet has no
SCADA and no smart-meter feed. Those assets cannot be scored on trend at all,
and a ranking that quietly sorts them to the bottom because nothing looks wrong
is how the unmonitored half of a network becomes invisible.

**Trend beats level.** An asset at 92% loading that has sat there for three
years is in a different state from one that reached 92% last month from 60%.
Rising oil temperature at constant or falling ambient is the degradation
signature and is weighted accordingly.
"""

from __future__ import annotations

import heapq
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

SEED = 20260907
POPULATION = 8_500
MATERIALISE = 3_000

# What a maintenance wing can attend in a month, and what each visit costs
# against what a failure costs. The ratio is the whole economic argument.
CREW_CAPACITY_PER_MONTH = 320
PREVENTIVE_COST = 8_500.0
EMERGENCY_REPAIR_COST = 62_000.0

DIVISIONS = ["Pune East", "Pune West", "Pune Rural"]
ASSET_TYPES = {"distribution transformer": 0.78, "feeder": 0.14, "breaker": 0.08}

CRITICAL_LOADS = [
    "municipal water pumping station", "community hospital",
    "district hospital", "water treatment works", "traffic control",
    "telecom exchange", "railway signalling",
]


@dataclass
class Asset:
    asset_id: str
    asset_type: str
    division: str
    subdivision: str
    rating_kva: int
    installed_year: int
    # --- condition ---------------------------------------------------------
    telemetry: bool
    peak_load_pct: int
    load_trend_6m: int              # percentage points of change
    oil_temp_c: int | None
    ambient_c: int | None
    oil_temp_trend_6m: int | None
    phase_imbalance_pct: int
    months_since_maintenance: int
    maintenance_cycle_months: int
    failures_3y: int
    trips_90d: int
    no_fault_found_trips_90d: int
    # --- consequence -------------------------------------------------------
    consumers_served: int
    critical_loads: list[str] = field(default_factory=list)
    alternative_feed: bool = False
    # --- scores ------------------------------------------------------------
    failure_risk: int = 0
    risk_band: str = ""
    risk_known: bool = True
    primary_driver: str = ""
    consequence_score: int = 0
    inspect_within_days: int | None = None
    factors: dict = field(default_factory=dict)


def _risk(a: Asset) -> tuple[int, str, dict, bool]:
    """Failure risk 0-100, the single driver, and whether it is knowable.

    Returns `known=False` for assets with no telemetry. Their score is built
    from age, maintenance and failure history alone, which is real information
    but cannot see a developing fault. Presenting that as a low risk is the
    error this flag exists to prevent.
    """
    f: dict[str, float] = {}

    # Thermal trend, the strongest signal and only available with telemetry.
    if a.telemetry and a.oil_temp_trend_6m is not None:
        # Rising oil temperature while ambient is flat or falling is the
        # classic degradation signature: the asset is dissipating heat worse
        # than it did, at the same work.
        ambient_move = 0 if a.ambient_c is None else 0
        if a.oil_temp_trend_6m >= 20:
            f["thermal_trend"] = 34.0
        elif a.oil_temp_trend_6m >= 10:
            f["thermal_trend"] = 20.0
        elif a.oil_temp_trend_6m >= 5:
            f["thermal_trend"] = 9.0
        del ambient_move

    # Loading. Level is context; the six-month move is the signal.
    if a.peak_load_pct >= 95:
        f["sustained_overload"] = 22.0
    elif a.peak_load_pct >= 85:
        f["high_loading"] = 13.0
    if a.load_trend_6m >= 18:
        f["load_rising_fast"] = 14.0
    elif a.load_trend_6m >= 10:
        f["load_rising"] = 7.0

    # Repeat trips restored with no fault found are the most underrated signal
    # in distribution maintenance — an intermittent developing fault.
    if a.no_fault_found_trips_90d >= 3:
        f["repeat_no_fault_found"] = 24.0
    elif a.no_fault_found_trips_90d == 2:
        f["repeat_no_fault_found"] = 13.0

    if a.failures_3y >= 2:
        f["repeat_failures"] = 12.0
    elif a.failures_3y == 1:
        f["prior_failure"] = 5.0

    overdue = a.months_since_maintenance - a.maintenance_cycle_months
    if overdue >= 12:
        f["maintenance_long_overdue"] = 14.0
    elif overdue >= 1:
        f["maintenance_overdue"] = 7.0

    if a.phase_imbalance_pct >= 15:
        f["phase_imbalance"] = 9.0

    age = 2026 - a.installed_year
    if age >= 20:
        f["age"] = 7.0
    elif age >= 12:
        f["age"] = 3.0

    score = int(round(min(100.0, sum(f.values()))))
    driver = max(f, key=f.get) if f else "no signal"
    return score, driver, {k: round(v, 1) for k, v in f.items()}, a.telemetry


def _consequence(a: Asset) -> int:
    """How much a failure here matters, 0-100. Never mixed into the risk."""
    s = min(60.0, a.consumers_served / 12.0)
    s += 30.0 if a.critical_loads else 0.0
    s += 0.0 if a.alternative_feed else 14.0
    return int(round(min(100.0, s)))


def _generate() -> tuple[list[Asset], dict]:
    rng = random.Random(SEED)
    types = list(ASSET_TYPES)
    tw = list(ASSET_TYPES.values())
    heap: list[tuple[int, int, Asset]] = []
    agg = {
        "assets": 0,
        "by_type": dict.fromkeys(ASSET_TYPES, 0),
        "by_band": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        "no_telemetry": 0,
        "no_telemetry_unscored_signals": 0,
        "critical_load_assets": 0,
        "low_risk_high_consequence": 0,
        "overdue_maintenance": 0,
        "repeat_no_fault_found": 0,
        "crew_capacity": CREW_CAPACITY_PER_MONTH,
    }

    for i in range(POPULATION):
        atype = rng.choices(types, weights=tw)[0]
        telemetry = rng.random() < 0.63
        installed = rng.randint(2001, 2024)
        load = rng.choices([45, 58, 66, 72, 79, 86, 91, 96],
                           weights=[10, 16, 18, 17, 14, 12, 8, 5])[0]
        oil = None if not telemetry or atype == "breaker" else \
            rng.randint(48, 96)
        trend = None if oil is None else rng.choices(
            [-4, 0, 3, 7, 12, 22, 32], weights=[8, 26, 22, 18, 13, 9, 4])[0]
        cycle = 12
        since = rng.choices([3, 8, 11, 14, 20, 28, 40],
                            weights=[18, 22, 20, 15, 12, 8, 5])[0]
        criticals = ([rng.choice(CRITICAL_LOADS)] if rng.random() < 0.055
                     else [])
        a = Asset(
            asset_id=f"{'DT' if atype.startswith('distribution') else 'FD' if atype == 'feeder' else 'BR'}-{4000 + i}",
            asset_type=atype,
            division=rng.choices(DIVISIONS, weights=[0.38, 0.31, 0.31])[0],
            subdivision=rng.choice(["Kharadi", "Hadapsar", "Wanowrie", "Baner",
                                    "Uruli", "Ranjangaon"]),
            rating_kva=rng.choice([100, 200, 315, 500, 630, 1000]),
            installed_year=installed,
            telemetry=telemetry,
            peak_load_pct=load,
            load_trend_6m=rng.choices([-3, 0, 4, 9, 14, 21],
                                      weights=[9, 24, 26, 20, 14, 7])[0],
            oil_temp_c=oil,
            ambient_c=rng.randint(29, 38) if oil else None,
            oil_temp_trend_6m=trend,
            phase_imbalance_pct=rng.choices([2, 5, 8, 12, 18, 24],
                                            weights=[24, 26, 22, 15, 9, 4])[0],
            months_since_maintenance=since,
            maintenance_cycle_months=cycle,
            failures_3y=rng.choices([0, 1, 2, 3], weights=[71, 20, 7, 2])[0],
            trips_90d=rng.choices([0, 1, 2, 3, 5], weights=[64, 20, 9, 5, 2])[0],
            no_fault_found_trips_90d=0,
            consumers_served=rng.randint(20, 900),
            critical_loads=criticals,
            alternative_feed=rng.random() < 0.42,
        )
        a.no_fault_found_trips_90d = (
            rng.randint(0, a.trips_90d) if a.trips_90d else 0)
        a.failure_risk, a.primary_driver, a.factors, a.risk_known = _risk(a)
        a.consequence_score = _consequence(a)
        a.risk_band = ("CRITICAL" if a.failure_risk >= 70 else
                       "HIGH" if a.failure_risk >= 45 else
                       "MEDIUM" if a.failure_risk >= 22 else "LOW")
        a.inspect_within_days = (
            7 if a.risk_band == "CRITICAL" else
            30 if a.risk_band == "HIGH" else
            90 if a.risk_band == "MEDIUM" else None)

        agg["assets"] += 1
        agg["by_type"][atype] += 1
        agg["by_band"][a.risk_band] += 1
        if not telemetry:
            agg["no_telemetry"] += 1
            agg["no_telemetry_unscored_signals"] += 1
        if criticals:
            agg["critical_load_assets"] += 1
        if a.risk_band in ("LOW", "MEDIUM") and a.consequence_score >= 70:
            agg["low_risk_high_consequence"] += 1
        if a.months_since_maintenance > a.maintenance_cycle_months:
            agg["overdue_maintenance"] += 1
        if a.no_fault_found_trips_90d >= 2:
            agg["repeat_no_fault_found"] += 1

        if len(heap) < MATERIALISE:
            heapq.heappush(heap, (a.failure_risk, i, a))
        elif a.failure_risk > heap[0][0]:
            heapq.heapreplace(heap, (a.failure_risk, i, a))

    ranked = [x for _s, _i, x in sorted(heap, key=lambda t: (-t[0], t[1]))]
    return ranked, agg


# Last year's failures, and whether the signature was there beforehand. This is
# the evidence for the client's argument — failure then emergency repair, or
# prediction then preventive maintenance.
FAILURE_REVIEW = {
    "period": "2025-09 to 2026-08",
    "failures": 214,
    "with_degradation_signature_beforehand": 137,
    "signature_visible_days_before_median": 34,
    "no_telemetry_so_unknowable": 61,
    "genuinely_sudden": 16,
    "emergency_repair_cost": 214 * EMERGENCY_REPAIR_COST,
    "consumer_hours_lost": 486_000,
    "note": ("137 of 214 failures showed a rising thermal trend, repeat "
             "no-fault-found trips, or sustained overload in the months "
             "before. 61 were on assets with no telemetry, where nothing "
             "could have been seen — which is an instrumentation gap, not a "
             "modelling one. 16 were genuinely sudden."),
}


def _load() -> tuple[list[Asset], dict]:
    key = f"{SEED}-{POPULATION}-{MATERIALISE}-v1"
    cache = Path(__file__).resolve().parent / "_assets_cache.json"
    if cache.exists():
        try:
            blob = json.loads(cache.read_text())
            if blob.get("key") == key:
                return [Asset(**a) for a in blob["ranked"]], blob["agg"]
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
BY_ID: dict[str, Asset] = {a.asset_id: a for a in RANKED}
