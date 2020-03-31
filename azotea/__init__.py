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

DEF_CONFIG = resource_filename(__name__, 'data/camera.ini')


# -----------------------
# Module global variables
# -----------------------

# Git Version Management
__version__ = get_versions()['version']
del get_versions
