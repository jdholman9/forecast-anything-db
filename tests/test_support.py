import pytest

from forecast_anything_db.schemas import Support, SupportType
from forecast_anything_db.support import validate_value


def test_continuous_accepts_real_numbers():
    s = Support(type=SupportType.continuous)
    validate_value(s, 50.25)
    validate_value(s, 0)
    validate_value(s, -3)


def test_continuous_rejects_bool_and_non_numbers():
    s = Support(type=SupportType.continuous)
    with pytest.raises(ValueError):
        validate_value(s, True)
    with pytest.raises(ValueError):
        validate_value(s, "50")
    with pytest.raises(ValueError):
        validate_value(s, None)


@pytest.mark.parametrize(
    "stype",
    [
        SupportType.binary,
        SupportType.count,
        SupportType.bounded,
        SupportType.datetime,
    ],
)
def test_unimplemented_supports_raise(stype):
    kwargs = {"type": stype}
    if stype == SupportType.bounded:
        kwargs["bounds"] = (0.0, 1.0)
    s = Support(**kwargs)
    with pytest.raises(NotImplementedError):
        validate_value(s, 1)
