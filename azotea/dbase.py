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

# ---------------------
# Third party libraries
# ---------------------

#--------------
# local imports
# -------------

from . import  AZOTEA_BAK_DIR, DEF_DBASE

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------


# -----------------------
# Module global functions
# -----------------------


def dbase_do_backup(ccomment):
	tstamp = datetime.datetime.utcnow().strftime(".%Y%m%d%H%M%S")
	filename = os.path.basename(DEF_DBASE) + tstamp
	dest_file = os.path.join(AZOTEA_BAK_DIR, filename)
	shutil.copy2(DEF_DBASE, dest_file)
	logging.info("database backup to {0}".format(dest_file))

# =====================
# Command esntry points
# =====================


def dbase_clear(connection, options):
	cursor = connection.cursor()
	cursor.execute("DELETE FROM image_t")
	cursor.execute("DELETE FROM master_dark_t")
	connection.commit()
	logging.info("Cleared data from database {0}".format(DEF_DBASE))


def dbase_purge(connection, options):
	cursor = connection.cursor()
	cursor.execute("DROP VIEW  IF EXISTS image_v")
	cursor.execute("DROP TABLE IF EXISTS image_t")
	cursor.execute("DROP TABLE IF EXISTS master_dark_t")
	cursor.execute("DROP TABLE IF EXISTS state_t")
	connection.commit()
	logging.info("Erased schema in database {0}".format(DEF_DBASE))


def dbase_backup(connection, options):
	connection.close()
	dbase_do_backup(options.comment)