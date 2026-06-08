# forecast-anything-db

A tiny Postgres database for forecasts of any shape — a single number, a
category, or a full distribution. You hand it a finished forecast; it validates
the shape, stores it, and hands it back. It never invents the numbers.

---

## Why store a distribution instead of a number?

*A point forecast is still first-class — it's just a one-particle bag. This
section is about why richer usually beats a bare number when you can manage it,
not a requirement to provide one.*

A point forecast — "120 thousand permits" — hides everything you don't know. The
single number looks confident, but it throws away the part that actually matters
for a decision: how wrong you might be, and in which direction.

A distribution keeps that. The spread *is* the information.

- **It's honest.** "Probably around 120, but anywhere from 90 to 160" is a
  different claim than "120." Storing the range stops you from pretending to a
  precision you don't have.
- **It scores fairly.** Proper scoring rules (CRPS, log score) grade the whole
  shape against what actually happened. They reward being both sharp *and*
  calibrated, and you can't game them by hedging to the middle. A point forecast
  can only ever be graded on distance from one number.
- **Real decisions are asymmetric.** Being 20 too high rarely costs the same as
  being 20 too low. To make that call you need the tails, not just the mean.
- **It's lossless.** You can always collapse a distribution to a point (take the
  mean). You can't recover a distribution from a point. Store the rich object and
  throw information away later if you want — not the other way around.

## How do I come up with one?

You don't need a fancy model. A reasonable distribution falls out of a point
forecast plus your track record:

1. **Start with your best single guess.** You usually already have this.
2. **Wrap your past errors around it.** If your 6-month-ahead forecasts have
   historically landed within ±15, that error bag *is* your uncertainty. Add
   those historical errors to your point and you have a sample bag.
3. **Or back out a Normal from an interval.** If you can say "80% chance it lands
   in `[lo, hi]`," then `sigma ≈ (hi − lo) / 2.56`. Sample it.
4. **Widen with horizon.** Further out = more uncertain. Don't reuse next month's
   spread for next year.
5. **Sanity-check the tails against base rates.** Don't put mass on impossible
   values — permits can't go negative, a share can't exceed 100%.
6. **Store it as samples.** A bag of draws is all the database wants.

The work of *making* the distribution lives in your code (a "producer"). This
database just keeps it.

---

## What it is

Three tables, one job: record what was forecast and what actually happened, so a
scoring layer on top can grade it later.

- **Target** — the question, plus what a valid answer looks like, what time it
  refers to, and how it settles.
- **Forecast** — one dated distribution for a target, stored as particles.
- **Outcome** — the single value that settled the target.

That's the whole atom. Scoring, dashboards, and entry windows sit *on top*; value
generation sits *upstream* in your producer; revision/vintage history sits
*alongside*. None of them live here — the database only validates and stores, and
never generates a forecast value. (See "What's built vs deferred" below for how
those three relate to this repo.)

## Quickstart

```bash
# 1. Point the package at a Postgres database (see "Database" below)
export FA_DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:5432/forecast_anything_v2"

# 2. Install and create the schema
pip install -e .
alembic upgrade head

# 3. Run the end-to-end demo
python examples/quickstart.py
```

```python
from datetime import datetime, timezone
from forecast_anything_db import (
    Support, SupportType, TimeScope, TimeScopeKind, ForecastKind,
    create_target, submit_forecast, record_outcome,
)

# A question: how many permits in March 2026?
target_id = create_target(
    question="US 5+ unit multifamily permits for Mar 2026 (thousands, NSA)?",
    support=Support(type=SupportType.continuous, units="thousands of permits"),
    time_scope=TimeScope(
        kind=TimeScopeKind.interval,
        start=datetime(2026, 3, 1, tzinfo=timezone.utc),
        end=datetime(2026, 4, 1, tzinfo=timezone.utc),
    ),
    resolution={"description": "Census BPS 5+ unit permits, NSA, thousands."},
)

# A forecast: a bag of draws your model already produced.
draws = [118.0, 121.5, 119.2, 125.0, 117.8]
submit_forecast(target_id, [{"value": v} for v in draws], kind=ForecastKind.samples)

# Later, the truth.
record_outcome(target_id, 122.4, observed_at=datetime.now(timezone.utc))
```

## Core concepts

### Particles — the only stored form

Every distribution is a list of **particles**: a flat bag of draws, no formulas.
Two kinds are implemented:

| Kind | Particle | N | For |
|---|---|---|---|
| `samples` | `{"value": <x>}`, implied weight `1/N` | natural to the data | point forecasts (N=1), ensembles, Monte Carlo, sampled parametrics |
| `pmf` | `{"value": <label>, "weight": <w>}`, weights sum to ~1 | one per category | explicit odds over a fixed category set (e.g. `D` 0.6 / `R` 0.35 / `other` 0.05) |

