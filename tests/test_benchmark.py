"""Structural smoke tests for tools/benchmark.py (Issue #16 Phase 9).

This is NOT a performance test -- asserting a specific latency number
in CI would be flaky by construction (shared runners, variable load).
It only checks that the benchmark actually runs, measures something,
and reports the shape Issue #16's write-up promised (a mean/median in
microseconds, and a minimal-vs-full byte comparison) -- so a future
refactor that silently breaks the benchmark (e.g. an exception, or a
result missing a field) fails CI instead of only being noticed when
someone happens to run it by hand. Run from the repo root:

    python3 -m unittest tests.test_benchmark -v
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.benchmark import (  # noqa: E402
    benchmark_enforce_in_process,
    benchmark_evaluate_in_process,
    measure_output_sizes,
)

_SUMMARY_KEYS = {"label", "n", "mean_us", "median_us", "min_us", "max_us"}


class InProcessBenchmarksRunAndReportTests(unittest.TestCase):
    def test_evaluate_benchmark_reports_a_positive_latency(self):
        result = benchmark_evaluate_in_process(iterations=20)
        self.assertEqual(set(result.keys()), _SUMMARY_KEYS)
        self.assertEqual(result["n"], 20)
        self.assertGreater(result["mean_us"], 0)
        self.assertGreater(result["median_us"], 0)

    def test_enforce_benchmark_reports_a_positive_latency(self):
        result = benchmark_enforce_in_process(iterations=20)
        self.assertEqual(set(result.keys()), _SUMMARY_KEYS)
        self.assertEqual(result["n"], 20)
        self.assertGreater(result["mean_us"], 0)


class OutputSizeMeasurementTests(unittest.TestCase):
    def test_measures_both_allow_and_deny_and_minimal_is_smaller_than_full(self):
        sizes = measure_output_sizes()
        self.assertEqual(set(sizes.keys()), {"allow", "deny"})
        for name, entry in sizes.items():
            with self.subTest(name=name):
                self.assertGreater(entry["minimal_bytes"], 0)
                self.assertGreater(entry["full_bytes"], 0)
                # Locks the Step 3 property this benchmark exists to
                # demonstrate: minimal output must stay smaller than
                # --full, not just "different".
                self.assertLess(entry["minimal_bytes"], entry["full_bytes"])


class ZeroIterationsIsRejectedNotACrashTests(unittest.TestCase):
    """Issue #37: --iterations 0 / --cli-iterations 0 used to crash deep
    inside statistics.mean() with a raw StatisticsError traceback. Both
    flags must instead fail fast with a clear argparse error.
    """

    def _run(self, *extra_args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "tools/benchmark.py", *extra_args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_iterations_zero_is_a_clean_argparse_error(self):
        result = self._run("--iterations", "0", "--cli-iterations", "1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--iterations must be at least 1", result.stderr)
        self.assertNotIn("StatisticsError", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_iterations_zero_is_a_clean_argparse_error(self):
        result = self._run("--iterations", "1", "--cli-iterations", "0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--cli-iterations must be at least 1", result.stderr)
        self.assertNotIn("StatisticsError", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
