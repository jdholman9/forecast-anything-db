"""forecast_anything_db - atomic layer for probabilistic forecasts.

Public surface: targets, forecasts, outcomes. Scoring is a layer above and is
not part of v1. Step 1 implements `continuous` support and the `samples` kind
end-to-end; other supports / the `pmf` kind raise NotImplementedError until a
source needs them.
"""

from .schemas import (
    ForecastKind,
    ResolutionRule,
    Support,
    SupportType,
    TimeScope,
    TimeScopeKind,
)
from .api import (
    create_target,
    delete_forecast,
    delete_outcome,
    get_forecast,
    get_outcome,
    get_target,
    list_forecasts,
    list_targets,
    record_outcome,
    submit_forecast,
)

__all__ = [
    "ForecastKind",
    "ResolutionRule",
    "Support",
    "SupportType",
    "TimeScope",
    "TimeScopeKind",
    "create_target",
    "get_target",
    "list_targets",
    "submit_forecast",
    "get_forecast",
    "list_forecasts",
    "delete_forecast",
    "record_outcome",
    "get_outcome",
    "delete_outcome",
]
