"""Categorical demo: a pmf forecast over a fixed category set.

Needs a live Postgres and the schema applied:

    export FA_DATABASE_URL="postgresql+psycopg://localhost/forecast_anything_v2"
    alembic upgrade head
    python examples/categorical.py

Same database, different shape: a `nominal` support pins the answer to a fixed
set of labels, and a `pmf` forecast puts explicit mass on each one. The weights
must be positive and sum to ~1; values outside the category set are rejected.
"""

from datetime import datetime, timezone

from forecast_anything_db import (
    ForecastKind,
    Support,
    SupportType,
    TimeScope,
    TimeScopeKind,
    create_target,
    get_outcome,
    list_forecasts,
    record_outcome,
    submit_forecast,
)


def main() -> None:
    target_id = create_target(
        question="Which party wins the 2026 House race in district X?",
        support=Support(type=SupportType.nominal, categories=["D", "R", "other"]),
        time_scope=TimeScope(
            kind=TimeScopeKind.instant,
            start=datetime(2026, 11, 3, tzinfo=timezone.utc),
        ),
        resolution={"description": "Settles on the certified result."},
    )
    print(f"created target {target_id}")

    pmf = [
        {"value": "D", "weight": 0.6},
        {"value": "R", "weight": 0.35},
        {"value": "other", "weight": 0.05},
    ]
    forecast_id = submit_forecast(target_id, pmf, kind=ForecastKind.pmf)
    print(f"submitted pmf forecast {forecast_id}: {len(pmf)} categories")

    record_outcome(target_id, "D", observed_at=datetime.now(timezone.utc))
    print("recorded outcome D")

    forecasts = list_forecasts(target_id)
    outcome = get_outcome(target_id)
    print(
        f"round-trip: target {target_id} has {len(forecasts)} forecast(s); "
        f"outcome = {outcome.observed_value!r}"
    )


if __name__ == "__main__":
    main()
