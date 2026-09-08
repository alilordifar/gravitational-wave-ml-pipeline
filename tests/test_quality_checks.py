import numpy as np

from src.transformation.quality_checks import check_window_quality


def test_valid_window():
    samples = np.random.default_rng(0).normal(size=8192)
    result = check_window_quality(samples)
    assert result["is_valid"] is True
    assert not result["has_nan"]
    assert not result["has_inf"]
    assert not result["is_flatline"]
    assert not result["all_zero"]


def test_flags_nan():
    samples = np.zeros(100)
    samples[5] = np.nan
    result = check_window_quality(samples)
    assert result["has_nan"] is True
    assert result["is_valid"] is False


def test_flags_inf():
    samples = np.ones(100)
    samples[0] = np.inf
    result = check_window_quality(samples)
    assert result["has_inf"] is True
    assert result["is_valid"] is False


def test_flags_flatline():
    samples = np.full(100, 3.0)
    result = check_window_quality(samples)
    assert result["is_flatline"] is True
    assert result["is_valid"] is False


def test_flags_all_zero():
    samples = np.zeros(100)
    result = check_window_quality(samples)
    assert result["all_zero"] is True
    assert result["is_flatline"] is True
    assert result["is_valid"] is False
