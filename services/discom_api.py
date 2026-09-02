"""Stand-in DISCOM systems: billing, metering, network, complaints, calls.

One service standing in for what would be several systems of record at a real
distribution utility — CRM, billing, MDM, GIS, the complaint system and the
call centre. Every route carries an `operation_id`, so each is both a REST tool
and an MCP tool; see mcp_server.py.

Read-only by design. Every one of these tools feeds a judgement that can end
with someone's supply disconnected or a prosecution, and a demo where an agent
can also *write* to the systems of record is a demo of something nobody should
deploy.
"""

from __future__ import annotations

import discom_data as data
from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="DISCOM systems (demo)",
    description=__doc__,
    version="1.0.0",
)


def _consumer(consumer_no: str) -> dict:
    row = data.CONSUMERS.get(consumer_no.upper())
    if row is None:
        raise HTTPException(404, f"No consumer {consumer_no}.")
    return row


# --- consumer and billing --------------------------------------------------

@app.get("/consumers/{consumer_no}", operation_id="getConsumer",
         summary="Consumer record: category, load, tariff, location, status")
def get_consumer(consumer_no: str) -> dict:
    """Identity, connected and sanctioned load, category, feeder and DT, supply
    status, and the current outstanding balance."""
    row = dict(_consumer(consumer_no))
    row["arrear_breakdown"] = data.ARREARS.get(row["consumer_no"], [])
    row["load_changes"] = data.LOAD_CHANGES.get(row["consumer_no"], [])
    return row


@app.get("/consumers/{consumer_no}/billing", operation_id="getBillingHistory",
         summary="Billed amounts by period, and whether each was actual or estimated")
def get_billing(consumer_no: str) -> dict:
    """Every billed period with units, basis and amount.

    `basis` matters more than the amount: a run of `estimated` periods followed
    by an `actual` read produces a large catch-up bill that looks to the
    consumer like a fault, and is the most common cause of a "meter running
    fast" complaint.
    """
    row = _consumer(consumer_no)
    bills = data.billing_for(row["consumer_no"])
    estimated = [b for b in bills if b["basis"] == "estimated"]
    return {
        "consumer_no": row["consumer_no"],
        "periods": bills,
        "estimated_period_count": len(estimated),
        "consecutive_estimated_before_last_actual": _run_of_estimates(bills),
        "outstanding": row["outstanding"],
        "arrear_breakdown": data.ARREARS.get(row["consumer_no"], []),
    }


def _run_of_estimates(bills: list[dict]) -> int:
    """How many estimated periods immediately precede the last actual read.

    Stated rather than left to be counted off the list: this single number
    separates a catch-up bill from a metering fault, and an agent that has to
    derive it by eye gets it wrong on a 24-row table.
    """
    run = 0
    for bill in reversed(bills):
        if bill["basis"] == "actual":
            break
    for bill in reversed(bills[:-1] if bills else []):
        if bill["basis"] == "estimated":
            run += 1
        else:
            break
    return run


@app.get("/consumers/{consumer_no}/payments", operation_id="getPaymentHistory",
         summary="Payment record by period, promises to pay, and receipts")
def get_payments(consumer_no: str) -> dict:
    """Per-period payment status, with counts already totalled.

    The counts are the point. Payment *behaviour* decides the recovery action,
    and a consumer who pays late every month is a different case from one who
    has stopped paying, though both show a balance.
    """
    row = _consumer(consumer_no)
    records = data.PAYMENTS.get(row["consumer_no"], [])
    counts = {s: sum(1 for r in records if r["status"] == s)
              for s in ("paid_on_time", "paid_late", "unpaid")}
    trailing = 0
    for rec in reversed(records):
        if rec["status"] == "unpaid":
            trailing += 1
        else:
            break
    return {
        "consumer_no": row["consumer_no"],
        "periods": records,
        "counts": counts,
        "consecutive_unpaid_now": trailing,
        "promises_to_pay": data.PROMISES.get(row["consumer_no"], []),
        "receipts": data.PAYMENT_RECEIPTS.get(row["consumer_no"], []),
    }


@app.get("/consumers/{consumer_no}/consumption", operation_id="getConsumptionHistory",
         summary="Metered consumption by period, actual or estimated")
