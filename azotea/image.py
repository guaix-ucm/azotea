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
import sqlite3
import os.path
import glob
import logging
import csv
import datetime
import math
import hashlib
import time

# ---------------------
# Third party libraries
# ---------------------

#--------------
# local imports
# -------------

from .           import AZOTEA_CSV_DIR, AZOTEA_CFG_DIR
from .camera     import CameraImage, CameraCache, MetadataError
from .utils      import merge_two_dicts, paging, LogCounter
from .exceptions import MixingCandidates, NoUserInfoError
from .config     import load_config_file, merge_options


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

N_COUNT = 50

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("azotea")


if sys.version_info[0] == 2:
	import errno
	class FileExistsError(OSError):
		def __init__(self, msg):
			super(FileExistsError, self).__init__(errno.EEXIST, msg)

# =======================
# Module global functions
# =======================

# -----------------
# Utility functions
# -----------------


def classification_algorithm1(name,  file_path, options):
	if name.upper().startswith(DARK_FRAME):
		result = {'name': name, 'type': DARK_FRAME}
	else:
		result = {'name': name, 'type': LIGHT_FRAME}
	return result


def session_processed(connection, session):
	row = {'session': session, 'state': RAW_STATS}
	cursor = connection.cursor()
	cursor.execute('''
		SELECT COUNT(*) 
		FROM image_t 
		WHERE state >= :state
		AND session = :session
		''',row)
	return cursor.fetchone()[0]


def latest_session(connection):
	'''Get Last recorded session'''
	cursor = connection.cursor()
	cursor.execute('''
		SELECT MAX(session)
		FROM image_t 
		''')
	return cursor.fetchone()[0]


def myopen(name, *args):
	if sys.version_info[0] < 3:
		return open(name, *args)
	else:
		return open(name,  *args, newline='')


def hash(filepath):
	'''Compute a hash from the image'''
	BLOCK_SIZE = 65536*65536 # The size of each read from the file
	file_hash = hashlib.sha256()
	with open(filepath, 'rb') as f:
		block = f.read(BLOCK_SIZE) 
		while len(block) > 0:
			file_hash.update(block)
			block = f.read(BLOCK_SIZE)
	return file_hash.digest()


def find_by_hash(connection, hash):
	row = {'hash': hash}
	cursor = connection.cursor()
	cursor.execute('''
		SELECT name
		FROM image_t 
		WHERE hash = :hash
		''',row)
	return cursor.fetchone()


def image_session_state_reset(connection, session):
	row = {'session': session, 'state': RAW_STATS, 'new_state': REGISTERED, 'type': UNKNOWN}
	cursor = connection.cursor()
	cursor.execute(
		'''
		UPDATE image_t
		SET state = :new_state, type = :type
		WHERE state >= :state
		AND session = :session
		''', row)
	connection.commit()


def work_dir_to_session(connection, work_dir, filt):
	file_list  = glob.glob(os.path.join(work_dir, filt))
	names_list = [ {'name': os.path.basename(p)} for p in file_list ]
	log.info("Found {0} candidates matching filter {1}".format(len(names_list), filt))
	cursor = connection.cursor()
	cursor.execute("CREATE TEMP TABLE candidate_t (name TEXT PRIMARY KEY)")
	cursor.executemany("INSERT OR IGNORE INTO candidate_t (name) VALUES (:name)", names_list)
	connection.commit()
	# Common images to database and work-dir
	cursor.execute(
		'''
		SELECT MAX(session), MAX(session) == MIN(session)
		FROM image_t
		WHERE name IN (SELECT name FROM candidate_t)
		'''
		)
	result = cursor.fetchall()
	if result:
		sessiones, flags = zip(*result)
		if flags[0] and not all(flags):
			raise MixingCandidates(names_common)
		session = sessiones[0]
	else:
		session = None
	return session

def work_dir_cleanup(connection):
	cursor = connection.cursor()
	cursor.execute("DROP TABLE IF EXISTS candidate_t")
	connection.commit()


def master_dark_for(connection, session):
	row = {'session': session}
	cursor = connection.cursor()
	cursor.execute('''
		SELECT COUNT(*) 
		FROM master_dark_t
		WHERE session = :session
		''',row)
	return cursor.fetchone()[0]



