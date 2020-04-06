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
from .camimage import  CameraImage, CameraCache
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

class NoWorkDirectoryError(ValueError):
	'''No working directory specified.'''
	def __str__(self):
		s = self.__doc__
		if self.args:
			s = "{0} \nre-run '{1} --new --work-dir WORK_DIR'".format(s, self.args[0])
		s = '{0}.'.format(s)
		return s

# -----------------------
# Module global variables
# -----------------------

duplicated_file_paths = []

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

def myopen(name, *args):
	if sys.version_info[0] < 3:
		return open(name, *args)
	else:
		return open(name,  *args, newline='')


def already_in_database(connection):
	cursor = connection.cursor()
	cursor.execute("SELECT file_path FROM image_t")
	return [item[0] for item in cursor]


def candidates(directory, options):
	'''candidate list of images to be inserted in the database'''
	file_list = sorted(glob.glob(os.path.join(directory, options.filter)))
	logging.info("Found {0} candidate images".format(len(file_list)))
	return file_list


def insert_list(connection, directory, options):
	'''Returns the list of file mpaths that must be really inserted in the database'''
	return list(set(candidates(directory, options)) - set(already_in_database(connection)))


def classification_algorithm1(name, file_path, options):
	if name.upper().startswith(DARK_FRAME):
		result = {'name': name, 'type': DARK_FRAME}
	else:
		result = {'name': name, 'type': LIGHT_FRAME}
	return result


def batch_processed(connection, batch):
	row = {'batch': batch, 'state': RAW_STATS}
	cursor = connection.cursor()
	cursor.execute('''
		SELECT COUNT(*) 
		FROM image_t 
		WHERE state >= :state
		AND batch = :batch
		''',row)
	return cursor.fetchone()[0]

def master_dark_for(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	cursor.execute('''
		SELECT COUNT(*) 
		FROM master_dark_t
		WHERE batch = :batch
		''',row)
	return cursor.fetchone()[0]


def find_by_hash(connection, hash):
	row = {'hash': hash}
	cursor = connection.cursor()
	cursor.execute('''
		SELECT name, file_path
		FROM image_t 
		WHERE hash = :hash
		''',row)
	return cursor.fetchone()


def latest_batch(connection):
	'''Get Last recorded batch'''
	cursor = connection.cursor()
	cursor.execute('''
		SELECT MAX(batch)
		FROM image_t 
		''')
	return cursor.fetchone()[0]


# ------------------
# Database iterables
# ------------------






# ------------------
# Database inserters
# ------------------





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
				file_path, 
				batch, 
				observer, 
				organization,
				email, 
				location, 
				roi,
				tstamp, 
				model, 
				iso, 
				exposure,
				type,
				state
			) VALUES (
				:name, 
				:hash,
				:file_path, 
				:batch, 
				:observer, 
				:organization, 
				:email,
				:location,
				:roi,
				:tstamp, 
				:model, 
				:iso, 
				:exposure,
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
				file_path, 
				batch, 
				observer, 
				organization,
				email, 
				location, 
				roi,
				tstamp, 
				model, 
				iso, 
				exposure,
				type,
				state
			) VALUES (
				:name, 
				:hash,
				:file_path, 
				:batch, 
				:observer, 
				:organization,
				:email, 
				:location,
				:roi,
				:tstamp, 
				:model, 
				:iso, 
				:exposure,
				:type,
				:state
			)
			''', rows)
	connection.commit()


def register_preamble(connection, directory, batch, options):
	file_list = insert_list(connection, directory, options)
	logging.info("Registering {0} new images".format(len(file_list)))
	metadata = {
		'batch'       : batch, 
		'observer'    : options.observer, 
		'organization': options.organization,
		'email'       : options.email, 
		'location'    : options.location,
		'state'       : REGISTERED,
		'type'        : UNKNOWN,
	}
	return file_list, metadata

def register_slow(connection,  file_list, metadata, options):
	
	global duplicated_file_paths
	camera_cache = CameraCache(options.camera) 

	for file_path in file_list:
		image = CameraImage(file_path, camera_cache)
		exif_metadata = image.loadEXIF()
		metadata['file_path'] = file_path
		metadata['hash']      = image.hash()
		metadata['roi']       = str(options.roi)  # provisional
		row   = merge_two_dicts(metadata, exif_metadata)
		try:
			register_insert_image(connection, row)
		except sqlite3.IntegrityError as e:
			connection.rollback()
			name2, path2 = find_by_hash(connection, metadata['hash'])
			duplicated_file_paths.append({'original': path2, 'duplicated': metadata['file_path']})
			logging.warn("Duplicate => {0} EQUALS {1}".format(row['file_path'], path2))
		else:
			logging.info("{0} from {1} registered in database".format(row['name'], exif_metadata['model']))


def register_fast(connection, file_list, metadata, options):
	rows = []
	camera_cache = CameraCache(options.camera) 
	for file_path in file_list:
		image = CameraImage(file_path, camera_cache)
		image.setROI(options.roi)
		exif_metadata = image.loadEXIF()
		metadata['file_path'] = file_path
		metadata['hash']      = image.hash()
		metadata['roi']       = str(options.roi)  # provisional
		row   = merge_two_dicts(metadata, exif_metadata)
		rows.append(row)
		logging.info("{0} from {1} being registered in database".format(row['name'], exif_metadata['model']))
	try:
		register_insert_images(connection, rows)
	except sqlite3.IntegrityError as e:
		connection.rollback()
		raise
	else:
		logging.info("{0} new images registered in database".format(len(rows)))


def do_register(connection, directory, batch, options):
	file_list, metadata = register_preamble(connection, directory, batch, options)
	if options.slow:
		register_slow(connection, file_list, metadata, options)
	else:
		register_fast(connection, file_list, metadata, options)




# --------------
# Image Dark
# --------------



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


def classify_all_iterable(connection, batch):
	row = {'type': UNKNOWN}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name, file_path
		FROM image_t
		WHERE type = :type
		''',row)
	return cursor


