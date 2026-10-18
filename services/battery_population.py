"""Stand-in battery OEM warranty data: batteries sold, warranty claims, the
technician's field readings, and the factory's retest of every battery that
came back.

Generated, not stored: a fixed seed builds the same population every time, in
about a second, so the numbers in battery-agent-tests.md stay true. Nothing here
touches the platform's database — the agents reach it only through the
read-only tools in battery_api.py.

The population (TODAY = 2026-10-01):
    ~115,000 batteries made at 4 plants x 2 lines, Jan 2022 - Aug 2026, sold
    through 300 dealers in 10 cities; ~6,000 warranty claims, each with OCV,
    load test, six cell gravities, an alternator check and a drain reading,
    the dealer's decision, and — for every battery replaced — the factory's
    retest verdict.

Serials say where a battery was made:  EX-A2-2603-2-00117
    A = plant (A Ahmednagar, H Haldia, B Bawal, S Hosur), 2 = line,
    2603 = made March 2026, 2 = batch, 00117 = unit.

Three patterns are planted for the three agents to find, each with a
counter-case that looks the same and is not (see PLANTED below):

  1  No fault found. Two Pune technicians approve replacements without a load
     test; the factory finds most of those batteries healthy.
     Counter: a Jaipur summer surge that looks like the same spike in claims,
     but whose batteries really failed (heat: grid corrosion, dry-out).

  2  Early batch failure. Batch A2-2603-2 fails ~5x faster in its first six
     months, with cell 3 reading low; its neighbour A2-2603-1 is mildly up.
     Counter: H1-2201-1 has the most claims of any batch — because it is three
     times the usual size, at a normal rate.

  3  Fraud network. One phone claims six batteries at three Mumbai dealers;
     dealer DLR-NGP-021 approves 94% of claims (Nagpur peers ~60%), many in the
     last ten days of warranty, through one technician; one label photo is
     reused on three claims.
     Counters: Sai Cabs, a taxi fleet, legitimately claims many batteries on
     one phone; DLR-JAI-012 approves 88% — because Jaipur's heat failures are
     real.
"""

from __future__ import annotations

import hashlib
import pickle
import random
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path

SEED = 20261001
TODAY = date(2026, 10, 1)

PLANTS = {"A": "Ahmednagar", "H": "Haldia", "B": "Bawal", "S": "Hosur"}
LINES = (1, 2)
#: Units per batch, normally; one counter-case batch is three times this.
BATCH_SIZE = 130

CITY_CODES: list[str] = []  # filled below
CITIES = {
    "PUN": "Pune", "MUM": "Mumbai", "NGP": "Nagpur", "JAI": "Jaipur", "DEL": "Delhi",
    "KOL": "Kolkata", "CHE": "Chennai", "BLR": "Bengaluru", "HYD": "Hyderabad", "LKO": "Lucknow",
}
CITY_CODES.extend(CITIES)
CODE_OF = {v: k for k, v in CITIES.items()}
DEALERS_PER_CITY = 30
TECHS_PER_CITY = 12


@dataclass(frozen=True)
class Model:
    code: str
    name: str
    kind: str  # car | 2w | inverter
    warranty_months: int
    price_rupees: int
    rated_cca: int
    weight: float  # share of sales


MODELS = (
    Model("EXC-35L", "Car battery 35Ah", "car", 48, 5200, 300, 0.38),
    Model("EXC-65H", "Car battery 65Ah", "car", 48, 7800, 520, 0.22),
    Model("EXM-9L", "Two-wheeler battery 9Ah", "2w", 36, 1800, 90, 0.25),
    Model("EXI-150", "Inverter battery 150Ah", "inverter", 48, 13500, 0, 0.15),
)
MODEL_BY_CODE = {m.code: m for m in MODELS}

#: What the factory finds when a battery comes back. "no_fault_found" means it
#: tested healthy: the replacement was given away.
GENUINE = ("sulphation", "cell_short", "open_circuit", "grid_corrosion", "dry_out")


