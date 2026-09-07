#!/usr/bin/env python3
"""One-shot setup for mcp-ardour.

Ardour has the least setup friction of this repo's three adapters: its
OSC surface is built into Ardour itself, so there's no external file to
install. This script only automates:
  1. `pip install -e .`

What this cannot automate — a manual step you still need to do:
  - In Ardour: Preferences > Control Surfaces > enable "Open Sound
    Control (OSC)", leaving Port Mode on "Auto". Ardour has no way to
    change this from outside the app.

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
    print("== Step 1/1: pip install -e . ==")
    run([sys.executable, "-m", "pip", "install", "-e", "."])

    print(
        "\nDone. Remaining manual step (cannot be automated from outside "
        "Ardour):\n"
        '  In Ardour: Preferences > Control Surfaces > enable "Open Sound '
        'Control (OSC)", Port Mode = Auto.\n'
        "Then run: python -m ardour_mcp.server"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
