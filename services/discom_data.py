"""Fixtures for the DISCOM demos.

Built so the arithmetic reconciles. A fixture whose numbers do not add up
produces a run that fails for reasons nobody can diagnose — an earlier demo
here had a consumer whose billed units contradicted their meter reads, and two
agents spent a plan-and-critique loop each trying to make it work before giving
up. Every consumer below has a payment record, a consumption series and a
ledger that agree with each other and with the story the case is meant to tell.

Amounts are ₹. Consumption is kWh. Dates are ISO.
"""

from __future__ import annotations

from datetime import date

TODAY = date(2026, 9, 1)


def _months_back(n: int) -> list[str]:
    """The last n billing periods, oldest first, as YYYY-MM."""
    out, y, m = [], TODAY.year, TODAY.month
    for _ in range(n):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        out.append(f"{y}-{m:02d}")
    return list(reversed(out))


PERIODS = _months_back(24)

CONSUMERS: dict[str, dict] = {
    # A good payer who has recently stopped. The case for a reminder or a call,
    # not a field visit — and the one most often over-escalated because the
    # balance looks alarming without the history behind it.
    "DL-4471002": {
        "consumer_no": "DL-4471002", "name": "S. Kulkarni",
        "category": "LT-1 Domestic", "connected_load_kw": 3.0,
        "sanctioned_load_kw": 3.0, "phase": "single",
        "address": "14 Shanti Nagar, Kharadi", "division": "Pune East",
        "subdivision": "Kharadi", "feeder": "F-11-KHR", "dt": "DT-1120",
        "connection_date": "2018-04-12", "supply_status": "connected",
        "meter_no": "MT-77120451", "outstanding": 9840.0,
        "medical_dependency": False,
    },
    # Large dues, long TD, and consumption after the disconnection. The case
    # field teams should be sent to, and the same consumer drives the illegal
    # restoration demo.
    "CM-8890145": {
        "consumer_no": "CM-8890145", "name": "Ravi Traders",
        "category": "LT-2 Commercial", "connected_load_kw": 16.0,
        "sanctioned_load_kw": 12.0, "phase": "three",
        "address": "Shop 4, Market Road, Hadapsar", "division": "Pune East",
        "subdivision": "Hadapsar", "feeder": "F-07-HDP", "dt": "DT-4587",
        "connection_date": "2015-08-01", "supply_status": "temporarily_disconnected",
        "meter_no": "MT-55093318", "outstanding": 85420.0,
        "medical_dependency": False,
    },
    # Smaller dues, shorter TD, premises empty. Scores low despite the arrears,
    # which is the point of recoverable-amount x probability.
    "DL-2245108": {
        "consumer_no": "DL-2245108", "name": "A. Fernandes",
        "category": "LT-1 Domestic", "connected_load_kw": 2.0,
        "sanctioned_load_kw": 2.0, "phase": "single",
        "address": "8B Rose Villa, Wanowrie", "division": "Pune East",
        "subdivision": "Wanowrie", "feeder": "F-03-WNW", "dt": "DT-2210",
        "connection_date": "2012-01-20", "supply_status": "temporarily_disconnected",
        "meter_no": "MT-31004476", "outstanding": 18260.0,
        "medical_dependency": False,
    },
    # A 60% consumption drop with a documented reason. The theft skill should
    # clear this one; an anomaly model on consumption alone would flag it.
    "IN-7734021": {
        "consumer_no": "IN-7734021", "name": "Deccan Polymers Pvt Ltd",
        "category": "HT Industrial", "connected_load_kw": 250.0,
        "sanctioned_load_kw": 250.0, "phase": "three",
        "address": "Plot 22, MIDC Ranjangaon", "division": "Pune Rural",
        "subdivision": "Ranjangaon", "feeder": "F-22-RJG", "dt": "DT-9001",
        "connection_date": "2009-11-05", "supply_status": "connected",
        "meter_no": "MT-90011203", "outstanding": 0.0,
        "medical_dependency": False,
    },
    # Drop, tamper events and a seal mismatch. The case that should be
    # inspected — and still must not be called theft in the report.
    "CM-5561093": {
        "consumer_no": "CM-5561093", "name": "Sunrise Cold Storage",
        "category": "LT-2 Commercial", "connected_load_kw": 45.0,
        "sanctioned_load_kw": 30.0, "phase": "three",
        "address": "Survey 118, Uruli Kanchan", "division": "Pune Rural",
        "subdivision": "Uruli", "feeder": "F-19-URL", "dt": "DT-7745",
        "connection_date": "2016-06-18", "supply_status": "connected",
        "meter_no": "MT-66210984", "outstanding": 12300.0,
        "medical_dependency": False,
    },
    # Estimated bills then one actual read. The complaint is real, the meter is
    # fine, and the cause is catch-up billing.
    "DL-9982334": {
        "consumer_no": "DL-9982334", "name": "P. Deshmukh",
        "category": "LT-1 Domestic", "connected_load_kw": 4.0,
        "sanctioned_load_kw": 4.0, "phase": "single",
        "address": "Flat 302, Green Meadows, Baner", "division": "Pune West",
        "subdivision": "Baner", "feeder": "F-14-BNR", "dt": "DT-3312",
        "connection_date": "2020-09-30", "supply_status": "connected",
        "meter_no": "MT-44872210", "outstanding": 14720.0,
        "medical_dependency": True,
    },
}


