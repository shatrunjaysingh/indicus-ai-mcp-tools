"""A stand-in for an IAM team's own stack, for the access-review demo.

Plays the part of the four systems a certification analyst pivots between:
SailPoint IdentityIQ, Active Directory, Secret Server (PAM) and ServiceNow —
plus the notification channel that chases SMEs.

In a real deployment these are the customer's own systems, reached with their
own credentials through the same custom-tool import used here; nothing in this
file is part of the platform.

Endpoints are shaped around the *questions the review asks*, not around the
tables underneath. `GET /post-cert/reinstated` exists because "was revoked
access quietly granted again" is the finding the whole post-certification phase
is for, and an agent should not have to reconstruct it from two other calls.

Serves on port 8302. Fixture data and its planted findings: iam_data.py.
"""

from __future__ import annotations

import json

import os
import pathlib
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

import iam_data as data

# Sized against the response cap, not chosen for roundness. A trimmed record
# is ~400 characters once the platform re-serialises with indent=2, so fifty
# came to 20,086 against a 20,000 cap — over by 86, and the caller loses the
# tail of its own batch with no way to tell. Forty leaves 4k of headroom and
# still answers a typical exception list in one call.
MAX_LOOKUP_NAMES = 40

app = FastAPI(
    title="IAM Access Review API",
    version="1.0.0",
    description=(
        "Identity governance, directory, privileged-access and ticketing data "
        "for access certification and service account review."
    ),
)


# --------------------------------------------------------------- readiness


# Two campaigns, so the demo can be run both ways.
#
# Q2 is the real environment: two in-scope applications are owned by people who
# have left, which must stop the launch. Q3 is the same environment after those
# owners were reassigned — everything else is identical, so the difference in
# outcome is attributable to the one thing that changed. A demo that can only
# ever fail shows the gate but never the pipeline behind it.
REMEDIATED_CAMPAIGNS = {"CERT-2026-Q3"}


@app.get("/readiness/scope", operation_id="getCertificationScope", summary="Applications in scope, with owner validity")
def certification_scope(campaign: str = "CERT-2026-Q2", only_in_scope: bool = True) -> dict:
    """Applications for the campaign, each flagged if its owner is not active.

    The owner check is returned with the scope rather than left to a second
    call: a campaign staged against an application whose owner has left produces
    certifications nobody actions, and that is only discoverable here.
    """
    remediated = campaign in REMEDIATED_CAMPAIGNS
    stand_in = next(
        u for u, r in data.IDENTITIES.items() if r["status"] == "active"
    )

    rows = []
    for name, app_record in data.APPLICATIONS.items():
        if only_in_scope and not app_record["in_scope"]:
            continue
        owner_name = app_record["owner"]
        owner = data.IDENTITIES.get(owner_name or "")
        if remediated and not (owner and owner["status"] == "active"):
            owner_name = stand_in
            owner = data.IDENTITIES[stand_in]
        rows.append(
            {
                **app_record,
                "owner": owner_name,
                "owner_status": owner["status"] if owner else "unknown",
                "owner_valid": bool(owner and owner["status"] == "active"),
            }
        )
    invalid = [r for r in rows if not r["owner_valid"]]
    return {
        "campaign": campaign,
        "count": len(rows),
        "applications": rows,
        "owner_issues": len(invalid),
        "owner_issue_apps": [r["name"] for r in invalid],
    }


@app.get("/readiness/entitlement-quality", operation_id="getEntitlementQuality", summary="Entitlements missing a business description")
def entitlement_quality(application: str | None = None) -> dict:
    """A reviewer cannot certify access nobody can describe."""
    rows = [
        e
        for e in data.ENTITLEMENTS.values()
        if application is None or e["application"] == application
    ]
    missing = [e for e in rows if not e["description"]]
    unowned = [e for e in rows if not e["owner"]]
    return {
        "total": len(rows),
        "missing_description": len(missing),
        "missing_description_ids": [e["entitlement_id"] for e in missing][:100],
        "without_owner": len(unowned),
        "sample": missing[:20],
    }


