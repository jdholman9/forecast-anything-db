"""Build-time constants and database URL resolution."""

from __future__ import annotations

import os

DEFAULT_SOURCE_ID = "self"
MAX_INLINE_PARTICLE_GUIDELINE = 10_000  # perf warning, not a hard reject
PMF_WEIGHT_TOLERANCE = 0.01

_DEFAULT_DB_URL = "postgresql+psycopg://localhost/forecast_anything_v2"


def database_url() -> str:
    """Postgres URL. No SQLite fallback by design (JSONB + tz semantics)."""
    return os.environ.get("FA_DATABASE_URL", _DEFAULT_DB_URL)
