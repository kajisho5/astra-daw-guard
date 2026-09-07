#!/usr/bin/env python3
"""One-shot setup for mcp-reaper.

Automates what can be automated:
  1. `pip install -e .` (this package + its dependencies, including
     python-reapy)
  2. `reapy.configure_reaper()` (writes reapy's companion script into
     Reaper's resource path)

What this cannot automate — a manual step you still need to do:
  - Reaper must be running before step 2, and must be **restarted**
    after this script finishes so it picks up reapy's companion script.
    There is no way to do either of those from outside Reaper.

Usage:
    python3 install.py
"""

from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> int:
    print("== Step 1/2: pip install -e . ==")
    run([sys.executable, "-m", "pip", "install", "-e", "."])

    print("\n== Step 2/2: reapy.configure_reaper() ==")
    print("This requires Reaper to already be running.")
    try:
        import reapy
    except ImportError:
        print("ERROR: python-reapy did not install correctly.", file=sys.stderr)
        return 1

    try:
        reapy.configure_reaper()
    except Exception as exc:  # reapy's own exception types aren't public API
        print(f"ERROR: reapy.configure_reaper() failed: {exc}", file=sys.stderr)
        print("Make sure Reaper is running, then re-run this script.", file=sys.stderr)
        return 1

    print(
        "\nDone. Restart Reaper now (required for reapy's companion script "
        "to load), then run: python -m reaper_mcp.server"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
