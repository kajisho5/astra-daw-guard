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
from typing import Union

from .capabilities import mcp_supports
from .rules import DENY, RULES, Decision
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
