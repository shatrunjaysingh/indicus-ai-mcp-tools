"""Deterministic fixture data for the IAM access-review demo.

Stands in for four systems an access-certification team pivots between:
SailPoint IdentityIQ, Active Directory, Secret Server (PAM) and ServiceNow.

Seeded, so every run of the demo produces the same population and the same
findings. A demo whose numbers move between runs cannot be rehearsed, and an
auditor cannot be walked through it twice.

The population is built to *contain* the conditions the review exists to find,
rather than being uniformly clean and needing a scripted surprise:

  * orphaned accounts with no resolvable owner
  * access revoked during certification and then quietly reinstated — the
    finding the whole post-certification phase exists to catch
  * service accounts absent from Secret Server (onboarding gaps)
  * inactive users still holding entitlements
  * entitlements with no business description, so the reviewer cannot judge
  * SMEs who never respond, twice

Counts are declared in SCALE and asserted at import, so the "1000+ records"
claim is checked rather than believed.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

SEED = 20260821
SCALE = {
    "identities": 640,
    "applications": 24,
    "entitlements": 310,
    "accounts": 1180,
}

_rng = random.Random(SEED)
_now = datetime(2026, 8, 21, tzinfo=UTC)


def _iso(days_ago: int) -> str:
    return (_now - timedelta(days=days_ago)).isoformat()


FIRST = [
    "Miriam", "Remy", "Priya", "Tomas", "Ada", "Kofi", "Lena", "Hiro", "Sofia",
    "Diego", "Nadia", "Owen", "Ines", "Marcus", "Yuki", "Farah", "Bram", "Chen",
    "Elena", "Rafael", "Anja", "Sami", "Nora", "Viktor", "Amara", "Josef",
]
LAST = [
    "Okafor", "Delacroix", "Raman", "Novak", "Lindqvist", "Mensah", "Weiss",
    "Tanaka", "Duarte", "Alvarez", "Haddad", "Griffiths", "Moreau", "Bell",
    "Sato", "Nasser", "Devries", "Wu", "Petrova", "Costa", "Berg", "Aziz",
]

DEPARTMENTS = [
    ("Finance", "high"), ("Engineering", "high"), ("Sales", "medium"),
    ("HR", "high"), ("Operations", "medium"), ("Marketing", "low"),
    ("Legal", "high"), ("Support", "medium"),
]

APP_NAMES = [
    ("SAP-FIN", "Finance", "high"), ("Workday-HR", "HR", "high"),
    ("Salesforce-CRM", "Sales", "medium"), ("Jira-Eng", "Engineering", "low"),
    ("Confluence", "Engineering", "low"), ("GitHub-Ent", "Engineering", "high"),
    ("AWS-Prod", "Engineering", "critical"), ("AWS-NonProd", "Engineering", "medium"),
    ("Oracle-DB", "Operations", "critical"), ("Tableau", "Operations", "medium"),
    ("ServiceNow", "Operations", "medium"), ("Concur-Expense", "Finance", "medium"),
    ("Coupa-Procure", "Finance", "high"), ("DocuSign", "Legal", "high"),
    ("NetSuite", "Finance", "high"), ("Zendesk", "Support", "low"),
    ("Slack-Ent", "Operations", "low"), ("Okta-Admin", "Engineering", "critical"),
    ("VPN-Gateway", "Operations", "high"), ("FileShare-Corp", "Operations", "medium"),
    ("PowerBI", "Marketing", "low"), ("Marketo", "Marketing", "low"),
    ("Snowflake", "Engineering", "critical"), ("Vault-Secrets", "Engineering", "critical"),
]


def _build_identities() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(SCALE["identities"]):
        first = _rng.choice(FIRST)
        last = _rng.choice(LAST)
        dept, sensitivity = _rng.choice(DEPARTMENTS)
        username = f"{first[0].lower()}.{last.lower()}{i:03d}"

        # ~8% have left but were never fully deprovisioned. They are the reason
        # the readiness phase checks inactive users before scoping.
        active = _rng.random() > 0.08
        out[username] = {
            "username": username,
            "display_name": f"{first} {last}",
            "email": f"{username}@example-corp.com",
            "department": dept,
            "data_sensitivity": sensitivity,
            "title": _rng.choice(
                ["Analyst", "Engineer", "Manager", "Director", "Specialist", "Lead"]
            ),
            "manager": None,  # filled below
            "status": "active" if active else "terminated",
            "terminated_on": None if active else _iso(_rng.randint(20, 400)),
            "hired_on": _iso(_rng.randint(400, 3000)),
        }

    usernames = list(out)
    managers = [u for u in usernames if out[u]["status"] == "active"][:60]
    for username, record in out.items():
        candidate = _rng.choice(managers)
        record["manager"] = None if candidate == username else candidate
        # A handful report to someone who has since left — the "verify active
        # managers" check exists because certifications sent to a terminated
        # manager are never actioned.
        if _rng.random() < 0.03:
            terminated = [u for u in usernames if out[u]["status"] == "terminated"]
            if terminated:
                record["manager"] = _rng.choice(terminated)
    return out


IDENTITIES = _build_identities()
_ACTIVE = [u for u, r in IDENTITIES.items() if r["status"] == "active"]
_TERMINATED = [u for u, r in IDENTITIES.items() if r["status"] == "terminated"]


def _build_applications() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for index, (name, dept, criticality) in enumerate(APP_NAMES):
        owner = _rng.choice(_ACTIVE)
        # Two applications are owned by someone who has left. Readiness must
        # catch this before the campaign is scoped.
        if index in (5, 17):
            owner = _rng.choice(_TERMINATED)
        out[name] = {
            "app_id": f"APP-{index + 1:03d}",
            "name": name,
            "department": dept,
            "criticality": criticality,
            "owner": owner,
            "connector": _rng.choice(["AD", "REST", "JDBC", "SCIM"]),
            "in_scope": criticality in ("high", "critical") or _rng.random() < 0.5,
            "last_aoc_review": _iso(_rng.randint(30, 400)),
        }
    return out


APPLICATIONS = _build_applications()
_APP_NAMES = list(APPLICATIONS)


def _build_entitlements() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(SCALE["entitlements"]):
        app = _rng.choice(_APP_NAMES)
        kind = _rng.choice(["Read", "Write", "Admin", "Approve", "Export"])
        ent_id = f"ENT-{i + 1:04d}"
        privileged = kind in ("Admin", "Approve")

        # ~14% have no business description. A reviewer cannot certify what
        # nobody can describe, which is why readiness chases these.
        described = _rng.random() > 0.14
        out[ent_id] = {
            "entitlement_id": ent_id,
            "name": f"{app}-{kind}",
            "application": app,
            "type": kind,
            "privileged": privileged,
            "description": (
                f"Grants {kind.lower()} access to {app} for {APPLICATIONS[app]['department']}."
                if described
                else ""
            ),
            "owner": _rng.choice(_ACTIVE) if _rng.random() > 0.05 else None,
            "member_count": 0,  # filled below
        }
    return out


ENTITLEMENTS = _build_entitlements()
_ENT_IDS = list(ENTITLEMENTS)


def _build_accounts() -> dict[str, dict]:
    """AD, non-AD and service accounts — the SAR population."""
    out: dict[str, dict] = {}
    total = SCALE["accounts"]

    for i in range(total):
        roll = _rng.random()
        if roll < 0.62:
            kind = "user"
        elif roll < 0.86:
            kind = "service"
        elif roll < 0.94:
            kind = "shared"
        else:
            kind = "system"

        account_id = f"ACC-{i + 1:05d}"
        source = _rng.choice(["ActiveDirectory", "ActiveDirectory", "NonAD-Oracle", "NonAD-SAP"])

        if kind == "user":
            owner = _rng.choice(list(IDENTITIES))
            name = owner
            interactive = True
        else:
            app = _rng.choice(_APP_NAMES)
            name = f"svc_{app.lower().replace('-', '_')}_{i:04d}"
            # ~11% of non-user accounts have no resolvable owner. These are the
            # orphans the review is meant to surface and the exception queue is
            # meant to receive.
            owner = _rng.choice(_ACTIVE) if _rng.random() > 0.11 else None
            interactive = kind == "shared" or _rng.random() < 0.18

        entitlements = _rng.sample(_ENT_IDS, _rng.randint(0, 6))
        for ent in entitlements:
            ENTITLEMENTS[ent]["member_count"] += 1

        out[account_id] = {
            "account_id": account_id,
            "account_name": name,
            "account_type": kind,
            "source": source,
            "owner": owner,
            "correlated": owner is not None,
            "interactive_login": interactive,
            "privileged": any(ENTITLEMENTS[e]["privileged"] for e in entitlements),
            "entitlements": entitlements,
            "last_login": _iso(_rng.randint(0, 500)),
            "password_last_set": _iso(_rng.randint(0, 900)),
            "created_on": _iso(_rng.randint(30, 2000)),
            "application": None if kind == "user" else _rng.choice(_APP_NAMES),
        }
    return out


ACCOUNTS = _build_accounts()
_SERVICE_ACCOUNTS = [
    a for a in ACCOUNTS.values() if a["account_type"] in ("service", "shared", "system")
]


def _build_secret_server() -> dict[str, dict]:
    """PAM inventory. Deliberately incomplete — the gap is the finding."""
    out: dict[str, dict] = {}
    for account in _SERVICE_ACCOUNTS:
        # ~27% of service accounts were never onboarded to the vault.
        if _rng.random() < 0.27:
            continue
        out[account["account_name"]] = {
            "secret_id": f"SS-{len(out) + 1:05d}",
            "account_name": account["account_name"],
            "folder": f"/Services/{account['application'] or 'Shared'}",
            "onboarded_on": _iso(_rng.randint(10, 900)),
            "rotation_enabled": _rng.random() > 0.22,
            "last_rotated": _iso(_rng.randint(0, 400)),
            "checkout_required": _rng.random() > 0.5,
        }
    return out


SECRET_SERVER = _build_secret_server()


def _build_certification() -> dict:
    """The prior campaign's decisions, and what actually happened afterwards."""
    decisions: list[dict] = []
    population = [a for a in ACCOUNTS.values() if a["entitlements"]]
    reviewed = _rng.sample(population, min(420, len(population)))

    for account in reviewed:
        for ent in account["entitlements"][:2]:
            revoke = _rng.random() < 0.18
            decisions.append(
                {
                    "decision_id": f"DEC-{len(decisions) + 1:05d}",
                    "account_id": account["account_id"],
                    "account_name": account["account_name"],
                    "entitlement_id": ent,
                    "entitlement_name": ENTITLEMENTS[ent]["name"],
                    "application": ENTITLEMENTS[ent]["application"],
                    "reviewer": _rng.choice(_ACTIVE),
                    "decision": "revoke" if revoke else "approve",
                    "decided_on": _iso(_rng.randint(30, 60)),
                    "comment": "" if not revoke else _rng.choice(
                        ["No longer required", "Role change", "Excessive privilege"]
                    ),
                }
            )
    return {"campaign_id": "CERT-2026-Q2", "decisions": decisions}


