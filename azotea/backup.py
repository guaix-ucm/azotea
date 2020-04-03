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
import datetime

# Python3 catch
try:
    raw_input
except:
    raw_input = input 


# ---------------------
# Third party libraries
# ---------------------

#--------------
# local imports
# -------------

from . import DEF_DBASE, AZOTEA_DIR
from .utils import  paging

# ----------------
# Module constants
# ----------------

BACKUP_DIR = os.path.join(AZOTEA_DIR, "backup")

# -----------------------
# Module global variables
# -----------------------


# -----------------------
# Module global functions
# -----------------------


# =====================
# Command esntry points
# =====================


def backup_list(connection, options):
	connection.close()
	file_list = glob.glob(os.path.join(BACKUP_DIR, '*.*' ))
	data = [ [os.path.basename(f)] for f in file_list ]
	headers = ["backup"]
	paging(data, headers, maxsize=len(file_list))


def backup_delete(connection, options):
	connection.close()
	file_path = os.path.join(BACKUP_DIR, options.bak_file)
	os.remove(file_path)
	logging.info("Done.")


def backup_restore(connection, options):
	connection.close()
	backup_file = os.path.join(BACKUP_DIR, options.bak_file)
	if not options.non_interactive:
		raw_input("Are you sure ???? <Enter> to continue or [Ctrl-C] to abort")
	shutil.copy2(backup_file, DEF_DBASE)
	logging.info("Done.")
	