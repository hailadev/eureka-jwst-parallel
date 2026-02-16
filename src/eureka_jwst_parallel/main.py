from src.eureka_jwst_parallel.pipeline_config import PipelineConfig
from src.eureka_jwst_parallel.cli_args import build_parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    pipeline = PipelineConfig(args)
    if pipeline.update_CRDS: pipeline.update_CRDS()
    if pipeline.high_cadence: pipeline.high_cadence_settings()
    pipeline.configure_directories()
    pipeline.print_pipeline_setup()


if __name__ == '__main__':
    main()
