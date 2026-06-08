"""Particle value validation against a target's support.

`continuous` is implemented; every other support raises NotImplementedError so a
half-validated value space can never be stored. Each deferred branch is a
one-function addition when its first real use arrives.
"""

from __future__ import annotations

from .schemas import Support, SupportType

IMPLEMENTED: frozenset[SupportType] = frozenset({SupportType.continuous})


def validate_value(support: Support, value: object) -> None:
    """Raise ValueError if `value` is not a legal particle value for `support`.
    Raise NotImplementedError for supports not yet built."""
    t = support.type
    if t == SupportType.continuous:
        # bool is an int subclass; reject it explicitly.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"continuous support requires a real number; got {value!r}")
        return
    raise NotImplementedError(
        f"support '{t.value}' is not implemented yet (continuous only)"
    )
