"""End-to-end demo: create a target, submit a forecast, record an outcome, read it back.

Needs a live Postgres and the schema applied:

    export FA_DATABASE_URL="postgresql+psycopg://localhost/forecast_anything_v2"
    alembic upgrade head
    python examples/quickstart.py

The database only validates and stores. The five draws below stand in for
whatever your model / error bag / sampled Normal actually produced.
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
        question="US 5+ unit multifamily permits for Mar 2026 (thousands, NSA)?",
        support=Support(type=SupportType.continuous, units="thousands of permits"),
        time_scope=TimeScope(
            kind=TimeScopeKind.interval,
            start=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end=datetime(2026, 4, 1, tzinfo=timezone.utc),
        ),
        resolution={"description": "Census BPS 5+ unit permits, NSA, thousands."},
    )
    print(f"created target {target_id}")

    draws = [118.0, 121.5, 119.2, 125.0, 117.8]
    forecast_id = submit_forecast(
        target_id,
        [{"value": v} for v in draws],
        kind=ForecastKind.samples,
    )
    mean = sum(draws) / len(draws)
    print(f"submitted forecast {forecast_id}: {len(draws)} particles, mean {mean:.1f}")

    record_outcome(target_id, 122.4, observed_at=datetime.now(timezone.utc))
    print("recorded outcome 122.4")

    # Read it back the way a scoring layer on top would.
    forecasts = list_forecasts(target_id)
    outcome = get_outcome(target_id)
    print(
        f"round-trip: target {target_id} has {len(forecasts)} forecast(s); "
        f"outcome = {outcome.observed_value}"
    )


if __name__ == "__main__":
    main()
