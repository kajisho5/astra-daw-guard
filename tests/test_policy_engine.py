"""Tests for policy_engine — the authoritative Policy Engine.

These are NOT tests of tools/deny_check.py (the heuristic sanity
checker); that tool is intentionally not held to this bar. Run from the
repo root:

    python3 -m unittest tests.test_policy_engine -v
"""

from __future__ import annotations

import ast
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from policy_engine import ALLOW, ASK, DENY, evaluate  # noqa: E402
from policy_engine.capabilities import CAPABILITY_MATRIX  # noqa: E402
from policy_engine.rules import RULES  # noqa: E402


class AllowTests(unittest.TestCase):
    """policy/allow.txt: safe reads and correctly-scoped writes."""

    def test_read_tempo(self):
        self.assertEqual(evaluate({"operation": "read.tempo"}).decision, ALLOW)

    def test_read_tracks(self):
        self.assertEqual(evaluate({"operation": "read.tracks"}).decision, ALLOW)

    def test_read_clips(self):
        self.assertEqual(evaluate({"operation": "read.clips"}).decision, ALLOW)

    def test_generate_midi_into_gen_track(self):
        d = evaluate(
            {
                "operation": "midi.write",
                "attributes": {"source": "generated", "track": "GEN-drums"},
            }
        )
        self.assertEqual(d.decision, ALLOW)
        self.assertEqual(d.rule_id, "GENERATED_MIDI_INTO_GEN_TRACK")

    def test_create_gen_track(self):
        d = evaluate({"operation": "track.create", "attributes": {"name": "GEN-bass"}})
        self.assertEqual(d.decision, ALLOW)
        self.assertEqual(d.rule_id, "CREATE_GEN_TRACK")

    def test_save_as_with_confirmed_request(self):
        d = evaluate(
            {
                "operation": "project.save",
                "attributes": {"mode": "save_as", "user_requested_this_turn": True},
            }
        )
        self.assertEqual(d.decision, ALLOW)

    def test_computer_use_allowed_when_no_mcp_capability(self):
        # Ardour's MCP has no tempo tool (see mcp-ardour/README.md), so
        # Computer Use for tempo is the documented last resort there.
        d = evaluate(
            {
                "operation": "computer_use.invoke",
                "attributes": {"daw": "ardour", "capability": "read.tempo"},
            }
        )
        self.assertEqual(d.decision, ALLOW)

    def test_mixer_change_on_gen_track(self):
        d = evaluate(
            {
                "operation": "track.mixer_change",
                "attributes": {"track": "GEN-drums", "param": "volume", "value": 0.7},
            }
        )
        self.assertEqual(d.decision, ALLOW)
        self.assertEqual(d.rule_id, "MIXER_CHANGE_ON_GEN_TRACK")

    def test_device_param_change_on_gen_track(self):
        d = evaluate(
            {
                "operation": "device.param_change",
                "attributes": {"track": "GEN-bass", "param_index": 0, "value": 0.5},
            }
        )
        self.assertEqual(d.decision, ALLOW)
        self.assertEqual(d.rule_id, "DEVICE_PARAM_CHANGE_ON_GEN_TRACK")

    def test_transport_control_always_allowed(self):
        d = evaluate({"operation": "transport.control", "attributes": {"action": "play"}})
        self.assertEqual(d.decision, ALLOW)
        self.assertEqual(d.rule_id, "TRANSPORT_CONTROL")

    def test_tempo_change_with_confirmed_request(self):
        d = evaluate(
            {
                "operation": "tempo.change",
                "attributes": {"bpm": 128.0, "user_requested_this_turn": True},
            }
        )
        self.assertEqual(d.decision, ALLOW)
        self.assertEqual(d.rule_id, "TEMPO_CHANGE_APPROVED")


