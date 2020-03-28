# ----------------------------------------------------------------------
# Copyright (c) 2020.
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------


#--------------
# local imports
# -------------

from ._version import get_versions

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

# Git Version Management
__version__ = get_versions()['version']
del get_versions
