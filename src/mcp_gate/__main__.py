"""CLI: python -m mcp_gate {gate boundary|gate prompt|suite|serve <roots...>}"""

import sys


def main(argv=None) -> int:
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    cmd = argv[0] if argv else ""

    if cmd == "gate" and len(argv) >= 2:
        from .gate import check
        return check(argv[1])
    if cmd == "suite":
        from .suite import run_suite
        return run_suite()
    if cmd == "serve":
        # Imported lazily so the gate/tests never require the MCP demo deps.
        from .server import serve
        serve(argv[1:])
        return 0

    print("usage: python -m mcp_gate {gate boundary | gate prompt | suite | "
          "serve <root> [root ...]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
