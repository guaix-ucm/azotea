# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright (c) 2020.
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import os
import os.path

# Access  template withing the package
from pkg_resources import resource_filename

#--------------
# local imports
# -------------

from ._version import get_versions

# ----------------
# Module constants
# ----------------

# ----------------
# Module constants
# ----------------

# Configuration file templates are built-in the package
DEF_CONFIG_TPL = resource_filename(__name__, os.path.join('data', 'azotenodo.ini'))

# Configuration file templates are built-in the package
AZOTEA_BASE_DIR = os.path.join(os.path.expanduser("~"), "azotea")
AZOTEA_CFG_DIR  = os.path.join(AZOTEA_BASE_DIR, "config")
AZOTEA_LOG_DIR  = os.path.join(AZOTEA_BASE_DIR, "log")
AZOTEA_CSV_DIR  = os.path.join(AZOTEA_BASE_DIR, "csv")

# These are in the user's file system
DEF_CONFIG     = os.path.join(AZOTEA_CFG_DIR, os.path.basename(DEF_CONFIG_TPL))
DEF_GLOBAL_CSV = os.path.join(AZOTEA_BASE_DIR, "azotea.csv")

DEF_TSTAMP = "%Y-%m-%dT%H:%M:%S"
# -----------------------
# Module global variables
# -----------------------

# Git Version Management
__version__ = get_versions()['version']
del get_versions
