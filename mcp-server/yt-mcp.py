"""Compatibility shim for the renamed content MCP server."""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    """Forward execution to the generalized content MCP entry point."""
    target = Path(__file__).with_name("content_mcp.py")
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
