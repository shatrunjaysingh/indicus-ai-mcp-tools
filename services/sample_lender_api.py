"""Sahyog Finance — a sample lender's back office (sample_clients.py).

What a lender's loan management and KYC systems offer a collections or
service agent: a borrower's loans and what is due, the accounts due or past
due for a campaign, a payment link the borrower can actually pay, whether a
payment came in, a promise to pay, a dispute (which takes the account out of
collections), and re-KYC: who is due, a re-KYC link, video-KYC slots.

Days past due (`dpd`) and the status are worked out from `due_on` against
today, so an account 5 days past due today is 6 days past due tomorrow.

Test data (tag "Test data" on /lender/docs): add a loan on your own mobile
(POST /loans), change any loan (PATCH /loans/{loan_no}, e.g. {"dpd": 20}) or
customer's KYC (PATCH /customers/{cif}), POST /reset to go back. Saved in
state/lender.json across restarts.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from sample_clients import (
    ALL_PEOPLE,
    IST,
    TestData,
    clean_phone,
    day,
    now_iso,
    page,
    public_url,
    remember_origin,
    require_key,
    today,
    valid_mobile,
)

SLUG = "lender"
BUSINESS = "Sahyog Finance"

app = FastAPI(title=f"{BUSINESS} loan & KYC systems (sample client)", description=__doc__, version="1.0.0")
#: Every API route needs the API key; the pages a customer opens from a link do not.
KEYED = [Depends(require_key), Depends(remember_origin)]

#: person index in ALL_PEOPLE → (kyc_status, rekyc_due offset, pending documents)
_KYC = {
    0: ("up_to_date", 400, []),
    1: ("due", 10, ["Address proof"]),
    2: ("up_to_date", 250, []),
    3: ("overdue", -12, ["PAN card", "Recent photograph"]),
    4: ("due", 5, ["Address proof"]),
    5: ("up_to_date", 600, []),
    6: ("overdue", -30, ["Address proof", "Signature specimen"]),
}

#: (loan_no, person, product, emi, due in days (negative: past due), outstanding, state)
_LOANS = [
    ("SF-1001", 0, "Two-wheeler loan", 4250, 3, 61200, ""),
    ("SF-1002", 1, "Personal loan", 6800, 0, 142000, ""),
    ("SF-1003", 2, "Consumer durable loan", 2150, -5, 12900, ""),
    ("SF-1004", 3, "Personal loan", 9400, -20, 198500, ""),
    ("SF-1005", 4, "Two-wheeler loan", 3600, -45, 54400, ""),
    ("SF-1006", 0, "Home loan", 18500, -4, 2350000, "paid"),
    ("SF-1007", 5, "Personal loan", 5200, -8, 88000, "disputed"),
    ("SF-1008", 6, "Consumer durable loan", 1890, 7, 9450, ""),
]


def _seed() -> dict[str, dict]:
    customers, loans, payments, disputes = {}, {}, {}, {}
    for i, p in enumerate(ALL_PEOPLE):
        cif = f"CIF{700100 + i}"
        status, due, docs = _KYC[i]
        customers[cif] = {
            "cif": cif,
            "customer_name": p["name"],
            "mobile": p["phone"],
            "preferred_language": p["language"],
            "city": p["city"],
            "kyc_status": status,
            "rekyc_due": day(due),
            "pending_documents": docs,
            "last_kyc_on": day(due - 730),
        }
    cifs = list(customers)
    for loan_no, person, product, emi, due, outstanding, state in _LOANS:
        loans[loan_no] = {
            "loan_no": loan_no,
            "cif": cifs[person],
            "product": product,
            "emi_amount": emi,
            "due_on": day(due),
            "total_outstanding": outstanding,
            "late_fee": 0 if due >= 0 else 500,
            "state": state,  # "" | "paid" | "disputed"; status and dpd are worked out
            "disbursed_on": day(due - 400),
        }
    payments["PAY-5001"] = {
        "payment_id": "PAY-5001", "loan_no": "SF-1006", "amount_received": 18500,
        "paid_at": day(-5) + "T11:42:10+05:30", "utr": "UTR4471200981", "mode": "NACH",
    }
    disputes["DSP-7001"] = {
        "id": "DSP-7001", "loan_no": "SF-1007", "reason": "EMI debited twice last month",
        "status": "Open", "raised_at": day(-6) + "T16:05:00+05:30",
    }
    return {"customers": customers, "loans": loans, "payments": payments, "disputes": disputes,
            "promises": {}, "payment_links": {}, "vkyc_bookings": {}}


DB = TestData(SLUG, _seed)


# ---- views -------------------------------------------------------------------------

def _customer_by_mobile(mobile: str) -> dict | None:
    m = clean_phone(mobile)
    return next((c for c in DB["customers"].values() if c["mobile"] == m), None)


def _loan(loan_no: str) -> dict:
    loan = DB["loans"].get(loan_no.strip().upper())
    if loan is None:
        raise HTTPException(404, f"No loan {loan_no}.")
    return loan


def _view(loan: dict) -> dict:
    """The loan as the system shows it: with the borrower, dpd and status."""
    c = DB["customers"][loan["cif"]]
    days_to_due = (date.fromisoformat(loan["due_on"]) - today()).days
    if loan["state"] == "paid":
        status, dpd = "Paid", 0
    elif loan["state"] == "disputed":
        status, dpd = "Disputed", max(-days_to_due, 0)
    elif days_to_due > 0:
        status, dpd = "Current", 0
    elif days_to_due == 0:
        status, dpd = "Due today", 0
    else:
        status, dpd = "Overdue", -days_to_due
    overdue_months = 0 if dpd == 0 else 1 + dpd // 30
    amount_due = 0 if status == "Paid" else loan["emi_amount"] * max(overdue_months, 1) + (loan["late_fee"] if dpd else 0)
    return {
        "loan_no": loan["loan_no"],
        "cif": loan["cif"],
        "borrower_name": c["customer_name"],
        "mobile": c["mobile"],
        "preferred_language": c["preferred_language"],
        "product": loan["product"],
        "emi_amount": loan["emi_amount"],
        "due_on": loan["due_on"],
        "days_to_due": days_to_due,
        "dpd": dpd,
        "bucket": "Current" if dpd == 0 else "1-30" if dpd <= 30 else "31-60" if dpd <= 60 else "60+",
        "status": status,
        "amount_due": amount_due,
        "late_fee": loan["late_fee"] if dpd else 0,
        "total_outstanding": loan["total_outstanding"],
        "open_dispute": next((d["id"] for d in DB["disputes"].values()
                              if d["loan_no"] == loan["loan_no"] and d["status"] == "Open"), None),
    }


# ---- loans and dues ----------------------------------------------------------------

@app.get(
    "/loans", dependencies=KEYED, operation_id="getBorrowerLoans", tags=["Loans"],
    summary="A borrower's loan accounts and what is due, by mobile",
    description="Every loan on the customer whose registered mobile this is, with EMI, due date, "
                "days past due (dpd), status (Current, Due today, Overdue, Paid, Disputed) and outstanding.",
)
def get_loans(mobile: str = Query(description="The borrower's registered mobile, any format")) -> dict:
    c = _customer_by_mobile(mobile)
    if c is None:
        return {"mobile": clean_phone(mobile), "loans": []}
    mine = [_view(loan) for loan in DB["loans"].values() if loan["cif"] == c["cif"]]
    return {"mobile": c["mobile"], "borrower_name": c["customer_name"], "loans": mine}


@app.get(
    "/dues", dependencies=KEYED, operation_id="listDueAccounts", tags=["Loans"],
    summary="Accounts with an EMI due or past due, for a reminder or collections campaign",
    description="Unpaid, undisputed accounts that are past due or fall due within `due_within_days` "
                "(default 7). Narrow by days past due with min_dpd / max_dpd: reminders before the due "
                "date are `max_dpd=0&due_within_days=3`; early collections `min_dpd=1&max_dpd=30`.",
)
def list_dues(
    min_dpd: int | None = Query(default=None, ge=0, description="Only accounts at least this many days past due"),
    max_dpd: int | None = Query(default=None, ge=0, description="Only accounts at most this many days past due (0: not yet overdue)"),
    due_within_days: int = Query(default=7, ge=0, le=60, description="Also include accounts not yet due that fall due within this many days"),
) -> dict:
    rows = []
    for loan in DB["loans"].values():
        v = _view(loan)
        if v["status"] in ("Paid", "Disputed"):
            continue
        if v["dpd"] == 0 and v["days_to_due"] > due_within_days:
            continue
        if min_dpd is not None and v["dpd"] < min_dpd:
            continue
        if max_dpd is not None and v["dpd"] > max_dpd:
            continue
        rows.append(v)
    rows.sort(key=lambda v: (-v["dpd"], v["days_to_due"]))
    return {"count": len(rows), "accounts": rows}


@app.get("/loans/{loan_no}", dependencies=KEYED, operation_id="getLoan", tags=["Loans"], summary="One loan account by loan number")
def get_loan(loan_no: str) -> dict:
    return _view(_loan(loan_no))


# ---- payments ----------------------------------------------------------------------

class PaymentLinkIn(BaseModel):
    loan_no: str = Field(examples=["SF-1003"])
    amount: float | None = Field(default=None, gt=0, description="Rupees; blank: the amount due")
    mobile: str | None = Field(default=None, description="Where the link is sent; blank: the registered mobile")


@app.post(
    "/payment-links", dependencies=KEYED, operation_id="createPaymentLink", tags=["Payments"],
    summary="Create a payment link for a loan's dues",
    description="A link the borrower opens to pay (valid 3 days). Opening `short_url` shows a page "
                "with a Pay now button; paying marks the EMI paid, which GET /payments/{loan_no} then shows.",
)
def create_payment_link(body: PaymentLinkIn) -> dict:
    v = _view(_loan(body.loan_no))
    if v["status"] == "Paid":
        raise HTTPException(409, f"Loan {v['loan_no']} has nothing due; this month's EMI is paid.")
    amount = round(body.amount or v["amount_due"], 2)
    link_id = DB.next_id("payment_links", "plink_", 80001)
    link = {
        "id": link_id,
        "loan_no": v["loan_no"],
        "amount": amount,
        "currency": "INR",
        "mobile": valid_mobile(body.mobile) if body.mobile else v["mobile"],
        "short_url": public_url(SLUG, f"pay/{link_id}"),
        "expire_by": (datetime.now(IST) + timedelta(days=3)).isoformat(timespec="seconds"),
        "status": "created",
        "created_at": now_iso(),
    }
    DB["payment_links"][link_id] = link
    DB.save()
    return link


@app.get("/payment-links/{link_id}", dependencies=KEYED, operation_id="getPaymentLink", tags=["Payments"], summary="One payment link and whether it was paid")
def get_payment_link(link_id: str) -> dict:
    link = DB["payment_links"].get(link_id.strip())
    if link is None:
        raise HTTPException(404, f"No payment link {link_id}.")
    return link


def _record_payment(loan_no: str, amount: float, mode: str) -> dict:
    loan = _loan(loan_no)
    pid = DB.next_id("payments", "PAY-", 5001)
    paid = {"payment_id": pid, "loan_no": loan["loan_no"], "amount_received": amount,
            "paid_at": now_iso(), "utr": f"UTR{4471200000 + int(pid[4:]) * 7}", "mode": mode}
    DB["payments"][pid] = paid
    loan["state"] = "paid"
    loan["total_outstanding"] = max(round(loan["total_outstanding"] - amount, 2), 0)
    return paid


@app.get("/pay/{link_id}", response_class=HTMLResponse, include_in_schema=False)
def pay_page(link_id: str) -> str:
    link = DB["payment_links"].get(link_id)
    if link is None:
        return page("Link not found", ["This payment link does not exist or was reset."])
    if link["status"] == "paid":
        return page("Paid", [f"₹{link['amount']:,.0f} received for loan {link['loan_no']}. Thank you."])
    return page(f"Pay ₹{link['amount']:,.0f} to {BUSINESS}",
                [f"Loan {link['loan_no']}", f"Link valid until {link['expire_by'][:16].replace('T', ' ')}"],
                button="Pay now")


@app.post("/pay/{link_id}", response_class=HTMLResponse, include_in_schema=False)
def pay_now(link_id: str) -> str:
    link = DB["payment_links"].get(link_id)
    if link is None:
        return page("Link not found", ["This payment link does not exist or was reset."])
    if link["status"] != "paid":
        paid = _record_payment(link["loan_no"], link["amount"], "UPI (payment link)")
        link.update(status="paid", paid_at=paid["paid_at"], utr=paid["utr"])
        DB.save()
    return page("Payment successful", [f"₹{link['amount']:,.0f} received for loan {link['loan_no']}.",
                                       f"UTR {link['utr']}"])


@app.get(
    "/payments/{loan_no}", dependencies=KEYED, operation_id="getPaymentStatus", tags=["Payments"],
    summary="Has this loan's EMI been paid — amount, time and UTR of the latest payment",
)
def get_payments(loan_no: str) -> dict:
    loan = _loan(loan_no)
    mine = sorted((p for p in DB["payments"].values() if p["loan_no"] == loan["loan_no"]),
                  key=lambda p: p["paid_at"], reverse=True)
    last = mine[0] if mine else None
    return {
        "loan_no": loan["loan_no"],
        "paid": loan["state"] == "paid",
        "amount_received": last["amount_received"] if last else 0,
        "paid_at": last["paid_at"] if last else None,
        "utr": last["utr"] if last else None,
        "payments": mine,
    }


# ---- promises and disputes ---------------------------------------------------------

class PromiseIn(BaseModel):
    loan_no: str = Field(examples=["SF-1004"])
    ptp_date: str = Field(description="YYYY-MM-DD, today or within 30 days", examples=["2026-11-12"])
    ptp_amount: float | None = Field(default=None, gt=0, description="Rupees; blank: the amount due")
    remark: str = Field(default="", max_length=500)


@app.post(
    "/promises", dependencies=KEYED, operation_id="recordPromiseToPay", tags=["Collections"],
    summary="Record a borrower's promise to pay (PTP) by a date",
)
def record_promise(body: PromiseIn) -> dict:
    v = _view(_loan(body.loan_no))
    try:
        when = date.fromisoformat(body.ptp_date)
    except ValueError as exc:
        raise HTTPException(422, "ptp_date must be YYYY-MM-DD.") from exc
    if not 0 <= (when - today()).days <= 30:
        raise HTTPException(422, "A promise date must be today or within the next 30 days.")
    pid = DB.next_id("promises", "PTP-", 6001)
    amount = round(body.ptp_amount or v["amount_due"], 2)
    DB["promises"][pid] = {"id": pid, "loan_no": v["loan_no"], "mobile": v["mobile"], "ptp_date": body.ptp_date,
                           "ptp_amount": amount, "remark": body.remark, "status": "Open", "created_at": now_iso()}
    DB.save()
    return {"id": pid, "message": f"Noted: ₹{amount:,.0f} on loan {v['loan_no']} by {body.ptp_date}.",
            "promise": DB["promises"][pid]}


@app.get("/promises", dependencies=KEYED, operation_id="listPromisesToPay", tags=["Collections"], summary="Promises to pay recorded, newest first")
def list_promises(loan_no: str | None = Query(default=None)) -> dict:
    rows = [p for p in DB["promises"].values() if not loan_no or p["loan_no"] == loan_no.strip().upper()]
    return {"promises": sorted(rows, key=lambda p: p["created_at"], reverse=True)}


class DisputeIn(BaseModel):
    loan_no: str = Field(examples=["SF-1003"])
    reason: str = Field(min_length=3, max_length=1000, examples=["I already paid this EMI in cash at the branch"])


@app.post(
    "/disputes", dependencies=KEYED, operation_id="raiseDispute", tags=["Collections"],
    summary="Raise a dispute on a loan; it leaves the collections list (/dues) until resolved",
)
def raise_dispute(body: DisputeIn) -> dict:
    loan = _loan(body.loan_no)
    did = DB.next_id("disputes", "DSP-", 7001)
    DB["disputes"][did] = {"id": did, "loan_no": loan["loan_no"], "reason": body.reason.strip(),
                           "status": "Open", "raised_at": now_iso()}
    if loan["state"] != "paid":
        loan["state"] = "disputed"
    DB.save()
    return {"id": did, "message": f"Dispute {did} is raised on loan {loan['loan_no']}; our team will call within 2 working days.",
            "dispute": DB["disputes"][did]}


@app.get("/disputes", dependencies=KEYED, operation_id="listDisputes", tags=["Collections"], summary="Disputes raised, newest first")
def list_disputes(loan_no: str | None = Query(default=None)) -> dict:
    rows = [d for d in DB["disputes"].values() if not loan_no or d["loan_no"] == loan_no.strip().upper()]
    return {"disputes": sorted(rows, key=lambda d: d["raised_at"], reverse=True)}


# ---- KYC -----------------------------------------------------------------------------

def _kyc(c: dict) -> dict:
    return {
        "cif": c["cif"],
        "customer_name": c["customer_name"],
        "mobile": c["mobile"],
        "preferred_language": c["preferred_language"],
        "kyc_status": c["kyc_status"],
        "rekyc_due": c["rekyc_due"],
        "pending_documents": c["pending_documents"],
        "rekyc_link": public_url(SLUG, f"rekyc/{c['cif']}") if c["kyc_status"] != "up_to_date" else None,
    }


@app.get(
    "/kyc", dependencies=KEYED, operation_id="getKycStatus", tags=["KYC"],
    summary="A customer's KYC status by mobile: up_to_date, due or overdue, with the re-KYC link",
)
def get_kyc(mobile: str = Query(description="The customer's registered mobile")) -> dict:
    c = _customer_by_mobile(mobile)
    if c is None:
        raise HTTPException(404, "No customer with that mobile.")
    return _kyc(c)


@app.get(
    "/kyc/due", dependencies=KEYED, operation_id="listKycDue", tags=["KYC"],
    summary="Customers whose re-KYC is due or overdue, for a re-KYC campaign",
)
def list_kyc_due() -> dict:
    rows = [_kyc(c) for c in DB["customers"].values() if c["kyc_status"] in ("due", "overdue")]
    return {"customers": sorted(rows, key=lambda r: r["rekyc_due"])}


@app.get("/rekyc/{cif}", response_class=HTMLResponse, include_in_schema=False)
def rekyc_page(cif: str) -> str:
    c = DB["customers"].get(cif)
    if c is None:
        return page("Link not found", ["This re-KYC link does not exist."])
    if c["kyc_status"] == "up_to_date":
        return page("KYC up to date", [f"Thank you, {c['customer_name']}. Nothing more is needed."])
    docs = ", ".join(c["pending_documents"]) or "none"
    return page(f"{BUSINESS}: update your KYC", [f"Customer {c['cif']}, {c['customer_name']}",
                                                 f"Documents needed: {docs}"], button="Submit documents")


@app.post("/rekyc/{cif}", response_class=HTMLResponse, include_in_schema=False)
def rekyc_done(cif: str) -> str:
    c = DB["customers"].get(cif)
    if c is None:
        return page("Link not found", ["This re-KYC link does not exist."])
    c.update(kyc_status="up_to_date", pending_documents=[], last_kyc_on=day(0), rekyc_due=day(730))
    DB.save()
    return page("KYC updated", [f"Thank you, {c['customer_name']}. Your KYC is up to date."])


def _slots_for(d: date) -> list[dict]:
    booked = {b["slot_id"] for b in DB["vkyc_bookings"].values() if b["status"] == "Booked"}
    out = []
    for minutes in range(10 * 60, 17 * 60 + 30, 30):
        start = datetime(d.year, d.month, d.day, minutes // 60, minutes % 60, tzinfo=IST)
        if start <= datetime.now(IST):
            continue
        sid = f"VK-{d:%Y%m%d}-{minutes // 60:02d}{minutes % 60:02d}"
        out.append({"slot_id": sid, "start_time": start.isoformat(),
                    "end_time": (start + timedelta(minutes=15)).isoformat(), "available": sid not in booked})
    return out


@app.get(
    "/vkyc/slots", dependencies=KEYED, operation_id="listVideoKycSlots", tags=["KYC"],
    summary="Free video-KYC slots on a day (10:00–17:30, every 30 minutes)",
)
def vkyc_slots(date: str | None = Query(default=None, description="YYYY-MM-DD; blank: tomorrow")) -> dict:
    try:
        d = datetime.fromisoformat(date).date() if date else today() + timedelta(days=1)
    except ValueError as exc:
        raise HTTPException(422, "date must be YYYY-MM-DD.") from exc
    return {"date": d.isoformat(), "slots": [s for s in _slots_for(d) if s["available"]]}


class VkycBookingIn(BaseModel):
    slot_id: str = Field(examples=["VK-20261110-1030"])
    mobile: str = Field(examples=["+919000000111"])


@app.post("/vkyc/bookings", dependencies=KEYED, operation_id="bookVideoKyc", tags=["KYC"], summary="Book a video-KYC slot for a customer")
def book_vkyc(body: VkycBookingIn) -> dict:
    try:
        _, ymd, _hm = body.slot_id.strip().upper().split("-")
        d = datetime.strptime(ymd, "%Y%m%d").date()
    except ValueError as exc:
        raise HTTPException(422, "slot_id looks like VK-20261110-1030; take one from /vkyc/slots.") from exc
    slot = next((s for s in _slots_for(d) if s["slot_id"] == body.slot_id.strip().upper()), None)
    if slot is None:
        raise HTTPException(404, f"No slot {body.slot_id}.")
    if not slot["available"]:
        raise HTTPException(409, f"Slot {slot['slot_id']} is taken; pick another from /vkyc/slots.")
    mobile = valid_mobile(body.mobile)
    c = _customer_by_mobile(mobile)
    bid = DB.next_id("vkyc_bookings", "VKB-", 9001)
    booking = {"id": bid, "slot_id": slot["slot_id"], "mobile": mobile, "cif": c["cif"] if c else None,
               "start_time": slot["start_time"], "join_url": public_url(SLUG, f"vkyc/join/{bid}"),
               "status": "Booked", "booked_at": now_iso()}
    DB["vkyc_bookings"][bid] = booking
    DB.save()
    when = slot["start_time"][:16].replace("T", " at ")
    return {"id": bid, "join_url": booking["join_url"], "start_time": slot["start_time"],
            "message": f"Video KYC booked for {when}. Keep your PAN and Aadhaar ready; join from {booking['join_url']}."}


@app.get("/vkyc/bookings", dependencies=KEYED, operation_id="listVideoKycBookings", tags=["KYC"], summary="Video-KYC bookings, by mobile or all")
def list_vkyc(mobile: str | None = Query(default=None)) -> dict:
    rows = [b for b in DB["vkyc_bookings"].values() if not mobile or b["mobile"] == clean_phone(mobile)]
    return {"bookings": sorted(rows, key=lambda b: b["start_time"])}


@app.get("/vkyc/join/{booking_id}", response_class=HTMLResponse, include_in_schema=False)
def vkyc_join(booking_id: str) -> str:
    b = DB["vkyc_bookings"].get(booking_id)
    if b is None:
        return page("Link not found", ["This video-KYC booking does not exist."])
    return page(f"{BUSINESS} video KYC", [f"Your call is at {b['start_time'][:16].replace('T', ' ')}.",
                                          "Our agent will start the video call here. Keep your PAN and Aadhaar ready."])


# ---- test data ---------------------------------------------------------------------

def _customer_for(mobile: str, name: str | None, language: str | None) -> str:
    """The customer (CIF) with this mobile, made if new; name/language updated if given."""
    mobile = valid_mobile(mobile)
    c = _customer_by_mobile(mobile)
    if c is None:
        cif = DB.next_id("customers", "CIF", 700100)
        c = DB["customers"][cif] = {
            "cif": cif, "customer_name": name or "Test borrower", "mobile": mobile,
            "preferred_language": language or "en-IN", "city": "", "kyc_status": "up_to_date",
            "rekyc_due": day(365), "pending_documents": [], "last_kyc_on": day(-365),
        }
    if name:
        c["customer_name"] = name
    if language:
        c["preferred_language"] = language
    return c["cif"]


class LoanEdit(BaseModel):
    """Only the fields given change. A new mobile moves the loan to that customer (made if new)."""

    mobile: str | None = Field(default=None, examples=["+918826889512"])
    borrower_name: str | None = Field(default=None, examples=["Shiwesh Shiwam"])
    preferred_language: str | None = Field(default=None, examples=["hi-IN"])
    product: str | None = None
    emi_amount: float | None = Field(default=None, gt=0)
    total_outstanding: float | None = Field(default=None, ge=0)
    due_on: str | None = Field(default=None, description="YYYY-MM-DD")
    due_in_days: int | None = Field(default=None, description="Days from today; negative is past due")
    dpd: int | None = Field(default=None, ge=0, description="Make it this many days past due (sets due_on)")
    status: str | None = Field(default=None, description="'paid', 'disputed' or 'open' (worked out from due_on)")


class NewLoan(LoanEdit):
    loan_no: str | None = Field(default=None, description="Blank: the next SF- number")
    mobile: str = Field(examples=["+918826889512"])
    borrower_name: str = Field(examples=["Shiwesh Shiwam"])
    product: str = Field(default="Personal loan")
    emi_amount: float = Field(default=3500, gt=0)


def _apply_loan(loan: dict, edit: LoanEdit) -> None:
    given = edit.model_dump(exclude_unset=True)
    if {"mobile", "borrower_name", "preferred_language"} & given.keys():
        cur = DB["customers"].get(loan.get("cif", ""), {})
        loan["cif"] = _customer_for(given.get("mobile") or cur.get("mobile", ""), given.get("borrower_name"),
                                    given.get("preferred_language"))
    for key in ("product", "emi_amount", "total_outstanding", "due_on"):
        if key in given:
            loan[key] = given[key]
    if given.get("due_in_days") is not None:
        loan["due_on"] = day(given["due_in_days"])
    if given.get("dpd") is not None:
        loan["due_on"] = day(-given["dpd"])
        loan["state"] = "" if loan["state"] == "paid" else loan["state"]
    if "status" in given:
        s = (given["status"] or "").strip().lower()
        loan["state"] = {"paid": "paid", "disputed": "disputed"}.get(s, "")
        if loan["state"] != "disputed":  # out of dispute: its open disputes are settled
            for d in DB["disputes"].values():
                if d["loan_no"] == loan["loan_no"] and d["status"] == "Open":
                    d["status"] = "Resolved"
    loan["late_fee"] = 500 if date.fromisoformat(loan["due_on"]) < today() else 0


@app.post("/loans", dependencies=KEYED, operation_id="testAddLoan", tags=["Test data"], status_code=201,
          summary="Test data: add a loan on any mobile (yours), e.g. 20 days past due")
def add_loan(body: NewLoan) -> dict:
    loan_no = (body.loan_no or DB.next_id("loans", "SF-", 1001)).strip().upper()
    if loan_no in DB["loans"]:
        raise HTTPException(409, f"Loan {loan_no} exists; change it with PATCH instead.")
    loan = {"loan_no": loan_no, "cif": "", "product": body.product, "emi_amount": body.emi_amount,
            "due_on": day(3), "total_outstanding": body.emi_amount * 12, "late_fee": 0, "state": "",
            "disbursed_on": day(-365)}
    _apply_loan(loan, body)
    DB["loans"][loan_no] = loan
    DB.save()
    return _view(loan)


@app.patch("/loans/{loan_no}", dependencies=KEYED, operation_id="testEditLoan", tags=["Test data"],
           summary="Test data: change a loan (only the fields you give)")
def edit_loan(loan_no: str, body: LoanEdit) -> dict:
    loan = _loan(loan_no)
    _apply_loan(loan, body)
    DB.save()
    return _view(loan)


class CustomerEdit(BaseModel):
    customer_name: str | None = None
    mobile: str | None = None
    preferred_language: str | None = Field(default=None, examples=["ta-IN"])
    kyc_status: str | None = Field(default=None, description="up_to_date, due or overdue")
    rekyc_due: str | None = Field(default=None, description="YYYY-MM-DD")
    pending_documents: list[str] | None = None


@app.patch("/customers/{cif}", dependencies=KEYED, operation_id="testEditCustomer", tags=["Test data"],
           summary="Test data: change a customer's details or KYC status")
def edit_customer(cif: str, body: CustomerEdit) -> dict:
    c = DB["customers"].get(cif.strip().upper())
    if c is None:
        raise HTTPException(404, f"No customer {cif}.")
    given = body.model_dump(exclude_unset=True)
    if given.get("mobile"):
        given["mobile"] = valid_mobile(given["mobile"])
    if given.get("kyc_status") and given["kyc_status"] not in ("up_to_date", "due", "overdue"):
        raise HTTPException(422, "kyc_status is up_to_date, due or overdue.")
    c.update({k: v for k, v in given.items() if v is not None})
    DB.save()
    return _kyc(c)


@app.post("/reset", dependencies=KEYED, operation_id="testReset", tags=["Test data"],
          summary="Test data: back to the original loans and customers (every change is undone)")
def reset() -> dict:
    return DB.reset()

