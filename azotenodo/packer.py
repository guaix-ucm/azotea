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

import logging
import os
import os.path
import zipfile
import hashlib
import datetime

#--------------
# local imports
# -------------


# -----------------------
# Module global variables
# -----------------------

SEMANTIC_VERSIONING_FMT = "%y.%m"

log     = logging.getLogger("azotenodo")

# -----------------------
# Module global functions
# -----------------------

def fingerprint(filepath):
    '''Compute a hash from the image'''
    file_hash = hashlib.md5()
    with open(filepath, 'rb') as f:
        block = f.read() 
        while len(block) > 0:
            file_hash.update(block)
            block = f.read()
    return file_hash.digest()


def get_paths(directory):
    '''Get all file paths in a list''' 
  
    file_paths = [] 
  
    # crawling through directory and subdirectories 
    for root, directories, files in os.walk(directory):
        log.info("Exploring = {0}".format(root))
        for filename in files: 
            filepath = os.path.join(root, filename) 
            file_paths.append(filepath) 
    return file_paths         


def pack(options):
    '''Pack all files in the ZIP file given by options'''
    paths = get_paths(options.csv_dir)
    log.info("Creating {0}".format(options.zip_file))
    with zipfile.ZipFile(options.zip_file, 'w') as myzip:
        for myfile in paths: 
            myzip.write(myfile) 



def make_new_release(options):
    hsh        = {}
    first_time = False
    version    = None
    changed    = False
    if os.path.exists(options.zip_file):
        hsh['prev'] = fingerprint(options.zip_file)
    else:
        hsh['prev'] = None
        first_time = True
    pack(options)
    hsh['now'] = fingerprint(options.zip_file)
    if hsh['now'] != hsh['prev']:
        log.info("new files were added to {0}".format(options.zip_file))
        version = datetime.datetime.utcnow().strftime(SEMANTIC_VERSIONING_FMT)
        changed = True
    return first_time, changed, version
