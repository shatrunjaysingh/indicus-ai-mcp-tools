"""Sample online stores' back offices (sample_clients.py).

What a real store's order system offers a help bot: find a customer, their
orders, one order; and three changes — cancel, return, change the delivery
address — each allowed only in the right state, as a real system would refuse.

Two stores share the code, each its own app with its own orders:

    /shop   Kettle & Co — eight orders for the four shared test people.
    /miso   Miso — the 300 orders the Customer Help Line demo used to upload
            (IDS-240001 … IDS-240300, all on +919000… test numbers), kept in
            sample_miso_orders.json with dates as days from today.

For testing, each store's data can be changed through its own API (and so
from its Swagger page, /shop/docs or /miso/docs): PATCH an order (any field,
including the phone and name, which moves it to that customer), POST a new
one, POST /reset to go back to the original. Changes — and the cancels,
returns and address changes the bot makes — are saved under SAMPLE_STATE_DIR
(state/<store>.json) so a restart keeps them until a reset.

Cash on delivery and delivery problems, for confirmation and NDR agents:
orders carry payment_mode (COD or Prepaid); COD orders wait in "Pending
confirmation" (GET /orders/cod-pending, POST /orders/{id}/confirm); a failed
delivery is "Delivery failed" with ndr_reason and attempt_count (GET
/orders/ndr, POST /orders/{id}/delivery to reattempt); GET
/orders/{id}/tracking and /orders/{id}/refund.
"""

from __future__ import annotations

import copy
import json
import logging
import os
from collections.abc import Callable
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from sample_clients import ALL_PEOPLE, clean_phone, day, now_iso, require_key, valid_mobile
from sample_shop_carts import attach as attach_carts

logger = logging.getLogger(__name__)
STATE_DIR = Path(os.environ.get("SAMPLE_STATE_DIR", Path(__file__).resolve().parent.parent / "state"))

CANCELLABLE = {"Pending confirmation", "Order placed", "Packed"}
ADDRESS_CHANGEABLE = {"Pending confirmation", "Order placed", "Packed"}
NOT_SHIPPED = {"Pending confirmation", "Order placed", "Packed", "Cancelled"}


class Reattempt(BaseModel):
    address: str | None = Field(default=None, min_length=10, max_length=500, description="A corrected address, if that was the problem")
    reattempt_date: str | None = Field(default=None, description="YYYY-MM-DD, today or later; blank: tomorrow")
    landmark: str | None = Field(default=None, max_length=200)
RETURNABLE = {"Delivered"}


class Reason(BaseModel):
    reason: str = Field(default="", max_length=500)


class Address(BaseModel):
    address: str = Field(min_length=10, max_length=500)


class OrderEdit(BaseModel):
    """Only the fields given are changed. A new phone (and name) moves the
    order to that customer, made if they are new."""

    phone: str | None = Field(default=None, examples=["+918826889512"])
    customer_name: str | None = Field(default=None, examples=["Shiwesh Shiwam"])
    pincode: str | None = Field(default=None, examples=["110001"])
    items: str | None = None
    status: str | None = Field(
        default=None,
        examples=["Delayed"],
        description="Order placed, Packed, Shipped, Out for delivery, Delayed, Delivered, Cancelled, …",
    )
    status_detail: str | None = Field(default=None, examples=["Held at the hub due to heavy rain"])
    ordered_on: str | None = Field(default=None, examples=["2026-10-30"])
    expected_on: str | None = Field(default=None, examples=["2026-11-04"])
    delivered_on: str | None = None
    courier: str | None = None
    awb: str | None = None
    tracking_url: str | None = None
    delivery_address: str | None = None
    payment_mode: str | None = Field(default=None, examples=["COD"], description="COD or Prepaid")
    amount: float | None = Field(default=None, examples=[1299])
    language: str | None = Field(default=None, examples=["hi-IN"], description="The customer's language")
    ndr_reason: str | None = Field(default=None, examples=["Customer not reachable"])
    attempt_count: int | None = Field(default=None, ge=0)


class NewOrder(OrderEdit):
    order_id: str = Field(min_length=3, max_length=40, examples=["IDS-249001"])
    phone: str = Field(examples=["+918826889512"])
    items: str = Field(examples=["Steel water bottle"])
    status: str = Field(examples=["Packed"])


