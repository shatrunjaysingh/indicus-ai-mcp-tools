"""Shared pieces of the sample client systems: pretend businesses whose
back-office APIs IndicusAI reaches through data connectors and the agent
catalog's standard actions, the way it would reach a real client's — so
connectors and catalog agents are built and tested without a client, and
nothing a customer owns is ever uploaded to IndicusAI.

    /shop      Kettle & Co, an online store, incl. cash on delivery and failed
               deliveries                              (sample_shop_api.py)
    /miso      Miso, a second store on the same API    (sample_shop_api.py)
    /power     Brightline Power, an electricity utility (sample_power_api.py)
    /service   FixRight Service, appliance & battery service (sample_service_api.py)
    /lender    Sahyog Finance, loans, EMIs and KYC      (sample_lender_api.py)
    /insurer   Suraksha Insurance, policy renewals      (sample_insurer_api.py)
    /clinic    CarePoint Clinics, appointments          (sample_clinic_api.py)
    /crm       LeadDesk CRM, leads, tickets, feedback   (sample_crm_api.py)
    /hiring    Kaam Staffing, applicants and interviews (sample_hiring_api.py)

The full route and field list, for writing mapping presets, is
docs/SAMPLE-CATALOG-SYSTEMS.md.

Each is protected by an API key in the `X-Api-Key` header, as most clients'
APIs are. The key is `SAMPLE_CLIENT_API_KEY` (a test value, never a real
secret); blank turns the check off for local poking with curl.

The data is synthetic and dated relative to today, so a "due tomorrow" bill
stays due tomorrow. /power and /service keep changes in memory until a
restart. The stores and the catalog businesses (/lender, /insurer, /clinic,
/crm, /hiring) are test data a tester changes from Swagger — add a record on their own
mobile, edit any record, POST /reset — saved under SAMPLE_STATE_DIR
(state/<name>.json, see TestData) so a restart keeps them until a reset.

The same customers appear across the businesses, so one test person can be
tried against every one (language is a BCP-47 code, as a dialler wants it):

    +919000000999  Asha Rao             Bengaluru 560001   en-IN
    +919000000111  Ravi Sen             Kolkata 700001     en-IN
    +919000000222  Meera Iyer           Chennai 600001     ta-IN
    +919000000333  Arjun Mehta          Mumbai 400001      hi-IN
    +919000000444  Sunita Sharma        Delhi 110001       hi-IN   (EXTRA_PEOPLE)
    +919000000555  Karthik Subramanian  Coimbatore 641001  ta-IN   (EXTRA_PEOPLE)
    +919000000666  Pooja Verma          Jaipur 302001      hi-IN   (EXTRA_PEOPLE)
"""

from __future__ import annotations

import copy
import hmac
import html
import json
import logging
import os
import re
from collections.abc import Callable
from contextvars import ContextVar
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

PEOPLE = [
    {"name": "Asha Rao", "phone": "+919000000999", "email": "asha.rao@example.com",
     "city": "Bengaluru", "pincode": "560001", "address": "14 MG Road, Bengaluru 560001",
     "language": "en-IN"},
    {"name": "Ravi Sen", "phone": "+919000000111", "email": "ravi.sen@example.com",
     "city": "Kolkata", "pincode": "700001", "address": "8 Park Street, Kolkata 700001",
     "language": "en-IN"},
    {"name": "Meera Iyer", "phone": "+919000000222", "email": "meera.iyer@example.com",
     "city": "Chennai", "pincode": "600001", "address": "22 Anna Salai, Chennai 600001",
     "language": "ta-IN"},
    {"name": "Arjun Mehta", "phone": "+919000000333", "email": "arjun.mehta@example.com",
     "city": "Mumbai", "pincode": "400001", "address": "5 Marine Drive, Mumbai 400001",
     "language": "hi-IN"},
]
#: Three more, for the catalog businesses: Hindi and Tamil speakers, so a
#: campaign has more than one language to route. Not in the original three
#: businesses' seeds, which index PEOPLE by position.
EXTRA_PEOPLE = [
    {"name": "Sunita Sharma", "phone": "+919000000444", "email": "sunita.sharma@example.com",
     "city": "Delhi", "pincode": "110001", "address": "31 Janpath, New Delhi 110001",
     "language": "hi-IN"},
    {"name": "Karthik Subramanian", "phone": "+919000000555", "email": "karthik.s@example.com",
     "city": "Coimbatore", "pincode": "641001", "address": "9 Avinashi Road, Coimbatore 641001",
     "language": "ta-IN"},
    {"name": "Pooja Verma", "phone": "+919000000666", "email": "pooja.verma@example.com",
     "city": "Jaipur", "pincode": "302001", "address": "12 MI Road, Jaipur 302001",
     "language": "hi-IN"},
]
ALL_PEOPLE = PEOPLE + EXTRA_PEOPLE


def today() -> date:
    return datetime.now(IST).date()


def day(offset: int) -> str:
    return (today() + timedelta(days=offset)).isoformat()


