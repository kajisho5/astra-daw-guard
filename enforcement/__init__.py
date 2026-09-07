"""ASTRA Enforcement Boundary — reference implementation.

Gates actual tool execution behind `policy_engine`'s ALLOW/ASK/DENY
decisions, so a DENY (or an unconfirmed ASK) means the tool function is
never called — not just a rule an agent is asked to honor.

Read README.md in this directory before using this module: it explains
exactly what "reference implementation" means here (there is no live
Astra agent runtime inside this repository to attach to) and what this
does and does not integrate with.
"""

from .boundary import ApprovalRequired, EnforcementBlocked, ToolDenied, enforce, guarded

__all__ = [
    "enforce",
    "guarded",
    "EnforcementBlocked",
    "ToolDenied",
    "ApprovalRequired",
]
