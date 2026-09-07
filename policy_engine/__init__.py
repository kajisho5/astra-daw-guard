"""astra-daw-guard Policy Engine: authoritative ALLOW/ASK/DENY enforcement.

This is the one authoritative safety gate in this repository. Contrast
with tools/deny_check.py, which is a heuristic, natural-language sanity
check an agent may run before Computer Use — advisory only, and never a
substitute for this engine.

See README.md in this directory for the Action Schema, decision format,
fail-closed philosophy, and capability model.
"""

from .engine import evaluate
from .rules import ALLOW, ASK, DENY, Decision
from .schema import Action, ActionSchemaError

__all__ = [
    "evaluate",
    "ALLOW",
    "ASK",
    "DENY",
    "Decision",
    "Action",
    "ActionSchemaError",
]
