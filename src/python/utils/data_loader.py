import h5py
import numpy as np
import logging

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