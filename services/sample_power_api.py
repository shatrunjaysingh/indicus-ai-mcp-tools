"""Brightline Power — a sample electricity utility's back office (sample_clients.py).

What a utility's billing and outage systems offer a help bot: a consumer's
accounts, their bills and a payment link, whether their area has a power cut
and when it is expected back, and complaints — raise one, follow it up. For a
bill-reminder campaign, GET /bills/due lists every unpaid bill with the
consumer's mobile, language and a payment link.

Changes last until a restart. To try a reminder on your own phone, PATCH
/accounts/{consumer_number} with your mobile.
"""

from __future__ import annotations

from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from sample_clients import ALL_PEOPLE, clean_phone, day, now_iso, require_key, today, valid_mobile

app = FastAPI(
    title="Brightline Power customer systems (sample client)",
    description=__doc__,
    version="1.0.0",
    dependencies=[Depends(require_key)],
)

#: (person, consumer number, tariff, monthly ₹ for the last three bills, latest paid?)
_ACCOUNTS = [
    (0, "BP1004417", "Domestic LT-1", [1840.0, 2215.0, 2390.0], False),
    (1, "BP2009921", "Domestic LT-1", [960.0, 1120.0, 1035.0], True),
    (2, "BP3001184", "Commercial LT-2", [8450.0, 9120.0, 8790.0], False),
    (3, "BP4007736", "Domestic LT-1", [3120.0, 2980.0, 3340.0], True),
]
#: Asha has a second connection (her shop); Sunita and Karthik (Hindi, Tamil) have unpaid bills.
_EXTRA = [
    (0, "BP1004418", "Commercial LT-2", [5120.0, 4870.0, 5340.0], True),
    (4, "BP5002210", "Domestic LT-1", [1420.0, 1610.0, 1785.0], False),
    (5, "BP6003390", "Domestic LT-1", [2260.0, 2045.0, 2190.0], False),
]

ACCOUNTS: dict[str, dict] = {}
BILLS: dict[str, list[dict]] = {}
for i, (p, cn, tariff, amounts, latest_paid) in enumerate(_ACCOUNTS + _EXTRA):
    person = ALL_PEOPLE[p]
    ACCOUNTS[cn] = {
        "consumer_number": cn,
        "name": person["name"],
        "phone": person["phone"],
        "address": person["address"] + (" (shop)" if (p, cn) == (0, "BP1004418") else ""),
        "area": person["city"],
        "pincode": person["pincode"],
        "tariff": tariff,
        "status": "Active",
        "language": person["language"],
    }
    bills = []
    for k, amount in enumerate(amounts):
        months_ago = len(amounts) - 1 - k
        due = day(5 - 30 * months_ago)
        paid = months_ago > 0 or latest_paid
        bills.append(
            {
                "bill_id": f"{cn}-{k + 1:02d}",
                "consumer_number": cn,
                "period": f"{months_ago} month(s) ago" if months_ago else "This month",
                "units_kwh": int(amount / 7.5),
                "amount": amount,
                "due_date": due,
                "status": "Paid" if paid else "Unpaid",
                "paid_on": day(2 - 30 * months_ago) if paid else None,
            }
        )
    BILLS[cn] = sorted(bills, key=lambda b: b["due_date"], reverse=True)

#: area → current outage, if any.
OUTAGES = {
    "Kolkata": {
        "area": "Kolkata",
        "status": "Power cut",
        "cause": "Transformer repair at Park Street substation",
        "started_at": day(0) + "T09:40:00+05:30",
        "expected_restore": day(0) + "T15:30:00+05:30",
    },
    "Chennai": {
        "area": "Chennai",
        "status": "Planned shutdown",
        "cause": "Line maintenance",
        "started_at": day(1) + "T10:00:00+05:30",
        "expected_restore": day(1) + "T14:00:00+05:30",
    },
}

COMPLAINTS: dict[str, dict] = {
    "BPC-50211": {
        "ticket": "BPC-50211",
        "consumer_number": "BP2009921",
        "category": "Voltage fluctuation",
        "description": "Lights flicker every evening.",
        "status": "Engineer assigned",
        "opened_at": day(-2) + "T18:10:00+05:30",
        "expected_by": day(1),
    }
}
CATEGORIES = ["No power", "Voltage fluctuation", "Bill dispute", "Meter fault", "New connection", "Other"]


def _account(cn: str) -> dict:
    a = ACCOUNTS.get(cn.strip().upper())
    if a is None:
        raise HTTPException(404, f"No consumer number {cn}.")
    return a


@app.get("/accounts", operation_id="findAccounts", summary="A consumer's electricity accounts by mobile")
def find_accounts(phone: str = Query(description="The consumer's registered mobile")) -> dict:
    mine = [a for a in ACCOUNTS.values() if a["phone"] == clean_phone(phone)]
    return {"accounts": mine}


def _pay_url(cn: str) -> str:
    return f"https://pay.example.com/brightline/{cn}"


