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
            # HDF5 reports sizes in bytes. Convert to MB for logging.
            size_mb = (ds.size * ds.dtype.itemsize) / 1024**2 # Bytes to KB to MB: divide by 1024 twice
            logger.info(f"Dataset shape: {ds.shape}  (~{size_mb:.2f} MB)")
            strain = ds[:]
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        raise

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