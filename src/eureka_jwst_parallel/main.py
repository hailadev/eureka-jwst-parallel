from src.eureka_jwst_parallel.pipeline_config import PipelineConfig
from src.eureka_jwst_parallel.cli_args import build_parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    pipeline = PipelineConfig(args)
    if pipeline.crds_flag: pipeline.update_crds()
    if pipeline.hc_flag: pipeline.high_cadence_settings()
    pipeline.print_pipeline_setup()


if __name__ == '__main__':
    main()
