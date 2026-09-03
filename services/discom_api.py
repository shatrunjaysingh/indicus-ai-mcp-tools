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
import discom_portfolio as portfolio
import csv
import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

# Where this deployment is reachable from a browser, so an export link can be
# handed to someone rather than being a path they have to assemble. Caddy routes
# /discom/exports/* to this service; see deploy/caddy/Caddyfile in the platform
# repository.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8304").rstrip("/")

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


# --- the collection portfolio ----------------------------------------------
# Use case 1 is a book-level problem: score everyone, segment, size a campaign,
# forecast the month. These tools do the scoring and the arithmetic; what they
# deliberately do not do is choose. Which segments to work, on what channel, at
# what capacity, and what to leave alone is the judgement, and it is the
# agent's.

@app.get("/portfolio", operation_id="getCollectionPortfolio",
         summary="The whole outstanding book: totals and behavioural segments, scored")
def get_portfolio() -> dict:
    """Every outstanding consumer, segmented, with expected recovery per segment.

    `expected_recovery` is outstanding x payment probability. Ranking on it
    rather than on the balance is the entire point: the segment holding the
    most money is not the segment that yields the most, and a campaign built on
    the balance column works the accounts least likely to pay.
    """
    totals = portfolio.SEGMENT_TOTALS
    accounts = sum(v["accounts"] for v in totals.values())
    segments = []
    for name, meta in portfolio.SEGMENTS.items():
        v = totals.get(name)
        if not v or not v["accounts"]:
            continue
        segments.append({
            "segment": name, "label": meta["label"],
            "definition": meta["definition"],
            "accounts": v["accounts"],
            "outstanding": round(v["outstanding"], 2),
            "expected_recovery": round(v["expected"], 2),
            "mean_payment_probability": round(v["p_sum"] / v["accounts"], 3),
            "mean_outstanding": round(v["outstanding"] / v["accounts"], 2),
            "historical_response_by_channel": meta["response"],
            "note": meta["note"],
        })
    segments.sort(key=lambda x: x["expected_recovery"], reverse=True)
    return {
        "population": accounts,
        "total_outstanding": round(sum(v["outstanding"] for v in totals.values()), 2),
        "total_expected_recovery": round(sum(v["expected"] for v in totals.values()), 2),
        "segments": segments,
        "by_division": {
            d: {"accounts": v["accounts"],
                "outstanding": round(v["outstanding"], 2),
                "expected_recovery": round(v["expected"], 2)}
            for d, v in portfolio.DIVISION_TOTALS.items()
        },
        "scoring_note": (
            "Payment probability comes from a scoring model run over the whole "
            "book. It is not produced by the agent. getConsumerScore returns "
            "the features behind any individual score."
        ),
    }


@app.get("/portfolio/campaign", operation_id="buildCampaignList",
         summary="Select the top N accounts for a channel, and size the campaign")