@app.get(
    "/bills/due", operation_id="listBillsDue", summary="Unpaid bills, for a bill-reminder campaign",
    description="Every unpaid bill due within `within_days` (default 15) or already overdue, with the "
                "consumer's mobile, name, language and a payment link.",
)
def bills_due(within_days: int = Query(default=15, ge=0, le=60, description="Due within this many days (overdue bills are always included)")) -> dict:
    rows = []
    for cn, bills in BILLS.items():
        a = ACCOUNTS[cn]
        for b in bills:
            days = (date.fromisoformat(b["due_date"]) - today()).days
            if b["status"] == "Unpaid" and days <= within_days:
                rows.append({"consumer_number": cn, "consumer_name": a["name"], "mobile": a["phone"],
                             "language": a["language"], "bill_id": b["bill_id"], "bill_amount": b["amount"],
                             "due_date": b["due_date"], "days_to_due": days, "payment_link": _pay_url(cn)})
    return {"count": len(rows), "bills": sorted(rows, key=lambda r: r["due_date"])}


@app.get("/accounts/{consumer_number}", operation_id="getAccount", summary="One account")
def get_account(consumer_number: str) -> dict:
    return _account(consumer_number)


@app.get("/accounts/{consumer_number}/bills", operation_id="getBills", summary="The latest bills, newest first")
def get_bills(consumer_number: str) -> dict:
    a = _account(consumer_number)
    return {"consumer_number": a["consumer_number"], "phone": a["phone"], "bills": BILLS[a["consumer_number"]]}


@app.get("/accounts/{consumer_number}/payment-link", operation_id="getPaymentLink", summary="A link to pay what is due")
def payment_link(consumer_number: str) -> dict:
    a = _account(consumer_number)
    due = [b for b in BILLS[a["consumer_number"]] if b["status"] == "Unpaid"]
    total = round(sum(b["amount"] for b in due), 2)
    return {
        "consumer_number": a["consumer_number"],
        "phone": a["phone"],
        "amount_due": total,
        "pay_url": _pay_url(a["consumer_number"]) if total else None,
        "message": "Nothing is due." if not total else f"₹{total:,.0f} is due.",
    }


@app.get("/accounts/{consumer_number}/outage", operation_id="getOutage", summary="Is there a power cut at this account's address")
def account_outage(consumer_number: str) -> dict:
    a = _account(consumer_number)
    o = OUTAGES.get(a["area"])
    return {
        "consumer_number": a["consumer_number"],
        "phone": a["phone"],
        "area": a["area"],
        "status": o["status"] if o else "Normal supply",
        "cause": o["cause"] if o else None,
        "expected_restore": o["expected_restore"] if o else None,
    }


class ComplaintIn(BaseModel):
    consumer_number: str
    category: str = Field(description=f"One of: {', '.join(CATEGORIES)}")
    description: str = Field(min_length=3, max_length=1000)


@app.post("/complaints", operation_id="raiseComplaint", summary="Raise a complaint")
def raise_complaint(body: ComplaintIn) -> dict:
    a = _account(body.consumer_number)
    category = next((c for c in CATEGORIES if c.lower() == body.category.strip().lower()), "Other")
    ticket = f"BPC-{50212 + len(COMPLAINTS)}"
    COMPLAINTS[ticket] = {
        "ticket": ticket,
        "consumer_number": a["consumer_number"],
        "phone": a["phone"],
        "category": category,
        "description": body.description.strip(),
        "status": "Registered",
        "opened_at": now_iso(),
        "expected_by": day(2),
    }
    return {"message": f"Complaint {ticket} is registered; we will act on it by {day(2)}.", "complaint": COMPLAINTS[ticket]}


@app.get("/complaints", operation_id="listComplaints", summary="A consumer's complaints")
def list_complaints(phone: str = Query(description="The consumer's registered mobile")) -> dict:
    mine = {a["consumer_number"] for a in ACCOUNTS.values() if a["phone"] == clean_phone(phone)}
    return {"complaints": [c for c in COMPLAINTS.values() if c["consumer_number"] in mine]}


@app.get("/complaints/{ticket}", operation_id="getComplaint", summary="One complaint")
def get_complaint(ticket: str) -> dict:
    c = COMPLAINTS.get(ticket.strip().upper())
    if c is None:
        raise HTTPException(404, f"No complaint {ticket}.")
    return {**c, "phone": ACCOUNTS[c["consumer_number"]]["phone"]}


class AccountEdit(BaseModel):
    """Only the fields given change."""

    phone: str | None = Field(default=None, examples=["+918826889512"])
    name: str | None = Field(default=None, examples=["Shiwesh Shiwam"])
    language: str | None = Field(default=None, examples=["hi-IN"])


@app.patch("/accounts/{consumer_number}", operation_id="testEditAccount", tags=["Test data"],
           summary="Test data: put an account on your mobile, or change its name or language (until a restart)")
def edit_account(consumer_number: str, body: AccountEdit) -> dict:
    a = _account(consumer_number)
    given = body.model_dump(exclude_unset=True)
    if given.get("phone"):
        given["phone"] = valid_mobile(given["phone"])
    a.update({k: v for k, v in given.items() if v is not None})
    return a
