"""SQLAlchemy ORM: target, forecast, outcome. Postgres + JSONB only.

No score table, no source table, no geography/condition/observed_series. Those
are layers above the atom (or future sibling projects), not stored here.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Target(Base):
    __tablename__ = "target"

    target_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    support: Mapped[dict] = mapped_column(JSONB, nullable=False)
    time_scope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    resolution: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    forecasts: Mapped[list["Forecast"]] = relationship(
        back_populates="target", cascade="all, delete-orphan"
    )
    outcome: Mapped["Outcome | None"] = relationship(
        back_populates="target", uselist=False, cascade="all, delete-orphan"
    )


class Forecast(Base):
    __tablename__ = "forecast"
    __table_args__ = (
        UniqueConstraint("target_id", "source_id", "as_of", name="uq_forecast_target_source_asof"),
    )

    forecast_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("target.target_id"), nullable=False)
    source_id: Mapped[str] = mapped_column(Text, nullable=False, default="self")
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    distribution: Mapped[list] = mapped_column(JSONB, nullable=False)

    target: Mapped["Target"] = relationship(back_populates="forecasts")


class Outcome(Base):
    __tablename__ = "outcome"

    target_id: Mapped[int] = mapped_column(
        ForeignKey("target.target_id"), primary_key=True
    )
    # NULL observed_value = settled but unscoreable; no row at all = pending.
    observed_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    target: Mapped["Target"] = relationship(back_populates="outcome")
