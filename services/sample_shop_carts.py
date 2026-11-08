"""Kettle & Co's unfinished carts and pay-online links (sample_shop_api.py).

What a store offers a cart-recovery agent:

- Carts started and not finished, with the link to continue (for a campaign),
  one cart by its id (and whether it has since become an order).
- A payment link for a cash-on-delivery order, so the customer pays online
  instead; paying marks the order prepaid.

The pages a customer opens (finish the order, pay) need no key; every API
route does. Test data: POST /carts adds a cart on your mobile, left as many
minutes ago as you say; POST /carts/reset goes back. Saved in
state/shop-carts.json across restarts.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.routing import Route

from sample_clients import IST, TestData, now_iso, page, public_url, remember_origin, valid_mobile

SLUG = "shop"
BUSINESS = "Kettle & Co"

#: (cart, customer, items, total, left minutes ago, ordered since)
_CARTS = [
    ("CART-9001", "KC-C100", "a ceramic kettle and two mugs", 1899, 120, False),
    ("CART-9002", "KC-C103", "a cast-iron tawa", 1249, 15, False),
    ("CART-9003", "KC-C102", "a steel lunch box set", 899, 180, True),
    ("CART-9004", "KC-C104", "a mixer grinder", 3499, 300, False),
]


class CartIn(BaseModel):
    customer_name: str = Field(min_length=2, max_length=120, examples=["Shiwesh Shiwam"])
    mobile: str = Field(examples=["+918826889512"])
    items: str = Field(default="a blue electric kettle")
    total: float = Field(default=1299, gt=0)
    minutes_ago: int = Field(default=90, ge=0, le=10080, description="How long ago the cart was left")
    language: str = Field(default="en-IN", examples=["hi-IN"])

class LinkIn(BaseModel):
    order_id: str = Field(examples=["KC-240109"])
    amount: float | None = Field(default=None, gt=0, description="Rupees; blank: the order total")
    mobile: str | None = None


def attach(app: FastAPI, customers: dict[str, dict], orders: dict[str, dict]) -> None:
    """Add the cart and payment-link routes to the store's app."""

    def seed() -> dict[str, dict]:
        carts = {}
        for cart_id, cid, items, total, minutes, ordered in _CARTS:
            c = customers.get(cid, {})
            left = datetime.now(IST) - timedelta(minutes=minutes)
            carts[cart_id] = {"cart_id": cart_id, "customer_name": c.get("name"), "mobile": c.get("phone"),
                              "language": c.get("language", "en-IN"), "items": items, "total": total,
                              "abandoned_at": left.isoformat(timespec="seconds"), "ordered": ordered}
        return {"carts": carts, "payment_links": {}}

    db = TestData("shop-carts", seed)
    keyed = [Depends(remember_origin)]  # the app already needs the key on every API route

    def view(c: dict) -> dict:
        return {**c, "status": "Ordered" if c["ordered"] else "Abandoned",
                "checkout_url": public_url(SLUG, f"checkout/{c['cart_id']}")}

    @app.get("/carts/abandoned", dependencies=keyed, operation_id="listAbandonedCarts", tags=["Carts"],
             summary="Carts started and not finished in the last 7 days, for a reminder campaign")
    def abandoned() -> dict:
        since = (datetime.now(IST) - timedelta(days=7)).isoformat()
        rows = [view(c) for c in db["carts"].values() if not c["ordered"] and c["abandoned_at"] >= since]
        return {"count": len(rows), "carts": sorted(rows, key=lambda r: r["abandoned_at"], reverse=True)}

    @app.get("/carts/{cart_id}", dependencies=keyed, operation_id="getCart", tags=["Carts"],
             summary="One cart: items, total, the link to continue, and whether it became an order")
    def get_cart(cart_id: str) -> dict:
        c = db["carts"].get(cart_id.strip().upper())
        if c is None:
            raise HTTPException(404, f"No cart {cart_id}.")
        return view(c)

    @app.post("/carts", dependencies=keyed, operation_id="testAddCart", tags=["Test data"], status_code=201,
              summary="Test data: add an unfinished cart (your mobile), left some minutes ago")
    def add_cart(body: CartIn) -> dict:
        cart_id = db.next_id("carts", "CART-", 9001)
        left = datetime.now(IST) - timedelta(minutes=body.minutes_ago)
        db["carts"][cart_id] = {"cart_id": cart_id, "customer_name": body.customer_name.strip(), "mobile": valid_mobile(body.mobile),
                                "language": body.language, "items": body.items, "total": body.total,
                                "abandoned_at": left.isoformat(timespec="seconds"), "ordered": False}
        db.save()
        return view(db["carts"][cart_id])

    @app.post("/carts/reset", operation_id="testResetCarts", tags=["Test data"],
              summary="Test data: back to the original carts and payment links")
    def reset_carts() -> dict:
        return db.reset()

    @app.post("/payment-links", dependencies=keyed, operation_id="createOrderPaymentLink", tags=["Payments"], status_code=201,
              summary="A link to pay a cash-on-delivery order online (the order becomes prepaid once paid)")
    def create_link(body: LinkIn) -> dict:
        o = orders.get(body.order_id.strip().upper())
        if o is None:
            raise HTTPException(404, f"No order {body.order_id}.")
        if str(o.get("payment_mode", "")).upper() != "COD":
            raise HTTPException(409, f"Order {o['order_id']} is already paid online.")
        link_id = db.next_id("payment_links", "kpl_", 50001)
        link = {"id": link_id, "order_id": o["order_id"], "amount": round(body.amount or o["amount"], 2),
                "mobile": valid_mobile(body.mobile) if body.mobile else o.get("phone"),
                "short_url": public_url(SLUG, f"pay/{link_id}"),
                "expire_by": (datetime.now(IST) + timedelta(days=2)).isoformat(timespec="seconds"),
                "status": "created", "created_at": now_iso()}
        db["payment_links"][link_id] = link
        db.save()
        return link

    # Pages the customer opens: plain routes, outside the key every API route needs.
    async def checkout_page(request: Request) -> HTMLResponse:
        c = db["carts"].get(request.path_params["cart_id"])
        if c is None:
            return HTMLResponse(page("Link not found", ["This cart does not exist or was reset."]))
        if request.method == "POST" or c["ordered"]:
            if not c["ordered"]:
                c["ordered"] = True
                db.save()
            return HTMLResponse(page("Order placed", [f"Thank you, {c['customer_name']}.", f"{c['items'].capitalize()}: ₹{c['total']:,.0f}."]))
        return HTMLResponse(page(f"Finish your order at {BUSINESS}", [c["items"].capitalize(), f"Total ₹{c['total']:,.0f}"], button="Place order"))

    async def pay_page(request: Request) -> HTMLResponse:
        link = db["payment_links"].get(request.path_params["link_id"])
        if link is None:
            return HTMLResponse(page("Link not found", ["This payment link does not exist or was reset."]))
        if request.method == "POST" and link["status"] != "paid":
            link.update(status="paid", paid_at=now_iso())
            o = orders.get(link["order_id"])
            if o is not None:
                o["payment_mode"], o["paid_online"] = "Prepaid", True
            db.save()
        if link["status"] == "paid":
            return HTMLResponse(page("Paid", [f"₹{link['amount']:,.0f} received for order {link['order_id']}. Thank you."]))
        return HTMLResponse(page(f"Pay ₹{link['amount']:,.0f} to {BUSINESS}", [f"Order {link['order_id']}"], button="Pay now"))

    app.router.routes.append(Route("/checkout/{cart_id}", checkout_page, methods=["GET", "POST"]))
    app.router.routes.append(Route("/pay/{link_id}", pay_page, methods=["GET", "POST"]))
