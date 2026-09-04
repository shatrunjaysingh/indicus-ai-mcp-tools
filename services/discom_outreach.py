"""Outbound consumer calls on a screened book, and what the conversation says.

Three capabilities, in order: place a call, record it, and analyse what was
said against what the meter already says. The third is the reason the first two
exist — a recording nobody reasons over is an archive, not an input.

WHAT THE CALL DOES NOT DO
-------------------------
It never mentions the bypass indicator, and it never uses the word theft.

That is not delicacy, it is the whole design. A bypass is physical — a hooked
cable, a shunted meter — and it takes minutes to remove. Telling a consumer
that the utility suspects one, days before an inspector arrives, destroys the
evidence the case rests on. Every consumer scoring 91 or above has that
indicator set, which is why calling the top of the book is the one target that
damages the utility rather than helping it.

So the questions are about facts the consumer already knows about their own
premises: did something change, is the equipment in use, was work done. An
answer to those is useful whether or not anyone is stealing anything, and none
of them tells the consumer what the utility is looking at.

Peer deviation is never asked about at all. "You use less than similar
consumers" is not a fact about the consumer, it is a fact about a cohort, and
putting it to someone as a question is an accusation with no answer.

WHAT THE ANALYSIS IS FOR
------------------------
Not to decide guilt. A recorded phone conversation with an automated system,
without caution and not before an authorised officer, is not evidence under
§126 or §135 and every output here says so. What it *can* do is find the
explanation the utility's own records do not hold — a tariff change, a vacancy,
a seasonal shutdown — and drop a score that should never have been high; or
find that the explanation offered is contradicted by the consumer's own meter,
which is a reason to inspect rather than a reason to conclude.

THE HIDDEN GROUND TRUTH
-----------------------
Each simulated consumer is given a `_truth` — genuinely faulty meter, genuinely
vacant, genuinely evasive — which drives what they say and is then withheld
from the analysis. The analysis has to recover it from the transcript alone, so
the demo can be scored rather than admired. An analysis that is only ever shown
its own answer key is worth nothing.
"""

from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from discom_theft import _load

RECORDINGS = Path(__file__).resolve().parent / "data" / "outreach"

# The consumer voice is Indian English; the agent is deliberately a different
# accent so the two are separable by ear on the mixdown as well as by channel.
AGENT_VOICE = "Samantha"
CONSUMER_VOICE = "Rishi"

# TCCCPR 2018 permits transactional calling 09:00-21:00. Nothing here dials,
# but the window is carried on every record so a real provider adapter has the
# constraint in front of it rather than in a document nobody opens.
CALLING_WINDOW = "09:00-21:00 IST"


# --------------------------------------------------------------------------
# 1. Targeting. A rule, not a hardcoded band — the client expects this to move.
# --------------------------------------------------------------------------

def _rule_score_exactly(value: int) -> Callable[[Any], bool]:
    return lambda c: c.anomaly_risk == value


RULES: dict[str, tuple[Callable[[Any], bool], str]] = {
    "score_100": (
        _rule_score_exactly(100),
        "Risk score exactly 100. Every one of these carries the bypass "
        "indicator, so calling them warns them — see the module note.",
    ),
    "inspect_urgent": (
        lambda c: c.recommended == "INSPECT_URGENT",
        "Score 91-100. Same warning: all of them carry the bypass indicator.",
    ),
    "inspect_routine": (
        lambda c: c.recommended == "INSPECT_ROUTINE",
        "Score 70-90. Worth a visit, evidence not yet conclusive.",
    ),
    "meter_test": (
        lambda c: c.recommended == "METER_TEST",
        "Score 45-69, consistent with a defective meter. The band the call "
        "was designed for: the questions are diagnostic, and an answer can "
        "clear the account before an inspector is dispatched.",
    ),
    "monitor": (
        lambda c: c.recommended == "MONITOR",
        "Score 25-44, one or two weak signals.",
    ),
    "suppressed": (
        lambda c: c.suppressed_by is not None,
        "Accounts whose score was reduced by a documented explanation. "
        "Calling these checks the suppression was right.",
    ),
}


def select(rule: str = "meter_test", limit: int = 10,
           consumer_nos: list[str] | None = None) -> list[Any]:
    """The consumers a campaign will call, highest risk first."""
    book, _ = _load()
    if consumer_nos:
        wanted = {c.strip().upper() for c in consumer_nos}
        chosen = [c for c in book if c.consumer_no.upper() in wanted]
    else:
        if rule not in RULES:
            raise KeyError(f"unknown rule {rule!r}; have {sorted(RULES)}")
        predicate, _ = RULES[rule]
        chosen = [c for c in book if predicate(c)]
    chosen.sort(key=lambda c: (-c.anomaly_risk, c.consumer_no))
    return chosen[:limit]


# --------------------------------------------------------------------------
# 2. The interview. Questions come from the signals that actually fired.
# --------------------------------------------------------------------------

@dataclass
class Question:
    signal: str
    ask: str
    # What a useful answer would establish. Carried into the analysis so a
    # non-answer can be recognised as one rather than scored as a reply.
    seeks: str


