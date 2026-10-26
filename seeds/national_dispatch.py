"""Seed the Smart Dispatch National Demo workspace: a battery brand's service
network across India.

    docker compose exec mcp-tools python seeds/national_dispatch.py   # on a deployment
    .venv/bin/python seeds/national_dispatch.py                       # on a laptop

    PLATFORM_API_URL   the platform's API (default http://127.0.0.1:8000/api/v1)
    SEED_EMAIL / SEED_PASSWORD   who runs it (default the demo account)

What it builds, through the platform's own APIs only — the same settings
screens, partner page and spreadsheet imports a client's desk uses:

  - the battery service blueprint and the client profile (brand, prefix,
    coverage "listed", tier SLAs, upcountry travel)
  - 3 service partners (West, South, North-East)
  - a centre in each of 40 cities, and a dealer beside most of them, half of
    which replace at their counter
  - coverage: every state with a centre is upcountry, the eight metros'
    districts metro, the other cities' districts local; the rest of India is
    not served
  - about 150 technicians, partners' and freelancers among them

No tickets, customers or claims: complaints come from real test calls and
WhatsApp. Every phone number is in the platform's placeholder range
(9000000xxx), which dispatch never dials, so nobody real is ever rung.

Idempotent: re-running updates the same centres (by code), technicians (by
phone) and coverage (by pincode). Same shape as seeds/battery.py.
"""

from __future__ import annotations

import asyncio
import io
import math
import os
import random

import httpx

