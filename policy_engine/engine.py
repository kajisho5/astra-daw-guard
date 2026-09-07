"""Policy Engine entrypoint: evaluate(action) -> Decision.

This is the one authoritative safety gate in astra-daw-guard. Contrast
with tools/deny_check.py, which is a heuristic, keyword-overlap sanity
check over free-text descriptions of an action — advisory only, and
explicitly not authoritative (see its own docstring). This module makes
the actual ALLOW/ASK/DENY call, and only ever sees structured Action
data — never natural language. Normalizing a user's or agent's plain
English/Japanese request into an Action dict is the calling agent's
job; keeping that boundary sharp is what stops this engine from having
to guess at meaning the way deny_check.py's keyword matching does.

Fail-closed: an operation this engine doesn't recognize, or a
well-formed operation missing fields it needs to decide, is DENY —
never ALLOW. "Could not determine" is not a reason to proceed.
"""

from __future__ import annotations

import dataclasses
from typing import Iterable, Sequence, Union

from .capabilities import mcp_supports
from .rules import ALLOW, ASK, DENY, RULES, Decision
from .schema import Action, ActionSchemaError

KNOWN_OPERATIONS = {
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
}


def _attach_capability_note(action: Action, decision: Decision) -> Decision:
    """Set `Decision.capability_available` for read.* Actions that name a
    DAW — see rules.Decision's docstring for why this is deliberately
    separate from `decision`/`rule_id`. Every other Action is returned
    unchanged (capability_available stays None: not applicable).
    """
    if not action.operation.startswith("read."):
        return decision
    daw = action.attr("daw")
    if not daw:
        return decision
    return dataclasses.replace(decision, capability_available=mcp_supports(daw, action.operation))


def evaluate(action: Union[dict, Action]) -> Decision:
    """Evaluate one Action and return an authoritative Decision.

    Accepts either an Action or a raw dict (parsed via Action.from_dict).
    Never raises for a malformed or unrecognized action — that case is
    itself a DENY decision, per this engine's fail-closed design, so
    callers can always trust the return value rather than having to
    wrap this in a try/except to stay safe.
    """
    if isinstance(action, dict):
        raw = action
        try:
            action = Action.from_dict(raw)
        except ActionSchemaError as exc:
            return Decision(
                decision=DENY,
                rule_id="INVALID_ACTION_SCHEMA",
                reason=f"Action could not be parsed: {exc}",
                operation=str(raw.get("operation", "")),
                target=str(raw.get("target", "")),
                attributes=raw.get("attributes", {}) if isinstance(raw.get("attributes"), dict) else {},
            )
    elif not isinstance(action, Action):
        # Neither a dict nor an already-built Action -- e.g. None, a
        # string, a list. This function's own docstring promises it
        # never raises for a malformed action; that promise must hold
        # for "malformed" in the broadest sense, not just "a dict with
        # the wrong shape".
        return Decision(
            decision=DENY,
            rule_id="INVALID_ACTION_SCHEMA",
            reason=f"Action must be a dict or Action instance, got {type(action).__name__}.",
            operation="",
            target="",
            attributes={},
        )

    if action.operation not in KNOWN_OPERATIONS:
        return Decision(
            decision=DENY,
            rule_id="UNKNOWN_OPERATION",
            reason=(
                f"{action.operation!r} is not in the Policy Engine's operation "
                "catalog. Unknown operations are denied rather than silently "
                "allowed."
            ),
            operation=action.operation,
            target=action.target,
            attributes=action.attributes,
        )

    for rule in RULES:
        decision = rule.evaluate(action)
        if decision is not None:
            return _attach_capability_note(action, decision)

    # A known operation that no rule matched (e.g. missing/invalid
    # attributes for that operation's decision logic): also fail closed.
    return Decision(
        decision=DENY,
        rule_id="NO_MATCHING_RULE",
        reason=(
            f"No rule produced a decision for operation {action.operation!r} "
            "with these attributes; denying rather than defaulting to allow."
        ),
        operation=action.operation,
        target=action.target,
        attributes=action.attributes,
    )


def evaluate_plan(actions: Sequence[Union[dict, Action]]) -> list[Decision]:
    """Evaluate a whole planned sequence of Actions up front (Issue #26).

    Returns one `Decision` per input Action, in the same order, by
    calling `evaluate()` on each independently — this is a stateless
    batching convenience, not a planner. It does NOT reason about
    dependencies between Actions (e.g. it will not notice that step 2
    only makes sense if step 1 is ALLOWed, or that step 3's DENY makes
    step 4 moot): every Action is evaluated exactly as if `evaluate()`
    had been called on it alone, with no memory of the others. Use this
    to get an up-front, single-pass verdict for a proposed multi-step
    task before starting it — see `checklists/before.md`.
    """
    return [evaluate(action) for action in actions]


# Worst-case-first, matching policy_engine.cli's exit code ordering
# (ALLOW=0, ASK=1, DENY=2): a DENY anywhere in a plan outranks an ASK,
# which outranks an all-ALLOW plan.
_DECISION_SEVERITY = {DENY: 2, ASK: 1, ALLOW: 0}


def worst_decision(decisions: Iterable[Decision]) -> str:
    """Return the most severe decision among `decisions` (DENY > ASK >
    ALLOW), or ALLOW for an empty sequence (there is nothing to block).
    """
    worst = ALLOW
    for decision in decisions:
        if _DECISION_SEVERITY[decision.decision] > _DECISION_SEVERITY[worst]:
            worst = decision.decision
    return worst


def plan_is_clear(decisions: Iterable[Decision]) -> bool:
    """True only if every Decision in `decisions` is ALLOW."""
    return worst_decision(decisions) == ALLOW
