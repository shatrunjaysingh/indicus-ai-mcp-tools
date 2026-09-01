"""The demo services.

Each module is a FastAPI app whose routes carry `operation_id`s. `mcp_server`
turns every such route into an MCP tool, so a new endpoint here becomes a new
MCP tool with no second edit.

The modules import each other by bare name — `import utility_data`, not
`from . import utility_data` — because they were written to run standalone
(`uvicorn utility_api:app`) and that is still useful when working on one of
them. Putting this directory on the path keeps both true: importable as a
package from mcp_server, and runnable on its own from inside this directory.
"""

import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
