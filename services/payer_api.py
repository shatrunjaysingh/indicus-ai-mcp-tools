"""A stand-in for a practice management system, for the demo.

This exists so the agent has somewhere real to read claims and benefits from —
it plays the part of the client's own system, which in a real deployment they
would connect with their own credentials. Nothing here is persisted by the
platform; the agent calls out, uses the answer, and the content is governed by
the workspace's retention mode like any other tool result.
"""

from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="Meridian Dental Payer API",
    version="1.0.0",
    description="Claims, remittance and eligibility for a dental practice.",
)

CLAIMS = {
    "CLM-88421": {
        "claim_id": "CLM-88421",
        "patient": {"name": "Dana Reed", "member_id": "MRD-4417732", "dob": "1986-03-11"},
        "payer": "Meridian Dental PPO",
        "date_of_service": "2026-05-14",
        "submitted_on": "2026-05-16",
        "billed_amount": 1240.00,
        "paid_amount": 0.00,
        "status": "denied",
        "procedures": [{"cdt_code": "D2740", "tooth": "19", "description": "Crown - porcelain/ceramic", "fee": 1240.00}],
        "adjustments": [{"carc": "197", "rarc": "N702", "description": "Precertification/authorization absent"}],
        "remark_text": "Prior authorization was not on file at the time of service. Retroactive review may be requested within 90 days of this remittance.",
        "eob_date": "2026-06-02",
        "age_days": 96,
    },
    "CLM-88503": {
        "claim_id": "CLM-88503",
        "patient": {"name": "Marcus Vela", "member_id": "MRD-2210984", "dob": "1974-11-02"},
        "payer": "Meridian Dental PPO",
        "date_of_service": "2026-06-03",
        "submitted_on": "2026-06-04",
        "billed_amount": 210.00,
        "paid_amount": 0.00,
        "status": "denied",
        "procedures": [{"cdt_code": "D1110", "tooth": None, "description": "Prophylaxis - adult", "fee": 210.00}],
        "adjustments": [{"carc": "119", "rarc": "N362", "description": "Benefit maximum for this time period has been reached"}],
        "remark_text": "Frequency limitation: 2 per benefit year. Prior prophylaxis paid 2026-01-08 and 2026-04-02.",
        "eob_date": "2026-06-20",
        "age_days": 78,
    },
    "CLM-88710": {
        "claim_id": "CLM-88710",
        "patient": {"name": "Priya Raman", "member_id": "MRD-9930025", "dob": "1991-07-25"},
        "payer": "Northbridge Dental",
        "date_of_service": "2026-07-09",
        "submitted_on": "2026-07-10",
        "billed_amount": 486.00,
        "paid_amount": 388.80,
        "status": "paid",
        "procedures": [{"cdt_code": "D4341", "tooth": None, "description": "Periodontal scaling and root planing, per quadrant", "fee": 486.00}],
        "adjustments": [{"carc": "45", "rarc": None, "description": "Charge exceeds fee schedule/contracted amount"}],
        "remark_text": "Paid at 80% of the contracted rate after a contractual adjustment of $97.20.",
        "eob_date": "2026-07-28",
        "age_days": 40,
    },
}

BENEFITS = {
    "MRD-4417732": {
        "member_id": "MRD-4417732",
        "patient_name": "Dana Reed",
        "plan": "Meridian Dental PPO",
        "effective_date": "2025-09-01",
        "termination_date": None,
        "coverage": {"preventive_pct": 100, "basic_pct": 80, "major_pct": 50},
        "deductible": {"individual": 50.00, "met_to_date": 50.00, "waived_for_preventive": True},
        "annual_maximum": 1500.00,
        "maximum_used": 320.00,
        "waiting_periods": {"basic_months": 0, "major_months": 12},
        "frequency_limits": {"D1110": "2 per benefit year", "D0120": "2 per benefit year", "D0274": "1 per benefit year"},
        "exclusions": ["Missing tooth clause applies to teeth extracted before 2025-09-01", "Implants not covered"],
        "notes": "Alternate benefit applies: posterior composites paid at the amalgam fee.",
    },
    "MRD-2210984": {
        "member_id": "MRD-2210984",
        "patient_name": "Marcus Vela",
        "plan": "Meridian Dental PPO",
        "effective_date": "2021-01-01",
        "termination_date": None,
        "coverage": {"preventive_pct": 100, "basic_pct": 80, "major_pct": 50},
        "deductible": {"individual": 50.00, "met_to_date": 0.00, "waived_for_preventive": True},
        "annual_maximum": 2000.00,
        "maximum_used": 1840.00,
        "waiting_periods": {"basic_months": 0, "major_months": 0},
        "frequency_limits": {"D1110": "2 per benefit year", "D0120": "2 per benefit year"},
        "exclusions": [],
        "notes": "Only $160 of the annual maximum remains.",
    },
}


@app.get("/claims/{claim_id}", operation_id="getClaim", summary="Fetch one claim with its remittance detail")
def get_claim(claim_id: str) -> dict:
    """Return a claim, its procedures, and the CARC/RARC adjustments on its EOB."""
    claim = CLAIMS.get(claim_id.upper())
    if claim is None:
        raise HTTPException(404, f"No claim {claim_id}.")
    return claim


@app.get("/claims", operation_id="listClaims", summary="List claims, optionally filtered by status and age")
def list_claims(status: str | None = None, min_age_days: int = 0) -> dict:
    """Return claims for the ageing report. `status` is one of paid, denied, pending."""
    rows = [
        c for c in CLAIMS.values()
        if (status is None or c["status"] == status) and c["age_days"] >= min_age_days
    ]
    return {"count": len(rows), "claims": rows}


@app.get("/eligibility/{member_id}", operation_id="getEligibility", summary="Fetch a member's benefit summary")
def get_eligibility(member_id: str) -> dict:
    """Return coverage percentages, deductible, annual maximum and limitations."""
    benefit = BENEFITS.get(member_id.upper())
    if benefit is None:
        raise HTTPException(404, f"No member {member_id}.")
    return benefit