class AskTests(unittest.TestCase):
    def test_save_as_without_confirmed_request(self):
        d = evaluate(
            {
                "operation": "project.save",
                "attributes": {"mode": "save_as", "filename": "song_2026.als"},
            }
        )
        self.assertEqual(d.decision, ASK)
        self.assertEqual(d.rule_id, "SAVE_AS_UNCONFIRMED")

    def test_approved_fetch_from_non_allowlisted_host(self):
        d = evaluate(
            {
                "operation": "midi.fetch",
                "attributes": {
                    "url": "https://example.com/x.mid",
                    "host": "example.com",
                    "user_approved_this_turn": True,
                },
            }
        )
        self.assertEqual(d.decision, ASK)
        self.assertEqual(d.rule_id, "MIDI_FETCH_NOT_ALLOWLISTED")

    def test_create_unrelated_track(self):
        d = evaluate({"operation": "track.create", "attributes": {"name": "Vocals"}})
        self.assertEqual(d.decision, ASK)

    def test_mixer_change_on_other_track(self):
        d = evaluate(
            {
                "operation": "track.mixer_change",
                "attributes": {"track": "Vocals", "param": "mute", "value": True},
            }
        )
        self.assertEqual(d.decision, ASK)
        self.assertEqual(d.rule_id, "MIXER_CHANGE_ON_OTHER_TRACK")

    def test_device_param_change_on_other_track(self):
        d = evaluate(
            {
                "operation": "device.param_change",
                "attributes": {"track": "Vocals", "param_index": 0, "value": 0.5},
            }
        )
        self.assertEqual(d.decision, ASK)
        self.assertEqual(d.rule_id, "DEVICE_PARAM_CHANGE_ON_OTHER_TRACK")

    def test_tempo_change_without_confirmed_request(self):
        d = evaluate({"operation": "tempo.change", "attributes": {"bpm": 128.0}})
        self.assertEqual(d.decision, ASK)

    def test_tempo_change_with_truthy_but_non_boolean_confirmation_still_asks(self):
        # CodeRabbit review finding on PR #47 (CWE-863 Authorization
        # Bypass): the predicate used to check truthiness, so a
        # malformed Action carrying the string "false" -- truthy in
        # Python -- or the int 1 would auto-ALLOW tempo changes despite
        # never actually receiving a real user confirmation this turn.
        for bogus_value in ("false", 1):
            with self.subTest(user_requested_this_turn=bogus_value):
                d = evaluate(
                    {
                        "operation": "tempo.change",
                        "attributes": {"bpm": 128.0, "user_requested_this_turn": bogus_value},
                    }
                )
                self.assertEqual(d.decision, ASK)
                self.assertEqual(d.rule_id, "TEMPO_CHANGE_UNCONFIRMED")

    def test_save_as_with_truthy_but_non_boolean_request_still_asks(self):
        # Same authorization-bypass class as MIDI_FETCH_NO_APPROVAL's
        # regression test above: SAVE_AS_APPROVED's predicate used to
        # check truthiness, so "false"/1 would auto-ALLOW a Save As
        # despite no real user request this turn.
        for bogus_value in ("false", 1):
            with self.subTest(user_requested_this_turn=bogus_value):
                d = evaluate(
                    {
                        "operation": "project.save",
                        "attributes": {"mode": "save_as", "user_requested_this_turn": bogus_value},
                    }
                )
                self.assertEqual(d.decision, ASK)
                self.assertEqual(d.rule_id, "SAVE_AS_UNCONFIRMED")


