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

from .camimage import  CameraImage


# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

# -----------------------
# Module global functions
# -----------------------

def stats_single(filepath, options):
    image = CameraImage(filepath, options)
    image.read()
    stats = image.stats()


if sys.version_info[0] < 3:
    def stats_multiple(directory, options):
        directory = directory[:-1] if os.path.basename(directory) == '' else directory
        outname = os.path.basename(directory) + '.csv'
        logging.info("CSV file is {0}".format(outname))
        with open(outname, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=CameraImage.HEADERS)
            writer.writeheader()
            for filename in glob.glob(directory + '/' + options.filter):
                image = CameraImage(filename, options)
                image.read()
                writer.writerow(image.stats())
        logging.info("Saved all to CSV file {0}".format(outname))
else:
    def stats_multiple(directory, options):
        directory = directory[:-1] if os.path.basename(directory) == '' else directory
        outname = os.path.basename(directory) + '.csv'
        logging.info("CSV file is {0}".format(outname))
        with open(outname, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=CameraImage.HEADERS)
            writer.writeheader()
            for filename in glob.glob(directory + '/' + options.filter):
                image = CameraImage(filename, options)
                image.read()
                writer.writerow(image.stats())
        logging.info("Saved all to CSV file {0}".format(outname))

        

# =====================
# Command esntry points
# =====================


def stats_compute(options):
    if options.input_file is not None:
        stats_single(options.input_file, options)
    else:
        stats_multiple(options.work_dir, options)
