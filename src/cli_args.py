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
        '--high_cadence',
        '-hc',
        action = 'store_true',
        dest = 'hc_flag',
        help = "Use this flag to enable high cadence processing"
    )
    
    return parser