class DenyTests(unittest.TestCase):
    """policy/deny.txt's 10 rules, one test each (plus fail-closed cases)."""

    def test_overwrite_current_project(self):
        d = evaluate({"operation": "project.save", "attributes": {"mode": "overwrite"}})
        self.assertEqual(d.decision, DENY)
        self.assertEqual(d.rule_id, "PROJECT_OVERWRITE")

    def test_overwrite_denied_even_if_user_requested(self):
        # deny.txt has no approval escape hatch for overwrite — unlike
        # save_as, "the user asked" does not flip this to ALLOW.
        d = evaluate(
            {
                "operation": "project.save",
                "attributes": {"mode": "overwrite", "user_requested_this_turn": True},
            }
        )
        self.assertEqual(d.decision, DENY)
        self.assertEqual(d.rule_id, "PROJECT_OVERWRITE")

    def test_install_plugin(self):
        self.assertEqual(evaluate({"operation": "daw.plugin_install"}).decision, DENY)

    def test_accept_license_dialog(self):
        self.assertEqual(evaluate({"operation": "daw.license_dialog_respond"}).decision, DENY)

    def test_download_midi_without_approval(self):
        d = evaluate(
            {
                "operation": "midi.fetch",
                "attributes": {"url": "https://mutopiaproject.org/x.mid", "host": "mutopiaproject.org"},
            }
        )
        self.assertEqual(d.decision, DENY)
        self.assertEqual(d.rule_id, "MIDI_FETCH_NO_APPROVAL")

    def test_download_midi_with_truthy_but_non_boolean_approval_is_still_denied(self):
        # Authorization-bypass regression (same class of bug CodeRabbit
        # found in PR #47's tempo.change rule, CWE-863): the old
        # predicate was `not a.attr("user_approved_this_turn", False)`,
        # which used truthiness. A malformed Action carrying the string
        # "false" (truthy in Python) or the int 1 would fail to trip
        # this DENY and fall through to be ASKed or even ALLOWed by the
        # allowlist rules below it -- on the single rule SKILL.md calls
        # its most important ("ネットから MIDI を無断で取得することは禁止").
        for bogus_value in ("false", 1):
            with self.subTest(user_approved_this_turn=bogus_value):
                d = evaluate(
                    {
                        "operation": "midi.fetch",
                        "attributes": {
                            "url": "https://mutopiaproject.org/x.mid",
                            "host": "mutopiaproject.org",
                            "user_approved_this_turn": bogus_value,
                        },
                    }
                )
                self.assertEqual(d.decision, DENY)
                self.assertEqual(d.rule_id, "MIDI_FETCH_NO_APPROVAL")

    def test_download_from_prohibited_dump_site_even_if_approved(self):
        d = evaluate(
            {
                "operation": "midi.fetch",
                "attributes": {
                    "url": "https://bitmidi.com/x.mid",
                    "host": "bitmidi.com",
                    "user_approved_this_turn": True,
                },
            }
        )
        self.assertEqual(d.decision, DENY)
        self.assertEqual(d.rule_id, "MIDI_DUMP_SITE")

    def test_use_non_allowlisted_public_domain_source_without_approval(self):
        d = evaluate(
            {
                "operation": "midi.fetch",
                "attributes": {"url": "https://example.com/x.mid", "host": "example.com"},
            }
        )
        self.assertEqual(d.decision, DENY)

    def test_send_unpublished_project_remotely(self):
        d = evaluate(
            {
                "operation": "data.send_external",
                "attributes": {"destination": "https://not-the-model-api.example.com"},
            }
        )
        self.assertEqual(d.decision, DENY)
        self.assertEqual(d.rule_id, "SEND_UNPUBLISHED_EXTERNALLY")

    def test_send_to_model_api_is_allowed(self):
        d = evaluate(
            {
                "operation": "data.send_external",
                "attributes": {"is_model_api_in_use": True},
            }
        )
        self.assertEqual(d.decision, ALLOW)

    def test_computer_use_when_equivalent_mcp_operation_exists(self):
        d = evaluate(
            {
                "operation": "computer_use.invoke",
                "attributes": {"daw": "reaper", "capability": "read.tempo"},
            }
        )
        self.assertEqual(d.decision, DENY)
        self.assertEqual(d.rule_id, "COMPUTER_USE_WHEN_MCP_AVAILABLE")

    def test_window_manipulation(self):
        d = evaluate({"operation": "daw.window_change", "attributes": {"action": "move"}})
        self.assertEqual(d.decision, DENY)

    def test_display_settings_change(self):
        d = evaluate({"operation": "daw.display_settings_change", "attributes": {"setting": "theme"}})
        self.assertEqual(d.decision, DENY)

    def test_unlabeled_mixed_sources(self):
        d = evaluate({"operation": "track.mix_sources", "attributes": {"labeled": False}})
        self.assertEqual(d.decision, DENY)

    def test_labeled_mixed_sources_allowed(self):
        d = evaluate({"operation": "track.mix_sources", "attributes": {"labeled": True}})
        self.assertEqual(d.decision, ALLOW)

    def test_generated_midi_into_wrong_track(self):
        d = evaluate(
            {
                "operation": "midi.write",
                "attributes": {"source": "generated", "track": "Drums"},
            }
        )
        self.assertEqual(d.decision, DENY)
        self.assertEqual(d.rule_id, "GENERATED_MIDI_INTO_OTHER_TRACK")

    # --- Fail-closed: unknown / malformed actions ---

    def test_unknown_operation_is_denied_not_allowed(self):
        d = evaluate({"operation": "totally.made.up"})
        self.assertEqual(d.decision, DENY)
        self.assertEqual(d.rule_id, "UNKNOWN_OPERATION")

    def test_missing_operation_field_is_denied(self):
        d = evaluate({"target": "current"})
        self.assertEqual(d.decision, DENY)
        self.assertEqual(d.rule_id, "INVALID_ACTION_SCHEMA")

    def test_non_dict_action_is_denied(self):
        d = evaluate({"operation": 123})
        self.assertEqual(d.decision, DENY)
        self.assertEqual(d.rule_id, "INVALID_ACTION_SCHEMA")

    def test_empty_dict_is_denied(self):
        d = evaluate({})
        self.assertEqual(d.decision, DENY)

    def test_non_dict_non_action_top_level_input_is_denied_not_a_crash(self):
        # evaluate()'s own docstring promises it never raises for a
        # malformed action -- that must hold for "malformed" in the
        # broadest sense (wrong Python type entirely), not just "a
        # dict with the wrong shape". Found by an adversarial review
        # of this "authoritative, fail-closed" engine, since nothing
        # previously exercised anything but dict input.
        for bad_action in (None, "read.tempo", 123, [1, 2, 3], 4.5, True):
            with self.subTest(bad_action=bad_action):
                d = evaluate(bad_action)
                self.assertEqual(d.decision, DENY)
                self.assertEqual(d.rule_id, "INVALID_ACTION_SCHEMA")

    def test_non_string_host_attribute_does_not_crash(self):
        # midi.fetch's dump-site/allowlist checks used to call
        # `.lower()` directly on the "host" attribute, which crashed
        # for any non-string value instead of failing closed.
        d = evaluate(
            {"operation": "midi.fetch", "attributes": {"host": 123, "user_approved_this_turn": True}}
        )
        self.assertIn(d.decision, (ASK, DENY))  # never ALLOW for a garbage host

    def test_non_string_daw_attribute_on_computer_use_does_not_crash(self):
        d = evaluate({"operation": "computer_use.invoke", "attributes": {"daw": 123, "capability": "read.tempo"}})
        self.assertIn(d.decision, (ALLOW, DENY))  # must not raise

    def test_unhashable_capability_attribute_does_not_crash(self):
        # mcp_supports() used CAPABILITY_MATRIX.get(operation, set())
        # with `operation` taken directly from the "capability"
        # attribute -- a list there is unhashable and used to raise
        # TypeError instead of failing closed.
        d = evaluate(
            {"operation": "computer_use.invoke", "attributes": {"daw": "reaper", "capability": ["read.tempo"]}}
        )
        self.assertIn(d.decision, (ALLOW, DENY))  # must not raise