def _series(pattern: list[int], periods: list[str], basis: str = "actual") -> list[dict]:
    return [
        {"period": p, "units": u, "basis": basis}
        for p, u in zip(periods, pattern, strict=False)
    ]


# --- consumption -----------------------------------------------------------
# Each series is written to make one case legible, and to stay consistent with
# the ledger and payment records below.

_STEADY_DOM = [310, 295, 340, 380, 420, 465, 430, 355, 320, 300, 290, 305] * 2

CONSUMPTION: dict[str, list[dict]] = {
    "DL-4471002": _series(_STEADY_DOM[:24], PERIODS),
    # Trades normally, then TD in month 20; the two periods after TD are the
    # illegal restoration signal.
    "CM-8890145": _series(
        [1450, 1520, 1380, 1610, 1700, 1580, 1490, 1550, 1620, 1470,
         1510, 1590, 1440, 1530, 1660, 1580, 1490, 1520, 620, 0,
         0, 0, 450, 1180],
        PERIODS,
    ),
    # Goes quiet at TD and stays quiet. Nobody is there.
    "DL-2245108": _series(
        [240, 255, 230, 275, 290, 310, 285, 250, 235, 220, 210, 245,
         230, 260, 240, 215, 190, 120, 40, 0, 0, 0, 0, 0],
        PERIODS,
    ),
    # Drops 60% at month 13 — when a documented load surrender took effect.
    "IN-7734021": _series(
        [88000, 91000, 87500, 90200, 89400, 92100, 88800, 90500,
         91200, 89900, 87600, 90800,
         36200, 35100, 36800, 35400, 36100, 35900, 36500, 35700,
         36300, 35800, 36600, 36000],
        PERIODS,
    ),
    # Drops with no documented reason, and the tamper log lines up with it.
    "CM-5561093": _series(
        [8200, 8450, 8100, 8600, 8900, 9200, 8800, 8300, 8150, 8050,
         7900, 8250, 8400, 8700, 8550, 8200,
         3100, 2950, 3050, 2900, 3150, 3000, 2980, 3100],
        PERIODS,
    ),
    # Estimated for five periods, then a true-up read that catches up the lot.
    "DL-9982334": (
        _series([420, 445, 410, 460, 480, 520, 495, 430, 415, 400,
                 390, 425, 440, 470, 455, 435, 445, 460, 450], PERIODS[:19])
        + _series([300, 300, 300, 300, 300], PERIODS[19:24], basis="estimated")
        + []
    ),
}
# The true-up: the actual read that follows five estimates recovers the
# under-estimated units in one bill, which is what the consumer complains about.
CONSUMPTION["DL-9982334"] = CONSUMPTION["DL-9982334"][:19] + [
    {"period": PERIODS[19], "units": 300, "basis": "estimated"},
    {"period": PERIODS[20], "units": 300, "basis": "estimated"},
    {"period": PERIODS[21], "units": 300, "basis": "estimated"},
    {"period": PERIODS[22], "units": 300, "basis": "estimated"},
    {"period": PERIODS[23], "units": 1180, "basis": "actual",
     "note": "True-up read. Recovers 880 units under-estimated over the four "
             "preceding estimated periods (4 x 220)."},
]


# --- tariff and ledger -----------------------------------------------------

RATE = {"LT-1 Domestic": 8.2, "LT-2 Commercial": 11.4, "HT Industrial": 9.1}