# --------------
# Image Register
# --------------

def register_insert_image(connection, row):
	'''slow version to find out the exact duplicate'''
	cursor = connection.cursor()
	cursor.execute(
			'''
			INSERT INTO image_t (
				name, 
				hash,
				session, 
				type,
				state
			) VALUES (
				:name, 
				:hash,
				:session,
				:type,
				:state
			)
			''', row)
	connection.commit()


def register_insert_images(connection, rows):
	'''fast version'''
	cursor = connection.cursor()
	cursor.executemany(
			'''
			INSERT INTO image_t (
				name, 
				hash,
				session,
				type,
				state
			) VALUES (
				:name, 
				:hash,
				:session, 
				:type,
				:state
			)
			''', rows)
	connection.commit()


def candidates(connection, work_dir, filt, session):
	'''candidate list of images to be inserted/removed to/from the database'''
	# New Images in the work dir that should be added to database
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name
		FROM candidate_t
		WHERE name NOT IN (SELECT name FROM image_t)
		'''
		)
	result = cursor.fetchall()
	if result:
		names_to_add, = zip(*result)
	else:
		names_to_add = []
	# Images no longer in the work dir, they should be deleted from database
	row = {'session': session}
	cursor.execute(
		'''
		SELECT name
		FROM image_t
		WHERE name NOT IN (SELECT name FROM candidate_t)
		AND session = :session
		''', row)
	result = cursor.fetchall()
	if result:
		names_to_del, = zip(*result)
	else:
		names_to_del = []
	return names_to_add, names_to_del


def register_delete_images(connection, rows):
	'''delete images'''
	cursor = connection.cursor()
	cursor.executemany(
			'''
			DELETE FROM image_t 
			WHERE name  == :name
			AND   session == :session
			''', rows)
	connection.commit()


def register_slow(connection, work_dir, names_list, session):
	duplicated_file_paths = []
	counter = LogCounter(N_COUNT)
	for name in names_list:
		file_path = os.path.join(work_dir, name)
		row  = {'name': name, 'session': session, 'state': REGISTERED, 'type': UNKNOWN,}
		row['hash'] = hash(file_path)
		counter.tick("Registered %d images in database (slow method)")
		try:
			register_insert_image(connection, row)
		except sqlite3.IntegrityError as e:
			connection.rollback()
			name2, = find_by_hash(connection, row['hash'])
			duplicated_file_paths.append({'original': name2, 'duplicated': file_path})
			log.warning("Duplicate => %s EQUALS %s", file_path, name2)
		else:
			log.debug("%s registered in database", row['name'])
	counter.end("Registered %d images in database (slow method)")


def register_fast(connection, work_dir, names_list, session):
	rows = []
	counter = LogCounter(N_COUNT)
	for name in names_list:
		file_path = os.path.join(work_dir, name)
		row  = {'name': name, 'session': session, 'state': REGISTERED, 'type': UNKNOWN,}
		row['hash'] = hash(file_path)
		rows.append(row)
		log.debug("%s being registered in database", row['name'])
		counter.tick("Registered %d images in database")
	counter.end("Registered %d images in database")
	register_insert_images(connection, rows)
	

def register_unregister(connection, names_list, session):
	rows = []
	counter = LogCounter(N_COUNT)
	log.info("Unregistering images from database")
	for name in names_list:
		rows.append({'session': session, 'name': name, 'session': session})
		log.debug("%s being removed from database", name)
		counter.tick("Removed %d images from database")
	counter.end("Removed %d images from database")
	register_delete_images(connection, rows)
	

def do_register(connection, work_dir, filt, session):
	names_to_add, names_to_del = candidates(connection, work_dir, filt, session)
	if names_to_del:
		register_unregister(connection, names_to_del, session)  
	if names_to_add:
		try:
			register_fast(connection, work_dir, names_to_add, session)
		except sqlite3.IntegrityError as e:
			connection.rollback()
			register_slow(connection, work_dir, names_to_add, session)
	log.info("{0} new images registered in database".format(len(names_to_add)))
	log.info("{0} images deleted from database".format(len(names_to_del)))



# --------------
# Image Classify
# --------------


def classify_update_db(connection, rows):
	cursor = connection.cursor()
	cursor.executemany(
		'''
		UPDATE image_t
		SET type  = :type
		WHERE name = :name
		''', rows)
	connection.commit()



def classify_session_iterable(connection, session):
	row = {'session': session, 'type': UNKNOWN}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name
		FROM image_t
		WHERE type = :type
		AND session = :session
		''', row)
	return cursor


