"""Telephony adapters. One interface, several vendors, chosen by configuration.

A call here is turn-based: the provider speaks a prompt, records the consumer's
answer, posts it back, and we return the next prompt. That is not a compromise
— it is the right shape for this work. The questions come from a fixed plan
derived from the signals that fired on the account, there is a natural pause
after each one, and the provider records the whole call for free. Real-time
media streaming buys conversational fluidity that a five-question diagnostic
questionnaire does not need, and costs a WebSocket audio path, streaming STT,
streaming TTS and barge-in handling.

So an adapter has to do four things, and each is a small translation of the
same idea into the vendor's dialect:

    originate      start a call, return the vendor's id for it
    say_and_record speak this text, record the reply, then POST to next_url
    say_and_hangup speak this text and end the call
    fetch          pull the finished recording down as a file

`LoopbackProvider` implements all four without a trunk and is the default. It
is not a mock: it drives the real state machine through the real webhook
handlers with real rendered audio, so everything except the phone network is
exercised. Swapping to a vendor changes environment variables.

WHAT IS AND IS NOT TESTED
-------------------------
Loopback is exercised end to end here. The Twilio adapter is written against
TwiML and is the one to reach for first with real credentials. The Exotel
adapter is written from its documented call flow and has not been run against
the service — it is marked as such rather than presented as equivalent, because
an adapter nobody has dialled through is a hypothesis.
"""

from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class Instruction:
    """What the provider should do next, before it is put into a dialect."""
    body: str
    media_type: str


class VoiceProvider(Protocol):
    name: str
    tested: bool

    def originate(self, to: str, call_id: str, answer_url: str,
                  status_url: str) -> str: ...
    def say_and_record(self, text: str, next_url: str,
                       max_seconds: int) -> Instruction: ...
    def say_and_hangup(self, text: str) -> Instruction: ...
    def recording_url(self, payload: dict) -> str | None: ...
    def fetch(self, url: str, dest: Path) -> Path: ...


def _post_form(url: str, data: dict, auth: tuple[str, str] | None = None) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    if auth:
        token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def _xml(text: str) -> str:
    """Escape for a TwiML/Exotel text node.

    Consumer numbers are spoken digit by digit and division names carry
    apostrophes; an unescaped ampersand in a prompt takes down the whole
    response with a parse error at the vendor rather than here.
    """
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


# --------------------------------------------------------------------------


class LoopbackProvider:
    """Runs the whole flow with no trunk. The default, and genuinely useful.

    It does not stub the state machine out — it posts to the same webhook
    handlers a vendor would, so queueing, turn sequencing, the calling window,
    retries, recording assembly, transcription and analysis all run exactly as
    they will in production. The only thing absent is the phone network.
    """

    name = "loopback"
    tested = True

    def __init__(self, settings: Any = None) -> None:
        self.settings = settings

    def originate(self, to: str, call_id: str, answer_url: str,
                  status_url: str) -> str:
        # The runtime drives loopback turns itself; there is nothing to dial.
        return f"LB-{call_id}"

    def say_and_record(self, text: str, next_url: str,
                       max_seconds: int) -> Instruction:
        return Instruction(json.dumps({
            "action": "say_and_record", "text": text,
            "next": next_url, "max_seconds": max_seconds}), "application/json")

    def say_and_hangup(self, text: str) -> Instruction:
        return Instruction(json.dumps({
            "action": "say_and_hangup", "text": text}), "application/json")

    def recording_url(self, payload: dict) -> str | None:
        return payload.get("RecordingUrl")

    def fetch(self, url: str, dest: Path) -> Path:
        # Loopback recordings are already on disk; the "url" is the path.
        return Path(url)