API = os.environ.get("PLATFORM_API_URL", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("SEED_EMAIL", "demo@example.com")
PASSWORD = os.environ.get("SEED_PASSWORD", "demo-password-1234")
WORKSPACE_NAME = "Smart Dispatch National Demo"

# --- the network -----------------------------------------------------------------------

#: (code, city, pincode of its centre, metro?, partner code or "", technicians)
CITIES: list[tuple[str, str, str, bool, str, int]] = [
    ("DEL", "Delhi", "110001", True, "", 6),
    ("GGN", "Gurugram", "122001", False, "", 3),
    ("NOI", "Noida", "201301", False, "", 3),
    ("LKO", "Lucknow", "226001", False, "", 4),
    ("KNP", "Kanpur", "208001", False, "", 3),
    ("AGR", "Agra", "282001", False, "", 3),
    ("VNS", "Varanasi", "221001", False, "", 3),
    ("JAI", "Jaipur", "302001", False, "", 4),
    ("CHD", "Chandigarh", "160017", False, "", 3),
    ("LDH", "Ludhiana", "141001", False, "", 3),
    ("DDN", "Dehradun", "248001", False, "", 3),
    ("MUM", "Mumbai", "400001", True, "SP-WEST", 6),
    ("THA", "Thane", "400601", False, "SP-WEST", 3),
    ("PUN", "Pune", "411001", True, "SP-WEST", 6),
    ("NSK", "Nashik", "422001", False, "SP-WEST", 3),
    ("NGP", "Nagpur", "440001", False, "", 3),
    ("AMD", "Ahmedabad", "380001", True, "", 6),
    ("SUR", "Surat", "395003", False, "", 3),
    ("BRC", "Vadodara", "390001", False, "", 3),
    ("GOA", "Panaji", "403001", False, "", 3),
    ("IDR", "Indore", "452001", False, "", 3),
    ("BPL", "Bhopal", "462001", False, "", 3),
    ("RPR", "Raipur", "492001", False, "", 3),
    ("BLR", "Bengaluru", "560001", True, "", 6),
    ("MYS", "Mysuru", "570001", False, "", 3),
    ("MAA", "Chennai", "600001", True, "", 6),
    ("CBE", "Coimbatore", "641001", False, "", 3),
    ("IXM", "Madurai", "625001", False, "", 3),
    ("COK", "Kochi", "682011", False, "", 3),
    ("TRV", "Thiruvananthapuram", "695001", False, "", 3),
    ("HYD", "Hyderabad", "500001", True, "SP-SOUTH", 6),
    ("VGA", "Vijayawada", "520001", False, "SP-SOUTH", 3),
    ("VTZ", "Visakhapatnam", "530001", False, "SP-SOUTH", 3),
    ("CCU", "Kolkata", "700016", True, "", 6),
    ("SLG", "Siliguri", "734001", False, "", 3),
    ("BBI", "Bhubaneswar", "751001", False, "", 3),
    ("PAT", "Patna", "800001", False, "", 3),
    ("RNC", "Ranchi", "834001", False, "", 3),
    ("JSR", "Jamshedpur", "831001", False, "", 3),
    ("GAU", "Guwahati", "781001", False, "SP-NE", 4),
]

PARTNERS = [
    {"code": "SP-WEST", "name": "Shree Battery Services", "contact_name": "Rohit Kulkarni"},
    {"code": "SP-SOUTH", "name": "Sri Venkateswara Power Care", "contact_name": "K. Srinivas"},
    {"code": "SP-NE", "name": "Brahmaputra Auto Electricals", "contact_name": "Pranjal Bora"},
]

#: First names by region, for technicians whose names read as local.
FIRST = {
    "North": ["Amit", "Rahul", "Sanjay", "Vikas", "Rakesh", "Deepak", "Manoj", "Sunil", "Ajay", "Pankaj"],
    "West": ["Sachin", "Nilesh", "Mahesh", "Ganesh", "Hardik", "Jignesh", "Sagar", "Vishal", "Prashant", "Tushar"],
    "South": ["Karthik", "Suresh", "Ravi", "Venkat", "Arun", "Prakash", "Naveen", "Srinivas", "Manju", "Anil"],
    "East": ["Subhajit", "Arindam", "Soumen", "Debasis", "Biswajit", "Prasanta", "Sanjib", "Tapas", "Ranjan", "Abhijit"],
    "North-East": ["Pranjal", "Bhaskar", "Dipankar", "Rituraj", "Hemanta"],
    "Central": ["Rajesh", "Mukesh", "Dinesh", "Santosh", "Ashok"],
}
LAST = {
    "North": ["Sharma", "Verma", "Gupta", "Singh", "Yadav", "Chauhan", "Mishra", "Pandey"],
    "West": ["Patil", "Jadhav", "Shinde", "Pawar", "Patel", "Desai", "Shah", "Kulkarni"],
    "South": ["Reddy", "Naidu", "Kumar", "Iyer", "Nair", "Gowda", "Rao", "Pillai"],
    "East": ["Das", "Ghosh", "Mondal", "Saha", "Roy", "Mohanty", "Sahoo", "Mahato"],
    "North-East": ["Bora", "Kalita", "Saikia", "Baruah", "Gogoi"],
    "Central": ["Tiwari", "Dubey", "Sahu", "Verma", "Patel"],
}
REGION_OF_STATE = {
    "Delhi": "North", "Haryana": "North", "Uttar Pradesh": "North", "Rajasthan": "North", "Chandigarh": "North",
    "Punjab": "North", "Uttarakhand": "North", "Maharashtra": "West", "Gujarat": "West", "Goa": "West",
    "Madhya Pradesh": "Central", "Chhattisgarh": "Central", "Karnataka": "South", "Tamil Nadu": "South",
    "Kerala": "South", "Telangana": "South", "Andhra Pradesh": "South", "West Bengal": "East", "Odisha": "East",
    "Bihar": "East", "Jharkhand": "East", "Assam": "North-East",
}
#: The languages a technician speaks, by region (Hindi, Bengali, Odia, English are what the alerts use).
LANGS = {"East": "Bengali;Hindi", "North-East": "English;Hindi", "South": "English;Hindi"}

SETTINGS = {
    "fieldservice_brand": "Exide",
    "fieldservice_asset_label": "battery",
    "fieldservice_ticket_prefix": "EXN",
    "fieldservice_coverage_mode": "listed",
    "fieldservice_sla_minutes": "240",
    "fieldservice_local_sla_minutes": "480",
    "fieldservice_upcountry_sla_hours": "48",
    "fieldservice_upcountry_booking": "slot",
    "fieldservice_upcountry_travel_rupees": "300",
    "fieldservice_dealer_reach_km": "25",
    "fieldservice_counter_sla_hours": "24",
}


def phone(n: int) -> str:
    """The platform's placeholder range: dispatch never dials 9000000xxx."""
    return f"9000000{n:03d}"


def csv_text(header: list[str], rows: list[list[object]]) -> bytes:
    out = io.StringIO()
    out.write(",".join(header) + "\n")
    for r in rows:
        out.write(",".join(f'"{v}"' if isinstance(v, str) and "," in v else str(v) for v in r) + "\n")
    return out.getvalue().encode()


async def place(c: httpx.AsyncClient, pin: str) -> dict:
    r = await c.get(f"/fieldservice/pincodes/{pin}")
    if r.status_code != 200:
        raise SystemExit(f"Pincode {pin} is not known to the platform: {r.text[:200]}")
    return r.json()


async def run_import(c: httpx.AsyncClient, kind: str, data: bytes) -> None:
    files = {"file": (f"{kind}.csv", data, "text/csv")}
    preview = (await c.post(f"/fieldservice/import/{kind}?commit=false", files=files)).json()
    if preview.get("error_count"):
        for e in preview["errors"][:10]:
            print(f"   line {e['line']}: {e['message']}")
        raise SystemExit(f"   {kind}: the file has problems; nothing imported.")
    done = (await c.post(f"/fieldservice/import/{kind}?commit=true", files=files)).json()
    print(f"   {kind}: {done['create']} new, {done['update']} changed, {done.get('remove', 0)} removed")


async def main() -> None:
    rnd = random.Random(20261025)
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

        # --- 1. profile, blueprint, coverage settings ---
        print("\n1. Profile and settings")
        for key, value in SETTINGS.items():
            r = await c.put(f"/config/workspace/{key}", json={"value": value})
            if r.status_code != 200:
                print(f"   {key}: {r.status_code} {r.text[:120]}")
        r = await c.post("/fieldservice/blueprint/apply-template", json={"template": "battery"})
        print("   battery blueprint:", "applied" if r.status_code == 200 else r.text[:120])

        # --- 2. partners ---
        print("\n2. Service partners")
        have = {p["code"] for p in (await c.get("/fieldservice/partners")).json()["partners"]}
        for i, p in enumerate(PARTNERS):
            if p["code"] in have:
                print(f"   {p['name']}: already there")
                continue
            body = {**p, "phone": phone(900 + i), "email": "", "active": True, "notes": "Demo partner."}
            r = await c.post("/fieldservice/partners", json=body)
            print(f"   {p['name']}: {'added' if r.status_code == 201 else r.text[:120]}")

        # --- 3. where every city is ---
        print("\n3. Placing 40 cities")
        places = {code: await place(c, pin) for code, _city, pin, *_ in CITIES}

        # --- 4. centres and dealers ---
        print("\n4. Centres and dealers")
        rows = []
        n_phone = 0
        for i, (code, city, pin, metro, partner, _techs) in enumerate(CITIES):
            p = places[code]
            region = REGION_OF_STATE.get(p["state"], "")
            n_phone += 1
            rows.append([f"{code}-C", f"{city} Service Centre", "centre", partner, pin, "", "",
                         f"{p['place']}, {city}", phone(n_phone), 25 if metro else 15, region, "no"])
            if i % 4 != 3:  # a dealer beside most centres; every other one replaces at its counter
                n_phone += 1
                lat = p["lat"] + rnd.uniform(-0.03, 0.03)
                lng = p["lng"] + rnd.uniform(-0.03, 0.03)
                rows.append([f"{code}-D", f"{city} Battery House", "dealer", partner, "", f"{lat:.5f}", f"{lng:.5f}",
                             f"Main Road, {city}", phone(n_phone), 8, region, "yes" if i % 2 == 0 else "no"])
        await run_import(c, "centres", csv_text(
            ["code", "name", "kind", "partner", "pincode", "lat", "lng", "address", "phone", "radius_km", "region",
             "counter"], rows))

        # --- 5. coverage ---
        print("\n5. Coverage")
        states = sorted({places[code]["state"] for code, *_ in CITIES})
        rows = [["", "", s, "upcountry", "", "", "", ""] for s in states]
        for code, _city, _pin, metro, partner, _techs in CITIES:
            p = places[code]
            rows.append(["", p["district"], p["state"], "metro" if metro else "local", f"{code}-C", partner, "", ""])
        await run_import(c, "coverage", csv_text(
            ["pincode", "district", "state", "tier", "centre", "partner", "sla_hours", "travel_rupees"], rows))

        # --- 6. technicians ---
        print("\n6. Technicians")
        rows = []
        n = 100
        used: set[str] = set()
        for code, city, _pin, _metro, partner, count in CITIES:
            p = places[code]
            region = REGION_OF_STATE.get(p["state"], "North")
            for k in range(count):
                n += 1
                while True:
                    name = f"{rnd.choice(FIRST[region])} {rnd.choice(LAST[region])}"
                    if name not in used:
                        used.add(name)
                        break
                # Within about 8 km of the city centre.
                r_km, a = 8 * math.sqrt(rnd.random()), rnd.uniform(0, 2 * math.pi)
                lat = p["lat"] + (r_km / 111) * math.cos(a)
                lng = p["lng"] + (r_km / (111 * math.cos(math.radians(p["lat"])))) * math.sin(a)
                freelance = k == count - 1 and count >= 4
                kind = "freelance" if freelance else ("partner" if partner else "employee")
                skills = "car battery;inverter" if k % 3 else "car battery"
                rows.append([name, phone(n), f"{code}-C", partner if not freelance else "", f"{lat:.5f}", f"{lng:.5f}",
                             skills, LANGS.get(region, "Hindi;English"), kind, 250 if freelance else "",
                             "08:00-20:00", 8])
        await run_import(c, "technicians", csv_text(
            ["name", "phone", "centre", "partner", "lat", "lng", "skills", "languages", "kind", "pay_per_job",
             "shift", "max_jobs_per_day"], rows))

        summary = (await c.get("/fieldservice/coverage/summary")).json()
        regions = (await c.get("/fieldservice/regions")).json()["regions"]
        print(
            f"\nDone. {summary['pincodes']['listed']:,} pincodes listed "
            f"({summary['pincodes']['metro']:,} metro, {summary['pincodes']['local']:,} local, "
            f"{summary['pincodes']['upcountry']:,} upcountry) across {len(states)} states; "
            f"regions: {', '.join(r['name'] for r in regions)}."
        )
        print(f"Open Smart Dispatch in the workspace '{WORKSPACE_NAME}'.")


if __name__ == "__main__":
    asyncio.run(main())
