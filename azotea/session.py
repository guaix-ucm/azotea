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

# ---------------------
# Third party libraries
# ---------------------

#--------------
# local imports
# -------------

from .utils      import paging

# ----------------
# Module constants
# ----------------


# -----------------------
# Module global variables
# -----------------------

# =======================
# Module global functions
# =======================

# -----------------
# Utility functions
# -----------------

def lookup_session(connection, session):
	'''Get one  session'''
	row = {'session': session}
	cursor = connection.cursor()
	cursor.execute('''
		SELECT session
		FROM image_t
		WHERE session = session 
		''', row)
	return cursor.fetchone()[0]


def latest_session(connection):
	'''Get Last recorded session'''
	cursor = connection.cursor()
	cursor.execute('''
		SELECT MAX(session)
		FROM image_t 
		''')
	return cursor.fetchone()[0]


def session_all_count(cursor):
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		GROUP BY session
		''')
	result = [ x[0] for x in cursor.fetchall()]
	return sum(result)


def session_session_count(cursor, session):
	row = {'session': session}
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		WHERE session = :session
		GROUP BY session, type, state
		''',row)
	result = [ x[0] for x in cursor.fetchall()]
	return sum(result)


# ------------------
# Database iterables
# ------------------


def session_summary_all_iterable(connection, session):
	cursor = connection.cursor()
	count = session_all_count(cursor)
	cursor.execute(
		'''
		SELECT session, type, s.label, COUNT(*)
		FROM image_t
		JOIN state_t AS s USING(state)
		GROUP BY session, type, state
		ORDER BY session DESC, type, state 
		''')
	return cursor, count


def session_extended_all_iterable(connection, session):
	cursor = connection.cursor()
	count = session_all_count(cursor)
	cursor.execute(
		'''
		SELECT session, name, tstamp, type, s.label
		FROM image_t
		JOIN state_t AS s USING(state)
		ORDER BY session DESC, name ASC, type
		''')
	return cursor, count


def session_summary_session_iterable(connection, session):
	row = {'session': session}
	cursor = connection.cursor()
	count = session_session_count(cursor, session)
	cursor.execute(
		'''
		SELECT session, type, s.label, COUNT(*)
		FROM image_t
		JOIN state_t AS s USING(state)
		WHERE session = :session
		GROUP BY session, type, state
		ORDER BY session DESC, type, state 
		''', row)
	return cursor, count


def session_extended_session_iterable(connection, session):
	row = {'session': session}
	cursor = connection.cursor()
	count = session_session_count(cursor, session)
	cursor.execute(
		'''
		SELECT session, name, tstamp, type, s.label
		FROM image_t
		JOIN state_t AS s USING(state)
		WHERE session = :session
		ORDER BY session DESC, name ASC, type
		''', row)
	return cursor, count


# ------------------
# Database inserters
# ------------------



# ==================================
# Image View sumcommands and options
# ==================================


SUMMARY_HEADERS = [
	'Session',
	'Type',
	'State',
	'# Images',
]


EXTENDED_HEADERS = [
	'Session',
	'Name',
	'Date',
	'Type',
	'State',
]




def do_session_view(connection, session, iterable, headers, options):
	cursor, count = iterable(connection, session)
	paging(cursor, headers, maxsize=count, page_size=options.page_size)


# =====================
# Command esntry points
# =====================


def session_current(connection, options):
	session = latest_session(connection)
	if options.extended:
		headers = EXTENDED_HEADERS
		iterable = session_extended_session_iterable 
	else:
		headers = SUMMARY_HEADERS
		iterable = session_summary_session_iterable
	do_session_view(connection, session, iterable, headers, options)


def session_list(connection, options):
	if options.all and options.extended:
		headers = EXTENDED_HEADERS
		session = None
		iterable = session_extended_all_iterable
	elif options.all and not options.extended:
		headers = SUMMARY_HEADERS
		session = None
		iterable = session_summary_all_iterable
	elif not options.all and options.extended:
		headers = EXTENDED_HEADERS
		session = lookup_session(connection, options.session)
		iterable = session_extended_session_iterable
	else:
		headers = SUMMARY_HEADERS
		session = lookup_session(connection, options.session)
		iterable = session_summary_session_iterable
	do_session_view(connection, session, iterable, headers, options)


