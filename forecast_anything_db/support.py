"""Particle value validation against a target's support.

`continuous`, `nominal`, and `ordinal` are implemented; every other support
raises NotImplementedError so a half-validated value space can never be stored.
Each deferred branch is a one-function addition when its first real use arrives.
"""

from __future__ import annotations

from .schemas import Support, SupportType

IMPLEMENTED: frozenset[SupportType] = frozenset(
    {SupportType.continuous, SupportType.nominal, SupportType.ordinal}
)


def validate_value(support: Support, value: object) -> None:
    """Raise ValueError if `value` is not a legal particle value for `support`.
    Raise NotImplementedError for supports not yet built."""
    t = support.type
    if t == SupportType.continuous:
        # bool is an int subclass; reject it explicitly.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"continuous support requires a real number; got {value!r}")
        return
    if t in (SupportType.nominal, SupportType.ordinal):
        # Ordinal validates identically to nominal; order only matters for
        # scoring, which lives outside this package.
        if not isinstance(value, str):
            raise ValueError(
                f"{t.value} support requires a category label (str); got {value!r}"
            )
        categories = support.categories or []
        if value not in categories:
            raise ValueError(f"{value!r} is not one of the categories {categories}")
        return
    raise NotImplementedError(
        f"support '{t.value}' is not implemented yet (continuous, nominal, ordinal)"
    )
