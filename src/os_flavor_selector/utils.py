# -*- coding: utf-8 -*-
"""Helper functions."""


import logging
import re
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


def is_valid_regex(pattern):
    """Returns True if the pattern is a valid regex, False otherwise."""
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


# vim: ts=4