@dataclass
class Battery:
    serial: str
    batch_id: str
    plant: str
    line: int
    made: str
    model: str
    sold_on: str
    dealer_id: str
    city: str
    segment: str  # private_car | taxi_fleet | two_wheeler | home_inverter
    owner_phone: str
    fleet_account: str | None = None
    warranty_until: str = ""


@dataclass
class Claim:
    claim_id: str
    serial: str
    filed_on: str
    city: str
    dealer_id: str
    technician_id: str
    claimant_phone: str
    months_in_service: int
    days_to_warranty_end: int
    complaint: str
    # The technician's readings.
    ocv_volts: float
    load_test: str  # pass | fail | not_done
    sg_cells: list[float]
    cca_measured: int | None
    alternator_check: str  # ok | undercharging | overcharging | not_checked
    parasitic_drain_ma: int | None
    label_photo_hash: str
    # The decision, and what came of it.
    outcome: str  # replaced_under_warranty | rejected | recharged_returned
    replacement_cost_rupees: int
    factory_verdict: str | None = None  # for replaced batteries only
    factory_note: str = ""
    retested_on: str | None = None
    tags: list[str] = field(default_factory=list)  # internal: why it was generated (never served)


@dataclass
class Dataset:
    batteries: dict[str, Battery]
    claims: dict[str, Claim]
    dealers: dict[str, dict]
    technicians: dict[str, dict]
    batches: dict[str, dict]
    production: dict[str, dict]
    claims_by_serial: dict[str, list[str]]


def _months_between(a: date, b: date) -> int:
    return max(0, (b.year - a.year) * 12 + (b.month - a.month) - (1 if b.day < a.day else 0))


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    return date(d.year + y, m + 1, min(d.day, 28))


def _phone(rng: random.Random) -> str:
    return f"+91{rng.choice('6789')}{rng.randint(100000000, 999999999)}"


def _photo(rng: random.Random) -> str:
    return "ph_" + hashlib.sha1(str(rng.random()).encode()).hexdigest()[:8]


def _readings(rng: random.Random, verdict: str, model: Model, *, careless: bool = False,
              weak_cell: int | None = None) -> dict:
    """What a technician's meter would show for a battery whose truth is `verdict`."""
    healthy = verdict == "no_fault_found"
    if healthy:
        # Usually brought in flat (a drain or a weak alternator), so OCV is often
        # middling — a charged-then-tested battery reads 12.4+ and passes.
        ocv = round(rng.uniform(12.35, 12.72) if careless or rng.random() < 0.55 else rng.uniform(11.9, 12.3), 2)
        sg = [round(rng.uniform(1.235, 1.28), 3) for _ in range(6)]
        load = "pass"
        alt = rng.choices(["undercharging", "ok", "overcharging"], [0.45, 0.45, 0.10])[0]
        drain = rng.choice([rng.randint(20, 45), rng.randint(60, 220)])
    else:
        ocv = round(rng.uniform(10.4, 12.15), 2)
        sg = [round(rng.uniform(1.22, 1.27), 3) for _ in range(6)]
        bad = weak_cell if weak_cell is not None else rng.randrange(6)
        if verdict in ("cell_short", "sulphation"):
            sg[bad] = round(rng.uniform(1.08, 1.17), 3)
        if verdict in ("dry_out", "grid_corrosion"):
            sg = [round(s - rng.uniform(0.02, 0.05), 3) for s in sg]
        load = "fail"
        alt = rng.choices(["ok", "undercharging", "overcharging"], [0.8, 0.12, 0.08])[0]
        drain = rng.randint(15, 45)
    if careless:
        load, alt = "not_done", "not_checked"
        drain = None
    elif rng.random() < 0.12:
        load = "not_done"
    if not careless and rng.random() < 0.25:
        alt = "not_checked"
    cca = None
    if model.rated_cca and load != "not_done":
        cca = int(model.rated_cca * (rng.uniform(0.85, 1.02) if healthy else rng.uniform(0.35, 0.7)))
    return {
        "ocv_volts": ocv, "load_test": load, "sg_cells": sg, "cca_measured": cca,
        "alternator_check": alt, "parasitic_drain_ma": drain,
    }