@app.get("/readiness/uncorrelated", operation_id="getUncorrelatedAccounts", summary="Accounts with no resolvable owner")
def uncorrelated_accounts(
    offset: int = Query(0, ge=0, description="Rows to skip, for paging past the cap"),
    limit: int = 100,
) -> dict:
    """Orphans. Each needs a human decision: correlate, or decommission.

    Every summary field is emitted before the array, and the array carries only
    the fields a correlation decision turns on. Both matter because the
    response is capped and truncation cuts from the end: with the counts last,
    a caller asking "how many of these are privileged?" lost the answer to the
    very records it was counting, and could only report a range.
    """
    rows = [a for a in data.ACCOUNTS.values() if not a["correlated"]]
    window = rows[offset : offset + limit]
    return {
        "count": len(rows),
        "privileged_count": sum(1 for a in rows if a["privileged"]),
        "interactive_count": sum(1 for a in rows if a["interactive_login"]),
        "offset": offset,
        "returned": len(window),
        "has_more": offset + limit < len(rows),
        "accounts": [
            {
                "account_id": a["account_id"],
                "account_name": a["account_name"],
                "account_type": a["account_type"],
                "application": a["application"],
                "privileged": a["privileged"],
                "interactive_login": a["interactive_login"],
                "last_login": a["last_login"],
                "source": a["source"],
            }
            for a in window
        ],
    }


@app.get("/readiness/inactive-with-access", operation_id="getInactiveUsersWithAccess", summary="Terminated identities still holding entitlements")
def inactive_with_access(limit: int = 100) -> dict:
    """Must be out of scope before launch, and remediated regardless."""
    rows = []
    for account in data.ACCOUNTS.values():
        identity = data.IDENTITIES.get(account["owner"] or "")
        if identity and identity["status"] == "terminated" and account["entitlements"]:
            rows.append(
                {
                    "account_id": account["account_id"],
                    "account_name": account["account_name"],
                    "owner": identity["username"],
                    "terminated_on": identity["terminated_on"],
                    "entitlement_count": len(account["entitlements"]),
                    "privileged": account["privileged"],
                }
            )
    return {"count": len(rows), "accounts": rows[:limit]}


# ---------------------------------------------------------- pre-validation


@app.get("/prevalidation/sme-status", operation_id="getSmeValidationStatus", summary="SME pre-validation responses and follow-ups")
def sme_status() -> dict:
    """Who has confirmed their entitlements, who has been chased, who is silent."""
    rows = list(data.SME_RESPONSES.values())
    return {
        "total": len(rows),
        "responded": sum(1 for r in rows if r["state"] == "responded"),
        "pending": sum(1 for r in rows if r["state"] == "pending"),
        # Two follow-ups already sent. These are the exception queue, not
        # another reminder.
        "no_response": sum(1 for r in rows if r["state"] == "no_response"),
        "responses": rows,
    }


@app.get("/identity/{username}", operation_id="getIdentity", summary="Identity record with manager and status")
def get_identity(username: str) -> dict:
    identity = data.IDENTITIES.get(username.lower())
    if identity is None:
        raise HTTPException(404, f"No identity {username}.")
    manager = data.IDENTITIES.get(identity["manager"] or "")
    return {
        **identity,
        "manager_status": manager["status"] if manager else "unknown",
        # A certification routed to a manager who has left is never actioned.
        "manager_valid": bool(manager and manager["status"] == "active"),
    }


# ----------------------------------------------------------- certification


def _known_campaign(campaign_id: str) -> None:
    """Both demo campaigns read the same decision set.

    Q3 is Q2 with the two owner assignments corrected, so the certification that
    follows is over the same population. Rejecting Q3 here would 404 the
    pipeline halfway through the run that is meant to show the happy path.
    """
    if campaign_id not in {data.CERTIFICATION["campaign_id"]} | REMEDIATED_CAMPAIGNS:
        raise HTTPException(404, f"No campaign {campaign_id}.")


