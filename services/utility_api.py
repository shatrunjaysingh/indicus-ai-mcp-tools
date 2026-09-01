"""A stand-in for a utility's own stack, for the field-visit review demo.

Plays the part of the recording store, the billing platform, the meter data
management system, the field inspection record and the grid event log — the
systems a revenue-protection analyst pivots between while working one disputed
account. In a real deployment these are the customer's own systems, connected
with their own credentials; nothing here is persisted by the platform.

The data is built so the pipeline can be demonstrated both ways. VISIT-4471 is
interference and the customer is at fault; VISIT-4472 is a billing estimation
fault and the customer is not. Both customers protest, and an analyst can only
tell them apart by putting the recording beside the meter data — which is
exactly the work being automated.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcribe import transcribe  # noqa: E402
from utility_data import (  # noqa: E402
    ACCOUNTS,
    BILLING_HISTORY,
    FIELD_INSPECTIONS,
    GRID_EVENTS,
    METER_READINGS,
    VISITS,
)

RECORDINGS = Path(__file__).resolve().parent / "data" / "recordings"

app = FastAPI(
    title="Meridian Utilities Field API",
    version="1.0.0",
    description=(
        "Visit recordings and transcription, billing history, meter data, "
        "field inspections and grid events."
    ),
)

# Transcribing is seconds of CPU, and a pipeline re-reads the same recording at
# several stages. Cached per visit for the life of the process; the recordings
# are fixtures and never change under it.
_transcripts: dict[str, dict] = {}


def _visit(visit_id: str) -> dict:
    visit = VISITS.get(visit_id.upper())
    if not visit:
        raise HTTPException(404, f"No visit {visit_id}")
    return visit


def _account(account_id: str) -> dict:
    account = ACCOUNTS.get(account_id.upper())
    if not account:
        raise HTTPException(404, f"No account {account_id}")
    return account


@app.get("/visits", operation_id="listVisits",
         summary="Field visits awaiting review")
def list_visits() -> dict:
    return {
        "visits": [
            {
                "visit_id": v["visit_id"],
                "account_id": v["account_id"],
                "meter_id": v["meter_id"],
                "visited_on": v["visited_on"],
                "representative": v["representative"],
                "reason": v["reason"],
                "has_recording": (RECORDINGS / v["recording"]).exists(),
            }
            for v in VISITS.values()
        ]
    }


@app.get("/visits/{visit_id}", operation_id="getVisit",
         summary="One visit, with the reason it was raised")
def get_visit(visit_id: str) -> dict:
    visit = _visit(visit_id)
    return {
        k: v for k, v in visit.items()
        # The script is the source the audio was generated from. Serving it
        # would let a caller read the conversation without transcribing it,
        # and the point of the exercise is that the transcript is what the
        # analysis gets — recognition errors included.
        if k not in {"script", "customer_voice"}
    }


@app.post("/visits/{visit_id}/transcript", operation_id="transcribeVisitRecording",
          summary="Transcribe the visit recording, with speakers attributed")
def transcribe_visit(visit_id: str) -> dict:
    visit = _visit(visit_id)
    key = visit["visit_id"]
    if key not in _transcripts:
        path = RECORDINGS / visit["recording"]
        if not path.exists():
            raise HTTPException(
                503,
                f"Recording {visit['recording']} is not present. Generate the "
                f"fixtures with demo/generate_visit_recordings.py.")
        try:
            _transcripts[key] = transcribe(path)
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller as-is
            raise HTTPException(500, f"Transcription failed: {exc}") from exc

    result = _transcripts[key]
    return {
        "visit_id": key,
        "account_id": visit["account_id"],
        "recorded_on": visit["visited_on"],
        **result,
    }


@app.get("/visits/{visit_id}/audio", include_in_schema=False)
def get_audio(visit_id: str) -> FileResponse:
    visit = _visit(visit_id)
    path = RECORDINGS / visit["recording"]
    if not path.exists():
        raise HTTPException(404, "Recording not generated")
    return FileResponse(path, media_type="audio/wav", filename=visit["recording"])


@app.get("/accounts/{account_id}", operation_id="getAccount",
         summary="Customer account: tariff, declared load, payment history")
def get_account(account_id: str) -> dict:
    return _account(account_id)


@app.get("/accounts/{account_id}/billing", operation_id="getBillingHistory",
         summary="Billed consumption by period, and whether each was actual or estimated")
def get_billing(account_id: str) -> dict:
    account = _account(account_id)
    periods = BILLING_HISTORY.get(account["account_id"], [])
    estimated = [p for p in periods if p["basis"] == "estimated"]
    return {
        "account_id": account["account_id"],
        "periods": periods,
        # Stated rather than left to be counted off the list: a run of
        # estimates followed by one actual read is the signature of a
        # catch-up, and it is the thing most easily missed by reading down a
        # column of numbers.
        "estimated_period_count": len(estimated),
        "longest_estimated_run": _longest_estimated_run(periods),
    }


def _longest_estimated_run(periods: list[dict]) -> int:
    longest = run = 0
    for period in periods:
        run = run + 1 if period["basis"] == "estimated" else 0
        longest = max(longest, run)
    return longest


@app.get("/meters/{meter_id}/readings", operation_id="getMeterReadings",
         summary="Register reads, meter diagnostics and load profile notes")
def get_readings(meter_id: str) -> dict:
    readings = METER_READINGS.get(meter_id.upper())
    if not readings:
        raise HTTPException(404, f"No meter {meter_id}")
    return readings


@app.get("/meters/{meter_id}/inspection", operation_id="getFieldInspection",
         summary="Physical inspection of the meter: seal status and findings")
def get_inspection(meter_id: str) -> dict:
    inspections = FIELD_INSPECTIONS.get(meter_id.upper())
    if inspections is None:
        raise HTTPException(404, f"No meter {meter_id}")
    return {"meter_id": meter_id.upper(), "inspections": inspections}


@app.get("/accounts/{account_id}/grid-events", operation_id="getGridEvents",
         summary="Outages, meter exchanges and billing corrections on the account")
def get_grid_events(account_id: str) -> dict:
    account = _account(account_id)
    return {
        "account_id": account["account_id"],
        "events": GRID_EVENTS.get(account["account_id"], []),
    }