def do_classify(connection, session, work_dir, options):
	rows = []
	counter = LogCounter(N_COUNT)
	log.info("Classifying images")
	for name, in classify_session_iterable(connection, session):
		file_path = os.path.join(work_dir, name)
		row = classification_algorithm1(name, file_path, options)
		log.debug("%s is type %s", name, row['type'])
		counter.tick("Classified %d images")
		rows.append(row)
	if rows:
		classify_update_db(connection, rows)
		counter.end("Classified %d images")
	else:
		log.info("No image type classification is needed")


# -----------
# Image Stats
# -----------

def stats_update_db(connection, rows):
	cursor = connection.cursor()
	cursor.executemany(
		'''
		UPDATE image_t
		SET 
			state               = :state,
			roi                 = :roi, 
			model               = :model,   -- EXIF
			iso                 = :iso,     -- EXIF
			tstamp              = :tstamp,  -- EXIF
			exptime             = :exptime, -- EXIF
			focal_length        = :focal_length, -- EXIF
			f_number            = :f_number,     -- EXIF
			aver_raw_signal_R1  = :aver_raw_signal_R1, 
			aver_raw_signal_G2  = :aver_raw_signal_G2, 
			aver_raw_signal_G3  = :aver_raw_signal_G3,
			aver_raw_signal_B4  = :aver_raw_signal_B4,
			vari_raw_signal_R1  = :vari_raw_signal_R1,
			vari_raw_signal_G2  = :vari_raw_signal_G2,
			vari_raw_signal_G3  = :vari_raw_signal_G3,
			vari_raw_signal_B4  = :vari_raw_signal_B4 
		WHERE name = :name
		''', rows)
	connection.commit()


def stats_delete_db(connection, rows):
	row = {'session': session, 'state': RAW_STATS}
	cursor = connection.cursor()
	cursor.executemany(
		'''
		DELETE FROM image_t
		WHERE name  = :name
		AND session = :session
		''', rows)
	connection.commit()


