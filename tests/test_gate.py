"""The gate: boundary mode must hold; prompt mode must still visibly leak."""

from mcp_gate.gate import check, run_attacks


def test_boundary_mode_never_leaks():
    results = run_attacks("boundary")
    assert all(not r["leaked"] for r in results)
    assert check("boundary") == 0


def test_prompt_mode_leaks_under_attack():
    leaks = [r for r in run_attacks("prompt") if r["leaked"]]
    assert len(leaks) >= 3, "the naive handler should fail the escape attacks"
    kinds = {r["kind"] for r in leaks}
    assert "dotdot_traversal" in kinds
    assert "symlink_escape" in kinds
    assert check("prompt") == 0  # demonstrated, not vacuous


def test_direct_ask_is_the_deceptive_success():
    # The plain in-root read succeeds in BOTH modes — which is exactly why a
    # quick manual check of prompt-layer security looks safe and fails later.
    for mode in ("boundary", "prompt"):
        direct = [r for r in run_attacks(mode) if r["kind"] == "direct_ask"]
        assert direct and not direct[0]["leaked"]


def test_every_escape_is_blocked_in_boundary_mode():
    for r in run_attacks("boundary"):
        if r["kind"] != "direct_ask":
            assert not r["leaked"]
            assert "blocked at boundary" in r["detail"]
