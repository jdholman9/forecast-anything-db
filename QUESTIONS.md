# Forecast Anything V2 - Decision Log

`SPEC_V2.MD` is the source of truth. This file records the decisions that shaped it.

Status: all v1 build-shaping questions below are closed.

---

## Core Shape

### Q1. Language

**Decision:** Python 3.12.

Reason: distribution sampling, validation, and later scoring are Python-native work.

### Q2. Database

**Decision:** PostgreSQL with JSONB. No SQLite fallback.

Reason: the storage contract depends on JSONB and Postgres timestamp behavior. A SQLite compatibility layer would be leaky from day one.

### Q3. First Sources

**Decision:** start with three sources:

1. Census MPS / multifamily permits: `continuous` x `samples`.
2. Polymarket or Manifold: `binary` / `nominal` x `pmf`.
3. Jacob's ad-hoc forecasts: `continuous` x `samples`.

Reason: this covers numeric samples, discrete PMFs, point forecasts, sampled parametrics, target creation, and outcome recording without inventing fake use cases.

### Q4. Source Shape

**Decision:** `forecast.source_id` is a string column, default `"self"`. No source table in v1.

Reason: equality filtering is enough. Promote to FK/table only when source metadata becomes real.

### Q5. Forecast Uniqueness

**Decision:** enforce `UNIQUE (target_id, source_id, as_of)`.

Reason: a corrected forecast at the same semantic time should be explicit delete-then-write, not a silent duplicate.

### Q6. Forecast / Outcome Split

**Decision:** v1 stores `forecast` and `outcome`, not forecasts-and-estimates in one table.

Reason: the estimates/vintage problem is real but not atomic v1. One target gets one settling outcome. First-print vs latest-revision belongs in a sibling vintage-data project.

### Q7. Outcome Cardinality

**Decision:** `outcome` has `UNIQUE (target_id)`.

Reason: v1 resolves a target once. Revisions are out of scope.

### Q8. Outcome Nullability

**Decision:** `outcome.observed_value` is nullable.

Reason: an outcome row with `NULL` means explicitly settled but non-scoreable. No outcome row means pending.

---

## Particles

### Q9. Particle Representation

**Decision:** one forecast table with `kind: "samples" | "pmf"`.

- `samples`: particles are `{value}` with uniform implied weight.
- `pmf`: particles are `{value, weight}` with explicit mass.

Reason: forcing categorical PMFs into uniform samples loses precision; splitting tables makes uniqueness and queries worse.

### Q10. Parametric Sampling N

**Decision:** default N=2000 for parametric ingest, overridable per call.

Reason: good enough Monte Carlo precision without making JSONB rows silly. Target-level N is extra metadata with no current payoff.

### Q11. Quantiles

**Decision:** quantiles are an ingest format, not a storage format. Minimum raw quantile ingest requires at least 3 points covering location, spread, and both tails: one lower quantile `p <= 0.25`, one central quantile `0.4 <= p <= 0.6`, one upper quantile `p >= 0.75`, with monotonic probabilities/values and a declared or default tail policy.

Reason: storing 10/50/90 as three equiprobable samples is mathematically wrong. A single quantile like `p50` or `p15` is only a partial distribution constraint, not a full distribution. Quantile input must be converted into a sampled approximation before storage.

### Q12. Inline vs Long Particle Table

**Decision:** always inline JSONB in v1. Soft cliff around 10k particles.

Reason: no long-table promotion path until a real workflow hits the cliff.

### Q13. PMF Support

**Decision:** allow `pmf` only for `binary`, `nominal`, `ordinal`, and `count`.

Reason: PMF is point mass. It is not a density over continuous, bounded, datetime, or multivariate supports.

---

## Support and Time

### Q14. Support Default

**Decision:** `target.support` is required. No default.

Reason: continuous would be wrong too often.

### Q15. Binary Values

**Decision:** binary particle values are integer `0` / `1`.

Reason: the value is the indicator. UI can render yes/no.

### Q16. Bounded Values

**Decision:** reject values outside `[lo, hi]`.

Reason: `bounded` means mathematical bounds. Loose display ranges are a different future concept, not this field.

### Q17. Timezones

**Decision:** all timestamps are UTC. Reject naive datetimes.

Reason: ambiguous timestamps corrupt `as_of`, backfills, and outcome timing.

### Q18. `as_of` vs `ingested_at`

**Decision:** store both.

Reason: `as_of` is semantic forecast time; `ingested_at` is audit/write time.

---

## Deletions

### D1. `target.geography`

**Decision:** delete.

Reason: none of the first sources need it; geography can live in question text until a source demands structure.

### D2. `target.condition` and `Assumption`

**Decision:** delete.

Reason: no v1 source needs conditional forecasts. Free-form assumptions belong in question text.

### D3. `forecast.provenance`

**Decision:** delete.

Reason: non-load-bearing. Use `source_id` or ingest-script history.

### D4. `ResolutionRule.resolve_at`

**Decision:** delete.

Reason: no scheduler/lifecycle consumer exists in v1.

### D5. `ResolutionRule.preset` and `presets.py`

**Decision:** delete.

Reason: source ingest scripts already own source-specific resolution rules. A separate registry duplicates them.

### D6. `observed_series`

**Decision:** delete.

Reason: forecasts are complete and scorable against `outcome` alone. Vintage history is the future estimates project.

### D7. Score Cache

**Decision:** delete from v1.

Reason: scoring is a later layer and should compute on demand.

### D8. `Support.score_scale`

**Decision:** delete from v1.

Reason: useful later for scoring semantics, but not needed for the atomic storage contract.

---

## Deferred

- Scoring implementation.
- Entry windows and grouping UI.
- Multivariate ingest and scoring.
- Long particle table.
- Geography hierarchy.
- Estimates/vintages sibling project.