def classify_batch_iterable(connection, batch):
	row = {'batch': batch, 'type': UNKNOWN}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name, file_path
		FROM image_t
		WHERE type = :type
		AND batch = :batch
		''', row)
	return cursor


def do_classyfy(connection, batch, src_iterable, options):
	rows = []
	for name, file_path in src_iterable(connection, batch):
		row = classification_algorithm1(name, file_path, options)
		logging.info("{0} is type {1}".format(name,row['type']))
		rows.append(row)
	if rows:
		classify_update_db(connection, rows)
	else:
		logging.info("No image type classification is needed")


# -----------
# Image Stats
# -----------

def stats_update_db(connection, rows):
	cursor = connection.cursor()
	cursor.executemany(
		'''
		UPDATE image_t
		SET state               = :state,
			roi                 = :roi, 
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

def stats_all_iterable(connection, batch):
	row = {'state': RAW_STATS}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name, file_path
		FROM image_t
		WHERE state < :state
		''', row)
	return cursor

def stats_batch_iterable(connection, batch):
	row = {'batch': batch, 'state': RAW_STATS}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name, file_path
		FROM image_t
		WHERE state < :state
		AND batch = :batch
		''', row)
	return cursor


def do_stats(connection, batch, src_iterable, options):
	camera_cache = CameraCache(options.camera)
	rows = []
	for name, file_path in src_iterable(connection, batch):
		image = CameraImage(file_path, camera_cache)
		image.setROI(options.roi)
		image.loadEXIF()    # we need to find out the camera model before reading
		image.read()
		row = image.stats()
		row['state'] = RAW_STATS
		rows.append(row)
	if rows:
		stats_update_db(connection, rows)
	else:
		logging.info("No image statistics to be computed")

# -----------------------------
# Image Apply Dark Substraction
# -----------------------------

def master_dark_db_update_all(connection, batch):
	row = {'type': DARK_FRAME, 'state': RAW_STATS}
	cursor = connection.cursor()
	cursor.execute(
		'''
		INSERT OR REPLACE INTO master_dark_t (
			batch, 
			roi, 
			N, 
			aver_R1, 
			aver_G2, 
			aver_G3, 
			aver_B4,
			vari_R1, 
			vari_G2, 
			vari_G3, 
			vari_B4
		)
		SELECT 
			batch, 
			MIN(roi), 
			COUNT(*), 
			AVG(aver_raw_signal_R1), 
			AVG(aver_raw_signal_G2), 
			AVG(aver_raw_signal_G3), 
			AVG(aver_raw_signal_B4),
			SUM(vari_raw_signal_R1)/COUNT(*),
			SUM(vari_raw_signal_G2)/COUNT(*),
			SUM(vari_raw_signal_G3)/COUNT(*),
			SUM(vari_raw_signal_B4)/COUNT(*)
		FROM image_t
		WHERE type = :type
		AND   state >= :state
		GROUP BY batch
		''', row)
	connection.commit()


