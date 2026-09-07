#!/usr/bin/env python3
"""Reproducible micro-benchmark for policy_engine/enforcement (Issue #16).

Issue #16 Phase 1 measured, by hand, a real gap between calling
policy_engine in-process and shelling out to its CLI -- that finding is
what drove Steps 1-3 (in-process priority, capability_available,
minimized CLI output). This script is that same measurement made
reproducible and runnable on demand, rather than a one-off number typed
into an Issue comment.

IMPORTANT: every number this script prints is measured live, in
whatever environment it runs in -- it is not a claim about Astra's
actual runtime, which this repo cannot observe (see Issue #16 Phase 1's
"measured vs unmeasurable" distinction: real Astra token counts and
real agent re-reading behavior stay unmeasurable here, always). Treat
these as microbenchmark orders of magnitude for this machine and this
Python interpreter, not production numbers -- re-run it yourself rather
than quoting this script's docstring or a past run's output as current.

Usage:
    python3 tools/benchmark.py
    python3 tools/benchmark.py --iterations 500
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from enforcement import enforce  # noqa: E402
from policy_engine import evaluate  # noqa: E402

_ALLOW_ACTION = {"operation": "read.tempo"}
_DENY_ACTION = {"operation": "project.save", "attributes": {"mode": "overwrite"}}


def _time_calls(fn: Callable[[], None], iterations: int) -> list[float]:
    """Return per-call wall time in microseconds, one entry per call."""
    samples = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1_000_000)
    return samples


def _summarize(label: str, samples: list[float]) -> dict:
    return {
        "label": label,
        "n": len(samples),
        "mean_us": statistics.mean(samples),
        "median_us": statistics.median(samples),
        "min_us": min(samples),
        "max_us": max(samples),
    }


def benchmark_evaluate_in_process(iterations: int) -> dict:
    return _summarize("policy_engine.evaluate() [in-process]", _time_calls(lambda: evaluate(_ALLOW_ACTION), iterations))


def benchmark_enforce_in_process(iterations: int) -> dict:
    return _summarize(
        "enforcement.enforce() [in-process, ALLOW]",
        _time_calls(lambda: enforce(_ALLOW_ACTION, lambda: None), iterations),
    )


def benchmark_cli_subprocess(iterations: int) -> dict:
    # CLI subprocess spin-up dominates; keep the default iteration count
    # low for this one so the whole script stays fast to run.
    action_json = json.dumps(_ALLOW_ACTION)

    def _run() -> None:
        subprocess.run(
            [sys.executable, "-m", "policy_engine.cli", action_json],
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    return _summarize("policy_engine.cli [subprocess]", _time_calls(_run, iterations))


def measure_output_sizes() -> dict:
    """Real byte counts for the CLI's default (minimal) vs --full output,
    for one ALLOW and one DENY decision -- see Issue #16 Step 3.
    """
    sizes = {}
    for name, action in (("allow", _ALLOW_ACTION), ("deny", _DENY_ACTION)):
        action_json = json.dumps(action)
        minimal = subprocess.run(
            [sys.executable, "-m", "policy_engine.cli", action_json],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        full = subprocess.run(
            [sys.executable, "-m", "policy_engine.cli", "--full", action_json],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        sizes[name] = {
            "minimal_bytes": len(minimal.encode("utf-8")),
            "full_bytes": len(full.encode("utf-8")),
        }
    return sizes


def _format_latency_row(result: dict) -> str:
    return (
        f"  {result['label']:<45} n={result['n']:<5} "
        f"mean={result['mean_us']:>10.1f}us  median={result['median_us']:>10.1f}us"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--iterations", type=int, default=1000, help="Iterations for in-process benchmarks")
    parser.add_argument(
        "--cli-iterations", type=int, default=20, help="Iterations for the CLI subprocess benchmark (slow)"
    )
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be at least 1")
    if args.cli_iterations < 1:
        parser.error("--cli-iterations must be at least 1")

    print("astra-daw-guard micro-benchmark (Issue #16)")
    print(f"Python: {sys.version.split()[0]}  Platform: {sys.platform}")
    print()
    print("Latency (measured live, this run only -- not a production Astra number):")
    print(_format_latency_row(benchmark_evaluate_in_process(args.iterations)))
    print(_format_latency_row(benchmark_enforce_in_process(args.iterations)))
    print(_format_latency_row(benchmark_cli_subprocess(args.cli_iterations)))

    print()
    print("CLI output size, default (minimal) vs --full:")
    for name, sizes in measure_output_sizes().items():
        reduction = 1 - (sizes["minimal_bytes"] / sizes["full_bytes"])
        print(
            f"  {name:<6} minimal={sizes['minimal_bytes']:>4}B  full={sizes['full_bytes']:>4}B  "
            f"reduction={reduction:.0%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
