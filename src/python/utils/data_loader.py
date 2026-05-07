from __future__ import annotations

from gwosc.locate import get_urls
from urllib.request import urlretrieve
import h5py
import numpy as np
import logging
import os


logger = logging.getLogger(__name__)


def load_hdf5_strain(file_path: str) -> np.ndarray:
    try:
        with h5py.File(file_path, "r") as f:
            ds = f["strain"]["Strain"]
            size_mb = (ds.size * ds.dtype.itemsize) / 1024**2
            shape, dtype = ds.shape, ds.dtype
            strain = ds[:]
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        raise

    rows = [
        ("File",      str(file_path)),
        ("Shape",     str(shape)),
        ("dtype",     str(dtype)),
        ("Size",      f"{size_mb:.2f} MB"),
        ("---",       ""),
        ("Min",       f"{strain.min():.6e}"),
        ("Max",       f"{strain.max():.6e}"),
        ("Std",       f"{strain.std():.6e}"),
        ("---",       ""),
        ("NaN count", str(int(np.isnan(strain).sum()))),
        ("Inf count", str(int(np.isinf(strain).sum()))),
    ]

    label_w = max(len(k) for k, _ in rows if k != "---")
    val_w   = max(len(v) for _, v in rows if v != "")
    inner_w = label_w + val_w + 5  # accounts for border padding and center divider

    top   = f"┌{'─' * inner_w}┐"
    title = f"│{'HDF5 Strain Dataset':^{inner_w}}│"
    head  = f"├{'─' * (label_w + 2)}┬{'─' * (val_w + 2)}┤"
    div   = f"├{'─' * (label_w + 2)}┼{'─' * (val_w + 2)}┤"
    bot   = f"└{'─' * (label_w + 2)}┴{'─' * (val_w + 2)}┘"

    lines = [top, title, head]
    for key, val in rows:
        if key == "---":
            lines.append(div)
        else:
            lines.append(f"│ {key:<{label_w}} │ {val:<{val_w}} │")
    lines.append(bot)

    logger.info("Loaded HDF5 strain:\n" + "\n".join(lines))
    return strain

def get_strain_data_from_gwpy(
    file_name: str, detector: str, start_time: int, duration: int, sample_rate: int = 4096
) -> tuple[str, object]:
    end_time = start_time + duration
    try:
        urls = get_urls(detector, start_time, end_time, sample_rate=sample_rate)
    except Exception as e:
        logger.error(f"Error fetching URLs for {detector} at {start_time}: {e}")
        raise

    if not urls:
        raise ValueError(f"No data found for {detector} [{start_time}, {end_time}]")

    local_path = f"{file_name}.hdf5"
    try:
        return urlretrieve(urls[0], local_path)
    except Exception as e:
        logger.error(f"Error downloading {urls[0]}: {e}")
        raise