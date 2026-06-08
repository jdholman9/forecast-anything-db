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


def test_nominal_accepts_category_and_rejects_others():
    s = Support(type=SupportType.nominal, categories=["D", "R", "other"])
    validate_value(s, "D")
    with pytest.raises(ValueError):
        validate_value(s, "Green")  # not a declared category
    with pytest.raises(ValueError):
        validate_value(s, 1)  # not a label


def test_ordinal_validates_like_nominal():
    s = Support(type=SupportType.ordinal, categories=["low", "med", "high"])
    validate_value(s, "high")
    with pytest.raises(ValueError):
        validate_value(s, "extreme")


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