@app.get("/certifications/{campaign_id}/progress", operation_id="getCertificationProgress", summary="Reviewer completion for a campaign")
def certification_progress(campaign_id: str) -> dict:
    _known_campaign(campaign_id)
    decisions = data.CERTIFICATION["decisions"]
    reviewers: dict[str, dict] = {}
    for decision in decisions:
        row = reviewers.setdefault(
            decision["reviewer"], {"reviewer": decision["reviewer"], "total": 0}
        )
        row["total"] += 1
    return {
        "campaign_id": campaign_id,
        "decisions_total": len(decisions),
        "reviewers": len(reviewers),
        "complete_pct": 100.0,
        "top_reviewers": sorted(
            reviewers.values(), key=lambda r: -r["total"]
        )[:10],
    }


@app.get("/certifications/{campaign_id}/decisions", operation_id="getCertificationDecisions", summary="All approve/revoke decisions")
def certification_decisions(
    campaign_id: str,
    decision: str | None = Query(None, description="approve | revoke"),
    application: str | None = Query(
        None, description="Return the individual rows for one application."
    ),
) -> dict:
    _known_campaign(campaign_id)
    rows = data.CERTIFICATION["decisions"]
    if decision:
        rows = [d for d in rows if d["decision"] == decision]

    # Compact records, and a truncation flag.
    #
    # The full 161 revoke decisions came to 50,000 characters — well past the
    # 20,000-character cap a tool response is allowed. The caller silently saw
    # the first 50 and had no way to know the other 111 existed. An agent that
    # cannot tell a complete answer from a truncated one will reason over the
    # part it can see and present the result as whole.
    #
    # So: only the fields the analysis actually uses, and `complete` stated
    # explicitly rather than left to be inferred from a count.
    # Short keys, and the application dropped — it is already the prefix of the
    # entitlement name, so carrying both spends characters on nothing. The
    # decision is omitted when the caller filtered by it, for the same reason.
    # Aggregated, not enumerated.
    #
    # Three attempts to fit 161 revocation records into one response failed,
    # each for a different reason — too verbose, then a row cap that cut the
    # list, then a budget measured before the platform re-serialised it. The
    # fourth attempt is to stop trying: nobody asked for 161 rows.
    #
    # The question this endpoint serves is "what was revoked, what came back,
    # what is unexplained". That is answered by counts plus the exceptions, and
    # the exceptions have their own endpoints. An analyst asking a colleague
    # would get a breakdown, not a spreadsheet, and would ask for the rows of
    # one application if they needed them.
    by_app: dict[str, dict[str, int]] = {}
    for r in rows:
        entry = by_app.setdefault(
            r["application"], {"application": r["application"], "approve": 0, "revoke": 0}
        )
        entry[r["decision"]] += 1

    breakdown = sorted(by_app.values(), key=lambda a: -a["revoke"])

    detail: list[dict] = []
    if application:
        # One application's rows are small enough to return whole.
        detail = [
            {
                "id": r["decision_id"],
                "acct": r["account_name"],
                "ent": r["entitlement_name"],
                "on": r["decided_on"][:10],
                **({} if decision else {"decision": r["decision"]}),
            }
            for r in rows
            if r["application"] == application
        ]

    return {
        "campaign_id": campaign_id,
        "count": len(rows),
        "filter": decision or "all",
        "by_application": breakdown,
        # Complete by construction: the breakdown covers every decision. Rows
        # are only returned for a named application, and then all of them.
        "complete": True,
        "detail_for": application,
        "decisions": detail,
        "note": (
            "Counts cover every decision. Pass `application` to see the "
            "individual rows for one application."
        ),
    }


# ------------------------------------------------------------- post-cert


@app.get("/post-cert/reinstated", operation_id="getReinstatedAccess", summary="Access revoked during certification and later granted again")
def reinstated_access() -> dict:
    """The finding the post-certification phase exists to produce.

    A decision report cannot show this: the decision still reads "revoke". Only
    comparing decisions against live entitlements reveals that the access came
    back — and whether it came back through a request or through nothing at all.
    """
    rows = data.REINSTATED
    unexplained = [r for r in rows if not r["ticket"]]
    return {
        "count": len(rows),
        "reinstated": rows,
        # No request record. This is the subset an auditor asks about.
        "without_request_ticket": len(unexplained),
    }