def _bill(consumer_no: str, period: str, units: int, basis: str) -> dict:
    rate = RATE[CONSUMERS[consumer_no]["category"]]
    return {"period": period, "units": units, "basis": basis,
            "amount": round(units * rate, 2)}


def billing_for(consumer_no: str) -> list[dict]:
    return [_bill(consumer_no, r["period"], r["units"], r["basis"])
            for r in CONSUMPTION[consumer_no]]


# Payment records. `status` is one of paid_on_time, paid_late, unpaid.
# Written to reconcile with the outstanding balance on each consumer.
PAYMENTS: dict[str, list[dict]] = {
    # 19 on time, 2 late, 3 unpaid — the pattern the payment-risk skill is
    # built to read correctly. The three unpaid are the current arrears.
    "DL-4471002": (
        [{"period": p, "status": "paid_on_time"} for p in PERIODS[:14]]
        + [{"period": PERIODS[14], "status": "paid_late", "days_late": 9},
           {"period": PERIODS[15], "status": "paid_on_time"},
           {"period": PERIODS[16], "status": "paid_on_time"},
           {"period": PERIODS[17], "status": "paid_on_time"},
           {"period": PERIODS[18], "status": "paid_late", "days_late": 12},
           {"period": PERIODS[19], "status": "paid_on_time"},
           {"period": PERIODS[20], "status": "paid_on_time"},
           {"period": PERIODS[21], "status": "unpaid"},
           {"period": PERIODS[22], "status": "unpaid"},
           {"period": PERIODS[23], "status": "unpaid"}]
    ),
    # Chronic. Two broken promises to pay, which is what should stop a third
    # instalment offer being recommended.
    "CM-8890145": (
        [{"period": p, "status": "paid_late", "days_late": 30 + (i % 20)}
         for i, p in enumerate(PERIODS[:14])]
        + [{"period": p, "status": "unpaid"} for p in PERIODS[14:]]
    ),
    "DL-2245108": (
        [{"period": p, "status": "paid_on_time"} for p in PERIODS[:10]]
        + [{"period": p, "status": "paid_late", "days_late": 22} for p in PERIODS[10:12]]
        + [{"period": p, "status": "unpaid"} for p in PERIODS[12:]]
    ),
    "IN-7734021": [{"period": p, "status": "paid_on_time"} for p in PERIODS],
    "CM-5561093": (
        [{"period": p, "status": "paid_on_time"} for p in PERIODS[:22]]
        + [{"period": p, "status": "paid_late", "days_late": 15} for p in PERIODS[22:]]
    ),
    "DL-9982334": (
        [{"period": p, "status": "paid_on_time"} for p in PERIODS[:23]]
        + [{"period": PERIODS[23], "status": "unpaid",
            "note": "Disputed — consumer has raised a complaint on this bill."}]
    ),
}

PROMISES: dict[str, list[dict]] = {
    "CM-8890145": [
        {"date": "2025-03-11", "amount": 20000.0, "kept": False},
        {"date": "2025-08-02", "amount": 15000.0, "kept": False},
    ],
    "DL-4471002": [],
}

# --- disconnection ---------------------------------------------------------

DISCONNECTIONS: dict[str, dict] = {
    "CM-8890145": {
        "consumer_no": "CM-8890145", "status": "temporarily_disconnected",
        "td_date": "2025-07-09", "td_days": (TODAY - date(2025, 7, 9)).days,
        # Executed and acknowledged, with a reading taken. This is what makes
        # the illegal restoration case sound rather than a records failure.
        "executed_on": "2025-07-09", "executed_by": "JE Hadapsar / crew 4",
        "field_acknowledgement": True,
        "method": "service cable disconnected at pole; meter left in situ, sealed",
        "reading_at_disconnection": 184220,
        "restoration_orders": [],
        "pd_eligible_after": "2026-01-09", "pd_converted": False,
    },
    "DL-2245108": {
        "consumer_no": "DL-2245108", "status": "temporarily_disconnected",
        "td_date": "2026-06-03", "td_days": (TODAY - date(2026, 6, 3)).days,
        "executed_on": "2026-06-03", "executed_by": "JE Wanowrie / crew 2",
        "field_acknowledgement": True,
        "method": "meter removed",
        "reading_at_disconnection": 41180,
        "restoration_orders": [],
        "pd_eligible_after": "2026-12-03", "pd_converted": False,
    },
}

