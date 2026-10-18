"""Stand-in battery OEM systems: sales registry, warranty claims, field
readings, factory retests and production records.

One service standing in for what would be a battery maker's warranty system,
its dealer portal and its plants' quality records. Every route carries an
`operation_id`, so each is both a REST tool and an MCP tool; see mcp_server.py.

Read-only by design: these tools feed judgements about technicians, dealers
and customers — a demo where the agent can also change a claim is a demo of
something nobody should deploy. The data is synthetic (battery_population.py).
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from datetime import date

import battery_population as pop
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="Battery warranty systems (demo)", description=__doc__, version="1.0.0")

REPLACED = "replaced_under_warranty"


def _d() -> pop.Dataset:
    return pop.data()


def _claims():
    return _d().claims.values()


def _rate(n: int, k: int) -> float:
    return round(k / n, 3) if n else 0.0


def _wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    """95% interval for a rate — a batch of 100 with 2 failures is not '2%'."""
    if not n:
        return [0.0, 0.0]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def _reading_profile(claims: list) -> dict:
    """What the technicians measured, summarised — the evidence behind a verdict."""
    if not claims:
        return {}
    ocv = [c.ocv_volts for c in claims]
    low_cells = Counter()
    for c in claims:
        cells = c.sg_cells
        worst = min(range(6), key=lambda i: cells[i])
        if cells[worst] < 1.18:
            low_cells[f"cell_{worst + 1}"] += 1
    return {
        "claims": len(claims),
        "ocv_median_v": round(statistics.median(ocv), 2),
        "ocv_at_or_above_12_4v_pct": round(100 * sum(v >= 12.4 for v in ocv) / len(ocv), 1),
        "load_test": dict(Counter(c.load_test for c in claims)),
        "alternator_check": dict(Counter(c.alternator_check for c in claims)),
        "low_gravity_cell": dict(low_cells),
    }


def _verdicts(claims: list) -> dict:
    tested = [c for c in claims if c.factory_verdict]
    nff = sum(c.factory_verdict == "no_fault_found" for c in tested)
    return {
        "replaced": sum(c.outcome == REPLACED for c in claims),
        "factory_retested": len(tested),
        "no_fault_found": nff,
        "no_fault_found_rate": _rate(len(tested), nff),
        "verdicts": dict(Counter(c.factory_verdict for c in tested)),
        "cost_of_no_fault_found_rupees": sum(c.replacement_cost_rupees for c in tested
                                             if c.factory_verdict == "no_fault_found"),
    }


def _filter(*, city=None, dealer_id=None, technician_id=None, batch_id=None, model=None, verdict=None,
            outcome=None, since=None, until=None):
    d = _d()
    out = []
    for c in d.claims.values():
        if city and c.city.lower() != city.lower():
            continue
        if dealer_id and c.dealer_id != dealer_id.upper():
            continue
        if technician_id and c.technician_id != technician_id.upper():
            continue
        b = d.batteries[c.serial]
        if batch_id and b.batch_id != batch_id.upper():
            continue
        if model and b.model != model.upper():
            continue
        if verdict and c.factory_verdict != verdict:
            continue
        if outcome and c.outcome != outcome:
            continue
        if since and c.filed_on < since:
            continue
        if until and c.filed_on > until:
            continue
        out.append(c)
    return out


# --- the portfolio ------------------------------------------------------------

@app.get("/summary", operation_id="getWarrantySummary",
         summary="Warranty portfolio: claims, replacements, factory verdicts, cost of no-fault-found")
def warranty_summary() -> dict:
    """The whole programme at a glance: batteries sold, claims, how many were
    replaced, what the factory found in them, and what replacing healthy
    batteries cost. Start here."""
    d = _d()
    claims = list(d.claims.values())
    return {
        "as_of": pop.TODAY.isoformat(),
        "batteries_sold": len(d.batteries),
        "claims": len(claims),
        **_verdicts(claims),
        "by_city": {
            city: {"claims": len(cs), **{k: v for k, v in _verdicts(cs).items() if k != "verdicts"}}
            for city, cs in sorted(_group(claims, lambda c: c.city).items())
        },
        "note": "no_fault_found_rate is of batteries the factory retested — each one a replacement given away.",
    }


def _group(claims, key) -> dict:
    out = defaultdict(list)
    for c in claims:
        out[key(c)].append(c)
    return out


@app.get("/claims", operation_id="listClaims", summary="Warranty claims, filtered")
def list_claims(
    city: str | None = None,
    dealer_id: str | None = None,
    technician_id: str | None = None,
    batch_id: str | None = None,
    model: str | None = None,
    verdict: str | None = Query(None, description="factory verdict, e.g. no_fault_found, cell_short"),
    outcome: str | None = Query(None, description="replaced_under_warranty | rejected | recharged_returned"),
    since: str | None = Query(None, description="filed on or after, YYYY-MM-DD"),
    until: str | None = Query(None, description="filed on or before, YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    """Claims matching the filters, newest first, with their readings and
    factory verdicts. `total` is the full count; at most `limit` are listed."""
    rows = sorted(_filter(city=city, dealer_id=dealer_id, technician_id=technician_id, batch_id=batch_id,
                          model=model, verdict=verdict, outcome=outcome, since=since, until=until),
                  key=lambda c: c.filed_on, reverse=True)
    return {"total": len(rows), "claims": [pop.claim_dict(c) for c in rows[:limit]]}


@app.get("/claims/{claim_id}", operation_id="getClaim", summary="One claim: readings, decision, factory verdict")
def get_claim(claim_id: str) -> dict:
    c = _d().claims.get(claim_id.upper())
    if c is None:
        raise HTTPException(404, f"No claim {claim_id}.")
    b = _d().batteries[c.serial]
    return {**pop.claim_dict(c), "battery": pop.battery_dict(b),
            "other_claims_on_this_serial": [x for x in _d().claims_by_serial.get(c.serial, []) if x != c.claim_id]}


@app.get("/batteries/{serial}", operation_id="getBattery", summary="One battery: where made, sold, every claim")
def get_battery(serial: str) -> dict:
    b = _d().batteries.get(serial.upper())
    if b is None:
        raise HTTPException(404, f"No battery {serial}.")
    claims = [_d().claims[i] for i in _d().claims_by_serial.get(b.serial, [])]
    return {**pop.battery_dict(b), "claims": [pop.claim_dict(c) for c in claims]}


# --- 1. no fault found ------------------------------------------------------------

@app.get("/analysis/no-fault-found", operation_id="getNoFaultFoundAnalysis",
         summary="No-fault-found rate and reading profile, grouped by city, technician, dealer, model or segment")
def no_fault_found_analysis(
    group_by: str = Query("city", pattern="^(city|technician|dealer|model|segment|month)$"),
    city: str | None = None,
    min_retested: int = Query(10, ge=1),
) -> dict:
    """For each group: how many replaced batteries the factory retested, how
    many were healthy, the cost of those, and what the technicians measured
    before replacing (OCV, whether a load test and an alternator check were
    done). Groups with fewer than `min_retested` retests are left out — a rate
    on five batteries is noise."""
    d = _d()
    claims = [c for c in d.claims.values() if c.outcome == REPLACED and c.factory_verdict
              and (not city or c.city.lower() == city.lower())]
    key = {
        "city": lambda c: c.city,
        "technician": lambda c: c.technician_id,
        "dealer": lambda c: c.dealer_id,
        "model": lambda c: d.batteries[c.serial].model,
        "segment": lambda c: d.batteries[c.serial].segment,
        "month": lambda c: c.filed_on[:7],
    }[group_by]
    overall = _verdicts(claims)
    groups = []
    for name, cs in _group(claims, key).items():
        if len(cs) < min_retested:
            continue
        v = _verdicts(cs)
        groups.append({
            group_by: name,
            "retested": v["factory_retested"],
            "no_fault_found": v["no_fault_found"],
            "no_fault_found_rate": v["no_fault_found_rate"],
            "rate_interval_95": _wilson(v["no_fault_found"], v["factory_retested"]),
            "cost_of_no_fault_found_rupees": v["cost_of_no_fault_found_rupees"],
            "before_replacing": _reading_profile(cs),
        })
    groups.sort(key=lambda g: g["no_fault_found_rate"], reverse=True)
    return {"group_by": group_by, "overall_no_fault_found_rate": overall["no_fault_found_rate"],
            "groups": groups}


@app.get("/technicians/{technician_id}", operation_id="getTechnicianProfile",
         summary="A technician's claims: how they test, what they approve, what the factory found")
def technician_profile(technician_id: str) -> dict:
    t = _d().technicians.get(technician_id.upper())
    if t is None:
        raise HTTPException(404, f"No technician {technician_id}.")
    mine = [c for c in _claims() if c.technician_id == t["technician_id"]]
    peers = [c for c in _claims() if c.city == t["city"] and c.technician_id != t["technician_id"]]

    def habits(cs):
        return {
            "claims": len(cs),
            "load_test_done_pct": round(100 * sum(c.load_test != "not_done" for c in cs) / len(cs), 1) if cs else 0,
            "alternator_checked_pct": round(100 * sum(c.alternator_check != "not_checked" for c in cs) / len(cs), 1)
            if cs else 0,
            "replaced_pct": round(100 * sum(c.outcome == REPLACED for c in cs) / len(cs), 1) if cs else 0,
            **{k: v for k, v in _verdicts(cs).items() if k != "verdicts"},
        }

    return {**t, "this_technician": habits(mine), "city_peers": habits(peers),
            "recent_claims": [c.claim_id for c in sorted(mine, key=lambda c: c.filed_on, reverse=True)[:10]]}


@app.get("/claims/{claim_id}/retest", operation_id="getFactoryRetest",
         summary="The factory's retest of a returned battery")
def factory_retest(claim_id: str) -> dict:
    c = _d().claims.get(claim_id.upper())
    if c is None:
        raise HTTPException(404, f"No claim {claim_id}.")
    if not c.factory_verdict:
        return {"claim_id": c.claim_id, "retested": False,
                "why": "Not replaced, or the battery has not reached the plant yet."}
    return {"claim_id": c.claim_id, "retested": True, "verdict": c.factory_verdict, "note": c.factory_note,
            "retested_on": c.retested_on, "field_readings": {k: getattr(c, k) for k in (
                "ocv_volts", "load_test", "sg_cells", "cca_measured", "alternator_check", "parasitic_drain_ma")}}


# --- 2. early batch failure ----------------------------------------------------------

def _batch_units() -> Counter:
    return Counter(b.batch_id for b in _d().batteries.values())


@app.get("/analysis/batch-failures", operation_id="getBatchFailureRates",
         summary="Early-life failure rate per batch, line or plant, with 95% intervals")
def batch_failure_rates(
    group_by: str = Query("batch", pattern="^(batch|line|plant|model|month_made)$"),
    within_months: int = Query(6, ge=1, le=48, description="count claims filed within this many months of sale"),
    min_units: int = Query(60, ge=10),
    genuine_only: bool = Query(True, description="drop claims the factory found healthy"),
    top: int = Query(20, ge=1, le=200),
) -> dict:
    """Failures within the first `within_months` months, per 1,000 batteries
    sold, for each group — the rate, not the count, because a big batch has
    more claims at the same rate. Each row carries its 95% interval and the
    factory verdicts. Sorted worst first."""
    d = _d()
    units = Counter()
    key = {
        "batch": lambda b: b.batch_id,
        "line": lambda b: f"{b.batch_id[:2]}",
        "plant": lambda b: b.plant,
        "model": lambda b: b.model,
        "month_made": lambda b: b.made[:7],
    }[group_by]
    for b in d.batteries.values():
        units[key(b)] += 1
    early = defaultdict(list)
    for c in d.claims.values():
        if c.months_in_service > within_months:
            continue
        if genuine_only and c.factory_verdict == "no_fault_found":
            continue
        early[key(d.batteries[c.serial])].append(c)
    rows = []
    for name, n in units.items():
        if n < min_units:
            continue
        k = len(early.get(name, []))
        rows.append({
            group_by: name, "units_sold": n, "early_failures": k,
            "per_1000": round(1000 * k / n, 1),
            "interval_95_per_1000": [round(1000 * x, 1) for x in _wilson(k, n)],
            "verdicts": dict(Counter(c.factory_verdict for c in early.get(name, []) if c.factory_verdict)),
        })
    rates = sorted(r["per_1000"] for r in rows)
    rows.sort(key=lambda r: r["per_1000"], reverse=True)
    return {"group_by": group_by, "within_months": within_months,
            "median_per_1000": rates[len(rates) // 2] if rates else 0.0, "groups": rows[:top]}


@app.get("/batches/{batch_id}", operation_id="getBatch",
         summary="One batch: units, claims, months to failure, readings, factory verdicts, where it was sold")
def get_batch(batch_id: str) -> dict:
    d = _d()
    batch = d.batches.get(batch_id.upper())
    if batch is None:
        raise HTTPException(404, f"No batch {batch_id}.")
    sold = [b for b in d.batteries.values() if b.batch_id == batch["batch_id"]]
    claims = [d.claims[i] for b in sold for i in d.claims_by_serial.get(b.serial, [])]
    months = Counter(min(c.months_in_service, 24) for c in claims)
    return {
        **batch,
        "units_sold": len(sold),
        "claims": len(claims),
        "claims_by_months_in_service": dict(sorted(months.items())),
        "sold_in_cities": dict(Counter(b.city for b in sold).most_common()),
        "readings": _reading_profile(claims),
        **_verdicts(claims),
        "claim_ids": [c.claim_id for c in claims[:40]],
    }


@app.get("/batches/{batch_id}/production", operation_id="getProductionRecord",
         summary="The plant's record for a batch: separator lot and supplier, formation temperature, QC")
def production_record(batch_id: str) -> dict:
    rec = _d().production.get(batch_id.upper())
    if rec is None:
        raise HTTPException(404, f"No production record for {batch_id}.")
    lot = rec["separator_lot"]
    same_lot = sorted(b for b, r in _d().production.items() if r["separator_lot"] == lot and b != rec["batch_id"])
    return {**rec, "other_batches_with_this_separator_lot": same_lot}


# --- 3. fraud and leakage ----------------------------------------------------------------

@app.get("/dealers/benchmark", operation_id="getDealerBenchmark",
         summary="Each dealer's approval rate, no-fault-found rate and late-warranty claims against city peers")
def dealer_benchmark(city: str | None = None, min_claims: int = Query(15, ge=1), top: int = Query(20, ge=1, le=300)) -> dict:
    """Dealers sorted by excess replacements: how many more batteries they
    replaced than their city's median rate would on the same number of claims.
    A high rate alone is not fraud — read it with the factory's
    no-fault-found rate: a dealer replacing batteries that really failed is
    doing the job."""
    d = _d()
    by_dealer = _group(d.claims.values(), lambda c: c.dealer_id)
    rows = []
    for dealer_id, cs in by_dealer.items():
        if len(cs) < min_claims:
            continue
        info = d.dealers[dealer_id]
        if city and info["city"].lower() != city.lower():
            continue
        v = _verdicts(cs)
        rows.append({
            "dealer_id": dealer_id, "city": info["city"], "claims": len(cs),
            "replaced_rate": _rate(len(cs), v["replaced"]),
            "no_fault_found_rate": v["no_fault_found_rate"],
            "filed_in_last_10_days_of_warranty_pct": round(
                100 * sum(0 <= c.days_to_warranty_end <= 10 for c in cs) / len(cs), 1),
            "top_technician_share_pct": round(100 * Counter(c.technician_id for c in cs).most_common(1)[0][1] / len(cs), 1),
        })
    by_city = _group(rows, lambda r: r["city"])
    city_median = {k: statistics.median(r["replaced_rate"] for r in v) for k, v in by_city.items()}
    all_claims_city = _group(d.claims.values(), lambda c: c.city)
    for r in rows:
        r["city_median_replaced_rate"] = round(city_median[r["city"]], 3)
        r["city_all_claims_replaced_rate"] = _rate(
            len(all_claims_city[r["city"]]), sum(c.outcome == REPLACED for c in all_claims_city[r["city"]]))
        r["above_city_median"] = round(r["replaced_rate"] - city_median[r["city"]], 3)
        # Replacements beyond what the city's median rate would give on this
        # many claims — volume-aware, so 14 of 15 does not outrank 50 of 55.
        r["excess_replacements"] = round(r["claims"] * r["above_city_median"], 1)
    rows.sort(key=lambda r: r["excess_replacements"], reverse=True)
    return {"dealers": rows[:top], "note": "Dealers with fewer than min_claims claims are left out."}


@app.get("/dealers/{dealer_id}", operation_id="getDealerProfile",
         summary="One dealer: claims, approvals, technicians used, timing against warranty end, verdicts")
def dealer_profile(dealer_id: str) -> dict:
    d = _d()
    info = d.dealers.get(dealer_id.upper())
    if info is None:
        raise HTTPException(404, f"No dealer {dealer_id}.")
    cs = [c for c in d.claims.values() if c.dealer_id == info["dealer_id"]]
    days = [c.days_to_warranty_end for c in cs]
    return {
        **info, "claims": len(cs), **_verdicts(cs),
        "replaced_rate": _rate(len(cs), sum(c.outcome == REPLACED for c in cs)),
        "technicians": dict(Counter(c.technician_id for c in cs).most_common()),
        "days_to_warranty_end": {
            "0_to_10": sum(0 <= x <= 10 for x in days), "11_to_60": sum(11 <= x <= 60 for x in days),
            "over_60": sum(x > 60 for x in days),
        },
        "readings": _reading_profile(cs),
        "claim_ids": [c.claim_id for c in sorted(cs, key=lambda c: c.filed_on, reverse=True)[:30]],
    }


@app.get("/fraud/shared-claimants", operation_id="findSharedClaimants",
         summary="Phone numbers that have claimed on several different batteries")
def shared_claimants(min_batteries: int = Query(3, ge=2)) -> dict:
    """Each phone that claimed on `min_batteries` or more different serials,
    with the dealers, dates and verdicts — and whether the batteries belong to
    a registered fleet account, which explains many batteries on one number."""
    d = _d()
    by_phone = _group(d.claims.values(), lambda c: c.claimant_phone)
    rows = []
    for phone, cs in by_phone.items():
        serials = {c.serial for c in cs}
        if len(serials) < min_batteries:
            continue
        fleets = {d.batteries[s].fleet_account for s in serials} - {None}
        rows.append({
            "phone": phone, "batteries": len(serials), "claims": len(cs),
            "registered_owner_on_all": all(d.batteries[s].owner_phone == phone for s in serials),
            "fleet_account": sorted(fleets)[0] if fleets else None,
            "dealers": dict(Counter(c.dealer_id for c in cs)),
            "first_claim": min(c.filed_on for c in cs), "last_claim": max(c.filed_on for c in cs),
            **{k: v for k, v in _verdicts(cs).items() if k in ("factory_retested", "no_fault_found", "verdicts")},
            "claim_ids": [c.claim_id for c in cs],
        })
    rows.sort(key=lambda r: r["batteries"], reverse=True)
    return {"phones": rows}


@app.get("/fraud/reused-photos", operation_id="findReusedPhotos",
         summary="Label photos that appear on more than one claim")
def reused_photos() -> dict:
    """The same label photo (by image fingerprint) attached to claims for
    different batteries — one photo cannot show two serials."""
    by_photo = _group(_claims(), lambda c: c.label_photo_hash)
    rows = [{
        "photo_hash": h, "claims": [{"claim_id": c.claim_id, "serial": c.serial, "dealer_id": c.dealer_id,
                                     "technician_id": c.technician_id, "filed_on": c.filed_on} for c in cs],
    } for h, cs in by_photo.items() if len({c.serial for c in cs}) > 1]
    return {"reused": rows}


@app.get("/fraud/expiry-timing", operation_id="getExpiryTiming",
         summary="How close to warranty end claims are filed, per dealer, against the norm")
def expiry_timing(min_claims: int = Query(15, ge=1), top: int = Query(15, ge=1, le=300)) -> dict:
    """Share of each dealer's claims filed in the last 10 days of warranty,
    against the share across all claims. A pile-up just before expiry suggests
    old batteries being pushed through while they still qualify."""
    d = _d()
    all_claims = list(d.claims.values())
    norm = round(100 * sum(0 <= c.days_to_warranty_end <= 10 for c in all_claims) / len(all_claims), 2)
    rows = []
    for dealer_id, cs in _group(all_claims, lambda c: c.dealer_id).items():
        if len(cs) < min_claims:
            continue
        late = sum(0 <= c.days_to_warranty_end <= 10 for c in cs)
        rows.append({"dealer_id": dealer_id, "city": d.dealers[dealer_id]["city"], "claims": len(cs),
                     "last_10_days": late, "last_10_days_pct": round(100 * late / len(cs), 1)})
    rows.sort(key=lambda r: r["last_10_days_pct"], reverse=True)
    return {"norm_last_10_days_pct": norm, "dealers": rows[:top]}


@app.get("/fraud/links", operation_id="getClaimLinks",
         summary="Everything linked to a phone, dealer, technician or photo: the network around it")
def claim_links(
    kind: str = Query(..., pattern="^(phone|dealer|technician|photo)$"),
    value: str = Query(...),
) -> dict:
    """The claims touching one phone, dealer, technician or photo, and every
    other phone, dealer, technician and photo those claims touch — one hop of
    the network, so a ring shows as shared links."""
    field_of = {"phone": "claimant_phone", "dealer": "dealer_id", "technician": "technician_id",
                "photo": "label_photo_hash"}[kind]
    v = value.strip()
    v = v if kind in ("phone", "photo") else v.upper()
    cs = [c for c in _claims() if getattr(c, field_of) == v]
    if not cs:
        raise HTTPException(404, f"No claims linked to {kind} {value}.")
    return {
        "kind": kind, "value": v, "claims": len(cs),
        "phones": dict(Counter(c.claimant_phone for c in cs)),
        "dealers": dict(Counter(c.dealer_id for c in cs)),
        "technicians": dict(Counter(c.technician_id for c in cs)),
        "photos_shared_with_other_claims": sorted({c.label_photo_hash for c in cs if sum(
            1 for x in _claims() if x.label_photo_hash == c.label_photo_hash) > 1}),
        **_verdicts(cs),
        "claim_ids": [c.claim_id for c in cs[:40]],
    }


@app.get("/reference", operation_id="getReference", summary="Plants, models, cities, and what each verdict means")
def reference() -> dict:
    return {
        "as_of": pop.TODAY.isoformat(),
        "plants": pop.PLANTS,
        "models": [{"code": m.code, "name": m.name, "kind": m.kind, "warranty_months": m.warranty_months,
                    "price_rupees": m.price_rupees} for m in pop.MODELS],
        "cities": list(pop.CITIES.values()),
        "serial_format": "EX-<plant><line>-<yymm made>-<batch>-<unit>, e.g. EX-A2-2603-2-00117",
        "factory_verdicts": pop.FACTORY_NOTES,
        "healthy_battery_signs": "OCV 12.4 V or more after rest, load test pass, all six cell gravities "
                                 "1.24-1.28 within 0.05 of each other.",
    }


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"ok": True, "claims": len(_d().claims), "as_of": date.today().isoformat()}
