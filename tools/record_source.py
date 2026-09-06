#!/usr/bin/env python3
"""Append one entry to sources.json recording a licensed fetch.

See sources/README.md for the schema and policy/license-allowlist.txt
for which hosts are allowed at all. This tool does not fetch anything
and does not judge licenses for you — it only records what you already
confirmed, and refuses to record a host that isn't on the allowlist
unless you pass --force.

Usage:
    python3 tools/record_source.py \\
        --url "https://mutopiaproject.org/ftp/.../piece.mid" \\
        --license "Public Domain (Mutopia)" \\
        --track "GEN-piano-ref"
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.parse
from datetime import datetime, timezone


def load_allowlist(path: pathlib.Path) -> list[str]:
    hosts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        hosts.append(line)
    return hosts


def host_of(url: str) -> str:
    if url.startswith("file://"):
        return "file"
    return urllib.parse.urlparse(url).netloc.lower()


def host_allowed(url: str, hosts: list[str]) -> bool:
    if url.startswith("file://"):
        return "file://" in hosts
    netloc = host_of(url)
    return any(
        netloc == h or netloc.endswith("." + h) for h in hosts if h != "file://"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--url", required=True, help="Full URL that was fetched")
    parser.add_argument("--license", required=True, help="License you confirmed for this file")
    parser.add_argument("--track", default=None, help="Track name it was used in, if any")
    parser.add_argument(
        "--allowlist",
        default=None,
        help="Path to policy/license-allowlist.txt (default: auto-detect)",
    )
    parser.add_argument(
        "--sources",
        default=None,
        help="Path to sources.json to append to (default: repo root sources.json)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Record even if the host is not on license-allowlist.txt "
        "(policy/deny.txt still applies to whether you should have fetched it at all)",
    )
    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    allowlist_path = (
        pathlib.Path(args.allowlist)
        if args.allowlist
        else repo_root / "policy" / "license-allowlist.txt"
    )
    sources_path = (
        pathlib.Path(args.sources) if args.sources else repo_root / "sources.json"
    )

    if not allowlist_path.exists():
        parser.error(f"allowlist file not found: {allowlist_path}")

    hosts = load_allowlist(allowlist_path)
    if not host_allowed(args.url, hosts) and not args.force:
        print(
            f"REFUSED: {args.url} is not on {allowlist_path}.",
            file=sys.stderr,
        )
        print(
            "Per policy/deny.txt, do not record (or fetch) from hosts outside "
            "the allowlist. Pass --force only if you have a separate, explicit "
            "reason this is fine.",
            file=sys.stderr,
        )
        return 1

    entries = []
    if sources_path.exists():
        text = sources_path.read_text(encoding="utf-8").strip()
        if text:
            entries = json.loads(text)

    entries.append(
        {
            "url": args.url,
            "host": host_of(args.url),
            "license": args.license,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "used_in_track": args.track,
        }
    )

    sources_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Recorded: {args.url} -> {sources_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
