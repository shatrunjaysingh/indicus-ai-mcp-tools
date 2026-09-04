"""Configuration for outbound calling.

Everything that differs between a laptop, a demo box and a client pilot lives
here and is read from the environment. Changing provider is a variable, not an
edit: the runtime asks this module what to use and never names a vendor.

    OUTREACH_PROVIDER        loopback | twilio | exotel      (default loopback)
    OUTREACH_PUBLIC_URL      where the provider can reach us
    OUTREACH_TEST_NUMBER     pin every call to this number   (default: set)
    OUTREACH_ALLOW_LIVE      "true" to permit dialling real consumers
    OUTREACH_MAX_CONCURRENT  simultaneous calls              (default 3)
    OUTREACH_WINDOW          local calling window            (default 09:00-21:00)
    OUTREACH_TIMEZONE        (default Asia/Kolkata)
    OUTREACH_MAX_ATTEMPTS    retries on no-answer            (default 2)
    OUTREACH_STT             provider | whisper              (default provider)

THE TEST NUMBER IS ON BY DEFAULT
--------------------------------
`OUTREACH_TEST_NUMBER` pins every call in every campaign to one number, and
until `OUTREACH_ALLOW_LIVE=true` is set explicitly, a campaign that would dial
consumer numbers refuses to start.

This is deliberate and it should stay. The failure mode being guarded against
is not subtle: a rule selects 13,195 accounts, someone runs it against a
provider that actually works, and the utility has auto-dialled a five-figure
number of consumers about suspected theft. There is no undo for that, and no
apology that fixes it. Opting *in* to live dialling costs one variable; opting
out after the fact costs the client their consumers' trust.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _bool(key: str, default: bool = False) -> bool:
    raw = _env(key).lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _int(key: str, default: int) -> int:
    try:
        return int(_env(key) or default)
    except ValueError:
        return default


@dataclass
class ProviderSettings:
    """Credentials and identity for one vendor. Absent values are reported."""

    name: str
    required: tuple[str, ...]
    values: dict[str, str] = field(default_factory=dict)

    @property
    def missing(self) -> list[str]:
        return [k for k in self.required if not self.values.get(k)]

    @property
    def configured(self) -> bool:
        return not self.missing


# Declared rather than coded, so adding a vendor is a table entry plus an
# adapter. The runtime never reads these directly — it asks for the active one.
PROVIDER_KEYS: dict[str, tuple[str, ...]] = {
    "loopback": (),
    "twilio": ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"),
    # Same credentials, no inbound connection. See TwilioInlineProvider.
    "twilio-inline": ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
                      "TWILIO_FROM_NUMBER"),
    "exotel": ("EXOTEL_SID", "EXOTEL_TOKEN", "EXOTEL_CALLER_ID",
               "EXOTEL_SUBDOMAIN"),
}


@dataclass
class OutreachConfig:
    provider: str
    public_url: str
    test_number: str
    allow_live: bool
    max_concurrent: int
    max_attempts: int
    stt: str
    window_start: time
    window_end: time
    timezone: str
    settings: ProviderSettings

    # ---- what the runtime asks --------------------------------------------

    def number_for(self, consumer_no: str, registered: str | None) -> str:
        """The number to actually dial for this consumer.

        Returns the test number unless live dialling was explicitly enabled.
        Called for every single call, so the guard cannot be bypassed by a code
        path that forgot to check it.
        """
        if not self.allow_live:
            return self.test_number
        if not registered:
            raise ValueError(
                f"{consumer_no} has no registered number and live dialling is "
                f"on. Refusing to guess.")
        return registered

    def within_window(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(ZoneInfo(self.timezone))
        return self.window_start <= now.timetz().replace(tzinfo=None) <= self.window_end

    def next_window_open(self, now: datetime | None = None) -> datetime:
        now = now or datetime.now(ZoneInfo(self.timezone))
        today = now.replace(hour=self.window_start.hour,
                            minute=self.window_start.minute,
                            second=0, microsecond=0)
        # timedelta, not day+1: on the 31st that raised, so a campaign queued
        # after hours on a month end failed instead of waiting.
        return today if now < today else today + timedelta(days=1)

    def webhook(self, path: str) -> str:
        return f"{self.public_url.rstrip('/')}/discom/outreach/voice/{path.lstrip('/')}"

    def blocking_problems(self) -> list[str]:
        """Everything that would stop a campaign, in one list.

        Collected rather than raised one at a time: an operator setting this up
        should see all four things they are missing at once, not discover them
        across four attempts.
        """
        problems: list[str] = []
        if self.provider not in PROVIDER_KEYS:
            problems.append(
                f"OUTREACH_PROVIDER={self.provider!r} is not one of "
                f"{', '.join(sorted(PROVIDER_KEYS))}")
            return problems
        if self.settings.missing:
            problems.append(
                f"{self.provider} needs {', '.join(self.settings.missing)}")
        if self.provider not in ("loopback", "twilio-inline"):
            if not self.public_url:
                problems.append(
                    "OUTREACH_PUBLIC_URL is unset. The provider calls back into "
                    "this service, so it needs a URL it can reach — a tunnel "
                    "locally (cloudflared/ngrok), the Caddy hostname when "
                    "deployed.")
            elif self.public_url.startswith("http://") and \
                    "localhost" not in self.public_url and \
                    "127.0.0.1" not in self.public_url:
                problems.append(
                    f"OUTREACH_PUBLIC_URL is plain http ({self.public_url}). "
                    f"Providers require https for webhooks.")
        if self.allow_live and self.provider == "twilio-inline":
            problems.append(
                "twilio-inline cannot end a call when the consumer declines — "
                "the script is fixed before dialling and nothing calls back to "
                "branch on. That is fine for your own phone and not fine for a "
                "consumer. Use OUTREACH_PROVIDER=twilio for live dialling.")
        if self.allow_live and self.provider == "loopback":
            problems.append(
                "OUTREACH_ALLOW_LIVE is on but the provider is loopback, which "
                "does not dial. One of the two is not what you meant.")
        if not self.allow_live and not self.test_number:
            problems.append(
                "OUTREACH_TEST_NUMBER is unset and live dialling is off, so "
                "there is no number to call.")
        return problems

    def describe(self) -> dict:
        """The active configuration, for an operator and for the API."""
        return {
            "provider": self.provider,
            "provider_configured": self.settings.configured,
            "missing_credentials": self.settings.missing,
            "public_url": self.public_url or "(unset)",
            "dialling": "LIVE — real consumer numbers" if self.allow_live
                        else f"TEST — every call pinned to {self.test_number}",
            "calling_window": f"{self.window_start:%H:%M}-{self.window_end:%H:%M} "
                              f"{self.timezone}",
            "in_window_now": self.within_window(),
            "max_concurrent": self.max_concurrent,
            "max_attempts": self.max_attempts,
            "speech_recognition": (
                "provider — the vendor returns text inline, no download"
                if self.stt == "provider" else
                "whisper — each answer is downloaded and transcribed here"),
            "blocking_problems": self.blocking_problems(),
        }


def _parse_window(raw: str) -> tuple[time, time]:
    try:
        start, end = raw.split("-")
        sh, sm = (int(x) for x in start.split(":"))
        eh, em = (int(x) for x in end.split(":"))
        return time(sh, sm), time(eh, em)
    except (ValueError, AttributeError):
        # TCCCPR 2018 permits transactional calling 09:00-21:00. A malformed
        # override falls back to the legal window rather than to no window.
        return time(9, 0), time(21, 0)


def load() -> OutreachConfig:
    provider = (_env("OUTREACH_PROVIDER") or "loopback").lower()
    keys = PROVIDER_KEYS.get(provider, ())
    tz = _env("OUTREACH_TIMEZONE", "Asia/Kolkata")
    # 09:00-21:00 is the TCCCPR window and the right default for calling Indian
    # consumers. It is the wrong default for a demo dialling a US number from a
    # US timezone, where it is frequently shut — and the failure shows up as a
    # refusal to dial, mid-demonstration. Outside India the window opens up
    # unless it was set deliberately; the legal constraint attaches to who is
    # being called, and nobody in this configuration is calling India.
    default_window = "09:00-21:00" if tz.startswith("Asia/") else "00:00-23:59"
    start, end = _parse_window(_env("OUTREACH_WINDOW", default_window))
    return OutreachConfig(
        provider=provider,
        public_url=_env("OUTREACH_PUBLIC_URL"),
        test_number=_env("OUTREACH_TEST_NUMBER"),
        allow_live=_bool("OUTREACH_ALLOW_LIVE", False),
        max_concurrent=_int("OUTREACH_MAX_CONCURRENT", 3),
        max_attempts=_int("OUTREACH_MAX_ATTEMPTS", 2),
        stt=(_env("OUTREACH_STT") or "provider").lower(),
        window_start=start, window_end=end,
        timezone=tz,
        settings=ProviderSettings(
            name=provider, required=keys,
            values={k: _env(k) for k in keys}),
    )