# --- meters ----------------------------------------------------------------

METERS: dict[str, dict] = {
    "MT-77120451": {"meter_no": "MT-77120451", "type": "single-phase static",
                    "installed": "2018-04-12", "last_read": "2026-08-28",
                    "last_read_kwh": 91340, "communication": "ok",
                    "seal_no_issued": "SL-88120", "tamper_events": []},
    "MT-55093318": {"meter_no": "MT-55093318", "type": "three-phase static",
                    "installed": "2015-08-01", "last_read": "2026-08-27",
                    "last_read_kwh": 185850, "communication": "ok",
                    "seal_no_issued": "SL-33418", "tamper_events": []},
    "MT-31004476": {"meter_no": "MT-31004476", "type": "single-phase static",
                    "installed": "2012-01-20", "last_read": "2026-06-03",
                    "last_read_kwh": 41180, "communication": "removed",
                    "seal_no_issued": "SL-11007", "tamper_events": []},
    "MT-90011203": {"meter_no": "MT-90011203", "type": "HT CT-operated",
                    "installed": "2009-11-05", "last_read": "2026-08-30",
                    "last_read_kwh": 2214500, "communication": "ok",
                    "seal_no_issued": "SL-90012", "tamper_events": []},
    # The tamper log that lines up with the consumption drop.
    "MT-66210984": {"meter_no": "MT-66210984", "type": "three-phase static",
                    "installed": "2016-06-18", "last_read": "2026-08-29",
                    "last_read_kwh": 402180, "communication": "intermittent",
                    "seal_no_issued": "SL-66219",
                    "tamper_events": [
                        {"date": "2026-04-28", "event": "cover_open",
                         "work_order": None},
                        {"date": "2026-05-02", "event": "magnetic_field",
                         "work_order": None},
                        {"date": "2026-06-14", "event": "cover_open",
                         "work_order": None},
                    ]},
    "MT-44872210": {"meter_no": "MT-44872210", "type": "single-phase static",
                    "installed": "2020-09-30", "last_read": "2026-08-26",
                    "last_read_kwh": 30240, "communication": "ok",
                    "seal_no_issued": "SL-44871", "tamper_events": []},
}

# --- site surveys ----------------------------------------------------------

SURVEYS: dict[str, dict] = {
    "CM-8890145": {
        "consumer_no": "CM-8890145", "surveyed_on": "2026-08-20",
        "surveyor": "Lineman R. Patil",
        "premises_status": "occupied — shop trading",
        "observations": "Shop open and trading. Cold room running. Service "
                        "cable appears reconnected at pole with a temporary "
                        "clamp. Meter in place, seal not matching records.",
        "supply_appears_live": True,
    },
    "DL-2245108": {
        "consumer_no": "DL-2245108", "surveyed_on": "2026-08-18",
        "surveyor": "Lineman S. Jadhav",
        "premises_status": "locked — no occupancy, post uncollected",
        "observations": "Premises locked. Neighbours state family relocated "
                        "in May. Meter removed at TD; service position dead.",
        "supply_appears_live": False,
    },
    "CM-5561093": {
        "consumer_no": "CM-5561093", "surveyed_on": "2026-08-25",
        "surveyor": "Vigilance team 2",
        "premises_status": "occupied — cold storage operating",
        "observations": "Two cold rooms running, compressors audible. Meter "
                        "body shows fresh scoring around the terminal cover.",
        "supply_appears_live": True,
    },
}

# What an image-analysis service returned for a survey. Detections with
# confidences, not observations — the site-survey skill exists partly to keep
# that distinction visible.
SURVEY_IMAGES: dict[str, dict] = {
    "CM-8890145": {
        "survey_id": "SRV-8890145-01", "images": 6,
        "ocr": {"meter_number_read": "MT-5509331B", "confidence": 0.71,
                "reading_visible": 185850, "reading_confidence": 0.93},
        "detections": [
            {"label": "meter", "confidence": 0.99},
            {"label": "meter_seal", "confidence": 0.88,
             "detail": "seal present, number reads SL-33418"},
            {"label": "service_wire", "confidence": 0.96},
            {"label": "temporary_clamp_on_service_cable", "confidence": 0.84},
            {"label": "pole", "confidence": 0.97},
            {"label": "premises_frontage_commercial", "confidence": 0.95},
            {"label": "meter_bypass", "confidence": 0.31},
        ],
        "not_captured": ["terminal chamber interior", "seal underside",
                         "pole termination close-up"],
    },
}

