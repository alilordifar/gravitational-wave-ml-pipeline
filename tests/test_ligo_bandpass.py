import numpy as np
import pytest

from src.transformation.processors.ligo_bandpass import apply_bandpass


def test_output_shape_matches_input():
    rng = np.random.default_rng(0)
    samples = rng.normal(size=8192)
    filtered = apply_bandpass(samples, sample_rate_hz=4096)
    assert filtered.shape == samples.shape


def test_attenuates_out_of_band_tone():
    sample_rate_hz = 4096
    t = np.arange(8192) / sample_rate_hz
    low_freq_tone = np.sin(2 * np.pi * 5 * t)      # below 20 Hz band -> attenuated
    in_band_tone = np.sin(2 * np.pi * 200 * t)     # inside 20-2000 Hz -> passes through

    filtered_low = apply_bandpass(low_freq_tone, sample_rate_hz)
    filtered_in_band = apply_bandpass(in_band_tone, sample_rate_hz)

    assert np.std(filtered_low) < 0.1 * np.std(low_freq_tone)
    assert np.std(filtered_in_band) > 0.5 * np.std(in_band_tone)


def test_rejects_band_above_nyquist():
    with pytest.raises(ValueError):
        apply_bandpass(np.zeros(100), sample_rate_hz=1000, high_freq_hz=2000)
