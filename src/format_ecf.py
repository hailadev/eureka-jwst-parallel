from pathlib import Path

import yaml
from loguru import logger


def update_ecf(ecf_path: Path, yaml_path: Path):
    """
    Rewrites .ecf file, inserting manually defined values specified in the project's configuration file.
    Permits consolidated adjustments to .ecf files without more manual intervention.
    
    Args:
        ecf_path (Path): Location of the .ecf file for the current Eureka pipeline stage
        yaml_path (Path): Location where the project's overarching configuration file is kept.
    """
    with open(yaml_path) as f:
        config = yaml.safe_load(f)
    with open(ecf_path) as f:
        lines = f.readlines()

    updated_lines = []
    for line in lines:
        stripped = line.strip()

        # Keeps comments and blank lines as is
        if not stripped or stripped.startswith("#"):
            updated_lines.append(line)
            continue
        
        key = stripped.split()[0]

        # Updates key/value pairs specified in config
        if key in config['ecf_settings']:
            logger.info(f"Inputing S1 ECF value for {key}")
            updated_lines.append(f"{key}\t{config['ecf_settings'][key]}\n")
        else:
            updated_lines.append(line)

    # Rewrites .ecf file
    with open(ecf_path, "w") as f:
        f.writelines(updated_lines)
