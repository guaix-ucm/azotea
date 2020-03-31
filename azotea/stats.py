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
import traceback

# ---------------------
# Third party libraries
# ---------------------

# Access  template withing the package
from pkg_resources import resource_filename


import numpy      as np
import matplotlib as mpl
from   matplotlib import pyplot as plt
from   mpl_toolkits.axes_grid1 import make_axes_locatable
from   matplotlib.colors       import LogNorm

#--------------
# local imports
# -------------

from . import __version__
from .camimage import  CanonEOS450EDImage, CanonEOS550EDImage


# ----------------
# Module constants
# ----------------


# -----------------------
# Module global variables
# -----------------------

# -----------------------
# Module global functions
# -----------------------

def stats_single(filename, options):
    image = CanonEOS450EDImage(filename)
    image.read()


def stats_multiple(directory, imgfilter):
    for filename in glob.glob(directory + '/' + imgfilter):
        image = CanonEOS450EDImage(filename)
        image.read()
        

# =====================
# Command esntry points
# =====================

def stats_compute(options):
    pass

def stats_compute(options):
    if options.input_file is not None:
        stats_single(options.input_file)
    else:
        stats_multiple(options.work_dir, options.filter)
