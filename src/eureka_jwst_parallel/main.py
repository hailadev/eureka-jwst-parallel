import os
from pipeline_config import PipelineConfig
from cli_args import build_parser


def update_CRDS():
    """
    Updates CRDS server URL and context.
    """
    os.environ['CRDS_SERVER_URL'] = 'https://jwst-crds.stsci.edu'
    os.environ['CRDS_CONTEXT'] = 'jwst-operational'
    # os.environ['CRDS_CONTEXT'] = 'jwst-2025-06-01T00:00:090'


def main():
    parser = build_parser()
    args = parser.parse_args()
    pipeline = PipelineConfig(args)
    pipeline.print_pipeline_setup()


if __name__ == '__main__':
    main()
