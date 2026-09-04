"""Generate the outbound consumer calls: audio, transcripts, analysis.

    .venv-audio/bin/python services/generate_outreach_calls.py --rule meter_test --limit 10

Offline, like `generate_visit_recordings.py`, and for the same reason: this
renders speech, mixes two channels and runs Whisper over both, which is minutes
of CPU for ten calls. Nothing that slow belongs inside a request a tool call is
waiting on. The API serves what this writes and answers with this command when
a campaign has not been generated.

INTERPRETER
-----------
Needs faster-whisper, which needs ctranslate2 and onnxruntime. Neither has a
wheel for Python 3.14, so the repo's main `.venv` cannot run this. `.venv-audio`
is a 3.11 environment for exactly this — the same 3.11 the Dockerfile builds on,
so what runs here is what runs in the image.

Output goes to `services/_outreach_cache.json` and `services/data/outreach/`.
The audio is not in version control.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audio  # noqa: E402
import discom_outreach as outreach  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rule", default="meter_test",
                    help=f"one of {sorted(outreach.RULES)}")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--consumers", default="",
                    help="comma-separated consumer numbers, overrides --rule")
    args = ap.parse_args()

    missing = audio.have_tools()
    if missing:
        print(f"{missing} is not on PATH — cannot generate call audio.")
        return 1
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        print("faster-whisper is not installed in this interpreter.")
        print("Use the 3.11 environment:")
        print("  .venv-audio/bin/python services/generate_outreach_calls.py")
        return 1

    nos = [x.strip() for x in args.consumers.split(",") if x.strip()] or None
    if nos:
        print(f"Calling {len(nos)} named consumers")
    else:
        meaning = outreach.RULES[args.rule][1]
        print(f"Rule {args.rule!r}, up to {args.limit} consumers")
        print(f"  {meaning}\n")

    result = outreach.generate_campaign(
        rule=args.rule, limit=args.limit, consumer_nos=nos, progress=True)

    s = result["summary"]
    print(f"\n{result['called']} calls placed.")
    print(f"  completed             {s['completed']}")
    print(f"  refused consent       {s['refused_consent']}")
    print(f"  diverted from a visit {s['diverted_from_inspection']}")
    print(f"  analysis defensible   {s['analysis_agreed_with_ground_truth']}")
    print("\n  by disposition:")
    for k, v in sorted(s["by_disposition"].items(), key=lambda kv: -kv[1]):
        print(f"    {k:<32} {v}")
    print(f"\nAudio in {outreach.RECORDINGS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
