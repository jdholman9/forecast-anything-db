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


def test_bounded_accepts_within_inclusive_range():
    s = Support(type=SupportType.bounded, bounds=(0.0, 1.0))
    validate_value(s, 0.0)  # lo endpoint is valid
    validate_value(s, 1.0)  # hi endpoint is valid
    validate_value(s, 0.42)


def test_bounded_rejects_out_of_range():
    s = Support(type=SupportType.bounded, bounds=(0.0, 1.0))
    with pytest.raises(ValueError):
        validate_value(s, -0.01)
    with pytest.raises(ValueError):
        validate_value(s, 1.5)


def test_bounded_rejects_bool_and_non_numbers():
    s = Support(type=SupportType.bounded, bounds=(0.0, 1.0))
    with pytest.raises(ValueError):
        validate_value(s, True)
    with pytest.raises(ValueError):
        validate_value(s, "0.5")


@pytest.mark.parametrize(
    "stype",
    [
        SupportType.binary,
        SupportType.count,
        SupportType.datetime,
    ],
)
def test_unimplemented_supports_raise(stype):
    s = Support(type=stype)
    with pytest.raises(NotImplementedError):
        validate_value(s, 1)