def store_app(
    title: str,
    customers: dict[str, dict],
    orders: dict[str, dict],
    *,
    slug: str = "",
    id_prefix: str = "C",
    original: Callable[[], tuple[dict[str, dict], dict[str, dict]]] | None = None,
) -> FastAPI:
    """One store's order API over its own customers and orders (changed in
    place, and saved when the store has a slug)."""
    app = FastAPI(title=title, description=__doc__, version="1.0.0", dependencies=[Depends(require_key)])
    state = STATE_DIR / f"{slug}.json" if slug else None
    if state is not None and state.exists():
        try:
            saved = json.loads(state.read_text())
            customers.clear(), customers.update(saved["customers"])
            orders.clear(), orders.update(saved["orders"])
        except (ValueError, KeyError) as exc:
            logger.warning("%s: saved test data unreadable, using the original: %s", slug, exc)
    by_phone = {c["phone"]: cid for cid, c in customers.items()}

    def _save() -> None:
        if state is None:
            return
        try:
            state.parent.mkdir(parents=True, exist_ok=True)
            tmp = state.with_suffix(".tmp")
            tmp.write_text(json.dumps({"customers": customers, "orders": orders}, ensure_ascii=False))
            tmp.replace(state)
        except OSError as exc:  # read-only disk: the change still holds until a restart
            logger.warning("%s: could not save test data: %s", slug, exc)

    def _customer(phone: str, name: str | None, pincode: str | None, language: str | None = None) -> str:
        """The customer with this mobile, made if new; their name updated if given."""
        phone = valid_mobile(phone)
        cid = by_phone.get(phone)
        if cid is None:
            cid = f"{id_prefix}{phone[-6:]}"
            while cid in customers and customers[cid]["phone"] != phone:
                cid += "X"
            customers[cid] = {"customer_id": cid, "name": name or "Test customer", "phone": phone,
                              "pincode": pincode or "", "language": language or "en-IN"}
            by_phone[phone] = cid
        elif name:
            customers[cid]["name"] = name
        if language:
            customers[cid]["language"] = language
        return cid

    def _get(order_id: str) -> dict:
        o = orders.get(order_id.strip().upper())
        if o is None:
            raise HTTPException(404, f"No order {order_id}.")
        return o

    @app.get("/customers", operation_id="findCustomer", summary="Find a customer by mobile number")
    def find_customer(phone: str = Query(description="The customer's mobile, any format")) -> dict:
        cid = by_phone.get(clean_phone(phone))
        if cid is None:
            raise HTTPException(404, "No customer with that mobile.")
        return customers[cid]

    @app.get("/orders", operation_id="listOrders", summary="A customer's orders, newest first")
    def list_orders(
        phone: str | None = Query(default=None, description="The customer's mobile"),
        customer_id: str | None = Query(default=None),
    ) -> dict:
        if not phone and not customer_id:
            raise HTTPException(422, "Give phone or customer_id.")
        cid = customer_id or by_phone.get(clean_phone(phone))
        mine = [o for o in orders.values() if o["customer_id"] == cid]
        return {"orders": sorted(mine, key=lambda o: o["ordered_on"] or "", reverse=True)}

    # --- cash on delivery and delivery problems (before /orders/{order_id}) -------

    def _who(o: dict) -> dict:
        c = customers.get(o["customer_id"], {})
        return {"mobile": o["phone"], "customer_name": o.get("customer_name") or c.get("name"),
                "language": c.get("language", "en-IN")}

    @app.get(
        "/orders/cod-pending", operation_id="listCodPendingOrders", tags=["Cash on delivery"],
        summary="Cash-on-delivery orders waiting for the customer to confirm, for a COD confirmation campaign",
    )
    def cod_pending() -> dict:
        rows = [{**_who(o), "order_id": o["order_id"], "total": o.get("amount"), "items": o["items"],
                 "payment_mode": o.get("payment_mode", "Prepaid"), "created_at": o["ordered_on"],
                 "delivery_address": o.get("delivery_address")}
                for o in orders.values() if o["status"] == "Pending confirmation"]
        return {"count": len(rows), "orders": sorted(rows, key=lambda r: r["created_at"] or "")}

    @app.get(
        "/orders/ndr", operation_id="listFailedDeliveries", tags=["Delivery problems"],
        summary="Failed deliveries (NDR) with the courier's reason and attempts, for a reattempt campaign",
    )
    def ndr() -> dict:
        rows = [{**_who(o), "order_id": o["order_id"], "items": o["items"], "total": o.get("amount"),
                 "payment_mode": o.get("payment_mode", "Prepaid"), "courier_name": o.get("courier"),
                 "awb_code": o.get("awb"), "ndr_reason": o.get("ndr_reason") or "Delivery attempt failed",
                 "attempt_count": o.get("attempt_count", 1), "last_attempt_on": o.get("last_attempt_on"),
                 "delivery_address": o.get("delivery_address")}
                for o in orders.values() if o["status"] == "Delivery failed"]
        return {"count": len(rows), "shipments": rows}

    @app.get("/orders/{order_id}", operation_id="getOrder", summary="One order")
    def get_order(order_id: str) -> dict:
        return _get(order_id)

    @app.post("/orders/{order_id}/cancel", operation_id="cancelOrder", summary="Cancel an order before it ships")
    def cancel_order(order_id: str, body: Reason) -> dict:
        o = _get(order_id)
        if o["status"] not in CANCELLABLE:
            raise HTTPException(409, f"Order {o['order_id']} is {o['status']} and can no longer be cancelled.")
        o.update(status="Cancelled", cancelled_at=now_iso(), cancel_reason=body.reason)
        _save()
        return {"message": f"Order {o['order_id']} is cancelled. The refund reaches you in 5 to 7 working days.", "order": o}

    @app.post("/orders/{order_id}/return", operation_id="startReturn", summary="Start a return for a delivered order")
    def start_return(order_id: str, body: Reason) -> dict:
        o = _get(order_id)
        if o["status"] not in RETURNABLE:
            raise HTTPException(409, f"Order {o['order_id']} is {o['status']}; only delivered orders can be returned.")
        o.update(status="Return requested", return_pickup_on=day(2), return_reason=body.reason)
        _save()
        return {"message": f"Return started for {o['order_id']}. Pickup on {o['return_pickup_on']}.", "order": o}

    @app.post("/orders/{order_id}/address", operation_id="changeAddress", summary="Change the delivery address before it ships")
    def change_address(order_id: str, body: Address) -> dict:
        o = _get(order_id)
        if o["status"] not in ADDRESS_CHANGEABLE:
            raise HTTPException(409, f"Order {o['order_id']} is {o['status']}; the address can no longer change.")
        o["delivery_address"] = body.address.strip()
        _save()
        return {"message": f"The delivery address for {o['order_id']} is changed.", "order": o}

    @app.post(
        "/orders/{order_id}/confirm", operation_id="confirmCodOrder", tags=["Cash on delivery"],
        summary="Confirm a cash-on-delivery order so it is packed and shipped",
    )
    def confirm_order(order_id: str) -> dict:
        o = _get(order_id)
        if o["status"] != "Pending confirmation":
            raise HTTPException(409, f"Order {o['order_id']} is {o['status']}; only orders pending confirmation can be confirmed.")
        o.update(status="Order placed", confirmed_at=now_iso())
        _save()
        return {"message": f"Order {o['order_id']} is confirmed. Keep ₹{o.get('amount') or 0:,.0f} ready at delivery.",
                "order": o}

    @app.get(
        "/orders/{order_id}/tracking", operation_id="getShipmentTracking", tags=["Delivery problems"],
        summary="Where a shipment is: status, courier, AWB, last scan, expected delivery date, tracking link",
    )
    def tracking(order_id: str) -> dict:
        o = _get(order_id)
        st = o["status"]
        shipment_status = {
            "Pending confirmation": "Awaiting confirmation", "Order placed": "Not yet shipped", "Packed": "Ready to ship",
            "Shipped": "In transit", "Delayed": "Delayed in transit", "Out for delivery": "Out for delivery",
            "Delivered": "Delivered", "Delivery failed": "Undelivered", "Reattempt scheduled": "Reattempt scheduled",
            "Cancelled": "Cancelled", "Return requested": "Return pickup scheduled",
        }.get(st, st)
        shipped = st not in NOT_SHIPPED
        hub = f"{o.get('courier') or 'Courier'} hub, pincode {o.get('pincode') or ''}".strip()
        last_scan = None
        if shipped:
            when = o.get("delivered_on") or o.get("last_attempt_on") or o.get("expected_on") or o["ordered_on"]
            activity = {"Delivered": "Delivered", "Out for delivery": "Out for delivery",
                        "Delivery failed": o.get("ndr_reason") or "Delivery attempt failed",
                        "Delayed": o.get("status_detail") or "Held at hub"}.get(st, "Arrived at hub")
            last_scan = {"location": hub, "activity": activity, "scanned_at": f"{when}T09:30:00+05:30" if when else None}
        return {
            "order_id": o["order_id"],
            "shipment_status": shipment_status,
            "courier_name": o.get("courier") if shipped else None,
            "awb_code": o.get("awb") if shipped else None,
            "current_location": last_scan["location"] if last_scan else None,
            "last_scan": last_scan,
            "edd": o.get("reattempt_on") or o.get("expected_on"),
            "delivered_on": o.get("delivered_on"),
            "tracking_url": o.get("tracking_url") if shipped else None,
        }

    @app.post(
        "/orders/{order_id}/delivery", operation_id="rescheduleDelivery", tags=["Delivery problems"],
        summary="After a failed delivery: book a reattempt, with a corrected address or date if given",
    )
    def reattempt(order_id: str, body: Reattempt) -> dict:
        o = _get(order_id)
        if o["status"] not in ("Delivery failed", "Reattempt scheduled"):
            raise HTTPException(409, f"Order {o['order_id']} is {o['status']}; a reattempt is only for a failed delivery.")
        when = body.reattempt_date or day(1)
        if when < day(0):
            raise HTTPException(422, "reattempt_date must be today or later, as YYYY-MM-DD.")
        if body.address:
            o["delivery_address"] = body.address.strip()
        if body.landmark:
            o["delivery_address"] = f"{o['delivery_address']} (near {body.landmark.strip()})"
        o.update(status="Reattempt scheduled", reattempt_on=when, expected_on=when)
        _save()
        return {"message": f"Delivery of {o['order_id']} will be tried again on {when}.", "order": o}

    @app.get(
        "/orders/{order_id}/refund", operation_id="getRefundStatus", tags=["Refunds"],
        summary="Refund status for a cancelled or returned order: amount, status, reference and expected date",
    )
    def refund(order_id: str) -> dict:
        o = _get(order_id)
        base = {"order_id": o["order_id"], "payment_mode": o.get("payment_mode", "Prepaid"), "refund_amount": 0,
                "refund_status": "Not applicable", "refund_ref": None, "initiated_on": None, "expected_by": None}
        if o.get("refund"):
            return {**base, **o["refund"]}
        if o["status"] not in ("Cancelled", "Return requested", "Returned"):
            return {**base, "message": f"Order {o['order_id']} is {o['status']}; there is no refund."}
        if o.get("payment_mode") == "COD" and not o.get("delivered_on"):
            return {**base, "message": "Cash on delivery, not delivered: nothing was paid, so nothing is refunded."}
        started = (o.get("cancelled_at") or "")[:10] or o.get("return_pickup_on") or day(0)
        status = "Initiated" if o["status"] == "Cancelled" else "Awaiting pickup"
        return {**base, "refund_amount": o.get("amount") or 0, "refund_status": status,
                "refund_ref": f"RF{o['order_id'].replace('-', '')}", "initiated_on": started,
                "expected_by": started if status != "Initiated" else day(5), "refund_mode": "Original payment method"}

    # --- test data: change the store's orders from Swagger ------------------------

    def _apply(o: dict, edit: OrderEdit) -> None:
        given = edit.model_dump(exclude_unset=True)
        if "phone" in given or "customer_name" in given or "language" in given:
            cid = _customer(given.get("phone") or o["phone"], given.get("customer_name"), given.get("pincode"),
                            given.get("language"))
            c = customers[cid]
            o.update(customer_id=cid, phone=c["phone"])
            if "customer_name" in o or "customer_name" in given:
                o["customer_name"] = c["name"]
        for key in ("pincode", "items", "status", "status_detail", "ordered_on", "expected_on",
                    "delivered_on", "courier", "awb", "tracking_url", "delivery_address",
                    "payment_mode", "amount", "ndr_reason", "attempt_count"):
            if key in given:
                o[key] = given[key]

    @app.patch(
        "/orders/{order_id}", operation_id="testEditOrder", tags=["Test data"],
        summary="Test data: change an order (only the fields you give)",
    )
    def edit_order(order_id: str, body: OrderEdit) -> dict:
        o = _get(order_id)
        _apply(o, body)
        _save()
        return o

    @app.post(
        "/orders", operation_id="testAddOrder", tags=["Test data"], status_code=201,
        summary="Test data: add an order",
    )
    def add_order(body: NewOrder) -> dict:
        oid = body.order_id.strip().upper()
        if oid in orders:
            raise HTTPException(409, f"Order {oid} exists; change it with PATCH instead.")
        cid = _customer(body.phone, body.customer_name, body.pincode, body.language)
        c = customers[cid]
        o = {"payment_mode": "Prepaid", "order_id": oid, "customer_id": cid, "customer_name": c["name"], "phone": c["phone"],
             "pincode": body.pincode or c["pincode"], "items": body.items, "status": body.status,
             "status_detail": "", "ordered_on": day(0), "expected_on": None, "delivered_on": None,
             "courier": "", "awb": "", "tracking_url": "", "delivery_address": f"Pincode {body.pincode or c['pincode']}"}
        _apply(o, body)
        orders[oid] = o
        _save()
        return o

    @app.post(
        "/reset", operation_id="testReset", tags=["Test data"],
        summary="Test data: back to the original orders (every change is undone)",
    )
    def reset() -> dict:
        if original is None:
            raise HTTPException(409, "This store has no original to go back to.")
        base_customers, base_orders = original()
        customers.clear(), customers.update(base_customers)
        orders.clear(), orders.update(base_orders)
        by_phone.clear(), by_phone.update({c["phone"]: cid for cid, c in customers.items()})
        if state is not None and state.exists():
            state.unlink()
        return {"message": "Back to the original data.", "orders": len(orders)}

    return app