def get_consumption(consumer_no: str) -> dict:
    """Units by period. Read `basis` before drawing any conclusion from a
    change: estimated periods carry no information about actual usage."""
    row = _consumer(consumer_no)
    series = data.CONSUMPTION[row["consumer_no"]]
    actual = [r["units"] for r in series if r["basis"] == "actual"]
    return {
        "consumer_no": row["consumer_no"],
        "periods": series,
        "mean_actual_units": round(sum(actual) / len(actual), 1) if actual else 0,
        "connected_load_kw": row["connected_load_kw"],
        "sanctioned_load_kw": row["sanctioned_load_kw"],
        "load_changes": data.LOAD_CHANGES.get(row["consumer_no"], []),
    }


@app.get("/consumers/{consumer_no}/notices", operation_id="getNoticeHistory",
         summary="Notices and reminders served, and whether they were delivered")
def get_notices(consumer_no: str) -> dict:
    """What recovery action has already been tried, and what it achieved.

    An undelivered notice is not a served notice, and a recovery step that has
    already failed twice should not be recommended a third time.
    """
    row = _consumer(consumer_no)
    return {"consumer_no": row["consumer_no"],
            "notices": data.NOTICES.get(row["consumer_no"], [])}


# --- disconnection and metering --------------------------------------------

@app.get("/consumers/{consumer_no}/disconnection", operation_id="getDisconnectionRecord",
         summary="Disconnection record: date, method, execution, restorations")
def get_disconnection(consumer_no: str) -> dict:
    """The TD/PD record.

    `executed_on` and `field_acknowledgement` decide whether a disconnection
    actually happened. An order raised and closed in the system with neither is
    not evidence that supply was cut, and every illegal-restoration case rests
    on that distinction.
    """
    row = _consumer(consumer_no)
    rec = data.DISCONNECTIONS.get(row["consumer_no"])
    if rec is None:
        return {"consumer_no": row["consumer_no"], "status": row["supply_status"],
                "disconnection_record": None}
    return rec


@app.get("/meters/{meter_no}", operation_id="getMeterStatus",
         summary="Meter record: type, last read, communication, tamper events")
def get_meter(meter_no: str) -> dict:
    """Meter identity and health, with the tamper log.

    A tamper event with no matching work order is evidence; one with a work
    order is maintenance. The log records both and does not distinguish them
    for you.
    """
    row = data.METERS.get(meter_no.upper())
    if row is None:
        raise HTTPException(404, f"No meter {meter_no}.")
    return row


@app.get("/consumers/{consumer_no}/survey", operation_id="getSiteSurvey",
         summary="Field site survey findings for a premises")
def get_survey(consumer_no: str) -> dict:
    """What a surveyor recorded at the premises. Where a survey and a desk
    inference disagree, the survey is the evidence."""
    row = _consumer(consumer_no)
    survey = data.SURVEYS.get(row["consumer_no"])
    if survey is None:
        return {"consumer_no": row["consumer_no"], "survey": None,
                "note": "No site survey on record for this consumer."}
    return survey


@app.get("/surveys/{consumer_no}/images", operation_id="getSurveyImageAnalysis",
         summary="Image-analysis detections and OCR from survey photographs")
def get_survey_images(consumer_no: str) -> dict:
    """Detections and OCR from the survey photographs.

    These are another system's *claims*, each with a confidence, not
    observations. `not_captured` is as important as the detections: a seal that
    was not photographed is not a missing seal.
    """
    row = _consumer(consumer_no)
    analysis = data.SURVEY_IMAGES.get(row["consumer_no"])
    if analysis is None:
        return {"consumer_no": row["consumer_no"], "analysis": None,
                "note": "No survey imagery analysed for this consumer."}
    return analysis


@app.get("/consumers/{consumer_no}/peers", operation_id="getPeerBenchmark",
         summary="Consumption of comparable consumers, as a distribution")
def get_peers(consumer_no: str) -> dict:
    """The subject against its cohort.

    Returned as a distribution rather than a single average on purpose. Peers
    are never exactly comparable, and a benchmark quoted as one number invites
    a weak signal to be treated as a strong one.
    """
    row = _consumer(consumer_no)
    peers = data.PEERS.get(row["consumer_no"])
    if peers is None:
        return {"consumer_no": row["consumer_no"], "benchmark": None,
                "note": "No comparable cohort established for this consumer."}
    return peers


