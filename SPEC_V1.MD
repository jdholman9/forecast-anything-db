# Forecast Anything — Specification

*Status: requirements complete (Elon Rule 1 — "make the requirements less dumb"). This document is the public contract the project is built against. Rules 2 (delete) and 3 (simplify) operate on what is written here.*

-----

## 1. What this is

Forecast Anything is one place to write down what you think will happen — or what you estimate is true — about any question, and to check yourself against reality later.

A forecast and an estimate are the same object: an answer to a question, attached to a moment in time. If that moment is in the future, it is a forecast. If it is now or in the past, it is an estimate. They live together, not in separate systems.

You record your answer in whatever form you actually have it — a single number, a range, odds across categories, a named distribution, or a bag of simulation draws — and the question can be about a number, a category, a date, or several of those at once.

You are only ever required to provide two things: **the question**, and **how it will be settled**. Everything else has a sensible default. A beginner stops at those two. An expert reaches for the rest.

-----

## 2. The core idea

There is **one atom**: a probability distribution over a typed outcome space, attached to a question and a point in time.

Everything the product stores is a point in a two-axis space. The axes — not "categorical vs numeric" — are the real structure:

- **Support** — what can the truth be? (binary, nominal, ordinal, count, continuous, bounded, datetime, multivariate)
- **Representation** — how is the distribution encoded? (point, interval, quantiles, parametric, samples, pmf)

Two consequences fall out of this and drive the whole schema:

**Forecast vs estimate is not a type — it is the sign of `as_of − target_time`.** A forecast is an answer whose `as_of` precedes the target period (predicting the future). An estimate is an answer whose `as_of` is at or after the target period (measuring something already realized, imperfectly — hence margins of error). A revision is just a later `as_of` for the same past target. This means one fact table, keyed on `(target, source, as_of)`, and forecast *updates* come for free (same target + source, many `as_of` rows).

**Truth can itself be an atom.** Some questions resolve to something genuinely observed (an election result, a published unemployment number). Others target a latent quantity never directly observed, only ever re-estimated — true median household income is the clean example. For those, "truth" is a later, more authoritative *estimate*. So resolution points at **either** an observed value **or** a designated authoritative atom.

-----

## 3. Glossary

- **Target** — the question. Carries the support, the time period, the resolution rule, optional scenario conditions, optional geography. This is where rigor lives or dies.
- **Atom** — one answer to a target, from one source, as of one moment. The fact table.
- **Source** — who produced the answer (a person, a model, an agency, a market).
- **Representation** — the encoding of the distribution inside an atom.
- **Support** — the outcome space of a target: the set of things the truth could turn out to be.
- **Resolution** — the rule that settles a target, fixed before any forecast and frozen thereafter.
- **Condition** — optional scenario assumptions under which a target's question is being answered.

-----

## 4. The two axes

### Support — what the truth can be

|`type`        |Truth looks like               |Example                           |Scoring family (deferred)    |
|--------------|-------------------------------|----------------------------------|-----------------------------|
|`binary`      |yes / no                       |"Will it rain tomorrow?"          |Brier                        |
|`nominal`     |one of N unordered categories  |"Which party wins?"               |Brier (multiclass)           |
|`ordinal`     |one of N **ordered** categories|"low / medium / high severity"    |RPS (uses the order)         |
|`count`       |non-negative integer           |"How many hurricanes this season?"|CRPS                         |
|`continuous`  |a real number                  |"Unemployment rate"               |CRPS                         |
|`bounded`     |a real number in `[lo, hi]`    |"Vote share, 0–100%"              |CRPS                         |
|`datetime`    |a point in time                |"When will the project ship?"     |CRPS (over time)             |
|`multivariate`|a vector of the above          |"GDP **and** unemployment jointly"|Energy / Variogram (deferred)|

Nominal and ordinal are deliberately distinct. Ordinal carries an order, which unlocks ranked scoring (RPS); flattening it to nominal throws that away.

### Representation — how the answer is encoded

