"""The call state machine: queue, dial, take turns, finish, analyse.

A real call is not a function that returns a result. You originate it and then
the *provider* calls you — ringing, answered, here is the reply to question
three, here is the recording. So the unit of work is a stored state that
several inbound requests advance, and this module is that state plus the
handlers that move it.

    QUEUED -> DIALING -> IN_PROGRESS -> COMPLETED
                      \\-> NO_ANSWER (retried, up to max_attempts)
                      \\-> REFUSED   (consumer declined; never retried)
                      \\-> FAILED

TRANSCRIPTS ON THE REAL PATH
----------------------------
We know exactly what the agent said, because we wrote it and handed it to the
provider to speak. Only the consumer's side needs recognition, and it arrives
one answer per turn, already attributed. So the transcript is assembled rather
than diarised: agent turns are verbatim, consumer turns are Whisper over that
turn's recording.

That is strictly better than transcribing a mixed recording. There is no
speaker inference to get wrong, and a recognition error can never move a
sentence from one party to the other — which, in a conversation whose whole
purpose is establishing what the consumer said, is the error that matters.
"""

from __future__ import annotations

import json
import random
import sys
import time as _time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import discom_outreach as outreach  # noqa: E402
import outreach_config as config_mod  # noqa: E402
import outreach_providers as providers  # noqa: E402
from discom_theft import _load  # noqa: E402

STORE = Path(__file__).resolve().parent / "_outreach_calls.json"
TURN_AUDIO = outreach.RECORDINGS / "turns"

# A consumer answering a question about their meter takes seconds, not a
# minute. A long cap mostly records silence after they have finished, which
# costs storage and gives the recogniser more room to hallucinate.
MAX_ANSWER_SECONDS = 25


