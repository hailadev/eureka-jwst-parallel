import argparse


def build_parser():
    """
    Creates and configures the command-line argument parser.
    Defines all supported command-line options and arguments, including flags, defaults, and help text. 
    """
    parser = argparse.ArgumentParser(
        prog = 'eureka_jwst_parallel',
    )
    parser.add_argument(
        'input_data_dir',
        help = "Path to your input data"
    )
    parser.add_argument(
        '--high_cadence',
        '-hc',
        action = 'store_true',
        dest = 'hc_flag',
        help = "Use this flag to enable high cadence processing"
    )
    parser.add_argument(
        '--update_crds',
        '-crds',
        action = 'store_true',
        dest = 'crds_flag',
        help = "Use this flag to update CRDS server URL and context."
    )
    return parser
