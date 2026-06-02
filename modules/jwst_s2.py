import glob
import os
import shutil
from os import makedirs, path
from pathlib import Path

from astropy.io import fits
from jwst.pipeline.calwebb_spec2 import Spec2Pipeline
from loguru import logger


def update_exp_type(
        directory_path: Path, 
        updated_dir_name: str, 
        suffix: str = 'rate.fits',  
        old_exp_type: str = 'NRS_BRIGHTOBJ', 
        new_exp_type: str = 'NRS_FIXEDSLIT'
    ):
    """
    Duplicates all rate.fits files into a new subdirectory and updates the EXP_TYPE header in each copy if necessary.
    If the subdirectory already exists, no changes are made and the existing directory is returned.
    The JWST pipeline is run on all files found in this updated subdirectory.

    Args:
        directory_path (Path): Path to the directory containing the rate files
        updated_dir_name (str): Name of the subdirectory to create inside directory_path
        suffix (str): File suffix to match. Defaults to 'rate.fits'
        old_exp_type (str): EXP_TYPE header value to replace. Defaults to 'NRS_BRIGHTOBJ'
        new_exp_type (str): Replacement EXP_TYPE header value. Defaults to 'NRS_FIXEDSLIT'

    Returns:
        str: Path to the subdirectory containing the header-updated files
    """
    logger.info("Attempting to update header exposure type")
    # Get the name of the provided directory and define the target subdirectory path
    updated_dir = os.path.join(directory_path, updated_dir_name)
    
    # Check if the target subdirectory exists
    if not os.path.exists(updated_dir):
        os.makedirs(updated_dir)
        logger.info(f"Created directory: {updated_dir}")
        
        for filename in os.listdir(directory_path):
            if filename.endswith(suffix):
                file_path = os.path.join(directory_path, filename)
                new_file_path = os.path.join(updated_dir, filename)
                
                # Copy the files to the updated subdirectory
                shutil.copy2(file_path, new_file_path)
                logger.info(f"Copied {filename} to {new_file_path}")
                
                # Open the copied FITS file
                with fits.open(new_file_path, mode='update') as hdul:
                    # Check if 'EXP_TYPE' is present and has the value 'NRS_BRIGHTOBJ'
                    if hdul[0].header.get('EXP_TYPE') == old_exp_type:
                        # Update the EXP_TYPE in the primary header
                        hdul[0].header['EXP_TYPE'] = new_exp_type
                        logger.info(f"Updated EXP_TYPE in {new_file_path}")
                    else:
                        logger.info(f"No change needed for {filename} (EXP_TYPE not '{old_exp_type}')")
    else:
        logger.info(f"Directory {updated_dir} already exists. No changes made.")
    
    logger.info("Process complete.")
    # Return the directory where the header-updated files are stored
    return updated_dir


def jwst_S2(fits_dir: Path, output_directory: Path):
    """
    Runs the JWST Spec2Pipeline on all .fits files in fits_dir, saving results to output_directory.
    Configured for NIRSpec TSO observations.

    Args:
        fits_dir (Path): Directory containing the EXP_TYPE-updated rate files
        output_directory (Path): Directory to save JWST S2 output
    """
    # Find all .fits files in the directory with updated headers
    fits_files = glob.glob(os.path.join(fits_dir, '*.fits'))

    # Log file names to confirm input
    logger.info('INPUT FILES:')
    logger.info("\n".join(os.path.basename(f) for f in fits_files))

    for data_filename in fits_files:
        logger.info(f'output dir: {output_directory}')
        if not path.exists(output_directory):
            makedirs(output_directory)

        # Initialize the pipeline instance 
        spec2 = Spec2Pipeline()        
        spec2.output_dir = str(output_directory)
        spec2.prefetch_references = False

        # Apply coordinate system
        spec2.assign_wcs.skip = False
        spec2.assign_wcs.save_results = True

        # MSA STEP
        spec2.msa_flagging.skip = True
        spec2.msa_flagging.save_results = False

        # 1/f noise removal pipeline 1.13.
        spec2.nsclean.skip = False
        spec2.nsclean.save_results = True

        # Removes the imprint from the MSA structure on the detector
        spec2.imprint_subtract.skip = True
        spec2.imprint_subtract.save_results = False

        # Background subtraction step
        spec2.bkg_subtract.skip = False
        spec2.bkg_subtract.save_results = True

        # Extract 2D spectra
        spec2.extract_2d.skip = False
        spec2.extract_2d.save_results = True

        # Source identification step
        spec2.srctype.skip = False
        spec2.srctype.source_type = 'POINT'  # TSO Observations default to a point source based on several tage

        # MSA background step
        spec2.master_background_mos.skip = True
        spec2.master_background_mos.save_results = False

        # Wavelength correction for targets that may be offcenter, usually for MOS and FS modes
        spec2.wavecorr.skip = True
        spec2.wavecorr.save_results = False

        # Straylight correction usally only for MIRI MRS
        spec2.straylight.skip = True
        spec2.straylight.save_results = False

        # For TSO observations the flat field step is run after the extract 2D step
        spec2.flat_field.skip = False
        spec2.flat_field.save_interpolated_flat = True
        spec2.flat_field.save_results = True

        # Removing fringes from optics, usually MIRI step
        spec2.fringe.skip = True
        spec2.fringe.save_results = False

        # Corrections needed to account for signal loss. Usually not used in TSO data
        spec2.pathloss.skip = True
        spec2.pathloss.save_results = False

        # Barshadow step for NIRSpec MSA
        spec2.barshadow.skip = True
        spec2.barshadow.save_results = False

        # Photometric calibration step
        spec2.photom.skip = False
        spec2.photom.save_results = True

        # Removing residual fringes from the MIRI data, skipped for TSO data
        spec2.residual_fringe.skip = True
        spec2.residual_fringe.save_results = False

        # Replace bad and outlier pixels, not default in TSO observations
        spec2.pixel_replace.skip = False
        spec2.pixel_replace.save_results = True

        # Resampling spectra to remove distortions typically skipped for TSO observations
        # EXP_TYPE must be updated in the header for this step to be counted
        spec2.resample_spec.skip = True
        spec2.resample_spec.save_results = True

        # Cube building usually skipped in non-IFU modes
        spec2.cube_build.skip = True
        spec2.cube_build.save_results = False

        # Extracts from 2d spectra file
        spec2.extract_1d.skip = False
        spec2.extract_1d.save_results = True

        spec2.save_results = True
        spec2.run(data_filename)

        # Confirm output was produced
        output_files = glob.glob(os.path.join(output_directory, '*.fits'))
        if output_files:
            logger.info("JWST S2 complete")
        else:
            logger.warning(f'JWST S2 finished running but no output .fits files were found in {output_directory}')