def master_dark_all_batches_iterable(connection):
	cursor = connection.cursor()
	cursor.execute("SELECT batch from master_dark_t")
	return cursor;


def dark_update_columns(connection, batch):
	row = {'type': LIGHT_FRAME, 'batch': batch, 'state': RAW_STATS, 'new_state': DARK_SUBSTRACTED}
	cursor = connection.cursor()
	cursor.execute(
		'''
		UPDATE image_t
		SET
			state        = :new_state,
			aver_dark_R1 = (SELECT aver_R1 FROM master_dark_t WHERE batch = :batch),
			aver_dark_G2 = (SELECT aver_G2 FROM master_dark_t WHERE batch = :batch),
			aver_dark_G3 = (SELECT aver_G3 FROM master_dark_t WHERE batch = :batch),
			aver_dark_B4 = (SELECT aver_B4 FROM master_dark_t WHERE batch = :batch),
			vari_dark_R1 = (SELECT vari_R1 FROM master_dark_t WHERE batch = :batch),
			vari_dark_G2 = (SELECT vari_G2 FROM master_dark_t WHERE batch = :batch),
			vari_dark_G3 = (SELECT vari_G3 FROM master_dark_t WHERE batch = :batch),
			vari_dark_B4 = (SELECT vari_B4 FROM master_dark_t WHERE batch = :batch)
		WHERE batch = :batch
		AND   state BETWEEN :state AND :new_state
		AND   type  = :type
		''',row)
	connection.commit()


def do_apply_dark(connection, batch, options):
	master_dark_db_update_all(connection, batch)
	if options.all:
		logging.info("Applying dark substraction to all images")
		for batch, in master_dark_all_batches_iterable(connection):
			dark_update_columns(connection, batch)
	else:
		if master_dark_for(connection, batch):
			logging.info("Applying dark substraction to current batch")
			dark_update_columns(connection, batch)

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
			'exposure'       ,
			'aver_signal_R1' ,
			'std_signal_R1'  ,
			'aver_signal_G2' ,
			'std_signal_G2'  ,
			'aver_signal_G3' ,
			'std_signal_G3'  ,
			'aver_signal_B4' ,
			'std_signal_B4'  ,
		]

