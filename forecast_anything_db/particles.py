"""Particle construction and validation.

Particles are the only stored distribution form. Two kinds:
- `samples`: each particle is `{"value": <x>}` with uniform implied weight 1/N
  (point forecasts, ensembles, Monte Carlo).
- `pmf`: each particle is `{"value": <label>, "weight": <w>}` with explicit mass
  summing to ~1, for discrete (categorical) supports.

The db never *generates* values (no sampling, no parametric->particle
conversion); callers hand it finished bags. These helpers only reshape an
already-sampled bag and validate it.
"""

from __future__ import annotations

from collections.abc import Iterable

from .config import PMF_WEIGHT_TOLERANCE
from .schemas import ForecastKind, Support, SupportType
from .support import validate_value

# pmf is point mass over discrete categories, not a density.
_PMF_SUPPORTS = frozenset(
    {SupportType.binary, SupportType.nominal, SupportType.ordinal, SupportType.count}
)


def point_to_samples(value: float) -> list[dict]:
    """A point forecast is a one-particle sample bag (N=1)."""
    return [{"value": float(value)}]


def samples_to_particles(values: Iterable[float]) -> list[dict]:
    """Wrap an already-sampled bag (e.g. ensemble / empirical) as particles."""
    vals = [float(v) for v in values]
    if not vals:
        raise ValueError("samples distribution requires at least one value")
    return [{"value": v} for v in vals]


def validate_distribution(
    support: Support, kind: ForecastKind, distribution: list[dict]
) -> None:
    """Validate a particle bag against the target support and forecast kind.
    Raises ValueError on malformed input, NotImplementedError for deferred kinds."""
    if not isinstance(distribution, list) or not distribution:
        raise ValueError("distribution must be a non-empty list of particles")

    if kind == ForecastKind.samples:
        for i, particle in enumerate(distribution):
            if not isinstance(particle, dict) or set(particle) != {"value"}:
                raise ValueError(
                    f"samples particle {i} must have exactly a 'value' key; "
                    f"got {sorted(particle) if isinstance(particle, dict) else type(particle)}"
                )
            validate_value(support, particle["value"])
        return

    if kind == ForecastKind.pmf:
        if support.type not in _PMF_SUPPORTS:
            raise ValueError(
                f"pmf is not valid for {support.type.value} support "
                "(discrete supports only: binary, nominal, ordinal, count)"
            )
        total = 0.0
        for i, particle in enumerate(distribution):
            if not isinstance(particle, dict) or set(particle) != {"value", "weight"}:
                raise ValueError(
                    f"pmf particle {i} must have exactly 'value' and 'weight' keys; "
                    f"got {sorted(particle) if isinstance(particle, dict) else type(particle)}"
                )
            weight = particle["weight"]
            if isinstance(weight, bool) or not isinstance(weight, (int, float)):
                raise ValueError(f"pmf particle {i} weight must be a number; got {weight!r}")
            if weight <= 0:
                raise ValueError(f"pmf particle {i} weight must be positive; got {weight}")
            validate_value(support, particle["value"])
            total += weight
        if abs(total - 1.0) > PMF_WEIGHT_TOLERANCE:
            raise ValueError(
                f"pmf weights must sum to ~1 (within {PMF_WEIGHT_TOLERANCE}); got {total}"
            )
        return

    raise ValueError(f"unknown forecast kind: {kind!r}")
