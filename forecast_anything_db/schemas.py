"""Pydantic write-path contract: Support, TimeScope, ResolutionRule, kinds.

Pure validation, no database. The Support enum *admits* all eight value spaces
(forward-looking schema), but value-level validation for non-`continuous`
supports is deferred (see support.py).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class SupportType(str, Enum):
    binary = "binary"
    nominal = "nominal"
    ordinal = "ordinal"
    count = "count"
    continuous = "continuous"
    bounded = "bounded"
    datetime = "datetime"
    multivariate = "multivariate"


class Support(BaseModel):
    """The forecast value space for a target (not necessarily the physical
    outcome set; a continuous forecast may settle against an integer outcome)."""

    model_config = ConfigDict(extra="forbid")

    type: SupportType
    categories: list[str] | None = None
    bounds: tuple[float, float] | None = None
    units: str | None = None
    dims: list["Support"] | None = None

    @model_validator(mode="after")
    def _check_shape(self) -> "Support":
        t = self.type
        if t in (SupportType.nominal, SupportType.ordinal) and not self.categories:
            raise ValueError(f"{t.value} support requires non-empty categories")
        if t == SupportType.bounded:
            if self.bounds is None:
                raise ValueError("bounded support requires bounds (lo, hi)")
            lo, hi = self.bounds
            if not lo < hi:
                raise ValueError("bounded support requires lo < hi")
        if t == SupportType.multivariate and not self.dims:
            raise ValueError("multivariate support requires dims")
        return self


class TimeScopeKind(str, Enum):
    instant = "instant"
    interval = "interval"
    datetime_answer = "datetime_answer"


def _require_aware_utc(dt: datetime | None, field: str) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"{field} must be timezone-aware UTC; got a naive datetime")
    return dt.astimezone(timezone.utc)


class TimeScope(BaseModel):
    """What time the target's answer refers to."""

    model_config = ConfigDict(extra="forbid")

    kind: TimeScopeKind
    start: datetime | None = None
    end: datetime | None = None

    @model_validator(mode="after")
    def _check_kind(self) -> "TimeScope":
        self.start = _require_aware_utc(self.start, "start")
        self.end = _require_aware_utc(self.end, "end")
        k = self.kind
        if k == TimeScopeKind.instant:
            if self.start is None:
                raise ValueError("instant time scope requires start")
            if self.end is not None:
                raise ValueError("instant time scope must not set end")
        elif k == TimeScopeKind.interval:
            if self.start is None or self.end is None:
                raise ValueError("interval time scope requires start and end")
            if not self.start < self.end:
                raise ValueError("interval time scope requires end after start")
        elif k == TimeScopeKind.datetime_answer:
            if self.start is not None or self.end is not None:
                raise ValueError("datetime_answer time scope must not set start/end")
        return self


class ResolutionRule(BaseModel):
    """How the target settles. Frozen (`locked_at`) when the first forecast lands."""

    model_config = ConfigDict(extra="forbid")

    description: str
    source_id: str | None = None
    locked_at: datetime | None = None

    @field_validator("description")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("resolution description is required")
        return v


class ForecastKind(str, Enum):
    samples = "samples"
    pmf = "pmf"
