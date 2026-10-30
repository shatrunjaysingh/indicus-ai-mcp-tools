"""A sample client app for the IndicusAI Connect API — "Demo Store".

Plays the part of a client: a store's chat screen (index.html) and the store's
own server (this file). The server is the reference for what a client builds:

    1. keep the Connect key and secrets here, never in the page
    2. sign a customer token for whoever is logged in
    3. forward each chat message to IndicusAI and pass the reply back
    4. receive and verify IndicusAI's webhooks

Run it (see README.md):

    export CONNECT_KEY=ick_…  CUSTOMER_SECRET=ics_…  [WEBHOOK_SECRET=whs_…]
    .venv/bin/python examples/connect_sample_app/app.py      # http://localhost:8090

Customers to "log in as" come from DEMO_CUSTOMERS ("Name:+91…,Name:+91…"):
use mobiles that are on the workspace's orders.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from collections import deque
from pathlib import Path

import httpx
import jwt  # pyjwt
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

API = os.environ.get("INDICUS_API", "https://indicus-ai.com/api/v1").rstrip("/")
CONNECT_KEY = os.environ.get("CONNECT_KEY", "")
CUSTOMER_SECRET = os.environ.get("CUSTOMER_SECRET", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
CUSTOMERS = [
    {"id": f"demo-{i}", "name": n.strip(), "phone": p.strip()}
    for i, pair in enumerate(os.environ.get("DEMO_CUSTOMERS", "Test customer:+919000000999").split(","))
    if ":" in pair
    for n, p in [pair.split(":", 1)]
]

app = FastAPI(title="Demo Store (IndicusAI Connect sample)")
#: The last webhooks received, for the developer panel.
WEBHOOKS: deque[dict] = deque(maxlen=50)


def customer_token(customer: dict) -> str:
    """Step 2: who is logged in, signed with the customer secret. Short-lived."""
    now = int(time.time())
    claims = {"sub": customer["id"], "phone": customer["phone"], "name": customer["name"],
              "iat": now, "exp": now + 600}
    return jwt.encode(claims, CUSTOMER_SECRET, algorithm="HS256")


def _headers(customer: dict | None) -> dict:
    headers = {"Authorization": f"Bearer {CONNECT_KEY}", "Content-Type": "application/json"}
    if customer is not None:
        headers["X-Customer-Token"] = customer_token(customer)
    return headers


def _customer(customer_id: str) -> dict | None:
    return next((c for c in CUSTOMERS if c["id"] == customer_id), None)


@app.get("/")
async def page() -> FileResponse:
    return FileResponse(Path(__file__).with_name("index.html"))


@app.get("/api/setup")
async def setup() -> dict:
    """What the page needs: who can log in, and whether the key works."""
    ok, who = False, ""
    if CONNECT_KEY:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{API}/connect/me", headers={"Authorization": f"Bearer {CONNECT_KEY}"})
        ok, who = r.status_code == 200, (r.json().get("name") if r.status_code == 200 else r.text[:200])
    return {"api": API, "key_ok": ok, "integration": who, "customers": CUSTOMERS,
            "customer_secret_set": bool(CUSTOMER_SECRET), "webhook_secret_set": bool(WEBHOOK_SECRET)}


@app.post("/api/chat")
async def chat(request: Request) -> StreamingResponse:
    """Step 3: forward a customer's message and stream IndicusAI's events back
    to the page (typing, message, handed_over, done)."""
    body = await request.json()
    customer = _customer(body.get("customer_id", ""))
    chat_id = body.get("chat_id") or f"demo-{uuid.uuid4().hex[:10]}"
    payload = {"text": body.get("text", ""), "client_message_id": uuid.uuid4().hex}
    url = f"{API}/connect/conversations/{chat_id}/messages"

    async def relay():
        # What was sent, for the developer panel (secrets shortened).
        yield _sse("request", {"POST": url, "as": customer["name"] if customer else "visitor (no token)",
                               "body": payload})
        try:
            async with httpx.AsyncClient(timeout=120) as c, c.stream(
                "POST", url, json=payload, headers={**_headers(customer), "Accept": "text/event-stream"}
            ) as r:
                if r.status_code != 200:
                    yield _sse("error", {"status": r.status_code, "body": (await r.aread()).decode()[:500]})
                    return
                event = "message"
                async for line in r.aiter_lines():
                    if line.startswith("event:"):
                        event = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        yield _sse(event, json.loads(line.split(":", 1)[1].strip() or "{}"))
        except httpx.HTTPError as exc:
            yield _sse("error", {"status": 0, "body": f"Could not reach IndicusAI: {exc}"})

    return StreamingResponse(relay(), media_type="text/event-stream")


@app.get("/api/events")
async def events(chat_id: str, customer_id: str = "", after: str = "") -> StreamingResponse:
    """After a hand-over: a person's replies, live, from IndicusAI's events
    stream — what a client app without a webhook does."""
    customer = _customer(customer_id)
    params = {"after": after} if after else {}

    async def relay():
        try:
            async with httpx.AsyncClient(timeout=None) as c, c.stream(
                "GET", f"{API}/connect/conversations/{chat_id}/events", params=params,
                headers={**_headers(customer), "Accept": "text/event-stream"},
            ) as r:
                event = "message"
                async for line in r.aiter_lines():
                    if line.startswith("event:"):
                        event = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        yield _sse(event, json.loads(line.split(":", 1)[1].strip() or "{}"))
        except httpx.HTTPError as exc:
            yield _sse("error", {"status": 0, "body": f"Events stream ended: {exc}"})

    return StreamingResponse(relay(), media_type="text/event-stream")


@app.get("/api/history")
async def history(chat_id: str, customer_id: str = "") -> JSONResponse:
    customer = _customer(customer_id)
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{API}/connect/conversations/{chat_id}/messages", headers=_headers(customer))
    return JSONResponse(status_code=r.status_code, content=r.json())


@app.post("/webhook")
async def webhook(request: Request) -> JSONResponse:
    """Step 4: IndicusAI's webhook. Checked before it is believed."""
    raw = await request.body()
    ts = request.headers.get("x-indicus-timestamp", "")
    given = request.headers.get("x-indicus-signature", "")
    good = "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), ts.encode() + b"." + raw, hashlib.sha256).hexdigest()
    fresh = ts.isdigit() and abs(time.time() - int(ts)) < 300
    valid = bool(WEBHOOK_SECRET) and fresh and hmac.compare_digest(good, given)
    WEBHOOKS.appendleft({"at": time.strftime("%H:%M:%S"), "valid": valid,
                         "event": request.headers.get("x-indicus-event", ""), "body": json.loads(raw or b"{}")})
    return JSONResponse(status_code=200 if valid else 401, content={"ok": valid})


@app.get("/api/webhooks")
async def webhooks() -> list[dict]:
    return list(WEBHOOKS)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


if __name__ == "__main__":
    if not CONNECT_KEY or not CUSTOMER_SECRET:
        raise SystemExit("Set CONNECT_KEY and CUSTOMER_SECRET (from Customer help → Apps & API). See README.md.")
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8090")))
