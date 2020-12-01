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
import logging

import os
import os.path


#--------------
# local imports
# -------------


# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("azotenodo")

# -----------------------
# Module global functions
# -----------------------
def upload_to_zenodo(zip_file, version, url, apikey):
    pass


def pack(options):
    '''Pack all files in the ZIPF file given by options'''
    paths = get_paths(options.csv_dir)
    log.info("Creating/Appending to {0}".format(options.zip_file))
    with zipfile.ZipFile(options.zip_file, 'w') as myzip:
        for myfile in paths: 
            myzip.write(myfile) 