|`representation`|Payload (sketch)                                        |Notes                                                                 |
|----------------|--------------------------------------------------------|----------------------------------------------------------------------|
|`point`         |`{ value }`                                             |A degenerate distribution. "Single number" is **not** a separate kind.|
|`interval`      |`{ lower, upper, level }` or `{ point, moe, moe_level }`|The Census `estimate ± MOE` case. Store the MOE as given.             |
|`quantiles`     |`[{ p, value }, …]`                                     |e.g. 10/50/90. Common for market-implied and model output.            |
|`parametric`    |`{ family, params }`                                    |e.g. `{ "normal", { mu, sigma } }`. The "specified distribution" case.|
|`samples`       |`{ draws: number[] }` (or `number[][]` for multivariate)|MCMC / ensemble. The "empirical distribution" case.                   |
|`pmf`           |`[{ label, weight }, …]`                                |Category odds. Weights stored **raw** (need not sum to 1).            |

### The original five cases, dissolved

|Original requirement                  |Becomes                                          |
|--------------------------------------|-------------------------------------------------|
|categorical → probability per category|`support: nominal`, `representation: pmf`        |
|a single number                       |`representation: point` (degenerate distribution)|
|a specified distribution              |`representation: parametric`                     |
|an empirical distribution             |`representation: samples`                        |
|census estimate ± margin of error     |`support: continuous`, `representation: interval`|

The categorical/numeric split and the forecast/estimate table split were themselves the dumb requirements. Both are deleted.

-----

## 5. Schema

Pseudotypes below (TypeScript-flavored for readability). Physical target is **Postgres**: JSONB for `payload`, native numeric arrays for samples/quantiles, strong TS tooling, identical from laptop to hosted box.

```ts
// THE QUESTION — rigor lives here
target {
  target_id
  description           // REQUIRED — unambiguous question text
  support: {
    type: "binary" | "nominal" | "ordinal" | "count"
        | "continuous" | "bounded" | "datetime" | "multivariate"
    categories?: string[]        // nominal / ordinal (order matters for ordinal)
    bounds?: [number, number]    // bounded / count
    units?: string               // continuous / count — CRPS is scale-dependent
    transform?: "level" | "log"  // the scale on which distances are measured
    dims?: Support[]             // multivariate: a vector of sub-supports
  }
  period_start          // covered period start  (= period_end for an instant)
  period_end            // covered period end
  resolution: ResolutionRule    // REQUIRED — see §7. Frozen on first forecast.
  condition: Assumption[]       // default [] (unconditional) — see §9
  geography?: Geography         // optional — see §10
  created_at
}

// THE FACT — one answer, one source, one moment
atom {
  atom_id
  target_id
  source_id
  as_of                 // the moment this answer is "as of"
                        //   as_of < period  → forecast
                        //   as_of ≥ period  → estimate / revision
  representation: "point" | "interval" | "quantiles"
                | "parametric" | "samples" | "pmf"   // default "point"
  payload               // shape depends on representation; stored RAW / native
  ingested_at
}

// THE REALIZED TRUTH — once known
resolution_outcome {
  target_id
  observed_value?           // for hard-observable targets
  authoritative_atom_id?    // for latent targets: truth is a designated atom
  observed_at
  settled: boolean
}
```

### Required vs defaulted

|Field                        |Required?|Default                               |
|-----------------------------|---------|--------------------------------------|
|`description`                |**yes**  |—                                     |
|`resolution`                 |**yes**  |— (but offered via presets, see §7)   |
|`support.type`               |no       |the simple cases (binary / continuous)|
|`representation`             |no       |`point`                               |
|`period_start` / `period_end`|no       |a single instant (start = end)        |
|`condition`                  |no       |`[]` (unconditional)                  |
|`geography`                  |no       |absent                                |

Only two fields are ever mandatory. This is the entire accessibility strategy: rigor available, never mandatory.

### Deferred tables (do not build yet — see §13)

