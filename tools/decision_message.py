#!/usr/bin/env python3
"""Turn a policy_engine Decision into ready-to-say, bilingual text.

Unlike tools/refusal_message.py (which is keyed by a separate slug and
only covers DENY, see its own docstring), this module is keyed by
policy_engine's own `rule_id` -- the id an agent already has from
`evaluate(action).rule_id` -- and covers ASK (a confirmation prompt to
put to the user) as well as DENY (a refusal). Use this one when you're
driving through policy_engine/enforcement; refusal_message.py stays
useful for a human reading policy/deny.txt line by line.

Usage:
    python3 tools/decision_message.py --list
    python3 tools/decision_message.py PROJECT_OVERWRITE
    python3 tools/decision_message.py SAVE_AS_UNCONFIRMED --lang ja

In-process:
    from policy_engine import evaluate
    from tools.decision_message import message_for_decision

    decision = evaluate(action)
    if decision.decision != "ALLOW":
        print(message_for_decision(decision, lang="en"))
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Optional


def load(path: pathlib.Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["messages"]


def _messages_path() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent / "decision_messages.json"


def message_for_rule_id(rule_id: str, lang: str = "both", *, messages: Optional[list[dict]] = None) -> Optional[dict]:
    """Return the message entry for `rule_id`, or None if this catalog
    has nothing for it (an unmapped rule_id -- see
    `message_for_decision` for the fallback callers should use instead
    of treating None as an error).
    """
    entries = messages if messages is not None else load(_messages_path())
    return next((m for m in entries if m["rule_id"] == rule_id), None)


def format_message(entry: dict, lang: str = "both") -> str:
    if lang == "en":
        return entry["en"]
    if lang == "ja":
        return entry["ja"]
    return f"{entry['en']}\n\n{entry['ja']}"


def message_for_decision(decision: Any, lang: str = "both") -> str:
    """Return ready-to-say text for a policy_engine Decision (or
    anything with `.rule_id`/`.reason`/`.decision` attributes, e.g. an
    enforcement.ToolDenied/.ApprovalRequired exception's `.decision`).

    Falls back to `decision.reason` (English only -- it is developer-
    facing prose, not localized copy) when this catalog has no entry
    for `decision.rule_id`, rather than raising: a newly added rule_id
    this file hasn't caught up with yet must never leave a caller with
    no text to show the user.
    """
    entry = message_for_rule_id(decision.rule_id)
    if entry is not None:
        return format_message(entry, lang)
    return decision.reason


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("rule_id", nargs="?", help="Policy Engine rule_id, e.g. PROJECT_OVERWRITE")
    parser.add_argument("--lang", choices=["en", "ja", "both"], default="both")
    parser.add_argument("--list", action="store_true", help="List all covered rule_ids and exit")
    parser.add_argument(
        "--messages",
        default=None,
        help="Path to decision_messages.json (default: auto-detect next to this script)",
    )
    args = parser.parse_args()

    messages_path = pathlib.Path(args.messages) if args.messages else _messages_path()
    entries = load(messages_path)

    if args.list:
        for m in entries:
            print(f"{m['rule_id']} ({m['kind']})")
        return 0

    if not args.rule_id:
        parser.error("provide a rule_id, or use --list")

    entry = message_for_rule_id(args.rule_id, messages=entries)
    if entry is None:
        print(f"No message for rule_id {args.rule_id!r}. Use --list to see covered ids.", file=sys.stderr)
        return 1

    print(format_message(entry, args.lang))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
