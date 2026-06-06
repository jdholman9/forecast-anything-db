# forecast_anything (v2)

A small, atomic-layer database for recording probabilistic forecasts of any question and the outcome that eventually settles it.

> **Status - pre-v1.** Specification lives in [`SPEC_V2.MD`](./SPEC_V2.MD); design decisions are tracked in [`QUESTIONS.md`](./QUESTIONS.md). Code has not been written yet. Nothing on PyPI.

---

## What it is

Three ideas sit at the core:

1. **Targets** - questions, plus forecast support, time scope, and resolution rules.
2. **Forecasts** - one dated distribution for a target, stored as particles.
3. **Outcomes** - the one settling value for a target.

Forecasts are not estimates, vintages, or revised official data. Those are a future sibling project. V1 stores forecasts and one settling outcome; that is enough to make the atom complete.

To define a target, you supply exactly the non-negotiables:

- The **question**.
- The **support**: what kind of forecast value is valid.
- The **time scope**: point-in-time, interval/window, or datetime answer.
- The **resolution rule**: how the question will be settled, frozen once the first forecast lands.

Everything else has a default.

## Particles

Every forecast distribution is stored as particles. The particle shape depends on the forecast's `kind`:

| Kind | Particle | Used for |
|---|---|---|
| `samples` | `{value}` with uniform implied weight `1/N` | point estimates, sampled parametrics, Monte Carlo, MCMC |
| `pmf` | `{value, weight}` with weights summing to about 1 | categorical odds, market-implied probabilities |

`N` is natural to the data: a point is N=1, a 3-category PMF is N=3, and a sampled `Normal(mu, sigma)` ingests as N=2000 by default.

Quantile input is an ingest format, not a storage format. It must be converted into a sampled distribution before storage; three quantile markers are not three equiprobable samples. Raw quantile ingest requires at least a lower, central, and upper quantile plus a tail policy.

## Supports

Support describes the stored forecast values, not necessarily every physically possible outcome. Count outcomes may still use continuous support when fractional forecast values are meaningful.

| Support | Particle `value` is | Example question |
|---|---|---|
| `binary` | `0` / `1` | "Will it rain tomorrow?" |
| `nominal` | category label | "Which party wins?" |
| `ordinal` | ordered category label | "low / medium / high severity" |
| `count` | non-negative integer | "How many hurricanes this season?" |
| `continuous` | real number | "Unemployment rate" |
| `bounded` | real number in strict `[lo, hi]` | "Vote share, 0-100%" |
| `datetime` | UTC timestamp | "When does the project ship?" |
| `multivariate` | vector | Schema admits it; ingest is deferred. |

## Time Scopes

Every target has one explicit time scope:

| Scope | Used for | Example |
|---|---|---|
| `instant` | stock measured at a point in time | "S&P 500 close on 2026-12-31" |
| `interval` | flow, count, or event window | "Permits issued in Q3" |
| `datetime_answer` | the answer value is itself a date | "When will the project ship?" |

## Architecture

This is **the atomic layer**. It stores targets, forecasts, and outcomes; nothing else.

Built on top later, as separate concerns:

- **Scoring**: Brier, CRPS, log score, RPS. The particle representation guarantees every stored forecast is scorable; the scoring layer is its own thing.
- **Entry windows and grouping**: batches, horizons, themes. Pure queries over atoms.
- **Estimates and vintages**: first-print Census number vs latest revision. Future sibling project, not in scope here.

See [`SPEC_V2.MD`](./SPEC_V2.MD) for the public contract: schema, design principles, and deliberate cuts.

## Stack

- Python 3.12
- PostgreSQL with JSONB
- SQLAlchemy 2.0 + psycopg
- Alembic
- Pydantic 2 for write-path validation
- NumPy + SciPy for parametric-to-particles sampling
- `scoringrules` / `properscoring` later, when scoring is built

## Docs

| File | Purpose |
|---|---|
| [`SPEC_V2.MD`](./SPEC_V2.MD) | Public contract: schema, principles, what's in/out. |
| [`QUESTIONS.md`](./QUESTIONS.md) | Decision log. |
| [`BUILD_PLAN.md`](./BUILD_PLAN.md) | Implementation defaults and config choices. |
| [`SPEC_V1.MD`](./SPEC_V1.MD) | Historical, superseded by V2. |
