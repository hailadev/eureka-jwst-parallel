"""
Docstring for parallel_pipeline_run_uncal_module

This module contains functions to run the Eureka Stage 1 pipeline from uncal files,
including high cadence data processing by accessing subintegrations.
"""



import os
import subprocess
import shutil
from datetime import datetime
from jwst import datamodels
import glob

import numpy as np
import argparse
from astropy.io import fits
from astropy.time import Time, TimeDelta
from jwst import datamodels
#from jwst.pipeline import Detector1Pipeline

import warnings



def process_uncal_file_with_subintegrations(
    input_file, output_dir=None, n_subints=2, int_start=None, int_end=None,
        ramp_fit_algorithm='OLS_C', jump_rejection_threshold=8.0,
        exposure=None, integration_list=None, eureka_env_name=None):
    """
    Process a JWST uncal file by breaking each integration into n_subints subintegrations.
    Only integrations specified in integration_list will be subdivided. If integration_list is not provided, the deprecated int_start/int_end range is used. Optionally, process only a specific exposure.

    Parameters
    ----------
    input_file : str
        Path to the uncal file.
    output_dir : str, optional
        Output directory.
    n_subints : int, optional
        Number of subintegrations per integration.
    int_start : int, optional (DEPRECATED)
        Start integration index (inclusive). Deprecated, use integration_list instead.
    int_end : int, optional (DEPRECATED)
        End integration index (inclusive). Deprecated, use integration_list instead.
    ramp_fit_algorithm : str, optional
        Ramp fit algorithm.
    jump_rejection_threshold : float, optional
        Jump rejection threshold.
    exposure : int or None, optional
        Exposure number to process (if applicable, default all).
    integration_list : list[int] or None, optional
        List of integration indices to process (default all). This list is 0-based and applies to the selected exposure. If provided, int_start/int_end are ignored.

    Returns
    -------
    list
        Paths to the three output rateints files and the final rate file
    """
    import numpy as np
    from jwst.datamodels import ImageModel
    # from eureka.S1_detector_processing.s1_process import EurekaS1Pipeline as Detector1Pipeline


    print(f"Processing {input_file} with {n_subints} subintegrations per integration")
    if integration_list is not None:
        print(f"Processing only integrations: {integration_list}")
        if int_start is not None or int_end is not None:
            warnings.warn("int_start and int_end are deprecated and ignored when integration_list is provided.", DeprecationWarning)
    else:
        print(f"Subdivision will be applied to integrations {int_start if int_start is not None else 0} "
              f"to {int_end if int_end is not None else 'end'} (DEPRECATED, use integration_list)")
        if int_start is not None or int_end is not None:
            warnings.warn("int_start and int_end are deprecated. Use integration_list instead.", DeprecationWarning)
    if exposure is not None:
        print(f"Processing only exposure {exposure}")

    # Set up output directory
    if output_dir is None:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    # Get base filename without extension for output naming
    base_filename = os.path.basename(input_file).split('_uncal.fits')[0]

    # Open the uncal file to get information about dimensions
    with datamodels.open(input_file) as uncal_model:
        ngroups = uncal_model.meta.exposure.ngroups
        nints = uncal_model.meta.exposure.nints
        # If exposure selection is supported by the file, add logic here (placeholder)
        # For now, assume one exposure per file
        if exposure is not None:
            # Placeholder: add logic if file contains multiple exposures
            pass

        # If integration_list is provided, use it exclusively
        if integration_list is not None:
            integration_list = sorted(set([i for i in integration_list if 0 <= i < nints]))
            if not integration_list:
                raise ValueError("integration_list is empty or out of range.")
            # The rest of the function should be updated to use integration_list for selection
            int_start = integration_list[0]
            int_end = integration_list[-1]
        else:
            # Set default values for int_start and int_end if not provided
            if int_start is None:
                int_start = 0
            if int_end is None:
                int_end = nints - 1
            # Validate int_start and int_end
            if int_start < 0 or int_start >= nints:
                raise ValueError(f"int_start must be between 0 and {nints-1}")
            if int_end < 0 or int_end >= nints:
                raise ValueError(f"int_end must be between 0 and {nints-1}")
            if int_start > int_end:
                raise ValueError("int_start cannot be greater than int_end")

        groups_per_subint = ngroups // n_subints
        if groups_per_subint < 2:
            raise ValueError(f"Cannot split into {n_subints} subintegrations - need at least 2 groups per subintegration")

        leftover_groups = ngroups % n_subints

    # Define output files for each section
    before_output = os.path.join(output_dir, f"{base_filename}_before_int{int_start}_rateints.fits")
    middle_output = os.path.join(output_dir, f"{base_filename}_int{int_start}_to_int{int_end}_subints_rateints.fits")
    after_output = os.path.join(output_dir, f"{base_filename}_after_int{int_end}_rateints.fits")
    output_files = []

    # --- Process integrations before int_start (no subdivision) ---
    if int_start > 0:
        print(f"Processing integrations 0 to {int_start-1} without subdivision...")
        process_uncal_dir = os.path.dirname(os.path.abspath(__file__))
        temp_output = os.path.basename(before_output).replace('_rateints.fits', '_temp.fits')
        env_name = eureka_env_name if eureka_env_name is not None else "base"
        import shlex
        steps_dict = {
            'ramp_fit': {'save_opt': False, 'algorithm': ramp_fit_algorithm},
            'jump': {'rejection_threshold': jump_rejection_threshold}
        }
        steps_str = repr(steps_dict)
        steps_str_escaped = shlex.quote(steps_str)
        command = [
            "conda", "run", "-n", env_name, "bash", "-c",
            (
                f"cd '{process_uncal_dir}' && "
                "python -c \""
                "from eureka.S1_detector_processing.s1_process import EurekaS1Pipeline as Detector1Pipeline; "
                f"Detector1Pipeline.call('{input_file}', output_dir='{output_dir}', output_file='{temp_output}', save_results=True, steps={steps_str})"
                "\""
            ).replace('{steps_str}', steps_str_escaped)
        ]
        print(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True)
        print("Output:", result.stdout)
        print("Error:", result.stderr)
        temp_file = before_output.replace('_rateints.fits', '_temp_rateints.fits')
        with datamodels.open(temp_file) as full_model, datamodels.cube.CubeModel() as before_model:
            before_shape = (int_start, *full_model.data.shape[1:])
            before_model.data = full_model.data[:int_start]
            before_model.err = full_model.err[:int_start]
            before_model.dq = full_model.dq[:int_start]
            before_model.var_poisson = full_model.var_poisson[:int_start]
            before_model.var_rnoise = full_model.var_rnoise[:int_start]
            before_model.update(full_model)
            before_model.meta.exposure.nints = int_start
            if hasattr(full_model, 'int_times'):
                before_model.int_times = full_model.int_times[:int_start]
            before_model.save(before_output)
        os.remove(temp_file)
        output_files.append(before_output)
    else:
        output_files.append(None)

    # --- Process integrations between int_start and int_end (with subdivision) ---
    if int_end >= int_start:
        print(f"Processing integrations {int_start} to {int_end} with subdivision...")
        subint_files = []
        process_uncal_dir = os.path.dirname(os.path.abspath(__file__))
        env_name = eureka_env_name if eureka_env_name is not None else "base"
        for subint_idx in range(n_subints):
            firstgroup = subint_idx * groups_per_subint
            lastgroup = ngroups - 1 if subint_idx == n_subints - 1 else firstgroup + groups_per_subint - 1
            temp_subint_output = os.path.join(
                output_dir, f"{base_filename}_int{int_start}-{int_end}_subint{subint_idx+1:02d}_temp.fits"
            )
            print(f"Processing subintegration {subint_idx+1}/{n_subints} (groups {firstgroup}-{lastgroup})")
            import shlex
            steps_dict = {
                'ramp_fit': {'save_opt': False, 'algorithm': ramp_fit_algorithm},
                'jump': {'rejection_threshold': jump_rejection_threshold}
            }
            steps_str = repr(steps_dict)
            steps_str_escaped = shlex.quote(steps_str)
            command = [
                "conda", "run", "-n", env_name, "bash", "-c",
                (
                    f"cd '{process_uncal_dir}' && "
                    "python -c \""
                    "from eureka.S1_detector_processing.s1_process import EurekaS1Pipeline as Detector1Pipeline; "
                    f"Detector1Pipeline.call('{input_file}', output_dir='{output_dir}', output_file='{os.path.basename(temp_subint_output)}', save_results=True, steps={steps_str})"
                    "\""
                ).replace('{steps_str}', steps_str_escaped)
            ]
            print(f"Running command: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True)
            print("Output:", result.stdout)
            print("Error:", result.stderr)
            temp_rateints = temp_subint_output.replace('.fits', '_rateints.fits')
            extracted_output = os.path.join(
                output_dir, f"{base_filename}_int{int_start}-{int_end}_subint{subint_idx+1:02d}.fits"
            )
            with datamodels.open(temp_rateints) as full_model, datamodels.cube.CubeModel() as extracted_model:
                n_middle_ints = int_end - int_start + 1
                extracted_model.data = full_model.data[int_start:int_end+1]
                extracted_model.err = full_model.err[int_start:int_end+1]
                extracted_model.dq = full_model.dq[int_start:int_end+1]
                extracted_model.var_poisson = full_model.var_poisson[int_start:int_end+1]
                extracted_model.var_rnoise = full_model.var_rnoise[int_start:int_end+1]
                extracted_model.update(full_model)
                extracted_model.meta.exposure.nints = n_middle_ints
                if hasattr(full_model, 'int_times'):
                    extracted_model.int_times = full_model.int_times[int_start:int_end+1]
                extracted_model.save(extracted_output)
            os.remove(temp_rateints)
            subint_files.append(extracted_output)
        print("Combining subdivided integrations into a single file...")
        combined_middle_model = combine_subints_files(subint_files, int_start, int_end, n_subints)
        combined_middle_model.save(middle_output)
        print(f"Saved subdivided integrations {int_start} to {int_end} to {middle_output}")
        output_files.append(middle_output)
        for file in subint_files:
            if os.path.exists(file):
                os.remove(file)
    else:
        output_files.append(None)

    # --- Process integrations after int_end (no subdivision) ---
    if int_end < nints - 1:
        print(f"Processing integrations {int_end+1} to {nints-1} without subdivision...")
        process_uncal_dir = os.path.dirname(os.path.abspath(__file__))
        temp_output = os.path.basename(after_output).replace('_rateints.fits', '_temp.fits')

        import shlex
        steps_dict = {
            'ramp_fit': {'save_opt': False, 'algorithm': ramp_fit_algorithm},
            'jump': {'rejection_threshold': jump_rejection_threshold}
        }
        steps_str = repr(steps_dict)
        steps_str_escaped = shlex.quote(steps_str)
        command = [
            "conda", "run", "-n", eureka_env_name, "bash", "-c",
            (
                f"cd '{process_uncal_dir}' && "
                "python -c \""
                "from eureka.S1_detector_processing.s1_process import EurekaS1Pipeline as Detector1Pipeline; "
                f"Detector1Pipeline.call('{input_file}', output_dir='{output_dir}', output_file='{temp_output}', save_results=True, steps={steps_str})"
                "\""
            ).replace('{steps_str}', steps_str_escaped)
        ]
        print(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True)
        print("Output:", result.stdout)
        print("Error:", result.stderr)
        temp_file = after_output.replace('_rateints.fits', '_temp_rateints.fits')
        with datamodels.open(temp_file) as full_model, datamodels.cube.CubeModel() as after_model:
            n_after_ints = nints - int_end - 1
            after_model.data = full_model.data[int_end+1:]
            after_model.err = full_model.err[int_end+1:]
            after_model.dq = full_model.dq[int_end+1:]
            after_model.var_poisson = full_model.var_poisson[int_end+1:]
            after_model.var_rnoise = full_model.var_rnoise[int_end+1:]
            after_model.update(full_model)
            after_model.meta.exposure.nints = n_after_ints
            if hasattr(full_model, 'int_times'):
                after_model.int_times = full_model.int_times[int_end+1:]
            after_model.save(after_output)
        os.remove(temp_file)
        output_files.append(after_output)
    else:
        output_files.append(None)

    # --- Create final combined rate file ---
    # Only include files that are not None and actually exist
    valid_rateints = [f for f in [before_output, middle_output, after_output] if f is not None and os.path.exists(f)]
    all_data, all_err, all_dq = [], [], []
    for f in valid_rateints:
        with datamodels.open(f) as cube:
            all_data.append(cube.data)
            all_err.append(cube.err)
            all_dq.append(cube.dq)
    data = np.concatenate(all_data, axis=0)
    err = np.concatenate(all_err, axis=0)
    dq = np.concatenate(all_dq, axis=0)
    # rate_data = np.mean(data, axis=0)
    # rate_err = np.sqrt(np.sum(err**2, axis=0)) / data.shape[0]
    # rate_dq = np.bitwise_or.reduce(dq, axis=0)
    # final_rate_file = os.path.join(output_dir, f"{base_filename}_final_rate.fits")
    # rate_model = ImageModel(data=rate_data, err=rate_err, dq=rate_dq)
    # rate_model.save(final_rate_file)
    # print(f"Saved final combined rate file to {final_rate_file}")

    # output_files.append(final_rate_file)
    return output_files


def combine_subints_files(subint_files, int_start, int_end, n_subints):
    """
    Combine multiple subintegration files into a single rateints file.
    
    Parameters
    ----------
    subint_files : list
        List of paths to subintegration files to combine
    int_start : int
        First integration that was subdivided (0-indexed)
    int_end : int
        Last integration that was subdivided (0-indexed)
    n_subints : int
        Number of subintegrations each original integration was split into
    
    Returns
    -------
    datamodel
        Combined datamodel
    """
    # Load the first file to use as a template
    template_model = datamodels.open(subint_files[0])
    
    # Determine shape of combined data
    shape_2d = template_model.data.shape[1:]  # (y, x)
    n_orig_ints = int_end - int_start + 1
    total_ints = n_orig_ints * n_subints
    
    # Create a new model with the right size
    combined_model = datamodels.cube.CubeModel(
        data=np.zeros((total_ints, *shape_2d), dtype=np.float32),
        err=np.zeros((total_ints, *shape_2d), dtype=np.float32),
        dq=np.zeros((total_ints, *shape_2d), dtype=np.uint32),
        var_poisson=np.zeros((total_ints, *shape_2d), dtype=np.float32),
        var_rnoise=np.zeros((total_ints, *shape_2d), dtype=np.float32)
    )
    
    # Copy metadata from template
    combined_model.update(template_model)
    
    # Update number of integrations
    combined_model.meta.exposure.nints = total_ints
    
    # Create int_times table with the right number of integrations
    int_times_dtype = [
        ('integration_number', '<i2'),
        ('int_start_MJD_UTC', '<f8'),
        ('int_mid_MJD_UTC', '<f8'),
        ('int_end_MJD_UTC', '<f8'),
        ('int_start_BJD_TDB', '<f8'),
        ('int_mid_BJD_TDB', '<f8'),
        ('int_end_BJD_TDB', '<f8')
    ]
    combined_int_times = np.zeros(total_ints, dtype=int_times_dtype)
    
    # Now populate the combined model with data from each subintegration
    for subint_idx, file_path in enumerate(subint_files):
        with datamodels.open(file_path) as model:
            # For each integration in the range int_start to int_end
            for orig_idx in range(n_orig_ints):
                # Map original integration index to the combined index
                combined_idx = orig_idx * n_subints + subint_idx
                
                # Copy data, error, and DQ arrays
                combined_model.data[combined_idx] = model.data[orig_idx]
                combined_model.err[combined_idx] = model.err[orig_idx]
                combined_model.dq[combined_idx] = model.dq[orig_idx]
                combined_model.var_poisson[combined_idx] = model.var_poisson[orig_idx]
                combined_model.var_rnoise[combined_idx] = model.var_rnoise[orig_idx]
                
                # Create integration time entries
                try:
                    if hasattr(model, 'int_times'):
                        orig_int_times = model.int_times
                        
                        # Integration number is 1-indexed in the table
                        combined_int_times['integration_number'][combined_idx] = combined_idx + 1
                        
                        # Handle time values 
                        if subint_idx == 0:  # First subintegration of this integration
                            int_start_time = orig_int_times['int_start_MJD_UTC'][orig_idx]
                            # Calculate the total integration duration
                            total_duration = (orig_int_times['int_end_MJD_UTC'][orig_idx] - 
                                             orig_int_times['int_start_MJD_UTC'][orig_idx])
                            subint_duration = total_duration / n_subints
                        else:
                            # Start time is the end time of the previous subintegration
                            prev_idx = orig_idx * n_subints + (subint_idx - 1)
                            int_start_time = combined_int_times['int_end_MJD_UTC'][prev_idx]
                            
                        int_end_time = int_start_time + subint_duration
                        int_mid_time = int_start_time + subint_duration / 2
                        
                        combined_int_times['int_start_MJD_UTC'][combined_idx] = int_start_time
                        combined_int_times['int_mid_MJD_UTC'][combined_idx] = int_mid_time
                        combined_int_times['int_end_MJD_UTC'][combined_idx] = int_end_time
                        
                        # If BJD TDB times are available, adjust them similarly
                        if 'int_start_BJD_TDB' in orig_int_times.dtype.names:
                            if subint_idx == 0:
                                bjd_start = orig_int_times['int_start_BJD_TDB'][orig_idx]
                                bjd_total_duration = (orig_int_times['int_end_BJD_TDB'][orig_idx] - 
                                                     orig_int_times['int_start_BJD_TDB'][orig_idx])
                                bjd_subint_duration = bjd_total_duration / n_subints
                            else:
                                prev_idx = orig_idx * n_subints + (subint_idx - 1)
                                bjd_start = combined_int_times['int_end_BJD_TDB'][prev_idx]
                            
                            bjd_end = bjd_start + bjd_subint_duration
                            bjd_mid = bjd_start + bjd_subint_duration / 2
                            
                            combined_int_times['int_start_BJD_TDB'][combined_idx] = bjd_start
                            combined_int_times['int_mid_BJD_TDB'][combined_idx] = bjd_mid
                            combined_int_times['int_end_BJD_TDB'][combined_idx] = bjd_end
                except (AttributeError, KeyError) as e:
                    warnings.warn(f"Error processing int_times for {file_path}: {e}")
    
    # Set the int_times table
    combined_model.int_times = combined_int_times
    
    # Close template model
    template_model.close()
    
    return combined_model


def run_eureka_S1(eureka_commands_directory, S1_eureka_script_name, eureka_env_name, uncal_data_dir,
                   high_cadence=False,
                   n_subints=5, integration_list=None, exposure=None, int_start=None, int_end=None):
    
    
    
    print('\nRunning Eureka Stage 1')

    # this is where current eureka data will be backed up (instead of stacking all of it in the same folder)
    directories_to_backup = ["Stage1"]
    backup_directory = os.path.join(eureka_commands_directory, "eureka_data_backup")


    # Change to the Eureka commands directory
    os.chdir(eureka_commands_directory)

    # Create the backup directory if it doesn't exist
    if not os.path.exists(backup_directory):
        os.makedirs(backup_directory)
        print(f"Created backup directory: {backup_directory}")

    # Get the current date and time to create a timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")

    # Move specified directories' contents to the backup directory with a timestamp
    for dir_name in directories_to_backup:
        dir_path = os.path.join(eureka_commands_directory, dir_name)
        if os.path.exists(dir_path):
            # Define the new backup subdirectory name with the timestamp
            dest_path = os.path.join(backup_directory, f"{dir_name}_{timestamp}")
            os.makedirs(dest_path, exist_ok=True)

            # Move each item inside the directory to the timestamped backup subdirectory
            for item in os.listdir(dir_path):
                shutil.move(os.path.join(dir_path, item), dest_path)
            print(f"Moved contents of {dir_name} to {dest_path}")

            # Delete the original directory after moving its contents
            shutil.rmtree(dir_path)
            print(f"Deleted original directory: {dir_path}")
        else:
            print(f"Directory does not exist: {dir_path}")


    
    if high_cadence:
        # --- HIGH CADENCE LOGIC ---
        output_dir = os.path.join(eureka_commands_directory, "Stage1", 'high_cadence_run1')
        os.makedirs(output_dir, exist_ok=True)
        uncal_files = glob.glob(os.path.join(uncal_data_dir, "*uncal.fits"))
        uncal_files.sort()  # Sort alphanumerically by filename
        if not uncal_files:
            print(f"No uncal FITS files found in {uncal_data_dir}")
        process_uncal_dir = os.path.dirname(os.path.abspath(__file__))
        for input_file in uncal_files:
            print(f"Processing file: {input_file}")
            process_uncal_file_with_subintegrations(
                input_file=input_file,
                output_dir=output_dir,
                n_subints=n_subints,
                integration_list=integration_list,
                exposure=exposure,
                eureka_env_name=eureka_env_name
            )
        temp_rate_files = glob.glob(os.path.join(output_dir, "*_temp_rateints.fits"))
        if temp_rate_files:
            print(f"Averaging {len(temp_rate_files)} temp rate files to create final rate file...")
            from jwst.datamodels import ImageModel
            data_list, err_list, dq_list = [], [], []
            for f in temp_rate_files:
                with datamodels.open(f) as m:
                    data_list.append(m.data)
                    err_list.append(m.err)
                    dq_list.append(m.dq)
            data_stack = np.stack(data_list, axis=0)
            err_stack = np.stack(err_list, axis=0)
            dq_stack = np.stack(dq_list, axis=0)
            avg_data = np.mean(data_stack, axis=0)
            avg_err = np.sqrt(np.sum(np.square(err_stack), axis=0)) / data_stack.shape[0]
            avg_dq = np.bitwise_or.reduce(dq_stack, axis=0)
            with datamodels.open(temp_rate_files[0]) as m:
                final_model = ImageModel(data=avg_data, err=avg_err, dq=avg_dq)
                final_model.update(m)
                final_rate_file = os.path.join(output_dir, "final_high_cadence_rate.fits")
                final_model.save(final_rate_file)
                print(f"Saved averaged final rate file to {final_rate_file}")
        else:
            print("No temp rate files found to average.")
    else:
        # --- NATIVE CADENCE LOGIC ---
        command = ["conda", "run", "-n", eureka_env_name, "python", S1_eureka_script_name]
        print(f'command: {" ".join(command)}')
        result = subprocess.run(command, capture_output=True, text=True)
        print("Output:", result.stdout)
        print("Error:", result.stderr)
        if int_start is not None or int_end is not None:
            warnings.warn("int_start and int_end are deprecated. Use integration_list instead.", DeprecationWarning)
        for d in glob.glob(os.path.join(eureka_commands_directory, "Stage1", "*run1")):
            if os.path.isdir(d):
                new_dir = os.path.join(eureka_commands_directory, "Stage1", "native_cadence_run1")
                os.rename(d, new_dir)
                print(f"Renamed {d} to {new_dir}")
                break
            # # Delete old output directory if it exists

            # if os.path.exists(output_dir):

            #     print(f"Removing existing output directory: {output_dir}")

            #     shutil.rmtree(output_dir)



            # # Recreate a clean output directory
