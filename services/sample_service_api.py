"""FixRight Service — a sample appliance and battery service company's back
office (sample_clients.py).

What a service business offers a help bot: a customer's registered products
and whether each is under warranty, their service requests with the
technician and visit time, and booking or moving a visit.
"""

from __future__ import annotations

from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from sample_clients import PEOPLE, clean_phone, day, now_iso, require_key, today

app = FastAPI(
    title="FixRight Service systems (sample client)",
    description=__doc__,
    version="1.0.0",
    dependencies=[Depends(require_key)],
)

#: (person, serial, product, bought days ago, warranty months)
_PRODUCTS = [
    (0, "FR-INV-77120", "Inverter battery 150 Ah", -400, 36),
    (0, "FR-AC-30911", "Split AC 1.5 ton", -900, 24),
    (1, "FR-CAR-55410", "Car battery 45 Ah", -200, 24),
    (2, "FR-INV-77345", "Inverter battery 200 Ah", -1200, 36),
    (3, "FR-WM-12006", "Washing machine 7 kg", -60, 24),
]

PRODUCTS: dict[str, dict] = {}
for p, serial, name, bought, months in _PRODUCTS:
    person = PEOPLE[p]
    bought_on = day(bought)
    until = date.fromisoformat(bought_on).replace(day=1)
    year, month = until.year + (until.month - 1 + months) // 12, (until.month - 1 + months) % 12 + 1
    warranty_until = until.replace(year=year, month=month).isoformat()
    PRODUCTS[serial] = {
        "serial": serial,
        "product": name,
        "phone": person["phone"],
        "owner": person["name"],
        "purchased_on": bought_on,
        "warranty_until": warranty_until,
        "address": person["address"],
    }

REQUESTS: dict[str, dict] = {
    "FRS-90021": {
        "request_id": "FRS-90021",
        "serial": "FR-INV-77120",
        "issue": "Backup lasts only 30 minutes",
        "status": "Technician on the way",
        "technician": "Imran K.",
        "technician_phone": "+919800001111",
        "visit_on": day(0),
        "visit_window": "2 pm – 4 pm",
        "opened_at": day(-1) + "T11:20:00+05:30",
    },
    "FRS-90007": {
        "request_id": "FRS-90007",
        "serial": "FR-CAR-55410",
        "issue": "Car does not start in the morning",
        "status": "Completed",
        "technician": "Suresh P.",
        "technician_phone": "+919800002222",
        "visit_on": day(-15),
        "visit_window": "10 am – 12 pm",
        "opened_at": day(-16) + "T09:05:00+05:30",
        "resolution": "Battery replaced under warranty",
    },
}
WINDOWS = ["10 am – 12 pm", "12 pm – 2 pm", "2 pm – 4 pm", "4 pm – 6 pm"]


def _product(serial: str) -> dict:
    p = PRODUCTS.get(serial.strip().upper())
    if p is None:
        raise HTTPException(404, f"No product with serial {serial}.")
    return p


def _with_warranty(p: dict) -> dict:
    left = (date.fromisoformat(p["warranty_until"]) - today()).days
    return {**p, "in_warranty": left >= 0, "warranty_days_left": max(left, 0)}


def _request(rid: str) -> dict:
    r = REQUESTS.get(rid.strip().upper())
    if r is None:
        raise HTTPException(404, f"No service request {rid}.")
    p = PRODUCTS[r["serial"]]
    return {**r, "product": p["product"], "phone": p["phone"]}


@app.get("/products", operation_id="listProducts", summary="A customer's registered products, with warranty")
def list_products(phone: str = Query(description="The customer's registered mobile")) -> dict:
    return {"products": [_with_warranty(p) for p in PRODUCTS.values() if p["phone"] == clean_phone(phone)]}


@app.get("/warranty/{serial}", operation_id="getWarranty", summary="Is this product under warranty")
def get_warranty(serial: str) -> dict:
    return _with_warranty(_product(serial))


