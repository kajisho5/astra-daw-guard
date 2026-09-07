"""Tests for enforcement/ — the reference Enforcement Boundary.

These are not re-tests of policy_engine's rules (see
tests/test_policy_engine.py for that); these are about the boundary
itself: does a DENY or an unapproved ASK decision actually prevent the
wrapped tool from running, and does ALLOW / an approved ASK actually run
it. Run from the repo root:

    python3 -m unittest tests.test_enforcement -v
"""

from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from enforcement import ApprovalRequired, ToolDenied, enforce, guarded  # noqa: E402


class Counter:
    """A tool stand-in that records how many times it actually ran."""

    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> str:
        self.count += 1
        return "executed"


class AllowExecutesTests(unittest.TestCase):
    def test_allow_calls_the_tool_and_returns_its_result(self):
        counter = Counter()
        result = enforce({"operation": "read.tempo"}, counter)
        self.assertEqual(counter.count, 1)
        self.assertEqual(result, "executed")


class AskBlocksUntilApprovedTests(unittest.TestCase):
    ACTION = {"operation": "project.save", "attributes": {"mode": "save_as"}}

    def test_ask_without_approval_does_not_call_the_tool(self):
        counter = Counter()
        with self.assertRaises(ApprovalRequired) as ctx:
            enforce(self.ACTION, counter)
        self.assertEqual(counter.count, 0)
        self.assertEqual(ctx.exception.decision.decision, "ASK")
        self.assertEqual(ctx.exception.decision.rule_id, "SAVE_AS_UNCONFIRMED")

    def test_ask_with_approval_calls_the_tool_exactly_once(self):
        counter = Counter()
        result = enforce(self.ACTION, counter, approved=True)
        self.assertEqual(counter.count, 1)
        self.assertEqual(result, "executed")

    def test_approval_is_scoped_to_the_call_not_global(self):
        # Approving one Action must not make an unrelated ASK Action
        # execute without its own approval.
        counter = Counter()
        enforce(self.ACTION, counter, approved=True)
        self.assertEqual(counter.count, 1)

        other_ask_action = {"operation": "track.create", "attributes": {"name": "Vocals"}}
        with self.assertRaises(ApprovalRequired):
            enforce(other_ask_action, counter)
        self.assertEqual(counter.count, 1)  # unchanged


class DenyNeverExecutesTests(unittest.TestCase):
    """The core test: a DENYed tool call must never run the tool — this
    is what makes the Policy Engine an actual Guard rather than a
    convention an agent is asked to follow.
    """

    def test_denied_tool_is_never_called(self):
        counter = Counter()
        before = counter.count
        with self.assertRaises(ToolDenied):
            enforce({"operation": "project.save", "attributes": {"mode": "overwrite"}}, counter)
        after = counter.count
        self.assertEqual(before, 0)
        self.assertEqual(after, 0)
        self.assertEqual(before, after)

    def test_deny_is_never_overridden_by_approved_true(self):
        # approved=True must never turn a DENY into an execution — only
        # ASK can be turned into an execution, and only by approval.
        counter = Counter()
        with self.assertRaises(ToolDenied):
            enforce(
                {"operation": "project.save", "attributes": {"mode": "overwrite"}},
                counter,
                approved=True,
            )
        self.assertEqual(counter.count, 0)

    def test_deny_exception_carries_the_real_decision_unmodified(self):
        counter = Counter()
        with self.assertRaises(ToolDenied) as ctx:
            enforce({"operation": "daw.plugin_install"}, counter)
        decision = ctx.exception.decision
        self.assertEqual(decision.decision, "DENY")
        self.assertEqual(decision.rule_id, "PLUGIN_OR_LICENSE_DIALOG")
        self.assertTrue(decision.reason)
        self.assertEqual(counter.count, 0)

    def test_all_ten_deny_txt_operations_never_execute(self):
        # One Counter, one blocked call per deny.txt-backed scenario —
        # every single one must leave the counter at 0.
        denied_actions = [
            {"operation": "midi.fetch", "attributes": {"host": "bitmidi.com", "user_approved_this_turn": True}},
            {"operation": "midi.fetch", "attributes": {"host": "mutopiaproject.org"}},
            {"operation": "project.save", "attributes": {"mode": "overwrite"}},
            {"operation": "track.mix_sources", "attributes": {"labeled": False}},
            {"operation": "daw.window_change", "attributes": {"action": "move"}},
            {"operation": "daw.display_settings_change", "attributes": {"setting": "theme"}},
            {"operation": "daw.plugin_install"},
            {"operation": "daw.license_dialog_respond"},
            {"operation": "data.send_external", "attributes": {"is_model_api_in_use": False}},
            {"operation": "computer_use.invoke", "attributes": {"daw": "reaper", "capability": "read.tempo"}},
        ]
        for action in denied_actions:
            counter = Counter()
            with self.assertRaises(ToolDenied, msg=action):
                enforce(action, counter)
            self.assertEqual(counter.count, 0, msg=action)


