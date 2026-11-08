"""Kaam Staffing — a sample applicant tracking system (sample_clients.py).

What a hiring team's system offers a screening agent:

- Applicants: a person's application by mobile, the new ones to call (for a
  campaign), and recording the screening (stage, score, the answers).
- Jobs: pay, shift, location and what each job needs — the agent answers
  applicants' questions from here.
- Interviews: free slots for a job, booking one, and tomorrow's interviews
  (for a reminder campaign).

Test data (tag "Test data" on /hiring/docs): POST /candidates adds an applicant
on any mobile (yours); PATCH a candidate also changes their name, mobile or
language; POST /reset goes back. Saved in state/hiring.json across restarts.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from sample_clients import (
    ALL_PEOPLE,
    IST,
    TestData,
    clean_phone,
    day,
    now_iso,
    require_key,
    valid_mobile,
)

SLUG = "hiring"
BUSINESS = "Kaam Staffing"
STAGES = ["New", "Screened", "Callback", "Not interested", "Interview scheduled", "Interview confirmed",
          "Reschedule", "Withdrawn", "Hired", "Rejected"]
SLOT_TIMES = ["10:00", "11:30", "15:00"]

app = FastAPI(title="Kaam Staffing applicant tracking (sample client)", description=__doc__, version="1.0.0")
KEYED = [Depends(require_key)]

_JOBS = {
    "JB-101": {"job_id": "JB-101", "title": "Delivery partner", "city": "Bengaluru",
               "salary": "₹22,000–28,000 a month plus incentives", "shift": "Flexible, 9 hours a day, 6 days a week",
               "requirements": "18 or over, own two-wheeler, valid driving licence, smartphone", "openings": 40,
               "venue": "Kaam Staffing, 3rd floor, 21 Residency Road, Bengaluru 560025"},
    "JB-102": {"job_id": "JB-102", "title": "Customer support associate", "city": "Mumbai",
               "salary": "₹18,000–21,000 a month", "shift": "Rotational, including some nights; 5 days a week",
               "requirements": "Class 12 pass, Hindi and English, comfortable on a computer", "openings": 25,
               "venue": "Kaam Staffing, 2 Bandra Kurla Complex, Mumbai 400051"},
    "JB-103": {"job_id": "JB-103", "title": "Retail store associate", "city": "Chennai",
               "salary": "₹16,000–19,000 a month", "shift": "10 am to 7 pm, weekends working, a weekday off",
               "requirements": "Class 10 pass, Tamil and some English", "openings": 12,
               "venue": "Kaam Staffing, 44 Anna Salai, Chennai 600002"},
}

#: (candidate, person, job, stage, applied days ago, interview tomorrow at)
_CANDIDATES = [
    ("CN-5001", 0, "JB-101", "New", 0, None),
    ("CN-5002", 3, "JB-102", "New", 0, None),
    ("CN-5003", 2, "JB-103", "New", -1, None),
    ("CN-5004", 6, "JB-102", "Interview scheduled", -3, "11:30"),
    ("CN-5005", 1, "JB-101", "Screened", -2, None),
]


def _at(days: int, hhmm: str) -> str:
    return f"{day(days)}T{hhmm}:00+05:30"


def _seed() -> dict[str, dict]:
    candidates, interviews = {}, {}
    for cid, person, job, stage, applied, interview in _CANDIDATES:
        p = ALL_PEOPLE[person]
        candidates[cid] = {"candidate_id": cid, "full_name": p["name"], "mobile": p["phone"],
                           "preferred_language": p["language"], "city": p["city"], "job_id": job,
                           "job_title": _JOBS[job]["title"], "job_city": _JOBS[job]["city"], "stage": stage,
                           "score": None, "notes": [], "applied_at": _at(applied, "09:40")}
        if interview:
            iid = f"IV-{7000 + len(interviews) + 1}"
            interviews[iid] = {"interview_id": iid, "candidate_id": cid, "job_id": job,
                               "start_time": _at(1, interview), "venue": _JOBS[job]["venue"], "status": "Scheduled"}
    return {"jobs": {k: dict(v) for k, v in _JOBS.items()}, "candidates": candidates, "interviews": interviews}


DB = TestData(SLUG, _seed)


def _stage(value: str) -> str:
    """Any common way of writing a stage → one of STAGES ("not_interested" → "Not interested")."""
    want = value.strip().replace("_", " ").lower()
    match = next((s for s in STAGES if s.lower() == want), None)
    if match is None:
        raise HTTPException(422, f"stage is one of: {', '.join(STAGES)}.")
    return match


def _candidate(cid: str) -> dict:
    c = DB["candidates"].get(cid.strip().upper())
    if c is None:
        raise HTTPException(404, f"No applicant {cid}.")
    return c


def _job(job_id: str) -> dict:
    j = DB["jobs"].get(job_id.strip().upper())
    if j is None:
        raise HTTPException(404, f"No job {job_id}.")
    return j


# ---- applicants ----------------------------------------------------------------------

@app.get("/candidates", dependencies=KEYED, operation_id="getCandidatesByMobile", tags=["Applicants"],
         summary="A person's applications by mobile, newest first")
def get_candidates(mobile: str = Query(description="The applicant's mobile, any format")) -> dict:
    m = clean_phone(mobile)
    rows = [c for c in DB["candidates"].values() if c["mobile"] == m]
    return {"mobile": m, "candidates": sorted(rows, key=lambda r: r["applied_at"], reverse=True)}


@app.get("/candidates/new", dependencies=KEYED, operation_id="listNewCandidates", tags=["Applicants"],
         summary="New applicants not yet screened, for a screening calling campaign")
def new_candidates() -> dict:
    rows = [{k: c[k] for k in ("candidate_id", "full_name", "mobile", "preferred_language", "job_id", "job_title",
                               "job_city", "applied_at")}
            for c in DB["candidates"].values() if c["stage"] == "New"]
    return {"count": len(rows), "candidates": sorted(rows, key=lambda r: r["applied_at"], reverse=True)}


class CandidateUpdate(BaseModel):
    stage: str | None = Field(default=None, description=", ".join(STAGES) + " (snake_case works too)")
    score: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=4000, description="Added to the applicant's notes")
    full_name: str | None = Field(default=None, description="Test data: change the name")
    mobile: str | None = Field(default=None, description="Test data: put the application on another mobile")
    preferred_language: str | None = Field(default=None, examples=["hi-IN"])


@app.patch("/candidates/{candidate_id}", dependencies=KEYED, operation_id="updateCandidate", tags=["Applicants"],
           summary="Record a screening: stage, score, answers (or change the contact details)")
def update_candidate(candidate_id: str, body: CandidateUpdate) -> dict:
    c = _candidate(candidate_id)
    given = body.model_dump(exclude_unset=True)
    if given.get("stage"):
        given["stage"] = _stage(given["stage"])
    if given.get("mobile"):
        given["mobile"] = valid_mobile(given["mobile"])
    note = given.pop("notes", None)
    if note:
        c["notes"].append({"at": now_iso(), "text": note.strip()})
    c.update({k: v for k, v in given.items() if v is not None})
    DB.save()
    return {**c, "message": f"Saved: stage {c['stage']}."}


class CandidateIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120, examples=["Shiwesh Shiwam"])
    mobile: str = Field(examples=["+918826889512"])
    job_id: str = Field(default="JB-101", description="JB-101 delivery (Bengaluru), JB-102 support (Mumbai), JB-103 retail (Chennai)")
    preferred_language: str = Field(default="en-IN", examples=["hi-IN"])
    city: str = ""


@app.post("/candidates", dependencies=KEYED, operation_id="testAddCandidate", tags=["Test data"], status_code=201,
          summary="Test data: add an applicant (your mobile), stage New")
def add_candidate(body: CandidateIn) -> dict:
    job = _job(body.job_id)
    cid = DB.next_id("candidates", "CN-", 5001)
    DB["candidates"][cid] = {"candidate_id": cid, "full_name": body.full_name.strip(), "mobile": valid_mobile(body.mobile),
                             "preferred_language": body.preferred_language, "city": body.city or job["city"],
                             "job_id": job["job_id"], "job_title": job["title"], "job_city": job["city"], "stage": "New",
                             "score": None, "notes": [], "applied_at": now_iso()}
    DB.save()
    return DB["candidates"][cid]


# ---- jobs and interviews -------------------------------------------------------------

@app.get("/jobs/{job_id}", dependencies=KEYED, operation_id="getJob", tags=["Jobs"],
         summary="One job: pay, shift, location and what it needs")
def get_job(job_id: str) -> dict:
    return _job(job_id)


def _slots(job: dict, start: str | None) -> list[dict]:
    """The next three working days' slots for a job, minus those booked."""
    taken = {i["start_time"] for i in DB["interviews"].values() if i["job_id"] == job["job_id"] and i["status"] != "Cancelled"}
    first = max(datetime.fromisoformat(start).date() if start else datetime.now(IST).date(), datetime.now(IST).date())
    out, d = [], first + timedelta(days=1)
    while len({s["start_time"][:10] for s in out}) < 3:
        if d.weekday() != 6:  # no interviews on Sundays
            for hhmm in SLOT_TIMES:
                at = f"{d.isoformat()}T{hhmm}:00+05:30"
                if at not in taken:
                    out.append({"slot_id": f"{job['job_id']}-{d.strftime('%Y%m%d')}-{hhmm.replace(':', '')}",
                                "start_time": at, "venue": job["venue"]})
        d += timedelta(days=1)
    return out