def plan(c: Any) -> list[Question]:
    """The questions worth asking this consumer, and nothing else.

    Driven off `signal_scores`, so a consumer is never asked about a signal
    that did not fire on their account. A fixed questionnaire would ask
    everybody about tamper events, and most of them have none.
    """
    qs: list[Question] = []
    s = c.signal_scores or {}

    if "sudden_drop" in s:
        qs.append(Question(
            "sudden_drop",
            f"Our records show the electricity recorded at your premises fell "
            f"by about {c.consumption_drop_pct:.0f} percent compared with last "
            f"year. Has anything changed at the premises — the equipment you "
            f"use, the number of people there, or how often it is open?",
            "a change at the premises that would explain a lower reading"))

    if "load_inconsistency" in s:
        qs.append(Question(
            "load_inconsistency",
            f"Our records show about {c.connected_load_kw:.0f} kilowatts of "
            f"equipment connected at your premises. Is all of that still in "
            f"use, or has some of it been removed or left idle?",
            "whether the connected equipment is actually running"))

    if "repeated_tampering" in s:
        when = _event_dates(c)
        qs.append(Question(
            "repeated_tampering",
            f"Our meter recorded its cover being opened on "
            f"{' and '.join(when)}. Do you know if any work was done on the "
            f"meter around then — by our staff, an electrician, or a "
            f"contractor?",
            "an authorised or explainable reason the meter was opened"))

    if "night_day" in s:
        qs.append(Question(
            "night_day",
            f"The meter shows noticeably more electricity used at night than "
            f"during the day. Is there equipment that runs overnight at your "
            f"premises?",
            "a legitimate overnight load"))

    if "excess_load" in s:
        qs.append(Question(
            "excess_load",
            f"Your sanctioned load is {c.sanctioned_load_kw:.0f} kilowatts and "
            f"we are seeing around {c.connected_load_kw:.0f} connected. Have "
            f"you added any equipment since the connection was sanctioned?",
            "added equipment, which is a load regularisation matter"))

    # Deliberately absent: peer_deviation and bypass_indicator. See module note.
    return qs


def _event_dates(c: Any) -> list[str]:
    rng = random.Random(f"dates-{c.consumer_no}")
    base = date(2026, 8, 20)
    out = []
    for _ in range(min(c.tamper_events_12m, 2)):
        d = base - timedelta(days=rng.randint(20, 300))
        out.append(d.strftime("%d %B %Y"))
    return out or ["a recent date"]


# --------------------------------------------------------------------------
# 3. The consumer side. A persona with a truth the analysis does not get.
# --------------------------------------------------------------------------

TRUTHS = {
    "GENUINE_METER_FAULT": "The meter is defective. The consumer is honest and puzzled.",
    "UNRECORDED_EXPLANATION": "There is a real explanation the utility never wrote down.",
    "GENUINELY_VACANT": "The premises really is empty or barely used.",
    "ADDED_LOAD_UNDECLARED": "They added equipment without regularising it. A §126 load matter, not theft.",
    "EVASIVE": "The account has something to hide. Answers deflect and do not settle.",
    "COOPERATIVE_UNAWARE": "Willing to help and genuinely does not know why consumption moved.",
    "REFUSES": "Declines to be recorded, or hangs up.",
}

# Weighted so the band being called shapes who answers. A meter-test account is
# far more likely to have a real fault than an urgent one, which is the point
# of calling that band and not the top of the book.
_TRUTH_WEIGHTS = {
    "METER_TEST": [("GENUINE_METER_FAULT", 30), ("UNRECORDED_EXPLANATION", 22),
                   ("COOPERATIVE_UNAWARE", 20), ("GENUINELY_VACANT", 10),
                   ("ADDED_LOAD_UNDECLARED", 8), ("EVASIVE", 6), ("REFUSES", 4)],
    "INSPECT_URGENT": [("EVASIVE", 40), ("REFUSES", 20), ("ADDED_LOAD_UNDECLARED", 14),
                       ("COOPERATIVE_UNAWARE", 12), ("UNRECORDED_EXPLANATION", 8),
                       ("GENUINE_METER_FAULT", 4), ("GENUINELY_VACANT", 2)],
    "INSPECT_ROUTINE": [("EVASIVE", 28), ("COOPERATIVE_UNAWARE", 20),
                        ("ADDED_LOAD_UNDECLARED", 18), ("UNRECORDED_EXPLANATION", 14),
                        ("GENUINE_METER_FAULT", 10), ("REFUSES", 6), ("GENUINELY_VACANT", 4)],
    "MONITOR": [("COOPERATIVE_UNAWARE", 34), ("UNRECORDED_EXPLANATION", 24),
                ("GENUINE_METER_FAULT", 18), ("GENUINELY_VACANT", 12),
                ("ADDED_LOAD_UNDECLARED", 6), ("EVASIVE", 4), ("REFUSES", 2)],
}
_TRUTH_WEIGHTS["NO_ACTION"] = _TRUTH_WEIGHTS["MONITOR"]


def _truth_for(c: Any, rng: random.Random) -> str:
    table = _TRUTH_WEIGHTS.get(c.recommended, _TRUTH_WEIGHTS["MONITOR"])
    return rng.choices([t for t, _ in table], weights=[w for _, w in table])[0]


