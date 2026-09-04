"""Building two-channel call audio from a script.

Extracted from `generate_visit_recordings.py`, which grew this machinery for
the field-visit fixtures and is now not the only thing that needs it: consumer
outreach records calls the same way and must produce audio the same
transcriber can read.

The one invariant worth stating, because everything downstream depends on it:
**each side gets its own channel, and is silent while the other is talking.**
`transcribe.py` takes its speaker labels from the channels rather than from
diarisation, so the attribution is a property of the medium. Mix the two sides
into one track and the pipeline is left inferring who said what from the words
— which, in a conversation where the question is what a consumer admitted, is
precisely the inference that must not be guessed.

Needs `say` (macOS) and `ffmpeg`/`ffprobe` on PATH. Nothing here runs at
request time; it is fixture generation.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

SAMPLE_RATE = 16_000  # what the transcriber wants; resampling later loses nothing

# A beat between turns. Real conversation does not butt utterances together,
# and the gap gives the transcriber a boundary to segment on.
GAP_SECONDS = 0.45


def have_tools() -> str | None:
    """The first missing binary, or None. Checked before a long generation."""
    for binary in ("say", "ffmpeg", "ffprobe"):
        if not shutil.which(binary):
            return binary
    return None


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {result.stderr.strip()[:400]}")


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def speak(text: str, voice: str, dest: Path) -> Path:
    """One utterance, as a mono WAV at the transcriber's sample rate."""
    aiff = dest.with_suffix(".aiff")
    run(["say", "-v", voice, "-o", str(aiff), text])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff),
         "-ar", str(SAMPLE_RATE), "-ac", "1", str(dest)])
    aiff.unlink()
    return dest


def silence(seconds: float, dest: Path) -> Path:
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono",
         "-t", f"{seconds:.3f}", str(dest)])
    return dest


def concat(parts: list[Path], dest: Path, work: Path) -> Path:
    listing = work / f"{dest.stem}-parts.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in parts))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c", "copy", str(dest)])
    listing.unlink()
    return dest


def build_two_channel(
    script: list[tuple[str, str]],
    voices: dict[str, str],
    left_speaker: str,
    dest: Path,
    work: Path,
    *,
    stem: str,
    progress: bool = False,
) -> Path:
    """Render `script` to a stereo WAV, plus an MP3 mixdown to listen to.

    `script` is [(speaker, text), ...]. `left_speaker` goes to channel 0, which
    is the channel `transcribe.py` labels first — get this wrong and every turn
    in every transcript is attributed to the wrong party.
    """
    left_track: list[Path] = []
    right_track: list[Path] = []

    for index, (speaker, text) in enumerate(script):
        utterance = speak(text, voices[speaker], work / f"{stem}-{index}.wav")
        hush = silence(duration(utterance), work / f"{stem}-{index}-q.wav")
        gap = silence(GAP_SECONDS, work / f"{stem}-{index}-g.wav")

        if speaker == left_speaker:
            left_track += [utterance, gap]
            right_track += [hush, gap]
        else:
            left_track += [hush, gap]
            right_track += [utterance, gap]
        if progress:
            print(f"   {stem}  turn {index + 1:>2}  {speaker:<12} "
                  f"{duration(utterance):>5.1f}s")

    left = concat(left_track, work / f"{stem}-L.wav", work)
    right = concat(right_track, work / f"{stem}-R.wav", work)

    dest.parent.mkdir(parents=True, exist_ok=True)
    # amerge, not join: two mono inputs become one two-channel stream with the
    # first input on the left.
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(left), "-i", str(right),
         "-filter_complex", "[0:a][1:a]amerge=inputs=2[a]", "-map", "[a]",
         "-ac", "2", "-ar", str(SAMPLE_RATE), str(dest)])

    # A mixdown for a person to listen to. The WAV is hard-panned because the
    # transcriber takes its speaker labels from the channels, which on
    # headphones puts each voice in one ear and is unpleasant to sit through.
    # Folding both to centre makes it play like a phone call. Nothing reads
    # this — it exists so the call can be reviewed by ear.
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(dest),
         "-filter_complex", "[0:a]pan=mono|c0=0.5*c0+0.5*c1,loudnorm[a]",
         "-map", "[a]", "-codec:a", "libmp3lame", "-b:a", "64k",
         "-ar", "22050", str(dest.with_suffix(".mp3"))])
    return dest
