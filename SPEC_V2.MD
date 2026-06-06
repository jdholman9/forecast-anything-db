# Forecast Anything - Specification V2

Supersedes V1. This is the public contract for the first build.

The project is an atomic database layer for probabilistic forecasts. It stores:

1. **Targets**: questions plus answer support and resolution rules.
2. **Forecasts**: dated probability distributions for targets.
3. **Outcomes**: the one settling value for each target.

It does not store scoring results, entry windows, groups, estimates, vintages, source registries, geography systems, conditional logic, dashboards, or lifecycle automation.

---

## 0. One-Paragraph Version

`forecast_anything` records probabilistic forecasts for arbitrary questions. A forecast is stored as particles: either uniform samples or an explicit PMF. A target defines what answer values are valid and how the question will resolve. An outcome records the settling truth. Everything else is a layer above the atom.

---

## 1. Core Entities

### Target

```python
target {
  target_id
  question: str                  # required; unambiguous human-readable question
  support: Support               # required; answer value shape
  resolution: ResolutionRule     # required; frozen on first forecast
  period_start, period_end       # optional; UTC; equal means an instant
  created_at                     # UTC
}
```

To create a target, the caller must provide `question`, `support`, and `resolution`. No default support. A default that is wrong half the time is worse than no default.

### Forecast

```python
forecast {
  forecast_id
  target_id
  source_id: str                 # default "self"; not a FK in v1
  as_of                          # semantic forecast timestamp, UTC
  ingested_at                    # server write timestamp, UTC
  kind: "samples" | "pmf"        # discriminator for particle shape
  distribution: list[Particle]   # inline JSONB

  # UNIQUE (target_id, source_id, as_of)
}
```

`as_of` and `ingested_at` are different. Backfilled forecasts set historical `as_of` with current `ingested_at`. If `as_of` is omitted, it defaults to `ingested_at`.

Corrected forecasts at the same `(target_id, source_id, as_of)` require explicit delete-then-write. No silent duplicates.

### Outcome

```python
outcome {
  target_id
  observed_value: nullable       # NULL = settled with no observable value
  observed_at                    # required UTC timestamp

  # UNIQUE (target_id)
}
```

Absence of an outcome row means pending. Presence of a row with `observed_value = NULL` means explicitly settled but not scoreable: voided question, unobservable target, bad premise, etc.

V1 allows one settling outcome per target. Revisions, first-print-vs-latest comparisons, and latent estimates belong to a future sibling project.

---

## 2. Particles

Particles are the only stored distribution representation.

There are two forecast kinds:

| Kind | Particle shape | Meaning |
|---|---|---|
| `samples` | `{value}` | Uniform implied weight `1/N`; used for point forecasts, sampled parametrics, Monte Carlo, MCMC |
| `pmf` | `{value, weight}` | Explicit mass per discrete value; weights must sum to about 1 |

`N` is natural to the input:

- Point estimate: `samples`, N=1.
- 3-category PMF: `pmf`, N=3.
- Parametric `Normal(mu, sigma)`: sampled to `samples`, N=2000 by default.
- Ensemble forecast: `samples`, N=ensemble size.

Parametric formulas are not stored. They are ingest formats only. The stored row contains particles.

Quantiles are also ingest formats, not storage formats. A quantile forecast is viable only when it contains enough information to infer location, spread, and both tails under a documented tail policy.

Minimum raw quantile ingest for v1:

- At least 3 quantile points.
- Probabilities strictly between 0 and 1.
- Probabilities strictly increasing; values non-decreasing.
- At least one lower quantile with `p <= 0.25`.
- At least one central quantile with `0.4 <= p <= 0.6`.
- At least one upper quantile with `p >= 0.75`.
- Tail policy declared or defaulted for below the lowest p and above the highest p.

`p10/p50/p90` qualifies. `p50` alone and `p15` alone do not. A single value forecast is still allowed, but it must be submitted as a point forecast, not as a one-quantile distribution.

Fewer quantiles can work only when paired with an explicit parametric family, e.g. fitting a Normal from `p10/p90`. That is parametric-from-quantiles ingest, not raw quantile ingest.

Particle bags are stored inline in the `forecast.distribution` JSONB column for v1. Soft performance cliff: around 10k particles per forecast. Above that, writes still work but reads will drag. A long `particle` table is a future migration, not v1 work.

---

## 3. Support

Support determines what a particle value is and which scores are valid later.

