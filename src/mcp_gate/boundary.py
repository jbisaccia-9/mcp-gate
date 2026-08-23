"""The guarantee.

An MCP server is told to stay inside its authorized *roots*. This module is the
part that *enforces* it, rather than trusting a path to already be well-behaved.

`resolve_within_roots` normalizes a requested path completely — URL-decodes it,
makes it absolute, and `realpath`s it so that ``..`` segments collapse and
symlinks are followed — and only then checks that the result sits inside one of
the authorized roots. Every known escape (``..`` traversal, absolute paths,
symlink escapes, ``%2e``-encoded traversal) is defused by that normalization
*before* the boundary check runs.
"""

import os
from urllib.parse import unquote


class AccessError(Exception):
    """Raised when a requested path resolves outside every authorized root."""


def _canonical(path: str) -> str:
    """Absolute, symlink-resolved, ``..``-collapsed form of a path."""
    return os.path.realpath(os.path.abspath(path))


def _is_within(candidate: str, root: str) -> bool:
    """True if canonical ``candidate`` is ``root`` or lives beneath it."""
    try:
        # commonpath compares whole path components, so "/a/sandbox_evil" is
        # correctly judged NOT within "/a/sandbox" (a str.startswith check
        # would wrongly accept it).
        return os.path.commonpath([candidate, root]) == root
    except ValueError:
        # Raised when the paths are on different drives / mixed abs+rel.
        return False


def resolve_within_roots(requested: str, roots, *, base: str = None) -> str:
    """Return the canonical path for ``requested`` iff it stays inside ``roots``.

    ``requested`` may be absolute or relative to ``base`` (which defaults to the
    first root). Raises :class:`AccessError` if the fully-resolved path escapes
    every authorized root.
    """
    if not roots:
        raise AccessError("no authorized roots configured")

    decoded = unquote(requested)  # defuse %2e%2e / %2f encoded traversal
    base = base or roots[0]
    joined = decoded if os.path.isabs(decoded) else os.path.join(base, decoded)

    candidate = _canonical(joined)
    for root in roots:
        if _is_within(candidate, _canonical(root)):
            return candidate

    raise AccessError(f"path escapes authorized roots: {requested!r}")
