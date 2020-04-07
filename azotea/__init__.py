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

DEF_WIDTH  = 500
DEF_HEIGHT = 400

SQL_TEST_STRING = "SELECT COUNT(*) FROM image_t"

# Configuration file templates are built-in the package
DEF_CAMERA_TPL = resource_filename(__name__, os.path.join('data', 'camera.ini'))
DEF_CONFIG_TPL = resource_filename(__name__, os.path.join('data', 'azotea.ini'))
SQL_SCHEMA     = resource_filename(__name__, os.path.join('data', 'sql', 'schema.sql'))
SQL_PURGE      = resource_filename(__name__, os.path.join('data', 'sql', 'purge.sql'))
SQL_DATA_DIR   = resource_filename(__name__, os.path.join('data', 'sql', 'data' ))


# Configuration file templates are built-in the package
AZOTEA_BASE_DIR = os.path.join(os.path.expanduser("~"), "azotea")
AZOTEA_CFG_DIR  = os.path.join(AZOTEA_BASE_DIR, "config")
AZOTEA_BAK_DIR  = os.path.join(AZOTEA_BASE_DIR, "backup")
AZOTEA_LOG_DIR  = os.path.join(AZOTEA_BASE_DIR, "log")
AZOTEA_CSV_DIR  = os.path.join(AZOTEA_BASE_DIR, "csv")
AZOTEA_DB_DIR   = os.path.join(AZOTEA_BASE_DIR, "dbase")

# These are in the user's file system
DEF_CAMERA     = os.path.join(AZOTEA_CFG_DIR, os.path.basename(DEF_CAMERA_TPL))
DEF_CONFIG     = os.path.join(AZOTEA_CFG_DIR, os.path.basename(DEF_CONFIG_TPL))
DEF_DBASE      = os.path.join(AZOTEA_DB_DIR, "azotea.db")
DEF_GLOBAL_CSV = os.path.join(AZOTEA_BASE_DIR, "azotea.csv")



DEF_TSTAMP = "%Y-%m-%dT%H:%M:%S"
# -----------------------
# Module global variables
# -----------------------

# Git Version Management
__version__ = get_versions()['version']
del get_versions
