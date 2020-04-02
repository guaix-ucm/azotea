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

def myopen(name, *args):
    if sys.version_info[0] < 3:
        return open(name, *args)
    else:
        return open(name,  *args, newline='')



def stats_multiple(directory, options):
    directory = directory[:-1] if os.path.basename(directory) == '' else directory
   
    fieldnames = ["observer","organization","location"]
    fieldnames.extend(CameraImage.HEADERS)
    metadata = {'observer': options.observer, 'organization': options.organization, 'location': options.location}
    logging.info("CSV file is {0}".format(options.csv_file))
    with myopen(options.csv_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
        writer.writeheader()
        file_list = glob.glob(os.path.join(directory, options.filter))
        maxsize = len(file_list)
        logging.info("{0}: Scanning a list of {1} entries using filter {2}".format(__name__, maxsize, options.filter))
        for filename in glob.glob(directory + '/' + options.filter):
            image = CameraImage(filename, options)
            image.read()
            row = image.stats()
            row.update(metadata)
            writer.writerow(row)
    logging.info("Saved all to CSV file {0}".format(options.csv_file))


# =====================
# Command esntry points
# =====================


def stats_compute(options):
    stats_multiple(options.work_dir, options)