def stats_session_iterable(connection, session):
	row = {'session': session, 'state': RAW_STATS}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name
		FROM image_t
		WHERE state < :state
		AND session = :session
		''', row)
	return cursor


def do_stats(connection, session, work_dir, options):
	camera_cache = CameraCache(options.camera)
	rows = []
	rows_to_delete = []
	counter = LogCounter(N_COUNT)
	log.info("Computing image statistics")
	for name, in stats_session_iterable(connection, session):
		file_path = os.path.join(work_dir, name)
		image = CameraImage(file_path, camera_cache)
		image.setROI(options.roi)
		counter.tick("Statistics for %d images done")
		try:
			metadata = image.loadEXIF()
		except MetadataError as e:
			log.warning(e)    # we need to find out the camera model before reading
			rows_to_delete().append({'session': session, 'name': name})
		else:
			image.read()
			row = image.stats()
			row['state']        = RAW_STATS
			row['observer']     = options.observer
			row['organization'] = options.organization
			row['email']        = options.email
			row['location']     = options.location
			row['model']        = metadata['model']
			row['iso']          = metadata['iso']
			row['tstamp']       = metadata['tstamp']
			row['exptime']      = metadata['exptime']
			row['focal_length'] = options.focal_length if metadata['focal_length'] is None else metadata['focal_length']
			row['f_number']     = options.f_number if metadata['f_number'] is None else metadata['f_number']
			rows.append(row)
	if rows_to_delete:
		stats_delete_db(connection, rows_to_delete)
		log.info("Unregistered {0} data base entries whose EXIF metadata could not be read".format(len(rows_to_delete)))
	if rows:
		counter.end("Statistics for %d images done")
		stats_update_db(connection, rows)
	else:
		log.info("No image statistics to be computed")

# -----------------------------
# Image Apply Dark Substraction
# -----------------------------

def master_dark_db_update_all(connection, session):
	row = {'type': DARK_FRAME, 'state': RAW_STATS}
	cursor = connection.cursor()
	cursor.execute(
		'''
		INSERT OR REPLACE INTO master_dark_t (
			session, 
			roi, 
			N, 
			aver_R1, 
			aver_G2, 
			aver_G3, 
			aver_B4,
			vari_R1, 
			vari_G2, 
			vari_G3, 
			vari_B4,
			min_exptime,
			max_exptime
		)
		SELECT 
			session, 
			MIN(roi), 
			COUNT(*), 
			AVG(aver_raw_signal_R1), 
			AVG(aver_raw_signal_G2), 
			AVG(aver_raw_signal_G3), 
			AVG(aver_raw_signal_B4),
			SUM(vari_raw_signal_R1)/COUNT(*),
			SUM(vari_raw_signal_G2)/COUNT(*),
			SUM(vari_raw_signal_G3)/COUNT(*),
			SUM(vari_raw_signal_B4)/COUNT(*),
			MIN(exptime),
			MAX(exptime)
		FROM image_t
		WHERE type = :type
		AND   state >= :state
		GROUP BY session
		''', row)
	connection.commit()


def master_dark_db_update_session(connection, session):
	row = {'type': DARK_FRAME, 'state': RAW_STATS, 'session': session}
	cursor = connection.cursor()
	cursor.execute(
		'''
		INSERT OR REPLACE INTO master_dark_t (
			session, 
			roi, 
			N, 
			aver_R1, 
			aver_G2, 
			aver_G3, 
			aver_B4,
			vari_R1, 
			vari_G2, 
			vari_G3, 
			vari_B4,
			min_exptime,
			max_exptime
		)
		SELECT 
			session, 
			MIN(roi), 
			COUNT(*), 
			AVG(aver_raw_signal_R1), 
			AVG(aver_raw_signal_G2), 
			AVG(aver_raw_signal_G3), 
			AVG(aver_raw_signal_B4),
			SUM(vari_raw_signal_R1)/COUNT(*),
			SUM(vari_raw_signal_G2)/COUNT(*),
			SUM(vari_raw_signal_G3)/COUNT(*),
			SUM(vari_raw_signal_B4)/COUNT(*),
			MIN(exptime),
			MAX(exptime)
		FROM image_t
		WHERE session = :session 
		AND   type    = :type
		AND   state  >= :state
		GROUP BY session
		''', row)
	connection.commit()


def dark_update_columns(connection, session):
	row = {'type': LIGHT_FRAME, 'session': session, 'state': RAW_STATS, 'new_state': DARK_SUBSTRACTED}
	cursor = connection.cursor()
	cursor.execute(
		'''
		UPDATE image_t
		SET
			state        = :new_state,
			aver_dark_R1 = (SELECT aver_R1 FROM master_dark_t WHERE session = :session),
			aver_dark_G2 = (SELECT aver_G2 FROM master_dark_t WHERE session = :session),
			aver_dark_G3 = (SELECT aver_G3 FROM master_dark_t WHERE session = :session),
			aver_dark_B4 = (SELECT aver_B4 FROM master_dark_t WHERE session = :session),
			vari_dark_R1 = (SELECT vari_R1 FROM master_dark_t WHERE session = :session),
			vari_dark_G2 = (SELECT vari_G2 FROM master_dark_t WHERE session = :session),
			vari_dark_G3 = (SELECT vari_G3 FROM master_dark_t WHERE session = :session),
			vari_dark_B4 = (SELECT vari_B4 FROM master_dark_t WHERE session = :session)
		WHERE session = :session
		AND   state BETWEEN :state AND :new_state
		AND   type  = :type
		''',row)
	connection.commit()


def do_apply_dark(connection, session, options):
	master_dark_db_update_session(connection, session)
	if master_dark_for(connection, session):
		log.info("Applying dark substraction to current working directory")
		dark_update_columns(connection, session)
	else:
		log.info("No dark frame found for current working directory")

# -----------
# Image Export
# -----------


VIEW_HEADERS = [
			'tstamp'         ,
			'name'           ,
			'model'          ,
			'iso'            ,
			'roi'            ,
			'dark_roi'       ,
			'exptime'        ,
			'aver_signal_R1' ,
			'std_signal_R1'  ,
			'aver_signal_G2' ,
			'std_signal_G2'  ,
			'aver_signal_G3' ,
			'std_signal_G3'  ,
			'aver_signal_B4' ,
			'std_signal_B4'  ,
		]

def export_session_iterable(connection, session):
	row = {'session': session, 'state': RAW_STATS, 'type': LIGHT_FRAME}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT  session,
				observer,
				organization,
				location,
				type,
				tstamp, 
				name, 
				model, 
				iso, 
				roi,
				dark_roi,
				exptime, 
				aver_signal_R1, 
				vari_signal_R1, -- Array index 13
				aver_signal_G2, 
				vari_signal_G2, -- Array index 15
				aver_signal_G3, 
				vari_signal_G3, -- Array index 17
				aver_signal_B4, 
				vari_signal_B4  -- Array index 19
		FROM image_v
		WHERE state >= :state
		AND   type = :type
		AND   session = :session
		''', row)
	return cursor

