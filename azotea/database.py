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

log = logging.getLogger("azotea")

# -----------------------
# Module global functions
# -----------------------

def latest_session(connection):
    '''Get Last recorded session'''
    cursor = connection.cursor()
    cursor.execute('''
        SELECT MAX(session)
        FROM image_t 
        ''')
    return cursor.fetchone()[0]


def dbase_do_backup(comment):
    tstamp = datetime.datetime.utcnow().strftime(".%Y%m%d%H%M%S")
    filename = os.path.basename(DEF_DBASE) + tstamp
    dest_file = os.path.join(AZOTEA_BAK_DIR, filename)
    shutil.copy2(DEF_DBASE, dest_file)
    log.info("database backup to {0}".format(dest_file))


def dbase_delete_selected_images(connection, session):
    row = {'session': session}
    cursor = connection.cursor()
    cursor.execute('''
        DELETE FROM image_t
        WHERE session == :session 
        ''', row)

def dbase_delete_selected_master_dark(connection, session):
    row = {'session': session}
    cursor = connection.cursor()
    cursor.execute('''
        DELETE FROM master_dark_t
        WHERE session == :session 
        ''', row)

# =====================
# Command esntry points
# =====================


def database_clear(connection, options):
    cursor = connection.cursor()
    if options.all:
        cursor.execute("DELETE FROM image_t")
        cursor.execute("DELETE FROM master_dark_t")
        log.info("Cleared all data from database {0}".format(os.path.basename(DEF_DBASE)))
    else:
        session = latest_session(connection)
        dbase_delete_selected_master_dark(connection, session)
        dbase_delete_selected_images(connection, session)
        log.info("Cleared data from session {1} in database {0}, ".format(os.path.basename(DEF_DBASE), session))
    connection.commit()



def database_purge(connection, options):
    cursor = connection.cursor()
    with open(SQL_PURGE) as f: 
        lines = f.readlines() 
    script = ''.join(lines)
    connection.executescript(script)
    connection.commit()    
    log.info("Erased schema in database {0}".format(os.path.basename(DEF_DBASE)))



def database_backup(connection, options):
    connection.close()
    dbase_do_backup(options.comment)