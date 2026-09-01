"""Speaker-attributed transcription of a two-channel visit recording.

Real speech-to-text, not a lookup: the audio is decoded and passed through
Whisper, and whatever comes back is what the pipeline sees. That matters for
the demo's honesty — a transcript that was really produced from audio carries
recognition errors, and a review that falls over on a misheard word is a review
worth knowing about before it meets a real recording.

Speakers come from the channels rather than from diarisation. The left channel
is the representative and the right is the customer, so each is transcribed on
its own and the two segment lists are merged on their start times. Whisper does
not attribute speakers at all, and inferring them from the words would have the
analysis deciding who admitted what based on its own guess about who was
talking.
"""

from __future__ import annotations

import subprocess
import tempfile
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

# base.en earns its extra weight over tiny on this material: the review turns
# on meter numbers, dates and seal identifiers, and tiny mishears digits often
# enough to matter. Loading is deferred so importing this module stays cheap.
MODEL_SIZE = "base.en"

_lock = threading.Lock()


@lru_cache(maxsize=1)
def _model() -> Any:
    from faster_whisper import WhisperModel

    return WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")


def _extract_channel(source: Path, channel: int, dest: Path) -> Path:
    """One channel of the stereo recording, as mono."""
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
         "-filter_complex", f"[0:a]pan=mono|c0=c{channel}[out]",
         "-map", "[out]", "-ar", "16000", str(dest)],
        check=True, capture_output=True)
    return dest


def _segments(path: Path, speaker: str) -> list[dict]:
    # Whisper will hallucinate filler over long silences, and each channel is
    # silent for roughly half its length by construction. The VAD filter drops
    # those stretches before they reach the decoder.
    segments, _info = _model().transcribe(
        str(path), vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 700})
    out = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            out.append({
                "speaker": speaker,
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": text,
            })
    return out


def transcribe(recording: Path) -> dict:
    """Speaker-labelled transcript of a dual-channel recording."""
    if not recording.exists():
        raise FileNotFoundError(recording)

    # One at a time: the model is not thread-safe and the demo API is happy to
    # serialise a request that takes a few seconds.
    with _lock, tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        left = _extract_channel(recording, 0, work / "rep.wav")
        right = _extract_channel(recording, 1, work / "customer.wav")
        turns = _segments(left, "representative") + _segments(right, "customer")

    turns.sort(key=lambda t: t["start"])

    return {
        "engine": f"faster-whisper/{MODEL_SIZE}",
        "diarisation": "channel-based (left=representative, right=customer)",
        "turn_count": len(turns),
        "duration_seconds": round(turns[-1]["end"], 1) if turns else 0.0,
        "turns": turns,
        "text": "\n".join(
            f"[{t['start']:>6.1f}] {t['speaker'].upper()}: {t['text']}"
            for t in turns
        ),
    }
