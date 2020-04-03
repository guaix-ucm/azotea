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

from . import DEF_DBASE, AZOTEA_DIR

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
	backup_dir = os.path.join(AZOTEA_DIR, "backup")
	filename = os.path.basename(DEF_DBASE) + tstamp
	if not os.path.exists(backup_dir):
		logging.info("Creating backup directory {0}".format(backup_dir))
		os.mkdir(backup_dir)
	dest_file = os.path.join(backup_dir, filename)
	shutil.copy2(DEF_DBASE, dest_file)
	logging.info("database backup to {0}".format(dest_file))

# =====================
# Command esntry points
# =====================


def dbase_clear(connection, options):
	cursor = connection.cursor()
	cursor.execute("DELETE FROM image_t")
	connection.commit()
	logging.info("Cleared data from database {0}".format(DEF_DBASE))


def dbase_purge(connection, options):
	cursor = connection.cursor()
	cursor.execute("DROP TABLE image_t")
	connection.commit()
	logging.info("Erased schema in database {0}".format(DEF_DBASE))


def dbase_backup(connection, options):
	connection.close()
	dbase_do_backup(options.comment)