# Answers per truth per signal. Written to be *analysable*: some corroborate the
# meter, some contradict it, and the contradiction has to be findable from the
# words plus the data, never from the label.
_ANSWERS: dict[str, dict[str, list[str]]] = {
    "GENUINE_METER_FAULT": {
        "sudden_drop": [
            "Nothing has changed at all. Same family, same appliances, same routine. "
            "But I will tell you something — the meter display has been blank for "
            "weeks now. Sometimes it comes back, mostly it is dead.",
            "No, nothing changed. If anything we are using more, we bought an air "
            "conditioner in April. The meter reading is what looks wrong to me."],
        "load_inconsistency": [
            "Everything is connected and everything runs. I have not removed a "
            "single thing. That is why I do not understand your reading."],
        "repeated_tampering": [
            "Nobody has touched that meter. It is inside a locked box on my wall. "
            "Your own man came in June and said the seal looked fine to him."],
        "night_day": [
            "We are a normal household. Everything is off by eleven. I cannot "
            "explain what your meter is showing at night."],
        "excess_load": [
            "We added the air conditioner, yes. I did not know that needed telling."],
    },
    "UNRECORDED_EXPLANATION": {
        "sudden_drop": [
            "Yes — we surrendered part of the load last year. I applied at the "
            "Hadapsar office, I have the acknowledgement paper. Thirty kilowatts "
            "down to fifteen. It should be on your file.",
            "We changed to the domestic tariff in March when the shop closed. I "
            "have the letter. That is why the usage looks different."],
        "load_inconsistency": [
            "Half of that equipment went when we surrendered the load. The old "
            "machines were sold. I gave the list to your office."],
        "repeated_tampering": [
            "That would be your own department. The meter was replaced under a "
            "work order — I signed for it, the man gave me a copy."],
        "night_day": [
            "The water pump runs at night on the timer, it always has. That was "
            "declared when we took the connection."],
        "excess_load": [
            "We reduced, we did not add. The sanction letter should show fifteen."],
    },
    "GENUINELY_VACANT": {
        "sudden_drop": [
            "The house is empty. My father passed away in January and nobody "
            "lives there now. I go once a month to check on it.",
            "We shut the unit down. It has been locked since February, there is "
            "nothing running."],
        "load_inconsistency": [
            "None of it is running. The main switch is off. There is nobody there."],
        "repeated_tampering": [
            "I would not know. I am not there. Nobody is there."],
        "night_day": [
            "There is nothing on at night. There is nothing on at any time. I "
            "told you, the place is locked."],
        "excess_load": [
            "Nothing has been added. Nothing is being used."],
    },
    "ADDED_LOAD_UNDECLARED": {
        "sudden_drop": [
            "Business is slow, that is all. Fewer orders, less running time."],
        "load_inconsistency": [
            "We did put in two more machines last year, and a bigger compressor. "
            "I know I should have applied for the load increase. I kept putting "
            "it off. What is the process to fix it?"],
        "repeated_tampering": [
            "The electrician opened it when we wired the new machines in. He said "
            "he had to. I did not know that was a problem."],
        "night_day": [
            "The compressor and the cold room run through the night, yes. That is "
            "the nature of the work."],
        "excess_load": [
            "Yes. Two machines and a compressor. I want to regularise it, tell me "
            "what to do."],
    },
    "EVASIVE": {
        "sudden_drop": [
            "Why are you asking me this? I pay my bill every month. Check your "
            "records.",
            "Nothing changed. Nothing. Who is asking, what is this about?",
            "How would I know what your meter says? That is your equipment, not "
            "mine."],
        "load_inconsistency": [
            "It is a house. Normal things. Why do you need a list?",
            "Some is used, some is not. What difference does it make."],
        "repeated_tampering": [
            "No idea. Maybe your own people. Maybe the wind.",
            "Cover open? Nobody opened anything. Your machine is wrong.",
            "There is construction all around here. Anyone could have touched it."],
        "night_day": [
            "At night we sleep. I do not know what you are talking about.",
            "Maybe the neighbours. Their line runs past my wall."],
        "excess_load": [
            "Same as always. Nothing added. You have the papers, you tell me."],
    },
    "COOPERATIVE_UNAWARE": {
        "sudden_drop": [
            "Honestly I have no idea. Nothing has changed that I can think of. "
            "Same people, same appliances. Should I be worried?",
            "That is strange. We have not changed anything. Can somebody come and "
            "look at it?"],
        "load_inconsistency": [
            "I think everything is in use. The fridge, fans, the pump, the "
            "television. I am not sure how to add it up."],
        "repeated_tampering": [
            "Not that I know of. Nobody told me anything. Is that serious?"],
        "night_day": [
            "The fridge runs, and the water pump goes on around five in the "
            "morning. Would that be it?"],
        "excess_load": [
            "We may have. I would have to check what was there originally."],
    },
}

_FOLLOW_UP = {
    "EVASIVE": [
        "I have answered you. Is there anything else?",
        "I do not want to discuss this on the phone. Send someone if you want.",
        "You people call and call. I have nothing more to say."],
}


def answer_for(truth: str, signal: str, rng: random.Random) -> tuple[str, bool]:
    """One consumer reply, and whether it actually addressed the question.

    Split out of `converse` so a turn-based call can ask one question at a time
    and get the next reply, rather than rendering a whole conversation up
    front. A real trunk works that way and so must the loopback that stands in
    for it, or the loopback stops proving anything about the real path.
    """
    bank = _ANSWERS.get(truth, {}).get(signal)
    if not bank:
        return (rng.choice(["I could not say.", "I do not know about that.",
                            "You would have to check that at your end."]), False)
    return (rng.choice(bank), True)


def opening_line(c: Any) -> str:
    return (
        f"Good morning. This is an automated call from the electricity "
        f"distribution company regarding consumer number "
        f"{_spell(c.consumer_no)}, at your registered premises in "
        f"{c.subdivision}. You are speaking to an automated system, not a "
        f"person. This call is being recorded. It is about your meter reading, "
        f"and it will take about two minutes. May I continue?")


CLOSING_LINE = (
    "Thank you. Nothing has been decided about your account on this call, "
    "and nothing you have said is treated as an admission of anything. What "
    "you have told me will be checked against our records. If a meter test "
    "or a site visit is needed you will be given notice in writing, and you "
    "will have the right to be heard before any assessment is raised. If "
    "you have documents, please bring them to your subdivision office. "
    "Goodbye.")

REFUSAL_CLOSE = (
    "Understood. I am ending the call and no recording will be kept "
    "beyond this point. Your account will be handled through the normal "
    "written process, and nothing you have said will count against you. "
    "Thank you for your time.")

# What a consumer declining sounds like, however they phrase it. Checked
# against the *recognised* answer to the opening, so a refusal is honoured even
# though nobody typed it into a menu.
REFUSAL_MARKERS = ("do not consent", "don't consent", "not talking to a machine",
                   "do not call", "don't call", "not interested", "no thank",
                   "send me a letter", "remove my number")


def refused_consent(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in REFUSAL_MARKERS)


