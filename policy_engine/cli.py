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
"""

from __future__ import annotations

import json
import sys

from .engine import evaluate
from .rules import ALLOW, ASK, DENY

_EXIT_CODES = {ALLOW: 0, ASK: 1, DENY: 2}


def main() -> int:
    raw = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    try:
        action_dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(
            json.dumps(
                {
                    "decision": DENY,
                    "rule_id": "INVALID_JSON",
                    "reason": f"Input was not valid JSON: {exc}",
                }
            )
        )
        return _EXIT_CODES[DENY]

    decision = evaluate(action_dict)
    print(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))
    return _EXIT_CODES[decision.decision]


if __name__ == "__main__":
    raise SystemExit(main())
