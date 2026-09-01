# indicus-ai-mcp-tools

Demo services for the IndicusAI platform, served two ways at once:

- **REST**, at `/soc`, `/utility`, `/payer`, `/iam` — registered as built-in
  custom HTTP tools, one tool per endpoint
- **MCP**, at `/mcp` — one connector carrying every tool on the server

Both surfaces call the same functions over the same fixtures. That is the
point: a demo comparing built-in tools against MCP proves nothing if the two
run on different data, because any difference could be blamed on the data.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/uvicorn mcp_server:app --port 8304
curl -s localhost:8304/health | python3 -m json.tool
```

Or `docker compose up -d`, which joins the platform's network so the platform
reaches it as `http://mcp-tools:8304`.

## Adding a tool

One edit:

```python
@app.get("/widgets/{widget_id}", operation_id="getWidget",
         summary="Fetch one widget")
def get_widget(widget_id: str) -> dict:
    """What the model reads to decide whether to call this."""
    ...
```

It is now a REST endpoint **and** an MCP tool called `soc_getWidget`. Nothing
else to register — `mcp_server` walks the routes and every one carrying an
`operation_id` becomes a tool. A route without one is skipped, which is how the
audio download stays out of the tool list.

Three things the wrapper handles, each learned by hitting it:

- **Names are `{service}_{operationId}`.** MCP names are flat across a server
  while operation_ids are unique only per service. SOC and IAM both define
  `getIdentity`; unprefixed, the second silently replaced the first and an
  agent asking for a SOC identity got IAM's answer.
- **`HTTPException` becomes a value, not a protocol error.** Over REST a 404
  *is* the response; over MCP there are no status codes, so an uncaught one
  reads as a broken server. `{"error": "No alert ALT-9999.", "status": 404}` is
  a fact the model can act on.
- **Annotations are resolved eagerly.** `from __future__ import annotations`
  makes them strings, which pydantic resolves through the handler's own module
  globals — not something a wrapper can inherit.

### A new service

Write the FastAPI app in `services/`, then add it to `SERVICES` in
`mcp_server.py`. That is the whole procedure.

## Seeding a demo

`seeds/` builds the workspace, skills, agents and pipeline in the platform.
They log in as `demo@example.com`, so `scripts/seed.py` in the platform repo
runs first.

```bash
DEMO_HOST=mcp-tools .venv/bin/python seeds/soc.py
DEMO_HOST=mcp-tools .venv/bin/python seeds/utility.py
```

`DEMO_HOST` is how the registered tool URLs and their `allowed_hosts` pin get
the right hostname. Inside a container `127.0.0.1` is that container, so the
default is only correct on a laptop.

## The recordings

`services/generate_visit_recordings.py` uses macOS `say` and **cannot run on
Linux**. Generate on a Mac, copy `data/recordings/` to the deployment. `data/`
is gitignored — the fixtures are derived, not source.

Only the utility demo needs them, and only to run a visit end to end; seeding
works without.
