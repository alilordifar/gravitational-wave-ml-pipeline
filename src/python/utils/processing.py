import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import h5py
import re
from scipy import signal
from pathlib import Path
import logging
import os

logging.basicConfig(
    level=logging.DEBUG,
    format = '%(asctime)s - %(levelname)s - %(message)s',
    handlers = [
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataProcessing:
    def __init__(self, data_format, data_dir):
        self.data_format = data_format
        self.data_dir = data_dir

    def list_dir(self):
        logger.info(f"Working Directory: \n {os.getcwd()}")
        logger.info(f"Changing Directory to Data Folder...")
        
        data_path = Path(self.data_dir)
        #logger.info(f"Working Dir: \n {os.getcwd()}")
        if self.data_format == 'hdf5':
            data = list(data_path.glob('*.hdf5'))
            logger.info(f"There are {len(data)} files in the directory!")
            for file in data:
                logger.info(f'Files:\n {file}')
        else:
            logger.error("Unsupported Data Format! Please choose H5PY Data Fromat.")
        return data


    def load_data(self):
        data = self.list_dir()
        file = data[0]
        if self.data_format == 'hdf5':
            with h5py.File(file, 'r') as f:
                logger.info("Loading Data...")
                logger.info(f"Top Level Keys: \n {f.keys()}")
                logger.info(f"\nInside Strain:\n {list(f['strain'].keys())} ")
                dataset = f['strain']['Strain']

                logger.info(f"Shape of Data:\n {dataset.shape}")
                logger.info(f"First 10 strains: \n {dataset[:10]}")
                logger.info(f"Data DType:\n {dataset.dtype}")
        else:
            logger.error("Unsupported Data Format!")

        return dataset

    def time_claculation(self):
        data = self.list_dir()
        match = re.match(r".*-(\d+)-(\d+)\.hdf5$", data[0].name, flags=re.IGNORECASE)
        file_start_gps_time = int(match.group(1))
        logger.info(f"File Start GPS Time: \n {file_start_gps_time}")
        file_duration = int(match.group(2))
        logger.info(f"File Duration: \n {file_duration}")

if __name__ == '__main__':
    processing = DataProcessing('hdf5', 'data/raw')
    os.chdir('../../..')
    processing.load_data()
    processing.time_claculation()