def converse(c: Any, questions: list[Question], rng: random.Random,
             truth: str) -> tuple[list[tuple[str, str]], dict]:
    """The full call, as [(speaker, text)], plus what happened procedurally.

    The opening is not decoration. Recording disclosure, automated-system
    disclosure and a consent checkpoint are what make the recording usable at
    all, and a consumer who declines is a legitimate outcome rather than a
    failed call.
    """
    script: list[tuple[str, str]] = []
    meta = {"consent": "granted", "questions_asked": 0,
            "questions_answered": 0, "ended_early": False}

    script.append(("agent",
        f"Good morning. This is an automated call from the electricity "
        f"distribution company regarding consumer number "
        f"{_spell(c.consumer_no)}, at your registered premises in "
        f"{c.subdivision}. You are speaking to an automated system, not a "
        f"person. This call is being recorded. It is about your meter reading, "
        f"and it will take about two minutes. May I continue?"))

    if truth == "REFUSES":
        script.append(("consumer",
            rng.choice([
                "No. I am not talking to a machine about my meter. Send me a "
                "letter.",
                "I do not consent to a recording. Do not call this number again."])))
        script.append(("agent",
            "Understood. I am ending the call and no recording will be kept "
            "beyond this point. Your account will be handled through the normal "
            "written process, and nothing you have said will count against you. "
            "Thank you for your time."))
        meta.update(consent="refused", ended_early=True)
        return script, meta

    script.append(("consumer", rng.choice([
        "Yes, go ahead.", "Alright. What is it about?", "Yes, fine. Tell me."])))

    for q in questions:
        script.append(("agent", q.ask))
        meta["questions_asked"] += 1
        bank = _ANSWERS.get(truth, {}).get(q.signal)
        if not bank:
            # No scripted answer for this pairing: the consumer says something
            # that does not settle the question. Recorded as unanswered rather
            # than quietly skipped, because a question the call failed to land
            # is exactly what a review needs to see.
            script.append(("consumer", rng.choice([
                "I could not say.", "I do not know about that.",
                "You would have to check that at your end."])))
            continue
        script.append(("consumer", rng.choice(bank)))
        meta["questions_answered"] += 1

        if truth == "EVASIVE" and rng.random() < 0.45:
            script.append(("agent",
                "I understand. Just so I record it correctly — was there any "
                "change at the premises in that period, yes or no?"))
            script.append(("consumer", rng.choice(_FOLLOW_UP["EVASIVE"])))

    script.append(("agent",
        "Thank you. Nothing has been decided about your account on this call, "
        "and nothing you have said is treated as an admission of anything. What "
        "you have told me will be checked against our records. If a meter test "
        "or a site visit is needed you will be given notice in writing, and you "
        "will have the right to be heard before any assessment is raised. If "
        "you have documents, please bring them to your subdivision office. "
        "Goodbye."))
    script.append(("consumer", rng.choice([
        "Alright. Thank you.", "Okay. Goodbye.", "Fine. Thank you."])))
    return script, meta


def _spell(consumer_no: str) -> str:
    """Read a consumer number the way a phone system has to.

    'MS-801023' spoken as written comes out of TTS as a word, and comes back
    out of the transcriber as one too. Spacing the digits keeps the number
    recoverable from the transcript, which matters because the transcript is
    what the review reads.
    """
    head, _, tail = consumer_no.partition("-")
    return f"{' '.join(head)} {' '.join(tail)}"


# --------------------------------------------------------------------------
# 4. The analysis. Claims out of the transcript, checked against the meter.
# --------------------------------------------------------------------------
#
# The split of work here is deliberate. This function does the *arithmetic* —
# which claim contradicts which reading, by how much — and leaves the judgement
# to the agent reading the result. Ask a language model to decide whether a
# night/day ratio of 2.6 is consistent with an empty house and it will produce
# a confident answer either way. Give it "claimed vacant; meter shows 2.6x more
# consumption at night than day; an unoccupied premises does not do that" and
# the judgement is the easy part and the number is not invented.

CLAIM_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    # Needles are phrases, not words. "removed" alone matched "I have not
    # removed a single thing" and recorded a load surrender the consumer had
    # just denied; "locked" alone matched "a locked box on my wall" and
    # recorded the premises as vacant. A keyword that can appear in the denial
    # of the claim is not a detector for it.
    ("premises_vacant", ("house is empty", "nobody lives", "nobody is there",
                         "shut the unit down", "locked since",
                         "place is locked", "main switch is off",
                         "nothing is running", "nothing running")),
    # A described symptom, not a complaint about the utility. "The display has
    # been blank for weeks" is a fact the consumer observed at their own
    # premises; "your machine is wrong" is an assertion anybody makes when
    # challenged, and the two were the same claim until an evasive consumer
    # deflecting five times in a row was routed to a meter test on the
    # strength of it.
    ("meter_defective", ("display has been blank", "display is blank",
                         "meter is dead", "mostly it is dead")),
    ("blames_meter", ("reading is what looks wrong", "your machine is wrong",
                      "that is your equipment")),
    ("load_surrendered", ("surrendered", "load surrender",
                          "machines were sold", "we reduced")),
    ("tariff_changed", ("domestic tariff", "shop closed")),
    ("authorised_work", ("work order", "your own department",
                         "replaced under")),
    ("equipment_added", ("more machines", "bigger compressor",
                         "air conditioner", "two machines")),
    ("business_slow", ("business is slow", "fewer orders", "less running")),
    ("overnight_load", ("water pump", "cold room", "compressor",
                        "on the timer", "runs through the night",
                        "fridge runs")),
    ("no_change", ("nothing has changed", "nothing changed", "same family",
                   "same appliances", "same as always")),
    ("denies_knowledge", ("no idea", "would not know", "i do not know",
                          "could not say", "not sure", "how would i know")),
    ("blames_others", ("neighbours", "the wind", "construction",
                       "anyone could")),
    ("deflects", ("why are you asking", "check your records", "who is asking",
                  "what is this about", "nothing more to say",
                  "call and call", "what difference does it make",
                  "send someone if you want")),
    ("offers_documents", ("acknowledgement", "i have the letter", "i signed",
                          "gave the list", "sanction letter",
                          "have the paper", "gave me a copy")),
    ("seeks_regularisation", ("what is the process", "want to regularise",
                              "tell me what to do", "should have applied")),
    ("vulnerability", ("passed away", "i am alone", "hospital", "medical")),
]