def export_batch_iterable(connection, batch):
	row = {'batch': batch, 'state': RAW_STATS, 'type': LIGHT_FRAME}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT  batch,
				observer,
				organization,
				email,
				location,
				type,
				tstamp, 
				name, 
				model, 
				iso, 
				roi,
				dark_roi,
				exposure, 
				aver_signal_R1, 
				vari_signal_R1, -- Array index 14
				aver_signal_G2, 
				vari_signal_G2, -- Array index 16
				aver_signal_G3, 
				vari_signal_G3, -- Array index 18
				aver_signal_B4, 
				vari_signal_B4  -- Array index 20
		FROM image_v
		WHERE state >= :state
		AND   type = :type
		AND   batch = :batch
		''', row)
	return cursor

def export_all_iterable(connection, batch):
	row = {'state': RAW_STATS, 'type': LIGHT_FRAME}
	cursor = connection.cursor()
	cursor.execute(
		'''
	   SELECT   batch,
				observer,
				organization,
				email,
				location,
				type,
				tstamp, 
				name, 
				model, 
				iso, 
				roi,
				dark_roi,
				exposure, 
				aver_signal_R1, 
				vari_signal_R1, -- Array index 14
				aver_signal_G2, 
				vari_signal_G2, -- Array index 16
				aver_signal_G3, 
				vari_signal_G3, -- Array index 18
				aver_signal_B4, 
				vari_signal_B4  -- Array index 20
		FROM image_v
		WHERE state >= :state
		AND   type = :type
		''', row)
	return cursor


def var2std(item):
	'''From vraiance to StdDev in seevral columns'''
	index, value = item
	return round(math.sqrt(value),1) if index in [14, 16, 18, 20] else value


def do_export(connection, batch, src_iterable, options):
	fieldnames = ["batch","observer","organization", "email","location", "type"]
	fieldnames.extend(VIEW_HEADERS)
	if options.all:
		with myopen(options.global_csv_file, 'w') as csvfile:
			writer = csv.writer(csvfile, delimiter=';')
			writer.writerow(fieldnames)
			for row in src_iterable(connection, batch):
				row = map(var2std, enumerate(row))
				writer.writerow(row)
		logging.info("Saved data to global CSV file {0}".format(options.global_csv_file))
	elif batch_processed(connection, batch):
		# Write a batch CSV file
		batch_csv_file = os.path.join(AZOTEA_BASE_DIR, str(batch) + '.csv')
		with myopen(batch_csv_file, 'w') as csvfile:
			writer = csv.writer(csvfile, delimiter=';')
			writer.writerow(fieldnames)
			for row in src_iterable(connection, batch):
				row = map(var2std, enumerate(row))
				writer.writerow(row)
		logging.info("Saved data to batch  CSV file {0}".format(batch_csv_file))
	else:
		logging.info("No new CSV file generation")
	
	

# ==================================
# Image List subcommands and options
# ==================================


EXIF_HEADERS = [
	'Name',
	'Batch',
	'Timestamp',
	'Model',
	'Exposure',
	'ISO',
]

GLOBAL_HEADERS = [
	'Name',
	'Type',
	'Batch',
	'Observer',
	'Organiztaion',
	'Location',
	'ROI',
]

STATE_HEADERS = [
	"Name",
	"Batch",
	"Type", 
	"State",
]

DATA_HEADERS = [
	"Name", "Batch",
	"\u03BC R1", "\u03C3^2 R1", 
	"\u03BC G2", "\u03C3^2 G2", 
	"\u03BC G3", "\u03C3^2 G3",
	"\u03BC B4", "\u03C3^2 B4",
]

RAW_DATA_HEADERS = [
	"Name", "Batch" ,
	"Raw \u03BC R1", "Raw \u03C3^2 R1", 
	"Raw \u03BC G2", "Raw \u03C3^2 G2", 
	"Raw \u03BC G3", "Raw \u03C3^2 G3",
	"Raw \u03BC B4", "Raw \u03C3^2 B4",
]

DARK_DATA_HEADERS = [
	"Name", "Batch" ,
	"Dark \u03BC R1", "Dark \u03C3^2 R1", 
	"Dark \u03BC G2", "Dark \u03C3^2 G2", 
	"Dark \u03BC G3", "Dark \u03C3^2 G3",
	"Dark \u03BC B4", "Dark \u03C3^2 B4",
]

def view_batch_count(cursor, batch):
	row = {'batch': batch}
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		WHERE batch = :batch
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

def view_meta_exif_all_iterable(connection, batch):
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT name, batch, tstamp, model, exposure, iso
		FROM image_t
		ORDER BY batch DESC, name ASC
		''')
	return cursor, count


def view_meta_exif_batch_iterable(connection, batch):
	'''batch may be None for NULL'''
	row = {'batch': batch}
	cursor = connection.cursor()
	count = view_batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT name, batch, tstamp, model, exposure, iso
		FROM image_t
		WHERE batch = :batch
		ORDER BY name DESC
		''', row)
	return cursor, count

# ------------
# Image General
# -------------

def view_meta_global_all_iterable(connection, batch):
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT name, type, batch, observer, organization, email, location, roi
		FROM image_t
		ORDER BY batch DESC
		''')
	return cursor, count


def view_meta_global_batch_iterable(connection, batch):
	'''batch may be None for NULL'''
	row = {'batch': batch}
	cursor = connection.cursor()
	count = view_batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT name, type, batch, observer, organization, email, location, roi
		FROM image_t
		WHERE batch = :batch
		ORDER BY name ASC
		''', row)
	return cursor, count

# -----------
# Image State
# -----------

def view_state_batch_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	count = view_batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT name, batch, type, s.label
		FROM image_t
		JOIN state_t AS s USING(state)
		WHERE batch = :batch
		ORDER BY batch DESC, name ASC
		''', row)
	return cursor, count


def view_state_all_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT name, batch, type, s.label
		FROM image_t
		JOIN state_t AS s USING(state)
		ORDER BY batch DESC, name ASC
		''', row)
	return cursor, count

# -----------
# Image Data
# -----------

def view_data_batch_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	count = view_batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT 
			name, batch, 
			aver_signal_R1, vari_signal_R1,
			aver_signal_G2, vari_signal_G2,
			aver_signal_G3, vari_signal_G3,
			aver_signal_B4, vari_signal_B4
		FROM image_v
		WHERE batch = :batch
		ORDER BY name ASC
		''', row)
	return cursor, count


