import numpy as np
import logging
from typing import Optional
from scipy.signal import butter, filtfilt, welch
from gwpy.timeseries import TimeSeries
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def signal_quality_check(signal: np.ndarray, sample_rate: int, duration: float) -> dict:
    expected_size = int(sample_rate * duration)

    report = {
        "expected_size": expected_size,
        "actual_size": signal.size,
        "size_ok": signal.size == expected_size,

        "nan_count": int(np.isnan(signal).sum()),
        "inf_count": int(np.isinf(signal).sum()),
        "finite_ok": bool(np.isfinite(signal).all()),

        "mean": float(np.nanmean(signal)),
        "std": float(np.nanstd(signal)),
        "min": float(np.nanmin(signal)),
        "max": float(np.nanmax(signal)),

        "is_flat": bool(np.nanstd(signal) == 0),
        "status": "pass"
    }

    if report["nan_count"] > 0 or report["inf_count"] > 0:
        report["status"] = "needs_repair"

    if not report["size_ok"] or report["is_flat"]:
        report["status"] = "drop_or_investigate"

    return report


def process_signal_quality(
    signal: np.ndarray,
    sample_rate: int,
    duration: float,
    interpolate: bool = True,
    clip_outliers: bool = True,
    outlier_percentiles: tuple = (0.1, 99.9),
) -> Optional[np.ndarray]:

    signal = signal.astype(float).copy()
    report = signal_quality_check(signal, sample_rate, duration)

    _status_label = {
        "pass":               "✓ pass",
        "needs_repair":       "⚠ needs repair",
        "drop_or_investigate": "✗ drop / investigate",
    }
    header = ("Check", "Value", "Status")
    rows = [
        ("Expected Size", f"{report['expected_size']:,}",        ""),
        ("Actual Size",   f"{report['actual_size']:,}",          "✓ ok"      if report["size_ok"]               else "✗ mismatch"),
        ("NaN Count",     f"{report['nan_count']:,}",            "✓ ok"      if report["nan_count"] == 0         else "⚠ found"),
        ("Inf Count",     f"{report['inf_count']:,}",            "✓ ok"      if report["inf_count"] == 0         else "⚠ found"),
        ("Mean",          f"{report['mean']:.4e}",               ""),
        ("Std Dev",       f"{report['std']:.4e}",                ""),
        ("Min",           f"{report['min']:.4e}",                ""),
        ("Max",           f"{report['max']:.4e}",                ""),
        ("Is Flat",       "Yes" if report["is_flat"] else "No",  "✗ flat"    if report["is_flat"]                else "✓ ok"),
    ]
    status_row = ("Overall Status", _status_label.get(report["status"], report["status"]), "")

    all_rows = [header] + rows + [status_row]
    col_w = [max(len(r[i]) for r in all_rows) for i in range(3)]
    a, b, c = col_w

    def _hline(l, m, r):
        return f"{l}{'─' * (a + 2)}{m}{'─' * (b + 2)}{m}{'─' * (c + 2)}{r}"

    def _row(cells):
        return "│ {} │ {} │ {} │".format(*(cells[i].ljust(col_w[i]) for i in range(3)))

    inner_w = a + b + c + 8
    qlines = [
        f"┌{'─' * inner_w}┐",
        f"│{'Signal Quality Report':^{inner_w}}│",
        _hline("├", "┬", "┤"),
        _row(header),
        _hline("├", "┼", "┤"),
        *[_row(r) for r in rows],
        _hline("├", "┼", "┤"),
        _row(status_row),
        _hline("└", "┴", "┘"),
    ]
    logger.info("\n" + "\n".join(qlines))

    expected_size = report["expected_size"]
    actions = []

    # 1. Drop flat signals
    if report["is_flat"]:
        logger.warning("Signal is flat — dropping.")
        return None

    # 2. Fix NaN / inf
    if report["nan_count"] > 0 or report["inf_count"] > 0:
        signal[~np.isfinite(signal)] = np.nan

        if interpolate:
            signal = (
                pd.Series(signal)
                .interpolate(method="linear")
                .bfill()
                .ffill()
                .to_numpy()
            )
            actions.append("Interpolated NaN/inf values")
        else:
            signal = np.nan_to_num(signal, nan=0.0, posinf=0.0, neginf=0.0)
            actions.append("Replaced NaN/inf values with zero")

    # 3. Fix length
    if signal.size != expected_size:
        actual_size = signal.size
        if actual_size < expected_size:
            signal = np.pad(signal, (0, expected_size - actual_size), mode="constant")
            actions.append(f"Padded signal: {actual_size:,} → {expected_size:,} samples")
        else:
            signal = signal[:expected_size]
            actions.append(f"Truncated signal: {actual_size:,} → {expected_size:,} samples")

    # 4. Clip extreme outliers
    if clip_outliers:
        low, high = np.percentile(signal, outlier_percentiles)
        signal = np.clip(signal, low, high)
        actions.append(
            f"Clipped outliers at {outlier_percentiles[0]}th / {outlier_percentiles[1]}th percentile"
        )

    if actions:
        action_rows = ["✓ " + a for a in actions]
        col = max(max(len(r) for r in action_rows), len("Processing Actions"))
        inner = col + 4
        alines = [
            f"┌{'─' * inner}┐",
            f"│{'Processing Actions':^{inner}}│",
            f"├{'─' * inner}┤",
            *[f"│  {r:<{col}}  │" for r in action_rows],
            f"└{'─' * inner}┘",
        ]
        logger.info("\n" + "\n".join(alines))

    return signal


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

