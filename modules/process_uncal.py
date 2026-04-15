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
    print("filename is ", filename)
    print("object is ", object)
    print("instrument is ", instrument)

    directories_to_backup = ['Stage1']
    backup_dir = os.path.join(output_dir, 'eureka_data_backup')
    os.chdir(output_dir)
    backup_directory(backup_dir, directories_to_backup, output_dir)

    # TO-DO: Add in option for high cadence logic here

    # Native cadence logic below
    logger.info("Running Eureka Stage 1")
    eventlabel = object + '_' + instrument
    print("event label is: ", eventlabel)

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


def backup_directory(backup_dir, directories_to_backup, output_dir):
    """
    Saves the results from past runs.

    Args:
        backup_dir
        directories_to_backup
        output_dir (Path): Location to store the backup
    """
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        logger.info(f"Created backup directory: {backup_dir}")
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')

    for dir_name in directories_to_backup:
        dir_path = os.path.join(output_dir, dir_name)
        if os.path.exists(dir_path):
            # Define the new backup subdirectory name with the timestamp
            dest_path = os.path.join(backup_dir, f'{dir_name}_{timestamp}')
            os.makedirs(dest_path, exist_ok=True)

            for item in os.listdir(dir_path):
                shutil.move(os.path.join(dir_path, item), dest_path)
            logger.info(f"Moved contents of {dir_name} to {dest_path}")

            # Delete the original directory after moving its contents
            shutil.rmtree(dir_path)
            logger.info(f"Deleted original directory: {dir_path}")
        else:
            logger.info(f"Directory does not exist: {dir_path}. No backup required.")
