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


if __name__ == "__main__":
    unittest.main()
