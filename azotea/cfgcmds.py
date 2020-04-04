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
import argparse
import sqlite3
import os
import os.path
import glob
import logging
import csv
import traceback
import shutil

# ---------------------
# Third party libraries
# ---------------------

# Access  template withing the package
from pkg_resources import resource_filename


import sys
from shutil import copyfileobj as copy


#--------------
# local imports
# -------------

from . import DEF_CAMERA_TPL, DEF_CONFIG_TPL, AZOTEA_CFG_DIR

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

# -----------------------
# Module global functions
# -----------------------

def config_list(filename):
    print('\n')
    with open(filename, 'r') as f:
        shutil.copyfileobj(f, sys.stdout)

def config_create(filename):
    dest = os.path.join(AZOTEA_CFG_DIR, os.path.basename(filename))
    shutil.copy2(filename, dest)
    logging.info("Created {0} file".format(dest))

# =====================
# Command esntry points
# =====================


def config_global(connection, options):
    if options.list:
        config_list(DEF_CONFIG_TPL)
    elif options.create:
        config_create(DEF_CONFIG_TPL)

def config_camera(connection, options):
    if options.list:
        config_list(DEF_CONFIG_TPL)
    elif options.create:
        config_create(DEF_CONFIG_TPL)
