"""Security regression tests for the ASTRA Runtime Efficiency & UX
Optimization work (Issue #16).

Steps 1-3 touched `policy_engine/engine.py`, `policy_engine/rules.py`,
and `policy_engine/cli.py` in the name of latency/token/UX efficiency.
None of those changes were supposed to affect any ALLOW/ASK/DENY
outcome. This module is not a re-test of policy_engine's rules (see
tests/test_policy_engine.py) or of the enforcement boundary (see
tests/test_enforcement.py) -- it specifically locks down the properties
an optimization pass could silently break: rule order/identity, that
`capability_available` never leaks into or influences a decision, and
that the CLI's now-minimal default output still carries everything an
agent needs to act safely. Run from the repo root:

    python3 -m unittest tests.test_security_regression -v
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
from policy_engine import ALLOW, ASK, DENY, evaluate  # noqa: E402
from policy_engine.cli import main as cli_main  # noqa: E402
from policy_engine.engine import KNOWN_OPERATIONS  # noqa: E402
from policy_engine.rules import RULES  # noqa: E402

# The exact rule_id order as of the pre-optimization baseline (PR #15).
# Steps 1-3 (PRs #17-#19) only added a field to Decision and
# post-processed it in evaluate() -- they must not have reordered,
# renamed, added, or removed any rule. If this list ever needs to
# change, that change must be deliberate policy work, never a side
# effect of a UX/latency optimization.
_EXPECTED_RULE_ORDER = [
    ("MIDI_DUMP_SITE", DENY),
    ("MIDI_FETCH_NO_APPROVAL", DENY),
    ("MIDI_FETCH_NOT_ALLOWLISTED", ASK),
    ("MIDI_FETCH_ALLOWED", ALLOW),
    ("PROJECT_OVERWRITE", DENY),
    ("SAVE_AS_APPROVED", ALLOW),
    ("SAVE_AS_UNCONFIRMED", ASK),
    ("UNLABELED_MIXED_SOURCES", DENY),
    ("LABELED_MIXED_SOURCES", ALLOW),
    ("WINDOW_MANIPULATION", DENY),
    ("DISPLAY_SETTINGS_CHANGE", DENY),
    ("PLUGIN_OR_LICENSE_DIALOG", DENY),
    ("SEND_UNPUBLISHED_EXTERNALLY", DENY),
    ("SEND_TO_MODEL_API", ALLOW),
    ("COMPUTER_USE_WHEN_MCP_AVAILABLE", DENY),
    ("COMPUTER_USE_NO_MCP", ALLOW),
    ("READ_ONLY", ALLOW),
    ("GENERATED_MIDI_INTO_GEN_TRACK", ALLOW),
    ("GENERATED_MIDI_INTO_OTHER_TRACK", DENY),
    ("CREATE_GEN_TRACK", ALLOW),
    ("CREATE_OTHER_TRACK", ASK),
    ("MIXER_CHANGE_ON_GEN_TRACK", ALLOW),
    ("MIXER_CHANGE_ON_OTHER_TRACK", ASK),
    ("DEVICE_PARAM_CHANGE_ON_GEN_TRACK", ALLOW),
    ("DEVICE_PARAM_CHANGE_ON_OTHER_TRACK", ASK),
    ("TRANSPORT_CONTROL", ALLOW),
    ("TEMPO_CHANGE_APPROVED", ALLOW),
    ("TEMPO_CHANGE_UNCONFIRMED", ASK),
]

# The same 10 deny.txt-backed Actions test_enforcement.py's
# test_all_ten_deny_txt_operations_never_execute uses, kept in sync
# deliberately: this suite re-checks them through evaluate() and the
# CLI, not just enforce(), so a regression in any one layer is caught.
_DENY_TXT_ACTIONS = [
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


def _run_cli(action: dict, *extra_args: str) -> tuple[int, dict]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exit_code = cli_main([*extra_args, json.dumps(action)])
    return exit_code, json.loads(buf.getvalue())


class RuleOrderAndIdentityRegressionTests(unittest.TestCase):
    """Locks down that no optimization step reordered, renamed, added,
    or removed a rule -- only Decision gained a new field.
    """

    def test_rule_order_and_decisions_match_the_pre_optimization_baseline(self):
        actual = [(r.rule_id, r.decision) for r in RULES]
        self.assertEqual(actual, _EXPECTED_RULE_ORDER)

    def test_known_operations_unchanged_by_the_optimization_work(self):
        self.assertEqual(
            KNOWN_OPERATIONS,
            {
                "read.tempo",
                "read.tracks",
                "read.clips",
                "read.project_info",
                "read.song_info",
                "read.transport",
                "midi.fetch",
                "midi.write",
                "project.save",
                "track.create",
                "track.mix_sources",
                "daw.window_change",
                "daw.display_settings_change",
                "daw.plugin_install",
                "daw.license_dialog_respond",
                "data.send_external",
                "computer_use.invoke",
                "track.mixer_change",
                "device.param_change",
                "transport.control",
                "tempo.change",
            },
        )


class DenyTxtStillDeniesEndToEndTests(unittest.TestCase):
    """Every deny.txt-backed Action must still DENY through evaluate(),
    enforce() (tool never runs), and the CLI (both minimal-default and
    --full output) -- across all three optimization steps at once.
    """

    def test_still_deny_via_evaluate(self):
        for action in _DENY_TXT_ACTIONS:
            with self.subTest(action=action):
                self.assertEqual(evaluate(action).decision, DENY)

    def test_still_deny_via_enforce_tool_never_runs(self):
        for action in _DENY_TXT_ACTIONS:
            with self.subTest(action=action):
                calls = []
                with self.assertRaises(ToolDenied):
                    enforce(action, lambda: calls.append(1))
                self.assertEqual(calls, [])

    def test_still_deny_via_cli_default_minimal_output(self):
        for action in _DENY_TXT_ACTIONS:
            with self.subTest(action=action):
                exit_code, payload = _run_cli(action)
                self.assertEqual(exit_code, 2)
                self.assertEqual(payload["decision"], DENY)
                self.assertTrue(payload["reason"])

    def test_still_deny_via_cli_full_output(self):
        for action in _DENY_TXT_ACTIONS:
            with self.subTest(action=action):
                exit_code, payload = _run_cli(action, "--full")
                self.assertEqual(exit_code, 2)
                self.assertEqual(payload["decision"], DENY)
                self.assertEqual(payload["operation"], action["operation"])


class CapabilityAvailableCannotInfluenceDecisionTests(unittest.TestCase):
    """capability_available (Issue #16 Step 2) must never change
    ALLOW/ASK/DENY, and must never appear on operations it isn't
    defined for -- regardless of what `daw` is passed.
    """

    def test_capability_available_absent_or_false_never_turns_deny_into_allow(self):
        # computer_use.invoke is deliberately daw-dependent (its own
        # rules use mcp_supports() directly, see the dedicated test
        # below) -- every other deny.txt-backed operation must stay
        # DENY no matter what `daw` is added to its attributes.
        for action in _DENY_TXT_ACTIONS:
            if action["operation"] == "computer_use.invoke":
                continue
            for daw in ("reaper", "ableton", "ardour", "some-unmodeled-daw"):
                augmented = dict(action)
                augmented["attributes"] = {**action.get("attributes", {}), "daw": daw}
                with self.subTest(action=action, daw=daw):
                    self.assertEqual(evaluate(augmented).decision, DENY)

    def test_capability_available_is_none_for_every_non_read_operation(self):
        non_read_ops = [op for op in KNOWN_OPERATIONS if not op.startswith("read.")]
        for operation in non_read_ops:
            for daw in ("reaper", "ableton", "ardour"):
                with self.subTest(operation=operation, daw=daw):
                    d = evaluate({"operation": operation, "attributes": {"daw": daw}})
                    self.assertIsNone(d.capability_available)

    def test_computer_use_invoke_capability_check_is_unaffected_by_step_2(self):
        # computer_use.invoke already used mcp_supports() before Step 2,
        # through a different mechanism (its own rule predicates, not
        # the read.*-only post-processing engine.evaluate() added).
        # Step 2 must not have added a second, conflicting capability
        # signal to this operation.
        denied = evaluate(
            {"operation": "computer_use.invoke", "attributes": {"daw": "reaper", "capability": "read.tempo"}}
        )
        self.assertEqual(denied.decision, DENY)
        self.assertEqual(denied.rule_id, "COMPUTER_USE_WHEN_MCP_AVAILABLE")
        self.assertIsNone(denied.capability_available)

        allowed = evaluate(
            {"operation": "computer_use.invoke", "attributes": {"daw": "ardour", "capability": "read.tempo"}}
        )
        self.assertEqual(allowed.decision, ALLOW)
        self.assertEqual(allowed.rule_id, "COMPUTER_USE_NO_MCP")
        self.assertIsNone(allowed.capability_available)


class CliMinimalOutputStillActionableTests(unittest.TestCase):
    """The CLI's minimized default output (Issue #16 Step 3) must still
    carry everything checklists/during.md tells an agent to act on.
    """

    def test_allow_minimal_output_has_decision_and_reason(self):
        exit_code, payload = _run_cli({"operation": "read.tempo"})
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["decision"], ALLOW)
        self.assertTrue(payload["reason"])

    def test_ask_minimal_output_has_decision_and_reason(self):
        exit_code, payload = _run_cli(
            {"operation": "project.save", "attributes": {"mode": "save_as"}}
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["decision"], ASK)
        self.assertTrue(payload["reason"])

    def test_minimal_output_still_surfaces_capability_gap(self):
        # The Ardour read.tempo gap this whole Step 2/3 pair exists to
        # surface must still be visible in the CLI's minimal output,
        # not only in --full.
        exit_code, payload = _run_cli(
            {"operation": "read.tempo", "attributes": {"daw": "ardour"}}
        )
        self.assertEqual(exit_code, 0)  # still ALLOW
        self.assertEqual(payload["decision"], ALLOW)
        self.assertIn("capability_available", payload)
        self.assertFalse(payload["capability_available"])


if __name__ == "__main__":
    unittest.main()
