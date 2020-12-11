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

PRODUCTION_DOI_PREFIX = "10.5281"
SANDBOX_DOI_PREFIX    = "10.5072"

PRODUCTION_URL_PREFIX = "https://zenodo.org/api"
SANDBOX_URL_PREFIX    = "https://sandbox.zenodo.org/api"

AZOTEA_PUBL_TITLE     = 'AZOTEA dataset'
AZOTEA_COMMUNITY      = 'azotea'


# Configuration file templates are built-in the package
DEF_CONFIG_TPL = resource_filename(__name__, os.path.join('data', 'azotenodo.ini'))

# Configuration file templates are built-in the package
AZOTEA_BASE_DIR = os.path.join(os.path.expanduser("~"), "azotea")
AZOTEA_CFG_DIR  = os.path.join(AZOTEA_BASE_DIR, "config")
AZOTEA_LOG_DIR  = os.path.join(AZOTEA_BASE_DIR, "log")
AZOTEA_CSV_DIR  = os.path.join(AZOTEA_BASE_DIR, "csv")
AZOTEA_ZIP_DIR  = os.path.join(AZOTEA_BASE_DIR, "zip")
AZOTEA_DB_DIR   = os.path.join(AZOTEA_BASE_DIR, "dbase")

DEF_DBASE      = os.path.join(AZOTEA_DB_DIR, "azotea.db")
DEF_CONFIG     = os.path.join(AZOTEA_CFG_DIR, os.path.basename(DEF_CONFIG_TPL))
DEF_ZIP_FILE   = os.path.join(AZOTEA_ZIP_DIR, "azotea.zip")

DEF_TSTAMP = "%Y-%m-%dT%H:%M:%S"
# -----------------------
# Module global variables
# -----------------------

# Git Version Management
__version__ = get_versions()['version']
del get_versions
