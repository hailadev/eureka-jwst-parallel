"""
This module contains functions to run the Eureka Stage 1 pipeline from uncal files.
"""

import glob
import os
from pathlib import Path
from typing import Optional

import eureka.lib.plots
import eureka.S1_detector_processing.s1_process as s1
from loguru import logger

from modules.custom_mask import apply_custom_mask, create_custom_mask

# Set usetex=True if you have LaTeX installed
eureka.lib.plots.set_rc(style='eureka', usetex=False, filetype='.png')


def run_eureka_S1(
        output_dir: Path,
        object: str,
        instrument: str,
        ecf_path: Path,
        custom_mask_values: Optional[list[list]] = []
    ):
    """
    Runs Stage 1 of the Eureka pipeline.

    Args:
        output_dir (Path): Path to the output directory
        object (str): Name of the astronomical target being observed
        instrument(str): Disperser used for the observation (e.g. PRISM)
        ecf_path (Path): Path to the folder where .ecf files are stored
        custom_mask_values (list[list]): List of coordinate pairs specified in config to be removed, filtering out outlier pixels
    """
    logger.info("Running Eureka S1")
    eventlabel = f"{object}_{instrument}"

    meta = s1.rampfitJWST(eventlabel, ecf_path=ecf_path)
    with open(meta.s1_logname) as f:
        print(f.read())
    logger.info("Eureka Stage 1 complete")

    # Find the run 1 directory
    run1_dirs = glob.glob(os.path.join(output_dir, "S1_*run1"))
    if not run1_dirs:
        raise FileNotFoundError("No run1 directory found in Stage1.")
    run1_path = run1_dirs[0]

    # Find the rate and rateints files directly in run1_path
    rate_file_paths = glob.glob(os.path.join(run1_path, "*_rate.fits"))
    rateints_file_paths = glob.glob(os.path.join(run1_path, "*rateints.fits"))

    logger.info(f"Found {len(rate_file_paths)} rate files and {len(rateints_file_paths)} rateints files in:\n{run1_path}.")

    if custom_mask_values:
        apply_mask(rateints_file_paths, rate_file_paths, custom_mask_values, output_dir)
    
    logger.info("Eureka S1 complete")
    return meta


def apply_mask(rateints_file_paths: list[Path], rate_file_paths: list[Path], custom_mask_values: list[list], output_dir: Path):
    """
    Creates and applies a custom mask, removing pixels that are NaN in all integrations and those manually specified in the configuration file.

    Args:
        rateints_file_paths (list[Path]): List of all rateints files produced in a Eureka stage run
        rate_file_paths (list[Path]): List of all rate files produced in a Eureka stage run
        custom_mask_values (list[list]): List of all pixels manually specified in config file for removal
        output_dir (Path): Location to save results
    """
    custom_mask_path = create_custom_mask(
        rateints_file = rateints_file_paths[0], 
        output_file = f"{output_dir}/custom_mask.fits", 
        additional_pixels = custom_mask_values
    )

    for rateints_file in rateints_file_paths:
        apply_custom_mask(rateints_file, custom_mask_path)
    for rate_file in rate_file_paths:
        apply_custom_mask(rate_file, custom_mask_path)