@app.get("/jobs/{job_id}/slots", dependencies=KEYED, operation_id="listInterviewSlots", tags=["Interviews"],
         summary="Free interview slots for a job over the next three working days")
def interview_slots(job_id: str, from_date: str | None = Query(default=None, alias="from", description="YYYY-MM-DD")) -> dict:
    job = _job(job_id)
    try:
        return {"job_id": job["job_id"], "slots": _slots(job, from_date)}
    except ValueError as exc:
        raise HTTPException(422, "from must be a date, YYYY-MM-DD.") from exc


class InterviewIn(BaseModel):
    candidate_id: str = Field(examples=["CN-5001"])
    slot_id: str = Field(examples=["JB-101-20261110-1000"])


@app.post("/interviews", dependencies=KEYED, operation_id="bookInterview", tags=["Interviews"], status_code=201,
          summary="Book an applicant's interview in a free slot")
def book_interview(body: InterviewIn) -> dict:
    c = _candidate(body.candidate_id)
    job = _job(c["job_id"])
    slot = next((s for s in _slots(job, None) if s["slot_id"] == body.slot_id.strip()), None)
    if slot is None:
        raise HTTPException(409, "That slot is not free any more; ask for the slots again.")
    iid = DB.next_id("interviews", "IV-", 7001)
    DB["interviews"][iid] = {"interview_id": iid, "candidate_id": c["candidate_id"], "job_id": job["job_id"],
                             "start_time": slot["start_time"], "venue": slot["venue"], "status": "Scheduled"}
    c["stage"] = "Interview scheduled"
    DB.save()
    when = slot["start_time"][:16].replace("T", " at ")
    return {"interview": DB["interviews"][iid], "message": f"Interview booked for {when} at {slot['venue']}."}


@app.get("/interviews/upcoming", dependencies=KEYED, operation_id="listUpcomingInterviews", tags=["Interviews"],
         summary="Tomorrow's interviews, for a reminder calling campaign")
def upcoming_interviews() -> dict:
    tomorrow = day(1)
    rows = []
    for i in DB["interviews"].values():
        if i["status"] != "Scheduled" or i["start_time"][:10] != tomorrow:
            continue
        c = DB["candidates"].get(i["candidate_id"]) or {}
        rows.append({**i, "full_name": c.get("full_name"), "mobile": c.get("mobile"),
                     "preferred_language": c.get("preferred_language"), "job_title": c.get("job_title")})
    return {"count": len(rows), "interviews": sorted(rows, key=lambda r: r["start_time"])}


@app.post("/reset", dependencies=KEYED, operation_id="testReset", tags=["Test data"],
          summary="Test data: back to the original applicants and interviews (every change is undone)")
def reset() -> dict:
    return DB.reset()