# ---- Kettle & Co ---------------------------------------------------------------

KETTLE_CUSTOMERS = {f"KC-C{100 + i}": {**p, "customer_id": f"KC-C{100 + i}"} for i, p in enumerate(ALL_PEOPLE)}

#: (customer, item, status, ordered days ago, expected in days or None, delivered days ago or None)
#: The first eight are prepaid; the rest are in _COD_AND_NDR below.
_ORDERS = [
    ("KC-C100", "Blue electric kettle", "Shipped", -3, 1, None),
    ("KC-C100", "Steel water bottle (1 L)", "Delivered", -12, None, -6),
    ("KC-C100", "Mixer grinder 750 W", "Packed", 0, 4, None),
    ("KC-C101", "Pressure cooker 5 L", "Delayed", -9, -2, None),
    ("KC-C101", "Non-stick tawa", "Delivered", -20, None, -14),
    ("KC-C102", "LED desk lamp", "Order placed", 0, 6, None),
    ("KC-C102", "Cotton bedsheet set", "Out for delivery", -4, 0, None),
    ("KC-C103", "Air fryer 4 L", "Delivered", -8, None, -2),
    ("KC-C101", "Induction cooktop", "Pending confirmation", 0, 5, None),
    ("KC-C102", "Copper water jug", "Pending confirmation", -1, 4, None),
    ("KC-C104", "Steel lunch box set", "Pending confirmation", 0, 5, None),
    ("KC-C105", "Wet grinder 2 L", "Delivery failed", -6, -1, None),
    ("KC-C103", "Ceramic dinner set", "Delivery failed", -7, -2, None),
    ("KC-C106", "Bluetooth speaker", "Cancelled", -10, None, None),
]
#: order → (payment mode, amount, extra fields). Orders not listed are prepaid.
_COD_AND_NDR = {
    "KC-240109": ("COD", 2499, {}),
    "KC-240110": ("COD", 899, {}),
    "KC-240111": ("COD", 649, {}),
    "KC-240112": ("COD", 3299, {"ndr_reason": "Customer not reachable", "attempt_count": 1, "last_attempt_on": -1}),
    "KC-240113": ("Prepaid", 1899, {"ndr_reason": "Address incomplete", "attempt_count": 2, "last_attempt_on": -2}),
    "KC-240114": ("Prepaid", 1499, {"cancelled_at": -9, "refund": {
        "refund_amount": 1499, "refund_status": "Processed", "refund_ref": "RFKC240114", "initiated_on": -9,
        "expected_by": -4, "processed_on": -5, "refund_mode": "UPI"}}),
}


