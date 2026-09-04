# Setting up outbound calling

Three configurations, same code. The provider is chosen by an environment
variable and nothing else changes.

    OUTREACH_PROVIDER        loopback | twilio | exotel      (default loopback)
    OUTREACH_PUBLIC_URL      where the provider can reach this service
    OUTREACH_TEST_NUMBER     pin every call to this number
    OUTREACH_ALLOW_LIVE      "true" to permit dialling real consumers
    OUTREACH_MAX_CONCURRENT  simultaneous calls              (default 3)
    OUTREACH_MAX_ATTEMPTS    retries on no-answer            (default 2)
    OUTREACH_WINDOW          calling window                  (default 09:00-21:00)
    OUTREACH_TIMEZONE        (default Asia/Kolkata)

`GET /discom/outreach/config` reports the active configuration and everything
blocking a campaign, all at once rather than one failure at a time.

## The guard you should not remove

Until `OUTREACH_ALLOW_LIVE=true` is set explicitly, **every call in every
campaign goes to `OUTREACH_TEST_NUMBER`**, whatever the rule selected.

The failure being guarded against is not exotic. A rule matches 13,195
accounts, someone runs it against a provider that works, and the utility has
auto-dialled a five-figure number of consumers about suspected electricity
theft. There is no undo. Opting in costs one variable.

## 1. Local, no telephony account — works today

    OUTREACH_PROVIDER=loopback
    OUTREACH_TEST_NUMBER=+919999900000

    .venv-audio/bin/uvicorn mcp_server:app --port 8304

Loopback is not a mock. It drives the real state machine through the real
webhook handlers, renders each consumer answer to speech, and runs it through
the same Whisper path a provider recording takes. Queueing, turn sequencing,
consent detection, retries, transcription and analysis all execute. The only
absent thing is the phone network.

    curl -XPOST '.../outreach/campaign/queue?rule=meter_test&limit=4'
    curl -XPOST '.../outreach/campaign/release'
    curl '.../outreach/live'

**Interpreter:** use `.venv-audio` (3.11). `ctranslate2` and `onnxruntime` have
no 3.14 wheel, and 3.11 is what the Dockerfile builds on, so this is also the
environment that matches production.

## 2. Real calls, demoing from the USA

Twilio, a US number, and a tunnel. Nothing about this touches Indian telecom
regulation, because nobody in this configuration is calling India.

**Get a number.** Twilio console -> Phone Numbers -> Buy a number, any US
local number with Voice. A trial account is enough to start; see the caveats
below.

**Expose the service.** The provider has to reach your laptop:

    cloudflared tunnel --url http://localhost:8304

It prints an `https://<something>.trycloudflare.com` hostname. That is
`OUTREACH_PUBLIC_URL`. It changes every restart, so set it each time.

**Configure:**

    export OUTREACH_PROVIDER=twilio
    export OUTREACH_PUBLIC_URL=https://<the-tunnel-hostname>
    export OUTREACH_TEST_NUMBER=+1<your own mobile>
    export OUTREACH_TIMEZONE=America/New_York
    export TWILIO_ACCOUNT_SID=AC...
    export TWILIO_AUTH_TOKEN=...
    export TWILIO_FROM_NUMBER=+1...

    .venv-audio/bin/uvicorn mcp_server:app --port 8304

**Check before you present, not during:**

    curl .../discom/outreach/config/verify

That asks Twilio whether the credentials work, whether the from-number really
belongs to the account, and — on a trial — which numbers are verified. Those
are the three things that otherwise surface half a minute before a call that
was supposed to work.

**The timezone matters.** The default calling window is 09:00-21:00 IST, which
is the right constraint for Indian consumers and is usually *shut* during US
business hours. Set `OUTREACH_TIMEZONE` to a US zone and the window opens to
the full day, because the legal restriction attaches to who is being called.
Get this wrong and `release` refuses to dial in front of the audience.

**Trial account caveats.** A trial can only call numbers you have verified in
the console, and Twilio speaks its own trial announcement before your first
prompt. Both go away on upgrade, which is about $20. For a demo where the call
lands on your own phone, a trial is fine — just verify the number first, and
expect the preamble.

**Speech recognition.** `OUTREACH_STT=provider` (the default) has Twilio
recognise each answer and post the text inline, so the next question follows in
about a second. `OUTREACH_STT=whisper` downloads each answer and transcribes it
here — more accurate on accented English, and four to six seconds of silence
per turn. Use `provider` for a live demo and `whisper` when the transcript
matters more than the pacing. The full call is recorded either way.

**Run it:**

    curl -XPOST '.../outreach/campaign/queue?rule=meter_test&limit=1'
    curl -XPOST '.../outreach/campaign/release'

Your phone rings. Answer it and the agent works through the questions that
consumer's fired signals produced. `OUTREACH_ALLOW_LIVE` stays unset, so every
call lands on your number no matter which consumers the rule selected.

## 3. Local, real calls to your own phone (India)

A provider has to reach your laptop, so you need a public URL:

    cloudflared tunnel --url http://localhost:8304

Then:

    OUTREACH_PROVIDER=twilio
    OUTREACH_PUBLIC_URL=https://<the-tunnel-hostname>
    OUTREACH_TEST_NUMBER=+91<your own verified number>
    TWILIO_ACCOUNT_SID=...
    TWILIO_AUTH_TOKEN=...
    TWILIO_FROM_NUMBER=+1...

A Twilio trial account dials verified numbers, which is enough to hear the
whole loop before anyone starts a procurement conversation. `OUTREACH_ALLOW_LIVE`
stays unset, so every call still lands on your phone regardless of which
consumers the rule picked.

## 4. Deployed

Caddy already routes a public hostname to this service, so webhooks land
directly and no tunnel is involved:

    OUTREACH_PROVIDER=exotel
    OUTREACH_PUBLIC_URL=https://<the deployment hostname>
    EXOTEL_SID / EXOTEL_TOKEN / EXOTEL_CALLER_ID / EXOTEL_SUBDOMAIN

Leave `OUTREACH_ALLOW_LIVE` unset until the client has agreed which consumers
are being called and the caller ID is the DISCOM's own.

**The Exotel adapter has not been run against a live account.** It is written
from the documented call flow, and the first real call should be treated as a
debugging session rather than a demonstration. The Twilio adapter is the one to
prove the path with.

## Before dialling Indian consumers

- **DLT registration** and an approved header, per TRAI TCCCPR 2018
- **Caller ID** that belongs to the DISCOM, not to a vendor
- **Calling window** 09:00-21:00 IST — enforced in code, not just documented
- **Recording disclosure** and **automated-system disclosure**, both in the
  opening line. They are there now and must not be trimmed for call time.
- **DPDP Act 2023**: the stated purpose has to be the actual purpose
- **Indic ASR.** Transcription runs `base.en`. Consumers will answer in Marathi
  and Hindi, and an English-only model does not fail loudly — it returns
  fluent, confident, wrong English and every layer above it believes the words.
  This is the largest gap between this pipeline and a production one.

## How a call runs

Turn-based: the provider speaks a prompt, records the reply, posts it back, and
the next prompt is returned. The questions come from `plan()`, which derives
them from the signals that fired on that account, so no two consumers are asked
the same set.

The agent's words are never transcribed — we wrote them. Only the consumer's
answers go through recognition, one per turn, already attributed. There is no
diarisation step to get wrong, so a recognition error cannot move a sentence
from one party to the other.
