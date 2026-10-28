"""Seed the Customer Help Demo workspace: a store's orders and its help bot.

    docker compose exec mcp-tools python seeds/customer_help.py   # on a deployment
    .venv/bin/python seeds/customer_help.py                       # on a laptop

    PLATFORM_API_URL   the platform's API (default http://127.0.0.1:8000/api/v1)
    SEED_EMAIL / SEED_PASSWORD   who runs it (default the demo account)
    DEMO_PHONE         optional: your own mobile — three orders are put on it,
                       so you can ask the bot about "your" orders on WhatsApp
                       or by phone and be recognised by your number

What it builds, through the platform's own APIs only — the same Customer
help screen a client uses:

  - the help bot (agent, skill, sample FAQ knowledge base), for "Indicus
    Demo Store"
  - 300 orders across India in every state an order goes through — placed,
    packed, shipped, out for delivery, delivered, delayed, cancelled, return
    requested — dated around today, uploaded as the client's spreadsheet

Every customer number is in the platform's placeholder range (9000000xxx),
except DEMO_PHONE's three. No conversations or hand-overs: those come from
real test messages and calls. Which numbers reach the bot is chosen on the
screen.

Idempotent: re-running updates the same orders (by order number) and keeps
the bot as it is.
"""

from __future__ import annotations

import asyncio
import csv
import io
import os
import random
from datetime import UTC, date, datetime, timedelta

import httpx