| Type | Particle value | Validation |
|---|---|---|
| `binary` | integer `0` or `1` | reject anything else |
| `nominal` | category label | must be in `categories` |
| `ordinal` | ordered category label | must be in `categories`; order matters |
| `count` | non-negative integer | reject negatives; reject above optional upper bound |
| `continuous` | real number | no range check |
| `bounded` | real number in `[lo, hi]` | reject outside bounds |
| `datetime` | UTC-aware timestamp | reject naive datetimes |
| `multivariate` | vector | schema admits; ingest deferred |

`Support` fields:

```python
Support {
  type
  categories: list[str] | None     # nominal / ordinal
  bounds: tuple[float, float] | None # bounded; optional upper bound for count
  units: str | None
  dims: list[Support] | None        # multivariate
}
```

`pmf` is valid only for discrete supports: `binary`, `nominal`, `ordinal`, and `count`. Reject `pmf` for `continuous`, `bounded`, `datetime`, and `multivariate`.

Multivariate support is schema-admitted but build-deferred. The Pydantic model may accept `type="multivariate"` and `dims`, but ingest raises `NotImplementedError` until a real source needs it.

---

## 4. Resolution Rule

The resolution description is stated before forecasts and frozen once the first forecast lands.

```python
ResolutionRule {
  description: str              # required; human-readable settlement rule
  source_id: str | None         # optional; source named by the rule, if useful
  locked_at: timestamp | None   # system metadata; null until first forecast
}
```

`locked_at` is not caller-supplied target metadata. It starts null and is set by the system when the first forecast lands. After that point, the rule fields are immutable. Without this, scoring is not trustworthy.

Per-source canonical resolution rules live in the source ingest scripts, not in a registry. A `presets.py` module and `ResolutionRule.preset` field were deliberately cut because they duplicate source scripts and invite drift.

---

## 5. Layering

Atomic means: if you remove this field/table, is the forecast still complete and later scorable? If yes, it is not atomic.

| Atomic in v1 | Layer above / not stored in atom |
|---|---|
| Target | Entry windows |
| Forecast | Batches, groups, themes |
| Outcome | Scoring results |
| Support | Dashboards |
| Resolution rule | Alerts and scheduled runs |

Scoring is a layer, not a stored atom. Scores are functions over `(forecast.distribution, outcome.observed_value)`. When scoring is built, compute on demand. Do not store score rows or cache results in the atomic schema for v1.

---

## 6. Deferred and Deleted

Deleted from v1:

- Estimates as first-class objects with revision lineage.
- `observed_series`.
- Parametric storage as a distinct representation.
- `target.geography`.
- `target.condition` and the `Assumption` type.
- `forecast.provenance`.
- `ResolutionRule.resolve_at`.
- `ResolutionRule.preset` and `presets.py`.
- `Support.score_scale`.
- Source table / FK.
- Score cache.

Deferred:

- Scoring implementation.
- Entry windows and grouping UI.
- Geography hierarchy and spatial joins.
- Long `particle` table.
- Multivariate ingest and scoring.
- Estimates/vintages sibling project.

---

## 7. Stack

| Need | Choice |
|---|---|
| Language | Python 3.12 |
| Database | PostgreSQL + JSONB |
| ORM | SQLAlchemy 2.0 + psycopg |
| Migrations | Alembic |
| Validation | Pydantic 2 |
| Distribution math | NumPy + SciPy |
| Scoring later | `scoringrules` or `properscoring` |
| Tests | pytest |

No SQLite fallback in v1. Postgres-first avoids pretending JSONB and timestamp behavior are portable when they are not.

---

## 8. First Sources

The first build should exercise the smallest useful matrix:

| Source | Supports / kinds | Why |
|---|---|---|
| Census MPS | `continuous` x `samples` | Real workflow, familiar data |
| Polymarket or Manifold | `binary` / `nominal` x `pmf` | Discrete probabilistic forecasts |
| Jacob's ad-hoc forecasts | `continuous` x `samples` | Personal on-ramp |

This is enough to test target creation, PMF validation, sampled parametric ingest, point forecasts, source filtering, outcome recording, and UTC timestamp behavior.

---

## 9. Positioning

The empty square is a domain-agnostic, embeddable, distribution-first atomic layer:

- More general than Fatebook because it is not binary-only.
- More embeddable than Metaculus because it is local infrastructure, not a closed platform.
- Lighter than hubverse because cadence, rounds, horizons, and windows are not baked into the atom.
- Less clever than Squiggle because formulas are ingest helpers, not storage semantics.

The public contract is the schema and write-path validation. Keep that small.
