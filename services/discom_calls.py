"""The call centre month: intent, resolution, conduct, deflection, and agents.

Use case 7. Twelve thousand calls, transcribed, with what the caller needed,
whether they got it, and what it says about how the centre is run.

Two parts of this are ethically loaded and are built accordingly.

**Agent performance.** Measured only on verifiable behaviours — did they verify
identity, check the record before answering, give a reference number, record an
outcome. Never on tone, accent, pace or politeness, none of which this fixture
even carries. And never from one call: a rate over five calls is noise, and
presenting it as performance is how a quality programme becomes a grievance.

The harder problem is call mix. Agents do not get the same calls. Someone
handling disconnection and payment-arrangement calls will resolve fewer of them
than someone handling tariff queries, and a raw ranking punishes whoever takes
the hard ones. Both figures are produced so the difference is visible.

**Abuse.** The flag for abuse toward an agent can be used to refuse service, so
the bar is high — threats or sustained personal abuse, not a frustrated
consumer raising their voice. Abuse *by* an agent is looked for just as hard,
because a quality programme that only counts one direction protects the utility
from its customers rather than serving them.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

SEED = 20260906
POPULATION = 12_000
AGENTS = 40

# Intents, how often they arrive, and whether a voice bot could close them from
# data alone. Deflectable means the answer is a fact the systems already hold —
# a balance, a restoration ETA, a bill breakdown — not that the caller will be
# satisfied with a machine giving it to them.
INTENTS = {
    "BILL_QUERY":            {"share": 0.26, "deflectable": True,
                              "answer": "outstanding amount and bill breakdown"},
    "OUTAGE_REPORT":         {"share": 0.17, "deflectable": True,
                              "answer": "known outage and restoration estimate"},
    "RESTORATION_STATUS":    {"share": 0.12, "deflectable": True,
                              "answer": "current status of the restoration"},
    "PAYMENT_ARRANGEMENT":   {"share": 0.11, "deflectable": False,
                              "answer": "requires a human decision on terms"},
    "METER_ISSUE":           {"share": 0.09, "deflectable": False,
                              "answer": "requires a test to be raised"},
    "COMPLAINT_FOLLOW_UP":   {"share": 0.09, "deflectable": True,
                              "answer": "status of an existing complaint"},
    "NEW_CONNECTION":        {"share": 0.06, "deflectable": True,
                              "answer": "application status"},
    "TARIFF_QUERY":          {"share": 0.05, "deflectable": True,
                              "answer": "applicable tariff and slab"},
    "THEFT_REPORT":          {"share": 0.02, "deflectable": False,
                              "answer": "must be taken by a person"},
    "OTHER":                 {"share": 0.03, "deflectable": False,
                              "answer": "unclassified"},
}

# How hard each intent is to resolve on the call, before any agent effect. This
# is what makes a raw resolution ranking unfair.
INTENT_DIFFICULTY = {
    "BILL_QUERY": 0.82, "OUTAGE_REPORT": 0.78, "RESTORATION_STATUS": 0.80,
    "PAYMENT_ARRANGEMENT": 0.41, "METER_ISSUE": 0.52,
    "COMPLAINT_FOLLOW_UP": 0.46, "NEW_CONNECTION": 0.63,
    "TARIFF_QUERY": 0.88, "THEFT_REPORT": 0.55, "OTHER": 0.50,
}


@dataclass
class Call:
    call_id: str
    consumer_no: str
    agent_id: str
    received: str
    duration_sec: int
    stated_intent: str
    actual_intent: str
    intent_reframed: bool
    resolved: str                  # YES | NO | PARTIAL
    reference_given: bool
    identity_verified: bool
    record_checked: bool
    outcome_recorded: bool
    commitment_made: str | None
    conduct_flag: str | None
    record_discrepancy: bool
    deflectable: bool
    linked_complaint: str | None
    followed_up: bool
    tags: list[str] = field(default_factory=list)


def _generate() -> tuple[list[Call], dict, dict]:
    rng = random.Random(SEED)
    intents = list(INTENTS)
    weights = [INTENTS[i]["share"] for i in intents]
    agent_ids = [f"AG-{100 + n}" for n in range(AGENTS)]
    # Agents are assigned an intent bias, so call mix genuinely differs — which
    # is the point of the adjusted metric.
    agent_bias = {a: rng.choice(intents) for a in agent_ids}
    # A quality factor per agent, independent of their mix.
    agent_quality = {a: min(1.0, max(0.0, rng.gauss(0.72, 0.13))) for a in agent_ids}

    calls: list[Call] = []
    per_agent: dict[str, dict] = {
        a: {"calls": 0, "resolved": 0, "expected_resolved": 0.0,
            "reference_given": 0, "identity_verified": 0, "record_checked": 0,
            "outcome_recorded": 0, "abuse_by_agent": 0, "mix": {}}
        for a in agent_ids
    }
    agg = {
        "calls": 0,
        "by_intent": dict.fromkeys(INTENTS, 0),
        "intent_reframed": 0,
        "resolution": {"YES": 0, "NO": 0, "PARTIAL": 0},
        "deflectable": 0,
        "conduct": {"ABUSE_TOWARD_AGENT": 0, "ABUSE_BY_AGENT": 0,
                    "SUSPECTED_FRAUD": 0, "VULNERABILITY": 0},
        "record_discrepancies": 0,
        "commitments_made": 0,
        "unresolved_no_followup": 0,
    }

    for i in range(POPULATION):
        agent = rng.choice(agent_ids)
        # Bias the mix toward this agent's specialism.
        actual = (agent_bias[agent] if rng.random() < 0.34
                  else rng.choices(intents, weights=weights)[0])

        # The caller opens with what upset them and reaches the need later.
        # A bill query that is really a payment-arrangement call is the classic.
        reframed = False
        stated = actual
        if actual == "PAYMENT_ARRANGEMENT" and rng.random() < 0.62:
            stated = "BILL_QUERY"
            reframed = True
        elif actual == "COMPLAINT_FOLLOW_UP" and rng.random() < 0.3:
            stated = "OUTAGE_REPORT"
            reframed = True

        difficulty = INTENT_DIFFICULTY[actual]
        p_resolved = min(0.97, max(0.05, difficulty * (0.55 + agent_quality[agent] * 0.6)))
        roll = rng.random()
        resolved = "YES" if roll < p_resolved else (
            "PARTIAL" if roll < p_resolved + 0.15 else "NO")

        record_checked = rng.random() < (0.55 + agent_quality[agent] * 0.4)
        conduct = None
        # Abuse toward an agent: rare, and the bar is threats or sustained
        # personal abuse rather than frustration.
        if rng.random() < 0.006:
            conduct = "ABUSE_TOWARD_AGENT"
        elif rng.random() < (0.10 - agent_quality[agent] * 0.09):
            conduct = "ABUSE_BY_AGENT"
        elif rng.random() < 0.004:
            conduct = "SUSPECTED_FRAUD"
        elif rng.random() < 0.035:
            conduct = "VULNERABILITY"

        c = Call(
            call_id=f"CL-{70000 + i}",
            consumer_no=f"MS-{800000 + rng.randint(0, 249_999)}",
            agent_id=agent,
            received=f"2026-08-{rng.randint(1, 28):02d}T{rng.randint(8, 20):02d}:"
                     f"{rng.randint(0, 59):02d}",
            duration_sec=rng.randint(45, 900),
            stated_intent=stated, actual_intent=actual,
            intent_reframed=reframed,
            resolved=resolved,
            reference_given=resolved != "NO" and rng.random() < (0.4 + agent_quality[agent] * 0.55),
            identity_verified=rng.random() < (0.7 + agent_quality[agent] * 0.28),
            record_checked=record_checked,
            outcome_recorded=rng.random() < (0.6 + agent_quality[agent] * 0.38),
            commitment_made=(
                f"callback by 2026-09-{rng.randint(3, 12):02d}"
                if resolved != "YES" and rng.random() < 0.4 else None),
            conduct_flag=conduct,
            # An agent stating something the ledger contradicts. Only findable
            # by checking, which is why record_checked matters.
            record_discrepancy=(not record_checked) and rng.random() < 0.13,
            deflectable=INTENTS[actual]["deflectable"],
            linked_complaint=(f"CMP-{40000 + rng.randint(0, 7999)}"
                              if actual == "COMPLAINT_FOLLOW_UP" else None),
            followed_up=resolved == "YES" or rng.random() < 0.45,
        )
        if reframed:
            c.tags.append(
                f"opened as {stated}, actual need {actual}")
        if c.record_discrepancy:
            c.tags.append("agent stated something the ledger contradicts")
        calls.append(c)

        a = per_agent[agent]
        a["calls"] += 1
        a["resolved"] += int(c.resolved == "YES")
        a["expected_resolved"] += difficulty
        a["reference_given"] += int(c.reference_given)
        a["identity_verified"] += int(c.identity_verified)
        a["record_checked"] += int(c.record_checked)
        a["outcome_recorded"] += int(c.outcome_recorded)
        a["abuse_by_agent"] += int(c.conduct_flag == "ABUSE_BY_AGENT")
        a["mix"][actual] = a["mix"].get(actual, 0) + 1

        agg["calls"] += 1
        agg["by_intent"][actual] += 1
        agg["intent_reframed"] += int(reframed)
        agg["resolution"][c.resolved] += 1
        agg["deflectable"] += int(c.deflectable)
        if c.conduct_flag:
            agg["conduct"][c.conduct_flag] += 1
        agg["record_discrepancies"] += int(c.record_discrepancy)
        agg["commitments_made"] += int(c.commitment_made is not None)
        if c.resolved != "YES" and not c.followed_up:
            agg["unresolved_no_followup"] += 1

    return calls, agg, per_agent


def _load():
    key = f"{SEED}-{POPULATION}-{AGENTS}-v1"
    cache = Path(__file__).resolve().parent / "_calls_cache.json"
    if cache.exists():
        try:
            blob = json.loads(cache.read_text())
            if blob.get("key") == key:
                return ([Call(**a) for a in blob["calls"]], blob["agg"],
                        blob["per_agent"])
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    calls, agg, per_agent = _generate()
    try:
        cache.write_text(json.dumps({
            "key": key, "calls": [asdict(c) for c in calls],
            "agg": agg, "per_agent": per_agent}))
    except OSError:
        pass
    return calls, agg, per_agent


CALLS, TOTALS, PER_AGENT = _load()
BY_ID: dict[str, Call] = {c.call_id: c for c in CALLS}