def _order(n: int, row) -> dict:
    cid, item, status, ordered, expected, delivered = row
    c = KETTLE_CUSTOMERS[cid]
    return {
        "order_id": f"KC-{240100 + n}",
        "customer_id": cid,
        "phone": c["phone"],
        "pincode": c["pincode"],
        "items": item,
        "status": status,
        "ordered_on": day(ordered),
        "expected_on": day(expected) if expected is not None else None,
        "delivered_on": day(delivered) if delivered is not None else None,
        "courier": "Delhivery" if n % 2 else "BlueDart",
        "awb": f"AWB{770100 + n}",
        "tracking_url": f"https://track.example.com/AWB{770100 + n}",
        "delivery_address": c["address"],
        "amount": [1299, 449, 3499, 2799, 899, 1599, 1999, 5499][n % 8],
        "payment_mode": "Prepaid",
    }


def _cod_and_ndr(o: dict) -> dict:
    mode, amount, extra = _COD_AND_NDR.get(o["order_id"], ("Prepaid", o["amount"], {}))
    o.update(payment_mode=mode, amount=amount)
    for key, value in extra.items():
        if key == "refund":
            value = {k: day(v) if k in ("initiated_on", "expected_by", "processed_on") else v for k, v in value.items()}
        elif key == "last_attempt_on":
            value = day(value)
        elif key == "cancelled_at":
            value = day(value) + "T10:00:00+05:30"
        o[key] = value
    if o["status"] == "Pending confirmation":
        o["courier"], o["awb"], o["tracking_url"] = "", "", ""
    return o


