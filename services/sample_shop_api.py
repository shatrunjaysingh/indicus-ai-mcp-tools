"""Sample online stores' back offices (sample_clients.py).

What a real store's order system offers a help bot: find a customer, their
orders, one order; and three changes — cancel, return, change the delivery
address — each allowed only in the right state, as a real system would refuse.

Two stores share the code, each its own app with its own orders:

    /shop   Kettle & Co — eight orders for the four shared test people.
    /miso   Miso — the 300 orders the Customer Help Line demo used to upload
            (IDS-240001 … IDS-240300, all on +919000… test numbers), kept in
            sample_miso_orders.json with dates as days from today.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from sample_clients import PEOPLE, clean_phone, day, now_iso, require_key

CANCELLABLE = {"Order placed", "Packed"}
ADDRESS_CHANGEABLE = {"Order placed", "Packed"}
RETURNABLE = {"Delivered"}


class Reason(BaseModel):
    reason: str = Field(default="", max_length=500)


class Address(BaseModel):
    address: str = Field(min_length=10, max_length=500)


def store_app(title: str, customers: dict[str, dict], orders: dict[str, dict]) -> FastAPI:
    """One store's order API over its own customers and orders (changed in place)."""
    app = FastAPI(title=title, description=__doc__, version="1.0.0", dependencies=[Depends(require_key)])
    by_phone = {c["phone"]: cid for cid, c in customers.items()}

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

    @app.get("/orders/{order_id}", operation_id="getOrder", summary="One order")
    def get_order(order_id: str) -> dict:
        return _get(order_id)

    @app.post("/orders/{order_id}/cancel", operation_id="cancelOrder", summary="Cancel an order before it ships")
    def cancel_order(order_id: str, body: Reason) -> dict:
        o = _get(order_id)
        if o["status"] not in CANCELLABLE:
            raise HTTPException(409, f"Order {o['order_id']} is {o['status']} and can no longer be cancelled.")
        o.update(status="Cancelled", cancelled_at=now_iso(), cancel_reason=body.reason)
        return {"message": f"Order {o['order_id']} is cancelled. The refund reaches you in 5 to 7 working days.", "order": o}

    @app.post("/orders/{order_id}/return", operation_id="startReturn", summary="Start a return for a delivered order")
    def start_return(order_id: str, body: Reason) -> dict:
        o = _get(order_id)
        if o["status"] not in RETURNABLE:
            raise HTTPException(409, f"Order {o['order_id']} is {o['status']}; only delivered orders can be returned.")
        o.update(status="Return requested", return_pickup_on=day(2), return_reason=body.reason)
        return {"message": f"Return started for {o['order_id']}. Pickup on {o['return_pickup_on']}.", "order": o}

    @app.post("/orders/{order_id}/address", operation_id="changeAddress", summary="Change the delivery address before it ships")
    def change_address(order_id: str, body: Address) -> dict:
        o = _get(order_id)
        if o["status"] not in ADDRESS_CHANGEABLE:
            raise HTTPException(409, f"Order {o['order_id']} is {o['status']}; the address can no longer change.")
        o["delivery_address"] = body.address.strip()
        return {"message": f"The delivery address for {o['order_id']} is changed.", "order": o}

    return app


# ---- Kettle & Co ---------------------------------------------------------------

KETTLE_CUSTOMERS = {f"KC-C{100 + i}": {**p, "customer_id": f"KC-C{100 + i}"} for i, p in enumerate(PEOPLE)}

#: (customer, item, status, ordered days ago, expected in days or None, delivered days ago or None)
_ORDERS = [
    ("KC-C100", "Blue electric kettle", "Shipped", -3, 1, None),
    ("KC-C100", "Steel water bottle (1 L)", "Delivered", -12, None, -6),
    ("KC-C100", "Mixer grinder 750 W", "Packed", 0, 4, None),
    ("KC-C101", "Pressure cooker 5 L", "Delayed", -9, -2, None),
    ("KC-C101", "Non-stick tawa", "Delivered", -20, None, -14),
    ("KC-C102", "LED desk lamp", "Order placed", 0, 6, None),
    ("KC-C102", "Cotton bedsheet set", "Out for delivery", -4, 0, None),
    ("KC-C103", "Air fryer 4 L", "Delivered", -8, None, -2),
]


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
    }


KETTLE_ORDERS = {o["order_id"]: o for o in (_order(n, r) for n, r in enumerate(_ORDERS, start=1))}

app = store_app("Kettle & Co order system (sample client)", KETTLE_CUSTOMERS, KETTLE_ORDERS)


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
miso_app = store_app("Miso order system (sample client)", MISO_CUSTOMERS, MISO_ORDERS)