def build_campaign(channel: str = "field_visit", capacity: int = 0,
                   exclude_disputed: bool = True,
                   exclude_vacated: bool = True,
                   min_outstanding: float = 0,
                   min_chronic_risk: float = 0,
                   division: str | None = None) -> dict:
    """The working list: the highest expected-recovery accounts a channel can
    reach, with what the selection is worth.

    This is the deliverable — from the whole book, the N accounts a field team
    should actually visit. The selection is done here rather than by the agent
    because it is a ranking over a million rows; what the agent decides is the
    channel, the capacity, and what to exclude, which is where the judgement
    is.

    Excluded groups are counted rather than silently dropped. A campaign that
    does not say what it left out cannot be reviewed.
    """
    spec = portfolio.CHANNELS.get(channel)
    if spec is None:
        raise HTTPException(
            404, f"Unknown channel {channel}. "
                 f"Known: {', '.join(portfolio.CHANNELS)}.")
    cap = capacity if capacity > 0 else spec["capacity_per_month"]
    if cap > spec["capacity_per_month"]:
        raise HTTPException(
            400,
            f"{channel} capacity is {spec['capacity_per_month']:,} per month; "
            f"{cap:,} was requested. A campaign that exceeds the capacity is "
            f"not executable.")

    excluded = {}
    if exclude_disputed:
        excluded["disputed"] = portfolio.SEGMENT_TOTALS["disputed"]["accounts"]
    if exclude_vacated:
        excluded["gone_away"] = portfolio.SEGMENT_TOTALS["gone_away"]["accounts"]

    source = portfolio.AT_RISK if min_chronic_risk > 0 else portfolio.TOP
    pool = [
        a for a in source
        if a.outstanding >= min_outstanding
        # Disconnection is the one channel with a legal precondition. A
        # high-value account with no served notice is not a target, however far
        # up the ranking it sits.
        and (channel != "disconnection" or a.dc_eligible)
        # So an early-warning population can be turned straight into a
        # campaign. Identifying who is about to become chronic is only worth
        # anything if it produces a list somebody works.
        and a.chronic_risk >= min_chronic_risk
        and (division is None or a.division == division)
        and not (exclude_disputed and a.segment == "disputed")
        and not (exclude_vacated and a.segment == "gone_away")
    ]
    selected = pool[:cap]
    exp = sum(a.expected_recovery for a in selected)
    due = sum(a.outstanding for a in selected)
    cost = len(selected) * spec["cost_per_account"]

    from collections import Counter
    mix = Counter(a.segment for a in selected)
    blocked = Counter(
        a.dc_blocked_by for a in source
        if channel == "disconnection" and not a.dc_eligible)

    return {
        "population": sum(v["accounts"] for v in portfolio.SEGMENT_TOTALS.values()),
        "selected": len(selected),
        "channel": channel,
        "capacity_used": f"{len(selected):,} of {spec['capacity_per_month']:,}",
        "selection_criteria": {
            "ranked_by": "expected_recovery = outstanding x payment_probability",
            "min_outstanding": min_outstanding,
            "min_chronic_risk": min_chronic_risk,
            "division": division or "all",
            "excluded_segments": excluded or "none",
        },
        "outstanding_selected": round(due, 2),
        "expected_recovery": round(exp, 2),
        "campaign_cost": round(cost, 2),
        "return_per_rupee_cost": round(exp / cost, 1) if cost else None,
        "segment_mix": dict(mix.most_common()),
        "disconnection_ineligible": dict(blocked.most_common()) or None,
        "sample": [
            {"consumer_no": a.consumer_no, "division": a.division,
             "segment": a.segment, "outstanding": a.outstanding,
             "payment_probability": a.payment_probability,
             "expected_recovery": a.expected_recovery}
            for a in selected[:10]
        ],
        "note": (
            f"Ranked list of {len(selected):,} accounts. The full list is "
            f"exported to the field system; the sample above is the top ten."
        ),
    }


@app.get("/portfolio/accounts", operation_id="listCollectionTargets",
         summary="Accounts ranked by expected recovery, filterable for a campaign")
def list_targets(segment: str | None = None, division: str | None = None,
                 min_outstanding: float = 0, min_probability: float = 0,
                 limit: int = 20) -> dict:
    """The ranked working list for a campaign, highest expected recovery first.

    `limit` caps what is returned, not what was matched: `matched` is the size
    of the real target list and is the number a campaign is sized against.
    Returning the whole book to a language model would be both useless and
    expensive.
    """
    rows = [
        a for a in portfolio.TOP
        if (segment is None or a.segment == segment)
        and (division is None or a.division == division)
        and a.outstanding >= min_outstanding
        and a.payment_probability >= min_probability
    ]
    rows.sort(key=lambda a: a.expected_recovery, reverse=True)
    shown = rows[: max(1, min(limit, 100))]
    return {
        "matched": len(rows),
        "returned": len(shown),
        "matched_outstanding": round(sum(a.outstanding for a in rows), 2),
        "matched_expected_recovery": round(sum(a.expected_recovery for a in rows), 2),
        "filters_applied": {
            "segment": segment or "all", "division": division or "all",
            "min_outstanding": min_outstanding,
            "min_probability": min_probability,
            "boundaries": "both minimums are inclusive (>=)",
            "ranked_by": "expected_recovery = outstanding x payment_probability",
        },
        "accounts": [
            {"consumer_no": a.consumer_no, "division": a.division,
             "category": a.category, "segment": a.segment,
             "outstanding": a.outstanding,
             "payment_probability": a.payment_probability,
             "expected_recovery": a.expected_recovery,
             "unpaid_cycles": a.unpaid_cycles,
             "notices_ignored": a.notices_ignored}
            for a in shown
        ],
    }


@app.get("/portfolio/consumers/{consumer_no}/score", operation_id="getConsumerScore",
         summary="One account's payment probability and the features behind it")
