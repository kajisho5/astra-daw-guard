#!/usr/bin/env python3
"""One-shot setup for mcp-ableton.

Automates what can be automated:
  1. `pip install -e .` (this package + its dependencies)
  2. Fetches AbletonOSC (https://github.com/ideoforms/AbletonOSC — a
     third-party project, not maintained by this repo) with `git clone`
     directly into Ableton's Remote Scripts folder for your OS.

What this cannot automate — manual steps you still need to do:
  1. Restart Ableton Live.
  2. Preferences > Link/Tempo/MIDI > Control Surface > select
     "AbletonOSC".
  Ableton has no way to change either of those from outside the app.

Usage:
    python3 install.py
"""

from __future__ import annotations

import pathlib
import platform
import subprocess
import sys

ABLETON_OSC_REPO = "https://github.com/ideoforms/AbletonOSC"


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def remote_scripts_dir() -> pathlib.Path:
    home = pathlib.Path.home()
    system = platform.system()
    if system == "Windows":
        return home / "Documents" / "Ableton" / "User Library" / "Remote Scripts"
    if system == "Darwin":
        return home / "Music" / "Ableton" / "User Library" / "Remote Scripts"
    raise RuntimeError(
        f"Unsupported OS for Ableton Live: {system!r}. Ableton Live only "
        "runs on Windows and macOS, so this script doesn't know where to "
        "put AbletonOSC on this platform."
    )


def main() -> int:
    print("== Step 1/2: pip install -e . ==")
    run([sys.executable, "-m", "pip", "install", "-e", "."])

    print("\n== Step 2/2: fetch AbletonOSC into Ableton's Remote Scripts folder ==")
    try:
        target_parent = remote_scripts_dir()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    target_parent.mkdir(parents=True, exist_ok=True)
    target = target_parent / "AbletonOSC"

    if target.exists():
        print(f"{target} already exists — updating it with `git pull` instead of cloning.")
        run(["git", "-C", str(target), "pull"])
    else:
        run(["git", "clone", ABLETON_OSC_REPO, str(target)])

    print(
        f"\nDone. AbletonOSC is now at: {target}\n"
        "Remaining manual steps (cannot be automated from outside Ableton):\n"
        "  1. Restart Ableton Live.\n"
        "  2. Preferences > Link/Tempo/MIDI > Control Surface > select "
        '"AbletonOSC".\n'
        "Then run: python -m ableton_mcp.server"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
