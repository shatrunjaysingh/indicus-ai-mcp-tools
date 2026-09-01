"""Export the IAM demo population to CSV.

One file per record type, written to demo/data/. The fixture is generated from a
fixed seed, so re-running produces byte-identical files — which is what makes it
safe to hand these to an auditor or diff them between cycles.

List-valued columns (an account's entitlements) are joined with `;` rather than
`,` so the files survive being opened in Excel without re-quoting.

    backend/.venv/bin/python demo/export_iam_csv.py
"""

from __future__ import annotations

import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import iam_data as data  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "data"


def write(name: str, rows: list[dict], columns: list[str]) -> int:
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    k: ";".join(map(str, v)) if isinstance(v, list) else v
                    for k, v in row.items()
                }
            )
    return len(rows)


def main() -> None:
    written: list[tuple[str, int]] = []

    written.append((
        "identities",
        write(
            "identities",
            list(data.IDENTITIES.values()),
            ["username", "display_name", "email", "department", "title", "manager",
             "status", "data_sensitivity", "hired_on", "terminated_on"],
        ),
    ))

    written.append((
        "applications",
        write(
            "applications",
            list(data.APPLICATIONS.values()),
            ["app_id", "name", "department", "criticality", "owner", "connector",
             "in_scope", "last_aoc_review"],
        ),
    ))

    written.append((
        "entitlements",
        write(
            "entitlements",
            list(data.ENTITLEMENTS.values()),
            ["entitlement_id", "name", "application", "type", "privileged",
             "owner", "member_count", "description"],
        ),
    ))

    # The owner's employment status is joined in here rather than left to a
    # lookup: "account belongs to someone who left" is the question this file
    # gets opened to answer.
    accounts = []
    for account in data.ACCOUNTS.values():
        identity = data.IDENTITIES.get(account["owner"] or "")
        accounts.append(
            {
                **account,
                "owner_status": identity["status"] if identity else "UNRESOLVED",
                "in_secret_server": (
                    account["account_name"] in data.SECRET_SERVER
                    if account["account_type"] != "user"
                    else ""
                ),
                "entitlement_count": len(account["entitlements"]),
            }
        )
    written.append((
        "accounts",
        write(
            "accounts",
            accounts,
            ["account_id", "account_name", "account_type", "source", "owner",
             "owner_status", "correlated", "privileged", "interactive_login",
             "in_secret_server", "application", "entitlement_count", "entitlements",
             "last_login", "password_last_set", "created_on"],
        ),
    ))

    written.append((
        "secret_server",
        write(
            "secret_server",
            list(data.SECRET_SERVER.values()),
            ["secret_id", "account_name", "folder", "onboarded_on",
             "rotation_enabled", "last_rotated", "checkout_required"],
        ),
    ))

    written.append((
        "certification_decisions",
        write(
            "certification_decisions",
            data.CERTIFICATION["decisions"],
            ["decision_id", "account_id", "account_name", "entitlement_id",
             "entitlement_name", "application", "reviewer", "decision",
             "decided_on", "comment"],
        ),
    ))

    written.append((
        "remediation_tickets",
        write(
            "remediation_tickets",
            list(data.TICKETS.values()),
            ["ticket_id", "decision_id", "account_name", "entitlement_id",
             "state", "opened_on"],
        ),
    ))

    # The headline finding gets its own file: it is the one an auditor asks for
    # by name, and it should not have to be derived from two others.
    written.append((
        "finding_reinstated_access",
        write(
            "finding_reinstated_access",
            data.REINSTATED,
            ["account_id", "account_name", "entitlement_id", "entitlement_name",
             "application", "revoked_on", "reinstated_on", "reinstated_by", "ticket"],
        ),
    ))

    written.append((
        "sme_responses",
        write(
            "sme_responses",
            list(data.SME_RESPONSES.values()),
            ["application", "sme", "state", "responded_on", "follow_ups_sent",
             "entitlements_confirmed"],
        ),
    ))

    total = sum(count for _, count in written)
    for name, count in written:
        print(f"  {count:>5}  {name}.csv")
    print(f"\n  {total:>5}  rows total, written to {OUT}")

    # The scale claim is checked here too, so a shrunken fixture cannot be
    # exported and handed on unnoticed.
    if total < 1000:
        raise SystemExit(f"Export is too small: {total} rows")


if __name__ == "__main__":
    main()
