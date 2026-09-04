"""How a call actually gets placed.

The demo does not dial anyone. It renders the conversation to audio and runs it
through the same transcriber a real recording would go through, so everything
downstream — transcription, corroboration, disposition — is exercised for real
against audio that was really synthesised and really recognised, recognition
errors included.

That is a deliberate choice about what to fake. Faking the *telephony* costs
the demo nothing: the pipeline never sees a difference between a WAV that came
off a PSTN leg and one that came out of `say`. Faking the *transcript* would
have cost it everything, because then the analysis would be reading text that
was never spoken and the demo would prove nothing about whether it works.

The provider interface below is the real seam. `SimulatedProvider` implements
it today; `ExotelProvider` and `TwilioProvider` are written out to the point
where the missing piece is credentials and a media-streaming handler, and they
refuse rather than pretend when those are absent. Anyone wiring a real trunk in
replaces one class and changes nothing else.

BEFORE A REAL TRUNK IS CONNECTED
--------------------------------
- **DLT registration** and an approved header, per TRAI TCCCPR 2018.
- **Calling window** 09:00-21:00 IST for transactional calls.
- **Recording disclosure** in the opening, before anything is retained — the
  script already carries it and it must not be trimmed for call time.
- **Automated-system disclosure**, likewise in the opening.
- **DPDP Act 2023**: voice is personal data, and the stated purpose has to be
  the actual purpose. "Meter reading verification" while screening for theft
  is the kind of drafting that loses a case.
- **Indic ASR.** `transcribe.py` runs `base.en`. Maharashtra consumers answer
  in Marathi and Hindi, and an English-only model transcribing Marathi does not
  fail loudly — it returns fluent, confident, wrong English, and every layer
  above it believes the words. This is the single largest gap between this
  pipeline and a production one.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class PlacedCall:
    call_id: str
    consumer_no: str
    status: str            # COMPLETED | REFUSED | NO_ANSWER | FAILED
    recording: Path | None
    provider: str
    note: str = ""


class CallProvider(Protocol):
    name: str

    def place(self, consumer_no: str, script: list[tuple[str, str]],
              call_id: str) -> PlacedCall: ...


class SimulatedProvider:
    """Renders the call to a two-channel recording instead of dialling.

    Produces exactly what a contact-centre recorder produces: agent on the left
    channel, consumer on the right. `transcribe.py` reads it without knowing
    the difference.
    """

    name = "simulated"

    def __init__(self, out_dir: Path, voices: dict[str, str]):
        self.out_dir = out_dir
        self.voices = voices

    def place(self, consumer_no: str, script: list[tuple[str, str]],
              call_id: str) -> PlacedCall:
        import audio

        missing = audio.have_tools()
        if missing:
            return PlacedCall(call_id, consumer_no, "FAILED", None, self.name,
                              f"{missing} is not on PATH")

        work = self.out_dir.parent / ".outreach-work"
        work.mkdir(parents=True, exist_ok=True)
        dest = self.out_dir / f"{call_id}.wav"
        try:
            audio.build_two_channel(
                script, self.voices, left_speaker="agent",
                dest=dest, work=work, stem=call_id)
        except Exception as exc:  # noqa: BLE001
            return PlacedCall(call_id, consumer_no, "FAILED", None, self.name,
                              str(exc)[:200])
        finally:
            for leftover in work.glob(f"{call_id}-*"):
                leftover.unlink(missing_ok=True)

        status = "REFUSED" if _refused(script) else "COMPLETED"
        return PlacedCall(call_id, consumer_no, status, dest, self.name)


def _refused(script: list[tuple[str, str]]) -> bool:
    return any("do not consent" in t.lower() or "not talking to a machine" in t.lower()
               for _, t in script)


class _RealProvider:
    """Shared shape for the trunk-backed providers.

    Neither is finished, and both say so rather than degrading to the simulator
    — a provider that silently produces synthetic audio when its credentials
    are missing would put fabricated consumer speech into an enforcement file.
    """

    name = "unset"
    env_keys: tuple[str, ...] = ()

    def __init__(self) -> None:
        self.missing = [k for k in self.env_keys if not os.environ.get(k)]

    def place(self, consumer_no: str, script, call_id: str) -> PlacedCall:
        raise NotImplementedError(
            f"{self.name} needs {', '.join(self.env_keys)} and a media-stream "
            f"handler that bridges the trunk to STT and TTS. Missing: "
            f"{', '.join(self.missing) or 'nothing — implement place()'}. "
            f"Until then use SimulatedProvider; it exercises every stage after "
            f"the audio arrives."
        )


class ExotelProvider(_RealProvider):
    """Indian trunk, DLT-aware. The usual choice for a DISCOM."""
    name = "exotel"
    env_keys = ("EXOTEL_SID", "EXOTEL_TOKEN", "EXOTEL_CALLER_ID")


class TwilioProvider(_RealProvider):
    """Available everywhere; DLT and Indian numbering need arranging separately."""
    name = "twilio"
    env_keys = ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER")


PROVIDERS = {p.name: p for p in (SimulatedProvider, ExotelProvider, TwilioProvider)}