CERTIFICATION = _build_certification()
_REVOKED = [d for d in CERTIFICATION["decisions"] if d["decision"] == "revoke"]

# The headline finding. Some revocations were carried out and then the access
# was granted again — which a decision report alone can never reveal, because
# the decision still reads "revoke". Only comparing decisions against live
# entitlements exposes it.
REINSTATED: list[dict] = []
for decision in _REVOKED:
    if _rng.random() < 0.14:
        REINSTATED.append(
            {
                "account_id": decision["account_id"],
                "account_name": decision["account_name"],
                "entitlement_id": decision["entitlement_id"],
                "entitlement_name": decision["entitlement_name"],
                "application": decision["application"],
                "revoked_on": decision["decided_on"],
                "reinstated_on": _iso(_rng.randint(5, 25)),
                "reinstated_by": _rng.choice(_ACTIVE),
                "ticket": None if _rng.random() < 0.55 else f"REQ{_rng.randint(10000, 99999)}",
            }
        )

# Remediation tickets. Not every revocation produced one — the missing ones are
# the second post-certification finding.
TICKETS: dict[str, dict] = {}
for decision in _REVOKED:
    if _rng.random() < 0.83:
        ticket_id = f"RITM{_rng.randint(100000, 999999)}"
        TICKETS[decision["decision_id"]] = {
            "ticket_id": ticket_id,
            "decision_id": decision["decision_id"],
            "account_name": decision["account_name"],
            "entitlement_id": decision["entitlement_id"],
            "state": _rng.choice(["Closed", "Closed", "Closed", "In Progress", "Open"]),
            "opened_on": decision["decided_on"],
        }