NOTICES: dict[str, list[dict]] = {
    "DL-4471002": [
        {"date": "2026-08-14", "type": "SMS reminder", "delivered": True,
         "responded": False},
    ],
    "CM-8890145": [
        {"date": "2025-04-02", "type": "SMS reminder", "delivered": True,
         "responded": False},
        {"date": "2025-05-19", "type": "15-day notice", "delivered": True,
         "responded": False},
        {"date": "2025-06-24", "type": "disconnection notice", "delivered": True,
         "responded": False},
        {"date": "2026-02-10", "type": "final demand", "delivered": True,
         "responded": False},
    ],
    "DL-2245108": [
        {"date": "2026-04-11", "type": "SMS reminder", "delivered": True,
         "responded": False},
        {"date": "2026-05-15", "type": "disconnection notice",
         "delivered": False, "note": "returned undelivered — addressee moved"},
    ],
    "DL-9982334": [],
    "CM-5561093": [],
    "IN-7734021": [],
}

# The documented reason IN-7734021's consumption halved. Without this the case
# looks identical to CM-5561093, which is the point of including both.
LOAD_CHANGES: dict[str, list[dict]] = {
    "IN-7734021": [
        {"date": "2025-08-30", "change": "load surrender",
         "from_kw": 250.0, "to_kw": 100.0,
         "reference": "LS/2025/1188 — approved, one production line "
                      "relocated to Aurangabad unit"},
    ],
}


# --- outstanding, derived --------------------------------------------------
# Computed from the unpaid bills rather than written down beside them. A
# hardcoded balance drifts the moment a consumption figure is edited, and an
# agent asked to reconcile a ledger that does not add up will either invent a
# reconciliation or loop trying to find one. This cannot drift.

LATE_FEE_RATE = 0.02  # per unpaid period, on the unpaid amount


def _outstanding(consumer_no: str) -> tuple[float, list[dict]]:
    bills = {b["period"]: b for b in billing_for(consumer_no)}
    unpaid = [p for p in PAYMENTS[consumer_no] if p["status"] == "unpaid"]
    lines, total = [], 0.0
    for n, rec in enumerate(reversed(unpaid)):
        bill = bills.get(rec["period"])
        if bill is None:
            continue
        fee = round(bill["amount"] * LATE_FEE_RATE * (n + 1), 2)
        total += bill["amount"] + fee
        lines.append({"period": rec["period"], "principal": bill["amount"],
                      "late_fee": fee})
    return round(total, 2), list(reversed(lines))


ARREARS: dict[str, list[dict]] = {}
for _cn, _rec in CONSUMERS.items():
    _total, _lines = _outstanding(_cn)
    _rec["outstanding"] = _total
    ARREARS[_cn] = _lines

# --- network assets --------------------------------------------------------

