"""
This module creates a custom mask accounting for NaN pixels and manually specified anomalous pixels.
It also implements a process by which to apply the mask to an existing fits file.
"""

import numpy as np
from astropy.io import fits
import matplotlib.pyplot as plt
import os
import time
from loguru import logger
from pathlib import Path


def create_custom_mask(rateints_file: Path, output_file: Path, additional_pixels: list[list] = []):
    """
    Use existing rateints file to create custom pixel mask based on manually specified pixels,
    and also include any pixels that are NaN in all integrations.

    Args:
        rateints_file (Path): Path to rateints file from stage 1 of Eureka/JWST pipeline
        output_file (Path): Path to save the output custom mask file (makes sure the pipeline knows where to find it)
        additional_pixels (list[list]): [x, y] coordinates of additional pixels to mask in the subarray coordinates 
    
    Returns:
        custom_mask.fits output_file with mask applied 
    """
    logger.info(f"Creating custom mask from {rateints_file}")
    
    # Open rateints file 
    with fits.open(rateints_file) as hdul:
        if 'SCI' in hdul:
            sci_data = hdul['SCI'].data
        else:
            sci_data = hdul[1].data  
           

        primary_header = hdul[0].header.copy()

    # Check dimensions - should be (integrations, y, x)
    print(f"Science data shape: {sci_data.shape}")
    sci_2d_shape = sci_data.shape[1:]  
    print(f"2D frame shape: {sci_2d_shape}")
    
    # Find pixels that are NaN in ALL integrations
    all_nan_mask = np.all(np.isnan(sci_data), axis=0)
    nan_y, nan_x = np.where(all_nan_mask)
    logger.info(f"Found {len(nan_y)} pixels that are NaN in all integrations")
    
    # List of all bad pixels
    bad_y_list = list(nan_y)
    bad_x_list = list(nan_x)
    
    # Add manually specified additional pixels
    if additional_pixels and any(additional_pixels):
        # Convert [x,y] input format to separate arrays
        # NOTE: DS9 uses 1-based coordinates, but numpy uses 0-based indexing
        additional_x = np.array([x - 1 for x, y in additional_pixels])
        additional_y = np.array([y - 1 for x, y in additional_pixels])
        
        bad_y_list.extend(additional_y)
        bad_x_list.extend(additional_x)
        
        logger.info(f"Added {len(additional_pixels)} manually specified bad pixels")
    
    bad_y = np.array(bad_y_list)
    bad_x = np.array(bad_x_list)
    logger.info(f"Total bad pixels to mask: {len(bad_y)} (NaN: {len(nan_y)}, Manual: {len(additional_pixels) if additional_pixels else 0})")
    
    # Display an image to see the mask
    mask_image = np.zeros(sci_2d_shape, dtype=bool)
    if len(bad_y) > 0:
        mask_image[bad_y, bad_x] = True

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(mask_image, cmap='gray', origin='lower')
    ax.set_title(f'Bad pixels to mask: {len(bad_y)} (NaN: {len(nan_y)}, Manual: {len(additional_pixels) if additional_pixels else 0})')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    
    # Plot different types of bad pixels with different colors
    if len(nan_y) > 0:
        ax.plot(nan_x, nan_y, 'bo', markersize=2, alpha=0.5, label='Always NaN pixels')
    
    if additional_pixels and any(additional_pixels):
        additional_x = np.array([x - 1 for x, y in additional_pixels])
        additional_y = np.array([y - 1 for x, y in additional_pixels])
        ax.plot(additional_x, additional_y, 'ro', markersize=3, alpha=0.7, label='Manual pixels')
    
    if len(nan_y) > 0 or (additional_pixels and len(additional_pixels) > 0):
        ax.legend()
    
    plt.show()

    # Create mask data array (0 = good pixel, 1 = bad pixel)
    mask_data = np.zeros(sci_2d_shape, dtype=np.uint32)
    
    # Set bad pixels to 1 
    DO_NOT_USE = 1  
    
    if len(bad_y) > 0:
        for y, x in zip(bad_y, bad_x):
            if (0 <= y < sci_2d_shape[0] and 0 <= x < sci_2d_shape[1]):
                mask_data[y, x] = DO_NOT_USE
    
    # Create FITS file
    primary_hdu = fits.PrimaryHDU(header=primary_header)
    
    # Update primary header with mask info
    primary_hdu.header['DESCRIP'] = "Custom bad pixel mask - NaN pixels and manual pixels"
    primary_hdu.header['AUTHOR'] = "dbl_make_custom_mask notebook"
    primary_hdu.header['MASKTYPE'] = "CUSTOM"
    primary_hdu.header['NANPIX'] = len(nan_y)
    primary_hdu.header['MANPIX'] = len(additional_pixels) if additional_pixels else 0
    primary_hdu.header['TOTBAD'] = len(bad_y)
    
    # Create mask extension
    mask_hdu = fits.ImageHDU(data=mask_data, name='DQ')
    mask_hdu.header['EXTNAME'] = 'DQ'
    mask_hdu.header['BUNIT'] = 'dimensionless'
    mask_hdu.header['COMMENT'] = 'Bad pixel mask: 0=good, 1=bad'
    
    # Create HDU list and save the mask
    hdul = fits.HDUList([primary_hdu, mask_hdu])
    hdul.writeto(output_file, overwrite=True)
    
    # Verify the final mask
    with fits.open(output_file) as hdul:
        logger.info("Verifying custom mask structure:")
        for i, ext in enumerate(hdul):
            extname = ext.name if hasattr(ext, 'name') else f"Extension {i}"
            shape = ext.data.shape if hasattr(ext, 'data') and ext.data is not None else "No data"
            print(f"  [{i}] {extname}: {shape}")
        
        # Count bad pixels in the mask
        bad_pixels = np.sum(hdul['DQ'].data != 0)
        logger.info(f"Bad pixels in custom mask: {bad_pixels}")
        logger.info(f"Final mask shape matches science data: {hdul['DQ'].data.shape == sci_2d_shape}")
    
    logger.info(f"Custom mask successfully created at: {output_file}")
    logger.info(f"This mask contains {len(nan_y)} pixels that are NaN in all integrations and {len(additional_pixels) if additional_pixels else 0} manually specified pixels.")
    
    return output_file