@dataclass
class Corroboration:
    claim: str
    verdict: str          # CORROBORATED | CONTRADICTED | UNTESTABLE
    against: str          # the reading it was checked against
    reasoning: str


# Words that flip a clause. Scoped to the clause the needle sits in, not the
# whole utterance — "Nobody has touched that meter. It is inside a locked box"
# must not have the first sentence suppress a match in the second.
_NEGATIONS = ("not ", "n't", "nobody ", "no one ", "never ", "nothing ")


def _claims(text: str) -> list[str]:
    """A first pass over what the consumer said.

    Keyword extraction, and honest about being that: it finds candidates and
    misses phrasings nobody wrote down. The agent reading the transcript is
    better at "did they actually claim this", which is why the transcript is
    returned in full and `checkClaimAgainstMeter` lets the agent test a claim
    it identified itself. This exists so a bulk export has something to sort
    on, not because it is the better reader.
    """
    clauses = [c.strip() for c in re.split(r"[.,;?!]", text.lower()) if c.strip()]
    found: list[str] = []
    for name, needles in CLAIM_PATTERNS:
        for clause in clauses:
            hit = next((n for n in needles if n in clause), None)
            if hit is None:
                continue
            before = clause[:clause.index(hit)]
            if any(neg in before for neg in _NEGATIONS):
                continue  # the clause denies the thing it mentions
            found.append(name)
            break
    return found


def corroborate(c: Any, claims: list[str]) -> list[Corroboration]:
    """Check each claim against this consumer's own meter data.

    A claim the meter can neither support nor refute is UNTESTABLE, and saying
    so is the honest output — collapsing it into "unsupported" would let an
    unfalsifiable statement read as a mark against the consumer.
    """
    out: list[Corroboration] = []

    if "premises_vacant" in claims:
        if c.night_day_ratio >= 2.4:
            out.append(Corroboration(
                "premises_vacant", "CONTRADICTED",
                f"night/day ratio {c.night_day_ratio:.1f}",
                "An unoccupied premises does not draw more power at night than "
                "by day. Something is running there on a schedule."))
        elif c.load_factor_ratio > 0.30:
            out.append(Corroboration(
                "premises_vacant", "CONTRADICTED",
                f"load factor {c.load_factor_ratio:.2f}",
                f"Consumption is still {c.load_factor_ratio:.0%} of connected "
                f"load. An empty premises with the main switch off does not "
                f"draw that."))
        elif c.consumption_drop_pct >= 55:
            out.append(Corroboration(
                "premises_vacant", "CORROBORATED",
                f"consumption down {c.consumption_drop_pct:.0f}%",
                "A drop of this size is what vacating a premises looks like."))
        else:
            out.append(Corroboration(
                "premises_vacant", "UNTESTABLE",
                "no reading distinguishes it",
                "Consumption has not fallen far enough to confirm a vacancy, "
                "nor is anything inconsistent with one."))

    if "meter_defective" in claims:
        if c.tamper_events_12m >= 2:
            out.append(Corroboration(
                "meter_defective", "UNTESTABLE",
                f"{c.tamper_events_12m} tamper events, no work order",
                "A defective meter and an interfered-with meter produce similar "
                "readings from the office. Only a meter test separates them, "
                "and it should be done before anything is alleged."))
        else:
            out.append(Corroboration(
                "meter_defective", "CORROBORATED",
                f"consumption down {c.consumption_drop_pct:.0f}%, "
                f"load factor {c.load_factor_ratio:.2f}",
                "The pattern is consistent with under-recording. A meter test "
                "is the correct next step, not an inspection."))

    if "load_surrendered" in claims or "tariff_changed" in claims:
        claim = "load_surrendered" if "load_surrendered" in claims else "tariff_changed"
        if c.connected_load_kw > c.sanctioned_load_kw * 1.25:
            out.append(Corroboration(
                claim, "CONTRADICTED",
                f"{c.connected_load_kw:.0f} kW connected against "
                f"{c.sanctioned_load_kw:.0f} kW sanctioned",
                "Connected load is above sanctioned, which is the opposite of "
                "a surrender. Either the surrender was never executed or the "
                "equipment is still in place."))
        else:
            out.append(Corroboration(
                claim, "CORROBORATED",
                f"connected {c.connected_load_kw:.0f} kW within sanctioned "
                f"{c.sanctioned_load_kw:.0f} kW",
                "Consistent with a reduction. Verifiable against the "
                "application record, which is where this should be closed."))

    if "authorised_work" in claims:
        out.append(Corroboration(
            "authorised_work", "UNTESTABLE",
            f"{c.tamper_events_12m} events logged with no linked work order",
            "The work order register decides this, not the meter. If a work "
            "order exists the events are explained and the score should fall; "
            "if it does not, the consumer has named a check that failed."))

    if "equipment_added" in claims or "seeks_regularisation" in claims:
        if c.connected_load_kw > c.sanctioned_load_kw * 1.25:
            out.append(Corroboration(
                "equipment_added", "CORROBORATED",
                f"{c.connected_load_kw:.0f} kW against "
                f"{c.sanctioned_load_kw:.0f} kW sanctioned",
                "This is unauthorised additional load — a §126 regularisation "
                "matter, not §135 theft. Route to load regularisation with the "
                "arrears calculated from the declared date, not to enforcement."))
        else:
            out.append(Corroboration(
                "equipment_added", "UNTESTABLE",
                "connected load within sanction",
                "Added equipment that still sits inside the sanctioned load "
                "needs no regularisation."))

    if "overnight_load" in claims:
        if c.night_day_ratio >= 2.4:
            out.append(Corroboration(
                "overnight_load", "CORROBORATED",
                f"night/day ratio {c.night_day_ratio:.1f}",
                "A declared overnight load explains the night/day signal. It "
                "should stop counting against this consumer."))
        else:
            out.append(Corroboration(
                "overnight_load", "UNTESTABLE",
                f"night/day ratio {c.night_day_ratio:.1f}",
                "No night/day anomaly on this account for the claim to explain."))

    if "no_change" in claims and c.consumption_drop_pct >= 35:
        out.append(Corroboration(
            "no_change", "CONTRADICTED",
            f"consumption down {c.consumption_drop_pct:.0f}%",
            "Nothing changed at the premises, but the recorded consumption "
            "moved substantially. Either the meter is wrong or the account is. "
            "Both are worth resolving; only one is an offence."))

    if "business_slow" in claims and c.night_day_ratio >= 2.4:
        out.append(Corroboration(
            "business_slow", "CONTRADICTED",
            f"night/day ratio {c.night_day_ratio:.1f}",
            "Reduced trading does not produce more consumption at night than "
            "by day. The premises is running something outside trading hours."))

    return out