class DecisionAuditabilityTests(unittest.TestCase):
    def test_decision_to_dict_has_all_audit_fields(self):
        d = evaluate({"operation": "daw.plugin_install"})
        payload = d.to_dict()
        for key in ("decision", "rule_id", "reason", "operation", "target", "attributes"):
            self.assertIn(key, payload)
        self.assertTrue(payload["reason"])  # never an empty explanation


class CapabilityAvailabilityTests(unittest.TestCase):
    """capability_available must never be confused with the ALLOW/ASK/DENY
    decision itself: it only says whether this repo's MCP/OSC adapter
    actually implements a given read for a given DAW. A read is always
    ALLOW regardless of this field — policy never forbids reading state.
    """

    def test_no_daw_given_is_not_applicable(self):
        d = evaluate({"operation": "read.tempo"})
        self.assertEqual(d.decision, ALLOW)
        self.assertIsNone(d.capability_available)

    def test_non_read_operation_is_not_applicable_even_with_daw(self):
        d = evaluate(
            {"operation": "track.create", "attributes": {"name": "GEN-drums", "daw": "reaper"}}
        )
        self.assertIsNone(d.capability_available)

    def test_supported_read_is_allow_and_capability_true(self):
        d = evaluate({"operation": "read.tempo", "attributes": {"daw": "reaper"}})
        self.assertEqual(d.decision, ALLOW)
        self.assertTrue(d.capability_available)

    def test_unsupported_read_is_still_allow_but_capability_false(self):
        # The confirmed gap this regression test locks down: Ardour has
        # no tempo-query OSC command (see mcp-ardour/README.md), so
        # read.tempo must stay ALLOW (policy permits reading tempo) while
        # capability_available reports False — a capability gap, never a
        # policy DENY.
        d = evaluate({"operation": "read.tempo", "attributes": {"daw": "ardour"}})
        self.assertEqual(d.decision, ALLOW)
        self.assertEqual(d.rule_id, "READ_ONLY")
        self.assertFalse(d.capability_available)

    def test_capability_available_matches_matrix_for_every_read_operation(self):
        for operation in CAPABILITY_MATRIX:
            for daw in ("reaper", "ableton", "ardour"):
                d = evaluate({"operation": operation, "attributes": {"daw": daw}})
                expected = daw in CAPABILITY_MATRIX[operation]
                self.assertEqual(d.capability_available, expected, msg=(operation, daw))


