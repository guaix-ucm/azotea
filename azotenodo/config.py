# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------


#--------------------
# System wide imports
# -------------------

import os.path
import errno
import logging

import configparser as ConfigParser


#--------------
# local imports
# -------------


# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("azotenodo")

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
    log.info("Opening configuration file %s", filepath)

    options = {}
    options['api_key_sandbox']    = parser.get("zenodo","api_key_sandbox")
    options['api_key_production'] = parser.get("zenodo","api_key_production")

    return options