# Prior SAR cycle, so "new since last review" is answerable.
PRIOR_SAR = {
    a["account_name"] for a in _SERVICE_ACCOUNTS if _rng.random() > 0.15
}

# SME responses to pre-validation. Some never reply, twice.
SME_RESPONSES: dict[str, dict] = {}
for app_name, app in APPLICATIONS.items():
    roll = _rng.random()
    if roll < 0.62:
        state = "responded"
    elif roll < 0.85:
        state = "pending"
    else:
        state = "no_response"
    SME_RESPONSES[app_name] = {
        "application": app_name,
        "sme": app["owner"],
        "state": state,
        "responded_on": _iso(_rng.randint(1, 20)) if state == "responded" else None,
        "follow_ups_sent": 0 if state == "responded" else (2 if state == "no_response" else 1),
        "entitlements_confirmed": (
            sum(1 for e in ENTITLEMENTS.values() if e["application"] == app_name)
            if state == "responded"
            else 0
        ),
    }


def record_count() -> int:
    return (
        len(IDENTITIES)
        + len(APPLICATIONS)
        + len(ENTITLEMENTS)
        + len(ACCOUNTS)
        + len(SECRET_SERVER)
        + len(CERTIFICATION["decisions"])
        + len(TICKETS)
    )


def summary() -> dict:
    """Headline counts, so the demo can state its own scale."""
    orphaned = [a for a in ACCOUNTS.values() if not a["correlated"]]
    undescribed = [e for e in ENTITLEMENTS.values() if not e["description"]]
    not_vaulted = [
        a for a in _SERVICE_ACCOUNTS if a["account_name"] not in SECRET_SERVER
    ]
    inactive_with_access = [
        a
        for a in ACCOUNTS.values()
        if a["owner"] in IDENTITIES
        and IDENTITIES[a["owner"]]["status"] == "terminated"
        and a["entitlements"]
    ]
    return {
        "total_records": record_count(),
        "identities": len(IDENTITIES),
        "active_identities": len(_ACTIVE),
        "terminated_identities": len(_TERMINATED),
        "applications": len(APPLICATIONS),
        "applications_in_scope": sum(1 for a in APPLICATIONS.values() if a["in_scope"]),
        "entitlements": len(ENTITLEMENTS),
        "accounts": len(ACCOUNTS),
        "service_accounts": len(_SERVICE_ACCOUNTS),
        "secret_server_onboarded": len(SECRET_SERVER),
        "certification_decisions": len(CERTIFICATION["decisions"]),
        "revocations": len(_REVOKED),
        "remediation_tickets": len(TICKETS),
        "findings": {
            "orphaned_accounts": len(orphaned),
            "entitlements_without_description": len(undescribed),
            "service_accounts_not_vaulted": len(not_vaulted),
            "terminated_users_with_access": len(inactive_with_access),
            "reinstated_after_revocation": len(REINSTATED),
            "revocations_without_ticket": len(_REVOKED) - len(TICKETS),
            "smes_not_responding": sum(
                1 for r in SME_RESPONSES.values() if r["state"] == "no_response"
            ),
        },
    }


# The scale claim is checked at import rather than asserted in prose.
assert record_count() >= 1000, f"fixture is too small: {record_count()} records"
