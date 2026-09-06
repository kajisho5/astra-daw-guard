#!/usr/bin/env python3
"""Best-effort, keyword-overlap check of an intended action against
policy/deny.txt.

This is a WARNING tool, not an authoritative blocker: it can miss real
violations (false negative) and flag safe actions (false positive). Run
it before Computer Use, per SKILL.md's priority order (MCP > read-only >
Computer Use), as one more sanity check — not a replacement for actually
reading policy/deny.txt and checklists/during.md.

Usage:
    python3 tools/deny_check.py "download a midi file from bitmidi.com"
    echo "save as project_2026.als" | python3 tools/deny_check.py

Exit code 0 = no likely match found. Exit code 1 = at least one likely
match found (treat as denied unless you can rule it out by hand).
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "or", "and", "if", "is",
    "this", "that", "not", "do", "does", "did", "to", "with", "without",
    "only", "any", "except", "already", "already", "same", "than",
    "already", "when", "than", "into", "onto", "from", "than", "used",
    "use", "using", "user", "will", "would", "can", "could", "should",
    # Too generic in a DAW context to discriminate between rules on their
    # own — every action mentions a "track", so it produces false matches
    # against unrelated deny rules that happen to also say "track".
    "track", "tracks",
}


def load_rules(deny_path: pathlib.Path) -> list[str]:
    rules = []
    for line in deny_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rules.append(line)
    return rules


def normalize(word: str) -> str:
    if len(word) > 6 and word.endswith("ing"):
        word = word[:-3]
    elif len(word) > 5 and word.endswith("ed"):
        word = word[:-2]
    elif len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    return word


def keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return {normalize(w) for w in words if len(w) > 3 and w not in STOPWORDS}


def words_match(a: str, b: str) -> bool:
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    return len(shorter) >= 5 and longer.startswith(shorter)


def shared_keywords(action_kw: set[str], rule_kw: set[str]) -> list[str]:
    shared = []
    for aw in action_kw:
        for rw in rule_kw:
            if words_match(aw, rw):
                shared.append(rw)
                break
    return shared


def check(action: str, rules: list[str], min_shared: int) -> list[tuple[str, list[str]]]:
    action_kw = keywords(action)
    hits = []
    for rule in rules:
        rule_kw = keywords(rule)
        shared = shared_keywords(action_kw, rule_kw)
        if len(shared) >= min_shared:
            hits.append((rule, sorted(set(shared))))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "action",
        nargs="?",
        help="Description of the action you're about to take. Reads stdin if omitted.",
    )
    parser.add_argument(
        "--deny",
        default=None,
        help="Path to policy/deny.txt (default: auto-detect relative to this script)",
    )
    parser.add_argument(
        "--min-shared",
        type=int,
        default=2,
        help="Minimum shared keywords to count as a likely match (default: 2)",
    )
    args = parser.parse_args()

    action = args.action if args.action is not None else sys.stdin.read()
    if not action.strip():
        parser.error("no action text provided (pass as argument or via stdin)")

    deny_path = (
        pathlib.Path(args.deny)
        if args.deny
        else pathlib.Path(__file__).resolve().parent.parent / "policy" / "deny.txt"
    )
    if not deny_path.exists():
        parser.error(f"deny file not found: {deny_path}")

    rules = load_rules(deny_path)
    hits = check(action, rules, args.min_shared)

    if not hits:
        print("OK: no likely match against policy/deny.txt (heuristic only, not a guarantee).")
        return 0

    print(f"WARNING: {len(hits)} likely match(es) against policy/deny.txt:")
    for rule, shared in hits:
        print(f"  - {rule}")
        print(f"    shared keywords: {', '.join(shared)}")
    print(
        "\nThis is a keyword-overlap heuristic, not a semantic check. "
        "When in doubt, treat as denied per checklists/during.md."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