def export_all_iterable(connection):
	row = {'state': RAW_STATS, 'type': LIGHT_FRAME}
	cursor = connection.cursor()
	cursor.execute(
		'''
	   SELECT   session,
				observer,
				organization,
				location,
				type,
				tstamp, 
				name, 
				model, 
				iso, 
				roi,
				dark_roi,
				exptime, 
				aver_signal_R1, 
				vari_signal_R1, -- Array index 13
				aver_signal_G2, 
				vari_signal_G2, -- Array index 15
				aver_signal_G3, 
				vari_signal_G3, -- Array index 17
				aver_signal_B4, 
				vari_signal_B4  -- Array index 19
		FROM image_v
		WHERE state >= :state
		AND   type = :type
		''', row)
	return cursor


def var2std(item):
	'''From Variance to StdDev in seevral columns'''
	index, value = item
	return round(math.sqrt(value),1) if index in [13, 15, 17, 19] else value


def get_file_path(connection, session, work_dir, options):
	# respect user's wishes above all
	if options.csv_file:
		return options.csv_file
	# This is for automatic reductions mainly
	middle = os.path.basename(work_dir)
	if middle == '':
		middle = os.path.basename(work_dir[:-1])
	name = "-".join([options.csv_file_prefix, "session", middle + '.csv'])
	return os.path.join(AZOTEA_CSV_DIR, name)
	

def do_export_work_dir(connection, session, work_dir, options):
	'''Export a working directory of image redictions to a single file'''
	fieldnames = ["session","observer","organization","location","type"]
	fieldnames.extend(VIEW_HEADERS)
	if session_processed(connection, session):
		# Write a session CSV file
		session_csv_file = get_file_path(connection, session, work_dir, options)
		with myopen(session_csv_file, 'w') as csvfile:
			writer = csv.writer(csvfile, delimiter=';')
			writer.writerow(fieldnames)
			for row in export_session_iterable(connection, session):
				row = map(var2std, enumerate(row))
				writer.writerow(row)
		log.info("Saved data to session CSV file {0}".format(session_csv_file))
	else:
		log.info("No new CSV file generation")
	

def do_export_all(connection,  options):
	'''Exports all the database to a single file'''
	fieldnames = ["session","observer","organization","location","type"]
	fieldnames.extend(VIEW_HEADERS)
	with myopen(options.csv_file, 'w') as csvfile:
		writer = csv.writer(csvfile, delimiter=';')
		writer.writerow(fieldnames)
		for row in export_all_iterable(connection):
			row = map(var2std, enumerate(row))
			writer.writerow(row)
	log.info("Saved data to global CSV file {0}".format(options.global_csv_file))

# ==================================
# Image List subcommands and options
# ==================================


EXIF_HEADERS = [
	'Name',
	'Session',
	'Timestamp',
	'Model',
	'Exposure',
	'ISO',
	'Focal',
	'f/'
]

GLOBAL_HEADERS = [
	'Name',
	'Type',
	'Session',
	'Observer',
	'Organiztaion',
	'Location',
	'ROI',
]

STATE_HEADERS = [
	"Name",
	"Session",
	"Type", 
	"State",
]

DATA_HEADERS = [
	"Name", "Session",
	"\u03BC R1", "\u03C3^2 R1", 
	"\u03BC G2", "\u03C3^2 G2", 
	"\u03BC G3", "\u03C3^2 G3",
	"\u03BC B4", "\u03C3^2 B4",
]

