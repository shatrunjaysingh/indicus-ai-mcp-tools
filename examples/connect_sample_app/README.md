# Demo Store — a sample client app for the Connect API

A store's chat screen and the store's own server, connected to the IndicusAI
help bot exactly the way a real client's app would be. Use it to test an
integration end to end without any client, to show prospects what their
integration looks like, and as a working reference for clients' developers
(`app.py` is the whole server side, about 150 lines).

## Run it

1. In IndicusAI, open the workspace with the help bot → **Customer help →
   Apps & API → Add an integration** (e.g. "Demo Store"). Copy the key and the
   customer secret it shows (shown once).
2. Pick one or two mobiles that are on that workspace's orders (**Customer help
   → Orders**) to log in as.
3. From the repo root:

```bash
read -s -p "Connect key: " CONNECT_KEY; echo; export CONNECT_KEY
read -s -p "Customer secret: " CUSTOMER_SECRET; echo; export CUSTOMER_SECRET
export DEMO_CUSTOMERS="Asha:+919000000999,Visitor test:+919111111111"
.venv/bin/python examples/connect_sample_app/app.py
```

4. Open http://localhost:8090. Choose who is logged in (or "Visitor"), and chat.

The right-hand panel shows what the store's server sends to IndicusAI and the
events it gets back (`typing → message → done`, `handed_over`).

## Settings

| Variable | Default | |
|---|---|---|
| `CONNECT_KEY` | — | The integration's key (`ick_…`). Required. |
| `CUSTOMER_SECRET` | — | Signs customer tokens (`ics_…`). Required. |
| `WEBHOOK_SECRET` | — | Checks webhooks (`whs_…`). Only for testing webhooks. |
| `DEMO_CUSTOMERS` | `Test customer:+919000000999` | Who can "log in", `Name:+91…` comma-separated |
| `INDICUS_API` | `https://indicus-ai.com/api/v1` | |
| `PORT` | `8090` | |

## Testing webhooks

IndicusAI posts webhooks to an https address, so this app has to be reachable
from the internet: run it on a server with https, or behind a tunnel you trust,
and set the integration's webhook to `https://<that address>/webhook` and
`WEBHOOK_SECRET` here. Each webhook appears in the panel with whether its
signature checked out.

## What to try

- As a logged-in customer: "Where is my order?" — the bot lists their orders
  without asking anything.
- As a visitor: the same — it asks for the last 4 digits of the order's mobile
  or the delivery pincode.
- Logged in with two orders: "Where are my orders?" — order cards, and a
  button per order; tap one to ask about it.
- With order changes switched on (**Customer help → Order changes**): "Cancel
  my order" — the bot asks to confirm with **Yes** / **No** buttons.
- "What is your return policy?" — from the workspace's FAQ.
- "I want to talk to a person" — a reference, and the conversation appears in
  **Customer help → Inbox**. Take it there and reply: the reply appears in this
  chat as a "Team" message (through IndicusAI's live events stream — no
  webhook needed). Give it back to the bot and the assistant answers again.

It never stores the key in the page: everything secret stays in `app.py`'s
process, which is the point a client's developers should copy.