- **`source`** — promote when you want to attribute, filter, or score by producer.
- **`places`** — a geography hierarchy with parent links; promote the day you roll county → state or join to boundaries for mapping.
- **`samples`** — long-format draws as their own rows; promote only for very large ensembles.

-----

## 6. Design principles

**Store raw, canonicalize on read.** Persist exactly what the source provided; convert only when math demands it. The Census reports a 90% margin of error — store the MOE, not a derived σ. (When you need a Normal, lower it on read: σ = MOE / 1.645.) Categorical weights that do not sum to 1 are stored as given; normalization happens on read, and a future UI warns rather than silently rewrites. Writing canonicalized is lossy and irreversible.

**Degenerate defaults.** Every general field collapses to its easy case with zero thought. A point forecast is a degenerate distribution. An unconditional forecast is an empty condition list. An instant is a period whose start equals its end. The plain case is always the simple case of the general one — so beginners never see the machinery and experts never hit a wall.

**Namespace, don't choose.** Where many encodings are valid (geography codes, distribution families), the schema records a `scheme`/`type` tag plus the raw value rather than committing to one. This is what keeps "anything" honest instead of "anything I enumerated."

**The schema is the public contract.** This is an open project; the schema is the most expensive thing to change once people depend on it. That is why effort concentrates here and almost nowhere else, and why the schema stays strictly domain-agnostic — no baked-in assumption that this is about economics or elections.

**Samples are the universal donor.** Every representation must be able to produce samples, and where it is exact, expose a CDF / quantile function. This single invariant is what keeps scoring open for any support × representation combination ever added (see §12).

-----

## 7. Resolution & integrity

The resolution rule must be stated clearly and unambiguously **before any forecast is submitted**, independent of which estimates are later stored.

The rule decomposes into **two orthogonal knobs**, not one enumerated list:

1. **Which publication counts** — `first-release` | `first-revision` | `nth-revision` | `final` | `value-as-of-date`.
1. **How its uncertainty is treated** — `point` (take the value, ignore the MOE) | `full` (keep the published distribution).

"First release, point" and "first revision, full distribution" are both valid combinations.

```ts
ResolutionRule {
  publication: "first-release" | "first-revision" | "nth-revision"
             | "final" | "value-as-of"
  nth?: number              // for nth-revision
  as_of_date?: date         // for value-as-of
  uncertainty: "point" | "full"
  source_id?                // who publishes the settling value
  authoritative_atom_id?    // latent targets: truth is a designated atom
  resolve_at?: date         // when settlement is expected
  preset?: string           // optional template that filled this rule
  locked_at?: timestamp     // set when the first forecast lands; immutable after
}
```

**The freeze is a hard constraint, not a nicety.** The rule is editable until the first forecast lands and frozen the instant it does. The system refuses to alter it once any atom exists for that target, and records `locked_at`. If the criterion could move after forecasts are visible, no Brier or CRPS number would mean anything.

**Presets are the on-ramp.** The resolution rule is the one mandatory field that cannot be silently defaulted. Beginners pick a template ("resolves to the official value from source X on date Y"); experts write a custom rule. This is the bridge from the rigor phase to the accessible product.

-----

## 8. Time — stock vs flow

Every quantity is either measured at a moment (a stock — the S&P close on June 30) or over a period (a flow — Q3 GDP growth). The target therefore carries **two timestamps**, `period_start` and `period_end`. When the quantity is an instant, the two are equal.

The **covered period is not the reporting moment.** Q3 GDP *covers* July–September but first *publishes* in late October. The two timestamps describe the covered period (Jul 1 – Sep 30). The reporting moment lives in the resolution rule, not in the timestamps. Keeping these separate is exactly why the pieces compose: the timestamps answer "for what span," resolution answers "settled by which publication, and when."

-----

## 9. Scenarios / conditions

Conditions belong on the **target**, not the atom. A conditional question resolves only on the occasions where its condition held, and that treatment must live with the resolution rule — which is target-level. "GDP if the Fed cuts 50bps" is a distinct *question* from "GDP," with its own resolution. A scenario fan across five Fed outcomes is therefore five targets that share structure, not one target with five tagged forecasts. One target, one resolution rule — invariant preserved.