RAW_DATA_HEADERS = [
	"Name", "Session" ,
	"Raw \u03BC R1", "Raw \u03C3^2 R1", 
	"Raw \u03BC G2", "Raw \u03C3^2 G2", 
	"Raw \u03BC G3", "Raw \u03C3^2 G3",
	"Raw \u03BC B4", "Raw \u03C3^2 B4",
]

DARK_DATA_HEADERS = [
	"Name", "Session" ,
	"Dark \u03BC R1", "Dark \u03C3^2 R1", 
	"Dark \u03BC G2", "Dark \u03C3^2 G2", 
	"Dark \u03BC G3", "Dark \u03C3^2 G3",
	"Dark \u03BC B4", "Dark \u03C3^2 B4",
]

def view_session_count(cursor, session):
	row = {'session': session}
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		WHERE session = :session
		''', row)
	return cursor.fetchone()[0]


def view_all_count(cursor):
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		''')
	return cursor.fetchone()[0]

# --------------
# Image metadata
# --------------

def view_meta_exif_all_iterable(connection, session):
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT name, session, tstamp, model, exptime, iso, focal_length, f_number
		FROM image_t
		ORDER BY session DESC, name ASC
		''')
	return cursor, count


def view_meta_exif_session_iterable(connection, session):
	'''session may be None for NULL'''
	row = {'session': session}
	cursor = connection.cursor()
	count = view_session_count(cursor, session)
	cursor.execute(
		'''
		SELECT name, session, tstamp, model, exptime, iso, focal_length, f_number
		FROM image_t
		WHERE session = :session
		ORDER BY name DESC
		''', row)
	return cursor, count

# ------------
# Image General
# -------------

def view_meta_global_all_iterable(connection, session):
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT name, type, session, observer, organization, email, location, roi
		FROM image_t
		ORDER BY session DESC
		''')
	return cursor, count


def view_meta_global_session_iterable(connection, session):
	'''session may be None for NULL'''
	row = {'session': session}
	cursor = connection.cursor()
	count = view_session_count(cursor, session)
	cursor.execute(
		'''
		SELECT name, type, session, observer, organization, email, location, roi
		FROM image_t
		WHERE session = :session
		ORDER BY name ASC
		''', row)
	return cursor, count

# -----------
# Image State
# -----------

def view_state_session_iterable(connection, session):
	row = {'session': session}
	cursor = connection.cursor()
	count = view_session_count(cursor, session)
	cursor.execute(
		'''
		SELECT name, session, type, s.label
		FROM image_t
		JOIN state_t AS s USING(state)
		WHERE session = :session
		ORDER BY session DESC, name ASC
		''', row)
	return cursor, count


def view_state_all_iterable(connection, session):
	row = {'session': session}
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT name, session, type, s.label
		FROM image_t
		JOIN state_t AS s USING(state)
		ORDER BY session DESC, name ASC
		''', row)
	return cursor, count

# -----------
# Image Data
# -----------

def view_data_session_iterable(connection, session):
	row = {'session': session}
	cursor = connection.cursor()
	count = view_session_count(cursor, session)
	cursor.execute(
		'''
		SELECT 
			name, session, 
			aver_signal_R1, vari_signal_R1,
			aver_signal_G2, vari_signal_G2,
			aver_signal_G3, vari_signal_G3,
			aver_signal_B4, vari_signal_B4
		FROM image_v
		WHERE session = :session
		ORDER BY name ASC
		''', row)
	return cursor, count


def view_data_all_iterable(connection, session):
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT 
			name, session,
			aver_signal_R1, vari_signal_R1,
			aver_signal_G2, vari_signal_G2,
			aver_signal_G3, vari_signal_G3,
			aver_signal_B4, vari_signal_B4
		FROM image_v
		ORDER BY session DESC, name ASC
		''', row)
	return cursor, count

# -------------
# Raw Image Data
# --------------

