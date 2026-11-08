"""CarePoint Clinics — a sample clinic chain's appointment system (sample_clients.py).

What a clinic's practice management system offers a booking or reminder
agent: the services offered, free slots for a service on a day at a branch,
booking, a patient's appointments, moving or cancelling one, and the
appointments coming up (for reminder calls).

Two branches, four services, slots every 30 minutes from 09:00 to 18:00 for
the next 7 days. A slot_id names its service, branch and time:
GP-BLR-20261109-1000 is a GP consultation in Bengaluru at 10:00 on 9 Nov.

Test data (tag "Test data" on /clinic/docs): book on your own mobile with
POST /appointments, change a patient's name, mobile or language with
PATCH /patients/{patient_id}, POST /reset to go back. Saved in state/clinic.json.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from sample_clients import ALL_PEOPLE, IST, TestData, clean_phone, now_iso, require_key, today, valid_mobile

SLUG = "clinic"
DAYS_AHEAD = 7

app = FastAPI(title="CarePoint Clinics appointment system (sample client)", description=__doc__, version="1.0.0")
#: Every API route needs the API key; the pages a customer opens from a link do not.
KEYED = [Depends(require_key)]

BRANCHES = {
    "BLR": {"branch_id": "BLR", "branch": "CarePoint Indiranagar, Bengaluru", "address": "100 Feet Road, Indiranagar, Bengaluru 560038", "phone": "+918040001000"},
    "CHN": {"branch_id": "CHN", "branch": "CarePoint T. Nagar, Chennai", "address": "45 Usman Road, T. Nagar, Chennai 600017", "phone": "+914440002000"},
}
SERVICES = {
    "GP": {"service_id": "GP", "service_name": "GP consultation", "duration_min": 30, "fee": 600,
           "doctors": {"BLR": "Dr. Anil Kumar", "CHN": "Dr. Kavya Raman"}},
    "DEN": {"service_id": "DEN", "service_name": "Dental check-up", "duration_min": 30, "fee": 800,
            "doctors": {"BLR": "Dr. Neha Kapoor", "CHN": "Dr. Senthil Murugan"}},
    "LAB": {"service_id": "LAB", "service_name": "Blood test (fasting)", "duration_min": 30, "fee": 450,
            "doctors": {"BLR": "Lab team", "CHN": "Lab team"}, "instructions": "Fast for 10–12 hours before; water is fine."},
    "PHY": {"service_id": "PHY", "service_name": "Physiotherapy session", "duration_min": 30, "fee": 900,
            "doctors": {"BLR": "Rahul Desai (physiotherapist)", "CHN": "Priya Natarajan (physiotherapist)"}},
}

#: (person, service, branch, days from today, HH:MM)
_APPTS = [
    (0, "GP", "BLR", 1, "10:00"),
    (2, "DEN", "CHN", 1, "11:30"),
    (4, "LAB", "BLR", 1, "09:00"),
    (5, "PHY", "CHN", 1, "16:00"),
    (1, "PHY", "BLR", 2, "17:00"),
    (3, "GP", "BLR", 3, "12:30"),
]


def _slot_id(service: str, branch: str, start: datetime) -> str:
    return f"{service}-{branch}-{start:%Y%m%d-%H%M}"


def _parse_slot(slot_id: str) -> tuple[str, str, datetime]:
    try:
        service, branch, ymd, hm = slot_id.strip().upper().split("-")
        start = datetime.strptime(ymd + hm, "%Y%m%d%H%M").replace(tzinfo=IST)
    except ValueError as exc:
        raise HTTPException(422, "slot_id looks like GP-BLR-20261109-1000; take one from /slots.") from exc
    if service not in SERVICES or branch not in BRANCHES or start.minute % 30 or not 9 <= start.hour < 18:
        raise HTTPException(404, f"No slot {slot_id}.")
    return service, branch, start


def _slot(service: str, branch: str, start: datetime) -> dict:
    s = SERVICES[service]
    return {
        "slot_id": _slot_id(service, branch, start),
        "service_id": service,
        "service_name": s["service_name"],
        "doctor_name": s["doctors"][branch],
        "branch_id": branch,
        "branch": BRANCHES[branch]["branch"],
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(minutes=s["duration_min"])).isoformat(),
        "fee": s["fee"],
    }


def _seed() -> dict[str, dict]:
    patients, appts = {}, {}
    for i, p in enumerate(ALL_PEOPLE):
        pid = f"PT-{20100 + i}"
        patients[pid] = {"patient_id": pid, "patient_name": p["name"], "mobile": p["phone"],
                         "preferred_language": p["language"], "email": p["email"]}
    for n, (person, service, branch, days, hm) in enumerate(_APPTS):
        d = today() + timedelta(days=days)
        start = datetime(d.year, d.month, d.day, int(hm[:2]), int(hm[3:]), tzinfo=IST)
        aid = f"CP-APT-{5001 + n}"
        appts[aid] = {"appointment_id": aid, "patient_id": f"PT-{20100 + person}",
                      **_slot(service, branch, start), "status": "Booked", "booked_at": now_iso()}
    return {"patients": patients, "appointments": appts}


DB = TestData(SLUG, _seed)


def _taken() -> set[str]:
    return {a["slot_id"] for a in DB["appointments"].values() if a["status"] == "Booked"}


def _view(a: dict) -> dict:
    p = DB["patients"].get(a["patient_id"], {})
    return {**a, "patient_name": p.get("patient_name"), "mobile": p.get("mobile"),
            "preferred_language": p.get("preferred_language"),
            "instructions": SERVICES.get(a["service_id"], {}).get("instructions", "")}


def _appt(appointment_id: str) -> dict:
    a = DB["appointments"].get(appointment_id.strip().upper())
    if a is None:
        raise HTTPException(404, f"No appointment {appointment_id}.")
    return a


def _free_slot(slot_id: str) -> dict:
    service, branch, start = _parse_slot(slot_id)
    if start <= datetime.now(IST):
        raise HTTPException(409, "That slot has passed; pick a later one.")
    if start.date() > today() + timedelta(days=DAYS_AHEAD):
        raise HTTPException(409, f"Slots open only {DAYS_AHEAD} days ahead.")
    if _slot_id(service, branch, start) in _taken():
        raise HTTPException(409, f"Slot {slot_id} is taken; pick another from /slots.")
    return _slot(service, branch, start)


@app.get("/services", dependencies=KEYED, operation_id="listServices", tags=["Booking"],
         summary="Services offered (GP, dental, blood test, physio), with branches, doctors and fees")
def list_services() -> dict:
    return {"services": list(SERVICES.values()), "branches": list(BRANCHES.values())}


@app.get(
    "/slots", dependencies=KEYED, operation_id="listFreeSlots", tags=["Booking"],
    summary="Free appointment slots for a service on a day, optionally at one branch",
)
def list_slots(
    service_id: str = Query(description="GP, DEN, LAB or PHY (from /services)", examples=["GP"]),
    date: str | None = Query(default=None, description="YYYY-MM-DD; blank: tomorrow"),
    branch: str | None = Query(default=None, description="BLR or CHN; blank: both"),
) -> dict:
    service = service_id.strip().upper()
    if service not in SERVICES:
        raise HTTPException(404, f"No service {service_id}; see /services.")
    try:
        d = datetime.fromisoformat(date).date() if date else today() + timedelta(days=1)
    except ValueError as exc:
        raise HTTPException(422, "date must be YYYY-MM-DD.") from exc
    branches = [branch.strip().upper()] if branch else list(BRANCHES)
    if any(b not in BRANCHES for b in branches):
        raise HTTPException(404, f"No branch {branch}; BLR or CHN.")
    if not today() <= d <= today() + timedelta(days=DAYS_AHEAD):
        return {"date": d.isoformat(), "slots": [], "message": f"Slots open from today to {DAYS_AHEAD} days ahead."}
    taken, now, out = _taken(), datetime.now(IST), []
    for b in branches:
        for minutes in range(9 * 60, 18 * 60, 30):
            start = datetime(d.year, d.month, d.day, minutes // 60, minutes % 60, tzinfo=IST)
            if start > now and _slot_id(service, b, start) not in taken:
                out.append(_slot(service, b, start))
    return {"date": d.isoformat(), "slots": out}


def _patient_for(mobile: str, name: str | None, language: str | None) -> str:
    mobile = valid_mobile(mobile)
    p = next((x for x in DB["patients"].values() if x["mobile"] == mobile), None)
    if p is None:
        pid = DB.next_id("patients", "PT-", 20100)
        p = DB["patients"][pid] = {"patient_id": pid, "patient_name": name or "Test patient", "mobile": mobile,
                                   "preferred_language": language or "en-IN", "email": ""}
    if name:
        p["patient_name"] = name
    if language:
        p["preferred_language"] = language
    return p["patient_id"]


class BookIn(BaseModel):
    slot_id: str = Field(examples=["GP-BLR-20261109-1000"])
    mobile: str = Field(examples=["+919000000999"])
    patient_name: str | None = Field(default=None, description="Needed for a new patient")
    preferred_language: str | None = Field(default=None, examples=["ta-IN"])


@app.post("/appointments", dependencies=KEYED, operation_id="bookAppointment", tags=["Booking"], status_code=201,
          summary="Book an appointment in a free slot (a new mobile becomes a new patient)")
def book(body: BookIn) -> dict:
    slot = _free_slot(body.slot_id)
    pid = _patient_for(body.mobile, body.patient_name, body.preferred_language)
    aid = DB.next_id("appointments", "CP-APT-", 5001)
    DB["appointments"][aid] = {"appointment_id": aid, "patient_id": pid, **slot, "status": "Booked", "booked_at": now_iso()}
    DB.save()
    a = _view(DB["appointments"][aid])
    when = a["start_time"][:16].replace("T", " at ")
    return {"appointment_id": aid, "message": f"Booked: {a['service_name']} with {a['doctor_name']}, {a['branch']}, {when}.",
            "appointment": a}


@app.get("/appointments", dependencies=KEYED, operation_id="getPatientAppointments", tags=["Appointments"],
         summary="A patient's appointments by mobile, soonest first")
def list_appointments(mobile: str = Query(description="The patient's mobile, any format")) -> dict:
    m = clean_phone(mobile)
    rows = [_view(a) for a in DB["appointments"].values() if DB["patients"].get(a["patient_id"], {}).get("mobile") == m]
    return {"mobile": m, "appointments": sorted(rows, key=lambda a: a["start_time"])}


@app.get(
    "/appointments/upcoming", dependencies=KEYED, operation_id="listUpcomingAppointments", tags=["Appointments"],
    summary="Booked appointments in the next N days (default 1: today and tomorrow), for reminder calls",
)
def upcoming(within_days: int = Query(default=1, ge=0, le=DAYS_AHEAD, description="0: today only; 1: today and tomorrow")) -> dict:
    now, last = datetime.now(IST), today() + timedelta(days=within_days)
    rows = []
    for a in DB["appointments"].values():
        start = datetime.fromisoformat(a["start_time"])
        if a["status"] == "Booked" and start > now and start.date() <= last:
            v = _view(a)
            rows.append({k: v[k] for k in ("appointment_id", "patient_id", "patient_name", "mobile", "preferred_language",
                                           "service_name", "doctor_name", "branch", "start_time", "instructions")})
    return {"count": len(rows), "appointments": sorted(rows, key=lambda r: r["start_time"])}


@app.get("/appointments/{appointment_id}", dependencies=KEYED, operation_id="getAppointment", tags=["Appointments"], summary="One appointment")
def get_appointment(appointment_id: str) -> dict:
    return _view(_appt(appointment_id))


class MoveIn(BaseModel):
    slot_id: str = Field(description="The new slot, from /slots", examples=["GP-BLR-20261110-1500"])


@app.patch("/appointments/{appointment_id}", dependencies=KEYED, operation_id="rescheduleAppointment", tags=["Appointments"],
           summary="Reschedule an appointment to another free slot")
def reschedule(appointment_id: str, body: MoveIn) -> dict:
    a = _appt(appointment_id)
    if a["status"] != "Booked":
        raise HTTPException(409, f"Appointment {a['appointment_id']} is {a['status']} and cannot be moved.")
    slot = _free_slot(body.slot_id)
    a.update(**slot, rescheduled_at=now_iso())
    DB.save()
    v = _view(a)
    return {"appointment_id": a["appointment_id"],
            "message": f"Moved to {v['start_time'][:16].replace('T', ' at ')}, {v['branch']}.", "appointment": v}


class CancelIn(BaseModel):
    reason: str = Field(default="", max_length=500)


@app.post("/appointments/{appointment_id}/cancel", dependencies=KEYED, operation_id="cancelAppointment", tags=["Appointments"],
          summary="Cancel an appointment (the slot is freed)")
def cancel(appointment_id: str, body: CancelIn | None = None) -> dict:
    a = _appt(appointment_id)
    if a["status"] != "Booked":
        raise HTTPException(409, f"Appointment {a['appointment_id']} is already {a['status']}.")
    a.update(status="Cancelled", cancelled_at=now_iso(), cancel_reason=(body.reason if body else ""))
    DB.save()
    return {"appointment_id": a["appointment_id"], "message": f"Appointment {a['appointment_id']} is cancelled.",
            "appointment": _view(a)}


# ---- test data ---------------------------------------------------------------------

class PatientEdit(BaseModel):
    patient_name: str | None = None
    mobile: str | None = Field(default=None, examples=["+918826889512"])
    preferred_language: str | None = Field(default=None, examples=["hi-IN"])


@app.patch("/patients/{patient_id}", dependencies=KEYED, operation_id="testEditPatient", tags=["Test data"],
           summary="Test data: change a patient's name, mobile or language (e.g. put your mobile on a seeded appointment)")
def edit_patient(patient_id: str, body: PatientEdit) -> dict:
    p = DB["patients"].get(patient_id.strip().upper())
    if p is None:
        raise HTTPException(404, f"No patient {patient_id}.")
    given = body.model_dump(exclude_unset=True)
    if given.get("mobile"):
        given["mobile"] = valid_mobile(given["mobile"])
    p.update({k: v for k, v in given.items() if v is not None})
    DB.save()
    return p


@app.post("/reset", dependencies=KEYED, operation_id="testReset", tags=["Test data"],
          summary="Test data: back to the original patients and appointments (every change is undone)")
def reset() -> dict:
    return DB.reset()