```ts
Assumption =
  | { kind: "target"; target_id; assumed_outcome }  // references a tracked target
  | { kind: "free"; text }                           // an untracked assumption

// target.condition: Assumption[]   — empty array = unconditional
```

A condition that references a tracked target can be checked automatically (the system knows later whether it held); a free-text condition is adjudicated by hand. **Reference a target over free text whenever possible.**

-----

## 10. Geography

Optional, and namespaced rather than committed to one representation — Census wants FIPS/GEOID, an international user wants ISO 3166, an EU user wants NUTS, an arbitrary region wants a polygon, a beginner just types "Stockton."

```ts
Geography {
  scheme: "ISO-3166" | "US-FIPS" | "census-GEOID"
        | "NUTS" | "latlng" | "geojson" | "name"
  value: string     // the code, coordinate pair, geojson, or opaque name
  label?: string    // human-readable
}
```

`name` is the beginner's degenerate case (an opaque label that joins to nothing until someone wants it to); codes are the rigorous case; `geojson`/`latlng` are the escape hatch. Geography sits on the target because it is part of a question's identity — unemployment-for-California and unemployment-for-Texas are two targets, not two forecasts of one. v1 stores it faithfully; PostGIS and spatial joins are a later tooling concern. Promote to a `places` table with parent links the day you actually roll a hierarchy up or join to boundaries for mapping — not before.

-----

## 11. Multivariate

The schema holds multivariate forecasts from **day one**, via a `multivariate` support type carried by `samples`: a sample is just a vector, so dependence and correlation come for free with no copula layer in v1. The parametric Gaussian case (MVN) is also expressible.

Do **not** offer multivariate binned pmf — the cell count explodes. Route all joint distributions through samples.

Tooling stays univariate-first. Multivariate **scoring is ignored until much later**: it needs Energy or Variogram scores, not univariate CRPS/Brier. The honest framing: the schema can store joint forecasts now; the product does not pretend to score them well yet.

-----

## 12. Scoring — out of scope to build, but it constrains the schema

Scoring (Brier, CRPS, RPS, and later Energy/Variogram for joint) is **not built in v1**. But it imposes one invariant that the atom must satisfy now, or "anything" quietly breaks:

> Every representation must be able to produce samples, and where exact, expose a CDF / quantile function.

Samples are the universal donor: Brier by binning, CRPS empirically, Energy Score from sample vectors, and a point forecast's CRPS is just the absolute error. Enforcing "every atom can produce samples" is what keeps every present and future support × representation combination scorable. A conditional forecast, additionally, is only scored on occasions where its condition held (§9).

-----

## 13. Deliberately deferred or deleted

**Deleted (were dumb requirements):**

- The forecast/estimate table split → replaced by the sign of `as_of − target_time`.
- "Single number" as its own concept → it is the `point` representation.
- The categorical/numeric top-level branch → replaced by support × representation.

**Deferred (schema admits, tooling does not yet implement):**

- Multivariate scoring (Energy/Variogram) — §11.
- Spatial joins / PostGIS and the `places` hierarchy — §10.
- Long-format `samples` table for very large ensembles — §5.
- The `source` dimension table — §5.

Guiding rule: the schema admits every support × representation combination; the build implements and validates only the handful the first real sources actually produce. Name the first two or three sources and the day-one build defines itself.

-----

## 14. Where this sits — the engineering process

Framed against the five-step discipline:

1. **Make requirements less dumb** — this document. Done: two top-level type splits deleted; the atom reduced to one shape; resolution integrity made a hard constraint.
1. **Delete parts and process** — §13 is the staging ground; cut anything not earning its place.
1. **Simplify and optimize** — only after deletion, so effort is not spent optimizing things that should not exist.
1. **Accelerate cycle time** — after the above.
1. **Automate** — last.

The remaining open input is the list of first real sources to load (Census, prediction markets, your own models, …). That choice turns this spec into a concrete v1 build.