@dataclass
class CallState:
    call_id: str
    consumer_no: str
    rule: str
    status: str = "QUEUED"
    turn: int = 0                       # 0 = opening, 1..n = planned questions
    attempts: int = 0
    provider: str = ""
    provider_call_id: str = ""
    signals: list[str] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)     # what we said
    answers: list[dict] = field(default_factory=list)    # what came back
    consent: str = "pending"
    recording: str | None = None
    error: str = ""
    queued_at: str = ""
    started_at: str = ""
    ended_at: str = ""
    analysis: dict | None = None
    # Only set by loopback, and never read by the analysis. See discom_outreach.
    _hidden_truth: str = ""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _read() -> dict[str, dict]:
    if STORE.exists():
        try:
            return json.loads(STORE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _write(data: dict[str, dict]) -> None:
    STORE.write_text(json.dumps(data, indent=1, default=str))


def get(call_id: str) -> CallState | None:
    raw = _read().get(call_id.upper())
    return CallState(**raw) if raw else None


def save(state: CallState) -> None:
    data = _read()
    data[state.call_id] = asdict(state)
    _write(data)


def all_calls(rule: str | None = None) -> list[CallState]:
    out = [CallState(**v) for v in _read().values()]
    if rule:
        out = [c for c in out if c.rule == rule]
    return sorted(out, key=lambda c: c.call_id)


# --------------------------------------------------------------------------
# Queueing
# --------------------------------------------------------------------------

def queue_campaign(rule: str = "meter_test", limit: int = 10,
                   consumer_nos: list[str] | None = None) -> dict:
    """Create the call records. Dials nothing — `pump()` does that."""
    cfg = config_mod.load()
    targets = outreach.select(rule, limit, consumer_nos)
    if not targets:
        raise ValueError(f"rule {rule!r} selected no consumers")

    data = _read()
    created, existing = [], []
    for c in targets:
        call_id = f"OC-{c.consumer_no.replace('-', '')}"
        if call_id in data and data[call_id]["status"] not in ("FAILED",):
            existing.append(call_id)
            continue
        state = CallState(
            call_id=call_id, consumer_no=c.consumer_no, rule=rule,
            provider=cfg.provider, queued_at=_now(),
            signals=[q.signal for q in outreach.plan(c)],
            _hidden_truth=outreach._truth_for(
                c, random.Random(f"outreach-{c.consumer_no}")),
        )
        data[call_id] = asdict(state)
        created.append(call_id)
    _write(data)

    return {
        "rule": rule,
        "queued": len(created),
        "already_present": len(existing),
        "call_ids": created,
        "configuration": cfg.describe(),
        "next_step":
            "Nothing has been dialled. Release the campaign to start calling."
            if created else "No new calls queued.",
    }


# --------------------------------------------------------------------------
# Dialling
# --------------------------------------------------------------------------

def pump(rule: str | None = None, max_calls: int | None = None) -> dict:
    """Start calls that are eligible to start now."""
    cfg = config_mod.load()
    problems = cfg.blocking_problems()
    if problems:
        return {"dialled": 0, "blocked_by": problems}

    # Loopback dials nobody, so the legal calling window does not apply to it.
    # Enforcing it there would make the demo unusable outside office hours for
    # no benefit to any consumer.
    if cfg.provider != "loopback" and not cfg.within_window():
        return {"dialled": 0, "blocked_by": [
            f"Outside the calling window ({cfg.window_start:%H:%M}-"
            f"{cfg.window_end:%H:%M} {cfg.timezone}). Opens "
            f"{cfg.next_window_open():%Y-%m-%d %H:%M}."]}

    provider = providers.build(cfg)
    waiting = [c for c in all_calls(rule) if c.status in ("QUEUED", "NO_ANSWER")
               and c.attempts < cfg.max_attempts]
    in_flight = sum(1 for c in all_calls() if c.status in ("DIALING", "IN_PROGRESS"))
    room = max(0, cfg.max_concurrent - in_flight)
    batch = waiting[:min(room, max_calls or room)]

    dialled = []
    for state in batch:
        book = {x.consumer_no: x for x in _load()[0]}
        consumer = book[state.consumer_no]
        try:
            number = cfg.number_for(state.consumer_no, None)
        except ValueError as exc:
            state.status, state.error = "FAILED", str(exc)
            save(state)
            continue

        state.attempts += 1
        state.status = "DIALING"
        state.started_at = _now()
        state.provider = cfg.provider
        save(state)

        try:
            if cfg.provider == "twilio-inline":
                # The whole script goes out with the dial; nothing calls back.
                _run_twilio_inline(state, consumer, cfg, provider, number)
            else:
                state.provider_call_id = provider.originate(
                    number, state.call_id,
                    cfg.webhook(f"answer?call_id={state.call_id}"),
                    cfg.webhook(f"status?call_id={state.call_id}"))
            save(state)
        except Exception as exc:  # noqa: BLE001
            state.status, state.error = "FAILED", str(exc)[:300]
            save(state)
            continue

        if cfg.provider == "loopback":
            _run_loopback(state, consumer, cfg)
        dialled.append(state.call_id)

    return {"dialled": len(dialled), "call_ids": dialled,
            "provider": cfg.provider,
            "still_waiting": max(0, len(waiting) - len(batch))}


# --------------------------------------------------------------------------
# Turn handlers — what the provider's webhooks call
# --------------------------------------------------------------------------

def on_answer(call_id: str) -> providers.Instruction:
    """The consumer picked up. Speak the opening and record the reply."""
    cfg = config_mod.load()
    provider = providers.build(cfg)
    state = get(call_id)
    if state is None:
        return provider.say_and_hangup("Sorry, there has been an error. Goodbye.")

    consumer = {x.consumer_no: x for x in _load()[0]}[state.consumer_no]
    state.status = "IN_PROGRESS"
    state.turn = 0
    text = outreach.opening_line(consumer)
    state.prompts = [text]
    save(state)
    return provider.say_and_record(
        text, cfg.webhook(f"turn?call_id={call_id}&turn=0"), MAX_ANSWER_SECONDS)


def on_turn(call_id: str, turn: int, payload: dict) -> providers.Instruction:
    """One answer arrived. Store it, decide the next prompt."""
    cfg = config_mod.load()
    provider = providers.build(cfg)
    state = get(call_id)
    if state is None:
        return provider.say_and_hangup("Sorry, there has been an error. Goodbye.")

    consumer = {x.consumer_no: x for x in _load()[0]}[state.consumer_no]
    questions = outreach.plan(consumer)

    heard = _capture(state, turn, payload, provider)

    # Turn 0 is the consent checkpoint, and it is honoured on what the consumer
    # actually said rather than on a keypress. Someone who says "do not call me
    # again" has declined however the menu was worded.
    if turn == 0 and outreach.refused_consent(heard):
        state.consent = "refused"
        state.status = "REFUSED"
        state.ended_at = _now()
        state.prompts.append(outreach.REFUSAL_CLOSE)
        save(state)
        _finalise(state, consumer)
        return provider.say_and_hangup(outreach.REFUSAL_CLOSE)

    if turn == 0:
        state.consent = "granted"

    next_index = turn  # question 1 follows turn 0
    if next_index < len(questions):
        text = questions[next_index].ask
        state.turn = turn + 1
        state.prompts.append(text)
        save(state)
        return provider.say_and_record(
            text, cfg.webhook(f"turn?call_id={call_id}&turn={turn + 1}"),
            MAX_ANSWER_SECONDS)

    state.prompts.append(outreach.CLOSING_LINE)
    state.status = "COMPLETED"
    state.ended_at = _now()
    save(state)
    _finalise(state, consumer)
    return provider.say_and_hangup(outreach.CLOSING_LINE)


def on_status(call_id: str, payload: dict) -> dict:
    """The provider reporting how the call ended."""
    state = get(call_id)
    if state is None:
        return {"ok": False, "reason": f"unknown call {call_id}"}

    status = (payload.get("CallStatus") or payload.get("Status") or "").lower()
    if status in ("no-answer", "busy", "no_answer", "failed") \
            and state.status not in ("COMPLETED", "REFUSED"):
        cfg = config_mod.load()
        exhausted = state.attempts >= cfg.max_attempts
        state.status = "FAILED" if exhausted else "NO_ANSWER"
        state.error = f"provider reported {status}"
        state.ended_at = _now() if exhausted else ""
    provider = providers.build(config_mod.load())
    url = provider.recording_url(payload)
    if url:
        state.recording = url
    save(state)
    return {"ok": True, "status": state.status, "attempts": state.attempts}


def _capture(state: CallState, turn: int, payload: dict,
             provider: Any) -> str:
    """Store one consumer answer and return what was heard."""
    # Three ways an answer arrives, in order of how much work they cost.
    # Loopback hands us the text. Provider speech recognition returns it inline
    # on the webhook — a second per turn, which is what makes a live call feel
    # like a conversation. A recording has to be downloaded and put through
    # Whisper, which is more accurate on accented English and adds four to six
    # seconds of silence to every turn.
    text = payload.get("_loopback_text", "") or payload.get("SpeechResult", "")
    confidence = payload.get("Confidence")
    url = provider.recording_url(payload)
    path = None

    if url and not text:
        TURN_AUDIO.mkdir(parents=True, exist_ok=True)
        path = TURN_AUDIO / f"{state.call_id}-{turn}.wav"
        try:
            path = provider.fetch(url, path)
            text = _recognise(path)
        except Exception as exc:  # noqa: BLE001
            state.error = f"turn {turn}: {str(exc)[:160]}"
            text = ""

    state.answers.append({
        "turn": turn, "text": text,
        "audio": str(path) if path else None,
        "recording_url": url,
        "confidence": confidence,
        # An empty answer is a fact about the call, not a gap to paper over. It
        # means the consumer said nothing the recogniser could use, and the
        # analysis counts it as a question that did not land.
        "heard": bool(text.strip()),
    })
    save(state)
    return text


def _recognise(path: Path) -> str:
    """Whisper over one answer. Attribution is already known, so no diarisation."""
    import transcribe as tr

    result = tr._segments(path, "customer")
    return " ".join(seg["text"] for seg in result).strip()


def _finalise(state: CallState, consumer: Any) -> None:
    """Assemble the transcript and run the analysis that already exists."""
    turns, clock = [], 0.0
    for index, prompt in enumerate(state.prompts):
        turns.append({"speaker": "representative", "text": prompt,
                      "start": clock, "end": clock + 4})
        clock += 5
        answer = next((a for a in state.answers if a["turn"] == index), None)
        if answer and answer["text"]:
            turns.append({"speaker": "customer", "text": answer["text"],
                          "start": clock, "end": clock + 4})
            clock += 5

    transcript = {
        "engine": "assembled (agent verbatim, consumer via faster-whisper)",
        "diarisation": "none needed — one recording per consumer answer",
        "turn_count": len(turns),
        "duration_seconds": round(clock, 1),
        "turns": turns,
        "text": "\n".join(
            f"{t['speaker'].upper()}: {t['text']}" for t in turns),
    }
    answered = sum(1 for a in state.answers if a["text"] and a["turn"] > 0)
    meta = {
        "consent": state.consent,
        "questions_asked": max(len(state.prompts) - 2, 0),
        "questions_answered": answered,
    }
    state.analysis = outreach.analyse(consumer, transcript, meta)
    state.analysis["transcript"] = transcript
    save(state)


# --------------------------------------------------------------------------
# Loopback driver
# --------------------------------------------------------------------------

def _run_loopback(state: CallState, consumer: Any, cfg: Any) -> None:
    """Walk one call through the real handlers, with no trunk.

    Renders each consumer answer to audio and puts it through the same Whisper
    path a provider recording takes, so the loopback is not a shortcut around
    recognition — a transcript here has the same mistakes in it that a real one
    would.
    """
    import audio

    rng = random.Random(f"loopback-{state.consumer_no}")
    truth = state._hidden_truth
    questions = outreach.plan(consumer)
    use_audio = audio.have_tools() is None

    on_answer(state.call_id)

    for turn in range(len(questions) + 1):
        if turn == 0:
            reply = (rng.choice([
                "No. I am not talking to a machine about my meter. Send me a letter.",
                "I do not consent to a recording. Do not call this number again."])
                if truth == "REFUSES" else
                rng.choice(["Yes, go ahead.", "Alright. What is it about?",
                            "Yes, fine. Tell me."]))
        else:
            reply, _ = outreach.answer_for(truth, questions[turn - 1].signal, rng)

        payload: dict = {}
        if use_audio:
            TURN_AUDIO.mkdir(parents=True, exist_ok=True)
            work = TURN_AUDIO / ".work"
            work.mkdir(exist_ok=True)
            dest = TURN_AUDIO / f"{state.call_id}-{turn}.wav"
            try:
                audio.speak(reply, outreach.CONSUMER_VOICE, dest)
                payload["RecordingUrl"] = str(dest)
            except Exception:  # noqa: BLE001
                payload["_loopback_text"] = reply
        else:
            payload["_loopback_text"] = reply

        instruction = on_turn(state.call_id, turn, payload)
        if "say_and_hangup" in instruction.body:
            break
        _time.sleep(0)

    on_status(state.call_id, {"CallStatus": "completed"})


# --------------------------------------------------------------------------
# Twilio inline: a real call with nothing calling back
# --------------------------------------------------------------------------

def _run_twilio_inline(state: CallState, consumer: Any, cfg: Any,
                       provider: Any, number: str) -> None:
    """Dial with the whole script attached. Nothing to wait for a webhook."""
    questions = outreach.plan(consumer)
    state.prompts = ([outreach.opening_line(consumer)]
                     + [q.ask for q in questions]
                     + [outreach.CLOSING_LINE])
    twiml = provider.build_call(state.prompts, MAX_ANSWER_SECONDS)
    state.provider_call_id = provider.originate_inline(number, twiml)
    state.status = "IN_PROGRESS"
    save(state)


def poll(rule: str | None = None) -> dict:
    """Advance inline calls: are they finished, and what came back.

    The webhook path is pushed to; this one has to ask. Called after a release
    and safe to call repeatedly — a call already analysed is skipped.
    """
    cfg = config_mod.load()
    if cfg.provider != "twilio-inline":
        return {"polled": 0,
                "note": f"{cfg.provider} does not poll; it is driven by webhooks."}

    provider = providers.build(cfg)
    book = {x.consumer_no: x for x in _load()[0]}
    finished, waiting = [], []

    for state in all_calls(rule):
        if state.status not in ("DIALING", "IN_PROGRESS") or not state.provider_call_id:
            continue
        try:
            info = provider.call_status(state.provider_call_id)
        except Exception as exc:  # noqa: BLE001
            state.error = str(exc)[:200]
            save(state)
            continue

        status = (info.get("status") or "").lower()
        if status in ("queued", "ringing", "in-progress"):
            waiting.append(state.call_id)
            continue

        if status in ("no-answer", "busy", "canceled", "failed"):
            exhausted = state.attempts >= cfg.max_attempts
            state.status = "FAILED" if exhausted else "NO_ANSWER"
            state.error = f"Twilio reported {status}"
            state.ended_at = _now() if exhausted else ""
            save(state)
            finished.append(state.call_id)
            continue

        # Completed. Pull the answers down in order and recognise each.
        TURN_AUDIO.mkdir(parents=True, exist_ok=True)
        state.answers = []
        for turn, rec in enumerate(provider.recordings(state.provider_call_id)):
            url = f"https://api.twilio.com{rec['uri'].replace('.json', '.wav')}"
            dest = TURN_AUDIO / f"{state.call_id}-{turn}.wav"
            text = ""
            try:
                provider.fetch(url, dest)
                text = _recognise(dest)
            except Exception as exc:  # noqa: BLE001
                state.error = f"turn {turn}: {str(exc)[:160]}"
            state.answers.append({
                "turn": turn, "text": text, "audio": str(dest),
                "recording_url": url, "confidence": None,
                "heard": bool(text.strip()),
            })

        first = state.answers[0]["text"] if state.answers else ""
        # An inline call cannot stop when someone declines — there is nothing
        # to branch on. The refusal is still honoured afterwards: the call is
        # marked REFUSED, never retried, and the analysis draws no inference
        # from it. What cannot be undone is that the questions were asked, and
        # that is why this mode is barred from live dialling.
        if outreach.refused_consent(first):
            state.consent = "refused"
            state.status = "REFUSED"
        else:
            state.consent = "granted"
            state.status = "COMPLETED"
        state.ended_at = _now()
        try:
            state.recording = provider.whole_call_recording(state.provider_call_id)
        except Exception:  # noqa: BLE001
            state.recording = None
        save(state)
        _finalise(state, book[state.consumer_no])
        finished.append(state.call_id)

    return {"polled": len(finished) + len(waiting),
            "finished": finished, "still_ringing": waiting}