def fourier_transform(signal, fs, nperseg=512):
    freqs, psd = welch(signal, fs=fs, nperseg=nperseg)

    peak_idx  = np.argmax(psd)
    peak_freq = freqs[peak_idx]
    peak_psd  = psd[peak_idx]
    df        = freqs[1] - freqs[0] if len(freqs) > 1 else 0.0

    header = ("Property", "Value")
    data = [
        ("Signal Samples",   f"{len(signal):,}"),
        ("Sample Rate",      f"{fs:,.1f} Hz"),
        ("Segment Length",   f"{nperseg} samples"),
        ("Freq Resolution",  f"{df:.4f} Hz"),
        ("Nyquist Freq",     f"{fs / 2:,.1f} Hz"),
        ("Freq Bins",        f"{len(freqs):,}"),
        ("Peak Frequency",   f"{peak_freq:.4f} Hz"),
        ("Peak PSD",         f"{peak_psd:.4e} V²/Hz"),
        ("Mean PSD",         f"{np.mean(psd):.4e} V²/Hz"),
        ("Median PSD",       f"{np.median(psd):.4e} V²/Hz"),
    ]

    all_rows = [header] + data
    col_w = [max(len(r[i]) for r in all_rows) for i in range(2)]
    a, b = col_w

    def hline(l, m, r):
        return f"{l}{'─' * (a + 2)}{m}{'─' * (b + 2)}{r}"

    def row_str(cells):
        return "│ {} │ {} │".format(cells[0].ljust(col_w[0]), cells[1].ljust(col_w[1]))

    inner_w = a + b + 5
    lines = [
        f"┌{'─' * inner_w}┐",
        f"│{'Welch Power Spectral Density Summary':^{inner_w}}│",
        hline("├", "┬", "┤"),
        row_str(header),
        hline("├", "┼", "┤"),
        *[row_str(r) for r in data],
        hline("└", "┴", "┘"),
    ]
    logger.info("\n" + "\n".join(lines))

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.semilogy(freqs, psd, color="steelblue", linewidth=1.4, label="PSD")
    ax.fill_between(freqs, psd, alpha=0.15, color="steelblue")
    ax.axvline(peak_freq, color="tomato", linestyle="--", linewidth=1.2,
               label=f"Peak: {peak_freq:.2f} Hz")
    ax.annotate(
        f"{peak_freq:.2f} Hz\n{peak_psd:.2e}",
        xy=(peak_freq, peak_psd),
        xytext=(peak_freq + (fs / 2) * 0.04, peak_psd),
        fontsize=8.5, color="tomato",
        arrowprops=dict(arrowstyle="->", color="tomato", lw=0.8),
    )
    ax.set_title("Welch Power Spectral Density", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Frequency [Hz]", fontsize=11)
    ax.set_ylabel("PSD [V²/Hz]", fontsize=11)
    ax.set_xlim(0, fs / 2)
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    ax.legend(fontsize=10, framealpha=0.7)
    fig.tight_layout()
    plt.show()

    return freqs, psd


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