# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright (c) 2020
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import sys
import os
import os.path
import glob
import logging
import shutil
import subprocess

# ---------------------
# Third party libraries
# ---------------------


#--------------
# local imports
# -------------

from .       import AZOTEA_CFG_DIR

# ----------------
# Module constants
# ----------------


# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("azotea")

# -----------------------
# Module global functions
# -----------------------



# =====================
# Command esntry points
# =====================


def changed_observer(connection, options):
	log.info("Changed observer metadata in %s", options.key)
	config_path = os.path.join(AZOTEA_CFG_DIR, options.key + '.ini')

def changed_location(connection, options):
	log.info("Changed location metadata in %s", options.key)
	config_path = os.path.join(AZOTEA_CFG_DIR, options.key + '.ini')

def changed_camera(connection, options):
	log.info("Changed camera metadata in %s", options.key)
	config_path = os.path.join(AZOTEA_CFG_DIR, options.key + '.ini')

def changed_image(connection, options):
	log.info("Changed image metadata in %s", options.key)
	config_path = os.path.join(AZOTEA_CFG_DIR, options.key + '.ini')
