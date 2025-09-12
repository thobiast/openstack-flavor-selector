# -*- coding: utf-8 -*-
"""Helper functions."""


import logging
import sys


def setup_logging(log_level):
    """Setup logging configuration."""
    datefmt = "%Y-%m-%d %H:%M:%S"
    msg_fmt = "%(asctime)s - %(module)s.%(funcName)s - [%(levelname)s] - %(message)s"

    formatter = logging.Formatter(
        fmt=msg_fmt,
        datefmt=datefmt,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)


# vim: ts=4
