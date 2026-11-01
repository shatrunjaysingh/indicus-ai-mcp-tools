"""Imitations of the vendor systems IndicusAI's ready-made connectors reach
(backend/app/customerhelp/vendors.py): Shopify, Salesforce, Zoho Desk, Zoho
CRM, Zoho Inventory / Books, Unicommerce and SAP S/4HANA.

Each answers at the paths and in the shape the vendor's published API
documents, and signs in the vendor's way, so a connector is built and tested
without a real account. They are imitations: only the calls the connectors
make, a few records each, for the shared test people (sample_clients.py).

Mounted at /vendors/<name>. On the platform, give the imitation's address as
the connector's API address (it keeps its token endpoint at …/oauth/token).

Test credentials (test values, never real secrets):

    shopify          X-Shopify-Access-Token: shpat_sample
    salesforce       client sample-client / sample-secret      (client credentials)
    zoho_*           client sample-client / sample-secret, refresh token sample-refresh
                     Desk organisation id 60001; Inventory organization id 60012
    unicommerce      user api@sample.in / sample-pass, facility WH01
    sap              SAMPLE_USER / sample-pass               (Basic)
"""

from __future__ import annotations

import base64
import re
from urllib.parse import parse_qs

from fastapi import Body, FastAPI, Header, HTTPException, Path, Query, Request

from sample_clients import PEOPLE, day

ASHA, RAVI, MEERA, ARJUN = (p["phone"] for p in PEOPLE)
CLIENT_ID, CLIENT_SECRET, REFRESH = "sample-client", "sample-secret", "sample-refresh"


def _bearer(authorization: str | None, prefix: str, token: str) -> None:
    got = (authorization or "").strip()
    if got.lower() != f"{prefix} {token}".lower():
        raise HTTPException(401, "INVALID_SESSION_ID: sign in first.")


def _token_app(app: FastAPI, *, grant: str, token: str, check) -> None:
    @app.post("/oauth/token", include_in_schema=False)
    async def issue(request: Request) -> dict:
        # Parsed by hand: no form-parsing dependency for one endpoint.
        form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
        if form.get("grant_type") != grant or not check(form):
            raise HTTPException(400, "invalid_client")
        return {"access_token": token, "token_type": "Bearer", "expires_in": 3600}


# --- Shopify ---------------------------------------------------------------------------------

shopify = FastAPI(title="Shopify Admin API (imitation)")
_SHOP_CUSTOMERS = {6001 + i: p for i, p in enumerate(PEOPLE)}
_SHOP_ORDERS = [
    {"id": 450789469 + n, "name": f"#{1001 + n}", "customer_id": cid, "status": st, "pay": pay, "ago": ago}
    for n, (cid, st, pay, ago) in enumerate(
        [(6001, "fulfilled", "paid", -9), (6001, None, "paid", -1), (6002, "partial", "paid", -4), (6003, None, "pending", 0)]
    )
]


def _shop_order(o: dict) -> dict:
    c = _SHOP_CUSTOMERS[o["customer_id"]]
    return {
        "id": o["id"], "name": o["name"], "phone": c["phone"], "email": c["email"],
        "fulfillment_status": o["status"], "financial_status": o["pay"], "created_at": day(o["ago"]) + "T10:00:00+05:30",
        "total_price": "1499.00", "currency": "INR", "cancelled_at": None,
        "order_status_url": f"https://acme.myshopify.com/orders/{o['id']}/authenticate",
        "customer": {"id": o["customer_id"], "phone": c["phone"]},
    }


def _shop_auth(token: str | None) -> None:
    if token != "shpat_sample":
        raise HTTPException(401, "[API] Invalid API key or access token (unrecognized login or wrong password)")


@shopify.get("/orders.json")
def shop_orders(name: str = "", status: str = "open", x_shopify_access_token: str | None = Header(None)) -> dict:
    _shop_auth(x_shopify_access_token)
    want = name if name.startswith("#") else f"#{name}"
    return {"orders": [_shop_order(o) for o in _SHOP_ORDERS if not name or o["name"] == want]}


@shopify.get("/customers/{customer_id}/orders.json")
def shop_customer_orders(customer_id: int, status: str = "open", x_shopify_access_token: str | None = Header(None)) -> dict:
    _shop_auth(x_shopify_access_token)
    return {"orders": [_shop_order(o) for o in _SHOP_ORDERS if o["customer_id"] == customer_id]}


