import numpy as np
import logging
from scipy.signal import butter, filtfilt, welch
from gwpy.timeseries import TimeSeries
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def normalize_strain(strain: np.ndarray) -> np.ndarray:
    mean = np.mean(strain)
    std = np.std(strain)

    if std == 0:
        raise ValueError("Standard deviation is zero, cannot normalize.")

    normalized_strain = (strain - mean) / std

    header = ("Statistic", "Before", "After")
    data = [
        ("Mean",    f"{mean:.6e}",             f"{np.mean(normalized_strain):.6e}"),
        ("Std Dev", f"{std:.6e}",              f"{np.std(normalized_strain):.6e}"),
        ("Min",     f"{np.min(strain):.6e}",   f"{np.min(normalized_strain):.6e}"),
        ("Max",     f"{np.max(strain):.6e}",   f"{np.max(normalized_strain):.6e}"),
    ]
    meta = [
        ("Samples", f"{strain.size:,}", f"{normalized_strain.size:,}"),
    ]

    all_rows = [header] + data + meta
    col_w = [max(len(r[i]) for r in all_rows) for i in range(3)]
    a, b, c = col_w

    def hline(l, m, r):
        return f"{l}{'─' * (a + 2)}{m}{'─' * (b + 2)}{m}{'─' * (c + 2)}{r}"

    def row_str(cells):
        return "│ {} │ {} │ {} │".format(*(cells[i].ljust(col_w[i]) for i in range(3)))

    inner_w = a + b + c + 8
    lines = [
        f"┌{'─' * inner_w}┐",
        f"│{'Strain Normalization Summary':^{inner_w}}│",
        hline("├", "┬", "┤"),
        row_str(header),
        hline("├", "┼", "┤"),
        *[row_str(r) for r in data],
        hline("├", "┼", "┤"),
        *[row_str(r) for r in meta],
        hline("└", "┴", "┘"),
    ]

    logger.info("\n" + "\n".join(lines))

    return normalized_strain

def segment_signal(signal, window_size, sample_rate):
    window_samples = int(window_size * sample_rate)
    segments = []
    
    for start in range(0, len(signal), window_samples):
        end = start + window_samples
        
        if end <= len(signal):
            segments.append(signal[start:end])
    
    return np.array(segments)

def fourier_transform(signal, fs):
    

def bandpass_filter(signal, lowcut, highcut, fs, order=4):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    
    b, a = butter(order, [low, high], btype='band')
    filtered = filtfilt(b, a, signal)
    
    return filtered

def bandpass_gwpy(signal, fs):
    ts = TimeSeries(signal, sample_rate=fs)
    return ts.bandpass(20, 500).value

def whiten_gwpy(signal, fs):
    ts = TimeSeries(signal, sample_rate=fs)
    return ts.whiten().value