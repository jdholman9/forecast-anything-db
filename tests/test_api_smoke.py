"""Round-trip smoke test. Skipped unless a Postgres is actually reachable
(needs psycopg + FA_DATABASE_URL pointing at a live database)."""

from datetime import datetime, timezone

import pytest

pytest.importorskip("psycopg")

from sqlalchemy import text  # noqa: E402

from forecast_anything_db import api, db  # noqa: E402
from forecast_anything_db.models import Base  # noqa: E402
from forecast_anything_db.schemas import (  # noqa: E402
    ForecastKind,
    Support,
    SupportType,
    TimeScope,
    TimeScopeKind,
)

try:
    with db.get_engine().connect() as conn:
        conn.execute(text("select 1"))
except Exception as exc:  # noqa: BLE001
    pytest.skip(f"no reachable Postgres: {exc}", allow_module_level=True)

UTC = timezone.utc


@pytest.fixture(autouse=True)
def _create_schema():
    Base.metadata.create_all(db.get_engine())
    yield
    # Clean up only this test's rows so it never pollutes a working database.
    with db.get_engine().begin() as conn:
        conn.execute(
            text(
                "delete from forecast where target_id in "
                "(select target_id from target where question like 'smoke:%')"
            )
        )
        conn.execute(
            text(
                "delete from outcome where target_id in "
                "(select target_id from target where question like 'smoke:%')"
            )
        )
        conn.execute(text("delete from target where question like 'smoke:%'"))


def test_forecast_particle_roundtrip():
    target_id = api.create_target(
        "smoke: MF permits Q3 2026 (thousands, NSA)?",
        Support(type=SupportType.continuous, units="thousands"),
        TimeScope(
            kind=TimeScopeKind.interval,
            start=datetime(2026, 7, 1, tzinfo=UTC),
            end=datetime(2026, 10, 1, tzinfo=UTC),
        ),
        {"description": "settles on Census MPS print", "source_id": "census_mps"},
    )

    bag = [{"value": 45.9}, {"value": 46.1}, {"value": 46.8}]
    forecast_id = api.submit_forecast(
        target_id, bag, kind=ForecastKind.samples, source_id="HoltWinters"
    )

    got = api.get_forecast(forecast_id)
    assert got.distribution == bag  # particles come back out intact

    target = api.get_target(target_id)
    assert target.resolution["locked_at"] is not None  # froze on first forecast


def test_pmf_kind_rejected_for_continuous():
    target_id = api.create_target(
        "smoke: pmf rejection",
        Support(type=SupportType.continuous),
        TimeScope(kind=TimeScopeKind.instant, start=datetime(2026, 12, 31, tzinfo=UTC)),
        {"description": "x"},
    )
    with pytest.raises(ValueError):
        api.submit_forecast(
            target_id, [{"value": 1, "weight": 1.0}], kind=ForecastKind.pmf
        )


def test_categorical_pmf_roundtrip():
    target_id = api.create_target(
        "smoke: which party wins?",
        Support(type=SupportType.nominal, categories=["D", "R", "other"]),
        TimeScope(kind=TimeScopeKind.instant, start=datetime(2026, 11, 3, tzinfo=UTC)),
        {"description": "settles on the certified result"},
    )
    pmf = [
        {"value": "D", "weight": 0.6},
        {"value": "R", "weight": 0.35},
        {"value": "other", "weight": 0.05},
    ]
    forecast_id = api.submit_forecast(target_id, pmf, kind=ForecastKind.pmf)
    assert api.get_forecast(forecast_id).distribution == pmf


def test_record_outcome_twice_raises_clean_error():
    target_id = api.create_target(
        "smoke: outcome uniqueness",
        Support(type=SupportType.continuous),
        TimeScope(kind=TimeScopeKind.instant, start=datetime(2026, 12, 31, tzinfo=UTC)),
        {"description": "x"},
    )
    api.record_outcome(target_id, 1.0, observed_at=datetime.now(UTC))
    # Second write must surface the clean domain error, not a raw IntegrityError.
    with pytest.raises(ValueError, match="already has an outcome"):
        api.record_outcome(target_id, 2.0, observed_at=datetime.now(UTC))


def test_duplicate_forecast_raises_clean_error():
    target_id = api.create_target(
        "smoke: forecast uniqueness",
        Support(type=SupportType.continuous),
        TimeScope(kind=TimeScopeKind.instant, start=datetime(2026, 12, 31, tzinfo=UTC)),
        {"description": "x"},
    )
    as_of = datetime(2026, 6, 1, tzinfo=UTC)
    api.submit_forecast(target_id, [{"value": 1.0}], kind=ForecastKind.samples, as_of=as_of)
    with pytest.raises(ValueError, match="already exists"):
        api.submit_forecast(
            target_id, [{"value": 2.0}], kind=ForecastKind.samples, as_of=as_of
        )
