import os, yaml
from pathlib import Path


# CRDS variables must be set before eureka module import
def load_config(config_path):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

config = load_config("config.yaml")
crds = config.get("crds_settings", {})
required = ["server_url", "context", "path"]
missing = [k for k in required if not crds.get(k)]
if missing:
    raise ValueError(f"Missing required CRDS config keys: {missing}")

os.environ["CRDS_SERVER_URL"] = crds["server_url"]
os.environ["CRDS_CONTEXT"] = crds["context"]
os.environ["CRDS_PATH"] = str(Path(crds["path"]).expanduser())
os.environ["CRDS_MODE"] = crds.get("mode", "auto")


from loguru import logger
from src.pipeline_config import PipelineConfig
from src.format_ecf import update_ecf
from modules.eureka_s1 import run_eureka_S1
from modules.jwst_s2 import update_exp_type, jwst_S2
from modules.eureka_s2_s3 import run_eureka_S2, run_eureka_S3


def extract_ecf_stage(ecf_dir: Path, stage: str):
    for file in ecf_dir.iterdir():
            if file.is_file() and stage in file.name:
                return file  # Full path
    raise FileNotFoundError(f"No file found containing '{stage}' in {ecf_dir}")


def main():
    pipeline = PipelineConfig()
    # pipeline.print_pipeline_setup()
    eventlabel = f"{pipeline.obj_name}_{pipeline.instrument}"
    topdir = Path(yaml.safe_load(open(pipeline.path_to_config))["paths"]["topdir"])

    if pipeline.run_from_uncal is True:
        S1_ecf = extract_ecf_stage(pipeline.ecf_dir, "S1")
        update_ecf(S1_ecf, pipeline.path_to_config, pipeline.eureka_output_dir)
        
        s1_meta = run_eureka_S1(
            output_dir = pipeline.eureka_output_dir,
            object = pipeline.obj_name,
            instrument = pipeline.instrument,
            ecf_path = pipeline.ecf_dir,
            custom_mask_values = pipeline.pixels_to_mask['S1']
        )
    else:
        s1_meta = None
        logger.info("Assuming Eureka S1 has already been run")

    if pipeline.run_jwst_S2:
        # Find the run1 directory produced by S1
        run1_dirs = sorted(pipeline.eureka_output_dir.glob("S1_*run1"))
        if not run1_dirs:
            raise FileNotFoundError("No S1 output directory found.")
        jwst_header_updated_dir = update_exp_type(
            directory_path = run1_dirs[-1],
            updated_dir_name = f"{pipeline.obj_name}_rate_files_updated_exp_type_to_NRS_FIXEDSLIT",
        )
        jwst_S2(
            fits_dir = jwst_header_updated_dir,
            output_directory = pipeline.jwst_s2_output_dir,
        )
    else:
        logger.info("Skipping JWST S2")

    if pipeline.run_eureka_S2:
        s1_dirs = sorted(pipeline.eureka_output_dir.glob("S1_*"))
        if not s1_dirs:
            raise FileNotFoundError("No S1 output directory found.")
        s2_ecf = extract_ecf_stage(pipeline.ecf_dir, "S2")
        update_ecf(s2_ecf, pipeline.path_to_config, pipeline.eureka_output_dir, inputdir=s1_dirs[-1].relative_to(topdir))
        s2_meta = run_eureka_S2(eventlabel=eventlabel, ecf_path=pipeline.ecf_dir, s1_meta=s1_meta)
    else: 
        s2_meta = None
        logger.info("Assuming Eureka S2 has already been run")

    if pipeline.run_eureka_S3:
        s2_dirs = sorted(pipeline.eureka_output_dir.glob("S2_*"))
        if not s2_dirs:
            raise FileNotFoundError("No S2 output directory found.")
        s3_ecf = extract_ecf_stage(pipeline.ecf_dir, "S3")
        update_ecf(s3_ecf, pipeline.path_to_config, pipeline.eureka_output_dir, inputdir=s2_dirs[-1].relative_to(topdir))
        run_eureka_S3(eventlabel=eventlabel, ecf_path=pipeline.ecf_dir, s2_meta=s2_meta)
    else:
        logger.info("Assuming Eureka S3 has already been run.")


if __name__ == '__main__':
    main()
