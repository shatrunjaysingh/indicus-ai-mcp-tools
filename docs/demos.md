# Demo fixtures

Four stand-in systems, one per demo. Each plays the part of a customer's own
stack — the systems an analyst pivots between while working a single case. In a
real deployment these are the customer's systems, reached with their own
credentials; nothing here is persisted by the platform.

Every demo is built the same way: a FastAPI service holding the data, its
operations imported as custom tools, and agents composed over those tools. The
data in each is built so the pipeline can be demonstrated **both ways** — one
case that should escalate and one that should not, distinguishable only by
enriching the evidence, which is exactly the work being automated.

| Demo | Service | Port | Workspace | Reproducible from this repo? |
|---|---|---|---|---|
| Field visit review | `utility_api.py` | 8303 | Revenue Protection | **Yes** — one seed script |
| IAM access review | `iam_api.py` | 8302 | IAM Access Review | **Yes** — one seed script |
| Continuous access governance | `iam_api.py` | 8302 | Agentic IAM | Partly — needs an external skill suite |
| SOC alert response | `soc_api.py` | 8301 | Security Operations | **No** — hand-built, see below |
| Dental RCM / payer | `payer_api.py` | 8300 | Default | Partly — tools imported by hand |

## Before any demo

The platform must be running (`api` on 8000, `web` on 5173) with Postgres and
Redis up. Check everything at once on the **Service status** page (`/status`) —
it probes each demo service and names it from its own OpenAPI title, so a port
serving the wrong thing shows up as wrong rather than as healthy.

```bash
curl -s localhost:5173/status/health | python3 -m json.tool
```

A demo service that is down makes its agents fail at the enrichment step with a
connection error. That failure is honest — the agent should refuse to invent
telemetry rather than borrow indicators from an unrelated case — but it looks
like a broken demo, so check first.

---

## Field visit review — Meridian Utilities (port 8303)

An electricity supplier finds a discrepancy on an account, sends a
representative to the property, records the conversation, and has to decide:
system fault, or is the customer at fault?

`utility_api.py` stands in for the recording store, the billing platform, the
meter data management system, the field inspection record and the grid event
log.

| Operation | Path |
|---|---|
| `listVisits` | `GET /visits` |
| `getVisit` | `GET /visits/{visit_id}` |
| `transcribeVisitRecording` | `POST /visits/{visit_id}/transcript` |
| `getAccount` | `GET /accounts/{account_id}` |
| `getBillingHistory` | `GET /accounts/{account_id}/billing` |
| `getMeterReadings` | `GET /meters/{meter_id}/readings` |
| `getFieldInspection` | `GET /meters/{meter_id}/inspection` |
| `getGridEvents` | `GET /accounts/{account_id}/grid-events` |

### The two cases

**VISIT-4471 — the customer is at fault.** The seal is cut and re-seated with a
number that does not match the one issued, there is a hand-removable bridge
across the current coil, and consumption fell 58% the night the meter logged its
cover being opened with no work order on file.

**VISIT-4472 — the customer is not at fault.** Ten estimated bills at a flat
240kWh, a meter exchange whose closing read was never transferred, and the
resulting 1,500kWh of under-billing landing in a single month.

Both visits are company-initiated: screening flagged the account and a
representative was sent to rule out interference. Both customers protest. The
one who is *innocent* sounds worse — he interrupts, demands to be believed, and
resents being suspected in his own kitchen. That is the point. Judged on manner
alone he is the guilty one, which is the mistake the pipeline exists to avoid.

VISIT-4472's arithmetic reconciles exactly, and is meant to: real consumption
between the two actual reads (44,907 − 41,007 = 3,900kWh over ten periods) minus
the 2,400kWh billed as estimate gives a 1,500kWh catch-up; plus the 402kWh
genuinely used in April, that is the 1,902kWh billed. A review that cannot show
this sum has not done the work. **If you change these numbers, check they still
reconcile** — an earlier version did not, and the symptom was not a wrong answer
but a stuck one: the critic kept refusing an arithmetic the agent had no way to
close, and the stage looped until it was cancelled.

### Transcription is real

`transcribeVisitRecording` runs speech-to-text over the audio rather than
returning a stored script. Speakers come from the recording's two channels —
representative left, customer right — because Whisper does not diarise, and
inferring the speaker from the words would have the analysis guessing who
admitted what.

The transcripts contain genuine recognition errors ("bit of gravel for work" for
"bit of travel for work"), which is the point: a review that falls over on a
misheard word should be found out here rather than in production.

Needs `faster-whisper` in the backend venv and `ffmpeg` on PATH. The model
downloads on first use.

```bash
uv pip install --python backend/.venv/bin/python faster-whisper
```

### Generating the recordings

**The audio is not in version control.** `demo/data/` is gitignored, so a fresh
clone has no recordings and `transcribeVisitRecording` answers 503 until they
are generated. This is a deliberate trade — 19MB of WAV per clone, forever, to
save one command — but it means this step is required, not optional.

