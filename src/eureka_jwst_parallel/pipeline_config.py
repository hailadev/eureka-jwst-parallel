import shutil
import os
from pathlib import Path
from astropy.io import fits
from platformdirs import user_data_dir


class PipelineConfig:
    def __init__(self, args):
        self.uncal_data_dir = Path(args.uncal_data_dir)
        self.hc_flag = args.hc_flag
        self.crds_flag = args.crds_flag
        
        # Default settings
        self.run_from_uncal = True
        self.apply_custom_mask_after_S1 = True
        self.run_jwst_S2 = True
        self.run_eureka_S2_S3 = True

        self.read_header()
        
    def read_header(self):
        """
        Reads .fits file to determine object name and instrument.
        """
        with fits.open(self.uncal_data_dir) as file:
            header = file[0].header
        self.instrument = header.get('GRATING', 'Unknown')
        self.obj_name = header.get('TARGPROP', 'Unknown')
    
    def high_cadence_settings(self):
        """
        Defines specific settings for high_cadence processing.
        """
        if self.instrument == 'PRISM':
            self.pixels_to_mask = None
            self.n_subints = None
            self.high_cadence_integrations_list = None
            self.high_cadence_exposure = None
            
            if self.obj_name == 'ZTFJ0038+2030':
                self.pixels_to_mask = [(488,31), (380, 29)]
                self.n_subints = 2
                self.high_cadence_exposure = 1 # The second exposure

            elif self.obj_name == 'WD1032' or self.obj_name == 'SDSS1411':
                self.n_subints = 2
        
        if self.instrument == 'G395H_nrs1' or self.instrument == 'G395H_nrs2':
            self.pixels_to_mask = None
            self.n_subints = None
    
    def update_crds(self):
        """
        Updates CRDS server URL and context.
        """
        server_url = input("Enter the CRDS server URL: ")
        context = input("Enter the CRDS context: ")
        os.environ['CRDS_SERVER_URL'] = server_url
        os.environ['CRDS_CONTEXT'] = context
    
    def configure_directories(self):
        """
        Sets up Application Support directory for data and data analysis output.
        """
        package_name = 'eureka_jwst_parallel'
        base_dir = Path(user_data_dir(package_name))
        
        data_dir = base_dir / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = data_dir

        src = Path(self.uncal_data_dir).expanduser().resolve()
        dest = data_dir / src.name
        shutil.copy2(src, dest) # Copy2 preserves file metadata
        
        output_dir = base_dir / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir

        self.eureka_env_name = 'Eureka_April' # Eureka conda environment
        return
    
    def print_pipeline_setup(self):
        """
        Prints the current pipeline configuration settings and directory layout.
        """
        print(f"""
        Object Name:                {self.obj_name}
        Instrument:                 {self.instrument}
        High cadence:               {self.hc_flag}

        Pipeline Steps:
        Run from uncal:           {self.run_from_uncal}
        Apply custom mask:        {self.apply_custom_mask_after_S1}
        Run jwst S2:              {self.run_jwst_S2}
        Run Eureka:               {self.run_eureka_S2_S3}

        Input data directory:       {self.data_dir}
        Eureka output directory:    {self.output_dir}
        """)