A point forecast is just `samples` with N=1. A categorical point forecast is
`samples` with a label value (`[{"value": "D"}]`). `pmf` is for discrete supports
only — it's rejected for `continuous`.

The database never builds particles for you. Your producer samples its model,
wraps its error bag, or backs out a Normal, then hands the finished list to
`submit_forecast`. Helpers for the mechanical reshaping (not generation) live in
`forecast_anything_db.particles`: `point_to_samples`, `samples_to_particles`.

### Support — what a valid answer looks like

`continuous`, `bounded`, `nominal`, and `ordinal` are implemented end-to-end.
`bounded` is a real number constrained to an inclusive `[lo, hi]` range (a share
in `[0, 1]`, a percentage in `[0, 100]`). Nominal and ordinal validate a value
against a fixed `categories` list (order only matters for scoring, which lives on
top, so the two validate identically here). The enum admits four others —
`binary`, `count`, `datetime`, `multivariate` — so the schema is stable, but value
validation for them raises `NotImplementedError` until a real use needs it. No
half-built value space can be stored.

### Time scope — what time the answer refers to

- `instant` — a stock at a point in time ("S&P close on 2026-12-31"). Needs `start`.
- `interval` — a flow or window ("permits in Q3"). Needs `start` and `end`.
- `datetime_answer` — the answer *is* a date ("when does it ship?"). Needs neither.

All timestamps are timezone-aware UTC; naive datetimes are rejected.

### Resolution — how it settles

A free-text rule (plus optional `source_id`) stated up front and **frozen**
(`locked_at`) the moment the first forecast lands. After that the question can't
be quietly redefined, so later scoring stays trustworthy.

## API

```python
create_target(question, support, time_scope, resolution) -> target_id
get_target(target_id) / list_targets()

submit_forecast(target_id, distribution, *, kind, source_id="self", as_of=None) -> forecast_id
get_forecast(forecast_id) / list_forecasts(target_id, *, source_id=None)
delete_forecast(forecast_id)

record_outcome(target_id, observed_value, observed_at)
get_outcome(target_id) / delete_outcome(target_id)
```

`support`, `time_scope`, and `resolution` accept either the Pydantic models or
plain dicts. One forecast per `(target_id, source_id, as_of)` — a correction is an
explicit delete-then-write, never a silent duplicate. An outcome row with
`observed_value = NULL` means "settled but unscoreable"; no row at all means
"pending."

## What's built vs deferred

| Built today | Deferred (schema-ready, raises `NotImplementedError`) |
|---|---|
| `continuous`, `bounded`, `nominal`, `ordinal` support | `binary`, `count`, `datetime`, `multivariate` |
| `samples` and `pmf` kinds | — |
| target / forecast / outcome storage + write-path validation | — |

Three things are deliberately out of this repo, each in a different relationship
to it:

- **Generation** of forecast values lives *upstream*, in your producer code — the
  database never invents a number, only validates and stores what you hand it.
- **Scoring** (CRPS / Brier / calibration) is a layer *on top* — it reads stored
  targets, forecasts, and outcomes and grades them; none of that needs to live in
  the storage atom.
- **Revision / vintage history** — the trail of how a metric's *measured* value
  gets re-estimated over time (e.g. a statistic's first release vs. its later
  revised releases) — is an *adjacent* concern. This repo records the single
  value that settled a target, not the history of how that value was revised.

## Stack

Python 3.11+ · PostgreSQL (JSONB) · SQLAlchemy 2.0 + psycopg 3 · Alembic ·
Pydantic 2 · pytest. No NumPy / SciPy — the database does no distribution math.

## Database

Postgres-only, no SQLite fallback (the storage contract leans on JSONB and
`timestamptz`). Create a database, run `alembic upgrade head`, and point the
package at it with `FA_DATABASE_URL`. It defaults to
`postgresql+psycopg://localhost/forecast_anything_v2`.

```bash
createdb forecast_anything_v2
export FA_DATABASE_URL="postgresql+psycopg://localhost/forecast_anything_v2"
alembic upgrade head
pytest          # the API smoke test skips itself if no database is reachable
```

## Design notes

The decision log in [`DECISIONS.md`](./DECISIONS.md) records *why* the schema is
shaped the way it is — the two particle kinds, the uniqueness constraints, the
deletions, and what was deferred. [`SPEC_V2.MD`](./SPEC_V2.MD) is the
forward-looking design the repo is growing toward (broader than what's built
today).