Needs macOS `say` and `ffmpeg`:

```bash
backend/.venv/bin/python demo/generate_visit_recordings.py
```

It writes two files per visit: `visit-NNNN.wav`, the hard-panned stereo the
pipeline transcribes, and `visit-NNNN.mp3`, a centred mixdown for listening to
the call yourself. Only the WAV is read by anything.

### Testing it

```bash
# 1. Start the service
backend/.venv/bin/uvicorn utility_api:app --app-dir demo --port 8303

# 2. Smoke-test the data before involving a model — this costs nothing
curl -s 127.0.0.1:8303/visits | python3 -m json.tool
curl -s 127.0.0.1:8303/accounts/ACC-31885/billing | python3 -m json.tool

# 3. Transcription, which takes ~20s the first time (model load)
curl -s -X POST 127.0.0.1:8303/visits/VISIT-4471/transcript \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['text'][:600])"

# 4. Build the workspace, agents and pipeline. Free — no model calls.
backend/.venv/bin/python backend/scripts/utility_demo_seed.py
```

Then run the **Field Visit Review** pipeline with `VISIT-4471` or `VISIT-4472`
as its input.

**What good looks like.** VISIT-4471 returns `VERDICT: CUSTOMER_AT_FAULT`
resting on the seal and the shunt, with the behavioural signals explicitly
labelled as corroboration and a recommended action of
`ESCALATE_REVENUE_PROTECTION` that states it authorises neither disconnection
nor a finding of criminal intent. VISIT-4472 should return `NO_CUSTOMER_FAULT`
with the catch-up arithmetic shown.

**Cost and duration.** Roughly **$0.21 and 2 minutes** with the agents as
seeded (Sonnet, `simple` execution). The same pipeline with `deep` agents cost
$1.36 and took 12 minutes for the same verdict — the plan/critic/retry loop
tripled the token count without changing the finding.

### Listening to a call

The WAV is hard-panned by design, so on headphones each voice arrives in one ear
only. Play the `.mp3` instead — same call, both speakers centred. With the API
running you can also stream a visit from it:

```
http://127.0.0.1:8303/visits/VISIT-4471/audio
```

That route is excluded from the OpenAPI schema on purpose: it exists for a
person, and importing it as a tool would let an agent pull two minutes of audio
into a context window that cannot hear it.

Worth doing once before demoing. VISIT-4472 is the useful listen.

---

## IAM access review (port 8302)

`iam_api.py` stands in for an identity governance stack: certification scope and
campaign progress, entitlement quality, uncorrelated accounts, terminated
identities still holding access, SME pre-validation, post-certification
remediation, service account inventory and Secret Server vault records.

It backs **two separate demos** over the same service.

### IAM Access Review — the scripted one

```bash
backend/.venv/bin/uvicorn iam_api:app --app-dir demo --port 8302
backend/.venv/bin/python backend/scripts/iam_demo_seed.py
```

Builds the **IAM Access Review** workspace and its pipeline of the same name.

Smoke-test the service first — all free:

```bash
curl -s 127.0.0.1:8302/summary | python3 -m json.tool
curl -s 127.0.0.1:8302/readiness/scope | python3 -m json.tool | head -30
curl -s 127.0.0.1:8302/certifications/CERT-2026-Q2/progress | python3 -m json.tool
curl -s "127.0.0.1:8302/sar/accounts/lookup?account_names=svc_jira_eng_0007" | python3 -m json.tool
```

### Agentic IAM — needs an external skill suite

`backend/scripts/agentic_iam_seed.py` builds the **Agentic IAM** workspace and
the *Continuous Access Governance* pipeline, but it reads its skills from:

```
~/Downloads/agentic-iam-skills-v1.0.0/skills
```

That path is outside the repo, so this seed **will not run on a machine that
does not have the suite**. It prints `skill suite not found` and stops rather
than building half a workspace. If you need this demo elsewhere, copy the suite
there first, or vendor it into `demo/skills/` and change `SUITE`.

### Known state

Port 8302 has no launchd agent, unlike the payer service, so it is frequently
not running. If IAM agents fail with connection errors, that is why. Start it
before demoing anything IAM.

---

## SOC alert response (port 8301)

`soc_api.py` plays the SIEM, the threat-intel platform, the asset inventory and
the identity provider — the four systems an analyst pivots between while working
one alert.

| Operation | Path |
|---|---|
| `getAlert` | `GET /alerts/{alert_id}` |
| `listAlerts` | `GET /alerts` |
| `getIndicatorReputation` | `GET /ioc/{indicator}` |
| `getAsset` | `GET /assets/{hostname}` |
| `getIdentity` | `GET /identity/{username}` |

### The two cases

