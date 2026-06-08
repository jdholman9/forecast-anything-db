import pytest

from forecast_anything_db import particles
from forecast_anything_db.schemas import ForecastKind, Support, SupportType

CONT = Support(type=SupportType.continuous)
NOMINAL = Support(type=SupportType.nominal, categories=["D", "R", "other"])


def test_point_to_samples_is_n1():
    out = particles.point_to_samples(46.1)
    assert out == [{"value": 46.1}]


def test_samples_to_particles_wraps_bag():
    out = particles.samples_to_particles([1, 2.5, 3])
    assert out == [{"value": 1.0}, {"value": 2.5}, {"value": 3.0}]


def test_samples_to_particles_rejects_empty():
    with pytest.raises(ValueError):
        particles.samples_to_particles([])


def test_validate_distribution_samples_ok():
    dist = particles.samples_to_particles([10.0, 11.0, 12.0])
    particles.validate_distribution(CONT, ForecastKind.samples, dist)


def test_validate_distribution_rejects_weight_key_in_samples():
    bad = [{"value": 1.0, "weight": 0.5}]
    with pytest.raises(ValueError):
        particles.validate_distribution(CONT, ForecastKind.samples, bad)


def test_validate_distribution_rejects_empty():
    with pytest.raises(ValueError):
        particles.validate_distribution(CONT, ForecastKind.samples, [])


def test_categorical_point_as_samples():
    # A categorical point forecast is samples N=1 with a label value.
    particles.validate_distribution(NOMINAL, ForecastKind.samples, [{"value": "D"}])


def test_pmf_valid_over_categories():
    dist = [
        {"value": "D", "weight": 0.6},
        {"value": "R", "weight": 0.35},
        {"value": "other", "weight": 0.05},
    ]
    particles.validate_distribution(NOMINAL, ForecastKind.pmf, dist)


def test_pmf_rejects_weights_not_summing_to_one():
    dist = [{"value": "D", "weight": 0.6}, {"value": "R", "weight": 0.1}]
    with pytest.raises(ValueError):
        particles.validate_distribution(NOMINAL, ForecastKind.pmf, dist)


def test_pmf_rejects_nonpositive_weight():
    dist = [{"value": "D", "weight": 1.0}, {"value": "R", "weight": 0.0}]
    with pytest.raises(ValueError):
        particles.validate_distribution(NOMINAL, ForecastKind.pmf, dist)


def test_pmf_rejects_value_not_in_categories():
    dist = [{"value": "Green", "weight": 1.0}]
    with pytest.raises(ValueError):
        particles.validate_distribution(NOMINAL, ForecastKind.pmf, dist)


def test_pmf_rejected_for_continuous_support():
    dist = [{"value": 1.0, "weight": 1.0}]
    with pytest.raises(ValueError):
        particles.validate_distribution(CONT, ForecastKind.pmf, dist)


def test_pmf_for_binary_is_deferred():
    binary = Support(type=SupportType.binary)
    dist = [{"value": 0, "weight": 0.5}, {"value": 1, "weight": 0.5}]
    with pytest.raises(NotImplementedError):
        particles.validate_distribution(binary, ForecastKind.pmf, dist)