@app.get("/post-cert/remediation-gaps", operation_id="getRemediationGaps", summary="Revocations with no remediation ticket")
def remediation_gaps() -> dict:
    revoked = [d for d in data.CERTIFICATION["decisions"] if d["decision"] == "revoke"]
    missing = [d for d in revoked if d["decision_id"] not in data.TICKETS]
    open_tickets = [
        t for t in data.TICKETS.values() if t["state"] in ("Open", "In Progress")
    ]
    return {
        "revocations": len(revoked),
        "tickets_created": len(data.TICKETS),
        "missing_tickets": len(missing),
        "missing": missing[:50],
        "still_open": len(open_tickets),
        "open_tickets": open_tickets[:50],
    }


# -------------------------------------------------------------------- SAR


@app.get("/sar/accounts/lookup", operation_id="getServiceAccount", summary="Look up named accounts, fully classified")
def service_account_lookup(
    account_names: str = Query(
        ...,
        description=(
            "One or more exact account names, comma-separated, up to 50 per "
            "call — e.g. svc_netsuite_0978,svc_docusign_0178"
        ),
    ),
) -> dict:
    """Everything a reviewer must decide about named accounts, in one call.

    A review names the accounts it needs answered — it does not want the
    inventory. Paging a 1,180-row list to find them costs more than the answer
    is worth and, past the response cap, cannot reach the tail at all; an agent
    that cannot look an account up either guesses or gives up, and both are
    wrong.

    Batched because one-at-a-time is what it costs, not what it returns. A run
    that resolved 148 accounts singly spent five seconds inside this endpoint
    and twelve minutes around it: every answer re-entered the conversation and
    was re-sent on each following turn, so the context grew to 211k tokens.
    Fifty names per call collapses that to a handful of round trips.
    """
    wanted = [n.strip() for n in account_names.split(",") if n.strip()]
    if not wanted:
        raise HTTPException(400, "Give at least one account name.")
    if len(wanted) > MAX_LOOKUP_NAMES:
        raise HTTPException(
            400,
            f"{len(wanted)} names requested; {MAX_LOOKUP_NAMES} is the maximum "
            "per call. Split the list across calls.",
        )

    by_name = {a["account_name"]: a for a in data.ACCOUNTS.values()}
    found, missing = [], []
    for name in wanted:
        account = by_name.get(name)
        if account is None:
            missing.append(name)
            continue
        non_human = account["account_type"] in ("service", "shared", "system")
        # Only the fields a service account review decides on. The full record
        # carries entitlement lists and provisioning timestamps that nothing
        # here reads: at 670 characters apiece a batch of fifty came to 27k and
        # was truncated by the response cap, which cost the caller the tail of
        # its own batch. Trimmed, fifty fit with room to spare.
        found.append(
            {
                "account_name": name,
                "account_id": account["account_id"],
                # Stated rather than implied: "absent from the prior cycle" and
                # "not a service account at all" are different answers, and a
                # reviewer acting on the second needs to know it applies.
                "classification": account["account_type"],
                "is_service_account": non_human,
                "privileged": account["privileged"],
                "interactive_login": account["interactive_login"],
                "owner": account["owner"],
                "in_password_vault": name in data.SECRET_SERVER,
                "new_since_last_cycle": (
                    None if not non_human else name not in data.PRIOR_SAR
                ),
                "application": account["application"],
                "last_login": account["last_login"],
            }
        )

    # Names that do not resolve are reported, not raised: one bad name in a
    # batch of fifty must not discard the forty-nine good answers.
    return {"count": len(found), "not_found": missing, "accounts": found}


