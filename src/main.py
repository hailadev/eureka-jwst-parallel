import os
from pathlib import Path


# CRDS variables must be set before eureka module imports
os.environ["CRDS_SERVER_URL"] = "https://jwst-crds.stsci.edu"
os.environ["CRDS_CONTEXT"] = "jwst-operational"
os.environ["CRDS_PATH"] = str(Path("~/crds_cache").expanduser())
os.environ["CRDS_MODE"] = "auto"


from src.cli_args import build_parser
from src.pipeline_config import PipelineConfig
from src.format_ecf import update_ecf
from modules.process_uncal import run_eureka_S1
from loguru import logger


def extract_ecf_stage(ecf_dir: Path, stage: str):
    for file in ecf_dir.iterdir():
            if file.is_file() and stage in file.name:
                return file  # Full path
    raise FileNotFoundError(f"No file found containing '{stage}' in {ecf_dir}")


def main():
    parser = build_parser()
    args = parser.parse_args()
    pipeline = PipelineConfig(args)
    if pipeline.crds_flag: pipeline.update_crds()
    # if pipeline.hc_flag: pipeline.high_cadence_settings()
    # pipeline.print_pipeline_setup()
    
    if pipeline.run_from_uncal is True:
        S1_ecf = extract_ecf_stage(pipeline.ecf_dir, "S1")
        update_ecf(S1_ecf, pipeline.path_to_config)
        
        run_eureka_S1(
            output_dir = pipeline.output_dir,
            uncal_data_dir = pipeline.input_dir,
            filename = pipeline.filename,
            object = pipeline.obj_name,
            instrument = pipeline.instrument,
            ecf_path=pipeline.ecf_dir,
            high_cadence = pipeline.hc_flag
        )
    else:
        logger.info("Assuming Eureka S1 has already been run")


if __name__ == '__main__':
    main()
