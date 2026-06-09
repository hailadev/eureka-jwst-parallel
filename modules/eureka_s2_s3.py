from pathlib import Path

import eureka.S2_calibrations.s2_calibrate as s2
import eureka.S3_data_reduction.s3_reduce as s3
from loguru import logger


def run_eureka_S2(eventlabel: str, ecf_path: Path, s1_meta=None):
    """
    Runs Eureka Stage 2, calibrating rateints files produced by Stage 1.
    
    Args:
        eventlabel (str): Unique identifier for the observation (e.g. 'WD1202_PRISM')
        ecf_path (Path): Directory containing the S2 .ecf file
        s1_meta: Metadata object from Eureka S1
    """
    logger.info("Running Eureka S2")
    s2_meta = s2.calibrateJWST(eventlabel, ecf_path=ecf_path, s1_meta=s1_meta)
    logger.info("Eureka S2 complete")
    return s2_meta


def run_eureka_S3(eventlabel: str, ecf_path: Path, s2_meta = None):
    """
    Runs Eureka Stage 3, producing time series spectra.

    Args:
        eventlabel (str): Unique identifier for the observation (e.g. 'WD1202_PRISM')
        ecf_path (Path): Directory containing the S3 .ecf file
        s2_meta: Metadata object generated in Eureka S2
    """
    logger.info("Running Eureka S3")
    spec, s3_meta = s3.reduce(eventlabel, ecf_path=ecf_path, s2_meta=s2_meta)
    logger.info("Eureka S3 complete")
    return s3_meta