def _kettle() -> tuple[dict[str, dict], dict[str, dict]]:
    return (
        copy.deepcopy(KETTLE_CUSTOMERS),
        {o["order_id"]: o for o in (_cod_and_ndr(_order(n, r)) for n, r in enumerate(_ORDERS, start=1))},
    )


_KC, KETTLE_ORDERS = _kettle()
app = store_app(
    "Kettle & Co order system (sample client)", _KC, KETTLE_ORDERS, slug="shop", id_prefix="KC-C", original=_kettle
)
# Unfinished carts and pay-online links (the cart-recovery agent), Kettle only.
attach_carts(app, _KC, KETTLE_ORDERS)


# ---- Miso ----------------------------------------------------------------------


def _miso() -> tuple[dict[str, dict], dict[str, dict]]:
    rows = json.loads((Path(__file__).with_name("sample_miso_orders.json")).read_text())
    customers: dict[str, dict] = {}
    orders: dict[str, dict] = {}
    for r in rows:
        cid = "MS-C" + r["phone"][-6:]
        customers.setdefault(cid, {"customer_id": cid, "name": r["name"], "phone": r["phone"], "pincode": r["pincode"]})
        orders[r["ref"]] = {
            "order_id": r["ref"],
            "customer_id": cid,
            "customer_name": r["name"],
            "phone": r["phone"],
            "pincode": r["pincode"],
            "items": r["items"],
            "status": r["status"],
            "status_detail": r["detail"],
            "ordered_on": day(r["ordered"]) if r["ordered"] is not None else None,
            "expected_on": day(r["expected"]) if r["expected"] is not None else None,
            "delivered_on": day(r["delivered"]) if r["delivered"] is not None else None,
            "courier": r["courier"],
            "awb": r["awb"],
            "tracking_url": r["tracking"],
            "delivery_address": f"Pincode {r['pincode']}",
        }
    return customers, orders


MISO_CUSTOMERS, MISO_ORDERS = _miso()
miso_app = store_app(
    "Miso order system (sample client)", MISO_CUSTOMERS, MISO_ORDERS, slug="miso", id_prefix="MS-C", original=_miso
)