def view_data_all_iterable(connection, batch):
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT 
			name, batch,
			aver_signal_R1, vari_signal_R1,
			aver_signal_G2, vari_signal_G2,
			aver_signal_G3, vari_signal_G3,
			aver_signal_B4, vari_signal_B4
		FROM image_v
		ORDER BY batch DESC, name ASC
		''', row)
	return cursor, count

# -------------
# Raw Image Data
# --------------

def view_raw_data_batch_iterable(connection, batch):
	row = {'batch': batch, 'light': LIGHT_FRAME, 'unknown': UNKNOWN}
	cursor = connection.cursor()
	count = view_batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT 
			name, batch, 
			aver_raw_signal_R1, vari_raw_signal_R1,
			aver_raw_signal_G2, vari_raw_signal_G2,
			aver_raw_signal_G3, vari_raw_signal_G3,
			aver_raw_signal_B4, vari_raw_signal_B4
		FROM image_t
		WHERE batch = :batch
		AND ((type = :light) OR (type = :unknown))
		ORDER BY name ASC
		''', row)
	return cursor, count


def view_raw_data_all_iterable(connection, batch):
	row = {'light': LIGHT_FRAME, 'unknown': UNKNOWN}
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT 
			name, batch,
			aver_raw_signal_R1, vari_raw_signal_R1,
			aver_raw_signal_G2, vari_raw_signal_G2,
			aver_raw_signal_G3, vari_raw_signal_G3,
			aver_raw_signal_B4, vari_raw_signal_B4
		FROM image_t
		WHERE type = :type
		AND ((type = :light) OR (type = :unknown))
		ORDER BY batch DESC, name ASC
		''', row)
	return cursor, count

# --------------
# Dark Image Data
# ---------------

def view_dark_data_batch_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	count = view_batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT 
			name, batch, 
			aver_dark_R1, vari_dark_R1,
			aver_dark_G2, vari_dark_G2,
			aver_dark_G3, vari_dark_G3,
			aver_dark_B4, vari_dark_B4
		FROM image_t
		WHERE batch = :batch
		ORDER BY name ASC
		''', row)
	return cursor, count


def view_dark_data_all_iterable(connection, batch):
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT 
			name, batch, 
			aver_dark_R1, vari_dark_R1,
			aver_dark_G2, vari_dark_G2,
			aver_dark_G3, vari_dark_G3,
			aver_dark_B4, vari_dark_B4
		FROM image_t
		ORDER BY batch DESC, name ASC
		''', row)
	return cursor, count

# ----------------
# View Master Dark
# -----------------

def view_master_dark_all_iterable(connection, batch):
	cursor = connection.cursor()
	cursor.execute("SELECT COUNT(*) FROM master_dark_t")
	count = cursor.fetchone()[0]
	cursor.execute(
		'''
		SELECT 
			batch, N, roi            
			aver_R1, vari_R1,             
			aver_G2, vari_G2,         
			aver_G3, vari_G3,             
			aver_B4, vari_B4             
		FROM master_dark_t
		ORDER BY batch DESC
		''')
	return cursor, count

def view_master_dark_batch_iterable(connection, batch):
	cursor = connection.cursor()
	row = {'batch': batch}
	cursor.execute("SELECT COUNT(*) FROM master_dark_t WHERE batch = :batch", row)
	count = cursor.fetchone()[0]
	cursor.execute(
		'''
		SELECT 
			batch, N, roi             
			aver_R1, vari_R1,             
			aver_G2, vari_G2,         
			aver_G3, vari_G3,             
			aver_B4, vari_B4
		FROM master_dark_t
		WHERE batch = :batch
		''', row)
	return cursor, count

MASTER_DARK_HEADERS = [
	"Batch", 
	"# Darks",
	"ROI",
	"\u03BC R1", "\u03C3^2 R1", 
	"\u03BC G2", "\u03C3^2 G2", 
	"\u03BC G3", "\u03C3^2 G3",
	"\u03BC B4", "\u03C3^2 B4",
]


# ---------
# View Dark
# ----------

def view_dark_batch_iterable(connection, batch):
	row = {'batch': batch, 'type': DARK_FRAME}
	cursor = connection.cursor()
	count = view_batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT 
			name, batch, 
			aver_raw_signal_R1, vari_raw_signal_R1,
			aver_raw_signal_G2, vari_raw_signal_G2,
			aver_raw_signal_G3, vari_raw_signal_G3,
			aver_raw_signal_B4, vari_raw_signal_B4
		FROM image_t
		WHERE batch = :batch
		AND type = :type
		ORDER BY name ASC
		''', row)
	return cursor, count


