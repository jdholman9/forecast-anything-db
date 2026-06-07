from datetime import datetime, timezone

import pytest

from forecast_anything_db.schemas import (
    ResolutionRule,
    Support,
    SupportType,
    TimeScope,
    TimeScopeKind,
)

UTC = timezone.utc


def test_nominal_support_requires_categories():
    with pytest.raises(ValueError):
        Support(type=SupportType.nominal)
    Support(type=SupportType.nominal, categories=["a", "b"])


def test_bounded_support_requires_ordered_bounds():
    with pytest.raises(ValueError):
        Support(type=SupportType.bounded, bounds=(1.0, 1.0))
    Support(type=SupportType.bounded, bounds=(0.0, 100.0))


def test_instant_scope_requires_start_and_no_end():
    TimeScope(kind=TimeScopeKind.instant, start=datetime(2026, 12, 31, tzinfo=UTC))
    with pytest.raises(ValueError):
        TimeScope(kind=TimeScopeKind.instant)
    with pytest.raises(ValueError):
        TimeScope(
            kind=TimeScopeKind.instant,
            start=datetime(2026, 12, 31, tzinfo=UTC),
            end=datetime(2027, 1, 1, tzinfo=UTC),
        )


def test_interval_scope_requires_end_after_start():
    TimeScope(
        kind=TimeScopeKind.interval,
        start=datetime(2026, 7, 1, tzinfo=UTC),
        end=datetime(2026, 10, 1, tzinfo=UTC),
    )
    with pytest.raises(ValueError):
        TimeScope(
            kind=TimeScopeKind.interval,
            start=datetime(2026, 10, 1, tzinfo=UTC),
            end=datetime(2026, 7, 1, tzinfo=UTC),
        )


def test_datetime_answer_scope_rejects_start_end():
    TimeScope(kind=TimeScopeKind.datetime_answer)
    with pytest.raises(ValueError):
        TimeScope(kind=TimeScopeKind.datetime_answer, start=datetime(2026, 7, 1, tzinfo=UTC))


def test_naive_datetime_rejected():
    with pytest.raises(ValueError):
        TimeScope(kind=TimeScopeKind.instant, start=datetime(2026, 12, 31))


def test_resolution_requires_description():
    with pytest.raises(ValueError):
        ResolutionRule(description="   ")
    rr = ResolutionRule(description="settles on Census MPS print")
    assert rr.locked_at is None