@app.get("/sar/accounts", operation_id="getServiceAccountInventory", summary="Service account inventory with classification")
def service_accounts(
    account_type: str | None = Query(None, description="service | shared | system | user"),
    name_contains: str | None = Query(
        None, description="Case-insensitive substring match on account name"
    ),
    offset: int = Query(0, ge=0, description="Rows to skip, for paging past the cap"),
    limit: int = 200,
) -> dict:
    rows = [
        a
        for a in data.ACCOUNTS.values()
        if (account_type is None or a["account_type"] == account_type)
        and (name_contains is None or name_contains.lower() in a["account_name"].lower())
    ]
    by_type: dict[str, int] = {}
    for account in data.ACCOUNTS.values():
        by_type[account["account_type"]] = by_type.get(account["account_type"], 0) + 1
    return {
        "count": len(rows),
        "by_type": by_type,
        "interactive": sum(1 for a in rows if a["interactive_login"]),
        "privileged": sum(1 for a in rows if a["privileged"]),
        "offset": offset,
        # Stated explicitly so a caller knows whether it has seen everything.
        # Silence here is what made the previous truncation unrecoverable.
        "returned": len(rows[offset : offset + limit]),
        "has_more": offset + limit < len(rows),
        "accounts": rows[offset : offset + limit],
    }


@app.get("/sar/vault-gaps", operation_id="getVaultOnboardingGaps", summary="Service accounts absent from Secret Server")
def vault_gaps(limit: int = 100) -> dict:
    """Privileged credentials outside the vault, ranked so the worst go first."""
    gaps = []
    for account in data.ACCOUNTS.values():
        if account["account_type"] == "user":
            continue
        if account["account_name"] in data.SECRET_SERVER:
            continue
        gaps.append(
            {
                "account_name": account["account_name"],
                "account_type": account["account_type"],
                "application": account["application"],
                "privileged": account["privileged"],
                "interactive_login": account["interactive_login"],
                "owner": account["owner"],
                "last_login": account["last_login"],
                # Interactive plus privileged plus no owner is the worst case:
                # a usable credential nobody is accountable for.
                "risk": (
                    "high"
                    if account["privileged"] and account["interactive_login"]
                    else "medium"
                    if account["privileged"] or account["owner"] is None
                    else "low"
                ),
            }
        )
    gaps.sort(key=lambda g: {"high": 0, "medium": 1, "low": 2}[g["risk"]])
    return {
        "count": len(gaps),
        "high_risk": sum(1 for g in gaps if g["risk"] == "high"),
        "gaps": gaps[:limit],
    }


@app.get("/sar/delta", operation_id="getServiceAccountDelta", summary="Service accounts new since the prior SAR cycle")
def sar_delta(
    offset: int = Query(0, ge=0, description="Rows to skip, for paging past the cap"),
    limit: int = 100,
) -> dict:
    current = {
        a["account_name"]: a
        for a in data.ACCOUNTS.values()
        if a["account_type"] in ("service", "shared", "system")
    }
    new = [current[n] for n in current if n not in data.PRIOR_SAR]
    removed = [n for n in data.PRIOR_SAR if n not in current]
    return {
        "current_total": len(current),
        "prior_total": len(data.PRIOR_SAR),
        "new_since_last_cycle": len(new),
        "removed_since_last_cycle": len(removed),
        "offset": offset,
        "returned": len(new[offset : offset + limit]),
        "has_more": offset + limit < len(new),
        "new_accounts": new[offset : offset + limit],
    }


@app.get("/secret-server/{account_name}", operation_id="getVaultRecord", summary="Secret Server record for one account")
def vault_record(account_name: str) -> dict:
    record = data.SECRET_SERVER.get(account_name)
    if record is None:
        # Absence is the answer the caller wants, not an error.
        return {
            "account_name": account_name,
            "onboarded": False,
            "note": "Not present in Secret Server. Credential is unmanaged.",
        }
    return {**record, "onboarded": True}


# ------------------------------------------------------------------ messaging
#
# Shaped after Microsoft Graph's sendMail/chat message calls rather than
# invented, so moving from this simulator to a real tenant is a change of
# url_template and credentials — not a change to the agent, the skill, or the
# way the pipeline reads the result. The demo's whole integration story rests
# on that being true, so the request and response shapes are the ones Graph
# actually uses.

SENT_MESSAGES: list[dict] = []


