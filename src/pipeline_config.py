import os
import yaml

from astropy.io import fits
from pathlib import Path

CONFIG_PATH = Path(__file__).parents[1] / 'config.yaml'

class PipelineConfig:
    def __init__(self, args):
        self.hc_flag = args.hc_flag
        self.crds_flag = args.crds_flag
        
        # Default settings
        self.apply_custom_mask_after_S1 = True
        self.run_jwst_S2 = True
        self.run_eureka_S2_S3 = True

        self._load_config()
        self.get_filename()
        self.read_header()
        # self.configure_directories()
        self.file_type()
    
    def _load_config(self):
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        paths = cfg['paths']
        self.path_to_config = CONFIG_PATH
        self.input_dir = self._validate_path(Path(paths['topdir']) / paths['inputdir'].lstrip('/'), 'input_dir')
        self.output_dir = self._validate_path(Path(paths['topdir']) / paths['outputdir'].lstrip('/'), 'output_dir')
        self.ecf_dir = self._validate_path(Path(paths['ecf_dir']), 'ecf_dir')
        self.pixels_to_mask = cfg['custom_mask']

    def _validate_path(self, path: Path, name: str):
        resolved = path.resolve()
        if not resolved.exists():
            raise ValueError(f'{name} does not exist: {resolved}')
        return resolved

    def get_filename(self):
        files = [f for f in os.listdir(self.input_dir) if os.path.isfile(os.path.join(self.input_dir, f))]
        if len(files) > 1:
            raise ValueError(f"Expected only one file in {self.input_dir}, but found {len(files)} files.")
        self.filename = self.input_dir / files[0]

    def read_header(self):
        """
        Reads .fits file to determine object name and instrument.
        """
        with fits.open(self.filename) as file:
            header = file[0].header
        self.instrument = header.get('GRATING', 'Unknown')
        self.obj_name = header.get('TARGPROP', 'Unknown')

    def file_type(self):
        basename = os.path.basename(self.filename)
        if "uncal" in basename:
            self.run_from_uncal = True # Defaults to S1
        elif "rate" or "rateints" in basename:
            self.run_from_uncal = False # Defaults to S2
        else:
            raise ValueError("Unexpected file type")
        return
    
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

        Input data directory:       {self.input_dir}
        Eureka output directory:    {self.output_dir}
        """)
