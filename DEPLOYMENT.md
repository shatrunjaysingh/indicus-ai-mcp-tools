# Deploying the demo tools

This repository runs beside a deployed IndicusAI platform. The platform's own
`DEPLOYMENT.md` covers the platform; this covers what is different about the
tools, and is written so either can be read first.

The whole thing is one container, `mcp-tools`, on port 8304, serving:

| | |
|---|---|
| `/soc` `/utility` `/payer` `/iam` | REST, registered as built-in custom tools |
| `/mcp` | the same operations as an MCP server, streamable HTTP |
| `/health` | both surfaces, and what is registered on each |

## Deploy

```bash
cd ~
git clone https://github.com/shatrunjaysingh/indicus-ai-mcp-tools.git
cd indicus-ai-mcp-tools
docker compose up -d --build
```

It joins the **platform's** compose network so the platform can reach it by
name. That network is `indicusai_default` by default; if your platform compose
project is named differently:

```bash
PLATFORM_NETWORK=<network> docker compose up -d
docker network ls          # to find it
```

Getting this wrong is quiet. The container starts, `/health` answers on the
host, and only a seed or a run reveals it — as a refused connection to
`mcp-tools`.

## Seed the demos

**From inside the container.** It has the seeds and their dependencies, and the
compose file sets both hostnames. This repository ships no virtualenv, so
running a seed on the host fails on `No such file or directory`.

```bash
docker compose exec mcp-tools python seeds/soc.py
docker compose exec mcp-tools python seeds/utility.py
```

`scripts/seed.py` in the platform repository must have run first — the seeds
authenticate as `demo@example.com` and none of them creates it.

The seeds are idempotent. Re-running reuses the workspace, leaves unchanged
skills alone, and resumes wherever the last attempt stopped.

### The two hostnames

Both are set for you by the compose file, and both are wrong anywhere else,
because inside a container `127.0.0.1` is the container:

| | Laptop | Deployed |
|---|---|---|
| `PLATFORM_API_URL` | `http://127.0.0.1:8000/api/v1` | `http://api:8000/api/v1` |
| `DEMO_HOST` | `127.0.0.1` | `mcp-tools` |

`DEMO_HOST` sets the registered tool URLs *and* their `allowed_hosts` pin, so a
tool registered under the wrong one is refused before the call leaves the
platform.

## Adding it as an MCP connector

The REST tools are registered by the seeds. The MCP server is added once, in
the platform UI:

> Administration → Connections → add an MCP server
>
> transport `http`, URL `http://mcp-tools:8304/mcp`

Probe it there — a healthy probe lists every tool. Two failures are worth
recognising:

- **`Not Found`** — the URL is missing `/mcp`, or has it twice.
- **could not be reached** — the container is not on the platform's network,
  or is being reached by a hostname the server does not answer to. MCP's DNS
  rebinding protection admits only the names in `ALLOWED_HOSTS`; set that
  variable to add one rather than editing the code.

Tool names are `{service}_{operationId}` — `soc_getAlert`, `iam_getIdentity`.
The prefix is not decoration: MCP names are flat across a server while
operation_ids are unique only within a service, and SOC and IAM both define
`getIdentity`.

## Adding a tool

One edit, in the relevant `services/*.py`:

```python
@app.get("/widgets/{widget_id}", operation_id="getWidget",
         summary="Fetch one widget")
def get_widget(widget_id: str) -> dict:
    """What the model reads to decide whether to call this."""
    ...
```

That is a REST endpoint **and** an MCP tool. `mcp_server` walks the routes and
registers every one carrying an `operation_id`; a route without one is skipped,
which is how the audio download stays out of the tool list.

Then `docker compose up -d --build`, and re-run the seed if the tool should be
registered as a built-in custom tool too — MCP picks it up with no reseeding,
since the connector lists tools at connect time.

A new service: write the app in `services/`, add it to `SERVICES` in
`mcp_server.py`.

### A new skill

Drop the markdown in `skills/` and add its slug to the seed's `SKILLS` list.
Whatever the frontmatter declares under `allowed-tools` is merged into the
published manifest — a skill naming a tool the connector list does not contain
used to fail validation with a message about the manifest.

## The visit recordings

`services/generate_visit_recordings.py` uses macOS `say` and **cannot run on
Linux**. Generate on a Mac and copy them up:

```bash
.venv/bin/python services/generate_visit_recordings.py
gcloud compute scp --zone=us-east1-b --recurse \
  data/recordings indicus-ai:~/indicus-ai-mcp-tools/data/
```

`data/` is gitignored: these are derived from a fixed script, so committing
them would store generated audio in the history. Only the utility demo needs
them, and only to run a visit end to end — seeding works without.

## Shipping a change

```bash
cd ~/indicus-ai-mcp-tools
git pull
docker compose up -d --build
```

The image carries the code, so a change to a service, a seed or a skill needs
the rebuild — a `git pull` alone changes nothing the container is running.

## Working on it locally

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/uvicorn mcp_server:app --port 8304 --reload
```

The defaults are the laptop ones, so seeds run with no environment set:

```bash
.venv/bin/python seeds/soc.py
```

Speech-to-text is an optional extra — `pip install -e '.[stt]'` — because
faster-whisper pulls onnxruntime, a couple of hundred megabytes nothing else
here needs.