EVASION_MARKERS = {"deflects", "blames_others", "denies_knowledge"}
COOPERATION_MARKERS = {"offers_documents", "seeks_regularisation",
                       "load_surrendered", "authorised_work", "overnight_load"}


def analyse(c: Any, transcript: dict, meta: dict) -> dict:
    """What the conversation established, and what should happen next."""
    consumer_text = " ".join(
        t["text"] for t in transcript["turns"] if t["speaker"] == "customer")
    claims = _claims(consumer_text)
    checks = corroborate(c, claims)

    contradicted = [x for x in checks if x.verdict == "CONTRADICTED"]
    corroborated = [x for x in checks if x.verdict == "CORROBORATED"]
    evasion = sorted(EVASION_MARKERS & set(claims))
    cooperation = sorted(COOPERATION_MARKERS & set(claims))

    answered = meta["questions_answered"]
    asked = max(meta["questions_asked"], 1)
    responsiveness = round(answered / asked, 2)

    disposition, why, changes = _disposition(
        c, meta, contradicted, corroborated, evasion, cooperation, claims)

    return {
        "consumer_no": c.consumer_no,
        "risk_score": c.anomaly_risk,
        "recommended_before_call": c.recommended,
        "consent": meta["consent"],
        "questions_asked": meta["questions_asked"],
        "questions_answered": answered,
        "responsiveness": responsiveness,
        "claims_made": claims,
        "corroboration": [asdict(x) for x in checks],
        "contradicted_count": len(contradicted),
        "corroborated_count": len(corroborated),
        "evasion_markers": evasion,
        "cooperation_markers": cooperation,
        "vulnerability_flagged": "vulnerability" in claims,
        "disposition": disposition,
        "why": why,
        "what_would_change_it": changes,
        # Stated on every single record, because this is the sentence that
        # keeps a phone call from being treated as a confession.
        "evidential_status":
            "Not evidence. An automated call, without caution and not before an "
            "authorised officer, cannot support a §135 prosecution or a §126 "
            "assessment. It directs where to look; the finding must come from "
            "a meter test or an inspection conducted under the Act.",
    }


