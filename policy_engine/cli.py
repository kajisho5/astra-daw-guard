#!/usr/bin/env python3
"""CLI for the Policy Engine: authoritative, JSON in, JSON out.

Usage:
    python3 -m policy_engine.cli '{"operation": "project.save", "attributes": {"mode": "overwrite"}}'
    echo '{"operation": "read.tempo"}' | python3 -m policy_engine.cli

Exit code 0 = ALLOW. Exit code 1 = ASK. Exit code 2 = DENY.

This is authoritative — unlike tools/deny_check.py's heuristic keyword
matching over free text, this takes a structured Action (see
policy_engine/README.md) and returns the Policy Engine's actual
decision, with no guessing involved.

Prefer `from policy_engine import evaluate` in-process when your caller
can import this repo (see checklists/during.md) — this CLI exists for
callers that can't. Default output is deliberately minimal (only what
an agent needs to act: `decision`, `rule_id`, `reason`, and
`capability_available` when it applies) since this text is what an
agent reads on every single operation. Pass --full for the complete
Decision (adds `operation`/`target`/`attributes`, useful for audit or
debugging), and --pretty for indented output.
"""

from __future__ import annotations

import argparse
import json
import sys

from .engine import evaluate
from .rules import ALLOW, ASK, DENY

_EXIT_CODES = {ALLOW: 0, ASK: 1, DENY: 2}


def _minimal(payload: dict) -> dict:
    out = {
        "decision": payload["decision"],
        "rule_id": payload["rule_id"],
        "reason": payload["reason"],
    }
    if payload.get("capability_available") is not None:
        out["capability_available"] = payload["capability_available"]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", nargs="?", help="Action JSON (or pipe it on stdin)")
    parser.add_argument(
        "--full", action="store_true", help="Print every Decision field, not just the minimal set"
    )
    parser.add_argument("--pretty", action="store_true", help="Indent the JSON output")
    args = parser.parse_args(argv)

    raw = args.action if args.action is not None else sys.stdin.read()
    try:
        action_dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        payload = {
            "decision": DENY,
            "rule_id": "INVALID_JSON",
            "reason": f"Input was not valid JSON: {exc}",
        }
        print(json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False))
        return _EXIT_CODES[DENY]

    decision = evaluate(action_dict)
    payload = decision.to_dict()
    if not args.full:
        payload = _minimal(payload)
    print(json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False))
    return _EXIT_CODES[decision.decision]


if __name__ == "__main__":
    raise SystemExit(main())