@shopify.get("/customers/search.json")
def shop_customer_search(query: str = "", x_shopify_access_token: str | None = Header(None)) -> dict:
    _shop_auth(x_shopify_access_token)
    m = re.match(r"phone:(\+?\d+)$", query.strip())
    found = [
        {"id": cid, "phone": c["phone"], "first_name": c["name"].split()[0]}
        for cid, c in _SHOP_CUSTOMERS.items()
        if m and c["phone"].endswith(m.group(1)[-10:])
    ]
    return {"customers": found}


# --- Salesforce ------------------------------------------------------------------------------

salesforce = FastAPI(title="Salesforce REST API (imitation)")
_token_app(
    salesforce, grant="client_credentials", token="sf-token",
    check=lambda f: f.get("client_id") == CLIENT_ID and f.get("client_secret") == CLIENT_SECRET,
)
_SF_CASES = [
    {"Id": "500A" + str(n), "CaseNumber": f"0000{1026 + n}", "Subject": s, "Status": st, "Priority": pr,
     "CreatedDate": day(ago) + "T09:00:00.000+0000", "ContactMobile": ph}
    for n, (s, st, pr, ago, ph) in enumerate(
        [("Refund not received", "Working", "High", -3, ASHA), ("Wrong size delivered", "Closed", "Medium", -20, ASHA),
         ("Installation visit", "New", "Low", -1, RAVI)]
    )
]


@salesforce.get("/query")
def sf_query(q: str, authorization: str | None = Header(None)) -> dict:
    _bearer(authorization, "Bearer", "sf-token")
    by_phone = re.search(r"ContactMobile = '([^']*)'", q)
    by_number = re.search(r"CaseNumber = '([^']*)'", q)
    rows = [c for c in _SF_CASES if (by_phone and c["ContactMobile"] == by_phone.group(1)) or (by_number and c["CaseNumber"] == by_number.group(1))]
    return {"totalSize": len(rows), "done": True, "records": [{"attributes": {"type": "Case"}, **r} for r in rows]}


@salesforce.post("/sobjects/Case", status_code=201)
def sf_new_case(body: dict = Body(...), authorization: str | None = Header(None)) -> dict:
    _bearer(authorization, "Bearer", "sf-token")
    case = {"Id": f"500A{len(_SF_CASES)}", "CaseNumber": f"0000{1026 + len(_SF_CASES)}", "Subject": body.get("Subject", ""),
            "Status": "New", "Priority": "Medium", "CreatedDate": day(0) + "T09:00:00.000+0000", "ContactMobile": body.get("SuppliedPhone", "")}
    _SF_CASES.append(case)
    return {"id": case["Id"], "success": True, "errors": []}


# --- Zoho (Desk, CRM, Inventory / Books) -------------------------------------------------------


def _zoho_app(title: str) -> FastAPI:
    app = FastAPI(title=title)
    _token_app(
        app, grant="refresh_token", token="zoho-token",
        check=lambda f: f.get("client_id") == CLIENT_ID and f.get("client_secret") == CLIENT_SECRET and f.get("refresh_token") == REFRESH,
    )
    return app


zoho_desk = _zoho_app("Zoho Desk API (imitation)")
_DESK = [
    {"id": "2200" + str(n), "ticketNumber": str(101 + n), "subject": s, "status": st, "createdTime": day(ago) + "T08:00:00.000Z",
     "dueDate": day(ago + 3) + "T08:00:00.000Z", "phone": ph, "channel": "Phone"}
    for n, (s, st, ago, ph) in enumerate([("Battery not charging", "Open", -2, ASHA), ("AC making noise", "On Hold", -5, RAVI), ("Invoice copy", "Closed", -15, ASHA)])
]


@zoho_desk.get("/tickets/search")
def desk_search(phone: str = "", ticketNumber: str = "", limit: int = 20, orgId: str | None = Header(None),  # noqa: N803 — Desk's names
                authorization: str | None = Header(None)):
    _bearer(authorization, "Zoho-oauthtoken", "zoho-token")
    if orgId != "60001":
        raise HTTPException(422, {"errorCode": "INVALID_ORG"})
    rows = [t for t in _DESK if (phone and t["phone"] == phone) or (ticketNumber and t["ticketNumber"] == ticketNumber)]
    if not rows:
        from fastapi.responses import Response

        return Response(status_code=204)  # Desk answers "nothing" with no content
    return {"data": rows[:limit], "count": len(rows)}