def _disposition(c, meta, contradicted, corroborated, evasion, cooperation,
                 claims) -> tuple[str, str, str]:
    """What should happen to this account now.

    Order matters here, and getting it wrong is not cosmetic. The first version
    tested `contradicted` before everything else, which sent an inspector to a
    consumer who had just reported a dead meter display — on a METER_TEST
    account, whose whole definition is "test before accusing". A generic
    contradiction outranking a specific fault report is the exact failure this
    band exists to prevent.
    """
    if meta["consent"] == "refused":
        return ("PROCEED_ON_DATA_ALONE",
                "The consumer declined to be recorded. That is their right and "
                "carries no inference — the account stands exactly where the "
                "screening left it.",
                "Nothing. Refusal must never move the score in either "
                "direction, or the call becomes a penalty for declining it.")

    if "vulnerability" in claims:
        return ("ROUTE_TO_HUMAN",
                "The consumer disclosed a bereavement or a medical "
                "circumstance. An automated follow-up is the wrong instrument "
                "regardless of what the meter says.",
                "A human officer's assessment. The screening signals remain "
                "open and are not cleared by this route.")

    # "Nothing changed at the premises" against a fallen reading is a weak
    # contradiction: under-recording produces it just as reliably as a
    # misdescribed account. Separating it from the hard ones is what keeps a
    # denial from being treated as a lie.
    hard = [x for x in contradicted if x.claim != "no_change"]
    weak_only = bool(contradicted) and not hard

    disputes_meter = "meter_defective" in claims or "blames_meter" in claims

    if "meter_defective" in claims and not hard and not evasion:
        return ("METER_TEST_PRIORITY",
                "The consumer reports a blank or dead display, and the "
                "consumption pattern is consistent with under-recording. The "
                "only thing their meter contradicts is 'nothing changed' — "
                "which is what a defective meter produces too, so it does not "
                "separate the two. Test the meter before anything is alleged; "
                "an inspection here would be an accusation made before the "
                "cheaper check that could have settled it.",
                "A meter that tests correct. Then the consumption question is "
                "live again and inspection is back on the table.")

    if hard:
        first = hard[0]
        return ("PROCEED_TO_INSPECTION",
                f"The explanation offered is contradicted by the consumer's own "
                f"meter: {first.reasoning}",
                "A documented explanation that survives the reading — a work "
                "order, a surrender acknowledgement, a tariff change on file.")

    if weak_only:
        # Disputing the reading, without deflecting, is worth a meter test on
        # any band — it is cheaper than an inspection and it is conclusive.
        # Disputing it while deflecting everything else is not: "your machine
        # is wrong" is what anybody says when challenged.
        if disputes_meter and not evasion:
            return ("METER_TEST_PRIORITY",
                    f"The consumer disputes the reading and answered the "
                    f"questions put to them. Consumption is down "
                    f"{c.consumption_drop_pct:.0f}% with no explanation "
                    f"offered that the meter contradicts. A meter test settles "
                    f"whether the reading is real for a fraction of the cost "
                    f"of an inspection.",
                    "A meter that tests correct, which would leave the "
                    "consumption unexplained and put inspection back on the "
                    "table.")
        # A denial on an account with physical evidence behind it does not
        # move anything. A denial on a metering-pattern account is a reason to
        # test the meter, which is the cheaper and more conclusive step.
        if c.recommended in ("INSPECT_URGENT", "INSPECT_ROUTINE"):
            return ("PROCEED_UNCHANGED",
                    "The consumer states nothing changed, which the reading "
                    "does not support — but a denial is not evidence, and this "
                    "account was already ranked on signals the call did not "
                    "touch. It stands where the screening put it.",
                    "A documented explanation, or a meter test result.")
        return ("METER_TEST_PRIORITY",
                f"Nothing changed at the premises on the consumer's account, "
                f"yet consumption fell {c.consumption_drop_pct:.0f}%. Either "
                f"the meter is wrong or the account is, and only one of those "
                f"is an offence. The meter test distinguishes them and costs a "
                f"fraction of an inspection.",
                "A meter that tests correct, which would leave the consumption "
                "unexplained and put inspection back on the table.")

    if corroborated and not evasion:
        c0 = corroborated[0]
        if c0.claim == "equipment_added":
            return ("ROUTE_TO_LOAD_REGULARISATION",
                    "Unauthorised additional load, volunteered by the consumer "
                    "and confirmed by the connected-load reading. §126, not "
                    "§135 — and they asked how to fix it.",
                    "Nothing. This is a billing and sanction correction, and "
                    "sending an enforcement team to a consumer who "
                    "self-declared would be indefensible.")
        if c0.claim == "meter_defective":
            return ("METER_TEST_PRIORITY",
                    "The consumer reports a blank or dead display and the "
                    "pattern is consistent with under-recording. Test the "
                    "meter before anything is alleged.",
                    "A meter that tests correct. Then the consumption question "
                    "is live again and inspection is back on the table.")
        return ("CLEAR_PENDING_RECORD_CHECK",
                f"The explanation is consistent with the meter "
                f"({c0.against}) and can be verified against the register. "
                f"If it checks out the score should fall.",
                "The document not existing. If the register has no such record "
                "the account returns to the screening band it came from.")

    if evasion and meta["questions_answered"] < meta["questions_asked"]:
        return ("PROCEED_UNCHANGED",
                "The call did not settle anything. Deflection is not evidence "
                "of wrongdoing — people are wary of unexpected calls about "
                "their bill — so this leaves the account exactly where the "
                "screening put it.",
                "Nothing from this call. The inspection decision rests on the "
                "meter data alone, as it did before.")

    return ("RECONTACT",
            "The consumer engaged but nothing was established either way. The "
            "questions asked did not reach a fact the meter can be checked "
            "against.",
            "A follow-up that asks about the specific signal still open, or a "
            "meter test if the account is otherwise unexplained.")


# --------------------------------------------------------------------------
# 5. Running a campaign end to end.
# --------------------------------------------------------------------------

import json  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

CACHE = Path(__file__).resolve().parent / "_outreach_cache.json"

# What the analysis should have concluded, given the hidden truth. Used only to
# score the pipeline — never to produce a disposition. If this table were
# consulted at analysis time the demo would be marking its own homework.
EXPECTED = {
    # PROCEED_TO_INSPECTION is deliberately absent. Sending an inspector to a
    # consumer whose meter is genuinely defective is the failure this band
    # exists to prevent, and scoring it as acceptable would hide it.
    "GENUINE_METER_FAULT": {"METER_TEST_PRIORITY", "CLEAR_PENDING_RECORD_CHECK"},
    "UNRECORDED_EXPLANATION": {"CLEAR_PENDING_RECORD_CHECK", "RECONTACT"},
    "GENUINELY_VACANT": {"CLEAR_PENDING_RECORD_CHECK", "PROCEED_TO_INSPECTION",
                         "ROUTE_TO_HUMAN", "RECONTACT"},
    "ADDED_LOAD_UNDECLARED": {"ROUTE_TO_LOAD_REGULARISATION",
                              "PROCEED_TO_INSPECTION", "RECONTACT"},
    "EVASIVE": {"PROCEED_UNCHANGED", "PROCEED_TO_INSPECTION", "RECONTACT"},
    "COOPERATIVE_UNAWARE": {"RECONTACT", "CLEAR_PENDING_RECORD_CHECK",
                            "PROCEED_TO_INSPECTION"},
    "REFUSES": {"PROCEED_ON_DATA_ALONE"},
}


def _key(rule: str, limit: int, consumer_nos: list[str] | None,
         provider: str) -> str:
    return f"{rule}|{limit}|{','.join(consumer_nos or [])}|{provider}|v1"


class CampaignNotGenerated(RuntimeError):
    """Asked for a campaign whose calls have not been made yet."""


def campaign(rule: str = "meter_test", limit: int = 10,
             consumer_nos: list[str] | None = None,
             provider: str = "simulated") -> dict:
    """A generated campaign, from the store. Never generates.

    Generation renders speech, mixes two channels and runs Whisper over both —
    minutes of CPU for ten calls, which is not something to do inside a request
    that a tool call is waiting on. `generate_visit_recordings.py` draws the
    same line for the field-visit fixtures and this follows it.
    """
    key = _key(rule, limit, consumer_nos, provider)
    store = _cache_read()
    if key not in store:
        raise CampaignNotGenerated(
            f"No campaign for rule {rule!r}, limit {limit}. Generate it with:\n"
            f"  .venv-audio/bin/python services/generate_outreach_calls.py "
            f"--rule {rule} --limit {limit}")
    return store[key]