def get_score(consumer_no: str) -> dict:
    """The score with its inputs.

    Returned with the contribution of each feature so a score can be explained
    to the person acting on it. A collection review's first question is always
    why this account and not that one, and a probability with no derivation
    cannot answer it.
    """
    acc = portfolio.BY_NO.get(consumer_no.upper())
    if acc is None:
        raise HTTPException(
            404, f"No account {consumer_no} in the collection book.")
    return {
        "consumer_no": acc.consumer_no, "division": acc.division,
        "category": acc.category, "segment": acc.segment,
        "segment_label": portfolio.SEGMENTS[acc.segment]["label"],
        "outstanding": acc.outstanding,
        "payment_probability": acc.payment_probability,
        "expected_recovery": acc.expected_recovery,
        "feature_contributions": acc.features,
        "inputs": {
            "unpaid_cycles": acc.unpaid_cycles,
            "days_since_last_payment": acc.days_since_last_payment,
            "on_time_ratio": acc.on_time_ratio,
            "notices_ignored": acc.notices_ignored,
            "broken_promises": acc.broken_promises,
            "connection_age_months": acc.connection_age_months,
            "has_open_dispute": acc.has_open_dispute,
            "consumption_last_period": acc.consumption_last_period,
        },
    }


@app.get("/portfolio/early-warning", operation_id="listEarlyWarning",
         summary="Accounts most likely to become chronic defaulters, ranked")
def list_early_warning(limit: int = 20, min_risk: float = 0.5,
                       division: str | None = None) -> dict:
    """Accounts heading for chronic default, before they get there.

    Ranked on chronic risk, not on payment probability — they answer different
    questions. Payment probability is about collecting this month; chronic risk
    is about whether this account is still collectable next year. An account
    can be low risk and unlikely to pay now, or high risk and paying today.

    Accounts already chronic score zero. The point is who can still be caught.
    """
    rows = [
        a for a in portfolio.AT_RISK
        if a.chronic_risk >= min_risk
        and (division is None or a.division == division)
    ]
    rows.sort(key=lambda a: a.chronic_risk, reverse=True)
    totals = portfolio.SEGMENT_TOTALS
    return {
        "population_at_risk": sum(v["at_risk"] for v in totals.values()),
        "population_at_risk_outstanding": round(
            sum(v["at_risk_outstanding"] for v in totals.values()), 2),
        "at_risk_threshold": portfolio.AT_RISK_THRESHOLD,
        "matched_in_working_list": len(rows),
        "note": ("population_at_risk counts the whole book above the threshold. "
                 "The rows below are the highest-risk accounts from the "
                 "materialised working list, ranked. Raise `limit` for a longer "
                 "list, or call buildCampaignList with min_chronic_risk to size "
                 "an intervention against this population and get the full "
                 "selection with its cost and expected recovery."),
        "accounts": [
            {"consumer_no": a.consumer_no, "division": a.division,
             "segment": a.segment, "outstanding": a.outstanding,
             "chronic_risk": a.chronic_risk,
             "payment_probability": a.payment_probability,
             "unpaid_cycles": a.unpaid_cycles,
             "notices_ignored": a.notices_ignored,
             "broken_promises": a.broken_promises}
            for a in rows[: max(1, min(limit, 100))]
        ],
    }


@app.get("/portfolio/export", operation_id="exportDefaulterList",
         summary="Write the matching accounts to a CSV file and return its link")