class TwilioProvider:
    """TwiML. The fastest route to a call you can actually hear.

    A trial account will dial verified numbers today, which is enough to prove
    the whole loop before anyone starts a procurement conversation.
    """

    name = "twilio"
    tested = False

    API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"

    def __init__(self, settings: Any) -> None:
        self.sid = settings.values["TWILIO_ACCOUNT_SID"]
        self.token = settings.values["TWILIO_AUTH_TOKEN"]
        self.from_number = settings.values["TWILIO_FROM_NUMBER"]

    def originate(self, to: str, call_id: str, answer_url: str,
                  status_url: str) -> str:
        result = _post_form(
            self.API.format(sid=self.sid),
            {"To": to, "From": self.from_number, "Url": answer_url,
             "StatusCallback": status_url,
             "StatusCallbackEvent": "completed",
             # A consumer who does not pick up in 30 seconds is not going to.
             # Longer just holds a concurrency slot open.
             "Timeout": "30",
             "MachineDetection": "Enable"},
            auth=(self.sid, self.token))
        return result.get("sid", "")

    def say_and_record(self, text: str, next_url: str,
                       max_seconds: int) -> Instruction:
        return Instruction(
            f'<?xml version="1.0" encoding="UTF-8"?><Response>'
            f'<Say voice="Polly.Aditi" language="en-IN">{_xml(text)}</Say>'
            f'<Record action="{_xml(next_url)}" method="POST" '
            f'maxLength="{max_seconds}" timeout="4" playBeep="false" '
            f'trim="trim-silence" />'
            f'</Response>', "application/xml")

    def say_and_hangup(self, text: str) -> Instruction:
        return Instruction(
            f'<?xml version="1.0" encoding="UTF-8"?><Response>'
            f'<Say voice="Polly.Aditi" language="en-IN">{_xml(text)}</Say>'
            f'<Hangup/></Response>', "application/xml")

    def recording_url(self, payload: dict) -> str | None:
        url = payload.get("RecordingUrl")
        return f"{url}.wav" if url else None

    def fetch(self, url: str, dest: Path) -> Path:
        req = urllib.request.Request(url)
        token = base64.b64encode(f"{self.sid}:{self.token}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
        return dest


class ExotelProvider:
    """Indian trunk with DLT registration. The one a DISCOM pilot ends on.

    NOT YET RUN against a live account. Exotel drives calls through App Bazaar
    flows rather than returning markup inline the way TwiML does, so the
    `say_and_record` shape below is the documented equivalent and not a
    verified one. Treat the first real call as a debugging session, and do not
    let this class's existence imply it has been tested.
    """

    name = "exotel"
    tested = False

    def __init__(self, settings: Any) -> None:
        v = settings.values
        self.sid = v["EXOTEL_SID"]
        self.token = v["EXOTEL_TOKEN"]
        self.caller_id = v["EXOTEL_CALLER_ID"]
        self.subdomain = v["EXOTEL_SUBDOMAIN"]

    def originate(self, to: str, call_id: str, answer_url: str,
                  status_url: str) -> str:
        url = (f"https://{self.subdomain}/v1/Accounts/{self.sid}"
               f"/Calls/connect.json")
        result = _post_form(url, {
            "From": to, "CallerId": self.caller_id, "Url": answer_url,
            "StatusCallback": status_url, "TimeLimit": "600",
            "TimeOut": "30"}, auth=(self.sid, self.token))
        return (result.get("Call") or {}).get("Sid", "")

    def say_and_record(self, text: str, next_url: str,
                       max_seconds: int) -> Instruction:
        return Instruction(
            f'<?xml version="1.0" encoding="UTF-8"?><Response>'
            f'<Say>{_xml(text)}</Say>'
            f'<Record action="{_xml(next_url)}" maxLength="{max_seconds}" '
            f'finishOnKey="#" />'
            f'</Response>', "application/xml")

    def say_and_hangup(self, text: str) -> Instruction:
        return Instruction(
            f'<?xml version="1.0" encoding="UTF-8"?><Response>'
            f'<Say>{_xml(text)}</Say><Hangup/></Response>', "application/xml")

    def recording_url(self, payload: dict) -> str | None:
        return payload.get("RecordingUrl")

    def fetch(self, url: str, dest: Path) -> Path:
        req = urllib.request.Request(url)
        token = base64.b64encode(f"{self.sid}:{self.token}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
        return dest


ADAPTERS: dict[str, type] = {
    "loopback": LoopbackProvider,
    "twilio": TwilioProvider,
    "exotel": ExotelProvider,
}


def build(config) -> VoiceProvider:
    """The provider the configuration selects. The only place a vendor is named."""
    adapter = ADAPTERS.get(config.provider)
    if adapter is None:
        raise KeyError(
            f"No adapter for {config.provider!r}. Have: {', '.join(ADAPTERS)}")
    problems = config.blocking_problems()
    if problems:
        raise RuntimeError("Cannot start calling:\n  - " + "\n  - ".join(problems))
    return adapter(config.settings)
