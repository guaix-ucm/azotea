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


# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------


# -----------------------
# Module global functions
# -----------------------


# =====================
# Command esntry points
# =====================


def dbase_clear(connection, options):
    cursor = connection.cursor()
    cursor.execute("DELETE FROM image_t")
    connection.commit()


def dbase_purge(connection, options):
    cursor = connection.cursor()
    cursor.execute("DROP TABLE image_t")
    connection.commit()