def now_iso() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def clean_phone(raw: str | None) -> str:
    """Any common way of writing an Indian mobile → +91XXXXXXXXXX."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        return "+91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits
    return "+" + digits if digits else ""


#: Declared as a security scheme, so the OpenAPI spec says "an API key in
#: X-Api-Key" rather than listing it as an input every operation asks for — an
#: importer then treats it as a stored credential, never something to fill in.
API_KEY = APIKeyHeader(name="X-Api-Key", auto_error=False, description="The client's API key")


def require_key(x_api_key: str | None = Security(API_KEY)) -> None:
    """The client's API key check. A FastAPI dependency on every route."""
    expected = os.environ.get("SAMPLE_CLIENT_API_KEY", "sample-client-key")
    if not expected:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(401, "Send the API key in the X-Api-Key header.")


def valid_mobile(raw: str | None) -> str:
    """clean_phone, refusing anything that is not a whole mobile number.

    An Indian mobile (10 digits, +91 optional) or any other country's number
    written with its + and country code (+18572227021) — a tester abroad needs
    an order on their own number. A bare 10-digit number is read as Indian.
    """
    phone = clean_phone(raw)
    indian = len(phone) == 13 and phone.startswith("+91")
    other = (raw or "").strip().startswith("+") and not phone.startswith("+91") and 9 <= len(phone) <= 16
    if not (indian or other):
        raise HTTPException(
            422, "Give a 10-digit Indian mobile (+918826889512), or another country's with + and its code (+18572227021)."
        )
    return phone


# ---- test data saved across restarts -------------------------------------------

STATE_DIR = Path(os.environ.get("SAMPLE_STATE_DIR", Path(__file__).resolve().parent.parent / "state"))


class TestData:
    """One business's editable test data: named tables (dicts of records),
    built by `seed`, saved to SAMPLE_STATE_DIR/<slug>.json after each change
    and loaded from there on start, until reset() goes back to the seed.

    Tables are changed in place, so a handler can hold `DB["loans"]`.
    """

    def __init__(self, slug: str, seed: Callable[[], dict[str, dict]]):
        self.slug, self.seed = slug, seed
        self.path = STATE_DIR / f"{slug}.json"
        self.tables: dict[str, dict] = seed()
        if self.path.exists():
            try:
                saved = json.loads(self.path.read_text())
                for name in self.tables:
                    if name in saved:
                        self.tables[name] = saved[name]
            except ValueError as exc:
                logger.warning("%s: saved test data unreadable, using the original: %s", slug, exc)

    def __getitem__(self, name: str) -> dict:
        return self.tables[name]

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.tables, ensure_ascii=False))
            tmp.replace(self.path)
        except OSError as exc:  # read-only disk: the change still holds until a restart
            logger.warning("%s: could not save test data: %s", self.slug, exc)

    def reset(self) -> dict:
        fresh = self.seed()
        for name, table in fresh.items():
            self.tables.setdefault(name, {})
            self.tables[name].clear()
            self.tables[name].update(copy.deepcopy(table))
        if self.path.exists():
            self.path.unlink()
        return {"message": "Back to the original test data.", **{n: len(t) for n, t in self.tables.items()}}

    def next_id(self, table: str, prefix: str, start: int) -> str:
        n = start + len(self.tables[table])
        while f"{prefix}{n}" in self.tables[table]:
            n += 1
        return f"{prefix}{n}"


# ---- links a customer opens: payment pages and the like ------------------------

_ORIGIN: ContextVar[str | None] = ContextVar("sample_origin", default=None)


async def remember_origin(request: Request) -> None:
    """A router dependency: note the address this business was reached at, so a
    link it hands out (a payment page) points back at itself. Async so it runs
    in the request's own context, which the sync handler's thread inherits."""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    root = request.scope.get("root_path", "")
    _ORIGIN.set(f"{host}{root}")


def public_url(slug: str, path: str) -> str:
    """https://<where this business is reached>/<path>. Over REST that is the
    request's own host (or X-Forwarded-Host); over MCP there is no request, so
    SAMPLE_PUBLIC_URL or PUBLIC_BASE_URL (the origin, without the /<slug>).
    Always https, as a payment link sent by SMS must be — locally, open the
    same path over http."""
    origin = _ORIGIN.get()
    if not origin:
        base = os.environ.get("SAMPLE_PUBLIC_URL") or os.environ.get("PUBLIC_BASE_URL") or "localhost:8304"
        origin = re.sub(r"^\w+://", "", base).rstrip("/") + f"/{slug}"
    return f"https://{origin}/{path.lstrip('/')}"


def page(title: str, lines: list[str], button: str | None = None, note: str = "") -> str:
    """A plain mobile-width page: a payment page, a re-KYC page, a join link.
    With a button it is a form that POSTs to its own address."""
    body = "".join(f"<p>{html.escape(x)}</p>" for x in lines)
    form = f'<form method="post"><button type="submit">{html.escape(button)}</button></form>' if button else ""
    small = f'<p class="note">{html.escape(note)}</p>' if note else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:420px;margin:40px auto;padding:0 16px;color:#1d2433;background:#fff}}
h1{{font-size:1.3rem}}button{{width:100%;padding:14px;font-size:1rem;border:0;border-radius:8px;background:#1f6feb;color:#fff;cursor:pointer}}
.note{{color:#667085;font-size:.85rem}}</style></head><body><h1>{html.escape(title)}</h1>{body}{form}{small}
<p class="note">Sample client system for testing. No real money moves.</p></body></html>"""