class TeamsMessage(BaseModel):
    recipient: str = Field(
        ..., description="Username of the person to message, e.g. r.wu035"
    )
    body: str = Field(..., description="Message text. Plain text, not HTML.")
    importance: str = Field(
        "normal", description="normal | high — high is for escalations"
    )


@app.post("/teams/chat", operation_id="sendTeamsMessage", summary="Send a Teams chat to one person")
def send_teams_message(message: TeamsMessage) -> dict:
    """Message an individual, and refuse to message someone who has left.

    Checked here rather than trusting the caller: a chase sent to a terminated
    identity is not merely wasted, it is the review telling itself it followed
    up when nobody was ever going to reply. The 404 and the 409 are different
    answers and the caller needs to tell them apart.
    """
    identity = data.IDENTITIES.get(message.recipient)
    if identity is None:
        raise HTTPException(404, f"No identity {message.recipient!r}.")
    if identity.get("status") != "active":
        raise HTTPException(
            409,
            f"{message.recipient} is {identity.get('status')} — "
            "cannot be messaged. Escalate to their manager instead.",
        )

    record = {
        "message_id": f"MSG-{len(SENT_MESSAGES) + 1:05d}",
        "recipient": message.recipient,
        "display_name": identity.get("display_name"),
        "manager": identity.get("manager"),
        "importance": message.importance,
        "body": message.body,
        "sent_at": datetime.now(UTC).isoformat(),
        "channel": "teams",
    }
    SENT_MESSAGES.append(record)
    return {"sent": True, **record}


@app.get("/teams/sent", operation_id="getSentMessages", summary="Messages this cycle has sent")
def sent_messages(recipient: str | None = Query(None)) -> dict:
    """What the run actually sent — the evidence half of an outbound action.

    A review that chases people has to be able to show whom it chased, or the
    chase is not auditable.
    """
    rows = [m for m in SENT_MESSAGES if recipient is None or m["recipient"] == recipient]
    return {"count": len(rows), "messages": rows}


# --- delivery -------------------------------------------------------------
#
# Two transports behind one contract. Without SMTP_HOST the endpoint records
# the message and says so; with it, the message is actually sent. The agent,
# the skill and the tool definition are identical either way — which is the
# whole point, because a demo that only works in simulation teaches the wrong
# thing about the integration.


# Read once, at import, from demo/.env when it exists.
#
# Environment variables alone would mean re-exporting five values on every
# restart, which is how a redirect gets forgotten and a test send reaches real
# people. A file that is already gitignored keeps the credential off disk in
# git and out of the shell history.
load_dotenv(pathlib.Path(__file__).with_name(".env"), override=False)


def _smtp_settings() -> dict[str, str] | None:
    host = os.environ.get("SMTP_HOST")
    if not host:
        return None
    return {
        "host": host,
        "port": os.environ.get("SMTP_PORT", "587"),
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "sender": os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "")),
        "starttls": os.environ.get("SMTP_STARTTLS", "1"),
        # Every message goes here instead of the address on the identity
        # record. The demo population has plausible-looking addresses at a
        # domain nobody owns; with real IAM data loaded they would be real
        # people. A redirect that must be switched off deliberately is the
        # difference between a test send and mailing someone's staff.
        "redirect_to": os.environ.get("SMTP_REDIRECT_TO", ""),
    }