class FailClosedTests(unittest.TestCase):
    def test_unknown_operation_never_executes(self):
        counter = Counter()
        with self.assertRaises(ToolDenied) as ctx:
            enforce({"operation": "totally.unknown"}, counter)
        self.assertEqual(counter.count, 0)
        self.assertEqual(ctx.exception.decision.rule_id, "UNKNOWN_OPERATION")

    def test_malformed_action_never_executes(self):
        counter = Counter()
        with self.assertRaises(ToolDenied) as ctx:
            enforce({"target": "x"}, counter)
        self.assertEqual(counter.count, 0)
        self.assertEqual(ctx.exception.decision.rule_id, "INVALID_ACTION_SCHEMA")

    def test_unknown_operation_never_executes_even_with_approved_true(self):
        counter = Counter()
        with self.assertRaises(ToolDenied):
            enforce({"operation": "totally.unknown"}, counter, approved=True)
        self.assertEqual(counter.count, 0)


class GuardedDecoratorTests(unittest.TestCase):
    def test_guarded_allow(self):
        calls: list[str] = []

        @guarded(lambda name: {"operation": "track.create", "attributes": {"name": name}})
        def create_track(name: str) -> str:
            calls.append(name)
            return f"created {name}"

        result = create_track("GEN-drums")
        self.assertEqual(result, "created GEN-drums")
        self.assertEqual(calls, ["GEN-drums"])

    def test_guarded_ask_then_approved(self):
        calls: list[str] = []

        @guarded(lambda name: {"operation": "track.create", "attributes": {"name": name}})
        def create_track(name: str) -> str:
            calls.append(name)
            return f"created {name}"

        with self.assertRaises(ApprovalRequired):
            create_track("Vocals")
        self.assertEqual(calls, [])

        result = create_track("Vocals", approved=True)
        self.assertEqual(result, "created Vocals")
        self.assertEqual(calls, ["Vocals"])

    def test_guarded_deny_never_calls_the_underlying_function(self):
        calls: list[str] = []

        @guarded(lambda: {"operation": "daw.plugin_install"})
        def install_plugin() -> str:
            calls.append("installed")
            return "installed"

        with self.assertRaises(ToolDenied):
            install_plugin()
        self.assertEqual(calls, [])

        with self.assertRaises(ToolDenied):
            install_plugin(approved=True)
        self.assertEqual(calls, [])


class AuditLogTests(unittest.TestCase):
    def test_audit_log_records_both_blocked_and_executed_calls(self):
        counter = Counter()
        log: list[dict] = []

        with self.assertRaises(ToolDenied):
            enforce({"operation": "daw.plugin_install"}, counter, audit_log=log)
        enforce({"operation": "read.tempo"}, counter, audit_log=log)

        self.assertEqual(len(log), 2)
        self.assertEqual(log[0]["decision"], "DENY")
        self.assertFalse(log[0]["executed"])
        self.assertEqual(log[1]["decision"], "ALLOW")
        self.assertTrue(log[1]["executed"])

        required_keys = (
            "decision",
            "rule_id",
            "reason",
            "operation",
            "target",
            "attributes",
            "timestamp",
            "executed",
        )
        for entry in log:
            for key in required_keys:
                self.assertIn(key, entry)

    def test_no_audit_log_by_default(self):
        # Passing no audit_log must not raise or require one.
        counter = Counter()
        enforce({"operation": "read.tracks"}, counter)
        self.assertEqual(counter.count, 1)


if __name__ == "__main__":
    unittest.main()
