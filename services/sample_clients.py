"""Shared pieces of the sample client systems: three pretend businesses whose
back-office APIs IndicusAI's chat bot reaches through data connectors, the way
it would reach a real client's — so connectors are built and tested without a
client, and nothing a customer owns is ever uploaded to IndicusAI.

    /shop      Kettle & Co, an online store           (sample_shop_api.py)
    /power     Brightline Power, an electricity utility (sample_power_api.py)
    /service   FixRight Service, appliance & battery service (sample_service_api.py)

Each is protected by an API key in the `X-Api-Key` header, as most clients'
APIs are. The key is `SAMPLE_CLIENT_API_KEY` (a test value, never a real
secret); blank turns the check off for local poking with curl.

The data is synthetic and in memory: changes (a cancelled order, a booked
visit) last until the service restarts, which is what a demo wants. Dates are
relative to today, so a "due tomorrow" bill stays due tomorrow.

The same customers appear in all three, so one test person can be tried
against every business:

    +919000000999  Asha Rao       Bengaluru 560001
    +919000000111  Ravi Sen       Kolkata 700001
    +919000000222  Meera Iyer     Chennai 600001
    +919000000333  Arjun Mehta    Mumbai 400001
"""

from __future__ import annotations

import hmac
import os
import re
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

IST = timezone(timedelta(hours=5, minutes=30))

PEOPLE = [
    {"name": "Asha Rao", "phone": "+919000000999", "email": "asha.rao@example.com",
     "city": "Bengaluru", "pincode": "560001", "address": "14 MG Road, Bengaluru 560001"},
    {"name": "Ravi Sen", "phone": "+919000000111", "email": "ravi.sen@example.com",
     "city": "Kolkata", "pincode": "700001", "address": "8 Park Street, Kolkata 700001"},
    {"name": "Meera Iyer", "phone": "+919000000222", "email": "meera.iyer@example.com",
     "city": "Chennai", "pincode": "600001", "address": "22 Anna Salai, Chennai 600001"},
    {"name": "Arjun Mehta", "phone": "+919000000333", "email": "arjun.mehta@example.com",
     "city": "Mumbai", "pincode": "400001", "address": "5 Marine Drive, Mumbai 400001"},
]


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
