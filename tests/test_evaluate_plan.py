"""Tests for policy_engine.evaluate_plan/plan_is_clear/worst_decision
(Issue #26) -- a stateless batch wrapper over evaluate(), not a planner.

Not a re-test of the rules themselves (see tests/test_policy_engine.py
for that) or of the CLI's own flags (see tests/test_cli.py's
EvaluatePlanCliTests for --plan). This locks down the one property that
matters here: batching must never change what a single evaluate() call
would have returned for the same Action. Run from the repo root:

    python3 -m unittest tests.test_evaluate_plan -v
"""

from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from policy_engine import (  # noqa: E402
    ALLOW,
    ASK,
    DENY,
    evaluate,
    evaluate_plan,
    plan_is_clear,
    worst_decision,
)

_ALLOW_ACTION = {"operation": "read.tempo"}
_ASK_ACTION = {"operation": "project.save", "attributes": {"mode": "save_as"}}
_DENY_ACTION = {"operation": "project.save", "attributes": {"mode": "overwrite"}}


class EvaluatePlanMatchesIndividualEvaluateTests(unittest.TestCase):
    """The core guarantee: evaluate_plan is exactly evaluate() mapped
    over the list, in order -- no cross-Action state, no reordering.
    """

    def test_empty_plan_returns_empty_list(self):
        self.assertEqual(evaluate_plan([]), [])

    def test_single_action_plan_matches_evaluate(self):
        (decision,) = evaluate_plan([_ALLOW_ACTION])
        self.assertEqual(decision.decision, evaluate(_ALLOW_ACTION).decision)
        self.assertEqual(decision.rule_id, evaluate(_ALLOW_ACTION).rule_id)

    def test_order_is_preserved(self):
        actions = [_DENY_ACTION, _ALLOW_ACTION, _ASK_ACTION]
        decisions = evaluate_plan(actions)
        self.assertEqual([d.decision for d in decisions], [DENY, ALLOW, ASK])

    def test_each_decision_is_independent_of_the_others_in_the_plan(self):
        # A DENY earlier in the plan must not affect a later Action's
        # own independent evaluation -- there is no shared state.
        plan_with_deny_first = evaluate_plan([_DENY_ACTION, _ALLOW_ACTION])
        allow_alone = evaluate(_ALLOW_ACTION)
        self.assertEqual(plan_with_deny_first[1].decision, allow_alone.decision)
        self.assertEqual(plan_with_deny_first[1].rule_id, allow_alone.rule_id)

    def test_accepts_a_mix_of_dicts_and_already_known_operations(self):
        decisions = evaluate_plan([_ALLOW_ACTION, _ASK_ACTION, _DENY_ACTION])
        self.assertEqual(len(decisions), 3)


class WorstDecisionTests(unittest.TestCase):
    def test_empty_sequence_is_allow(self):
        self.assertEqual(worst_decision([]), ALLOW)

    def test_all_allow_is_allow(self):
        decisions = evaluate_plan([_ALLOW_ACTION, _ALLOW_ACTION])
        self.assertEqual(worst_decision(decisions), ALLOW)

    def test_ask_outranks_allow(self):
        decisions = evaluate_plan([_ALLOW_ACTION, _ASK_ACTION])
        self.assertEqual(worst_decision(decisions), ASK)

    def test_deny_outranks_ask_and_allow(self):
        decisions = evaluate_plan([_ALLOW_ACTION, _ASK_ACTION, _DENY_ACTION])
        self.assertEqual(worst_decision(decisions), DENY)

    def test_deny_outranks_ask_regardless_of_order(self):
        decisions = evaluate_plan([_DENY_ACTION, _ASK_ACTION])
        self.assertEqual(worst_decision(decisions), DENY)


class PlanIsClearTests(unittest.TestCase):
    def test_true_for_empty_plan(self):
        self.assertTrue(plan_is_clear([]))

    def test_true_when_every_decision_is_allow(self):
        decisions = evaluate_plan([_ALLOW_ACTION, _ALLOW_ACTION])
        self.assertTrue(plan_is_clear(decisions))

    def test_false_when_any_decision_is_ask(self):
        decisions = evaluate_plan([_ALLOW_ACTION, _ASK_ACTION])
        self.assertFalse(plan_is_clear(decisions))

    def test_false_when_any_decision_is_deny(self):
        decisions = evaluate_plan([_ALLOW_ACTION, _DENY_ACTION])
        self.assertFalse(plan_is_clear(decisions))


if __name__ == "__main__":
    unittest.main()