def export_list(segment: str | None = None, min_chronic_risk: float = 0,
                min_outstanding: float = 0, min_probability: float = 0,
                division: str | None = None,
                dc_eligible_only: bool = False) -> dict:
    """Export the full matching list to CSV, and return where it is.

    **The rows do not come back through this call.** A list of fifty thousand
    accounts costs nothing to write to a file and a great deal to pass through
    a language model — tens of lakhs of tokens, most of a context window, and a
    reply nobody can read. The file is written by this service; what comes back
    is the row count, the columns, the link, and five rows so the caller can
    see the shape.

    Scans the whole book rather than the materialised pools, so an export is
    complete rather than the top slice of a ranking.
    """
    exports = Path(__file__).resolve().parent / "_exports"
    exports.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    name = f"defaulters-{stamp}.csv"
    path = exports / name

    columns = [
        "consumer_no", "division", "category", "segment", "outstanding",
        "payment_probability", "expected_recovery", "chronic_risk",
        "unpaid_cycles", "days_since_last_payment", "on_time_ratio",
        "notices_ignored", "broken_promises", "has_open_dispute",
        "dc_eligible", "dc_blocked_by",
    ]

    rows = 0
    total_due = 0.0
    total_expected = 0.0
    preview: list[dict] = []
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for a in portfolio.stream_book():
            if segment and a.segment != segment:
                continue
            if a.chronic_risk < min_chronic_risk:
                continue
            if a.outstanding < min_outstanding:
                continue
            if a.payment_probability < min_probability:
                continue
            if division and a.division != division:
                continue
            if dc_eligible_only and not a.dc_eligible:
                continue
            record = {c: getattr(a, c) for c in columns}
            writer.writerow(record)
            rows += 1
            total_due += a.outstanding
            total_expected += a.expected_recovery
            if len(preview) < 5:
                preview.append(record)

    return {
        "rows": rows,
        "file": name,
        "download_url": f"{PUBLIC_BASE_URL}/discom/exports/{name}",
        "size_kb": round(path.stat().st_size / 1024, 1),
        "columns": columns,
        "filters_applied": {
            "segment": segment or "all",
            "min_chronic_risk": min_chronic_risk,
            "min_outstanding": min_outstanding,
            "min_probability": min_probability,
            "division": division or "all",
            "dc_eligible_only": dc_eligible_only,
        },
        "total_outstanding": round(total_due, 2),
        "total_expected_recovery": round(total_expected, 2),
        "preview": preview,
        "note": ("Full list written to the file. Open it in Excel or import it "
                 "to the field system; do not ask for the rows in chat."),
    }


@app.get("/exports/{name}", include_in_schema=False)
def download_export(name: str) -> FileResponse:
    """Serve a written export. Not a tool — a browser link."""
    # Name comes from a URL, so it is not trusted to be a bare filename.
    if "/" in name or "\\" in name or name.startswith("."):
        raise HTTPException(400, "Bad export name.")
    path = Path(__file__).resolve().parent / "_exports" / name
    if not path.is_file():
        raise HTTPException(404, f"No export {name}.")
    return FileResponse(path, media_type="text/csv", filename=name)


@app.get("/portfolio/channels", operation_id="getRecoveryChannels",
         summary="Cost and monthly capacity of each recovery channel")
def get_channels() -> dict:
    """What each channel costs per account and how many it can do in a month.

    Field capacity is the binding constraint in every collection programme.
    It is what turns targeting into an optimisation rather than a ranking:
    6,000 visits against 24,000 outstanding accounts means choosing.
    """
    return {
        "channels": [{"channel": k, **v} for k, v in portfolio.CHANNELS.items()],
        "note": ("Capacities are per month for the whole book. A campaign that "
                 "exceeds one is not a plan."),
    }


@app.get("/portfolio/campaigns", operation_id="getCampaignHistory",
         summary="Past collection campaigns: channel, segment, cost and recovery")
def get_campaigns() -> dict:
    """What has already been tried and what it returned.

    Included because the most common collection mistake is repeating a campaign
    that did not work, and the record of it is usually in a spreadsheet nobody
    consults before the next one is planned.
    """
    return {"campaigns": portfolio.CAMPAIGNS}


@app.get("/portfolio/forecast", operation_id="getCollectionForecast",
         summary="Expected collection for the coming month, with track record")
def get_collection_forecast(division: str | None = None) -> dict:
    """Expected collection, and how the last six forecasts performed.

    The track record is returned unaggregated so the shape of the error shows.
    A forecast that is consistently over is a different problem from one that
    scatters, and only the first means the target being set is unreachable.
    """
    totals = portfolio.DIVISION_TOTALS
    if division:
        if division not in totals:
            raise HTTPException(
                404, f"No division {division}. Known: {', '.join(totals)}.")
        baseline = totals[division]["expected"]
        count = totals[division]["accounts"]
    else:
        baseline = sum(v["expected"] for v in totals.values())
        count = sum(v["accounts"] for v in totals.values())
    return {
        "division": division or "all",
        "method": ("Sum of per-account expected recovery, adjusted for the "
                   "share historically collected within the month rather than "
                   "eventually."),
        "accounts": count,
        "gross_expected_recovery": round(baseline, 2),
        "within_month_share": 0.58,
        "forecast_collection_next_month": round(baseline * 0.58, 2),
        "recent_accuracy": portfolio.FORECAST_HISTORY,
        "caveat": ("Excludes any campaign not yet run. A forecast is what the "
                   "book yields at current effort, not a target."),
    }
