"""Unit tests for the boundary guarantee itself."""

import os
import pathlib
import shutil

import pytest

from mcp_gate.boundary import AccessError, resolve_within_roots
from mcp_gate.gate import build_fixture


@pytest.fixture
def fx():
    tmp, roots = build_fixture()
    yield tmp, roots
    shutil.rmtree(tmp, ignore_errors=True)


def test_allows_file_within_root(fx):
    _, roots = fx
    real = resolve_within_roots("notes.txt", roots)
    assert os.path.isfile(real)
    assert real.startswith(os.path.realpath(roots[0]))


def test_blocks_dotdot_traversal(fx):
    _, roots = fx
    with pytest.raises(AccessError):
        resolve_within_roots("../out_of_bounds/secret.txt", roots)


def test_blocks_absolute_path_outside(fx):
    tmp, roots = fx
    outside = os.path.join(tmp, "out_of_bounds", "secret.txt")
    with pytest.raises(AccessError):
        resolve_within_roots(outside, roots)


def test_blocks_symlink_escape(fx):
    _, roots = fx
    with pytest.raises(AccessError):
        resolve_within_roots("backdoor/secret.txt", roots)


def test_blocks_encoded_traversal(fx):
    _, roots = fx
    with pytest.raises(AccessError):
        resolve_within_roots("%2e%2e/out_of_bounds/secret.txt", roots)


def test_sibling_prefix_not_confused(fx):
    # A sibling dir that merely shares a name prefix ("sandbox_evil" vs
    # "sandbox") must not be treated as inside the root.
    tmp, roots = fx
    evil = pathlib.Path(tmp) / "sandbox_evil"
    evil.mkdir()
    (evil / "x.txt").write_text("nope")
    with pytest.raises(AccessError):
        resolve_within_roots(str(evil / "x.txt"), roots)


def test_no_roots_raises():
    with pytest.raises(AccessError):
        resolve_within_roots("notes.txt", [])
