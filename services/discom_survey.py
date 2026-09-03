"""Submitted site surveys, with image analysis already run over them.

Use case 4. A surveyor photographs a premises; a vision service returns
detections and an OCR read of the meter number; this queue holds the results
and what they disagree with in the DISCOM's own records.

**The agent does not look at photographs.** No vision model sits behind it, and
one would not change the design: the detections are another system's claims,
each with a confidence, and the reviewing step exists precisely to decide which
claims are strong enough to act on. Treating a 0.31 detection as an observation
is the failure this whole queue is built to prevent.

What the review adds over the surveyor is the cross-check. A surveyor at the
premises cannot see that the meter number they photographed belongs to a
different consumer, that the reading is below the last billed read, or that
this address is recorded as disconnected. Those comparisons are where the
errors are.

3,000 surveys a month, which is what a division's field force submits.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

SEED = 20260904
POPULATION = 3_000

# Minutes a surveyor spends on a submission today, and what is left when the
# extraction is automatic. The residue is walking, photographing and judgement,
# none of which this removes.
MINUTES_MANUAL = 14.0
MINUTES_ASSISTED = 5.5

# Below this the meter number is reported UNREADABLE rather than guessed. A
# guessed meter number attaches the whole survey to the wrong consumer, which
# is worse than no meter number at all.
OCR_CONFIDENCE_FLOOR = 0.80

DIVISIONS = ["Pune East", "Pune West", "Pune Rural"]

# What the vision service reports, and how often. Condition findings are the
# ones with consequences.
DETECTION_CLASSES = [
    "meter", "meter_seal", "service_wire", "pole", "premises_frontage",
    "meter_glass_broken", "seal_missing", "seal_tampered", "meter_burnt",
    "temporary_clamp_on_service_cable", "meter_bypass", "unauthorised_tap",
]

# OCR digit confusions, in the order they actually occur.
OCR_CONFUSIONS = [("8", "B"), ("0", "O"), ("1", "7"), ("5", "S"), ("6", "G")]


@dataclass
class Survey:
    survey_id: str
    consumer_no: str
    division: str
    surveyor: str
    submitted: str
    images: int
    # --- what the vision service returned ---------------------------------
    ocr_meter_number: str
    ocr_confidence: float
    ocr_reading: int | None
    detections: list[dict] = field(default_factory=list)
    not_captured: list[str] = field(default_factory=list)
    # --- the record it is checked against ---------------------------------
    record_meter_number: str = ""
    record_last_read: int = 0
    record_supply_status: str = "connected"
    record_tariff_category: str = "LT-1 Domestic"
    # --- the outcome ------------------------------------------------------
    status: str = ""            # VERIFIED | PARTIAL | UNUSABLE
    meter_number_outcome: str = ""
    discrepancies: list[str] = field(default_factory=list)
    # The same finding, without the numbers, so a queue can be counted
    # by type. The prose form is unique per survey and tallies to one.
    discrepancy_types: list[str] = field(default_factory=list)
    referral: str | None = None
    needs_human: bool = False


def _corrupt(number: str, rng: random.Random) -> str | None:
    """Introduce one real OCR confusion, or none if the number has no candidate.

    Only substitutes characters that are actually confusable. The first version
    fell back to replacing the last character with whatever it had drawn, which
    manufactured substitutions like 8 to O — not a confusion any reader makes,
    and classified downstream as a genuine meter mismatch. That inflated the
    "the meter may not be the one billed" count with fixture noise, which is
    the one number in this queue nobody should have to doubt.
    """
    candidates = [(f, t) for f, t in OCR_CONFUSIONS if f in number]
    if not candidates:
        return None
    frm, to = rng.choice(candidates)
    i = number.rindex(frm)
    return number[:i] + to + number[i + 1:]


def _review(s: Survey) -> None:
    """Decide the outcome, and what disagrees with the records.

    Order matters. The meter number is resolved first because everything else
    in the survey attaches to it: a survey matched to the wrong consumer is not
    a survey with one bad field, it is evidence about somebody else.
    """
    # --- 1. the anchor ---
    if s.ocr_confidence < OCR_CONFIDENCE_FLOOR:
        s.meter_number_outcome = "UNREADABLE"
        s.needs_human = True
    elif s.ocr_meter_number == s.record_meter_number:
        s.meter_number_outcome = "MATCHES_RECORD"
    else:
        # Differing by exactly one known confusion pair is almost always the
        # reader, not a different meter. Flagged for confirmation and never
        # silently corrected — silent correction is how a genuine meter swap
        # disappears.
        pairs = [(a, b) for a, b in OCR_CONFUSIONS]
        diff = [
            (x, y) for x, y in zip(s.ocr_meter_number, s.record_meter_number,
                                   strict=False) if x != y
        ]
        likely_ocr = len(diff) == 1 and any(
            {diff[0][0], diff[0][1]} == {a, b} for a, b in pairs)
        if likely_ocr:
            s.meter_number_outcome = "LIKELY_OCR_ARTEFACT"
            s.discrepancies.append(
                f"read {s.ocr_meter_number}, record {s.record_meter_number} — "
                f"differs by one known OCR pair; confirm manually")
            s.discrepancy_types.append("meter_number_ocr_artefact")
        else:
            s.meter_number_outcome = "DIFFERS_FROM_RECORD"
            s.discrepancies.append(
                f"read {s.ocr_meter_number}, record {s.record_meter_number} — "
                f"the meter at the premises may not be the one billed")
            s.discrepancy_types.append("meter_number_differs")
        s.needs_human = True

    # --- 2. the cross-checks a surveyor cannot do at the premises ---
    if s.ocr_reading is not None and s.ocr_reading < s.record_last_read:
        s.discrepancies.append(
            f"photographed reading {s.ocr_reading:,} is below the last billed "
            f"read {s.record_last_read:,} — replaced meter, tampering, or a "
            f"billing error")
        s.discrepancy_types.append("reading_below_last_billed")
        s.needs_human = True

    live = any(d["label"] in ("temporary_clamp_on_service_cable",
                              "unauthorised_tap") and d["confidence"] >= 0.7
               for d in s.detections)
    if s.record_supply_status == "temporarily_disconnected" and live:
        s.discrepancies.append(
            "signs of live supply at a premises recorded as disconnected")
        s.discrepancy_types.append("live_supply_at_disconnected_premises")
        s.referral = "ILLEGAL_RESTORATION"
        s.needs_human = True

    if (s.record_tariff_category.startswith("LT-1")
            and any(d["label"] == "premises_frontage"
                    and d.get("detail") == "commercial" for d in s.detections)):
        s.discrepancies.append(
            "commercial frontage on a domestic tariff — unauthorised use "
            "under §126, not theft")
        s.discrepancy_types.append("commercial_frontage_domestic_tariff")
        s.referral = s.referral or "UNAUTHORISED_USE_126"
        s.needs_human = True

    # --- 3. usability ---
    has_meter = any(d["label"] == "meter" and d["confidence"] >= 0.9
                    for d in s.detections)
    if not has_meter or s.meter_number_outcome == "UNREADABLE":
        s.status = "UNUSABLE"
    elif s.not_captured or s.discrepancies:
        s.status = "PARTIAL"
    else:
        s.status = "VERIFIED"


def _generate() -> tuple[list[Survey], dict]:
    rng = random.Random(SEED)
    out: list[Survey] = []
    agg = {
        "surveys": 0,
        "by_status": {"VERIFIED": 0, "PARTIAL": 0, "UNUSABLE": 0},
        "meter_number": {"MATCHES_RECORD": 0, "LIKELY_OCR_ARTEFACT": 0,
                         "DIFFERS_FROM_RECORD": 0, "UNREADABLE": 0},
        "needs_human": 0,
        "referrals": {"ILLEGAL_RESTORATION": 0, "UNAUTHORISED_USE_126": 0},
        "discrepancy_counts": {},
        "minutes_manual": 0.0, "minutes_assisted": 0.0,
    }

    for i in range(POPULATION):
        real_meter = f"MT-{rng.randint(10_000_000, 99_999_999)}"
        # Tuned to ~4% below the floor. An engine returning one unreadable
        # meter in six would not be deployed, and a fixture that claims it
        # invites the wrong conversation about whether this works at all.
        conf = round(min(0.99, max(0.45, rng.gauss(0.93, 0.065))), 2)
        misread = conf >= OCR_CONFIDENCE_FLOOR and rng.random() < 0.07
        swapped = rng.random() < 0.012  # a genuinely different meter on site
        if swapped:
            read_meter = f"MT-{rng.randint(10_000_000, 99_999_999)}"
        elif misread:
            read_meter = _corrupt(real_meter, rng) or real_meter
        else:
            read_meter = real_meter

        last_read = rng.randint(5_000, 400_000)
        reading_below = rng.random() < 0.035
        ocr_reading = (last_read - rng.randint(500, 40_000)) if reading_below \
            else last_read + rng.randint(0, 3_000)

        detections = [
            {"label": "meter", "confidence": round(rng.uniform(0.88, 0.99), 2)},
            {"label": "service_wire", "confidence": round(rng.uniform(0.8, 0.99), 2)},
            {"label": "pole", "confidence": round(rng.uniform(0.7, 0.99), 2)},
        ]
        commercial_front = rng.random() < 0.06
        detections.append({
            "label": "premises_frontage",
            "confidence": round(rng.uniform(0.85, 0.99), 2),
            "detail": "commercial" if commercial_front else "residential"})
        if rng.random() < 0.72:
            detections.append({"label": "meter_seal",
                               "confidence": round(rng.uniform(0.6, 0.97), 2)})
        for cls, prob in [("seal_missing", 0.06), ("seal_tampered", 0.035),
                          ("meter_glass_broken", 0.03), ("meter_burnt", 0.02),
                          ("temporary_clamp_on_service_cable", 0.045),
                          ("unauthorised_tap", 0.02),
                          ("meter_bypass", 0.03)]:
            if rng.random() < prob:
                detections.append({
                    "label": cls,
                    "confidence": round(rng.uniform(0.28, 0.93), 2)})

        not_captured = []
        for what, prob in [("terminal chamber interior", 0.41),
                           ("seal underside", 0.33),
                           ("pole termination close-up", 0.27),
                           ("meter nameplate", 0.08)]:
            if rng.random() < prob:
                not_captured.append(what)

        status = rng.choices(
            ["connected", "temporarily_disconnected"], weights=[0.88, 0.12])[0]

        s = Survey(
            survey_id=f"SRV-{60000 + i}",
            consumer_no=f"MS-{800000 + rng.randint(0, 249_999)}",
            division=rng.choices(DIVISIONS, weights=[0.4, 0.32, 0.28])[0],
            surveyor=f"Lineman {rng.choice('ABCDEFGHJKLMNPQRS')}. "
                     f"{rng.choice(['Patil','Jadhav','Kulkarni','Shinde','More','Pawar'])}",
            submitted=f"2026-08-{rng.randint(1, 28):02d}",
            images=rng.randint(3, 9),
            ocr_meter_number=read_meter, ocr_confidence=conf,
            ocr_reading=ocr_reading,
            detections=detections, not_captured=not_captured,
            record_meter_number=real_meter, record_last_read=last_read,
            record_supply_status=status,
            record_tariff_category=rng.choices(
                ["LT-1 Domestic", "LT-2 Commercial"], weights=[0.74, 0.26])[0],
        )
        _review(s)
        out.append(s)

        agg["surveys"] += 1
        agg["by_status"][s.status] += 1
        agg["meter_number"][s.meter_number_outcome] += 1
        agg["needs_human"] += int(s.needs_human)
        if s.referral:
            agg["referrals"][s.referral] += 1
        for kind in s.discrepancy_types:
            agg["discrepancy_counts"][kind] = agg["discrepancy_counts"].get(kind, 0) + 1
        agg["minutes_manual"] += MINUTES_MANUAL
        agg["minutes_assisted"] += MINUTES_ASSISTED

    return out, agg


def _load() -> tuple[list[Survey], dict]:
    key = f"{SEED}-{POPULATION}-v4"
    cache = Path(__file__).resolve().parent / "_survey_cache.json"
    if cache.exists():
        try:
            blob = json.loads(cache.read_text())
            if blob.get("key") == key:
                return [Survey(**a) for a in blob["surveys"]], blob["agg"]
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    surveys, agg = _generate()
    try:
        cache.write_text(json.dumps({
            "key": key, "surveys": [asdict(a) for a in surveys], "agg": agg}))
    except OSError:
        pass
    return surveys, agg


SURVEYS, TOTALS = _load()
BY_ID: dict[str, Survey] = {s.survey_id: s for s in SURVEYS}
