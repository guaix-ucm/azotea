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

# Configuration file templates are built-in the package
DEF_CAMERA_TPL = resource_filename(__name__, os.path.join('data', 'camera.ini'))
DEF_CONFIG_TPL = resource_filename(__name__, os.path.join('data', 'azotea.ini'))
SQL_DATAMODEL  = resource_filename(__name__, os.path.join('data', 'azotea.sql'))

# These are in the user's file system
DEF_CAMERA     = os.path.join(os.path.expanduser("~"), os.path.basename(DEF_CAMERA_TPL))
DEF_CONFIG     = os.path.join(os.path.expanduser("~"), os.path.basename(DEF_CONFIG_TPL))
DEF_GLOBAL_CSV = os.path.join(os.path.expanduser("~"), "azotea.csv")
DEF_DBASE      = os.path.join(os.path.expanduser("~"), "azotea.db")

# -----------------------
# Module global variables
# -----------------------

# Git Version Management
__version__ = get_versions()['version']
del get_versions
