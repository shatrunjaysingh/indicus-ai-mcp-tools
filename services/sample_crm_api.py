"""LeadDesk CRM — a sample CRM's leads, support tickets and feedback (sample_clients.py).

What a CRM offers sales, service and survey agents:

- Leads: a person's leads, the new ones to call (for a campaign), adding one,
  moving it along (stage, score, notes) and booking a callback.
- Tickets: a person's cases, the unassigned ones to triage, raising one with
  a due-by time, and updating category, priority, team, status or a note.
- Feedback: saving a rating, and the customers due a survey. A ticket set to
  Resolved joins the survey list on its own.

Test data (tag "Test data" on /crm/docs): POST /leads and POST /tickets take
any mobile (yours); PATCH a lead or ticket also changes its name, mobile or
language; POST /feedback/due adds a survey; POST /reset goes back. Saved in
state/crm.json across restarts.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from sample_clients import ALL_PEOPLE, IST, TestData, clean_phone, day, now_iso, require_key, valid_mobile

SLUG = "crm"
STAGES = ["New", "Contacted", "Qualified", "Callback scheduled", "Test drive booked", "Won", "Lost"]
PRIORITIES = {"Urgent": 4, "High": 24, "Medium": 48, "Low": 72}  # hours to due_by
TICKET_STATUSES = ["New", "Open", "Pending", "Resolved", "Closed"]
CATEGORIES = ["Cards", "Payments", "Account", "Digital banking", "Loans", "Other"]
TEAMS = ["Cards desk", "Payments ops", "Branch services", "Digital support", "Loans desk"]

app = FastAPI(title="LeadDesk CRM (sample client)", description=__doc__, version="1.0.0")
#: Every API route needs the API key; the pages a customer opens from a link do not.
KEYED = [Depends(require_key)]

#: (lead_id, person, product interest, source, stage, score, created days ago)
_LEADS = [
    ("LD-3001", 0, "Credit card", "Website", "New", 40, 0),
    ("LD-3002", 4, "Home loan", "Facebook ad", "New", 55, -1),
    ("LD-3003", 5, "Car test-drive", "Google ad", "New", 65, 0),
    ("LD-3004", 1, "Home loan", "Branch walk-in", "Contacted", 60, -6),
    ("LD-3005", 6, "Credit card", "Partner referral", "New", 35, -2),
    ("LD-3006", 3, "Car test-drive", "Website", "Qualified", 80, -4),
]

#: (case, person, title, description, category, priority, team, status, opened days ago)
_TICKETS = [
    ("CASE-40001", 0, "Card blocked after wrong PIN", "Entered the wrong PIN three times at an ATM; card now blocked.",
     "Cards", "High", "Cards desk", "Open", -1),
    ("CASE-40002", 1, "Refund not received", "Merchant refunded ₹2,340 ten days ago; not in my account yet.",
     None, None, None, "New", 0),
    ("CASE-40003", 2, "Wrong address on statement", "Statement still shows my old Adyar address.",
     None, None, None, "New", 0),
    ("CASE-40004", 3, "App login OTP not arriving", "OTP SMS never comes when logging in to the app.",
     "Digital banking", "Medium", "Digital support", "Resolved", -5),
    ("CASE-40005", 4, "Want to close my account", "I am moving abroad and want to close my savings account.",
     None, None, None, "New", -1),
]


def _at(days: int, hhmm: str = "10:00") -> str:
    return f"{day(days)}T{hhmm}:00+05:30"


def _seed() -> dict[str, dict]:
    leads, tickets, surveys, callbacks = {}, {}, {}, {}
    for lid, person, product, source, stage, score, created in _LEADS:
        p = ALL_PEOPLE[person]
        leads[lid] = {"lead_id": lid, "full_name": p["name"], "mobile": p["phone"], "email": p["email"],
                      "preferred_language": p["language"], "city": p["city"], "product_interest": product,
                      "lead_source": source, "stage": stage, "score": score, "owner": None,
                      "notes": [], "next_callback_at": None, "created_at": _at(created, "09:15")}
    callbacks["CB-6001"] = {"id": "CB-6001", "lead_id": "LD-3006", "callback_at": _at(1, "18:00"),
                            "note": "Wants a weekend test drive", "created_at": _at(-1, "12:00")}
    leads["LD-3006"]["next_callback_at"] = callbacks["CB-6001"]["callback_at"]
    for case, person, title, desc, cat, prio, team, status, opened in _TICKETS:
        p = ALL_PEOPLE[person]
        created = _at(opened, "11:00")
        tickets[case] = {"case_number": case, "title": title, "description": desc, "category": cat,
                         "priority": prio or "Medium", "team": team, "status": status,
                         "contact_name": p["name"], "mobile": p["phone"], "preferred_language": p["language"],
                         "created_at": created,
                         "due_by": (datetime.fromisoformat(created) + timedelta(hours=PRIORITIES[prio or "Medium"])).isoformat(),
                         "history": []}
    for sid, person, ref, context in [
        ("SV-8001", 3, "CASE-40004", "Support case resolved: app login OTP not arriving"),
        ("SV-8002", 0, "CARD-DELIVERY-1182", "New credit card delivered"),
        ("SV-8003", 5, "BRANCH-VISIT-CBE", "Visited the Coimbatore branch"),
    ]:
        p = ALL_PEOPLE[person]
        surveys[sid] = {"id": sid, "mobile": p["phone"], "full_name": p["name"],
                        "preferred_language": p["language"], "reference": ref, "context": context,
                        "added_at": _at(-1, "17:00")}
    return {"leads": leads, "callbacks": callbacks, "tickets": tickets, "surveys": surveys, "feedback": {}}


DB = TestData(SLUG, _seed)


def _pick(value: str | None, allowed: list[str] | dict, what: str) -> str | None:
    if value is None:
        return None
    match = next((a for a in allowed if a.lower() == value.strip().lower()), None)
    if match is None:
        raise HTTPException(422, f"{what} is one of: {', '.join(allowed)}.")
    return match


# ---- leads -------------------------------------------------------------------------

def _lead(lead_id: str) -> dict:
    lead = DB["leads"].get(lead_id.strip().upper())
    if lead is None:
        raise HTTPException(404, f"No lead {lead_id}.")
    return lead


@app.get("/leads", dependencies=KEYED, operation_id="getLeadsByMobile", tags=["Leads"], summary="A person's leads by mobile, newest first")
def get_leads(mobile: str = Query(description="The lead's mobile, any format")) -> dict:
    m = clean_phone(mobile)
    rows = [lead for lead in DB["leads"].values() if lead["mobile"] == m]
    return {"mobile": m, "leads": sorted(rows, key=lambda r: r["created_at"], reverse=True)}


@app.get("/leads/new", dependencies=KEYED, operation_id="listNewLeads", tags=["Leads"],
         summary="New leads not yet contacted, for a speed-to-lead calling campaign")
def new_leads() -> dict:
    rows = [{k: lead[k] for k in ("lead_id", "full_name", "mobile", "preferred_language", "product_interest",
                                  "lead_source", "city", "score", "created_at")}
            for lead in DB["leads"].values() if lead["stage"] == "New"]
    return {"count": len(rows), "leads": sorted(rows, key=lambda r: r["created_at"], reverse=True)}


class LeadIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120, examples=["Shiwesh Shiwam"])
    mobile: str = Field(examples=["+918826889512"])
    product_interest: str = Field(examples=["Credit card"], description="e.g. Credit card, Home loan, Car test-drive")
    lead_source: str = Field(default="Website")
    preferred_language: str = Field(default="en-IN", examples=["hi-IN"])
    city: str = ""
    email: str = ""


@app.post("/leads", dependencies=KEYED, operation_id="createLead", tags=["Leads"], status_code=201, summary="Create a lead (stage New)")
def create_lead(body: LeadIn) -> dict:
    lid = DB.next_id("leads", "LD-", 3001)
    DB["leads"][lid] = {"lead_id": lid, "full_name": body.full_name.strip(), "mobile": valid_mobile(body.mobile),
                        "email": body.email, "preferred_language": body.preferred_language, "city": body.city,
                        "product_interest": body.product_interest, "lead_source": body.lead_source,
                        "stage": "New", "score": 50, "owner": None, "notes": [], "next_callback_at": None,
                        "created_at": now_iso()}
    DB.save()
    return DB["leads"][lid]


class LeadUpdate(BaseModel):
    stage: str | None = Field(default=None, description=", ".join(STAGES))
    score: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=2000, description="Added to the lead's notes")
    owner: str | None = None
    full_name: str | None = Field(default=None, description="Test data: change the name")
    mobile: str | None = Field(default=None, description="Test data: put the lead on another mobile")
    preferred_language: str | None = Field(default=None, examples=["ta-IN"])
    product_interest: str | None = None


@app.patch("/leads/{lead_id}", dependencies=KEYED, operation_id="updateLead", tags=["Leads"],
           summary="Update a lead: stage, score, add a note (or change its contact details)")
def update_lead(lead_id: str, body: LeadUpdate) -> dict:
    lead = _lead(lead_id)
    given = body.model_dump(exclude_unset=True)
    if "stage" in given:
        given["stage"] = _pick(given["stage"], STAGES, "stage")
    if given.get("mobile"):
        given["mobile"] = valid_mobile(given["mobile"])
    note = given.pop("notes", None)
    if note:
        lead["notes"].append({"at": now_iso(), "text": note.strip()})
    lead.update({k: v for k, v in given.items() if v is not None})
    DB.save()
    return lead


class CallbackIn(BaseModel):
    callback_at: str = Field(description="ISO date-time, e.g. 2026-11-10T18:00:00+05:30")
    note: str = Field(default="", max_length=500)


@app.post("/leads/{lead_id}/callbacks", dependencies=KEYED, operation_id="scheduleLeadCallback", tags=["Leads"],
          summary="Schedule a callback for a lead at a time the person asked for")
def schedule_callback(lead_id: str, body: CallbackIn) -> dict:
    lead = _lead(lead_id)
    try:
        when = datetime.fromisoformat(body.callback_at)
    except ValueError as exc:
        raise HTTPException(422, "callback_at must be an ISO date-time, e.g. 2026-11-10T18:00:00+05:30.") from exc
    if when.tzinfo is None:
        when = when.replace(tzinfo=IST)
    if when < datetime.now(IST):
        raise HTTPException(422, "callback_at is in the past.")
    cid = DB.next_id("callbacks", "CB-", 6001)
    DB["callbacks"][cid] = {"id": cid, "lead_id": lead["lead_id"], "callback_at": when.isoformat(),
                            "note": body.note, "created_at": now_iso()}
    lead.update(next_callback_at=when.isoformat(), stage="Callback scheduled" if lead["stage"] in ("New", "Contacted") else lead["stage"])
    DB.save()
    local = when.astimezone(IST)
    return {"id": cid, "lead_id": lead["lead_id"], "callback_at": when.isoformat(),
            "message": f"Callback booked for {local:%d %b at %H:%M}."}


@app.get("/callbacks", dependencies=KEYED, operation_id="listLeadCallbacks", tags=["Leads"], summary="Lead callbacks booked, soonest first")
def list_callbacks() -> dict:
    return {"callbacks": sorted(DB["callbacks"].values(), key=lambda c: c["callback_at"])}


# ---- tickets -----------------------------------------------------------------------

def _ticket(case_number: str) -> dict:
    t = DB["tickets"].get(case_number.strip().upper())
    if t is None:
        raise HTTPException(404, f"No case {case_number}.")
    return t


@app.get("/tickets", dependencies=KEYED, operation_id="getTicketsByMobile", tags=["Tickets"], summary="A customer's support cases by mobile, newest first")
def get_tickets(mobile: str = Query(description="The customer's mobile, any format")) -> dict:
    m = clean_phone(mobile)
    rows = [t for t in DB["tickets"].values() if t["mobile"] == m]
    return {"mobile": m, "tickets": sorted(rows, key=lambda t: t["created_at"], reverse=True)}


@app.get("/tickets/unassigned", dependencies=KEYED, operation_id="listUnassignedTickets", tags=["Tickets"],
         summary="Open cases with no team yet, for triage (categorise, prioritise, route)")
def unassigned() -> dict:
    rows = [t for t in DB["tickets"].values() if not t["team"] and t["status"] not in ("Resolved", "Closed")]
    return {"count": len(rows), "tickets": sorted(rows, key=lambda t: t["created_at"])}


@app.get("/tickets/{case_number}", dependencies=KEYED, operation_id="getTicket", tags=["Tickets"], summary="One support case")
def get_ticket(case_number: str) -> dict:
    return _ticket(case_number)


class TicketIn(BaseModel):
    title: str = Field(min_length=3, max_length=200, examples=["Card not working abroad"])
    description: str = Field(min_length=3, max_length=4000)
    mobile: str = Field(examples=["+918826889512"])
    category: str | None = Field(default=None, description=", ".join(CATEGORIES))
    priority: str = Field(default="Medium", description="Urgent (4 h), High (24 h), Medium (48 h), Low (72 h)")
    contact_name: str | None = None
    preferred_language: str | None = Field(default=None, examples=["hi-IN"])


@app.post("/tickets", dependencies=KEYED, operation_id="createTicket", tags=["Tickets"], status_code=201,
          summary="Raise a support case; returns the case number and when it is due")
def create_ticket(body: TicketIn) -> dict:
    mobile = valid_mobile(body.mobile)
    prio = _pick(body.priority, PRIORITIES, "priority")
    known = next((t for t in DB["tickets"].values() if t["mobile"] == mobile), None) or \
        next((lead for lead in DB["leads"].values() if lead["mobile"] == mobile), None) or {}
    case = DB.next_id("tickets", "CASE-", 40001)
    created = datetime.now(IST)
    t = {"case_number": case, "title": body.title.strip(), "description": body.description.strip(),
         "category": _pick(body.category, CATEGORIES, "category") if body.category else None,
         "priority": prio, "team": None, "status": "New",
         "contact_name": body.contact_name or known.get("contact_name") or known.get("full_name") or "Customer",
         "mobile": mobile, "preferred_language": body.preferred_language or known.get("preferred_language") or "en-IN",
         "created_at": created.isoformat(timespec="seconds"),
         "due_by": (created + timedelta(hours=PRIORITIES[prio])).isoformat(timespec="seconds"), "history": []}
    DB["tickets"][case] = t
    DB.save()
    return {"case_number": case, "due_by": t["due_by"],
            "message": f"Case {case} is raised; we will get back by {created + timedelta(hours=PRIORITIES[prio]):%d %b %H:%M}.",
            "ticket": t}


class TicketUpdate(BaseModel):
    category: str | None = Field(default=None, description=", ".join(CATEGORIES))
    priority: str | None = Field(default=None, description=", ".join(PRIORITIES))
    team: str | None = Field(default=None, description=", ".join(TEAMS))
    status: str | None = Field(default=None, description=", ".join(TICKET_STATUSES))
    note: str | None = Field(default=None, max_length=2000, description="Added to the case history")
    contact_name: str | None = Field(default=None, description="Test data: change the name")
    mobile: str | None = Field(default=None, description="Test data: put the case on another mobile")
    preferred_language: str | None = None


@app.patch("/tickets/{case_number}", dependencies=KEYED, operation_id="updateTicket", tags=["Tickets"],
           summary="Update a case: category, priority, team, status, or add a note")
def update_ticket(case_number: str, body: TicketUpdate) -> dict:
    t = _ticket(case_number)
    given = body.model_dump(exclude_unset=True)
    if given.get("category"):
        given["category"] = _pick(given["category"], CATEGORIES, "category")
    if given.get("priority"):
        given["priority"] = _pick(given["priority"], PRIORITIES, "priority")
        t["due_by"] = (datetime.fromisoformat(t["created_at"]) + timedelta(hours=PRIORITIES[given["priority"]])).isoformat()
    if given.get("team"):
        given["team"] = _pick(given["team"], TEAMS, "team")
    if given.get("status"):
        given["status"] = _pick(given["status"], TICKET_STATUSES, "status")
    if given.get("mobile"):
        given["mobile"] = valid_mobile(given["mobile"])
    note = given.pop("note", None)
    changed = {k: v for k, v in given.items() if v is not None}
    was = t["status"]
    t.update(changed)
    if changed or note:
        t["history"].append({"at": now_iso(), "changes": changed, "note": (note or "").strip()})
    if t["status"] == "Resolved" and was != "Resolved" and not any(s["reference"] == t["case_number"] for s in DB["surveys"].values()):
        sid = DB.next_id("surveys", "SV-", 8001)
        DB["surveys"][sid] = {"id": sid, "mobile": t["mobile"], "full_name": t["contact_name"],
                              "preferred_language": t["preferred_language"], "reference": t["case_number"],
                              "context": f"Support case resolved: {t['title']}", "added_at": now_iso()}
    DB.save()
    return t


# ---- feedback ----------------------------------------------------------------------

class FeedbackIn(BaseModel):
    mobile: str = Field(examples=["+919000000333"])
    rating: int = Field(ge=1, le=5, description="1 (poor) to 5 (excellent)")
    comment: str = Field(default="", max_length=2000)
    reference: str | None = Field(default=None, description="What it is about, e.g. the case number from /feedback/due")


@app.post("/feedback", dependencies=KEYED, operation_id="saveFeedback", tags=["Feedback"], status_code=201,
          summary="Save a customer's rating (1–5) and comment; a matching survey leaves /feedback/due")
def save_feedback(body: FeedbackIn) -> dict:
    mobile = valid_mobile(body.mobile)
    fid = DB.next_id("feedback", "FB-", 9001)
    DB["feedback"][fid] = {"id": fid, "mobile": mobile, "rating": body.rating, "comment": body.comment,
                           "reference": body.reference, "received_at": now_iso(),
                           "sentiment": "positive" if body.rating >= 4 else "neutral" if body.rating == 3 else "negative"}
    DB.save()
    follow = " A team member will call you about it." if body.rating <= 2 else ""
    return {"id": fid, "message": f"Thank you for your feedback.{follow}", "feedback": DB["feedback"][fid]}


@app.get("/feedback", dependencies=KEYED, operation_id="listFeedback", tags=["Feedback"], summary="Feedback received, newest first")
def list_feedback(mobile: str | None = Query(default=None)) -> dict:
    rows = [f for f in DB["feedback"].values() if not mobile or f["mobile"] == clean_phone(mobile)]
    return {"feedback": sorted(rows, key=lambda f: f["received_at"], reverse=True)}


def _answered(s: dict) -> bool:
    return any(f["mobile"] == s["mobile"] and (not f["reference"] or f["reference"] == s["reference"])
               for f in DB["feedback"].values())


@app.get("/feedback/due", dependencies=KEYED, operation_id="listSurveysDue", tags=["Feedback"],
         summary="Customers due a feedback survey (resolved cases, deliveries, visits) who have not answered yet")
def surveys_due() -> dict:
    rows = [{k: s[k] for k in ("mobile", "full_name", "preferred_language", "reference", "context")}
            for s in DB["surveys"].values() if not _answered(s)]
    return {"count": len(rows), "customers": rows}


class SurveyIn(BaseModel):
    mobile: str = Field(examples=["+918826889512"])
    full_name: str = Field(examples=["Shiwesh Shiwam"])
    preferred_language: str = Field(default="en-IN")
    reference: str = Field(default="TEST-SURVEY", examples=["CASE-40002"])
    context: str = Field(default="Recent visit")


@app.post("/feedback/due", dependencies=KEYED, operation_id="testAddSurveyDue", tags=["Test data"], status_code=201,
          summary="Test data: add a customer (your mobile) to the survey list")
def add_survey(body: SurveyIn) -> dict:
    sid = DB.next_id("surveys", "SV-", 8001)
    DB["surveys"][sid] = {"id": sid, "mobile": valid_mobile(body.mobile), "full_name": body.full_name,
                          "preferred_language": body.preferred_language, "reference": body.reference,
                          "context": body.context, "added_at": now_iso()}
    DB.save()
    return DB["surveys"][sid]


@app.post("/reset", dependencies=KEYED, operation_id="testReset", tags=["Test data"],
          summary="Test data: back to the original leads, cases and surveys (every change is undone)")
def reset() -> dict:
    return DB.reset()