def view_dark_all_iterable(connection, batch):
	row = {'batch': batch, 'type': DARK_FRAME}
	cursor = connection.cursor()
	count = view_all_count(cursor)
	cursor.execute(
		'''
		SELECT 
			name, batch,
			aver_raw_signal_R1, vari_raw_signal_R1,
			aver_raw_signal_G2, vari_raw_signal_G2,
			aver_raw_signal_G3, vari_raw_signal_G3,
			aver_raw_signal_B4, vari_raw_signal_B4
		FROM image_t
		WHERE type = :type
		ORDER BY batch DESC, name ASC
		''', row)
	return cursor, count


def do_image_view(connection, batch, iterable, headers, options):
	cursor, count = iterable(connection, batch)
	paging(cursor, headers, maxsize=count, page_size=options.page_size)

# =====================
# Command esntry points
# =====================

# These display various data

def image_list(connection, options):
	batch = latest_batch(connection)
	if options.exif:
		headers = EXIF_HEADERS
		iterable = view_meta_exif_all_iterable if options.all else view_meta_exif_batch_iterable
	elif options.generic:
		headers = GLOBAL_HEADERS
		iterable = view_meta_global_all_iterable if options.all else view_meta_global_batch_iterable
	elif options.state:
		headers = STATE_HEADERS
		iterable = view_state_all_iterable if options.all else view_state_batch_iterable
	elif options.data:
		headers = DATA_HEADERS
		iterable = view_data_all_iterable if options.all else view_data_batch_iterable
	elif options.raw_data:
		headers = RAW_DATA_HEADERS
		iterable = view_raw_data_all_iterable if options.all else view_raw_data_batch_iterable
	elif options.dark_data:
		headers = DARK_DATA_HEADERS
		iterable = view_dark_data_all_iterable if options.all else view_dark_data_batch_iterable
	elif options.dark:
		headers = RAW_DATA_HEADERS
		iterable = view_dark_all_iterable if options.all else view_dark_batch_iterable
	elif options.master:
		headers = MASTER_DARK_HEADERS
		iterable = view_master_dark_all_iterable if options.all else view_master_dark_batch_iterable
	else:
		return
	do_image_view(connection, batch, iterable, headers, options)


# These are the pipelien stages in execution order

def image_register(connection, options):
	if options.new:
		batch = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
	else:
		batch = latest_batch(connection)
		if batch is None:
			raise NoBatchError("image regiter")
	do_register(connection, options.work_dir, batch, options)


def image_classify(connection, options):
	batch = latest_batch(connection)
	iterable = classify_all_iterable if options.all else classify_batch_iterable
	do_classyfy(connection, batch, classify_batch_iterable, options)


def image_stats(connection, options):
	batch = latest_batch(connection)
	iterable = stats_all_iterable if options.all else stats_batch_iterable
	do_stats(connection, batch, iterable, options)


def image_dark(connection, options):
	batch = latest_batch(connection)
	do_apply_dark(connection, batch, options)


def image_export(connection, options):
	batch = latest_batch(connection)
	iterable = export_all_iterable if options.all else export_batch_iterable
	do_export(connection, batch, iterable, options)


def image_reduce(connection, options):
	# Step 1 is a bit tricky in the generic pipeline
	if options.new and not options.work_dir:
		raise NoWorkDirectoryError("image reduce")
	if not options.all and not options.work_dir:
		raise NoWorkDirectoryError("image reduce")

	if options.new:
		batch = int(datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"))
	else:
		batch = latest_batch(connection)
		if batch is None:
			raise NoBatchError("image reduce")

	if not options.all:
		do_register(connection, options.work_dir, batch, options)
	
	# Step 2
	iterable = stats_all_iterable if options.all else stats_batch_iterable
	do_stats(connection, batch, iterable, options)

	# Step 3
	iterable = classify_all_iterable if options.all else classify_batch_iterable
	do_classyfy(connection, batch, iterable, options)

	# Step 4
	do_apply_dark(connection, batch, options)
	# Step 5
	iterable = export_all_iterable if options.all else export_batch_iterable
	do_export(connection, batch, iterable, options)
