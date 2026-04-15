# eureka-jwst-parallel

## Setup

To initially set up the repository, run the following commands:

```git submodule update --init --recursive```

```conda activate eureka```

```python -m pip install -e . --no-build-isolation```

## Defining configuration variables

All user-defined inputs are managed through the config.yaml file located in the project's root directory.

Before running the pipeline, make sure to define:
- The path to your input data directory
- The path where output files should be saved
- The path where ECF files are stored

Optional configuration:
- You can override any .ecf parameter using the format
```ecf_variable_name: desired_value```
- To mask specific pixels, list them under the custom_mask section in a list (e.g. [x, y])

## Running the pipeline

After setup, run the pipeline with the following command:

 ```python -m src.main```