def apply_custom_mask(file_path: Path, mask_path: Path):
    """
    Applies mask to filter out NaN pixels in all integrations and those manually specified in the config to account for anomalies.

    Args:
        file_path (Path): Path to file to which the mask is being applied
        mask_path (Path): Path to the custom mask
    """
    mask_data = fits.getdata(mask_path)
    print(f"Mask shape: {mask_data.shape}")
    print(f"Mask data type: {mask_data.dtype}")
    print(f"Unique values in mask: {np.unique(mask_data)}")
    print(f"Number of pixels to mask (value=1): {np.sum(mask_data == 1)}")
    print(f"Number of good pixels (value=0): {np.sum(mask_data == 0)}")

    bad_pixel_mask = (mask_data == 1)
    with fits.open(file_path, mode='update') as hdul:
        try: # Rate file structure
            sci_data = hdul['SCI'].data
            if bad_pixel_mask.shape != sci_data.shape:
                raise ValueError(f"Mask shape {bad_pixel_mask.shape} does not match SCI shape {sci_data.shape} in {file_path}")
            sci_data[bad_pixel_mask] = np.nan
            logger.info(f"Applied custom mask to {file_path} - masked {np.sum(bad_pixel_mask)} pixels")

        except: # Rateints file structure
            sci_data = hdul['SCI'].data
            for i in range(sci_data.shape[0]):
                if bad_pixel_mask.shape != sci_data[i].shape:
                    raise ValueError(f"Mask shape {bad_pixel_mask.shape} does not match SCI integration shape {sci_data[i].shape} in {file_path}")
                sci_data[i][bad_pixel_mask] = np.nan
            logger.info(f"Applied custom mask to {file_path} - masked {np.sum(bad_pixel_mask)} pixels per integration")
    
    # Add in a 30 second pause to make sure the files are done being written before moving on
    os.sync()
    time.sleep(30)