def generate_campaign(rule: str = "meter_test", limit: int = 10,
                      consumer_nos: list[str] | None = None,
                      provider: str = "simulated",
                      progress: bool = False) -> dict:
    """Call every selected consumer, record, transcribe and analyse.

    Offline. Needs `say`, `ffmpeg` and faster-whisper — see
    `generate_outreach_calls.py` for the interpreter this wants.
    """
    import outreach_providers as provs
    import transcribe as tr

    key = _key(rule, limit, consumer_nos, provider)
    cached = _cache_read()

    targets = select(rule, limit, consumer_nos)
    if not targets:
        raise ValueError(f"rule {rule!r} selected no consumers")

    if provider != "simulated":
        provs.PROVIDERS[provider]().place("", [], "")  # raises with the reason

    driver = provs.SimulatedProvider(
        RECORDINGS, {"agent": AGENT_VOICE, "consumer": CONSUMER_VOICE})

    calls = []
    for c in targets:
        rng = random.Random(f"outreach-{c.consumer_no}")
        truth = _truth_for(c, rng)
        questions = plan(c)
        script, meta = converse(c, questions, rng, truth)
        call_id = f"OC-{c.consumer_no.replace('-', '')}"

        if progress:
            print(f"  {call_id}  score {c.anomaly_risk:>3}  "
                  f"{len(questions)} questions  ...", flush=True)
        placed = driver.place(c.consumer_no, script, call_id)
        if placed.status == "FAILED":
            calls.append({"call_id": call_id, "consumer_no": c.consumer_no,
                          "status": "FAILED", "note": placed.note})
            continue

        transcript = tr.transcribe(placed.recording)
        analysis = analyse(c, transcript, meta)
        if progress:
            print(f"       {transcript['duration_seconds']:>5.1f}s  "
                  f"{transcript['turn_count']:>2} turns  -> "
                  f"{analysis['disposition']}", flush=True)

        calls.append({
            "call_id": call_id,
            "consumer_no": c.consumer_no,
            "division": c.division,
            "subdivision": c.subdivision,
            "category": c.category,
            "status": placed.status,
            "provider": placed.provider,
            "calling_window": CALLING_WINDOW,
            "duration_seconds": transcript["duration_seconds"],
            "turns": transcript["turn_count"],
            "questions_planned": [asdict(q) for q in questions],
            "transcript": transcript,
            "analysis": analysis,
            "recording": f"{call_id}.wav",
            "listen": f"{call_id}.mp3",
            # Held back from `analysis` on purpose — see the module note.
            "_hidden_truth": truth,
            "_analysis_agreed": analysis["disposition"] in EXPECTED[truth],
        })

    result = {
        "rule": rule,
        "rule_meaning": RULES.get(rule, (None, "explicit consumer list"))[1],
        "requested": limit,
        "called": len(calls),
        "provider": provider,
        "summary": _rollup(calls),
        "calls": calls,
    }
    cached[key] = result
    _cache_write(cached)
    return result


def _rollup(calls: list[dict]) -> dict:
    done = [c for c in calls if c.get("analysis")]
    by_disposition: dict[str, int] = {}
    for c in done:
        d = c["analysis"]["disposition"]
        by_disposition[d] = by_disposition.get(d, 0) + 1

    agreed = sum(1 for c in done if c.get("_analysis_agreed"))
    cleared = sum(1 for c in done if c["analysis"]["disposition"] in
                  ("CLEAR_PENDING_RECORD_CHECK", "ROUTE_TO_LOAD_REGULARISATION",
                   "METER_TEST_PRIORITY"))
    return {
        "completed": sum(1 for c in done if c["status"] == "COMPLETED"),
        "refused_consent": sum(1 for c in done if c["status"] == "REFUSED"),
        "by_disposition": by_disposition,
        "diverted_from_inspection": cleared,
        "diverted_note":
            f"{cleared} of {len(done)} calls produced a reason not to send an "
            f"inspector — a meter test, a load regularisation, or an "
            f"explanation to verify against the register. That is the number "
            f"the campaign is worth, and each one still needs the record check "
            f"before the score is actually reduced.",
        "analysis_agreed_with_ground_truth": f"{agreed}/{len(done)}",
        "agreement_note":
            "Each simulated consumer was given a hidden truth that the analysis "
            "never sees. This is the share where the disposition was defensible "
            "given that truth. It measures the pipeline, not the consumers.",
    }


def _cache_read() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _cache_write(data: dict) -> None:
    CACHE.write_text(json.dumps(data, indent=1, default=str))


def reanalyse(rule: str = "meter_test", limit: int = 10,
              consumer_nos: list[str] | None = None,
              provider: str = "simulated") -> dict:
    """Re-run the analysis over transcripts already captured.

    The analysis changes far more often than the audio does. Re-rendering
    speech and re-running Whisper to test a change in the disposition logic
    would make every iteration minutes long, and would also move the
    transcripts underneath the comparison — so a change in the output could no
    longer be attributed to the change in the code.
    """
    key = _key(rule, limit, consumer_nos, provider)
    store = _cache_read()
    if key not in store:
        raise CampaignNotGenerated(f"Nothing generated for {rule}/{limit} yet.")

    result = store[key]
    book = {c.consumer_no: c for c in _load()[0]}
    for call in result["calls"]:
        if not call.get("analysis"):
            continue
        c = book[call["consumer_no"]]
        # The procedural facts come from the stored call, not from replaying
        # the conversation — replaying would re-roll the persona.
        meta = {
            "consent": call["analysis"]["consent"],
            "questions_asked": call["analysis"]["questions_asked"],
            "questions_answered": call["analysis"]["questions_answered"],
        }
        call["analysis"] = analyse(c, call["transcript"], meta)
        call["_analysis_agreed"] = (
            call["analysis"]["disposition"] in EXPECTED[call["_hidden_truth"]])
    result["summary"] = _rollup(result["calls"])
    store[key] = result
    _cache_write(store)
    return result
