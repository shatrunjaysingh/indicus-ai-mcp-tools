"""Generate the field-visit call recordings.

    backend/.venv/bin/python demo/generate_visit_recordings.py

Produces, per visit, under `demo/data/recordings/`: a stereo WAV with the
representative on the left channel and the customer on the right, which is
what the pipeline transcribes; and an MP3 mixdown of the same call for
listening to, which nothing reads.

Two channels rather than one mixed track, because that is how contact-centre
audio is actually captured, and because it makes speaker attribution a property
of the recording instead of a guess made afterwards. Whisper does not diarise;
a single mixed track would leave the pipeline inferring who spoke from the
words, which is precisely the inference the review is supposed to test. With
split channels each side is transcribed on its own and the labels are carried
by the medium.

Needs `say` (macOS) and `ffmpeg` on PATH. Nothing here runs at request time.

The output is *not* in version control — `demo/data/` is gitignored, and 19MB
of WAV does not belong in the history. A fresh clone therefore has no
recordings until this is run, and `utility_api.py` answers 503 with that
instruction until it is.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utility_data import REP_VOICE, VISITS  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "recordings"
SAMPLE_RATE = 16_000  # what the transcriber wants; resampling later loses nothing

# A beat between turns. Real conversation does not butt utterances together,
# and the gap gives the transcriber a boundary to segment on.
GAP_SECONDS = 0.45


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {result.stderr.strip()[:400]}")


def _duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _speak(text: str, voice: str, dest: Path) -> Path:
    """One utterance, as a mono WAV at the transcriber's sample rate."""
    aiff = dest.with_suffix(".aiff")
    _run(["say", "-v", voice, "-o", str(aiff), text])
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff),
          "-ar", str(SAMPLE_RATE), "-ac", "1", str(dest)])
    aiff.unlink()
    return dest


def _silence(seconds: float, dest: Path) -> Path:
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
          "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono",
          "-t", f"{seconds:.3f}", str(dest)])
    return dest


def _concat(parts: list[Path], dest: Path, work: Path) -> Path:
    listing = work / f"{dest.stem}-parts.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in parts))
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
          "-i", str(listing), "-c", "copy", str(dest)])
    listing.unlink()
    return dest


def build(visit: dict, work: Path) -> Path:
    """Two mono tracks that are silent while the other side is talking."""
    rep_track: list[Path] = []
    cust_track: list[Path] = []

    for index, (speaker, text) in enumerate(visit["script"]):
        voice = REP_VOICE if speaker == "rep" else visit["customer_voice"]
        utterance = _speak(text, voice, work / f"{visit['visit_id']}-{index}.wav")
        hush = _silence(_duration(utterance), work / f"{visit['visit_id']}-{index}-q.wav")
        gap = _silence(GAP_SECONDS, work / f"{visit['visit_id']}-{index}-g.wav")

        if speaker == "rep":
            rep_track += [utterance, gap]
            cust_track += [hush, gap]
        else:
            rep_track += [hush, gap]
            cust_track += [utterance, gap]
        print(f"   {visit['visit_id']}  turn {index + 1:>2}  {speaker:<8} "
              f"{_duration(utterance):>5.1f}s")

    left = _concat(rep_track, work / f"{visit['visit_id']}-L.wav", work)
    right = _concat(cust_track, work / f"{visit['visit_id']}-R.wav", work)

    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / visit["recording"]
    # amerge, not join: two mono inputs become one two-channel stream with the
    # first input on the left.
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(left), "-i", str(right),
          "-filter_complex", "[0:a][1:a]amerge=inputs=2[a]", "-map", "[a]",
          "-ac", "2", "-ar", str(SAMPLE_RATE), str(dest)])

    # A mixdown for a person to listen to. The WAV is hard-panned because the
    # transcriber takes its speaker labels from the channels, which on
    # headphones puts each voice in one ear and is unpleasant to sit through.
    # Folding both to centre makes it play like a phone call. Nothing reads
    # this — it exists so the fixture can be reviewed by ear.
    listen = dest.with_suffix(".mp3")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(dest),
          "-filter_complex", "[0:a]pan=mono|c0=0.5*c0+0.5*c1,loudnorm[a]",
          "-map", "[a]", "-codec:a", "libmp3lame", "-b:a", "64k",
          "-ar", "22050", str(listen)])
    return dest


def main() -> None:
    for binary in ("say", "ffmpeg", "ffprobe"):
        if not shutil.which(binary):
            print(f"{binary} not found on PATH — cannot generate recordings.")
            raise SystemExit(1)

    work = ROOT / "data" / ".audio-work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    try:
        for visit in VISITS.values():
            print(f"\n{visit['visit_id']} — {visit['reason']}")
            dest = build(visit, work)
            print(f"   → {dest.relative_to(ROOT)}  "
                  f"{_duration(dest):.1f}s stereo")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print("\nDone. Recordings in", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
