"""Suraksha Insurance — a sample insurer's policy and renewal systems (sample_clients.py).

What an insurer's policy admin system offers a renewal agent: a customer's
policies, the policies falling due for renewal (for a campaign), a renewal
quote with a payment link the customer can pay, and recording how the call
went (renew, call back, not renewing).

Test data (tag "Test data" on /insurer/docs): add a policy on your own mobile
(POST /policies), change any policy (PATCH /policies/{policy_no}, e.g.
{"expires_in_days": 7}), POST /reset to go back. Saved in state/insurer.json.
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

SLUG = "insurer"
BUSINESS = "Suraksha Insurance"
INTENTS = ("renew", "callback", "not_renewing")
GRACE_DAYS = {"Motor": 0, "Health": 30, "Term": 30}

app = FastAPI(title=f"{BUSINESS} policy systems (sample client)", description=__doc__, version="1.0.0")
#: Every API route needs the API key; the pages a customer opens from a link do not.
KEYED = [Depends(require_key), Depends(remember_origin)]

#: (policy_no, person, line, plan, sum insured, premium, expires in days, extra)
_POLICIES = [
    ("SI-MTR-240011", 0, "Motor", "Car Secure Comprehensive", 640000, 11800, 7,
     {"vehicle_no": "KA01AB1234", "vehicle": "Hyundai i20 2022", "ncb_percent": 25}),
    ("SI-HLT-240012", 1, "Health", "Family Health Floater 5L", 500000, 18400, 15,
     {"members": 3}),
    ("SI-TRM-240013", 2, "Term", "Suraksha Term Life 1 Cr", 10000000, 14200, 30, {}),
    ("SI-MTR-240014", 3, "Motor", "Two-wheeler Comprehensive", 72000, 2100, -20,
     {"vehicle_no": "MH02CD5678", "vehicle": "Honda Activa 2021", "ncb_percent": 20}),
    ("SI-HLT-240015", 4, "Health", "Individual Health 3L", 300000, 9600, 7, {"members": 1}),
    ("SI-MTR-240016", 5, "Motor", "Car Secure Comprehensive", 520000, 9900, 15,
     {"vehicle_no": "TN38EF9012", "vehicle": "Maruti Swift 2020", "ncb_percent": 35}),
]


def _seed() -> dict[str, dict]:
    policies = {}
    for pno, person, line, plan, si, premium, expires, extra in _POLICIES:
        p = ALL_PEOPLE[person]
        policies[pno] = {
            "policy_no": pno,
            "line": line,
            "plan_name": plan,
            "holder_name": p["name"],
            "mobile": p["phone"],
            "email": p["email"],
            "preferred_language": p["language"],
            "sum_insured": si,
            "annual_premium": premium,
            "start_date": day(expires - 365),
            "expiry_date": day(expires),
            "renewed": False,
            "last_disposition": None,
            **extra,
        }
    return {"policies": policies, "quotes": {}, "dispositions": {}}


DB = TestData(SLUG, _seed)


def _policy(policy_no: str) -> dict:
    p = DB["policies"].get(policy_no.strip().upper())
    if p is None:
        raise HTTPException(404, f"No policy {policy_no}.")
    return p


def _view(p: dict) -> dict:
    days = (date.fromisoformat(p["expiry_date"]) - today()).days
    status = "Active" if days >= 0 else "In grace period" if -days <= GRACE_DAYS.get(p["line"], 0) else "Lapsed"
    return {**p, "status": status, "days_to_expiry": days}


def _quote_figures(v: dict) -> tuple[float, str, str]:
    """(renewal premium, last date to renew, notes)."""
    days = v["days_to_expiry"]
    if v["line"] == "Motor":
        ncb = v.get("ncb_percent", 0)
        if days < -90:
            return round(v["annual_premium"] * 1.25), day(30), "Lapsed over 90 days: the no-claim bonus is lost and a vehicle inspection is needed."
        if days < 0:
            return (round(v["annual_premium"] * 1.06), day(14),
                    f"Lapsed {-days} days ago: a vehicle inspection is needed before renewal; the {ncb}% no-claim bonus is kept if renewed within 90 days.")
        next_ncb = min(ncb + 5 if ncb < 25 else ncb + 10, 50)
        return (round(v["annual_premium"] * 1.04 * (1 - (next_ncb - ncb) / 100)), v["expiry_date"],
                f"No-claim bonus goes from {ncb}% to {next_ncb}% on renewal before expiry.")
    if v["line"] == "Health":
        grace_end = (date.fromisoformat(v["expiry_date"]) + timedelta(days=GRACE_DAYS["Health"])).isoformat()
        return (round(v["annual_premium"] * 1.08), grace_end,
                "Renew within the 30-day grace period to keep waiting-period credits; claims are not paid during the grace period.")
    grace_end = (date.fromisoformat(v["expiry_date"]) + timedelta(days=GRACE_DAYS["Term"])).isoformat()
    return v["annual_premium"], grace_end, "Premium is fixed for the policy term; cover continues if paid within the 30-day grace period."


@app.get("/policies", dependencies=KEYED, operation_id="getCustomerPolicies", tags=["Policies"],
         summary="A customer's policies by mobile, with expiry and status")
def get_policies(mobile: str = Query(description="The policyholder's registered mobile, any format")) -> dict:
    m = clean_phone(mobile)
    return {"mobile": m, "policies": [_view(p) for p in DB["policies"].values() if p["mobile"] == m]}


@app.get("/policies/{policy_no}", dependencies=KEYED, operation_id="getPolicy", tags=["Policies"], summary="One policy by policy number")
def get_policy(policy_no: str) -> dict:
    return _view(_policy(policy_no))


@app.get(
    "/renewals", dependencies=KEYED, operation_id="listRenewalsDue", tags=["Renewals"],
    summary="Policies falling due for renewal within N days, for a renewal campaign",
    description="Policies expiring between today and `within_days` from now (default 30) that are not yet "
                "renewed. `include_lapsed=true` adds policies that expired in the last 90 days.",
)
def list_renewals(
    within_days: int = Query(default=30, ge=0, le=90, description="Expiring within this many days"),
    include_lapsed: bool = Query(default=False, description="Also policies expired in the last 90 days"),
) -> dict:
    rows = []
    for p in DB["policies"].values():
        v = _view(p)
        if p["renewed"]:
            continue
        if 0 <= v["days_to_expiry"] <= within_days or (include_lapsed and -90 <= v["days_to_expiry"] < 0):
            premium, last_date, _ = _quote_figures(v)
            rows.append({
                "policy_no": v["policy_no"], "plan_name": v["plan_name"], "line": v["line"],
                "holder_name": v["holder_name"], "mobile": v["mobile"],
                "preferred_language": v["preferred_language"], "expiry_date": v["expiry_date"],
                "days_to_expiry": v["days_to_expiry"], "status": v["status"],
                "renewal_premium": premium, "last_date": last_date,
            })
    return {"count": len(rows), "renewals": sorted(rows, key=lambda r: r["days_to_expiry"])}


@app.get(
    "/policies/{policy_no}/renewal-quote", dependencies=KEYED, operation_id="getRenewalQuote", tags=["Renewals"],
    summary="Renewal quote: premium, last date to renew, no-claim bonus / notes, and a payment link",
    description="The payment_link opens a page with a Pay now button; paying renews the policy for a year.",
)
def renewal_quote(policy_no: str) -> dict:
    v = _view(_policy(policy_no))
    if v["renewed"]:
        raise HTTPException(409, f"Policy {v['policy_no']} is already renewed, to {v['expiry_date']}.")
    premium, last_date, notes = _quote_figures(v)
    qid = DB.next_id("quotes", "RQ-", 31001)
    quote = {
        "quote_id": qid, "policy_no": v["policy_no"], "plan_name": v["plan_name"],
        "renewal_premium": premium, "gst_included": True, "last_date": last_date,
        "ncb_percent": v.get("ncb_percent"), "notes": notes,
        "payment_link": public_url(SLUG, f"pay/{qid}"),
        "valid_till": (datetime.now(IST) + timedelta(days=7)).isoformat(timespec="seconds"),
        "status": "created",
    }
    DB["quotes"][qid] = quote
    DB.save()
    return quote


class DispositionIn(BaseModel):
    intent: str = Field(description="renew, callback or not_renewing", examples=["callback"])
    remark: str = Field(default="", max_length=1000, examples=["Will renew after salary on the 1st"])
    callback_at: str | None = Field(default=None, description="For a callback: when, ISO date-time")


@app.post(
    "/policies/{policy_no}/disposition", dependencies=KEYED, operation_id="recordRenewalDisposition", tags=["Renewals"],
    summary="Record the outcome of a renewal call: renew, callback or not_renewing",
)
def record_disposition(policy_no: str, body: DispositionIn) -> dict:
    p = _policy(policy_no)
    intent = body.intent.strip().lower().replace("-", "_").replace(" ", "_")
    if intent not in INTENTS:
        raise HTTPException(422, f"intent is one of: {', '.join(INTENTS)}.")
    did = DB.next_id("dispositions", "DISP-", 41001)
    row = {"id": did, "policy_no": p["policy_no"], "mobile": p["mobile"], "intent": intent,
           "remark": body.remark, "callback_at": body.callback_at, "recorded_at": now_iso()}
    DB["dispositions"][did] = row
    p["last_disposition"] = intent
    DB.save()
    msg = {"renew": f"Noted: {p['holder_name']} will renew {p['policy_no']}.",
           "callback": f"Noted: call {p['holder_name']} back" + (f" at {body.callback_at}." if body.callback_at else "."),
           "not_renewing": f"Noted: {p['holder_name']} is not renewing {p['policy_no']}."}[intent]
    return {"id": did, "message": msg, "disposition": row}


@app.get("/dispositions", dependencies=KEYED, operation_id="listRenewalDispositions", tags=["Renewals"], summary="Renewal call outcomes recorded")
def list_dispositions(policy_no: str | None = Query(default=None)) -> dict:
    rows = [d for d in DB["dispositions"].values() if not policy_no or d["policy_no"] == policy_no.strip().upper()]
    return {"dispositions": sorted(rows, key=lambda d: d["recorded_at"], reverse=True)}


@app.get("/pay/{quote_id}", response_class=HTMLResponse, include_in_schema=False)
def pay_page(quote_id: str) -> str:
    q = DB["quotes"].get(quote_id)
    if q is None:
        return page("Link not found", ["This payment link does not exist or was reset."])
    if q["status"] == "paid":
        return page("Policy renewed", [f"Policy {q['policy_no']} is renewed. Thank you."])
    return page(f"Pay ₹{q['renewal_premium']:,.0f} to {BUSINESS}",
                [f"Renewal of {q['plan_name']}", f"Policy {q['policy_no']}"], button="Pay now")


@app.post("/pay/{quote_id}", response_class=HTMLResponse, include_in_schema=False)
def pay_now(quote_id: str) -> str:
    q = DB["quotes"].get(quote_id)
    if q is None:
        return page("Link not found", ["This payment link does not exist or was reset."])
    p = DB["policies"].get(q["policy_no"])
    if q["status"] != "paid" and p is not None:
        base = max(date.fromisoformat(p["expiry_date"]), today())
        p.update(expiry_date=(base + timedelta(days=365)).isoformat(), renewed=True, renewed_on=day(0),
                 annual_premium=q["renewal_premium"])
        q.update(status="paid", paid_at=now_iso())
        DB.save()
    return page("Payment successful", [f"Policy {q['policy_no']} is renewed until {p['expiry_date'] if p else ''}."])


# ---- test data ---------------------------------------------------------------------

class PolicyEdit(BaseModel):
    """Only the fields given change."""

    mobile: str | None = Field(default=None, examples=["+918826889512"])
    holder_name: str | None = None
    preferred_language: str | None = Field(default=None, examples=["hi-IN"])
    plan_name: str | None = None
    line: str | None = Field(default=None, description="Motor, Health or Term")
    sum_insured: float | None = None
    annual_premium: float | None = None
    expiry_date: str | None = Field(default=None, description="YYYY-MM-DD")
    expires_in_days: int | None = Field(default=None, description="Days from today; negative has lapsed")
    vehicle_no: str | None = None
    ncb_percent: int | None = None
    renewed: bool | None = None


class NewPolicy(PolicyEdit):
    policy_no: str | None = Field(default=None, description="Blank: the next number")
    mobile: str = Field(examples=["+918826889512"])
    holder_name: str = Field(examples=["Shiwesh Shiwam"])
    line: str = Field(default="Motor")
    plan_name: str | None = Field(default=None, description="Blank: a standard plan for the line")
    annual_premium: float = 8500
    expires_in_days: int | None = 7


def _apply_policy(p: dict, edit: PolicyEdit) -> None:
    given = edit.model_dump(exclude_unset=True)
    if given.get("mobile"):
        given["mobile"] = valid_mobile(given["mobile"])
    if given.get("line"):
        given["line"] = given["line"].strip().capitalize()
        if given["line"] not in GRACE_DAYS:
            raise HTTPException(422, "line is Motor, Health or Term.")
    days = given.pop("expires_in_days", None)
    p.update({k: v for k, v in given.items() if v is not None})
    if days is not None:
        p["expiry_date"] = day(days)
        p["start_date"] = day(days - 365)


@app.post("/policies", dependencies=KEYED, operation_id="testAddPolicy", tags=["Test data"], status_code=201,
          summary="Test data: add a policy on any mobile (yours), e.g. expiring in 7 days")
def add_policy(body: NewPolicy) -> dict:
    line = body.line.strip().capitalize()
    if line not in GRACE_DAYS:
        raise HTTPException(422, "line is Motor, Health or Term.")
    prefix = {"Motor": "MTR", "Health": "HLT", "Term": "TRM"}[line]
    pno = (body.policy_no or DB.next_id("policies", f"SI-{prefix}-", 240011)).strip().upper()
    if pno in DB["policies"]:
        raise HTTPException(409, f"Policy {pno} exists; change it with PATCH instead.")
    plan = body.plan_name or {"Motor": "Car Secure Comprehensive", "Health": "Individual Health 3L",
                              "Term": "Suraksha Term Life 1 Cr"}[line]
    p = {"policy_no": pno, "line": line, "plan_name": plan, "holder_name": "", "mobile": "",
         "email": "", "preferred_language": "en-IN", "sum_insured": body.sum_insured or 500000,
         "annual_premium": body.annual_premium, "start_date": day(-358), "expiry_date": day(7),
         "renewed": False, "last_disposition": None}
    if line == "Motor":
        p["ncb_percent"] = 20
    _apply_policy(p, body)
    DB["policies"][pno] = p
    DB.save()
    return _view(p)


@app.patch("/policies/{policy_no}", dependencies=KEYED, operation_id="testEditPolicy", tags=["Test data"],
           summary="Test data: change a policy (only the fields you give)")
def edit_policy(policy_no: str, body: PolicyEdit) -> dict:
    p = _policy(policy_no)
    _apply_policy(p, body)
    DB.save()
    return _view(p)


@app.post("/reset", dependencies=KEYED, operation_id="testReset", tags=["Test data"],
          summary="Test data: back to the original policies (every change is undone)")
def reset() -> dict:
    return DB.reset()