def _deliver(to: str, cc: list[str], subject: str, body: str) -> dict:
    settings = _smtp_settings()
    if settings is None:
        return {"delivered": False, "transport": "recorded",
                "note": "SMTP_HOST is not set; the message was recorded, not sent."}

    redirect = settings["redirect_to"]
    envelope_to = [redirect] if redirect else [to, *cc]

    message = EmailMessage()
    message["From"] = settings["sender"]
    message["To"] = redirect or to
    if cc and not redirect:
        message["Cc"] = ", ".join(cc)
    message["Subject"] = subject
    if redirect:
        # The intended recipients travel in the body, not just the log: a
        # redirected test is only useful if you can see who it would have gone
        # to without going back to the database.
        body = (
            f"[Redirected test send]\n"
            f"Intended To: {to}\n"
            f"Intended Cc: {', '.join(cc) if cc else '(none)'}\n\n{body}"
        )
    message.set_content(body)

    try:
        port = int(settings["port"])
        if port == 465:
            with smtplib.SMTP_SSL(settings["host"], port, timeout=20) as smtp:
                if settings["user"]:
                    smtp.login(settings["user"], settings["password"])
                smtp.send_message(message, to_addrs=envelope_to)
        else:
            with smtplib.SMTP(settings["host"], port, timeout=20) as smtp:
                if settings["starttls"] not in ("0", "false", "False"):
                    smtp.starttls()
                if settings["user"]:
                    smtp.login(settings["user"], settings["password"])
                smtp.send_message(message, to_addrs=envelope_to)
    except Exception as exc:  # noqa: BLE001
        # Surfaced rather than swallowed. A review that believes it chased
        # someone it never reached is worse than one that reports a failure.
        raise HTTPException(502, f"SMTP delivery failed: {exc}") from exc

    return {"delivered": True, "transport": "smtp",
            "envelope_to": envelope_to, "redirected": bool(redirect)}


class MailRecipient(BaseModel):
    """Graph nests the address one level down; kept so the shape matches."""

    address: str = Field(..., description="Email address of the recipient")


class OutlookMail(BaseModel):
    recipient: str = Field(
        ..., description="Username of the person to email, e.g. r.wu035"
    )
    subject: str = Field(..., description="Subject line")
    body: str = Field(..., description="Message body. Plain text, not HTML.")
    cc_manager: bool = Field(
        False, description="Copy the recipient's manager — use when escalating"
    )


@app.post("/outlook/sendmail", operation_id="sendOutlookEmail", summary="Email one person, optionally copying their manager")
def send_outlook_mail(mail: OutlookMail) -> dict:
    """Send mail, and refuse to send to someone who has left.

    Same rule as the Teams step and for the same reason: a chase sent to a
    terminated identity lets the review record a follow-up that was never going
    to be answered. Escalation copies the manager rather than replacing the
    recipient, so the trail still shows who was originally asked.
    """
    identity = data.IDENTITIES.get(mail.recipient)
    if identity is None:
        raise HTTPException(404, f"No identity {mail.recipient!r}.")
    if identity.get("status") != "active":
        raise HTTPException(
            409,
            f"{mail.recipient} is {identity.get('status')} — "
            "cannot be emailed. Escalate to their manager instead.",
        )

    cc: list[str] = []
    if mail.cc_manager and identity.get("manager"):
        manager = data.IDENTITIES.get(identity["manager"])
        if manager and manager.get("status") == "active":
            cc.append(manager["email"])

    delivery = _deliver(identity.get("email"), cc, mail.subject, mail.body)

    record = {
        "message_id": f"MSG-{len(SENT_MESSAGES) + 1:05d}",
        "recipient": mail.recipient,
        "display_name": identity.get("display_name"),
        "to": identity.get("email"),
        "cc": cc,
        **delivery,
        "manager": identity.get("manager"),
        "subject": mail.subject,
        "body": mail.body,
        "sent_at": datetime.now(UTC).isoformat(),
        "channel": "outlook",
    }
    SENT_MESSAGES.append(record)
    return {"sent": True, **record}


@app.get("/estate", include_in_schema=False)
def estate() -> dict:
    """The whole estate in the shape the platform's connector contract expects.

    Out of the agent-facing schema on purpose: this is a bulk export for
    campaign construction, not something a model should ever pull into a
    prompt. A connector for a real directory implements this same four-key
    response and everything above it stays unchanged.
    """
    return {
        "identities": data.IDENTITIES,
        "applications": data.APPLICATIONS,
        "entitlements": data.ENTITLEMENTS,
        "accounts": data.ACCOUNTS,
    }


# ------------------------------------------------------------------ meta


@app.get("/summary", operation_id="getEnvironmentSummary", summary="Population counts and standing findings")
def environment_summary() -> dict:
    """Lets the demo state its own scale rather than being told."""
    return data.summary()