# --- network ---------------------------------------------------------------

@app.get("/assets/{asset_id}", operation_id="getDTHealth",
         summary="Distribution asset condition: loading, thermal, maintenance, failures")
def get_asset(asset_id: str) -> dict:
    """Condition and history for a DT or transformer.

    Trends are returned as series, not as current values, because the rate of
    change is the signal and the level is only context.
    """
    row = data.ASSETS.get(asset_id.upper())
    if row is None:
        raise HTTPException(404, f"No asset {asset_id}.")
    return row


@app.get("/assets/{asset_id}/load", operation_id="getLoadHistory",
         summary="Loading history for an asset or feeder")
def get_load(asset_id: str) -> dict:
    """Monthly peak loading as a percentage of rating."""
    row = data.ASSETS.get(asset_id.upper())
    if row is None:
        raise HTTPException(404, f"No asset {asset_id}.")
    return {"asset_id": row["asset_id"], "rating_kva": row["rating_kva"],
            "load_pct_trend": row["load_pct_trend"],
            "phase_imbalance_pct": row["phase_imbalance_pct"]}


@app.get("/assets/{asset_id}/maintenance", operation_id="getMaintenanceHistory",
         summary="Maintenance, failures and trips for an asset")
def get_maintenance(asset_id: str) -> dict:
    """Maintenance cycle, last attendance, failures and trips.

    A trip recorded as "restored, no fault found" is not a clean record —
    repeats of it are the classic signature of an intermittent developing
    fault, and they are returned here rather than filtered out.
    """
    row = data.ASSETS.get(asset_id.upper())
    if row is None:
        raise HTTPException(404, f"No asset {asset_id}.")
    return {"asset_id": row["asset_id"],
            "last_maintenance": row["last_maintenance"],
            "maintenance_cycle_months": row["maintenance_cycle_months"],
            "installed": row["installed"],
            "failures": row["failures"], "trips": row["trips"],
            "consumers_served": row["consumers_served"],
            "critical_loads": row["critical_loads"],
            "alternative_feed": row["alternative_feed"]}


@app.get("/feeders/{feeder_id}/losses", operation_id="getFeederLosses",
         summary="Energy in against energy billed for a feeder")
def get_feeder_losses(feeder_id: str) -> dict:
    """Feeder-level loss.

    Loss locates an area worth investigating. It is never evidence against any
    particular consumer on the feeder, and must not contribute to an individual
    consumer's anomaly score.
    """
    row = data.FEEDERS.get(feeder_id.upper())
    if row is None:
        raise HTTPException(404, f"No feeder {feeder_id}.")
    return row


@app.get("/feeders/{feeder_id}/outages", operation_id="getOutageHistory",
         summary="Recorded outages on a feeder")
def get_outages(feeder_id: str) -> dict:
    """Outages, with cause where one was recorded."""
    key = feeder_id.upper()
    if key not in data.FEEDERS:
        raise HTTPException(404, f"No feeder {feeder_id}.")
    return {"feeder_id": key, "outages": data.OUTAGES.get(key, [])}


@app.get("/feeders/{feeder_id}/forecast", operation_id="getLoadForecast",
         summary="Demand forecast for a feeder, with assumptions and track record")
def get_forecast(feeder_id: str) -> dict:
    """The forecast, what it assumed, and how recent forecasts performed.

    `recent_accuracy` is returned unaggregated so the *shape* of the error is
    visible. A consistent one-directional miss is a different problem from
    scatter of the same magnitude, and a mean absolute error hides which one
    you have.
    """
    row = data.FORECASTS.get(feeder_id.upper())
    if row is None:
        raise HTTPException(404, f"No forecast for {feeder_id}.")
    return row


@app.get("/weather/{area}", operation_id="getWeatherContext",
         summary="Temperature outlook and calendar events for an area")
def get_weather(area: str) -> dict:
    """Temperature against the normal-year mean, plus festivals and holidays in
    the horizon — the two assumptions most likely to break a demand forecast."""
    row = data.WEATHER.get(area)
    if row is None:
        raise HTTPException(404, f"No weather context for {area}.")
    return row


