"""ASTRA Enforcement Boundary — reference implementation.

`policy_engine.evaluate` answers exactly one question — "what is the
decision for this Action?" — and never executes anything (see
policy_engine/README.md). This module is the other half of the
boundary: given an Action and an actual callable (the tool), it asks
the Policy Engine first and only calls the tool if the decision allows
it. That separation is deliberate: Policy Engine stays a pure function
from Action to Decision, and this module owns the one responsibility of
turning a Decision into "did the tool run or not."

The core guarantee this module exists to provide: a DENY decision means
the wrapped tool is *never* called, regardless of any `approved` flag a
caller passes. `approved=True` can only ever turn an ASK into an
execution (for that exact Action, on that one call) — it cannot
override a DENY. See enforcement/README.md's "Security" section for why
that boundary is drawn exactly there.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, Optional, TypeVar, Union

from policy_engine import ALLOW, ASK, DENY, Decision, evaluate
from policy_engine.schema import Action

T = TypeVar("T")


class EnforcementBlocked(RuntimeError):
    """Base class for a blocked tool call.

    `.decision` is the exact, unmodified `policy_engine.Decision` the
    Policy Engine returned — never re-wrapped into a vaguer error, so a
    caller (or a human reading a traceback) can always see the real
    `rule_id` and `reason`.
    """

    def __init__(self, decision: Decision):
        self.decision = decision
        super().__init__(f"{decision.decision} ({decision.rule_id}): {decision.reason}")


class ToolDenied(EnforcementBlocked):
    """The Policy Engine returned DENY. The tool was never called, and
    no `approved` flag can change that — DENY has no override.
    """


class ApprovalRequired(EnforcementBlocked):
    """The Policy Engine returned ASK. The tool was never called.

    Call `enforce` (or the `guarded` function) again with
    `approved=True`, passing the *same* Action, once — and only once —
    the user has explicitly confirmed that specific action in this
    turn. Do not infer approval from an earlier, different action, from
    silence, or from a general "this seems fine" judgment call: the
    approval this parameter represents must be about the action that
    was actually described to the user.
    """


def _record(
    audit_log: Optional[list[dict]], decision: Decision, *, executed: bool
) -> None:
    if audit_log is None:
        return
    entry = decision.to_dict()
    entry["executed"] = executed
    entry["timestamp"] = time.time()
    audit_log.append(entry)


def enforce(
    action: Union[dict, Action],
    tool: Callable[[], T],
    *,
    approved: bool = False,
    audit_log: Optional[list[dict]] = None,
) -> T:
    """Call `tool()` only if the Policy Engine allows `action`.

    - ALLOW: calls `tool()` and returns its result.
    - ASK and `approved=True`: calls `tool()` and returns its result.
      This is how a caller carries out an action after obtaining
      explicit, this-action user confirmation — the caller is asserting
      that confirmation happened; this function has no way to verify it
      independently (see `ApprovalRequired`'s docstring).
    - ASK and `approved=False` (the default): raises `ApprovalRequired`.
      `tool` is never called.
    - DENY: raises `ToolDenied`, unconditionally. `tool` is never
      called, regardless of `approved`.

    If `audit_log` is given, one dict (the Decision plus `executed` and
    `timestamp`) is appended for every call, whether blocked or not.
    """
    decision = evaluate(action)

    if decision.decision == DENY:
        _record(audit_log, decision, executed=False)
        raise ToolDenied(decision)

    if decision.decision == ASK and not approved:
        _record(audit_log, decision, executed=False)
        raise ApprovalRequired(decision)

    _record(audit_log, decision, executed=True)
    return tool()


def guarded(build_action: Callable[..., Union[dict, Action]]):
    """Decorator: gate a tool function behind the Policy Engine.

    `build_action(*args, **kwargs)` must return the Action describing
    what calling the wrapped function with those same arguments would
    do — it is called with exactly the arguments the wrapped function
    is called with (minus `approved`/`audit_log`, see below).

    The wrapped function gains two new keyword-only parameters that are
    consumed here and never forwarded to the original function:
    `approved` (default False) and `audit_log` (default None) — see
    `enforce` above for what they do.

    Example:

        @guarded(lambda name: {"operation": "track.create", "attributes": {"name": name}})
        def create_track(name):
            ...  # only runs if the Policy Engine allows it
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(
            *args: Any,
            approved: bool = False,
            audit_log: Optional[list[dict]] = None,
            **kwargs: Any,
        ) -> T:
            action = build_action(*args, **kwargs)
            return enforce(
                action,
                lambda: fn(*args, **kwargs),
                approved=approved,
                audit_log=audit_log,
            )

        return wrapper

    return decorator