Both fire the *same detection rule* — "Encoded PowerShell spawned by Office
process" — and can only be told apart by enriching the indicators.

**ALT-2291 — a genuine intrusion.** `FIN-WS-0447`, user `m.okafor`. Word spawns
encoded PowerShell that decodes to a download from `185.220.101.44`, followed by
8.8MB outbound. Should be contained.

**ALT-2288 — a false positive.** `IT-ADM-0012`, service account `svc_sccm`. The
SCCM agent spawns encoded PowerShell that decodes to
`Get-WmiObject -Class Win32_QuickFixEngineering` — a patch-inventory query — with
one connection to `10.14.2.31:8530`, the internal WSUS port. Should be **tuned
out, not escalated**.

If a run recommends containment on ALT-2288, that is a genuine finding about the
pipeline's judgement rather than an infrastructure problem.

### Testing it

```bash
backend/.venv/bin/uvicorn soc_api:app --app-dir demo --port 8301

curl -s 127.0.0.1:8301/alerts/ALT-2288 | python3 -m json.tool
curl -s 127.0.0.1:8301/ioc/185.220.101.44 | python3 -m json.tool
curl -s 127.0.0.1:8301/assets/FIN-WS-0447 | python3 -m json.tool
```

Then run the **SOC Alert Response** pipeline in the **Security Operations**
workspace with `ALT-2291` or `ALT-2288`.

### Not reproducible from this repo

Only `soc_api.py` is in version control. The Security Operations workspace, its
four agents (Alert Triage, IOC Enrichment, Incident Response, Detection Tuning)
and the SOC Alert Response pipeline were **built by hand through the UI**, and
the tools were imported from the OpenAPI spec rather than registered by a
script. There is no `soc_demo_seed.py`.

On this machine that work already exists in the database. On a fresh install it
does not, and rebuilding it means repeating the UI steps from memory. If this
demo matters, it needs a seed script of its own — `utility_demo_seed.py` is the
pattern to copy.

---

## Dental RCM / payer API (port 8300)

`payer_api.py` stands in for a dental practice's management system: claims with
real CARC/RARC codes, and benefit summaries with waiting periods and frequency
limits. The demo agents reach it through a custom tool imported from its OpenAPI
spec, which is the same path a client would use to connect their own system.

| Operation | Path |
|---|---|
| `getClaim` | `GET /claims/{claim_id}` |
| `listClaims` | `GET /claims?status=&min_age_days=` |
| `getEligibility` | `GET /eligibility/{member_id}` |

Claims worth demoing: `CLM-88421` (prior auth missing, and a waiting period
underneath it), `CLM-88503` (frequency limit — the right answer is to bill the
patient, not appeal), `CLM-88710` (paid, with a contractual adjustment).

### Testing it

It starts automatically at login via a launchd agent on macOS:

```bash
demo/install-payer-agent.sh      # install and start
demo/install-payer-agent.sh -u   # stop and remove
```

Or by hand:

```bash
backend/.venv/bin/uvicorn payer_api:app --app-dir demo --port 8300

curl -s 127.0.0.1:8300/claims/CLM-88421 | python3 -m json.tool
curl -s "127.0.0.1:8300/claims?status=denied" | python3 -m json.tool
```

Under Docker Compose it comes up with everything else, as the `payer` service —
the only demo service that does.

Its tools live in the **Default** workspace rather than one of its own.

### Re-importing the tools

If the custom tools are ever cleared, re-import them from the spec at
`http://127.0.0.1:8300/openapi.json`. The importer needs an explicit base URL —
FastAPI does not emit a `servers` block — and the tools should be pinned to
`allowed_hosts: ["127.0.0.1"]`.

---

## If a fresh clone must work without generating audio

The field-visit audio could be tracked instead, by committing a **stereo** MP3 as
the pipeline's input: roughly 1.2MB per visit against 9.4MB of WAV, small enough
for version control, and Whisper decodes MP3 without complaint.

Two conditions, both easy to get wrong:

- It must keep the channel separation. The `.mp3` written today is the mono
  mixdown, and transcribing that would collapse the two speakers into one track
  — the labels would then be inferred from the words, which is the failure the
  split channels exist to prevent.
- Transcription quality should be re-checked at whatever bitrate is chosen.
  Lossy compression is unlikely to matter at speech bitrates, but the review
  turns on meter numbers and dates, and "unlikely to matter" is not a
  measurement.

Not done, because the generation step is one command and 19MB in the history is
permanent.

---

## Ports, in one place

The port a service runs on must match the `url_template` on its registered
custom tools. If they disagree, the status page reports a healthy service that
no agent can reach — and the agents fail at enrichment with a connection error.

| Port | Service | Started by |
|---|---|---|
| 8300 | Payer | launchd agent, or Docker Compose |
| 8301 | SOC | by hand |
| 8302 | IAM | by hand |
| 8303 | Utilities | by hand |