def _decide(rng: random.Random, readings: dict, *, lenient: bool = False) -> str:
    load = readings["load_test"]
    if lenient:
        return "replaced_under_warranty" if rng.random() < 0.95 else "rejected"
    if load == "fail":
        return "replaced_under_warranty" if rng.random() < 0.92 else "rejected"
    if load == "pass":
        return "recharged_returned" if rng.random() < 0.85 else "replaced_under_warranty"
    return "replaced_under_warranty" if rng.random() < 0.55 else "rejected"


FACTORY_NOTES = {
    "no_fault_found": "Charged and load-tested at the plant: within specification. No fault found.",
    "sulphation": "Heavy sulphation; capacity 48% of rated after desulphation charge.",
    "cell_short": "Internal short in one cell; separator breach.",
    "open_circuit": "Open circuit at an intercell weld.",
    "grid_corrosion": "Positive grid corrosion consistent with sustained high temperature.",
    "dry_out": "Electrolyte loss (dry-out); consistent with heat and overcharging.",
}


def _generate() -> Dataset:
    rng = random.Random(SEED)

    dealers: dict[str, dict] = {}
    technicians: dict[str, dict] = {}
    for code, city in CITIES.items():
        for i in range(1, DEALERS_PER_CITY + 1):
            did = f"DLR-{code}-{i:03d}"
            dealers[did] = {"dealer_id": did, "city": city, "city_code": code,
                            "name": f"{city} Battery Point {i}"}
        for i in range(1, TECHS_PER_CITY + 1):
            tid = f"TEC-{code}-{i:03d}"
            technicians[tid] = {"technician_id": tid, "city": city, "city_code": code,
                                "name": f"Technician {code}-{i:03d}"}

    # --- production and sales ------------------------------------------------
    batteries: dict[str, Battery] = {}
    batches: dict[str, dict] = {}
    production: dict[str, dict] = {}
    month = date(2022, 1, 1)
    last = date(2026, 8, 1)
    while month <= last:
        yymm = month.strftime("%y%m")
        for plant in PLANTS:
            for line in LINES:
                for n in (1, 2):
                    batch_id = f"{plant}{line}-{yymm}-{n}"
                    size = BATCH_SIZE * 3 if batch_id == "H1-2201-1" else int(BATCH_SIZE * rng.uniform(0.85, 1.15))
                    model = rng.choices(MODELS, [m.weight for m in MODELS])[0]
                    batches[batch_id] = {"batch_id": batch_id, "plant": PLANTS[plant], "plant_code": plant,
                                         "line": line, "made": month.isoformat(), "model": model.code,
                                         "units_made": size}
                    production[batch_id] = {
                        "batch_id": batch_id,
                        "acid_density_g_cm3": round(rng.uniform(1.275, 1.285), 3),
                        "formation_max_temp_c": round(rng.uniform(44, 49), 1),
                        "separator_lot": f"SEP-{yymm}-{rng.randint(1, 4):02d}",
                        "separator_supplier": "Polysep Ltd",
                        "qc_capacity_pct": round(rng.uniform(98.5, 101.5), 1),
                        "qc_notes": "",
                    }
                    for unit in range(1, size + 1):
                        sold = month + timedelta(days=rng.randint(20, 140))
                        if sold > TODAY:
                            continue
                        code = rng.choice(CITY_CODES)
                        dealer = f"DLR-{code}-{rng.randint(1, DEALERS_PER_CITY):03d}"
                        segment = {"car": rng.choices(["private_car", "taxi_fleet"], [0.85, 0.15])[0],
                                   "2w": "two_wheeler", "inverter": "home_inverter"}[model.kind]
                        serial = f"EX-{batch_id}-{unit:05d}"
                        batteries[serial] = Battery(
                            serial=serial, batch_id=batch_id, plant=PLANTS[plant], line=line,
                            made=month.isoformat(), model=model.code, sold_on=sold.isoformat(),
                            dealer_id=dealer, city=CITIES[code], segment=segment, owner_phone=_phone(rng),
                            warranty_until=_add_months(sold, model.warranty_months).isoformat(),
                        )
        month = _add_months(month, 1)

    # The bad batch's production record shows what changed.
    production["A2-2603-2"].update({
        "separator_lot": "SEP-2603-09", "separator_supplier": "NewSep Industries (first lot)",
        "formation_max_temp_c": 53.4,
        "qc_notes": "Formation temperature excursion on line 2, 11-12 Mar; separator from a newly approved supplier.",
    })
    production["A2-2603-1"].update({"separator_lot": "SEP-2603-09",
                                     "separator_supplier": "NewSep Industries (first lot)",
                                     "qc_notes": "Part of separator lot SEP-2603-09 used at the end of the run."})

    # --- claims -----------------------------------------------------------------
    claims: dict[str, Claim] = {}
    counters: dict[str, int] = defaultdict(lambda: 10000)
    claims_by_serial: dict[str, list[str]] = defaultdict(list)
    sloppy = {"TEC-PUN-004", "TEC-PUN-009"}
    lenient_dealer, lenient_tech = "DLR-NGP-021", "TEC-NGP-007"

    def add(b: Battery, filed: date, verdict: str, *, claim_id: str | None = None, tech: str | None = None,
            dealer: str | None = None, phone: str | None = None, careless: bool = False, lenient: bool = False,
            weak_cell: int | None = None, photo: str | None = None, complaint: str | None = None,
            tags: tuple[str, ...] = ()) -> Claim:
        model = MODEL_BY_CODE[b.model]
        code = CODE_OF[b.city]
        if claim_id is None:
            counters[code] += 1
            claim_id = f"CLM-{code}-{counters[code]}"
        tech = tech or f"TEC-{code}-{rng.randint(1, TECHS_PER_CITY):03d}"
        if tech in sloppy and not careless:
            careless = rng.random() < 0.85
        readings = _readings(rng, verdict, model, careless=careless, weak_cell=weak_cell)
        outcome = _decide(rng, readings, lenient=lenient or (tech in sloppy and careless))
        sold = date.fromisoformat(b.sold_on)
        c = Claim(
            claim_id=claim_id, serial=b.serial, filed_on=filed.isoformat(), city=b.city,
            dealer_id=dealer or b.dealer_id, technician_id=tech, claimant_phone=phone or b.owner_phone,
            months_in_service=_months_between(sold, filed),
            days_to_warranty_end=(date.fromisoformat(b.warranty_until) - filed).days,
            complaint=complaint or rng.choice(["Vehicle does not start", "Slow cranking in the morning",
                                               "Backup time dropped", "Battery drains overnight",
                                               "Will not hold charge"]),
            label_photo_hash=photo or _photo(rng),
            outcome=outcome,
            replacement_cost_rupees=model.price_rupees if outcome == "replaced_under_warranty" else 0,
            tags=list(tags),
            **readings,
        )
        if outcome == "replaced_under_warranty":
            c.factory_verdict = verdict
            c.factory_note = FACTORY_NOTES[verdict]
            c.retested_on = (filed + timedelta(days=rng.randint(12, 30))).isoformat()
            if c.retested_on > TODAY.isoformat():
                c.factory_verdict, c.factory_note, c.retested_on = None, "", None  # in transit
        claims[claim_id] = c
        claims_by_serial[b.serial].append(claim_id)
        return c

    jaipur_summer = (date(2026, 4, 1), date(2026, 6, 30))
    for b in batteries.values():
        model = MODEL_BY_CODE[b.model]
        sold = date.fromisoformat(b.sold_on)
        months_live = min(model.warranty_months, _months_between(sold, TODAY))
        if months_live < 1:
            continue
        # Genuine failures: rarer early, more later; heavier for taxis.
        p_genuine = 0.045 * (months_live / model.warranty_months) * (1.8 if b.segment == "taxi_fleet" else 1.0)
        p_nff = 0.014 * (months_live / model.warranty_months)
        if b.city == "Pune":
            p_nff *= 2.4  # brought in, and replaced, by two technicians who do not test
        early = None
        if b.batch_id == "A2-2603-2":
            early = 0.21
        elif b.batch_id == "A2-2603-1":
            early = 0.07
        if early is not None and months_live >= 1:
            if rng.random() < early:
                filed = sold + timedelta(days=rng.randint(30, min(180, months_live * 30)))
                if filed <= TODAY:
                    add(b, filed, "cell_short", weak_cell=2,
                        complaint=rng.choice(["Vehicle does not start", "Slow cranking in the morning"]),
                        tags=("early_batch",))
                    continue
        r = rng.random()
        if r < p_genuine:
            filed = sold + timedelta(days=rng.randint(30, months_live * 30))
            verdict = rng.choices(GENUINE, [0.32, 0.18, 0.1, 0.22, 0.18])[0]
            if b.city == "Jaipur" and rng.random() < 0.5:
                verdict = rng.choice(("grid_corrosion", "dry_out"))
            if filed <= TODAY:
                add(b, filed, verdict)
        elif r < p_genuine + p_nff:
            filed = sold + timedelta(days=rng.randint(30, months_live * 30))
            if filed <= TODAY:
                tech = None
                if b.city == "Pune" and rng.random() < 0.6:
                    tech = rng.choice(sorted(sloppy))
                add(b, filed, "no_fault_found", tech=tech, tags=("nff",))
        # Jaipur's summer: heat kills batteries for real.
        if b.city == "Jaipur" and b.segment != "two_wheeler" and sold < jaipur_summer[0] - timedelta(days=200):
            if rng.random() < 0.035:
                filed = jaipur_summer[0] + timedelta(days=rng.randint(0, 90))
                add(b, filed, rng.choice(("grid_corrosion", "dry_out")), dealer=b.dealer_id,
                    tags=("jaipur_heat",))

    # Jaipur's high-approval dealer: real failures, approved because they are real.
    jai12 = [b for b in batteries.values() if b.city == "Jaipur" and b.segment == "private_car"
             and b.serial not in claims_by_serial and "2023-06-01" < b.sold_on < "2025-09-01"]
    for b in rng.sample(jai12, 26):
        filed = date(2026, 5, 1) + timedelta(days=rng.randint(0, 50))
        if filed > date.fromisoformat(b.sold_on):
            add(b, filed, rng.choice(("grid_corrosion", "dry_out", "sulphation")), dealer="DLR-JAI-012",
                tags=("jai012",))

    # --- the fraud network ---------------------------------------------------------
    # Batteries whose warranty ended in the last 15 months, so a claim can land
    # in its last days — which is the point of the timing pattern.
    nagpur = [b for b in batteries.values() if b.city == "Nagpur" and b.segment in ("private_car", "two_wheeler")
              and b.serial not in claims_by_serial and "2025-07-01" <= b.warranty_until <= TODAY.isoformat()]
    rng.shuffle(nagpur)
    reused = "ph_7d1c09e2"
    for i, b in enumerate(nagpur[:48]):
        end = date.fromisoformat(b.warranty_until)
        near_end = rng.random() < 0.45
        filed = end - timedelta(days=rng.randint(1, 10)) if near_end else (
            date.fromisoformat(b.sold_on) + timedelta(days=rng.randint(200, 900)))
        if filed > TODAY or filed <= date.fromisoformat(b.sold_on):
            filed = min(TODAY - timedelta(days=rng.randint(5, 60)), end - timedelta(days=3))
            if filed <= date.fromisoformat(b.sold_on):
                continue
        verdict = "no_fault_found" if rng.random() < 0.58 else rng.choice(GENUINE)
        tech = lenient_tech if rng.random() < 0.82 else f"TEC-NGP-{rng.randint(1, TECHS_PER_CITY):03d}"
        photo = reused if i in (3, 11) else None
        add(b, filed, verdict, dealer=lenient_dealer, tech=tech, lenient=True, photo=photo,
            tags=("ngp031",) + (("near_expiry",) if near_end else ()))
    other = next(b for b in nagpur[60:] if b.serial not in claims_by_serial)
    add(other, date(2026, 8, 19), "no_fault_found", dealer="DLR-NGP-018", photo=reused, tags=("photo_reuse",))

    # One phone, six batteries, three Mumbai dealers, two months.
    mumbai = [b for b in batteries.values() if b.city == "Mumbai" and b.segment == "private_car"
              and b.serial not in claims_by_serial]
    rng.shuffle(mumbai)
    ring_phone = "+919820155443"
    ring_dealers = ("DLR-MUM-007", "DLR-MUM-019", "DLR-MUM-026")
    for i, b in enumerate(mumbai[:6]):
        filed = date(2026, 7, 4) + timedelta(days=i * 9 + rng.randint(0, 4))
        add(b, filed, "no_fault_found" if i not in (2, 5) else "sulphation", dealer=ring_dealers[i % 3],
            phone=ring_phone, lenient=True, claim_id=f"CLM-MUM-4{4210 + i}", tags=("ring",))

    # Sai Cabs: one fleet phone, many taxis, real failures — legitimate.
    fleet_phone = "+919822077110"
    taxis = [b for b in batteries.values() if b.city == "Mumbai" and b.segment == "taxi_fleet"
             and b.serial not in claims_by_serial][:14]
    for b in taxis:
        b.owner_phone, b.fleet_account = fleet_phone, "Sai Cabs Pvt Ltd (fleet account FL-0042)"
    for i, b in enumerate(taxis[:9]):
        filed = date.fromisoformat(b.sold_on) + timedelta(days=rng.randint(240, 600))
        if filed <= TODAY:
            add(b, filed, rng.choice(("sulphation", "grid_corrosion", "dry_out")), dealer="DLR-MUM-012",
                phone=fleet_phone, tags=("fleet",))

    # --- named cases the test document uses -------------------------------------
    pune_b = rng.choice([b for b in batteries.values() if b.city == "Pune" and b.model == "EXC-35L"
                         and b.serial not in claims_by_serial and "2024-03-01" < b.sold_on < "2025-06-01"])
    c = add(pune_b, date(2026, 6, 12), "no_fault_found", claim_id="CLM-PUN-24601", tech="TEC-PUN-004",
            careless=True, complaint="Vehicle does not start", tags=("named",))
    c.ocv_volts, c.outcome = 12.58, "replaced_under_warranty"
    c.replacement_cost_rupees, c.factory_verdict = 5200, "no_fault_found"
    c.factory_note, c.retested_on = FACTORY_NOTES["no_fault_found"], "2026-07-02"

    jai_b = rng.choice([b for b in batteries.values() if b.city == "Jaipur" and b.model == "EXC-35L"
                        and b.serial not in claims_by_serial and "2023-09-01" < b.sold_on < "2025-03-01"])
    c = add(jai_b, date(2026, 5, 22), "grid_corrosion", claim_id="CLM-JAI-31877", complaint="Slow cranking in the morning",
            tags=("named",))
    c.ocv_volts, c.load_test, c.alternator_check = 11.62, "fail", "ok"
    c.outcome, c.replacement_cost_rupees = "replaced_under_warranty", 5200
    c.factory_verdict, c.factory_note, c.retested_on = "grid_corrosion", FACTORY_NOTES["grid_corrosion"], "2026-06-14"

    return Dataset(batteries, claims, dealers, technicians, batches, production, dict(claims_by_serial))


_DATA: Dataset | None = None
#: Bump when the generator changes, so the cache is rebuilt.
VERSION = "battery-v2"
_CACHE = Path(__file__).with_name("_battery_cache.pickle")


def data() -> Dataset:
    """The dataset — generated once (~15 s), then read from a local cache."""
    global _DATA
    if _DATA is None:
        try:
            with _CACHE.open("rb") as fh:
                version, cached = pickle.load(fh)
            if version == VERSION:
                _DATA = cached
        except (OSError, EOFError, pickle.UnpicklingError, ValueError, AttributeError):
            pass
    if _DATA is None:
        _DATA = _generate()
        try:
            with _CACHE.open("wb") as fh:
                pickle.dump((VERSION, _DATA), fh)
        except OSError:
            pass  # read-only checkout: regenerate next time
    return _DATA


def claim_dict(c: Claim) -> dict:
    out = asdict(c)
    out.pop("tags", None)
    return out


def battery_dict(b: Battery) -> dict:
    return asdict(b)
