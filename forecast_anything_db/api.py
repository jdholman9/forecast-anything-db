"""Public write/read API. Validation happens here against the target's support;
persistence is JSONB. Requires a live Postgres at call time."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from . import particles
from .config import DEFAULT_SOURCE_ID
from .db import session
from .models import Forecast, Outcome, Target
from .schemas import ForecastKind, ResolutionRule, Support, TimeScope


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce(model_cls, value):
    return value if isinstance(value, model_cls) else model_cls.model_validate(value)


# --- targets ---------------------------------------------------------------

def create_target(question: str, support, time_scope, resolution) -> int:
    if not question or not question.strip():
        raise ValueError("question is required")
    s = _coerce(Support, support)
    ts = _coerce(TimeScope, time_scope)
    rr = _coerce(ResolutionRule, resolution)
    with session() as db:
        target = Target(
            question=question.strip(),
            support=s.model_dump(mode="json"),
            time_scope=ts.model_dump(mode="json"),
            resolution=rr.model_dump(mode="json"),
        )
        db.add(target)
        db.commit()
        db.refresh(target)
        return target.target_id


def get_target(target_id: int) -> Target | None:
    with session() as db:
        return db.get(Target, target_id)


def list_targets() -> list[Target]:
    with session() as db:
        return list(db.scalars(select(Target).order_by(Target.target_id)))


# --- forecasts -------------------------------------------------------------

def submit_forecast(
    target_id: int,
    distribution: list[dict],
    *,
    kind: str | ForecastKind,
    source_id: str = DEFAULT_SOURCE_ID,
    as_of: datetime | None = None,
) -> int:
    k = ForecastKind(kind)
    if as_of is not None and (as_of.tzinfo is None or as_of.tzinfo.utcoffset(as_of) is None):
        raise ValueError("as_of must be timezone-aware UTC")
    with session() as db:
        target = db.get(Target, target_id)
        if target is None:
            raise ValueError(f"no target with id {target_id}")
        support = Support.model_validate(target.support)
        particles.validate_distribution(support, k, distribution)

        # Freeze the resolution rule on the first forecast.
        resolution = dict(target.resolution)
        if resolution.get("locked_at") is None:
            resolution["locked_at"] = _utcnow().isoformat()
            target.resolution = resolution

        forecast = Forecast(
            target_id=target_id,
            source_id=source_id,
            as_of=as_of or _utcnow(),
            kind=k.value,
            distribution=distribution,
        )
        db.add(forecast)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(
                f"a forecast for target {target_id} from source {source_id!r} at that "
                "as_of already exists; delete it first to replace"
            ) from exc
        db.refresh(forecast)
        return forecast.forecast_id


def get_forecast(forecast_id: int) -> Forecast | None:
    with session() as db:
        return db.get(Forecast, forecast_id)


def list_forecasts(target_id: int, *, source_id: str | None = None) -> list[Forecast]:
    stmt = select(Forecast).where(Forecast.target_id == target_id)
    if source_id is not None:
        stmt = stmt.where(Forecast.source_id == source_id)
    stmt = stmt.order_by(Forecast.as_of, Forecast.forecast_id)
    with session() as db:
        return list(db.scalars(stmt))


def delete_forecast(forecast_id: int) -> None:
    with session() as db:
        obj = db.get(Forecast, forecast_id)
        if obj is not None:
            db.delete(obj)
            db.commit()


# --- outcomes --------------------------------------------------------------

def record_outcome(
    target_id: int, observed_value, observed_at: datetime
) -> None:
    if observed_at.tzinfo is None or observed_at.tzinfo.utcoffset(observed_at) is None:
        raise ValueError("observed_at must be timezone-aware UTC")
    with session() as db:
        target = db.get(Target, target_id)
        if target is None:
            raise ValueError(f"no target with id {target_id}")
        db.add(
            Outcome(
                target_id=target_id,
                observed_value=observed_value,
                observed_at=observed_at,
            )
        )
        # One outcome per target: rely on the PK constraint, not a racy pre-check.
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(f"target {target_id} already has an outcome") from exc


def get_outcome(target_id: int) -> Outcome | None:
    with session() as db:
        return db.get(Outcome, target_id)


def delete_outcome(target_id: int) -> None:
    with session() as db:
        obj = db.get(Outcome, target_id)
        if obj is not None:
            db.delete(obj)
            db.commit()
