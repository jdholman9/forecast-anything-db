"""Particle construction and validation.

Particles are the only stored distribution form. Step 1 supports the `samples`
kind: each particle is `{"value": <number>}` with uniform implied weight 1/N.
The db never *generates* values (no sampling, no parametric->particle
conversion); callers hand it finished bags. These helpers only reshape an
already-sampled bag and validate it. `pmf` ingest is deferred to the step that
adds discrete supports.
"""

from __future__ import annotations

from collections.abc import Iterable

from .schemas import ForecastKind, Support
from .support import validate_value


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
        raise NotImplementedError(
            "pmf ingest is not implemented in step 1 (samples only)"
        )

    raise ValueError(f"unknown forecast kind: {kind!r}")