API = os.environ.get("PLATFORM_API_URL", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("SEED_EMAIL", "demo@example.com")
PASSWORD = os.environ.get("SEED_PASSWORD", "demo-password-1234")
DEMO_PHONE = os.environ.get("DEMO_PHONE", "")
WORKSPACE_NAME = "Customer Help Demo"
BRAND = "Indicus Demo Store"
ORDERS = 300

CITIES = [
    ("Delhi", "110001"), ("Gurugram", "122001"), ("Lucknow", "226001"), ("Jaipur", "302001"),
    ("Chandigarh", "160017"), ("Mumbai", "400001"), ("Pune", "411001"), ("Ahmedabad", "380001"),
    ("Surat", "395003"), ("Indore", "452001"), ("Bengaluru", "560001"), ("Chennai", "600001"),
    ("Hyderabad", "500001"), ("Kochi", "682011"), ("Coimbatore", "641001"), ("Kolkata", "700016"),
    ("Bhubaneswar", "751001"), ("Patna", "800001"), ("Guwahati", "781001"), ("Ranchi", "834001"),
]
FIRST = ["Asha", "Rahul", "Priya", "Arjun", "Sneha", "Vikram", "Ananya", "Rohan", "Kavya", "Amit",
         "Neha", "Suresh", "Divya", "Karthik", "Pooja", "Sourav", "Meera", "Imran", "Lakshmi", "Ritu"]
LAST = ["Sharma", "Patel", "Reddy", "Das", "Iyer", "Singh", "Nair", "Ghosh", "Kulkarni", "Khan",
        "Mohanty", "Gupta", "Rao", "Bora", "Mehta"]
ITEMS = ["Steel water bottle", "Pressure cooker 5L", "Cotton bedsheet set", "Wireless earbuds",
         "Mixer grinder 750W", "Non-stick tawa", "LED desk lamp", "Yoga mat", "Backpack 30L",
         "Electric kettle 1.5L", "Ceiling fan", "Running shoes", "Smartwatch", "Air fryer 4L",
         "School bag", "Water purifier filter", "Induction cooktop", "Bluetooth speaker"]
COURIERS = ["Delhivery", "Blue Dart", "Ekart", "Xpressbees", "DTDC", "India Post"]
DELAY_REASONS = ["Held at the hub due to heavy rain", "Address could not be found — courier will call",
                 "Delivery attempted, customer not available", "Delayed at the sorting centre"]

COLUMNS = ["Order Number", "Mobile", "Pincode", "Customer Name", "Status", "Remarks", "Items",
           "Order Date", "Expected Delivery", "Delivered On", "Courier", "AWB Number", "Tracking Link"]


def today() -> date:
    return (datetime.now(UTC) + timedelta(hours=5, minutes=30)).date()


def build(rnd: random.Random) -> bytes:
    t = today()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(COLUMNS)
    for i in range(ORDERS):
        ref = f"IDS-{240001 + i}"
        city, pin = rnd.choice(CITIES)
        phone = f"9000000{rnd.randrange(1000):03d}"
        if DEMO_PHONE and i < 3:
            phone = DEMO_PHONE
        name = f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"
        items = ", ".join(rnd.sample(ITEMS, rnd.choice((1, 1, 1, 2))))
        age = rnd.randrange(0, 21)
        ordered = t - timedelta(days=age)
        promised = ordered + timedelta(days=rnd.choice((3, 4, 5, 6, 7)))
        status, remarks, delivered, courier, awb = "", "", "", "", ""
        if age <= 1:
            status = rnd.choice(("Order placed", "Packed"))
        elif promised < t and rnd.random() < 0.75:
            status, delivered = "Delivered", str(promised - timedelta(days=rnd.choice((0, 0, 1))))
        elif promised < t:
            status, remarks = "Delayed", rnd.choice(DELAY_REASONS)
        elif promised == t:
            status, remarks = "Out for delivery", f"Out for delivery from the {city} hub"
        else:
            status, remarks = "Shipped", f"In transit to {city}"
        if rnd.random() < 0.04:
            status, remarks, delivered = "Cancelled", "Cancelled by the customer", ""
        elif status == "Delivered" and rnd.random() < 0.06:
            status, remarks = "Return requested", "Pickup to be scheduled"
        if status not in ("Order placed", "Packed", "Cancelled"):
            courier = rnd.choice(COURIERS)
            awb = f"{courier[:2].upper()}{rnd.randrange(10**9, 10**10)}"
        if i < 3 and DEMO_PHONE:
            # Yours: one on its way, one late, one delivered — the three answers worth hearing.
            status, remarks, delivered, promised = [
                ("Shipped", f"In transit to {city}", "", t + timedelta(days=1)),
                ("Delayed", DELAY_REASONS[0], "", t - timedelta(days=2)),
                ("Delivered", "", str(t - timedelta(days=3)), t - timedelta(days=3)),
            ][i]
            # Not from rnd: with or without DEMO_PHONE, every other order is the same.
            courier, awb = "Delhivery", f"DL{9_000_000_001 + i}"
        w.writerow([
            ref, phone, pin, name, status, remarks, items, str(ordered),
            "" if status == "Cancelled" else str(promised), delivered, courier, awb,
            f"https://track.example.in/{awb}" if awb else "",
        ])
    return out.getvalue().encode()


async def main() -> None:
    rnd = random.Random(20261028)
    async with httpx.AsyncClient(base_url=API, timeout=240) as c:
        login = await c.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
        if login.status_code != 200:
            print(f"Could not log in as {EMAIL} — create it first (platform repo: scripts/seed.py).")
            return
        auth = login.json()
        c.headers.update({"Authorization": f"Bearer {auth['access_token']}"})
        c.headers["X-Workspace-Id"] = auth["default_workspace_id"]

        # --- 0. workspace ---
        existing = (await c.get("/workspaces")).json()
        found = next((w for w in existing if w["name"] == WORKSPACE_NAME), None)
        if found:
            workspace = found["id"]
            print(f"0. Reusing workspace '{WORKSPACE_NAME}'")
        else:
            created = await c.post("/workspaces", json={"name": WORKSPACE_NAME})
            if created.status_code not in (200, 201):
                print("   could not create the workspace:", created.text[:200])
                return
            workspace = created.json()["id"]
            print(f"0. Created workspace '{WORKSPACE_NAME}'")
        c.headers["X-Workspace-Id"] = workspace

        # --- 1. the bot ---
        print("\n1. The help bot")
        r = await c.post("/customer-help/setup", json={"brand": BRAND})
        if r.status_code != 200:
            raise SystemExit(f"   setup failed: {r.status_code} {r.text[:300]}")
        print(f"   {'created' if r.json()['created'] else 'already there'}: agent {r.json()['agent_id']}")

        # --- 2. orders ---
        print("\n2. Orders")
        data = build(rnd)
        files = {"file": ("orders.csv", data, "text/csv")}
        preview = await c.post("/customer-help/orders/import?commit=false", files=files)
        if preview.status_code != 200:
            raise SystemExit(f"   the file was refused: {preview.text[:300]}")
        if preview.json().get("error_count"):
            for e in preview.json()["errors"][:10]:
                print(f"   line {e['line']}: {e['message']}")
            raise SystemExit("   the file has problems; nothing imported.")
        done = (await c.post("/customer-help/orders/import?commit=true", files=files)).json()
        print(f"   {done['create']} new, {done['update']} changed, {done['unchanged']} unchanged")
        if DEMO_PHONE:
            print(f"   orders IDS-240001..240003 are on {DEMO_PHONE}")

        print("\nDone. Open Customer help to choose which numbers reach the bot, and to try it.")


if __name__ == "__main__":
    asyncio.run(main())
