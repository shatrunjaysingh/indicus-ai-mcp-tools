"""Demand forecasts across the hierarchy, with their own error record.

Use case 9. State to circle to division to subdivision to feeder, each level
forecast and each compared against what actually happened.

The reason to build the whole hierarchy rather than one node is that the
hierarchy is where the misleading number lives. **Errors at feeder level
partially cancel when summed.** A circle forecast can sit at 2% mean absolute
error while the feeders inside it average 11%, because a feeder that came in
high and one that came in low net out on the way up.

Load management, load shedding and network planning are decided at feeder and
DT level. Procurement is decided at circle and state level. So the accuracy
figure quoted in a procurement meeting is genuinely good and genuinely
irrelevant to the people switching load, and a forecasting programme judged
only on the aggregate will be reported as a success by the people buying power
and as useless by the people running the network.

Errors here are generated at the leaf and aggregated upward, so the cancelling
is arithmetic rather than asserted.
"""

from __future__ import annotations

import json
import random
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path

SEED = 20260908

CIRCLES = 3
DIVISIONS_PER_CIRCLE = 3
SUBDIVISIONS_PER_DIVISION = 3
FEEDERS_PER_SUBDIVISION = 22
MONTHS = ["2025-09", "2025-10", "2025-11", "2025-12", "2026-01", "2026-02",
          "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]

# Months carrying a festival that moves demand in this region, and months where
# agricultural pumping dominates a rural feeder's profile.
FESTIVAL_MONTHS = {"2025-10", "2025-11", "2026-03"}
IRRIGATION_MONTHS = {"2025-11", "2025-12", "2026-01", "2026-02"}
PEAK_MONTHS = {"2026-04", "2026-05", "2026-06"}

FEEDER_KINDS = {
    "urban domestic": 0.34,
    "urban mixed": 0.22,
    "commercial": 0.14,
    "industrial": 0.09,
    "rural agricultural": 0.21,
}

# How hard each kind is to forecast, and what drives its error.
KIND_VOLATILITY = {
    "urban domestic": 0.055,
    "urban mixed": 0.062,
    "commercial": 0.070,
    "industrial": 0.115,        # step changes when a large consumer moves
    "rural agricultural": 0.150,  # crop calendar and supply schedule, not weather
}


@dataclass
class Node:
    node_id: str
    name: str
    level: str
    parent: str | None
    kind: str | None = None
    solar_penetration_pct: float = 0.0
    forecast_mwh: dict = field(default_factory=dict)
    actual_mwh: dict = field(default_factory=dict)
    # --- computed ----------------------------------------------------------
    mape_pct: float = 0.0
    bias_pct: float = 0.0
    peak_month_mape_pct: float = 0.0
    worst_month: str = ""
    worst_month_error_pct: float = 0.0


def _generate() -> tuple[dict[str, Node], dict]:
    rng = random.Random(SEED)
    nodes: dict[str, Node] = {}
    kinds = list(FEEDER_KINDS)
    kw = list(FEEDER_KINDS.values())

    state = Node("ST-1", "Maharashtra West", "state", None)
    nodes[state.node_id] = state

    for c in range(CIRCLES):
        cid = f"CR-{c + 1}"
        nodes[cid] = Node(cid, f"Circle {c + 1}", "circle", "ST-1")
        for d in range(DIVISIONS_PER_CIRCLE):
            did = f"DV-{c + 1}{d + 1}"
            nodes[did] = Node(did, f"Division {c + 1}-{d + 1}", "division", cid)
            for s in range(SUBDIVISIONS_PER_DIVISION):
                sid = f"SD-{c + 1}{d + 1}{s + 1}"
                nodes[sid] = Node(sid, f"Subdivision {c+1}-{d+1}-{s+1}",
                                  "subdivision", did)
                for fdr in range(FEEDERS_PER_SUBDIVISION):
                    fid = f"FD-{c+1}{d+1}{s+1}-{fdr + 1:02d}"
                    kind = rng.choices(kinds, weights=kw)[0]
                    node = Node(fid, f"Feeder {fid}", "feeder", sid, kind=kind,
                                solar_penetration_pct=round(
                                    rng.uniform(0, 22) if kind.startswith("urban")
                                    else rng.uniform(0, 4), 1))
                    base = rng.uniform(280, 1_450)
                    for m in MONTHS:
                        seasonal = 1.0
                        if m in PEAK_MONTHS:
                            seasonal += 0.22
                        if m in IRRIGATION_MONTHS and kind == "rural agricultural":
                            seasonal += 0.35
                        if m in FESTIVAL_MONTHS:
                            seasonal += 0.07
                        actual = base * seasonal * rng.uniform(0.95, 1.05)
                        # The forecast misses by an amount scaled to how hard
                        # this kind is, with a systematic under-forecast in
                        # peak months — the failure that matters, because that
                        # is when the power has to be bought.
                        vol = KIND_VOLATILITY[kind]
                        err = rng.gauss(0, vol)
                        if m in PEAK_MONTHS:
                            err -= 0.055
                        if m in FESTIVAL_MONTHS and kind != "industrial":
                            err -= 0.03
                        node.forecast_mwh[m] = round(actual * (1 + err), 1)
                        node.actual_mwh[m] = round(actual, 1)
                    nodes[fid] = node

    # Aggregate upward. This is where the cancelling happens, arithmetically.
    for level in ("subdivision", "division", "circle", "state"):
        for node in [n for n in nodes.values() if n.level == level]:
            children = [n for n in nodes.values() if n.parent == node.node_id]
            for m in MONTHS:
                node.forecast_mwh[m] = round(
                    sum(c.forecast_mwh[m] for c in children), 1)
                node.actual_mwh[m] = round(
                    sum(c.actual_mwh[m] for c in children), 1)
            if children and children[0].level == "feeder":
                node.solar_penetration_pct = round(
                    statistics.mean(c.solar_penetration_pct for c in children), 1)

    for node in nodes.values():
        errs = [(node.forecast_mwh[m] - node.actual_mwh[m]) / node.actual_mwh[m]
                for m in MONTHS]
        node.mape_pct = round(statistics.mean(abs(e) for e in errs) * 100, 2)
        node.bias_pct = round(statistics.mean(errs) * 100, 2)
        peak = [(node.forecast_mwh[m] - node.actual_mwh[m]) / node.actual_mwh[m]
                for m in MONTHS if m in PEAK_MONTHS]
        node.peak_month_mape_pct = round(
            statistics.mean(abs(e) for e in peak) * 100, 2)
        worst = max(MONTHS, key=lambda m: abs(
            (node.forecast_mwh[m] - node.actual_mwh[m]) / node.actual_mwh[m]))
        node.worst_month = worst
        node.worst_month_error_pct = round(
            (node.forecast_mwh[worst] - node.actual_mwh[worst])
            / node.actual_mwh[worst] * 100, 2)

    by_level = {}
    for level in ("state", "circle", "division", "subdivision", "feeder"):
        rows = [n for n in nodes.values() if n.level == level]
        by_level[level] = {
            "nodes": len(rows),
            "mean_mape_pct": round(statistics.mean(n.mape_pct for n in rows), 2),
            "mean_bias_pct": round(statistics.mean(n.bias_pct for n in rows), 2),
            "mean_peak_mape_pct": round(
                statistics.mean(n.peak_month_mape_pct for n in rows), 2),
            "worst_node_mape_pct": round(max(n.mape_pct for n in rows), 2),
        }
    agg = {
        "levels": by_level,
        "months": MONTHS,
        "festival_months": sorted(FESTIVAL_MONTHS),
        "peak_months": sorted(PEAK_MONTHS),
        "irrigation_months": sorted(IRRIGATION_MONTHS),
        "feeder_kinds": {
            k: {
                "feeders": sum(1 for n in nodes.values()
                               if n.level == "feeder" and n.kind == k),
                "mean_mape_pct": round(statistics.mean(
                    n.mape_pct for n in nodes.values()
                    if n.level == "feeder" and n.kind == k), 2),
            } for k in FEEDER_KINDS
        },
    }
    return nodes, agg


def _load() -> tuple[dict[str, Node], dict]:
    key = f"{SEED}-{CIRCLES}-{FEEDERS_PER_SUBDIVISION}-v1"
    cache = Path(__file__).resolve().parent / "_forecast_cache.json"
    if cache.exists():
        try:
            blob = json.loads(cache.read_text())
            if blob.get("key") == key:
                return ({k: Node(**v) for k, v in blob["nodes"].items()},
                        blob["agg"])
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    nodes, agg = _generate()
    try:
        cache.write_text(json.dumps({
            "key": key, "nodes": {k: asdict(v) for k, v in nodes.items()},
            "agg": agg}))
    except OSError:
        pass
    return nodes, agg


NODES, TOTALS = _load()