def view_raw_data_session_iterable(connection, session):
	row = {'session': session, 'light': LIGHT_FRAME, 'unknown': UNKNOWN}
	cursor = connection.cursor()
	count = view_session_count(cursor, session)
	cursor.execute(
		'''
		SELECT 
			name, session, 
			aver_raw_signal_R1, vari_raw_signal_R1,
			aver_raw_signal_G2, vari_raw_signal_G2,
			aver_raw_signal_G3, vari_raw_signal_G3,
			aver_raw_signal_B4, vari_raw_signal_B4
		FROM image_t
		WHERE session = :session
		AND ((type = :light) OR (type = :unknown))
		ORDER BY name ASC
		''', row)
	return cursor, count


def view_raw_data_all_iterable(connection, session):
	row = {'light': LIGHT_FRAME, 'unknown': UNKNOWN}
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT 
			name, session,
			aver_raw_signal_R1, vari_raw_signal_R1,
			aver_raw_signal_G2, vari_raw_signal_G2,
			aver_raw_signal_G3, vari_raw_signal_G3,
			aver_raw_signal_B4, vari_raw_signal_B4
		FROM image_t
		WHERE type = :type
		AND ((type = :light) OR (type = :unknown))
		ORDER BY session DESC, name ASC
		''', row)
	return cursor, count

# --------------
# Dark Image Data
# ---------------

def view_dark_data_session_iterable(connection, session):
	row = {'session': session}
	cursor = connection.cursor()
	count = view_session_count(cursor, session)
	cursor.execute(
		'''
		SELECT 
			name, session, 
			aver_dark_R1, vari_dark_R1,
			aver_dark_G2, vari_dark_G2,
			aver_dark_G3, vari_dark_G3,
			aver_dark_B4, vari_dark_B4
		FROM image_t
		WHERE session = :session
		ORDER BY name ASC
		''', row)
	return cursor, count


def view_dark_data_all_iterable(connection, session):
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT 
			name, session, 
			aver_dark_R1, vari_dark_R1,
			aver_dark_G2, vari_dark_G2,
			aver_dark_G3, vari_dark_G3,
			aver_dark_B4, vari_dark_B4
		FROM image_t
		ORDER BY session DESC, name ASC
		''', row)
	return cursor, count

# ----------------
# View Master Dark
# -----------------

def view_master_dark_all_iterable(connection, session):
	cursor = connection.cursor()
	cursor.execute("SELECT COUNT(*) FROM master_dark_t")
	count = cursor.fetchone()[0]
	cursor.execute(
		'''
		SELECT 
			session, N, roi            
			aver_R1, vari_R1,             
			aver_G2, vari_G2,         
			aver_G3, vari_G3,             
			aver_B4, vari_B4             
		FROM master_dark_t
		ORDER BY session DESC
		''')
	return cursor, count

def view_master_dark_session_iterable(connection, session):
	cursor = connection.cursor()
	row = {'session': session}
	cursor.execute("SELECT COUNT(*) FROM master_dark_t WHERE session = :session", row)
	count = cursor.fetchone()[0]
	cursor.execute(
		'''
		SELECT 
			session, N, roi,           
			(min_exptime == max_exptime) as good_flag,
			aver_R1, vari_R1,             
			aver_G2, vari_G2,         
			aver_G3, vari_G3,             
			aver_B4, vari_B4
		FROM master_dark_t
		WHERE session = :session
		''', row)
	return cursor, count

MASTER_DARK_HEADERS = [
	"Session", 
	"# Darks",
	"ROI",
	"Good?",
	"\u03BC R1", "\u03C3^2 R1", 
	"\u03BC G2", "\u03C3^2 G2", 
	"\u03BC G3", "\u03C3^2 G3",
	"\u03BC B4", "\u03C3^2 B4",
]


# ---------
# View Dark
# ----------

def view_dark_session_iterable(connection, session):
	row = {'session': session, 'type': DARK_FRAME}
	cursor = connection.cursor()
	count = view_session_count(cursor, session)
	cursor.execute(
		'''
		SELECT 
			name, session, 
			aver_raw_signal_R1, vari_raw_signal_R1,
			aver_raw_signal_G2, vari_raw_signal_G2,
			aver_raw_signal_G3, vari_raw_signal_G3,
			aver_raw_signal_B4, vari_raw_signal_B4
		FROM image_t
		WHERE session = :session
		AND type = :type
		ORDER BY name ASC
		''', row)
	return cursor, count