# --- complaints and calls --------------------------------------------------

@app.get("/complaints/{complaint_id}", operation_id="getComplaint",
         summary="One complaint with its text and channel")
def get_complaint(complaint_id: str) -> dict:
    """The complaint as the consumer wrote it. Read it for danger before
    categorising it: safety wording is often buried inside a billing query."""
    row = data.COMPLAINTS.get(complaint_id.upper())
    if row is None:
        raise HTTPException(404, f"No complaint {complaint_id}.")
    return row


@app.get("/complaints", operation_id="listComplaints",
         summary="Open complaints in the queue")
def list_complaints(status: str | None = None) -> dict:
    """Complaints, optionally filtered by status."""
    rows = [c for c in data.COMPLAINTS.values()
            if status is None or c["status"] == status]
    return {"count": len(rows), "complaints": rows}


@app.get("/consumers/{consumer_no}/complaints", operation_id="getComplaintHistory",
         summary="Prior complaints for a consumer, and how each was closed")
def get_complaint_history(consumer_no: str) -> dict:
    """Prior complaints.

    How a complaint was *closed* matters as much as that it was: repeated
    closures with no site visit recorded are the pattern behind most
    escalations to a regulator.
    """
    row = _consumer(consumer_no)
    prior = data.COMPLAINT_HISTORY.get(row["consumer_no"], [])
    return {"consumer_no": row["consumer_no"], "prior_complaints": prior,
            "count": len(prior)}


@app.get("/calls/{call_id}", operation_id="getCallTranscript",
         summary="Call-centre transcript with speaker attribution and timestamps")
def get_call(call_id: str) -> dict:
    """A transcribed call, turn by turn, with timestamps for citation."""
    row = data.CALLS.get(call_id.upper())
    if row is None:
        raise HTTPException(404, f"No call {call_id}.")
    return row


# --- management ------------------------------------------------------------

@app.get("/td-consumers", operation_id="listTDConsumers",
         summary="Temporarily disconnected consumers, filterable by dues and TD age")
def list_td(min_outstanding: float = 0, min_td_days: int = 0,
            division: str | None = None) -> dict:
    """TD consumers matching the filters.

    `filters_applied` is echoed back deliberately. Boundary choices — whether
    the threshold is inclusive, what the day count runs from — change these
    numbers materially, and a caller who cannot see them cannot check the
    answer.
    """
    rows = []
    for consumer_no, rec in data.DISCONNECTIONS.items():
        consumer = data.CONSUMERS[consumer_no]
        if consumer["outstanding"] < min_outstanding:
            continue
        if rec["td_days"] < min_td_days:
            continue
        if division and consumer["division"] != division:
            continue
        rows.append({"consumer_no": consumer_no, "name": consumer["name"],
                     "division": consumer["division"],
                     "outstanding": consumer["outstanding"],
                     "td_days": rec["td_days"], "td_date": rec["td_date"]})
    rows.sort(key=lambda r: r["outstanding"], reverse=True)
    return {
        "count": len(rows),
        "filters_applied": {
            "min_outstanding": min_outstanding,
            "min_outstanding_boundary": "inclusive (>=)",
            "min_td_days": min_td_days,
            "min_td_days_measured_from": "date of disconnection",
            "division": division or "all",
        },
        "consumers": rows,
    }


@app.get("/divisions/{division}", operation_id="getDivisionSummary",
         summary="Division rollup: consumers, TD, conversions, collection, losses")
def get_division(division: str) -> dict:
    """Division-level figures.

    `period_note` carries the things that make a month-on-month comparison
    invalid — a provisional partial month, a boundary revision. Read it before
    comparing anything, because those explain more apparent movements than any
    change in performance.
    """
    row = data.DIVISIONS.get(division)
    if row is None:
        raise HTTPException(
            404, f"No division {division}. Known: {', '.join(data.DIVISIONS)}.")
    return row


@app.get("/divisions", operation_id="listDivisions",
         summary="All divisions with their headline figures")
def list_divisions() -> dict:
    """Every division. Denominators are included so a ranking cannot be built
    on rates alone."""
    return {"count": len(data.DIVISIONS),
            "divisions": list(data.DIVISIONS.values())}
