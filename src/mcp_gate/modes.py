"""Two ways an MCP file tool can honor its roots — one enforced, one not.

`read_boundary` is what the server actually ships: it runs the path through the
:func:`~mcp_gate.boundary.resolve_within_roots` guarantee first. `read_prompt`
is the deliberately-naive control: it behaves as if a system-prompt instruction
("only read files under the roots") were the whole defense, and opens whatever
path it is handed. The gate runs the same attacks through both.
"""

import os
from urllib.parse import unquote

from .boundary import resolve_within_roots


def read_boundary(requested: str, roots) -> str:
    """ENFORCED: resolve against the roots boundary, then read. Raises
    :class:`~mcp_gate.boundary.AccessError` for anything outside."""
    real = resolve_within_roots(requested, roots)
    with open(real, "r", encoding="utf-8") as fh:
        return fh.read()


def read_prompt(requested: str, roots) -> str:
    """UNENFORCED CONTROL: a prompt *told* the caller to stay in-roots, but the
    path is opened as given. ``..``, absolute paths, and symlinks all resolve at
    the OS level, so this leaks. It exists to prove the boundary is doing work."""
    base = roots[0] if roots else os.getcwd()
    decoded = unquote(requested)
    target = decoded if os.path.isabs(decoded) else os.path.join(base, decoded)
    with open(target, "r", encoding="utf-8") as fh:  # no boundary check
        return fh.read()
