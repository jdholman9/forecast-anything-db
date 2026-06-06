# Forecast Anything V2 - Build Plan

Implementation choices for the first code pass. `SPEC_V2.MD` is the public contract; this file is how to build it.

---

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.12 |
| Database | PostgreSQL, no SQLite fallback |
| ORM | SQLAlchemy 2.0 + psycopg 3 |
| Migrations | Alembic |
| Validation | Pydantic 2 |
| Distribution math | NumPy + SciPy |
| Scoring | Deferred; later use `scoringrules` or `properscoring` |
| Tests | pytest |

---

## Package Layout

```text
forecast-anything-v2/
  pyproject.toml
  alembic/
  forecast_anything_v2/
    __init__.py
    config.py
    db.py
    models.py
    schemas.py
    support.py
    particles.py
    api.py
    sources/
      census_mps.py
      polymarket.py
  tests/
    test_support.py
    test_particles.py
    test_api_smoke.py
```

Do not scaffold dashboards, scoring tables, source registry tables, presets, geography, or observed series.

---

## Constants

```python
DEFAULT_SOURCE_ID = "self"
DEFAULT_PARAMETRIC_SAMPLES = 2000
MAX_INLINE_PARTICLE_GUIDELINE = 10_000  # documentation/perf warning, not a hard reject
PMF_WEIGHT_TOLERANCE = 0.01
```

`DEFAULT_PARAMETRIC_SAMPLES` applies only when a parametric ingest helper samples a distribution. It does not override natural N for points, PMFs, or ensembles.

---

## Database Tables

### `target`

- `target_id` primary key.
- `question` text, required.
- `support` JSONB, required.
- `time_scope` JSONB, required.
- `resolution` JSONB, required.
- `created_at` timestamptz required.

### `forecast`

- `forecast_id` primary key.
- `target_id` FK.
- `source_id` text, default `"self"`.
- `as_of` timestamptz required.
- `ingested_at` timestamptz required, server-side default.
- `kind` text enum: `samples | pmf`.
- `distribution` JSONB required.
- unique constraint: `(target_id, source_id, as_of)`.

### `outcome`

- `target_id` primary key / FK.
- `observed_value` JSONB nullable.
- `observed_at` timestamptz required.

No score table.

---

## Validation

Validate at the API/write path after fetching target support.

### Timestamp Rules

- All datetimes must be timezone-aware UTC.
- Reject naive datetimes.
- If `as_of` is omitted, use `ingested_at`.

### Support Rules

| Support | Rule |
|---|---|
| `binary` | value must be integer `0` or `1` |
| `nominal` | value must be one of `categories` |
| `ordinal` | value must be one of ordered `categories` |
| `count` | value must be non-negative integer; reject above optional upper bound |
| `continuous` | value must be numeric |
| `bounded` | value must be numeric and inside `[lo, hi]` |
| `datetime` | value must be UTC-aware datetime |
| `multivariate` | raise `NotImplementedError` on ingest in v1 |

### Time Scope Rules

- `time_scope` is required for every target.
- `kind="instant"` requires `start` and rejects `end`.
- `kind="interval"` requires `start` and `end`; `end` must be after `start`.
- `kind="datetime_answer"` rejects `start` and `end`; the forecast value is itself a datetime.
- All supplied timestamps must be timezone-aware UTC.

### Kind Rules

- `samples` is valid for all implemented supports.
- `pmf` is valid only for `binary`, `nominal`, `ordinal`, and `count`.
- `pmf` weights must be positive and sum to within `PMF_WEIGHT_TOLERANCE` of 1.
- `samples` particles must not carry weights.

### Quantile Input

Quantile helpers must convert quantiles into a sampled distribution before writing a forecast row.

Do not store quantile markers directly as uniform samples unless the caller explicitly asks for a discrete three-point forecast.

Raw quantile ingest validation:

- Require at least 3 quantile points.
- Require probabilities strictly between 0 and 1.
- Require probabilities strictly increasing and values non-decreasing.
- Require at least one lower quantile `p <= 0.25`.
- Require at least one central quantile `0.4 <= p <= 0.6`.
- Require at least one upper quantile `p >= 0.75`.
- Require declared/default tail policy outside the lowest and highest supplied p.

Implementation can start with one simple helper:

```python
def samples_from_quantiles(points: list[tuple[float, float]], n: int = 2000) -> list[float]:
    """Interpolate inverse CDF from (p, value) pairs and sample uniform p-grid."""
```

---

## API Surface

Minimum first pass:

```python
create_target(question, support, time_scope, resolution)
get_target(target_id)
list_targets()

submit_forecast(target_id, distribution, *, kind, source_id="self", as_of=None)
get_forecast(forecast_id)
list_forecasts(target_id, *, source_id=None)
delete_forecast(forecast_id)

record_outcome(target_id, observed_value, observed_at)
get_outcome(target_id)
delete_outcome(target_id)
```

No scoring API in first pass unless the storage API is done and tested.

---

## First Source Helpers

Build these only after the core API is usable:

- `sources/census_mps.py`: creates continuous interval targets and submits `samples`.
- `sources/polymarket.py`: creates binary/nominal targets and submits `pmf`.

Jacob's ad-hoc forecasts should use the public API, not a special source module.

---

## Tests Required

- Create target with required support/time_scope/resolution.
- Reject missing support.
- Reject missing or invalid time_scope.
- Freeze resolution once first forecast lands.
- Submit point forecast as `samples` N=1.
- Submit parametric forecast sampled to N=2000 by default.
- Submit PMF forecast and reject bad weights.
- Reject PMF for continuous/bounded/datetime support.
- Reject bounded value outside bounds.
- Reject naive datetimes.
- Enforce forecast uniqueness.
- Record outcome, including `observed_value=None`.
- Confirm no source/geography/condition/observed_series/scoring tables exist.

---

## Build Order

1. Scaffold package, `pyproject.toml`, Alembic.
2. Add Pydantic support/particle schemas.
3. Add SQLAlchemy models and first migration.
4. Add API write path and validation.
5. Add tests around target/forecast/outcome.
6. Add Census MPS helper.
7. Add Polymarket/Manifold helper.
8. Revisit scoring only after storage is boring.
