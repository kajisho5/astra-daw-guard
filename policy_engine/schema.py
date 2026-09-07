"""Action Schema for astra-daw-guard's Policy Engine.

An Action is the *only* input the Policy Engine ever sees. It is
deliberately not natural language: turning a user's or agent's plain
English/Japanese intent into an Action is the calling agent's job, not
this engine's. The engine only ever reasons about structured data —
see engine.py's docstring for why that boundary matters.

Shape:

    {
        "operation": "project.save",
        "target": "current",
        "attributes": {"mode": "overwrite"}
    }

`operation` must be one of `policy_engine.engine.KNOWN_OPERATIONS`.
Anything else is rejected by the engine as UNKNOWN_OPERATION — that is
the fail-closed boundary the whole engine is built around, not
something this module enforces itself (this module only checks
structural validity: is it a dict, does it have a string operation).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ActionSchemaError(ValueError):
    """Raised when a raw value cannot be parsed into an Action at all."""


@dataclass(frozen=True)
class Action:
    operation: str
    target: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Any) -> "Action":
        if not isinstance(data, dict):
            raise ActionSchemaError(
                f"action must be a JSON object, got {type(data).__name__}"
            )
        operation = data.get("operation")
        if not isinstance(operation, str) or not operation:
            raise ActionSchemaError(
                "action must have a non-empty string 'operation' field"
            )
        target = data.get("target", "")
        if not isinstance(target, str):
            raise ActionSchemaError("'target', if present, must be a string")
        attributes = data.get("attributes", {})
        if not isinstance(attributes, dict):
            raise ActionSchemaError("'attributes', if present, must be an object")
        return cls(operation=operation, target=target, attributes=dict(attributes))

    def attr(self, name: str, default: Any = None) -> Any:
        return self.attributes.get(name, default)