ASSETS: dict[str, dict] = {
    # The requirement's own example: 92% load, abnormal thermal trend.
    "DT-4587": {
        "asset_id": "DT-4587", "type": "distribution transformer",
        "rating_kva": 315, "installed": "2011-03-14",
        "feeder": "F-07-HDP", "subdivision": "Hadapsar",
        "consumers_served": 214, "critical_loads": [],
        "alternative_feed": False,
        "load_pct_trend": [{"month": "2026-03", "peak_pct": 71},
                           {"month": "2026-04", "peak_pct": 78},
                           {"month": "2026-05", "peak_pct": 84},
                           {"month": "2026-06", "peak_pct": 88},
                           {"month": "2026-07", "peak_pct": 91},
                           {"month": "2026-08", "peak_pct": 92}],
        # Rising at near-constant ambient: the degradation signature.
        "oil_temp_trend": [{"month": "2026-03", "max_c": 62, "ambient_c": 34},
                           {"month": "2026-04", "max_c": 68, "ambient_c": 36},
                           {"month": "2026-05", "max_c": 79, "ambient_c": 37},
                           {"month": "2026-06", "max_c": 86, "ambient_c": 33},
                           {"month": "2026-07", "max_c": 91, "ambient_c": 31},
                           {"month": "2026-08", "max_c": 94, "ambient_c": 32}],
        "phase_imbalance_pct": 18,
        "last_maintenance": "2023-11-02",
        "maintenance_cycle_months": 12,
        "failures": [{"date": "2024-08-19", "type": "HV fuse", "outage_hours": 6}],
        "trips": [{"date": "2026-06-11", "finding": "restored, no fault found"},
                  {"date": "2026-07-23", "finding": "restored, no fault found"},
                  {"date": "2026-08-15", "finding": "restored, no fault found"}],
    },
    # Healthy, so the skill has something to be unexcited about.
    "DT-1120": {
        "asset_id": "DT-1120", "type": "distribution transformer",
        "rating_kva": 200, "installed": "2019-06-01",
        "feeder": "F-11-KHR", "subdivision": "Kharadi",
        "consumers_served": 96, "critical_loads": [], "alternative_feed": True,
        "load_pct_trend": [{"month": m, "peak_pct": p} for m, p in
                           [("2026-03", 54), ("2026-04", 57), ("2026-05", 61),
                            ("2026-06", 63), ("2026-07", 62), ("2026-08", 60)]],
        "oil_temp_trend": [{"month": m, "max_c": t, "ambient_c": a} for m, t, a in
                           [("2026-03", 51, 34), ("2026-04", 55, 36),
                            ("2026-05", 58, 37), ("2026-06", 56, 33),
                            ("2026-07", 54, 31), ("2026-08", 53, 32)]],
        "phase_imbalance_pct": 4,
        "last_maintenance": "2026-02-10", "maintenance_cycle_months": 12,
        "failures": [], "trips": [],
    },
    # Low risk, high consequence — the ranking case the skill must handle
    # without inflating the risk band.
    "DT-2210": {
        "asset_id": "DT-2210", "type": "distribution transformer",
        "rating_kva": 500, "installed": "2017-02-20",
        "feeder": "F-03-WNW", "subdivision": "Wanowrie",
        "consumers_served": 380,
        "critical_loads": ["Wanowrie Municipal Water Pumping Station",
                           "Sai Community Hospital (40 beds)"],
        "alternative_feed": False,
        "load_pct_trend": [{"month": m, "peak_pct": p} for m, p in
                           [("2026-03", 62), ("2026-04", 64), ("2026-05", 68),
                            ("2026-06", 70), ("2026-07", 69), ("2026-08", 67)]],
        "oil_temp_trend": [{"month": m, "max_c": t, "ambient_c": a} for m, t, a in
                           [("2026-03", 58, 34), ("2026-04", 61, 36),
                            ("2026-05", 64, 37), ("2026-06", 62, 33),
                            ("2026-07", 60, 31), ("2026-08", 59, 32)]],
        "phase_imbalance_pct": 7,
        "last_maintenance": "2025-12-05", "maintenance_cycle_months": 12,
        "failures": [], "trips": [{"date": "2026-05-02", "finding": "LV surge"}],
    },
}

FEEDERS: dict[str, dict] = {
    "F-07-HDP": {"feeder_id": "F-07-HDP", "subdivision": "Hadapsar",
                 "energy_in_kwh": 1284000, "energy_billed_kwh": 981000,
                 "loss_pct": 23.6, "dts": ["DT-4587"],
                 "note": "Loss above subdivision average of 14.1%."},
    "F-11-KHR": {"feeder_id": "F-11-KHR", "subdivision": "Kharadi",
                 "energy_in_kwh": 902000, "energy_billed_kwh": 810000,
                 "loss_pct": 10.2, "dts": ["DT-1120"]},
    "F-19-URL": {"feeder_id": "F-19-URL", "subdivision": "Uruli",
                 "energy_in_kwh": 1105000, "energy_billed_kwh": 812000,
                 "loss_pct": 26.5, "dts": ["DT-7745"],
                 "note": "Loss above subdivision average of 15.8%."},
    "F-03-WNW": {"feeder_id": "F-03-WNW", "subdivision": "Wanowrie",
                 "energy_in_kwh": 1420000, "energy_billed_kwh": 1268000,
                 "loss_pct": 10.7, "dts": ["DT-2210"]},
}


# --- peer benchmarks -------------------------------------------------------
# Deliberately wide. Peer comparison is the weakest evidence in a theft case and
# a benchmark presented as a tight number invites it to be treated as strong.

