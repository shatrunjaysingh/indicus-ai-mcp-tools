"""Every demo service, over REST and MCP, from one process.

The platform can reach an external system two ways — a custom HTTP tool per
endpoint, or one MCP connector carrying every tool on the server. Both are
worth showing, and showing them against different fixtures would prove nothing:
any difference in a run could be blamed on the data rather than the transport.
So one set of fixtures is served over both.

    /soc/*        /utility/*      /payer/*      /iam/*      REST, as custom tools
    /mcp                                                    the same operations as MCP

**Tools are derived from the routes, not listed here.** Every route with an
`operation_id` becomes an MCP tool named `{service}_{operationId}`, calling the
same function the REST endpoint calls. Adding an endpoint to any service
therefore adds an MCP tool, and the two surfaces cannot drift apart — which
they would if this file held a list someone had to remember to update.

The service prefix is not decoration. MCP tool names are flat across a server
while operation_ids are unique only within a service, and SOC and IAM both
define `getIdentity`.

To add a service: write the FastAPI app, give each route an `operation_id`, and
add it to SERVICES below. That is the whole procedure.
"""

from __future__ import annotations

import contextlib
import functools
import inspect
import os
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from services import iam_api, payer_api, soc_api, utility_api

# mount path -> the FastAPI app serving it.
SERVICES: dict[str, FastAPI] = {
    "soc": soc_api.app,
    "utility": utility_api.app,
    "payer": payer_api.app,
    "iam": iam_api.app,
}

mcp: MCPServer = MCPServer(
    name="indicus-demos",
    instructions=(
        "Fixtures for the Indicus demos. SOC tools cover alert triage, threat "
        "intelligence, asset inventory and identity. Utility tools cover field "
        "visits, accounts, billing, meter readings and grid events. Payer and "
        "IAM tools cover claims and access certification."
    ),
)


def _as_tool(fn: Any) -> Any:
    """Expose a FastAPI handler as an MCP tool.

    Only the error contract differs between the surfaces. Over REST an
    HTTPException *is* the response; over MCP there are no status codes, so an
    uncaught one surfaces as a protocol failure and the agent sees a broken
    server rather than a missing record. "No alert ALT-9999" is a fact a model
    can act on, so it is returned as a value.
    """

    # functools.wraps rather than copying attributes by hand, for __module__:
    # a handler annotated with a model defined in its own module (iam's
    # TeamsMessage) is a forward reference pydantic resolves through the
    # function's module. A wrapper that claims to live here makes that name
    # unresolvable and the server refuses to start.
    @functools.wraps(fn)
    async def tool(*args: Any, **kwargs: Any) -> Any:
        try:
            result = fn(*args, **kwargs)
            return await result if inspect.isawaitable(result) else result
        except HTTPException as exc:
            return {"error": exc.detail, "status": exc.status_code}

    tool.__doc__ = fn.__doc__ or fn.__name__
    # The SDK builds each input schema from the signature, and a bare
    # (*args, **kwargs) wrapper yields a schema whose only field is "kwargs" —
    # every call then fails validation before the handler runs, and a model
    # reading that schema cannot construct a valid call at all.
    #
    # eval_str resolves the annotations against the *handler's* module before
    # they are attached here. `from __future__ import annotations` makes every
    # annotation a string, and pydantic resolves those through the function's
    # __globals__ — which a wrapper defined in this module does not share, no
    # matter what __module__ claims. A handler taking a model defined beside it
    # (iam's TeamsMessage) is then unresolvable and the server will not start.
    # Resolving here means the schema is built from real classes.
    tool.__signature__ = inspect.signature(fn, eval_str=True)  # type: ignore[attr-defined]
    tool.__annotations__ = {
        name: param.annotation
        for name, param in tool.__signature__.parameters.items()
        if param.annotation is not inspect.Parameter.empty
    }
    return tool


def _register(service: str, app: FastAPI) -> list[str]:
    """Register every operation on one service, namespaced by service name.

    Namespaced because MCP tool names are flat across a server while
    operation_ids are only unique within a service. SOC and IAM both define
    `getIdentity`, and registering both unprefixed silently kept the last one:
    35 operations became 34 tools, and an agent asking for a SOC identity got
    IAM's answer — wrong data returned confidently, with nothing in any log
    except one line saying the tool already existed.
    """
    names = []
    for route in app.routes:
        # No operation_id means the route was not meant as a tool — the audio
        # download is a browser convenience, not something an agent calls.
        if not isinstance(route, APIRoute) or not route.operation_id:
            continue
        name = f"{service}_{route.operation_id}"
        if name in _SEEN:
            # Cannot happen with distinct service names, which is the point of
            # asserting it: the failure it replaces was silent.
            raise RuntimeError(f"Duplicate MCP tool name {name!r}.")
        _SEEN.add(name)
        mcp.add_tool(_as_tool(route.endpoint), name=name)
        names.append(name)
    return names


_SEEN: set[str] = set()


REGISTERED: dict[str, list[str]] = {n: _register(n, a) for n, a in SERVICES.items()}

# streamable_http_path="/" because this is mounted at /mcp below; left at its
# default the endpoint would be /mcp/mcp and the client would get a bare "Not
# Found" naming neither the path it tried nor the one that exists.
#
# The host list is what makes this reachable from another container. DNS
# rebinding protection is on by default and admits only localhost, so over a
# compose network — where Host is `mcp-tools:8304` — every request is refused,
# with an error that says nothing about hostnames.
#
# Kept on rather than disabled, and extendable without a code change: whoever
# deploys this behind a different name sets ALLOWED_HOSTS rather than editing
# and rebuilding.
_HOSTS = [
    "mcp-tools", "mcp-tools:8304",
    "127.0.0.1", "127.0.0.1:8304",
    "localhost", "localhost:8304",
    *(h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()),
]

_mcp_app = mcp.streamable_http_app(
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(
        allowed_hosts=_HOSTS, allowed_origins=["*"]
    ),
)


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # The MCP session manager is started by the sub-app's own lifespan, which a
    # mount does not run. Without this every /mcp request fails with "Task group
    # is not initialized" — a mounted server that answers nothing.
    async with _mcp_app.router.lifespan_context(_mcp_app):
        yield


app = FastAPI(title="Indicus demo tools", description=__doc__, lifespan=lifespan)
app.mount("/mcp", _mcp_app)
for _name, _app in SERVICES.items():
    app.mount(f"/{_name}", _app)


@app.get("/health")
def health() -> dict:
    """Both surfaces, and what is registered on each."""
    return {
        "status": "ok",
        "rest": [f"/{n}" for n in SERVICES],
        "mcp": {"endpoint": "/mcp", "transport": "streamable-http"},
        "tools": REGISTERED,
        "tool_count": sum(len(v) for v in REGISTERED.values()),
    }
