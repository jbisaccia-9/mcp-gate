"""A demo client that drives the mcp-gate server end to end.

It spawns the server over stdio and shows all four behaviors: logging
notifications, progress updates, a boundary-blocked attack, and server-initiated
sampling (the server asks *this* client to call the model).

Run from the repo root (needs the demo extras + ANTHROPIC_API_KEY):

    pip install -e ".[demo]"
    python -m mcp_gate.client ./data/sandbox
"""

import asyncio
import os
import sys

from anthropic import AsyncAnthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import (
    CreateMessageResult,
    LoggingMessageNotificationParams,
    TextContent,
)

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
_anthropic = AsyncAnthropic()  # reads ANTHROPIC_API_KEY from the environment


async def logging_callback(params: LoggingMessageNotificationParams) -> None:
    print(f"  [server log] {params.data}")


async def progress_callback(progress, total, message=None) -> None:
    pct = f" ({progress / total * 100:.0f}%)" if total else ""
    print(f"  [progress] {progress}/{total}{pct}")


async def sampling_callback(context, params) -> CreateMessageResult:
    """The server asked us to run the model — do it and hand the result back."""
    messages = [
        {"role": m.role, "content": m.content.text}
        for m in params.messages
        if m.content.type == "text"
    ]
    resp = await _anthropic.messages.create(
        model=MODEL,
        max_tokens=getattr(params, "maxTokens", None) or 400,
        system=getattr(params, "systemPrompt", None) or "",
        messages=messages,
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return CreateMessageResult(
        role="assistant", model=MODEL, content=TextContent(type="text", text=text)
    )


async def run(roots) -> None:
    server = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_gate", "serve", *roots]
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(
            read,
            write,
            logging_callback=logging_callback,
            sampling_callback=sampling_callback,
        ) as session:
            await session.initialize()

            print("\n== read an allowed file ==")
            res = await session.call_tool(
                "read_file", {"path": "notes.txt"}, progress_callback=progress_callback
            )
            print("  result:", res.content)

            print("\n== attempt a traversal attack (should be blocked) ==")
            res = await session.call_tool(
                "read_file",
                {"path": "../out_of_bounds/secret.txt"},
                progress_callback=progress_callback,
            )
            print(f"  isError={res.isError} result={res.content}")

            print("\n== summarize an allowed file (server-initiated sampling) ==")
            res = await session.call_tool(
                "summarize_file",
                {"path": "notes.txt"},
                progress_callback=progress_callback,
            )
            print("  summary:", res.content)


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:] or ["./data/sandbox"]))