PEERS: dict[str, dict] = {
    "CM-5561093": {"cohort": "LT-2 Commercial, cold storage, 30-50 kW, Uruli",
                   "cohort_size": 34, "median_monthly_kwh": 7900,
                   "p25_monthly_kwh": 5600, "p75_monthly_kwh": 10400,
                   "subject_recent_mean_kwh": 3035},
    "IN-7734021": {"cohort": "HT Industrial, polymers, 100-300 kW, Pune Rural",
                   "cohort_size": 11, "median_monthly_kwh": 41000,
                   "p25_monthly_kwh": 28000, "p75_monthly_kwh": 76000,
                   "subject_recent_mean_kwh": 36000},
    "DL-4471002": {"cohort": "LT-1 Domestic, 3 kW, Kharadi", "cohort_size": 412,
                   "median_monthly_kwh": 330, "p25_monthly_kwh": 240,
                   "p75_monthly_kwh": 445, "subject_recent_mean_kwh": 318},
}

# --- complaints ------------------------------------------------------------

COMPLAINTS: dict[str, dict] = {
    # The requirement's own example. The meter is fine; five estimated bills
    # then a true-up read is the cause.
    "CMP-33012": {
        "complaint_id": "CMP-33012", "consumer_no": "DL-9982334",
        "received": "2026-08-29T09:14:00", "channel": "mobile app",
        "text": "Bill has suddenly increased and meter is running very fast. "
                "Last month 2400 rupees, this month 9600. Nothing has changed "
                "in my house. My mother is on oxygen concentrator so I cannot "
                "have supply cut. Please check the meter urgently.",
        "status": "open",
    },
    # Safety buried inside a billing complaint.
    "CMP-33018": {
        "complaint_id": "CMP-33018", "consumer_no": "DL-4471002",
        "received": "2026-08-30T21:40:00", "channel": "call centre",
        "text": "I want to complain about my bill amount and also there is "
                "sparking from the meter box outside and burning smell since "
                "evening. Bill is showing arrears which I already paid.",
        "status": "open",
    },
    # A third repeat with no resolution.
    "CMP-33021": {
        "complaint_id": "CMP-33021", "consumer_no": "CM-5561093",
        "received": "2026-08-31T11:02:00", "channel": "portal",
        "text": "Third time I am complaining about low voltage in the "
                "afternoon. Complaint numbers CMP-31877 and CMP-32544 were "
                "closed without anyone visiting. My compressors are tripping. "
                "If this is not fixed I will go to the consumer forum.",
        "status": "open",
    },
}

COMPLAINT_HISTORY: dict[str, list[dict]] = {
    "CM-5561093": [
        {"complaint_id": "CMP-31877", "received": "2026-06-19",
         "category": "VOLTAGE_QUALITY", "closed": "2026-06-23",
         "resolution": "Closed — no fault found. No site visit recorded."},
        {"complaint_id": "CMP-32544", "received": "2026-07-28",
         "category": "VOLTAGE_QUALITY", "closed": "2026-08-01",
         "resolution": "Closed — consumer not contactable. No site visit "
                       "recorded."},
    ],
    "DL-9982334": [], "DL-4471002": [],
}

OUTAGES: dict[str, list[dict]] = {
    "F-19-URL": [{"date": "2026-08-14", "duration_min": 214,
                  "cause": "DT-7745 LV fuse"},
                 {"date": "2026-08-22", "duration_min": 96,
                  "cause": "feeder trip, cause not recorded"}],
    "F-11-KHR": [], "F-07-HDP": [{"date": "2026-08-15", "duration_min": 47,
                                  "cause": "DT-4587 trip, no fault found"}],
    "F-03-WNW": [],
}

# --- call centre -----------------------------------------------------------

