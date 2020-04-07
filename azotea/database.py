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

import os.path
import logging
import shutil
import datetime
import glob

# ---------------------
# Third party libraries
# ---------------------

#--------------
# local imports
# -------------

from . import  *

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


def database_clear(connection, options):
    cursor = connection.cursor()
    cursor.execute("DELETE FROM image_t")
    cursor.execute("DELETE FROM master_dark_t")
    connection.commit()
    logging.info("Cleared data from database {0}".format(os.path.basename(DEF_DBASE)))


def database_purge(connection, options):
    cursor = connection.cursor()
    with open(SQL_PURGE) as f: 
        lines = f.readlines() 
    script = ''.join(lines)
    connection.executescript(script)
    connection.commit()    
    logging.info("Erased schema in database {0}".format(os.path.basename(DEF_DBASE)))



def database_backup(connection, options):
    connection.close()
    dbase_do_backup(options.comment)