def view_dark_all_iterable(connection, session):
	row = {'session': session, 'type': DARK_FRAME}
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT 
			name, session,
			aver_raw_signal_R1, vari_raw_signal_R1,
			aver_raw_signal_G2, vari_raw_signal_G2,
			aver_raw_signal_G3, vari_raw_signal_G3,
			aver_raw_signal_B4, vari_raw_signal_B4
		FROM image_t
		WHERE type = :type
		ORDER BY session DESC, name ASC
		''', row)
	return cursor, count


def do_image_view(connection, session, iterable, headers, options):
	cursor, count = iterable(connection, session)
	paging(cursor, headers, maxsize=count, page_size=options.page_size)

# =====================
# Command esntry points
# =====================

# These display various data

def image_list(connection, options):
	session = latest_session(connection)
	if options.exif:
		headers = EXIF_HEADERS
		iterable = view_meta_exif_all_iterable if options.all else view_meta_exif_session_iterable
	elif options.generic:
		headers = GLOBAL_HEADERS
		iterable = view_meta_global_all_iterable if options.all else view_meta_global_session_iterable
	elif options.state:
		headers = STATE_HEADERS
		iterable = view_state_all_iterable if options.all else view_state_session_iterable
	elif options.data:
		headers = DATA_HEADERS
		iterable = view_data_all_iterable if options.all else view_data_session_iterable
	elif options.raw_data:
		headers = RAW_DATA_HEADERS
		iterable = view_raw_data_all_iterable if options.all else view_raw_data_session_iterable
	elif options.dark_data:
		headers = DARK_DATA_HEADERS
		iterable = view_dark_data_all_iterable if options.all else view_dark_data_session_iterable
	elif options.dark:
		headers = RAW_DATA_HEADERS
		iterable = view_dark_all_iterable if options.all else view_dark_session_iterable
	elif options.master:
		headers = MASTER_DARK_HEADERS
		iterable = view_master_dark_all_iterable if options.all else view_master_dark_session_iterable
	else:
		return
	do_image_view(connection, session, iterable, headers, options)


def image_export(connection, options):
	do_export_all(connection, options)
	

def do_image_reduce(connection, options):

	file_options = load_config_file(options.config)
	options      = merge_options(options, file_options)

	old_session = work_dir_to_session(connection, options.work_dir, options.filter)
	new_session = int(datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"))
	session = new_session if old_session is None else old_session
	log.info("==> Start reduction session, id = %d", session)
	# Step 1: registering
	do_register(connection, options.work_dir, options.filter, session)
	
	if options.reset:
		image_session_state_reset(connection, session)
	# Step 2
	do_stats(connection, session, options.work_dir, options)

	# Step 3
	#iterable = classify_all_iterable if options.all else classify_session_iterable
	do_classify(connection, session, options.work_dir, options)

	# Step 4
	do_apply_dark(connection, session, options)
	# Step 5
	#iterable = export_all_iterable if options.all else export_session_iterable
	#do_export(connection, session, iterable, options)
	do_export_work_dir(connection, session, options.work_dir, options)

	# Cleanup session stuff
	work_dir_cleanup(connection)


def do_image_multidir_reduce(connection, options):
	with os.scandir(options.work_dir) as it:
		dirs  = [ entry.path for entry in it if entry.is_dir() ]
		files = [ entry.path for entry in it if entry.is_file() ]
	if dirs:
		if files:
			log.warning("Ignoring files in %s", options.work_dir)
		for item in dirs:
			options.work_dir = item
			do_image_reduce(connection, options)
			time.sleep(1.5)
	else:
		do_image_reduce(connection, options)


def image_reduce(connection, options):
	if not options.multiuser:
		do_image_multidir_reduce(connection, options)
	else:
		# os.scandir() only available from Python 3.6   
		with os.scandir(options.work_dir) as it:
			dirs = [ (entry.name, entry.path) for entry in it if entry.is_dir() ]
		if dirs:
			for name, path in dirs:
				options.config   = os.path.join(AZOTEA_CFG_DIR, name + '.ini')
				options.work_dir = path
				try:
					do_image_multidir_reduce(connection, options)
				except IOError as e:
					log.warning("No %s.ini file, skipping observer", name)
		else:
			raise NoUserInfoError(options.work_dir)
