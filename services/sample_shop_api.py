"""Kettle & Co — a sample online store's back office (sample_clients.py).

What a real store's order system offers a help bot: find a customer, their
orders, one order; and three changes — cancel, return, change the delivery
address — each allowed only in the right state, as a real system would refuse.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from sample_clients import PEOPLE, clean_phone, day, now_iso, require_key

app = FastAPI(
    title="Kettle & Co order system (sample client)",
    description=__doc__,
    version="1.0.0",
    dependencies=[Depends(require_key)],
)

CUSTOMERS = {f"KC-C{100 + i}": {**p, "customer_id": f"KC-C{100 + i}"} for i, p in enumerate(PEOPLE)}
_BY_PHONE = {c["phone"]: cid for cid, c in CUSTOMERS.items()}

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
    c = CUSTOMERS[cid]
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


ORDERS = {o["order_id"]: o for o in (_order(n, r) for n, r in enumerate(_ORDERS, start=1))}

CANCELLABLE = {"Order placed", "Packed"}
ADDRESS_CHANGEABLE = {"Order placed", "Packed"}
RETURNABLE = {"Delivered"}


def _get(order_id: str) -> dict:
    o = ORDERS.get(order_id.strip().upper())
    if o is None:
        raise HTTPException(404, f"No order {order_id}.")
    return o


@app.get("/customers", operation_id="findCustomer", summary="Find a customer by mobile number")
def find_customer(phone: str = Query(description="The customer's mobile, any format")) -> dict:
    cid = _BY_PHONE.get(clean_phone(phone))
    if cid is None:
        raise HTTPException(404, "No customer with that mobile.")
    return CUSTOMERS[cid]


@app.get("/orders", operation_id="listOrders", summary="A customer's orders, newest first")
def list_orders(
    phone: str | None = Query(default=None, description="The customer's mobile"),
    customer_id: str | None = Query(default=None),
) -> dict:
    if not phone and not customer_id:
        raise HTTPException(422, "Give phone or customer_id.")
    cid = customer_id or _BY_PHONE.get(clean_phone(phone))
    mine = [o for o in ORDERS.values() if o["customer_id"] == cid]
    return {"orders": sorted(mine, key=lambda o: o["ordered_on"], reverse=True)}


@app.get("/orders/{order_id}", operation_id="getOrder", summary="One order")
def get_order(order_id: str) -> dict:
    return _get(order_id)


class Reason(BaseModel):
    reason: str = Field(default="", max_length=500)


class Address(BaseModel):
    address: str = Field(min_length=10, max_length=500)


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