CALLS: dict[str, dict] = {
    # Opens as a bill query, is actually a payment-arrangement call, and the
    # agent gets a fact wrong that the ledger disproves.
    "CALL-77201": {
        "call_id": "CALL-77201", "consumer_no": "DL-4471002",
        "date": "2026-08-30", "duration_sec": 407, "agent_id": "AG-114",
        "transcript": [
            {"t": "00:04", "who": "agent", "text": "Good morning, DISCOM helpline, how may I help you?"},
            {"t": "00:09", "who": "consumer", "text": "Yes, I am getting messages about disconnection. I have a bill of nine thousand something. I have never had this problem before."},
            {"t": "00:22", "who": "agent", "text": "Let me check. Consumer number please."},
            {"t": "00:31", "who": "consumer", "text": "DL four four seven one zero zero two."},
            {"t": "00:48", "who": "agent", "text": "Yes sir, three bills are unpaid. June, July, August. No payment received since May."},
            {"t": "00:57", "who": "consumer", "text": "That is not right, I paid in July. I have the message on my phone. Four thousand two hundred, I paid it."},
            {"t": "01:09", "who": "agent", "text": "Sir, the system is not showing any payment. You have to pay the full amount otherwise disconnection will happen."},
            {"t": "01:21", "who": "consumer", "text": "But I am telling you I paid. And listen, I lost my job in June. I can pay some now and the rest next month. Can that be done?"},
            {"t": "01:38", "who": "agent", "text": "Sir, for instalment you have to come to the office and apply."},
            {"t": "01:44", "who": "consumer", "text": "I cannot come during working hours. Is there no other way? Can you note it down at least?"},
            {"t": "01:55", "who": "agent", "text": "I will look into it. Anything else?"},
            {"t": "02:01", "who": "consumer", "text": "So what happens about the disconnection? Will it be stopped?"},
            {"t": "02:07", "who": "agent", "text": "I cannot say. Pay as soon as possible. Thank you for calling."},
        ],
    },
}

# The payment the agent said did not exist. It did.
PAYMENT_RECEIPTS: dict[str, list[dict]] = {
    "DL-4471002": [
        {"date": "2026-07-14", "amount": 4200.0, "mode": "UPI",
         "receipt": "RCT-2026-0714-99183",
         "note": "Received and receipted. Posted to a suspense account on "
                 "2026-07-16 and not applied to the consumer ledger."},
    ],
}

# --- forecasting -----------------------------------------------------------

FORECASTS: dict[str, dict] = {
    "F-07-HDP": {
        "scope": "F-07-HDP", "level": "feeder", "horizon": "2026-09",
        "forecast_peak_mw": 4.12, "forecast_energy_mwh": 1310,
        "model": "SARIMAX with temperature regressor",
        "assumptions": {"mean_temp_c": 29.5, "festival_days": 0,
                        "agricultural_share_pct": 0,
                        "structural_changes": "none assumed"},
        # September 2026 carries Ganesh Chaturthi in this region; the forecast
        # assumed none, which is the reviewable error.
        "recent_accuracy": [
            {"month": "2026-05", "forecast_mwh": 1240, "actual_mwh": 1331},
            {"month": "2026-06", "forecast_mwh": 1265, "actual_mwh": 1352},
            {"month": "2026-07", "forecast_mwh": 1288, "actual_mwh": 1401},
            {"month": "2026-08", "forecast_mwh": 1295, "actual_mwh": 1388},
        ],
    },
}

WEATHER: dict[str, dict] = {
    "Pune East": {"area": "Pune East", "period": "2026-09",
                  "normal_mean_temp_c": 27.8, "forecast_mean_temp_c": 31.2,
                  "note": "3.4 C above the normal-year mean used by most "
                          "seasonal models.",
                  "calendar": [{"date": "2026-09-15", "event": "Ganesh Chaturthi"},
                               {"date": "2026-09-16", "event": "public holiday"}]},
}

# --- management rollups ----------------------------------------------------

DIVISIONS: dict[str, dict] = {
    "Pune East": {"division": "Pune East", "consumers": 214_500,
                  "td_count": 3_180, "pd_conversions_ytd": 412,
                  "billed_cr": 188.4, "collected_cr": 171.2,
                  "collection_efficiency_pct": 90.9, "at_c_loss_pct": 16.2,
                  "period_note": "Collection figure for the current month is "
                                 "provisional and covers 1-28 only."},
    "Pune West": {"division": "Pune West", "consumers": 190_200,
                  "td_count": 2_040, "pd_conversions_ytd": 96,
                  "billed_cr": 176.1, "collected_cr": 168.9,
                  "collection_efficiency_pct": 95.9, "at_c_loss_pct": 11.4},
    "Pune Rural": {"division": "Pune Rural", "consumers": 98_700,
                   "td_count": 4_910, "pd_conversions_ytd": 288,
                   "billed_cr": 121.7, "collected_cr": 98.3,
                   "collection_efficiency_pct": 80.8, "at_c_loss_pct": 24.7,
                   "period_note": "Boundary revised on 2026-06-01; 11,200 "
                                  "consumers transferred in from Pune East. "
                                  "Month-on-month comparisons before and after "
                                  "that date are not like for like."},
}
