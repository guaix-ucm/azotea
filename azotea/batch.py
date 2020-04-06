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
import math

# ---------------------
# Third party libraries
# ---------------------

#--------------
# local imports
# -------------

from .         import AZOTEA_BASE_DIR
from .camimage import  CameraImage
from .utils    import merge_two_dicts, paging


# ----------------
# Module constants
# ----------------

# values for the 'state' column in table

REGISTERED       = 0
RAW_STATS        = 1
DARK_SUBSTRACTED = 2

LIGHT_FRAME = "LIGHT"
DARK_FRAME  = "DARK"
UNKNOWN     = "UNKNOWN"


# ----------
# Exceptions
# ----------

class NoBatchError(ValueError):
	'''No batch to operate upon.'''
	def __str__(self):
		s = self.__doc__
		if self.args:
			s = "{0} \nre-run '{1} --new --work-dir WORK_DIR'".format(s, self.args[0])
		s = '{0}.'.format(s)
		return s


# -----------------------
# Module global variables
# -----------------------

# =======================
# Module global functions
# =======================

# -----------------
# Utility functions
# -----------------

def lookup_batch(connection, batch):
	'''Get one  batch'''
	row = {'batch': batch}
	cursor = connection.cursor()
	cursor.execute('''
		SELECT batch
		FROM image_t
		WHERE batch = batch 
		''', row)
	return cursor.fetchone()[0]

def latest_batch(connection):
	'''Get Last recorded batch'''
	cursor = connection.cursor()
	cursor.execute('''
		SELECT MAX(batch)
		FROM image_t 
		''')
	return cursor.fetchone()[0]


def batch_all_count(cursor):
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		GROUP BY batch
		''')
	result = [ x[0] for x in cursor.fetchall()]
	return sum(result)

def batch_batch_count(cursor, batch):
	row = {'batch': batch}
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		WHERE batch = :batch
		GROUP BY batch, type, state
		''',row)
	result = [ x[0] for x in cursor.fetchall()]
	return sum(result)




# ------------------
# Database iterables
# ------------------


def batch_summary_all_iterable(connection, batch):
	cursor = connection.cursor()
	count = batch_all_count(cursor)
	cursor.execute(
		'''
		SELECT batch, type, s.label, COUNT(*)
		FROM image_t
		JOIN state_t AS s USING(state)
		GROUP BY batch, type, state
		ORDER BY batch DESC, type, state 
		''')
	return cursor, count


def batch_extended_all_iterable(connection, batch):
	cursor = connection.cursor()
	count = batch_all_count(cursor)
	cursor.execute(
		'''
		SELECT batch, name, tstamp, type, s.label
		FROM image_t
		JOIN state_t AS s USING(state)
		ORDER BY batch DESC, name ASC, type
		''')
	return cursor, count


def batch_summary_batch_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	count = batch_batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT batch, type, s.label, COUNT(*)
		FROM image_t
		JOIN state_t AS s USING(state)
		WHERE batch = :batch
		GROUP BY batch, type, state
		ORDER BY batch DESC, type, state 
		''', row)
	return cursor, count


def batch_extended_batch_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	count = batch_batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT batch, name, tstamp, type, s.label
		FROM image_t
		JOIN state_t AS s USING(state)
		WHERE batch = :batch
		ORDER BY batch DESC, name ASC, type
		''', row)
	return cursor, count


# ------------------
# Database inserters
# ------------------



# ==================================
# Image View sumcommands and options
# ==================================


SUMMARY_HEADERS = [
	'Batch',
	'Type',
	'State',
	'# Images',
]


EXTENDED_HEADERS = [
	'Batch',
	'Name',
	'Date',
	'Type',
	'State',
]




def do_batch_view(connection, batch, iterable, headers, options):
	cursor, count = iterable(connection, batch)
	paging(cursor, headers, maxsize=count, page_size=options.page_size)


# =====================
# Command esntry points
# =====================


def batch_current(connection, options):
	batch = latest_batch(connection)
	if options.extended:
		headers = EXTENDED_HEADERS
		iterable = batch_extended_batch_iterable 
	else:
		headers = SUMMARY_HEADERS
		iterable = batch_summary_batch_iterable
	do_batch_view(connection, batch, iterable, headers, options)


def batch_list(connection, options):
	if options.all and options.extended:
		headers = EXTENDED_HEADERS
		batch = None
		iterable = batch_extended_all_iterable
	elif options.all and not options.extended:
		headers = SUMMARY_HEADERS
		batch = None
		iterable = batch_summary_all_iterable
	elif not options.all and options.extended:
		headers = EXTENDED_HEADERS
		batch = lookup_batch(connection, options.batch)
		iterable = batch_extended_batch_iterable
	else:
		headers = SUMMARY_HEADERS
		batch = lookup_batch(connection, options.batch)
		iterable = batch_summary_batch_iterable
	do_batch_view(connection, batch, iterable, headers, options)