zoho_crm = _zoho_app("Zoho CRM API (imitation)")
_CRM = [
    {"id": "4876" + str(n), "Case_Number": str(2001 + n), "Subject": s, "Status": st, "Priority": "High", "Created_Time": day(ago) + "T11:00:00+05:30", "Phone": ph}
    for n, (s, st, ago, ph) in enumerate([("Meter reading wrong", "New", -1, ASHA), ("Duplicate bill", "Escalated", -6, MEERA)])
]


@zoho_crm.get("/Cases/search")
def crm_search(criteria: str, authorization: str | None = Header(None)):
    _bearer(authorization, "Zoho-oauthtoken", "zoho-token")
    m = re.fullmatch(r"\((Phone|Case_Number):equals:([^)]*)\)", criteria)
    if not m:
        raise HTTPException(400, {"code": "INVALID_QUERY"})
    rows = [c for c in _CRM if str(c[m.group(1)]) == m.group(2)]
    if not rows:
        from fastapi.responses import Response

        return Response(status_code=204)
    return {"data": rows, "info": {"count": len(rows), "more_records": False}}


zoho_inventory = _zoho_app("Zoho Inventory / Books API (imitation)")
_ZC = {f"46000{n}": p for n, p in enumerate(PEOPLE)}
_SO = [
    {"salesorder_id": "9001" + str(n), "salesorder_number": f"SO-0001{n}", "customer_id": cid, "order_status": st, "date": day(ago), "shipment_date": day(ago + 4), "total": tot}
    for n, (cid, st, ago, tot) in enumerate([("460000", "confirmed", -2, 23999.0), ("460000", "fulfilled", -30, 4500.0), ("460001", "draft", 0, 999.0)])
]
_INV = [
    {"invoice_id": "8101" + str(n), "invoice_number": f"INV-00{40 + n}", "customer_id": cid, "status": st, "date": day(ago), "due_date": day(ago + 15), "total": tot, "balance": bal,
     "invoice_url": f"https://zohosecurepay.in/books/sample/secure?CInvoiceID=8101{n}"}
    for n, (cid, st, ago, tot, bal) in enumerate([("460000", "overdue", -20, 23999.0, 23999.0), ("460001", "paid", -9, 999.0, 0.0)])
]


def _org(organization_id: str) -> None:
    if organization_id != "60012":
        raise HTTPException(400, {"code": 6041, "message": "This user is not associated with the organization."})


@zoho_inventory.get("/contacts")
def inv_contacts(organization_id: str, phone: str = "", contact_type: str = "", authorization: str | None = Header(None)) -> dict:
    _bearer(authorization, "Zoho-oauthtoken", "zoho-token")
    _org(organization_id)
    return {"code": 0, "contacts": [{"contact_id": cid, "contact_name": p["name"], "phone": p["phone"]} for cid, p in _ZC.items() if phone and p["phone"] == phone]}


@zoho_inventory.get("/salesorders")
def inv_salesorders(organization_id: str, customer_id: str = "", salesorder_number: str = "", authorization: str | None = Header(None)) -> dict:
    _bearer(authorization, "Zoho-oauthtoken", "zoho-token")
    _org(organization_id)
    rows = [s for s in _SO if (customer_id and s["customer_id"] == customer_id) or (salesorder_number and s["salesorder_number"] == salesorder_number)]
    return {"code": 0, "message": "success", "salesorders": rows}


@zoho_inventory.get("/invoices")
def inv_invoices(organization_id: str, customer_id: str = "", authorization: str | None = Header(None)) -> dict:
    _bearer(authorization, "Zoho-oauthtoken", "zoho-token")
    _org(organization_id)
    return {"code": 0, "message": "success", "invoices": [i for i in _INV if i["customer_id"] == customer_id]}


# --- Unicommerce -----------------------------------------------------------------------------

unicommerce = FastAPI(title="Unicommerce API (imitation)")
_token_app(
    unicommerce, grant="password", token="uc-token",
    check=lambda f: f.get("client_id") == "my-trusted-client" and f.get("username") == "api@sample.in" and f.get("password") == "sample-pass",
)
_UC = {
    code: {"code": code, "displayOrderCode": disp, "status": st, "channel": ch, "created": day(ago) + "T10:00:00", "notificationMobile": ph}
    for code, disp, st, ch, ago, ph in [
        ("SO7001", "AMZ-402-1", "PROCESSING", "AMAZON_IN", -1, ASHA),
        ("SO7002", "FK-88123", "COMPLETE", "FLIPKART", -12, ASHA),
        ("SO7003", "SHOP-5510", "CREATED", "SHOPIFY", 0, RAVI),
    ]
}


