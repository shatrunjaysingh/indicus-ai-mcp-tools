"""Data for the field-visit review demo.

Stands in for a utility's own systems: the billing platform, the meter data
management system, the field inspection record and the grid event log. In a
real deployment these are the customer's systems, reached with their own
credentials.

The two visits are built so the pipeline can be demonstrated both ways, and so
that the recording alone is not enough to decide either. VISIT-4471 is
interference — the customer is at fault. VISIT-4472 is a billing estimation
fault — the customer is not. Both customers sound plausible and both are upset,
which is the point: intent read off the words alone gets VISIT-4472 wrong,
because a frightened cooperative customer and a rehearsed one are hard to tell
apart until the meter data is put beside them.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------

ACCOUNTS = {
    "ACC-40192": {
        "account_id": "ACC-40192",
        "customer_name": "R. Whitfield",
        "service_address": "14 Alder Grove, Northolt",
        "meter_id": "MTR-88213",
        "meter_type": "single-phase electronic",
        "meter_installed": "2019-04-02",
        "tariff": "Domestic Economy-7 (off-peak EV)",
        "tariff_changed": "2025-11-18",
        "customer_since": "2019-04-02",
        "occupancy": "4 residents, declared unchanged since 2023",
        "registered_load": [
            "EV charge point, 7.4kW, notified 2025-11-12",
            "Air-source heat pump, 5kW, notified 2022-08-03",
        ],
        "payment_history": "no arrears; direct debit since 2019",
        "prior_disputes": [],
    },
    "ACC-31885": {
        "account_id": "ACC-31885",
        "customer_name": "S. Nayar",
        "service_address": "8 Corn Mill Court, Reading",
        "meter_id": "MTR-77104",
        "meter_type": "single-phase smart (exchanged)",
        "meter_installed": "2026-03-31",
        "tariff": "Domestic Standard Variable",
        "tariff_changed": "2024-01-09",
        "customer_since": "2021-06-30",
        "occupancy": "2 residents, declared unchanged since 2021",
        "registered_load": [],
        "payment_history": "no arrears; direct debit since 2021",
        "prior_disputes": [
            {
                "date": "2026-05-02",
                "subject": "Disputed bill 2026-04",
                "outcome": "open",
            }
        ],
    },
}


# --------------------------------------------------------------------------
# Billing history — 14 months, most recent last
# --------------------------------------------------------------------------
#
# ACC-40192: consumption falls off a cliff in 2025-12, the month after an EV
# charge point was notified. A household that adds 7.4kW of charging and then
# uses 60% less electricity is the anomaly the whole review turns on.
#
# ACC-31885: ten estimated bills at a flat, too-low figure, then one
# "catch-up" actual read that lands the entire under-estimate in a single
# month. The spike is real arithmetic, not real consumption.

BILLING_HISTORY = {
    "ACC-40192": [
        {"period": "2025-06", "kwh": 812, "amount_gbp": 214.36, "basis": "actual"},
        {"period": "2025-07", "kwh": 771, "amount_gbp": 203.54, "basis": "actual"},
        {"period": "2025-08", "kwh": 745, "amount_gbp": 196.68, "basis": "actual"},
        {"period": "2025-09", "kwh": 803, "amount_gbp": 211.99, "basis": "actual"},
        {"period": "2025-10", "kwh": 889, "amount_gbp": 234.70, "basis": "actual"},
        {"period": "2025-11", "kwh": 951, "amount_gbp": 251.06, "basis": "actual"},
        {"period": "2025-12", "kwh": 402, "amount_gbp": 106.13, "basis": "actual",
         "flag": "step change: -58% against same month prior year"},
        {"period": "2026-01", "kwh": 388, "amount_gbp": 102.43, "basis": "actual",
         "flag": "sustained low against heat pump + EV load"},
        {"period": "2026-02", "kwh": 371, "amount_gbp": 97.94, "basis": "actual"},
        {"period": "2026-03", "kwh": 359, "amount_gbp": 94.77, "basis": "actual"},
        {"period": "2026-04", "kwh": 366, "amount_gbp": 96.62, "basis": "actual"},
        {"period": "2026-05", "kwh": 344, "amount_gbp": 90.82, "basis": "actual"},
        {"period": "2026-06", "kwh": 351, "amount_gbp": 92.66, "basis": "actual"},
        {"period": "2026-07", "kwh": 338, "amount_gbp": 89.23, "basis": "actual",
         "flag": "revenue protection referral raised"},
    ],
    "ACC-31885": [
        {"period": "2025-06", "kwh": 240, "amount_gbp": 68.40, "basis": "estimated"},
        {"period": "2025-07", "kwh": 240, "amount_gbp": 68.40, "basis": "estimated"},
        {"period": "2025-08", "kwh": 240, "amount_gbp": 68.40, "basis": "estimated"},
        {"period": "2025-09", "kwh": 240, "amount_gbp": 68.40, "basis": "estimated"},
        {"period": "2025-10", "kwh": 240, "amount_gbp": 68.40, "basis": "estimated"},
        {"period": "2025-11", "kwh": 240, "amount_gbp": 68.40, "basis": "estimated"},
        {"period": "2025-12", "kwh": 240, "amount_gbp": 68.40, "basis": "estimated"},
        {"period": "2026-01", "kwh": 240, "amount_gbp": 68.40, "basis": "estimated"},
        {"period": "2026-02", "kwh": 240, "amount_gbp": 68.40, "basis": "estimated"},
        {"period": "2026-03", "kwh": 240, "amount_gbp": 68.40, "basis": "estimated",
         "flag": "meter exchanged 2026-03-31; estimate continued"},
        {"period": "2026-04", "kwh": 1902, "amount_gbp": 542.07, "basis": "actual",
         "flag": "catch-up read: +693% against rolling estimate"},
        {"period": "2026-05", "kwh": 402, "amount_gbp": 114.57, "basis": "actual"},
        {"period": "2026-06", "kwh": 388, "amount_gbp": 110.58, "basis": "actual"},
        {"period": "2026-07", "kwh": 395, "amount_gbp": 112.58, "basis": "actual"},
    ],
}


# --------------------------------------------------------------------------
# Meter reads
# --------------------------------------------------------------------------

METER_READINGS = {
    "MTR-88213": {
        "meter_id": "MTR-88213",
        "account_id": "ACC-40192",
        "reads": [
            {"date": "2025-10-31", "register_kwh": 148_902, "source": "actual"},
            {"date": "2025-11-30", "register_kwh": 149_853, "source": "actual"},
            {"date": "2025-12-31", "register_kwh": 150_255, "source": "actual"},
            {"date": "2026-01-31", "register_kwh": 150_643, "source": "actual"},
            {"date": "2026-07-31", "register_kwh": 152_401, "source": "actual"},
        ],
        "diagnostics": [
            {"date": "2025-12-03", "event": "terminal cover removed",
             "detail": "cover-open flag raised at 23:14, cleared 23:51. No "
                       "work order open for this meter on this date."},
            {"date": "2026-02-19", "event": "cover-open flag", "detail":
                "raised 01:02, cleared 01:33. No work order."},
            {"date": "2026-06-11", "event": "reverse-running detected",
             "detail": "register decremented 0.4kWh over 6 minutes."},
        ],
        "load_profile_note": (
            "Half-hourly profile shows no overnight charging signature after "
            "2025-12-02, despite an EV charge point notified 2025-11-12 and an "
            "Economy-7 tariff applied for that purpose on 2025-11-18."
        ),
    },
    "MTR-77104": {
        "meter_id": "MTR-77104",
        "account_id": "ACC-31885",
        "reads": [
            # The anchor. Without a real read at the start of the estimated
            # window the catch-up cannot be computed at all — the baseline has
            # to be invented, and every figure downstream inherits the guess.
            {"date": "2025-05-31", "register_kwh": 41_007, "source": "actual",
             "detail": "last actual read before the estimated run"},
            {"date": "2025-09-30", "register_kwh": 41_967, "source": "estimated"},
            {"date": "2025-12-31", "register_kwh": 42_687, "source": "estimated"},
            {"date": "2026-02-28", "register_kwh": 43_167, "source": "estimated"},
            {"date": "2026-03-31", "register_kwh": 44_907, "source": "actual",
             "role": "closing", "meter": "MTR-77104-OLD",
             "detail": "final read of the removed meter"},
            {"date": "2026-03-31", "register_kwh": 0, "source": "actual",
             "role": "opening", "meter": "MTR-77104",
             "detail": "initial read of the replacement"},
            {"date": "2026-04-30", "register_kwh": 402, "source": "actual"},
            {"date": "2026-05-31", "register_kwh": 790, "source": "actual"},
            {"date": "2026-07-31", "register_kwh": 1_573, "source": "actual"},
        ],
        "diagnostics": [],
        "load_profile_note": (
            "Half-hourly profile from the replacement meter is flat and "
            "consistent at roughly 13kWh/day across the whole period, "
            "including April. There is no consumption event in April that "
            "corresponds to the amount billed."
        ),
    },
}


# --------------------------------------------------------------------------
# Field inspections — the physical check
# --------------------------------------------------------------------------

FIELD_INSPECTIONS = {
    "MTR-88213": [
        {
            "date": "2026-08-14",
            "inspector": "field-ops/7734",
            "seal_status": "BROKEN — utility seal cut and re-seated; "
                           "seal number does not match the one issued at "
                           "installation (issued S-40021, found S-39887)",
            "findings": [
                "Terminal block shows fresh tooling marks.",
                "A length of 6mm cable is bridged across the current coil "
                "inside the terminal chamber.",
                "Bridge is removable by hand and was not fitted at install.",
            ],
            "photographs": 6,
            "conclusion": "Physical interference consistent with a shunt "
                          "across the metering element.",
        }
    ],
    "MTR-77104": [
        {
            "date": "2026-08-15",
            "inspector": "field-ops/7734",
            "seal_status": "INTACT — seal S-51902, matches the record for the "
                           "replacement fitted 2026-03-31",
            "findings": [
                "No tooling marks. Terminal chamber undisturbed.",
                "Meter register agrees with the display and with the "
                "half-hourly feed.",
                "Installation paperwork for the 2026-03-31 exchange is "
                "missing the old meter's final read.",
            ],
            "photographs": 4,
            "conclusion": "No evidence of interference. The exchange "
                          "paperwork is incomplete.",
        }
    ],
}


# --------------------------------------------------------------------------
# Grid events — the innocent explanations, where they exist
# --------------------------------------------------------------------------

GRID_EVENTS = {
    "ACC-40192": [],
    "ACC-31885": [
        {
            "date": "2026-03-31",
            "type": "planned meter exchange",
            "detail": "Meter exchange programme MX-2026-11. The removed "
                      "meter's final read (44,907kWh) was not transferred to "
                      "the billing platform, so the account continued to bill "
                      "on the pre-exchange estimate until the first actual "
                      "read of the replacement.",
        },
        {
            "date": "2026-04-30",
            "type": "billing catch-up",
            "detail": "Estimation correction applied. The whole "
                      "under-estimated period was billed into 2026-04 as a "
                      "single adjustment rather than spread across the "
                      "periods it accrued in.",
        },
    ],
}


# --------------------------------------------------------------------------
# The visits
# --------------------------------------------------------------------------
#
# `script` drives both the audio generation and nothing else: the pipeline
# never reads it. What the pipeline gets is whatever the transcription returns
# from the recording, which is the point of doing the audio for real.

REP_VOICE = "Samantha"

VISITS = {
    "VISIT-4471": {
        "visit_id": "VISIT-4471",
        "account_id": "ACC-40192",
        "meter_id": "MTR-88213",
        "visited_on": "2026-08-14",
        "representative": "J. Osei (field-ops/7734)",
        "reason": "Consumption step change; revenue protection referral.",
        "recording": "visit-4471.wav",
        "duration_note": "Dual channel: representative left, customer right.",
        "customer_voice": "Fred",
        "script": [
            ("rep", "Good morning. I'm from the electricity network. "
                    "We've written twice about the readings at this address. "
                    "Do you have a few minutes?"),
            ("customer", "I suppose. I've been meaning to call you lot, "
                         "actually. Your bills have been all over the place."),
            ("rep", "That's partly why I'm here. Since December your usage "
                    "has dropped by about sixty per cent. Has anything "
                    "changed in the house?"),
            ("customer", "No. Nothing's changed. Same four of us, same "
                         "everything."),
            ("rep", "No change to the heating, or how you're running the "
                    "hot water?"),
            ("customer", "No. Well. We've been away a fair bit, on and off. "
                         "That'll be it."),
            ("rep", "Away for how much of the period, roughly? We're looking "
                    "at eight months."),
            ("customer", "I couldn't say exactly. Weekends. Bit of travel "
                         "for work. It adds up, doesn't it."),
            ("rep", "It can. I'm also seeing an electric vehicle charger "
                    "notified in November, and you moved to the off-peak "
                    "tariff for it."),
            ("customer", "We barely use that. It mostly gets charged at the "
                         "office. Free there, isn't it."),
            ("rep", "The tariff application says the vehicle is charged "
                    "overnight at home. That's the basis it was granted on."),
            ("customer", "Well, plans change. I'm not going to be penalised "
                         "for that."),
            ("rep", "Nobody's said anything about a penalty. I do need to "
                    "ask about the meter itself. Has anyone been to it, "
                    "other than us?"),
            ("customer", "There was a chap, a while back. Said he was doing "
                         "a service on it. I assumed he was one of yours."),
            ("rep", "Do you remember when, or who he was with?"),
            ("customer", "Not really. Before Christmas some time. He had a "
                         "van. I didn't stand over him."),
            ("rep", "We have no work order for this meter over that period, "
                    "and the meter logged its cover being opened on the "
                    "third of December, at eleven at night."),
            ("customer", "Then it was probably him. Look, I don't know what "
                         "you want me to say. I'm not an electrician."),
            ("rep", "I understand. I do have to tell you that I've inspected "
                    "the terminal chamber this morning, and the seal has "
                    "been cut and put back."),
            ("customer", "That's not... I didn't do that. That must have "
                         "been the man who came. Are you accusing me of "
                         "something? Because I'd want someone else here for "
                         "that."),
            ("rep", "You're entitled to that, and nothing is decided today. "
                    "I'm recording what I found and it goes to a review."),
            ("customer", "Fine. But I want it on record that I've paid every "
                         "bill you've ever sent me. Every one."),
        ],
    },
    "VISIT-4472": {
        "visit_id": "VISIT-4472",
        "account_id": "ACC-31885",
        "meter_id": "MTR-77104",
        "visited_on": "2026-08-15",
        "representative": "J. Osei (field-ops/7734)",
        "reason": ("Revenue protection screening: ten months of flat low reads "
                   "followed by a step change at meter exchange — a pattern "
                   "consistent with interference ending when the meter was "
                   "swapped."),
        "recording": "visit-4472.wav",
        "duration_note": "Dual channel: representative left, customer right.",
        "customer_voice": "Rishi",
        "script": [
            ("rep", "Good morning. I'm from the electricity network. Your "
                    "account came up on a review of meter readings and I've "
                    "been asked to check the meter and go through a few "
                    "questions. Is now convenient?"),
            ("customer", "A review? I'm the one who's been chasing you about "
                         "that April bill for three months. Nobody would "
                         "speak to me."),
            ("rep", "I can see a dispute logged. That isn't what brings me "
                    "here today, though the two may turn out to be the same "
                    "thing."),
            ("customer", "Then what brings you here?"),
            ("rep", "Your readings ran flat at the same low figure for ten "
                    "months and then stepped up sharply. That pattern gets "
                    "looked at."),
            ("customer", "Looked at for what? Say what you mean."),
            ("rep", "It can mean a meter has been interfered with, and I "
                    "have to rule that out. It can also mean a billing "
                    "fault. I don't know which yet."),
            ("customer", "You think I have been stealing electricity. In my "
                         "own home. That is what you are saying."),
            ("rep", "I'm saying I have to check. Has anything changed in the "
                    "flat — new appliance, anyone else staying?"),
            ("customer", "Nothing. Two of us, same as always. Two bedrooms. "
                         "Look around, there is nothing here that could use "
                         "what you are billing me for."),
            ("rep", "Has anyone been to the meter, other than us?"),
            ("customer", "Someone came and changed it, at the end of March. "
                         "He was from you, he had the badge, I signed "
                         "something. He left a card with the new number on "
                         "it, I kept it."),
            ("rep", "That's on our record too. I'd like to read the meter "
                    "myself and check the seal."),
            ("customer", "Check it. Check all of it. I would rather you "
                         "looked properly than sent me another letter."),
            ("rep", "Seal's intact, and the number matches what we issued in "
                    "March. Reading agrees with the display."),
            ("customer", "I also started photographing the reading every "
                         "week after that bill came, because I stopped "
                         "trusting it. They are on my phone with the dates. "
                         "Take them."),
            ("rep", "I will, thank you. Those are useful."),
            ("customer", "So am I a thief or not? You have been in my "
                         "kitchen for ten minutes."),
            ("rep", "I can't give you a finding today. What I'll be putting "
                    "in is that your bills up to March were estimates, all "
                    "at the same figure, and that it looks like the old "
                    "meter's final reading never got transferred when it was "
                    "exchanged."),
            ("customer", "So the whole thing landed in one month. That is "
                         "what I have been telling your call centre since "
                         "May."),
            ("rep", "That's what I'll be asking them to check."),
            ("customer", "I am not refusing to pay for what I have used. I "
                         "never have. I am asking not to be charged all of "
                         "it in April, and not to be treated as a suspect "
                         "for asking."),
            ("rep", "That's a reasonable position and I'll record it that "
                    "way."),
        ],
    },
}
