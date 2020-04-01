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


def stats_single(filepath, options):
    image = CameraImage(filepath, options)
    remaining    = os.path.dirname(filepath)
    location     = os.path.basename(remaining)
    remaining    = os.path.dirname(remaining)
    observer     = os.path.basename(remaining)
    remaining    = os.path.dirname(remaining)
    organization = os.path.basename(remaining)
    fieldnames = ["observer","organization","location"]
    fieldnames.extend(CameraImage.HEADERS)
    metadata = {'observer': observer, 'organization': organization, 'location': location}
    with myopen(options.csv_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
        writer.writeheader()
        image = CameraImage(filepath, options)
        image.read()
        row = image.stats()
        row.update(metadata)
        writer.writerow(row)
    logging.info("Saved image stats to CSV file {0}".format(options.csv_file))


def stats_multiple(directory, options):
    directory = directory[:-1] if os.path.basename(directory) == '' else directory
    location     = os.path.basename(directory)
    remaining    = os.path.dirname(directory)
    observer     = os.path.basename(remaining)
    remaining    = os.path.dirname(remaining)
    organization = os.path.basename(remaining)
    fieldnames   = ["observer","organization","location"]
    fieldnames.extend(CameraImage.HEADERS)
    metadata = {'observer': observer, 'organization': organization, 'location': location} 
    logging.info("CSV file is {0}".format(options.csv_file))
    with myopen(options.csv_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
        writer.writeheader()
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
    if options.input_file is not None:
        stats_single(options.input_file, options)
    else:
        stats_multiple(options.work_dir, options)
