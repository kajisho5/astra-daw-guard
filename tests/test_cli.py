"""Tests for policy_engine/cli.py — the non-Python-caller fallback.

Not a re-test of policy_engine's rules (see tests/test_policy_engine.py
for that); this only covers the CLI's own contract: default output is
minimal (agent-visible output minimization, Issue #16), --full restores
every Decision field, --pretty indents, and exit codes still map to
ALLOW/ASK/DENY. Run from the repo root:

    python3 -m unittest tests.test_cli -v
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from policy_engine.cli import main  # noqa: E402


def _run(argv: list[str]) -> tuple[int, dict]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exit_code = main(argv)
    return exit_code, json.loads(buf.getvalue())


def _run_plan(argv: list[str]) -> tuple[int, list[dict]]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exit_code = main(argv)
    lines = buf.getvalue().strip("\n").splitlines()
    return exit_code, [json.loads(line) for line in lines]


class DefaultOutputIsMinimalTests(unittest.TestCase):
    def test_allow_default_output_has_only_the_minimal_keys(self):
        exit_code, payload = _run(['{"operation": "read.tempo"}'])
        self.assertEqual(exit_code, 0)
        self.assertEqual(set(payload.keys()), {"decision", "rule_id", "reason"})
        self.assertEqual(payload["decision"], "ALLOW")

    def test_deny_default_output_has_only_the_minimal_keys(self):
        exit_code, payload = _run(
            ['{"operation": "project.save", "attributes": {"mode": "overwrite"}}']
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(set(payload.keys()), {"decision", "rule_id", "reason"})
        self.assertEqual(payload["decision"], "DENY")

    def test_capability_available_included_only_when_not_none(self):
        _, with_daw = _run(['{"operation": "read.tempo", "attributes": {"daw": "ardour"}}'])
        self.assertEqual(set(with_daw.keys()), {"decision", "rule_id", "reason", "capability_available"})
        self.assertFalse(with_daw["capability_available"])

        _, without_daw = _run(['{"operation": "read.tempo"}'])
        self.assertNotIn("capability_available", without_daw)

    def test_default_output_is_compact_not_indented(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(['{"operation": "read.tempo"}'])
        self.assertNotIn("\n", buf.getvalue().rstrip("\n"))


class FullFlagRestoresEveryFieldTests(unittest.TestCase):
    def test_full_output_has_every_decision_field(self):
        exit_code, payload = _run(["--full", '{"operation": "read.tempo"}'])
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            set(payload.keys()),
            {"decision", "rule_id", "reason", "operation", "target", "attributes", "capability_available"},
        )


class PrettyFlagIndentsTests(unittest.TestCase):
    def test_pretty_output_is_indented(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["--pretty", '{"operation": "read.tempo"}'])
        self.assertIn("\n", buf.getvalue().rstrip("\n"))


class ExitCodesUnchangedTests(unittest.TestCase):
    def test_allow_ask_deny_exit_codes(self):
        allow_code, _ = _run(['{"operation": "read.tempo"}'])
        ask_code, _ = _run(['{"operation": "project.save", "attributes": {"mode": "save_as"}}'])
        deny_code, _ = _run(['{"operation": "daw.plugin_install"}'])
        self.assertEqual(allow_code, 0)
        self.assertEqual(ask_code, 1)
        self.assertEqual(deny_code, 2)

    def test_invalid_json_is_denied_with_minimal_output(self):
        exit_code, payload = _run(["not json"])
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["rule_id"], "INVALID_JSON")


class PlanFlagTests(unittest.TestCase):
    """--plan (Issue #26): one Decision line per input Action, exit
    code reflects the worst decision across the whole plan.
    """

    def test_all_allow_plan_prints_one_line_per_action_and_exits_zero(self):
        plan = json.dumps(
            [{"operation": "read.tempo"}, {"operation": "track.create", "attributes": {"name": "GEN-bass"}}]
        )
        exit_code, payloads = _run_plan(["--plan", plan])
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(payloads), 2)
        self.assertTrue(all(p["decision"] == "ALLOW" for p in payloads))

    def test_a_deny_anywhere_in_the_plan_makes_exit_code_two(self):
        plan = json.dumps(
            [{"operation": "read.tempo"}, {"operation": "project.save", "attributes": {"mode": "overwrite"}}]
        )
        exit_code, payloads = _run_plan(["--plan", plan])
        self.assertEqual(exit_code, 2)
        self.assertEqual([p["decision"] for p in payloads], ["ALLOW", "DENY"])

    def test_worst_case_precedence_is_deny_over_ask_over_allow(self):
        plan = json.dumps(
            [
                {"operation": "project.save", "attributes": {"mode": "save_as"}},  # ASK
                {"operation": "read.tempo"},  # ALLOW
            ]
        )
        exit_code, _ = _run_plan(["--plan", plan])
        self.assertEqual(exit_code, 1)

    def test_empty_plan_exits_zero_with_no_output_lines(self):
        exit_code, payloads = _run_plan(["--plan", "[]"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(payloads, [])

    def test_plan_output_stays_minimal_by_default(self):
        exit_code, payloads = _run_plan(["--plan", json.dumps([{"operation": "read.tempo"}])])
        self.assertEqual(set(payloads[0].keys()), {"decision", "rule_id", "reason"})

    def test_plan_full_flag_restores_every_field(self):
        exit_code, payloads = _run_plan(["--plan", "--full", json.dumps([{"operation": "read.tempo"}])])
        self.assertEqual(
            set(payloads[0].keys()),
            {"decision", "rule_id", "reason", "operation", "target", "attributes", "capability_available"},
        )

    def test_non_array_input_with_plan_flag_is_denied(self):
        exit_code, payload = _run(["--plan", '{"operation": "read.tempo"}'])
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["rule_id"], "INVALID_JSON")


if __name__ == "__main__":
    unittest.main()
