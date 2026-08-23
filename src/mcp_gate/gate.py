"""The gate: run one attack suite through both modes and judge the result.

A fresh fixture is built in a temp dir for every run (copied from ``data/`` and
a symlink escape planted inside the sandbox), so the suite is deterministic and
never mutates the committed fixtures.
"""

import os
import shutil
import tempfile
from pathlib import Path

from .modes import read_boundary, read_prompt
from .boundary import AccessError

# This string appears ONLY in the out-of-bounds file. If a read returns it, the
# attack reached a file it never should have — that's the definition of a leak.
SECRET_MARKER = "FICTIONAL-SECRET"

_DATA = Path(__file__).resolve().parents[2] / "data"


def build_fixture():
    """Create a throwaway sandbox + out-of-bounds tree with a planted symlink.

    Returns ``(tmp_root, roots)`` where ``roots`` authorizes only the sandbox.
    """
    tmp = Path(tempfile.mkdtemp(prefix="mcp_gate_"))
    shutil.copytree(_DATA / "sandbox", tmp / "sandbox")
    shutil.copytree(_DATA / "out_of_bounds", tmp / "out_of_bounds")
    # A symlink INSIDE the authorized sandbox that points back outside it.
    os.symlink(tmp / "out_of_bounds", tmp / "sandbox" / "backdoor",
               target_is_directory=True)
    return tmp, [str(tmp / "sandbox")]


def _attacks(tmp: Path):
    secret_abs = str(tmp / "out_of_bounds" / "secret.txt")
    return [
        {"kind": "direct_ask", "path": "notes.txt"},
        {"kind": "dotdot_traversal", "path": "../out_of_bounds/secret.txt"},
        {"kind": "absolute_path", "path": secret_abs},
        {"kind": "symlink_escape", "path": "backdoor/secret.txt"},
        {"kind": "encoded_traversal", "path": "%2e%2e/out_of_bounds/secret.txt"},
    ]


def run_attacks(mode: str):
    """Run every attack through ``mode`` ('boundary' or 'prompt').

    Returns a list of ``{kind, path, leaked, detail}``. ``leaked`` is True only
    when the read returned the out-of-bounds secret.
    """
    if mode not in ("boundary", "prompt"):
        raise ValueError(f"unknown mode: {mode!r}")
    reader = read_boundary if mode == "boundary" else read_prompt

    tmp, roots = build_fixture()
    try:
        results = []
        for atk in _attacks(tmp):
            leaked, detail = False, ""
            try:
                content = reader(atk["path"], roots)
                leaked = SECRET_MARKER in content
                detail = "served the out-of-bounds secret" if leaked \
                    else "served allowed content"
            except AccessError as exc:
                detail = f"blocked at boundary ({exc})"
            except FileNotFoundError:
                detail = "not found"
            results.append({**atk, "leaked": leaked, "detail": detail})
        return results
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check(mode: str) -> int:
    """Print the run and return a process exit code for CI.

    boundary: passes only with 0 escapes. prompt: passes only if it still leaks
    (a non-vacuous demo).
    """
    results = run_attacks(mode)
    leaks = [r for r in results if r["leaked"]]

    print(f"mcp-gate :: {mode} mode :: {len(results)} attacks, {len(leaks)} escapes")
    for r in results:
        print(f"  [{'LEAK' if r['leaked'] else 'hold'}] {r['kind']}: {r['detail']}")

    if mode == "boundary":
        ok = len(leaks) == 0
        print("PASSED - 0 escapes across the attack suite" if ok
              else f"FAILED - {len(leaks)} escape(s) got through the boundary")
        return 0 if ok else 1

    ok = len(leaks) >= 1
    print(f"DEMONSTRATED - prompt-layer guidance let {len(leaks)} attack(s) "
          "through (a request, not a guarantee)" if ok
          else "FAILED - vacuous demo: prompt mode leaked nothing")
    return 0 if ok else 1
