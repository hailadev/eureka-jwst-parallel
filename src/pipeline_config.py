import os
from pathlib import Path

import yaml
from astropy.io import fits

CONFIG_PATH = Path(__file__).parents[1] / 'config.yaml'

class PipelineConfig:
    def __init__(self):
        self._load_config()
        self.get_filename()
        self.read_header()
        self.file_type()
    
    def _load_config(self):
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        paths = cfg['paths']
        self.path_to_config = CONFIG_PATH
        self.hc_flag = cfg.get('high_cadence', False)
        self.apply_custom_mask_after_S1 = cfg.get('apply_custom_mask_after_S1', True)
        self.run_jwst_S2 = cfg.get('run_jwst_S2', True)
        self.run_eureka_S2 = cfg.get('run_eureka_S2', True)
        self.run_eureka_S3 = cfg.get('run_eureka_S3', True)
        self.pixels_to_mask = cfg['custom_mask']

        # Input and ECF dirs must exist
        self.input_dir = self._validate_path(Path(paths['topdir']) / paths['inputdir'].lstrip('/'), 'input_dir')
        self.ecf_dir = self._validate_path(Path(paths['ecf_dir']), 'ecf_dir')

        # Create output directory if it doesn't already exist
        if 'outputdir' not in paths:
            raise ValueError("The output directory must be specified in config.yaml.")
        self.output_dir = Path(paths['topdir']) / paths['outputdir'].lstrip('/')
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories to separate Eureka and JWST pipeline output data
        run_dir = self._next_run_dir()
        self.eureka_output_dir = run_dir / 'eureka'
        self.eureka_output_dir.mkdir(parents=True, exist_ok=True)
        self.jwst_s2_output_dir = run_dir / 'jwst_S2'
        self.jwst_s2_output_dir.mkdir(parents=True, exist_ok=True)
    
    def _next_run_dir(self) -> Path:
        existing = [
            d for d in self.output_dir.iterdir()
            if d.is_dir() and d.name.startswith('run')
            and d.name[3:].isdigit()
        ]
        next_n = max((int(d.name[3:]) for d in existing), default=0) + 1
        run_dir = self.output_dir / f'run{next_n}'
        run_dir.mkdir()
        return run_dir

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
