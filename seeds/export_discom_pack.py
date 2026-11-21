"""Write the DISCOM agents as a catalog pack for the platform's Agent catalog.

    python seeds/export_discom_pack.py ~/agentic-platform/backend/app/catalog/packs/discom

The agents, their prompts and their tools are the ones `seeds/discom.py`
registers; the skills are `skills/*.md`, copied byte for byte. This script is
the only bridge, so the seed stays the one place they are written and the pack
cannot drift from it: change the seed or a skill, then run this again.

Tool addresses are written as paths. The platform joins them to the API
address a client gives when adding the agent, so the same pack reads the demo
tools here and a DISCOM's own API built to the same paths.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "seeds"))
sys.path.insert(0, str(ROOT))

import discom  # noqa: E402 — after the path is set

#: What the catalog card says. The seed has prompts, not listings.
LISTING: dict[str, tuple[str, str]] = {
    "outreach": (
        "Calls the consumers a theft screening flagged and works out what each conversation actually established, checked against the consumer's own meter readings.",
        "Queues and reviews outreach calls. Nothing said on an automated call is treated as evidence or an admission; a real dial needs the operator's explicit go-ahead.",
    ),
    "payment": (
        "Scores payment probability, flags defaulters early, recommends the recovery step (SMS → call → visit → disconnection), forecasts collection and plans campaigns.",
        "Six skills over the collection book: payment probability, early warning, recovery action ladder, monthly collection forecast, payment-behaviour segments and campaign optimisation.",
    ),
    "recovery": (
        "Ranks temporarily disconnected accounts by recoverable amount × probability of recovery, and builds the field plan within your teams' capacity.",
        "Uses dues, TD age, payments, meter status, site surveys, restoration history and notices to recommend field visit, notice, PD review or write-off review, with the evidence for each.",
    ),
    "theft": (
        "Screens metering and billing data for theft, tampering and bypass, and gives each consumer a risk score with the evidence behind it.",
        "Moves enforcement from random to intelligence-led inspection. Feeder loss alone is never treated as evidence against a consumer.",
    ),
    "survey": (
        "Reviews a field site survey — image detections, the OCR'd meter number and the surveyor's notes — and flags what contradicts your own records.",
        "Decides which of the vision service's detections are strong enough to act on, and cross-checks the meter number, reading and connection status with the DISCOM's data.",
    ),
    "restoration": (
        "Finds consumption that restarted after a disconnection without a restoration order, and turns the suspicious cases into inspection tasks.",
        "Correlates disconnection events, meter reads, restoration orders, payments and work orders, and rules out authorised restorations before flagging a case.",
    ),
    "complaint": (
        "Classifies, prioritises and routes complaints, spots repeats and escalation risk, predicts SLA breaches and drafts responses.",
        "Works from the complaint text with the consumer's billing, metering, outage and work-order history behind it.",
    ),
    "call": (
        "Reviews call-centre calls: intent, resolution, agent assist, quality, agent performance, unresolved calls and fraud or abuse screening.",
        "Also covers the voice bot's simple questions — what do I owe, when is my supply back, why did my bill go up — answered from the DISCOM's own systems.",
    ),
    "asset": (
        "Predicts distribution transformer and feeder failures from load, temperature and failure history, and plans preventive maintenance within crew capacity.",
        "Assets without telemetry are said to be unscored rather than scored low.",
    ),
    "forecast": (
        "Explains and checks demand forecasts from state down to feeder and DT, for procurement, peak demand and load management.",
        "Shows where an accurate-looking circle figure hides large feeder-level errors. It evaluates the forecasts your model produces; it does not produce them.",
    ),
    "copilot": (
        "An assistant for DISCOM staff: asks across consumers, collection, TD/PD, theft, complaints and assets, and writes the analysis or the monthly review.",
        "“TD consumers above ₹50,000 for more than 180 days”, “which divisions convert TD to PD best”, “why did recovery fall in Division X”.",
    ),
}


def main(out: Path) -> None:
    base = discom.DISCOM_API
    tools = []
    for t in discom.TOOLS:
        url = t["url_template"]
        if not url.startswith(base):
            raise SystemExit(f"{t['name']}: {url} is not under {base}")
        tools.append({
            "name": t["name"],
            "description": t["description"],
            "method": t["method"],
            "path": url[len(base):],
            "param_locations": t["param_locations"],
            "input_schema": t["input_schema"],
        })

    agents = []
    skills: set[str] = set()
    for key, name, tier, slugs, tool_names, prompt in discom.AGENTS:
        slugs = [slugs] if isinstance(slugs, str) else list(slugs)
        if key not in LISTING:
            raise SystemExit(f"No catalog listing written for agent '{key}'.")
        missing = [x for x in tool_names if x not in discom.TOOL_NAMES]
        if missing:
            raise SystemExit(f"{name}: unknown tools {missing}")
        summary, about = LISTING[key]
        agents.append({
            "key": key, "name": name, "tier": tier, "skills": slugs,
            "tools": list(tool_names), "prompt": prompt,
            "summary": summary, "about": about,
        })
        skills.update(slugs)

    (out / "skills").mkdir(parents=True, exist_ok=True)
    for old in (out / "skills").glob("*.md"):
        if old.stem not in skills:
            old.unlink()
    for slug in sorted(skills):
        shutil.copyfile(ROOT / "skills" / f"{slug}.md", out / "skills" / f"{slug}.md")

    pack = {
        "id": "discom",
        "title": "DISCOM",
        "api_path": "/discom",
        "source": "indicus-ai-mcp-tools: seeds/export_discom_pack.py — do not edit by hand",
        "tools": tools,
        "agents": agents,
    }
    (out / "pack.json").write_text(json.dumps(pack, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(agents)} agents, {len(skills)} skills, {len(tools)} tools → {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]).expanduser().resolve())
