"""The complaint queue, classified, with the statutory clocks running.

Use case 6. Eight thousand complaints a month: category, priority, owning
department, repeat detection, escalation risk, and SLA breach prediction.

The one thing this queue must never get wrong is safety. Sparking, a burning
smell, a shock, a fallen conductor — those are a danger to life whatever else
the complaint is about, and they arrive buried inside billing queries because
that is what the consumer was already angry about. Every classification path
here checks for danger before it checks for anything else.

SLA windows are the Standards of Performance a state commission sets. They are
statutory: a breach is a compensation liability, not a service metric, which is
why predicting them before they happen is worth more than counting them
afterwards.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

SEED = 20260905
POPULATION = 8_000
NOW = datetime(2026, 9, 2, tzinfo=UTC)

DIVISIONS = ["Pune East", "Pune West", "Pune Rural"]

# Standards of Performance. Hours, and the department that owns the clock.
SLA = {
    "SAFETY_HAZARD":            {"hours": 3, "dept": "O&M Emergency"},
    "SUPPLY_OUTAGE":            {"hours": 8, "dept": "O&M"},
    "VOLTAGE_QUALITY":          {"hours": 72, "dept": "O&M"},
    "METER_FAULT":              {"hours": 360, "dept": "Metering"},
    "BILLING_DISPUTE":          {"hours": 168, "dept": "Billing"},
    "DISCONNECTION_RESTORATION": {"hours": 24, "dept": "Revenue"},
    "NEW_CONNECTION":           {"hours": 720, "dept": "Commercial"},
    "THEFT_REPORT":             {"hours": 168, "dept": "Vigilance"},
    "STAFF_CONDUCT":            {"hours": 336, "dept": "Administration"},
    "OTHER":                    {"hours": 168, "dept": "Consumer Services"},
}

# Complaint texts by category, written as consumers write them. Several carry
# a second issue inside the first, which is the classification problem.
TEMPLATES = {
    "BILLING_DISPUTE": [
        "Bill has suddenly increased and meter is running very fast. Last "
        "month {low} rupees, this month {high}. Nothing changed in my house.",
        "I am being charged for {units} units but the house was locked all "
        "month. Please check.",
        "Arrears showing on my bill which I have already paid. Receipt "
        "number is with me.",
        "Bill amount is wrong, average billing has been done for four months "
        "and now one big bill has come.",
    ],
    "SAFETY_HAZARD": [
        "There is sparking from the meter box outside and burning smell since "
        "evening. Please send someone urgently.",
        "Wire has fallen in front of my gate and children play there. Very "
        "dangerous.",
        "I got a shock from the meter board when switching on. Somebody must "
        "come today.",
        "Pole outside our house is leaning and the cable is very low, a truck "
        "will catch it.",
    ],
    "SUPPLY_OUTAGE": [
        "No supply since {hours} hours in our area. No information from "
        "anyone.",
        "Power went at night and has not come back. Neighbours also have no "
        "supply.",
        "Only one phase is coming, motor is not working.",
    ],
    "METER_FAULT": [
        "Meter display is blank since last week, reading is not visible.",
        "Meter is showing reading even when main switch is off.",
        "New meter was installed but reading started from wrong number.",
    ],
    "VOLTAGE_QUALITY": [
        "Voltage is very low in the afternoon, compressors are tripping.",
        "Bulbs are fusing repeatedly, voltage is fluctuating badly.",
        "Low voltage every evening between 7 and 10, fan runs slow.",
    ],
    "DISCONNECTION_RESTORATION": [
        "Payment made yesterday but supply not restored. Receipt attached.",
        "Connection was cut by mistake, my dues are cleared.",
    ],
    "NEW_CONNECTION": [
        "Applied for new connection {days} days back, no response yet.",
        "Demand note paid but meter not installed.",
    ],
    "THEFT_REPORT": [
        "My neighbour has taken direct connection from the pole. Please check.",
    ],
    "STAFF_CONDUCT": [
        "Lineman asked for money to restore my supply. I want to complain.",
        "Nobody at the office listens, I have come three times.",
    ],
}

# Safety words. Presence of any of these outranks whatever the consumer thinks
# their complaint is about.
DANGER_WORDS = ["spark", "burning smell", "shock", "fallen", "leaning",
                "smoke", "fire", "live wire"]


@dataclass
class Complaint:
    complaint_id: str
    consumer_no: str
    division: str
    channel: str
    received: str
    text: str
    true_category: str
    # --- classification ----------------------------------------------------
    category: str = ""
    priority: str = ""
    department: str = ""
    likely_cause: str = ""
    recommended_action: str = ""
    safety_override: bool = False
    # --- history and risk --------------------------------------------------
    prior_complaints: int = 0
    prior_closed_without_visit: int = 0
    is_repeat: bool = False
    escalation_risk: str = "LOW"
    # --- the clock ---------------------------------------------------------
    sla_hours: int = 0
    hours_elapsed: float = 0.0
    sla_status: str = ""          # WITHIN | AT_RISK | BREACHED
    hours_remaining: float = 0.0
    reassigned_once: bool = False
    # --- the billing context that changes the answer -----------------------
    estimated_periods_before_actual: int = 0
    resolved: bool = False
    tags: list[str] = field(default_factory=list)


def _classify(c: Complaint) -> None:
    """Category, priority, department, cause and action.

    Safety first, and not as a tie-break — as a precondition. A consumer
    writing about their bill *and* a burning smell has raised a safety incident
    with a billing query attached, and classifying by the first sentence puts a
    danger to life in a seven-day queue.
    """
    lowered = c.text.lower()
    danger = any(w in lowered for w in DANGER_WORDS)

    if danger:
        c.category = "SAFETY_HAZARD"
        c.priority = "CRITICAL_SAFETY"
        c.safety_override = c.true_category != "SAFETY_HAZARD"
        c.likely_cause = "possible live fault or damaged apparatus"
        c.recommended_action = "immediate site attendance"
        if c.safety_override:
            c.tags.append("safety found inside a non-safety complaint")
    else:
        c.category = c.true_category
        c.priority = {
            "SUPPLY_OUTAGE": "HIGH",
            "DISCONNECTION_RESTORATION": "HIGH",
            "THEFT_REPORT": "MEDIUM",
            "STAFF_CONDUCT": "HIGH",
            "VOLTAGE_QUALITY": "MEDIUM",
            "METER_FAULT": "MEDIUM",
            "BILLING_DISPUTE": "MEDIUM",
            "NEW_CONNECTION": "LOW",
            "OTHER": "LOW",
        }[c.category]

        # The example from the requirement, and the mistake it invites. A run
        # of estimated bills followed by one actual read produces exactly the
        # "bill jumped, meter is running fast" complaint, and the cause is
        # catch-up billing rather than a fast meter. Sending a technician to
        # test a working meter wastes the visit and does not answer the
        # consumer.
        if c.category == "BILLING_DISPUTE":
            if c.estimated_periods_before_actual >= 3:
                c.likely_cause = (
                    f"catch-up billing — {c.estimated_periods_before_actual} "
                    f"estimated periods then an actual read")
                c.recommended_action = (
                    "explain the true-up to the consumer; no meter test needed")
                c.tags.append("estimation catch-up, not a meter fault")
            else:
                c.likely_cause = "billed consumption disputed"
                c.recommended_action = "verify the read, then respond"
        elif c.category == "METER_FAULT":
            c.likely_cause = "meter not recording or displaying correctly"
            c.recommended_action = "meter test"
        elif c.category == "VOLTAGE_QUALITY":
            c.likely_cause = "distribution loading or a network fault"
            c.recommended_action = "voltage logging at the premises"
        elif c.category == "SUPPLY_OUTAGE":
            c.likely_cause = "fuse, feeder trip or DT failure"
            c.recommended_action = "restore supply, then record the cause"
        else:
            c.likely_cause = "see complaint text"
            c.recommended_action = "route to the owning department"

    # Repeats. Three attempts at the same issue means the routing is part of
    # the problem, so a repeat is never LOW however small the issue.
    if c.is_repeat:
        c.tags.append(f"repeat: {c.prior_complaints} prior")
        if c.priority == "LOW":
            c.priority = "MEDIUM"
        if c.prior_complaints >= 2 and c.priority == "MEDIUM":
            c.priority = "HIGH"

    c.department = SLA[c.category]["dept"]
    c.sla_hours = SLA[c.category]["hours"]


def _risk(c: Complaint) -> None:
    """Escalation risk and SLA status.

    Escalation risk is a fact about the DISCOM's handling, not about the
    consumer being difficult. Nothing here reads the consumer's tone.
    """
    c.hours_remaining = round(c.sla_hours - c.hours_elapsed, 1)
    if c.resolved:
        c.sla_status = "WITHIN"
    elif c.hours_remaining <= 0:
        c.sla_status = "BREACHED"
    elif c.hours_remaining <= c.sla_hours * 0.25:
        c.sla_status = "AT_RISK"
    else:
        c.sla_status = "WITHIN"

    score = 0
    if c.prior_complaints >= 2:
        score += 2
    if c.prior_closed_without_visit >= 1:
        score += 2
    if c.sla_status == "BREACHED":
        score += 2
    elif c.sla_status == "AT_RISK":
        score += 1
    if c.reassigned_once:
        score += 1
    if "consumer forum" in c.text.lower() or "complain" in c.text.lower():
        score += 1
    if c.priority == "CRITICAL_SAFETY":
        score += 1
    c.escalation_risk = "HIGH" if score >= 4 else "MEDIUM" if score >= 2 else "LOW"


def _generate() -> tuple[list[Complaint], dict]:
    rng = random.Random(SEED)
    cats = list(TEMPLATES)
    weights = [28, 6, 22, 9, 11, 7, 9, 2, 3, 3][:len(cats)]
    out: list[Complaint] = []
    agg = {
        "complaints": 0,
        "by_category": dict.fromkeys(SLA, 0),
        "by_priority": {"CRITICAL_SAFETY": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        "by_department": {},
        "by_sla": {"WITHIN": 0, "AT_RISK": 0, "BREACHED": 0},
        "escalation": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
        "repeats": 0, "safety_overrides": 0, "estimation_catchup": 0,
        "closed_without_visit_history": 0,
    }

    for i in range(POPULATION):
        cat = rng.choices(cats, weights=weights[:len(cats)])[0]
        text = rng.choice(TEMPLATES[cat]).format(
            low=rng.randint(800, 3000), high=rng.randint(6000, 14000),
            units=rng.randint(200, 900), hours=rng.randint(6, 40),
            days=rng.randint(20, 90))
        # A safety phrase appended to a complaint about something else, which
        # is how these actually arrive.
        if cat != "SAFETY_HAZARD" and rng.random() < 0.035:
            text += (" Also there is " +
                     rng.choice(["sparking from the meter box",
                                 "a burning smell from the connection",
                                 "a fallen wire near the gate"]) + ".")
        prior = rng.choices([0, 1, 2, 3], weights=[70, 18, 8, 4])[0]
        received = NOW - timedelta(hours=rng.uniform(0.5, 400))
        c = Complaint(
            complaint_id=f"CMP-{40000 + i}",
            consumer_no=f"MS-{800000 + rng.randint(0, 249_999)}",
            division=rng.choices(DIVISIONS, weights=[0.4, 0.32, 0.28])[0],
            channel=rng.choices(
                ["mobile app", "call centre", "portal", "walk-in", "SMS"],
                weights=[34, 31, 18, 12, 5])[0],
            received=received.strftime("%Y-%m-%dT%H:%M"),
            text=text, true_category=cat,
            prior_complaints=prior,
            prior_closed_without_visit=(
                rng.randint(0, prior) if prior and rng.random() < 0.55 else 0),
            is_repeat=prior > 0,
            hours_elapsed=round((NOW - received).total_seconds() / 3600, 1),
            reassigned_once=rng.random() < 0.14,
            estimated_periods_before_actual=(
                rng.choices([0, 1, 3, 4, 5], weights=[62, 12, 12, 9, 5])[0]
                if cat == "BILLING_DISPUTE" else 0),
            resolved=rng.random() < 0.55,
        )
        _classify(c)
        _risk(c)
        out.append(c)

        agg["complaints"] += 1
        agg["by_category"][c.category] += 1
        agg["by_priority"][c.priority] += 1
        agg["by_department"][c.department] = agg["by_department"].get(c.department, 0) + 1
        agg["by_sla"][c.sla_status] += 1
        agg["escalation"][c.escalation_risk] += 1
        agg["repeats"] += int(c.is_repeat)
        agg["safety_overrides"] += int(c.safety_override)
        agg["estimation_catchup"] += int(
            "estimation catch-up, not a meter fault" in c.tags)
        agg["closed_without_visit_history"] += int(c.prior_closed_without_visit > 0)

    return out, agg


def _load() -> tuple[list[Complaint], dict]:
    key = f"{SEED}-{POPULATION}-v1"
    cache = Path(__file__).resolve().parent / "_complaints_cache.json"
    if cache.exists():
        try:
            blob = json.loads(cache.read_text())
            if blob.get("key") == key:
                return [Complaint(**a) for a in blob["complaints"]], blob["agg"]
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    rows, agg = _generate()
    try:
        cache.write_text(json.dumps({
            "key": key, "complaints": [asdict(a) for a in rows], "agg": agg}))
    except OSError:
        pass
    return rows, agg


COMPLAINTS, TOTALS = _load()
BY_ID: dict[str, Complaint] = {c.complaint_id: c for c in COMPLAINTS}
