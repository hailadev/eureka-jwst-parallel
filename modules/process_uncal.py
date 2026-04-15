"""
This module contains functions to run the Eureka Stage 1 pipeline from uncal files.
"""

import glob
from loguru import logger
import numpy as np
import os
import shutil
import eureka.S1_detector_processing.s1_process as s1
import eureka.lib.plots

from datetime import datetime
from pathlib import Path
from typing import Optional

# Set usetex=True if you have LaTeX installed
eureka.lib.plots.set_rc(style='eureka', usetex=False, filetype='.png')


def run_eureka_S1(
        output_dir: Path,
        uncal_data_dir: Path,
        filename: str,
        object: str,
        instrument: str,
        ecf_path: Path,
        high_cadence: bool = False,
        # n_subints: int = 5, # for high cadence processing
        # integration_list: Optional[list] = None, # for high cadence processing
        # exposure = None, # for high cadence processing
    ):
    """
    Run Stage 1 of the Eureka pipeline.
    Backs up directories to save the past run, if applicable.

    Args:
        output_dir (Path): Path to the output directory
        uncal_data_dir (Path): Path to the input directory containing the uncal.fits file
        filename (str): Path to the specific uncal.fits file to analyze
        object (str): Astronomical object being observed
        instrument(str): 
        ecf_path (Path): Path to the folder where .ecf files are stored
        high_cadence (bool): Flag to toggle on/off high cadence analysis        
    """
    backup_directory(output_dir)

    # TO-DO: Add in option for high cadence logic here

    # Native cadence logic below
    logger.info("Running Eureka Stage 1")
    eventlabel = object + '_' + instrument

    meta = s1.rampfitJWST(eventlabel, ecf_path=ecf_path)
    with open(meta.s1_logname) as f:
        print(f.read())
    logger.info("Eureka Stage 1 complete")

    for d in glob.glob(os.path.join(output_dir, 'Stage1', '*run1')):
        if os.path.isdir(d):
            new_dir = os.path.join(output_dir, 'Stage1', 'native_cadence_run1')
            os.rename(d, new_dir)
            logger.info(f"Renamed {d} to {new_dir}")
            break


def backup_directory(output_dir):
    """
    Saves the results from past runs.

    Args:
        output_dir (Path): Location where Eureka stores outputted results
    """
    backup_dir = os.path.join(output_dir, 'eureka_data_backup')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        logger.info(f"Created backup directory: {backup_dir}")
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')

    for dir in output_dir.iterdir():
        if "DS" in dir.name or "data_backup" in dir.name:
            continue
        if not dir.exists():
            logger.info(f"Directory does not exist: {dir}. No backup required.")
            continue
        
        dest_path = os.path.join(backup_dir, f'{dir.name}_{timestamp}')
        shutil.move(str(dir), str(dest_path))
        logger.info(f"Moved contents of {dir} to {dest_path}")
