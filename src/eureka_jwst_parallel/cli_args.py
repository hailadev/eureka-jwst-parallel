import argparse


def build_parser():
    parser = argparse.ArgumentParser(
        prog = 'eureka_jwst_parallel',
    )
    parser.add_argument(
        'uncal_data_dir',
        help = "Path to your input data"
    )
    parser.add_argument(
        '--high_cadence',
        '-hc',
        action = 'store_true',
        help = "Use this flag to enable high cadence processing"
    )
    return parser
