# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------


#--------------------
# System wide imports
# -------------------
#from __future__ import division, absolute_import

import sys
import os
import os.path
import argparse
import errno
import copy

import logging

try:
    # Python 2
    import ConfigParser
except:
    import configparser as ConfigParser


# ---------------
# Twisted imports
# ---------------


#--------------
# local imports
# -------------

from .utils import chop, merge_two_dicts, ROI

# ----------------
# Module constants
# ----------------
# -----------------------
# Module global variables
# -----------------------


# ------------------------
# Module Utility Functions
# ------------------------


def load_config_file(filepath):
    '''
    Load options from configuration file whose path is given
    Returns a dictionary
    '''

    if filepath is None or not (os.path.exists(filepath)):
        raise IOError(errno.ENOENT,"No such file or directory", filepath)

    parser  = ConfigParser.RawConfigParser()
    # str is for case sensitive options
    parser.optionxform = str
    parser.read(filepath)
    logging.info("Opening configuration file {0}".format(filepath))

    options = {}
    options['observer']      = parser.get("observer","observer")
    options['organization']  = parser.get("observer","organization")
    options['location']      = parser.get("location","location")
    options['roi']           = ROI(0, parser.getint("image","width"), 0, parser.getint("image","height"))
    options['scale']         = parser.getfloat("image","scale")

    return options




def merge_options(cmdline_opts, file_opts):
    # Read the command line arguments and config file options
    cmdline_opts = vars(cmdline_opts) # command line options as dictionary
    cmdline_set  = set(cmdline_opts)
    fileopt_set  = set(file_opts)
    conflict_keys = fileopt_set.intersection(cmdline_set)
    options      = merge_two_dicts(file_opts, cmdline_opts)
    # Solve conflicts due to the fact that command line always sets 'None'
    # for missing aruments and take precedence over file opts
    # in the above dictionary merge
    for key in conflict_keys:
        if cmdline_opts[key] is None and file_opts[key] is not None:
            options[key] = file_opts[key]
    options  = argparse.Namespace(**options)
    return options