class SourceSyncTests(unittest.TestCase):
    """Rules must not silently drift away from policy/deny.txt and
    policy/allow.txt — the whole point of naming those as source of
    truth in the design doc.
    """

    @classmethod
    def setUpClass(cls):
        def lines(path: pathlib.Path) -> set[str]:
            return {
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            }

        cls.deny_lines = lines(REPO_ROOT / "policy" / "deny.txt")
        cls.allow_lines = lines(REPO_ROOT / "policy" / "allow.txt")
        cls.all_policy_lines = cls.deny_lines | cls.allow_lines

    def test_every_rule_source_text_is_an_exact_policy_line(self):
        for rule in RULES:
            if rule.source_text is not None:
                self.assertIn(
                    rule.source_text,
                    self.all_policy_lines,
                    f"Rule {rule.rule_id!r}'s source_text does not exactly match a "
                    "current line in policy/deny.txt or policy/allow.txt",
                )

    def test_every_deny_txt_line_is_covered_by_a_rule(self):
        covered = {rule.source_text for rule in RULES if rule.source_text}
        uncovered = self.deny_lines - covered
        self.assertFalse(
            uncovered,
            f"policy/deny.txt line(s) not referenced by any rule: {uncovered}",
        )


class CapabilityMatrixTests(unittest.TestCase):
    """CAPABILITY_MATRIX must match what mcp-*/*/server.py actually
    implement — not what we'd like them to implement.
    """

    @staticmethod
    def _tool_names(server_path: pathlib.Path) -> set[str]:
        tree = ast.parse(server_path.read_text(encoding="utf-8"))
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("get_")
        }

    def test_reaper_has_tempo_and_tracks(self):
        tools = self._tool_names(REPO_ROOT / "mcp-reaper" / "reaper_mcp" / "server.py")
        self.assertIn("get_tempo", tools)
        self.assertIn("reaper", CAPABILITY_MATRIX["read.tempo"])
        self.assertIn("get_tracks", tools)
        self.assertIn("reaper", CAPABILITY_MATRIX["read.tracks"])

    def test_ableton_has_tempo_and_tracks(self):
        tools = self._tool_names(REPO_ROOT / "mcp-ableton" / "ableton_mcp" / "server.py")
        self.assertIn("get_tempo", tools)
        self.assertIn("ableton", CAPABILITY_MATRIX["read.tempo"])
        self.assertIn("get_tracks", tools)
        self.assertIn("ableton", CAPABILITY_MATRIX["read.tracks"])

    def test_ardour_has_no_tempo_tool(self):
        tools = self._tool_names(REPO_ROOT / "mcp-ardour" / "ardour_mcp" / "server.py")
        self.assertNotIn("get_tempo", tools)
        self.assertNotIn("ardour", CAPABILITY_MATRIX["read.tempo"])
        self.assertIn("get_tracks", tools)
        self.assertIn("ardour", CAPABILITY_MATRIX["read.tracks"])


if __name__ == "__main__":
    unittest.main()
