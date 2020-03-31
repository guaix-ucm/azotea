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
import os
import os.path
import glob
import logging

# ---------------------
# Third party libraries
# ---------------------

# Access  template withing the package
from pkg_resources import resource_filename

#--------------
# local imports
# -------------

from . import __version__

from .camimage import  CanonEOS450EDImage, CanonEOS550EDImage

from .utils import  paging

# ----------------
# Module constants
# ----------------

# Exisf Headers we are interested in
EXIF_HEADERS = [
    'Image DateTime',
    'Image Model',
    'EXIF ExposureTime',
    'EXIF ISOSpeedRatings'
]
 
# -----------------------
# Module global variables
# -----------------------

# -----------------------
# Module global functions
# -----------------------

def metadata_single(filename):
    image = CanonEOS450EDImage(filename)
    dict_exif = image.loadEXIF()
    headers = ["File Name"]
    headers.extend(sorted(EXIF_HEADERS))
    data = [image.name()]   
    if sys.version_info[0] < 3:
        data.extend([ value for key, value in sorted(dict_exif.iteritems()) if key in EXIF_HEADERS])
    else:
        data.extend([ value for key, value in sorted(dict_exif.items()) if key in EXIF_HEADERS])
    data = [data]   # tabulate require a list of rows
    paging(data, headers)


def metadata_multiple(directory, imgfilter):
    headers = ["File Name"]
    headers.extend(sorted(EXIF_HEADERS))
    data = []
    for filename in glob.glob(directory + '/' + imgfilter):
        image = CanonEOS450EDImage(filename)
        dict_exif = image.loadEXIF()
        row = [image.name()]   
        if sys.version_info[0] < 3:
            row.extend([ value for key, value in sorted(dict_exif.iteritems()) if key in EXIF_HEADERS])
        else:
            row.extend([ value for key, value in sorted(dict_exif.items()) if key in EXIF_HEADERS])
        data.append(row)
    paging(data, headers)

# =====================
# Command esntry points
# =====================

def metadata_display(options):
    if options.input_file is not None:
        metadata_single(options.input_file)
    else:
        metadata_multiple(options.work_dir, options.filter)
