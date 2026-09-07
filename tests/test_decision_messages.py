"""Tests for tools/decision_message.py and tools/decision_messages.json
-- the Approval UX / Failure UX phases of Issue #16.

Approval UX and Failure UX turned out to be the same underlying gap:
an agent holding a policy_engine Decision had no ready-made, consistent
way to phrase what it means to the user -- a refusal for DENY, a
confirmation prompt for ASK -- beyond tools/refusal_message.py, which
only covers DENY and is keyed by its own slug rather than
policy_engine's rule_id. This suite locks down that the message catalog
stays in sync with policy_engine/rules.py (Issue #16's recurring
"never let a machine-readable source of truth silently drift" pattern)
and that the fallback path never leaves a caller with nothing to say.
Run from the repo root:

    python3 -m unittest tests.test_decision_messages -v
"""

from __future__ import annotations

import pathlib
import sys
import unittest
from dataclasses import dataclass

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from policy_engine.rules import ALLOW, ASK, DENY, RULES  # noqa: E402
from tools.decision_message import format_message, load, message_for_decision, message_for_rule_id  # noqa: E402

# The three fail-closed rule_ids policy_engine.engine.evaluate() can
# return that aren't in RULES (they're synthesized directly in
# evaluate(), see engine.py).
_FAIL_CLOSED_RULE_IDS = {"UNKNOWN_OPERATION", "INVALID_ACTION_SCHEMA", "NO_MATCHING_RULE"}


@dataclass
class _FakeDecision:
    decision: str
    rule_id: str
    reason: str


class CatalogSyncTests(unittest.TestCase):
    """Every DENY/ASK rule_id a real Decision can carry must have a
    message entry -- an ALLOW never needs one (an agent just proceeds),
    so ALLOW rule_ids are deliberately not required here.
    """

    @classmethod
    def setUpClass(cls):
        cls.entries = load(pathlib.Path(__file__).resolve().parent.parent / "tools" / "decision_messages.json")
        cls.covered_rule_ids = {m["rule_id"] for m in cls.entries}

    def test_every_deny_and_ask_rule_id_in_rules_py_is_covered(self):
        deny_and_ask_rule_ids = {r.rule_id for r in RULES if r.decision in (DENY, ASK)}
        missing = deny_and_ask_rule_ids - self.covered_rule_ids
        self.assertEqual(missing, set(), f"rule_ids missing from decision_messages.json: {missing}")

    def test_every_fail_closed_rule_id_is_covered(self):
        missing = _FAIL_CLOSED_RULE_IDS - self.covered_rule_ids
        self.assertEqual(missing, set(), f"fail-closed rule_ids missing: {missing}")

    def test_no_entry_references_a_nonexistent_or_allow_rule_id(self):
        real_rule_ids = {r.rule_id for r in RULES} | _FAIL_CLOSED_RULE_IDS
        allow_rule_ids = {r.rule_id for r in RULES if r.decision == ALLOW}
        for rule_id in self.covered_rule_ids:
            with self.subTest(rule_id=rule_id):
                self.assertIn(rule_id, real_rule_ids)
                self.assertNotIn(rule_id, allow_rule_ids)

    def test_kind_matches_the_rule_s_actual_decision(self):
        rule_decision = {r.rule_id: r.decision for r in RULES}
        for entry in self.entries:
            if entry["rule_id"] in _FAIL_CLOSED_RULE_IDS:
                self.assertEqual(entry["kind"], "deny")
                continue
            with self.subTest(rule_id=entry["rule_id"]):
                self.assertEqual(entry["kind"], rule_decision[entry["rule_id"]].lower())

    def test_every_entry_has_non_empty_en_and_ja(self):
        for entry in self.entries:
            with self.subTest(rule_id=entry["rule_id"]):
                self.assertTrue(entry["en"].strip())
                self.assertTrue(entry["ja"].strip())

    def test_no_duplicate_rule_ids(self):
        ids = [m["rule_id"] for m in self.entries]
        self.assertEqual(len(ids), len(set(ids)))


class MessageForDecisionTests(unittest.TestCase):
    def test_deny_decision_gets_its_catalog_message(self):
        d = _FakeDecision(decision=DENY, rule_id="PROJECT_OVERWRITE", reason="unused")
        text = message_for_decision(d, lang="en")
        self.assertIn("won't overwrite", text)

    def test_ask_decision_gets_its_catalog_message(self):
        d = _FakeDecision(decision=ASK, rule_id="SAVE_AS_UNCONFIRMED", reason="unused")
        text = message_for_decision(d, lang="ja")
        self.assertIn("保存してよろしいですか", text)

    def test_unmapped_rule_id_falls_back_to_reason_rather_than_crashing(self):
        d = _FakeDecision(decision=DENY, rule_id="SOME_FUTURE_RULE_NOT_YET_CATALOGED", reason="the real reason text")
        self.assertEqual(message_for_decision(d), "the real reason text")

    def test_message_for_rule_id_returns_none_for_unknown_id(self):
        self.assertIsNone(message_for_rule_id("SOME_FUTURE_RULE_NOT_YET_CATALOGED"))

    def test_lang_both_includes_english_and_japanese(self):
        d = _FakeDecision(decision=DENY, rule_id="PROJECT_OVERWRITE", reason="unused")
        text = message_for_decision(d, lang="both")
        self.assertIn("won't overwrite", text)
        self.assertIn("上書き保存しません", text)


if __name__ == "__main__":
    unittest.main()
