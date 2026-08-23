"""The advanced MCP server — this is the "showcase" half of the repo.

It exposes typed file tools over stdio and, on every call, demonstrates the
three capabilities the project is about:

  * **access**   — every path goes through ``resolve_within_roots`` before any
    filesystem touch (the same guarantee the gate proves).
  * **logs**     — ``ctx.info`` emits MCP logging notifications, including the
    exact moment a request is refused at the boundary.
  * **progress** — ``ctx.report_progress`` streams progress as work proceeds.
  * **sampling** — ``summarize_file`` asks the *client* to run the model via
    ``ctx.session.create_message`` (server-initiated sampling).

Requires the demo extras: ``pip install -e ".[demo]"``. Nothing here runs in CI.
"""

import os

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import SamplingMessage, TextContent

from .boundary import AccessError, resolve_within_roots

mcp = FastMCP(name="mcp-gate")

# Authorized roots, set by serve(). Tools read from this.
ROOTS: list[str] = []


@mcp.tool()
async def list_roots(ctx: Context) -> list[str]:
    """Return the directories this server is authorized to access."""
    await ctx.info(f"list_roots: {len(ROOTS)} authorized root(s)")
    return ROOTS


@mcp.tool()
async def read_file(path: str, ctx: Context) -> str:
    """Read a file, but only if it resolves inside an authorized root."""
    await ctx.info(f"read_file: request for {path!r}")
    await ctx.report_progress(10, 100)
    try:
        real = resolve_within_roots(path, ROOTS)
    except AccessError as exc:
        await ctx.info(f"read_file: BLOCKED at roots boundary — {exc}")
        raise ValueError(str(exc))
    await ctx.report_progress(55, 100)
    with open(real, "r", encoding="utf-8") as fh:
        content = fh.read()
    await ctx.info(f"read_file: served {real} ({len(content)} bytes) from within roots")
    await ctx.report_progress(100, 100)
    return content


@mcp.tool()
async def list_dir(path: str, ctx: Context) -> list[str]:
    """List a directory, but only if it resolves inside an authorized root."""
    await ctx.info(f"list_dir: request for {path!r}")
    try:
        real = resolve_within_roots(path, ROOTS)
    except AccessError as exc:
        await ctx.info(f"list_dir: BLOCKED at roots boundary — {exc}")
        raise ValueError(str(exc))
    return sorted(os.listdir(real))


@mcp.tool()
async def summarize_file(path: str, ctx: Context) -> str:
    """Access-check a file, then ask the client to summarize it (sampling)."""
    await ctx.info(f"summarize_file: request for {path!r}")
    real = resolve_within_roots(path, ROOTS)  # access gate first
    with open(real, "r", encoding="utf-8") as fh:
        content = fh.read()
    await ctx.report_progress(40, 100)
    await ctx.info("summarize_file: requesting a completion from the client (sampling)")
    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=f"Summarize this file:\n\n{content}"),
            )
        ],
        max_tokens=400,
        system_prompt="You summarize files in two sentences.",
    )
    await ctx.report_progress(100, 100)
    return result.content.text if result.content.type == "text" else "(non-text result)"


def serve(roots) -> None:
    """Set the authorized roots and run the server over stdio."""
    global ROOTS
    ROOTS = [os.path.realpath(os.path.abspath(r)) for r in roots] or [os.getcwd()]
    mcp.run(transport="stdio")
