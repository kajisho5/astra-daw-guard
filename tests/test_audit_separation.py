"""Tests for Issue #16's "Audit separation" goal: the agent-visible
surface (an `enforce()` return value, or the CLI's minimized default
output) may be minimal, but a complete, durable audit record must
always be obtainable separately and must never lose a field.

Not a re-test of enforcement's block/execute guarantees (see
tests/test_enforcement.py) or of the CLI's own flags (see
tests/test_cli.py) -- this specifically locks down the *separation*:
that minimizing what an agent reads in real time (Issue #16 Step 3)
never trades away what an auditor can reconstruct afterward. Run from
the repo root:

    python3 -m unittest tests.test_audit_separation -v
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

from enforcement import ToolDenied, enforce  # noqa: E402
from policy_engine.cli import main as cli_main  # noqa: E402

_DECISION_FIELDS = {
    "decision",
    "rule_id",
    "reason",
    "operation",
    "target",
    "attributes",
    "capability_available",
}


class AuditLogIsTheFullRecordTests(unittest.TestCase):
    """enforce()'s return value to the caller is deliberately thin (just
    the tool's own result, or an exception) -- the audit_log entry is
    where every Decision field must still be reconstructable.
    """

    def test_allow_return_value_carries_nothing_about_the_decision(self):
        log: list[dict] = []
        result = enforce({"operation": "read.tempo"}, lambda: "tool result", audit_log=log)
        # The caller-visible return value is exactly the tool's result --
        # no decision/rule_id/reason leaks into it, by construction (it's
        # a bare string, not a dict).
        self.assertEqual(result, "tool result")
        self.assertNotIsInstance(result, dict)

    def test_audit_log_entry_has_every_decision_field_for_an_allowed_call(self):
        log: list[dict] = []
        enforce({"operation": "read.tempo"}, lambda: "tool result", audit_log=log)
        self.assertEqual(len(log), 1)
        self.assertTrue(_DECISION_FIELDS.issubset(log[0].keys()))
        self.assertTrue(log[0]["executed"])

    def test_audit_log_entry_has_every_decision_field_for_a_denied_call(self):
        log: list[dict] = []
        with self.assertRaises(ToolDenied):
            enforce({"operation": "daw.plugin_install"}, lambda: "unreachable", audit_log=log)
        self.assertEqual(len(log), 1)
        self.assertTrue(_DECISION_FIELDS.issubset(log[0].keys()))
        self.assertFalse(log[0]["executed"])

    def test_audit_log_preserves_capability_available_for_a_capability_gap(self):
        # The Ardour read.tempo gap (Issue #16 Step 2) must be
        # reconstructable from the audit trail even though nothing in
        # a minimal agent-visible surface would necessarily show it.
        log: list[dict] = []
        enforce(
            {"operation": "read.tempo", "attributes": {"daw": "ardour"}},
            lambda: "tool result",
            audit_log=log,
        )
        self.assertEqual(log[0]["decision"], "ALLOW")
        self.assertFalse(log[0]["capability_available"])

    def test_audit_log_grows_by_exactly_one_entry_per_call_regardless_of_outcome(self):
        log: list[dict] = []
        enforce({"operation": "read.tempo"}, lambda: "ok", audit_log=log)
        with self.assertRaises(ToolDenied):
            enforce({"operation": "daw.plugin_install"}, lambda: "unreachable", audit_log=log)
        self.assertEqual(len(log), 2)


class CliFullFlagIsTheAuditEquivalentTests(unittest.TestCase):
    """For a non-Python caller (no audit_log to pass), --full is the
    only way to get the complete record -- it must match what
    Decision.to_dict()/the audit_log entry (minus executed/timestamp)
    would contain, field for field.
    """

    def _run_cli_full(self, action: dict) -> dict:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli_main(["--full", json.dumps(action)])
        return json.loads(buf.getvalue())

    def test_cli_full_output_has_exactly_the_decision_fields(self):
        payload = self._run_cli_full({"operation": "read.tempo", "attributes": {"daw": "ardour"}})
        self.assertEqual(set(payload.keys()), _DECISION_FIELDS)

    def test_cli_full_output_matches_an_equivalent_audit_log_entry(self):
        action = {"operation": "project.save", "attributes": {"mode": "overwrite"}}
        cli_payload = self._run_cli_full(action)

        log: list[dict] = []
        with self.assertRaises(ToolDenied):
            enforce(action, lambda: "unreachable", audit_log=log)
        audit_entry = log[0]

        for field in _DECISION_FIELDS:
            self.assertEqual(cli_payload[field], audit_entry[field], msg=field)


if __name__ == "__main__":
    unittest.main()
