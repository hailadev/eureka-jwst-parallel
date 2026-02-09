from pathlib import Path
from astropy.io import fits


class PipelineConfig:
    def __init__(self, args):
        self.uncal_data_dir = Path(args.uncal_data_dir)
        self.high_cadence = args.high_cadence
        
        # Default settings
        self.run_from_uncal = True
        self.apply_custom_mask_after_S1 = True
        self.run_jwst_S2 = True
        self.run_eureka_S2_S3 = True

        # self.jwst_S2_output_dir = Path("")
        # self.eureka_commands_directory = ""
        # self.eureka_env_name = ""

        self.read_header()
        
    def read_header(self):
        """
        Reads .fits file to determine object name and instrument.
        """
        with fits.open(self.uncal_data_dir) as file:
            header = file[0].header
        self.instrument = header.get('INSTRUME', 'Unknown')
        self.obj_name = header.get('TARGPROP', 'Unknown')
    
    @property
    def high_cadence_settings(self):
        if self.instrument == "PRISM":
            self.pixels_to_mask = None
            self.n_subints = None
            self.high_cadence_integrations_list = None
            self.high_cadence_exposure = None
            
            if self.obj_name == "ZTFJ0038+2030":
                self.pixels_to_mask = [(488,31), (380, 29)]
                self.n_subints = 2
                self.high_cadence_exposure = 1 # the second exposure

            elif self.obj_name == "WD1032" or self.obj_name == "SDSS1411":
                self.n_subints = 2
        
        if self.instrument == "G395H_nrs1" or self.instrument == "G395H_nrs2":
            self.pixels_to_mask = None
            self.n_subints = None
    
    def print_pipeline_setup(self):
        print(f"""
        Object Name:                {self.obj_name}
        Instrument:                 {self.instrument}
        High cadence:               {self.high_cadence}

        Pipeline Steps:
        Run from uncal:           {self.run_from_uncal}
        Apply custom mask:        {self.apply_custom_mask_after_S1}
        Run jwst S2:              {self.run_jwst_S2}
        Run Eureka:               {self.run_eureka_S2_S3}
        """)