@app.get("/requests", operation_id="listRequests", summary="A customer's service requests, newest first")
def list_requests(phone: str = Query(description="The customer's registered mobile")) -> dict:
    mine = [_request(r) for r in REQUESTS if PRODUCTS[REQUESTS[r]["serial"]]["phone"] == clean_phone(phone)]
    return {"requests": sorted(mine, key=lambda r: r["opened_at"], reverse=True)}


@app.get("/visits", operation_id="listScheduledVisits", summary="Technician visits scheduled soon (for confirmation calls)")
def list_visits(
    within_days: int = Query(default=1, ge=0, le=7, description="Today and this many days ahead"),
) -> dict:
    """Every open request with a visit from today to `within_days` ahead: who to
    call to confirm the slot or say the technician is on the way."""
    langs = {p["phone"]: p.get("language", "en-IN") for p in PEOPLE}
    last = today().toordinal() + within_days
    out = []
    for rid in REQUESTS:
        r = _request(rid)
        if not r.get("visit_on") or r.get("status") in ("Closed", "Completed", "Cancelled"):
            continue
        if date.fromisoformat(r["visit_on"][:10]).toordinal() > last:
            continue
        owner = PRODUCTS[r["serial"]]
        out.append({
            "request_id": r["request_id"], "mobile": r["phone"], "customer_name": owner.get("owner"),
            "preferred_language": langs.get(r["phone"], "en-IN"), "product": r["product"],
            "visit_on": r["visit_on"], "visit_window": r.get("visit_window"), "technician": r.get("technician"),
        })
    return {"count": len(out), "visits": sorted(out, key=lambda v: v["visit_on"])}


@app.get("/requests/{request_id}", operation_id="getRequest", summary="One service request")
def get_request(request_id: str) -> dict:
    return _request(request_id)


class BookIn(BaseModel):
    serial: str
    issue: str = Field(min_length=3, max_length=1000)
    preferred_date: str | None = Field(default=None, description="YYYY-MM-DD; blank: the next free day")


@app.post("/requests", operation_id="bookVisit", summary="Book a service visit")
def book_visit(body: BookIn) -> dict:
    p = _product(body.serial)
    when = body.preferred_date or day(1)
    try:
        if date.fromisoformat(when) < today():
            raise ValueError
    except ValueError as exc:
        raise HTTPException(422, "The visit date must be today or later, as YYYY-MM-DD.") from exc
    rid = f"FRS-{90022 + len(REQUESTS)}"
    REQUESTS[rid] = {
        "request_id": rid,
        "serial": p["serial"],
        "issue": body.issue.strip(),
        "status": "Visit booked",
        "technician": None,
        "technician_phone": None,
        "visit_on": when,
        "visit_window": WINDOWS[len(REQUESTS) % len(WINDOWS)],
        "opened_at": now_iso(),
        "chargeable": not _with_warranty(p)["in_warranty"],
    }
    r = _request(rid)
    note = " It is out of warranty, so the visit is chargeable." if r["chargeable"] else ""
    return {"message": f"Visit {rid} booked for {when}, {r['visit_window']}.{note}", "request": r}


class MoveIn(BaseModel):
    new_date: str = Field(description="YYYY-MM-DD")


@app.post("/requests/{request_id}/reschedule", operation_id="rescheduleVisit", summary="Move a booked visit")
def reschedule(request_id: str, body: MoveIn) -> dict:
    r = REQUESTS.get(request_id.strip().upper())
    if r is None:
        raise HTTPException(404, f"No service request {request_id}.")
    if r["status"] in ("Completed", "Cancelled"):
        raise HTTPException(409, f"Request {r['request_id']} is {r['status']} and cannot be moved.")
    try:
        if date.fromisoformat(body.new_date) < today():
            raise ValueError
    except ValueError as exc:
        raise HTTPException(422, "The new date must be today or later, as YYYY-MM-DD.") from exc
    r.update(visit_on=body.new_date, status="Visit booked", technician=None, technician_phone=None)
    return {"message": f"Visit {r['request_id']} moved to {body.new_date}, {r['visit_window']}.", "request": _request(request_id)}