@unicommerce.post("/oms/saleorder/get")
def uc_get(body: dict = Body(...), authorization: str | None = Header(None)) -> dict:
    _bearer(authorization, "bearer", "uc-token")
    o = _UC.get(str(body.get("code") or ""))
    if o is None:
        return {"successful": False, "errors": [{"code": 1001, "description": "Invalid sale order code"}]}
    return {"successful": True, "saleOrderDTO": o}


@unicommerce.post("/oms/saleOrder/cancel")
def uc_cancel(body: dict = Body(...), authorization: str | None = Header(None), facility: str | None = Header(None)) -> dict:
    _bearer(authorization, "bearer", "uc-token")
    if facility != "WH01":
        raise HTTPException(400, "Facility header required")
    o = _UC.get(str(body.get("saleOrderCode") or ""))
    if o is None or o["status"] not in ("CREATED", "PENDING_VERIFICATION", "PROCESSING"):
        return {"successful": False, "errors": [{"code": 1002, "description": "Sale order cannot be cancelled"}]}
    o["status"] = "CANCELLED"
    return {"successful": True}


# --- SAP S/4HANA (OData v2) -------------------------------------------------------------------

sap = FastAPI(title="SAP S/4HANA OData API (imitation)")
_BP = {"1000101": ("2201", ASHA), "1000102": ("2202", RAVI), "1000103": ("2203", MEERA)}
_SAP_SO = [
    {"SalesOrder": str(1234 + n), "SoldToParty": bp, "CreationDate": f"/Date({1761955200000 + ago * 86400000})/", "RequestedDeliveryDate": day(ago + 7),
     "TotalNetAmount": amt, "TransactionCurrency": "INR", "OverallSDProcessStatus": st, "OverallDeliveryStatus": dl, "PurchaseOrderByCustomer": f"PO-{88 + n}"}
    for n, (bp, ago, amt, st, dl) in enumerate([("1000101", -3, "185000.00", "B", "A"), ("1000101", -40, "72000.00", "C", "C"), ("1000102", -1, "9900.00", "A", "A")])
]


def _sap_auth(authorization: str | None) -> None:
    if (authorization or "") != "Basic " + base64.b64encode(b"SAMPLE_USER:sample-pass").decode():
        raise HTTPException(401, "Unauthorized")


def _eq(filt: str, field: str) -> str | None:
    m = re.fullmatch(rf"{field} eq '([^']*)'", filt.strip())
    return m.group(1) if m else None


@sap.get("/API_SALES_ORDER_SRV/A_SalesOrder")
def sap_orders(f: str = Query("", alias="$filter"), authorization: str | None = Header(None)) -> dict:
    _sap_auth(authorization)
    who = _eq(f, "SoldToParty")
    return {"d": {"results": [o for o in _SAP_SO if o["SoldToParty"] == who]}}


@sap.get("/API_SALES_ORDER_SRV/A_SalesOrder('{so}')")
def sap_order(so: str = Path(...), authorization: str | None = Header(None)) -> dict:
    _sap_auth(authorization)
    o = next((o for o in _SAP_SO if o["SalesOrder"] == so), None)
    if o is None:
        raise HTTPException(404, {"error": {"code": "SY/530", "message": {"lang": "en", "value": "Resource not found"}}})
    return {"d": o}


@sap.get("/API_BUSINESS_PARTNER/A_AddressPhoneNumber")
def sap_phone(f: str = Query("", alias="$filter"), authorization: str | None = Header(None)) -> dict:
    _sap_auth(authorization)
    phone = _eq(f, "InternationalPhoneNumber")
    return {"d": {"results": [{"AddressID": addr} for addr, ph in _BP.values() if ph == phone]}}


@sap.get("/API_BUSINESS_PARTNER/A_BusinessPartnerAddress")
def sap_partner(f: str = Query("", alias="$filter"), authorization: str | None = Header(None)) -> dict:
    _sap_auth(authorization)
    addr = _eq(f, "AddressID")
    return {"d": {"results": [{"BusinessPartner": bp, "AddressID": a} for bp, (a, _) in _BP.items() if a == addr]}}


APPS: dict[str, FastAPI] = {
    "shopify": shopify,
    "salesforce": salesforce,
    "zoho_desk": zoho_desk,
    "zoho_crm": zoho_crm,
    "zoho_inventory": zoho_inventory,
    "unicommerce": unicommerce,
    "sap": sap,
}
