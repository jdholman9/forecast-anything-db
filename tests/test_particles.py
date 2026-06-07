import pytest

from forecast_anything_db import particles
from forecast_anything_db.schemas import ForecastKind, Support, SupportType

CONT = Support(type=SupportType.continuous)


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


def test_pmf_kind_is_deferred():
    with pytest.raises(NotImplementedError):
        particles.validate_distribution(CONT, ForecastKind.pmf, [{"value": 0, "weight": 1.0}])
