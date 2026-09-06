#!/usr/bin/env python3
"""Look up a ready-made refusal message for a policy/deny.txt rule.

Usage:
    python3 tools/refusal_message.py --list
    python3 tools/refusal_message.py no_unapproved_midi_download
    python3 tools/refusal_message.py no_unapproved_midi_download --lang ja
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


def load(path: pathlib.Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["rules"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("id", nargs="?", help="Rule id, e.g. no_unapproved_midi_download")
    parser.add_argument("--lang", choices=["en", "ja", "both"], default="both")
    parser.add_argument("--list", action="store_true", help="List all rule ids and exit")
    parser.add_argument(
        "--messages",
        default=None,
        help="Path to refusal_messages.json (default: auto-detect next to this script)",
    )
    args = parser.parse_args()

    messages_path = (
        pathlib.Path(args.messages)
        if args.messages
        else pathlib.Path(__file__).resolve().parent / "refusal_messages.json"
    )
    rules = load(messages_path)

    if args.list:
        for r in rules:
            print(r["id"])
        return 0

    if not args.id:
        parser.error("provide a rule id, or use --list")

    match = next((r for r in rules if r["id"] == args.id), None)
    if match is None:
        print(f"Unknown rule id: {args.id!r}. Use --list to see valid ids.", file=sys.stderr)
        return 1

    if args.lang in ("en", "both"):
        print(match["en"])
    if args.lang == "both":
        print()
    if args.lang in ("ja", "both"):
        print(match["ja"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
