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

from .         import AZOTEA_DIR
from .camimage import  CameraImage
from .utils    import merge_two_dicts, paging


# ----------------
# Module constants
# ----------------

# values for the 'state' column in table

REGISTERED       = "REGISTERED"
CLASSIFIED       = "CLASSIFIED"
RAW_STATS        = "RAW STATS"
DARK_SUBSTRACTED = "DARK SUBSTRACTED"

LIGHT_FRAME = "LIGHT"
DARK_FRAME  = "DARK"
UNKNOWN     = "UNKNOWN"

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
	file_list = glob.glob(directory + '/' + options.filter)
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
	row = {'batch': batch}
	cursor = connection.cursor()
	cursor.execute('''
		SELECT COUNT(*) 
		FROM image_t 
		WHERE state IS NOT NULL
		AND batch = :batch
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

def insert_new_image(connection, row):
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

def insert_new_images(connection, rows):
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



def db_update_type(connection, rows):
	cursor = connection.cursor()
	cursor.executemany(
		'''
		UPDATE image_t
		SET type = :type, state = :state
		WHERE name = :name
		''', rows)
	connection.commit()


def db_update_stats(connection, rows):
	cursor = connection.cursor()
	cursor.executemany(
		'''
		UPDATE image_t
		SET state               = :state,
			roi                 = :roi, 
			mean_raw_signal_R1  = :mean_raw_signal_R1, 
			mean_raw_signal_G2  = :mean_raw_signal_G2, 
			mean_raw_signal_G3  = :mean_raw_signal_G3,
			mean_raw_signal_B4  = :mean_raw_signal_B4,
			vari_raw_signal_R1  = :vari_raw_signal_R1,
			vari_raw_signal_G2  = :vari_raw_signal_G2,
			vari_raw_signal_G3  = :vari_raw_signal_G3,
			vari_raw_signal_B4  = :vari_raw_signal_B4 
		WHERE name = :name
		''', rows)
	connection.commit()

# --------------
# Image Register
# --------------

		 
def image_register_preamble(connection, directory, batch, options):
	file_list = insert_list(connection, directory, options)
	logging.info("Registering {0} new images".format(len(file_list)))
	metadata = {
		'batch'       : batch, 
		'observer'    : options.observer, 
		'organization': options.organization, 
		'location'    : options.location,
		'state'       : REGISTERED,
		'type'        : UNKNOWN,
	}
	return file_list, metadata

def image_register_slow(connection,  file_list, metadata, options):
	
	global duplicated_file_paths 

	for file_path in file_list:
		image = CameraImage(file_path, options)
		exif_metadata = image.loadEXIF()
		metadata['file_path'] = file_path
		metadata['hash']      = image.hash()
		metadata['roi']       = str(options.roi)  # provisional
		row   = merge_two_dicts(metadata, exif_metadata)
		try:
			insert_new_image(connection, row)
		except sqlite3.IntegrityError as e:
			connection.rollback()
			name2, path2 = find_by_hash(connection, metadata['hash'])
			duplicated_file_paths.append({'original': path2, 'duplicated': metadata['file_path']})
			logging.warn("{0} is duplicate of {1}".format(row['file_path'], path2))
		else:
			logging.info("{0} registered in database".format(row['name']))


def image_register_fast(connection, file_list, metadata, options):
	rows = []
	for file_path in file_list:
		image = CameraImage(file_path, options)
		exif_metadata = image.loadEXIF()
		metadata['file_path'] = file_path
		metadata['hash']      = image.hash()
		metadata['roi']       = str(options.roi)  # provisional
		row   = merge_two_dicts(metadata, exif_metadata)
		rows.append(row)
		logging.info("{0} registering in database".format(row['name']))
	try:
		insert_new_images(connection, rows)
	except sqlite3.IntegrityError as e:
		connection.rollback()
		logging.error("Detected duplicated images. Re-run with --slow option to find out which")
		raise
	else:
		logging.info("{0} new images registered in database".format(len(rows)))


def do_image_register(connection, directory, batch, options):
	file_list, metadata = image_register_preamble(connection, directory, batch, options)
	if options.slow:
		image_register_slow(connection, file_list, metadata, options)
	else:
		image_register_fast(connection, file_list, metadata, options)




# --------------
# Image Dark
# --------------





# --------------
# Image Classify
# --------------

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


def do_image_classify(connection, batch, src_iterable, options):
	rows = []
	for name, file_path in src_iterable(connection, batch):
		row = classification_algorithm1(name, file_path, options)
		row['state'] = CLASSIFIED
		logging.info("{0} is type {1}".format(name,row['type']))
		rows.append(row)
	if rows:
		db_update_type(connection, rows)
	else:
		logging.info("No image type classification is needed")


# -----------
# Image Stats
# -----------


def stats_all_iterable(connection, batch):
	row = {'state': CLASSIFIED}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name, file_path
		FROM image_t
		WHERE state = :state
		''', row)
	return cursor

def stats_batch_iterable(connection, batch):
	row = {'batch': batch, 'state': CLASSIFIED}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name, file_path
		FROM image_t
		WHERE state = :state
		AND batch = :batch
		''', row)
	return cursor


def do_image_stats(connection, batch, src_iterable, options):
	rows = []
	for name, file_path in src_iterable(connection, batch):
		image = CameraImage(file_path, options)
		image.extended(options.extended)
		image.loadEXIF()    # we need to find out the camera model before reading
		image.read()
		row = image.stats()
		row['state'] = RAW_STATS
		rows.append(row)
	if rows:
		db_update_stats(connection, rows)
	else:
		logging.info("No image statistics to be computed")

# -----------------------------
# Image Apply Dark Substraction
# -----------------------------

def db_update_all_master_dark(connection, batch):
	row = {'type': DARK_FRAME, 'state': RAW_STATS}
	cursor = connection.cursor()
	cursor.execute(
		'''
		INSERT OR REPLACE INTO master_dark_t (
			batch, 
			roi, 
			N, 
			mean_R1, 
			mean_G2, 
			mean_G3, 
			mean_B4,
			vari_R1, 
			vari_G2, 
			vari_G3, 
			vari_B4
		)
		SELECT 
			batch, 
			MIN(roi), 
			COUNT(*), 
			AVG(mean_raw_signal_R1), 
			AVG(mean_raw_signal_G2), 
			AVG(mean_raw_signal_G3), 
			AVG(mean_raw_signal_B4),
			SUM(vari_raw_signal_R1)/COUNT(*),
			SUM(vari_raw_signal_G2)/COUNT(*),
			SUM(vari_raw_signal_G3)/COUNT(*),
			SUM(vari_raw_signal_B4)/COUNT(*)
		FROM image_t
		WHERE type = :type
		AND   state = :state
		GROUP BY batch
		''', row)
	connection.commit()



def db_update_dark_columns(connection, batch):
	row = {'type': LIGHT_FRAME, 'batch': batch, 'state': RAW_STATS, 'new_state': DARK_SUBSTRACTED}
	cursor = connection.cursor()
	cursor.execute(
		'''
		UPDATE image_t
		SET mean_dark_R1 = (SELECT mean_R1 FROM master_dark_t WHERE batch = :batch)
		WHERE batch = :batch
		AND   state = :state
		AND   type  = :type
		''',row)
	cursor.execute(
		'''
		UPDATE image_t
		SET mean_dark_G2 = (SELECT mean_G2 FROM master_dark_t WHERE batch = :batch)
		WHERE batch = :batch
		AND   state = :state
		AND   type  = :type
		''',row)
	cursor.execute(
		'''
		UPDATE image_t
		SET mean_dark_G3 = (SELECT mean_G3 FROM master_dark_t WHERE batch = :batch)
		WHERE batch = :batch
		AND   state = :state
		AND   type  = :type
		''',row)
	cursor.execute(
		'''
		UPDATE image_t
		SET mean_dark_B4 = (SELECT mean_B4 FROM master_dark_t WHERE batch = :batch)
		WHERE batch = :batch
		AND   state = :state
		AND   type  = :type
		''',row)
	cursor.execute(
		'''
		UPDATE image_t
		SET vari_dark_R1 = (SELECT vari_R1 FROM master_dark_t WHERE batch = :batch)
		WHERE batch = :batch
		AND   state = :state
		AND   type  = :type
		''',row)
	cursor.execute(
		'''
		UPDATE image_t
		SET vari_dark_G2 = (SELECT vari_G2 FROM master_dark_t WHERE batch = :batch)
		WHERE batch = :batch
		AND   state = :state
		AND   type  = :type
		''',row)
	cursor.execute(
		'''
		UPDATE image_t
		SET vari_dark_G3 = (SELECT vari_G3 FROM master_dark_t WHERE batch = :batch)
		WHERE batch = :batch
		AND   state = :state
		AND   type  = :type
		''',row)
	cursor.execute(
		'''
		UPDATE image_t
		SET vari_dark_B4 = (SELECT vari_B4 FROM master_dark_t WHERE batch = :batch)
		WHERE batch = :batch
		AND   state = :state
		AND   type  = :type
		''',row)
	cursor.execute(
		'''
		UPDATE image_t
		SET   state = :new_state
		WHERE batch = :batch
		AND   state = :state
		AND   type  = :type
		''',row)
	connection.commit()


def master_dark_all_batches_iterable(connection):
	cursor = connection.cursor()
	cursor.execute("SELECT batch from master_dark_t")
	return cursor;


def do_image_apply_dark(connection, batch, options):
	logging.info("Updating master darks for all batches")
	db_update_all_master_dark(connection, batch)
	if options.all:
		logging.info("Appling dark substraction to all images")
		for batch, in master_dark_all_batches_iterable(connection):
			db_update_dark_columns(connection, batch)
	else:
		logging.info("Appling dark substraction to current batch")
		db_update_dark_columns(connection, batch)

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
			'mean_signal_R1' ,
			'std_signal_R1'  ,
			'mean_signal_G2' ,
			'std_signal_G2'  ,
			'mean_signal_G3' ,
			'std_signal_G3'  ,
			'mean_signal_B4' ,
			'std_signal_B4'  ,
		]

def export_batch_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT  batch,
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
				exposure, 
				mean_signal_R1, 
				vari_signal_R1, 
				mean_signal_G2, 
				vari_signal_G2, 
				mean_signal_G3, 
				vari_signal_G3, 
				mean_signal_B4, 
				vari_signal_B4
		FROM image_v
		WHERE state IS NOT NULL
		AND   batch = :batch
		''', row)
	return cursor

def export_all_iterable(connection, batch):
	cursor = connection.cursor()
	cursor.execute(
		'''
	   SELECT   batch,
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
				exposure, 
				mean_signal_R1, 
				vari_signal_R1, 
				mean_signal_G2, 
				vari_signal_G2, 
				mean_signal_G3, 
				vari_signal_G3, 
				mean_signal_B4, 
				vari_signal_B4
		FROM image_v
		WHERE state IS NOT NULL
		''')
	return cursor


def var2std(item):
	'''From vraiance to StdDev in seevral columns'''
	index, value = item
	return round(math.sqrt(value),1) if index in [13, 15, 17, 19] else value


def do_image_export(connection, batch, src_iterable, options):
	fieldnames = ["batch","observer","organization","location", "type"]
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
		batch_csv_file = os.path.join(AZOTEA_DIR, batch + '.csv')
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
# Image View sumcommands and options
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
	"Raw \u03BC R1", "Raw \u03C3^2 R1", 
	"Raw \u03BC G2", "Raw \u03C3^2 G2", 
	"Raw \u03BC G3", "Raw \u03C3^2 G3",
	"Raw \u03BC B4", "Raw \u03C3^2 B4",
]

def batch_count(cursor, batch):
	row = {'batch': batch}
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		WHERE batch = :batch
		''', row)
	return cursor.fetchone()[0]


def all_count(cursor):
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		''')
	return cursor.fetchone()[0]

# --------------
# Image metadata
# --------------

def metadata_exif_all_iterable(connection, batch):
	cursor = connection.cursor()
	count = all_count(cursor)
	cursor.execute(
		'''
		SELECT name, batch, tstamp, model, exposure, iso
		FROM image_t
		ORDER BY batch DESC, name ASC
		''')
	return cursor, count


def metadata_exif_batch_iterable(connection, batch):
	'''batch may be None for NULL'''
	row = {'batch': batch}
	cursor = connection.cursor()
	count = batch_count(cursor, batch)
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

def metadata_global_all_iterable(connection, batch):
	cursor = connection.cursor()
	count = all_count(cursor)
	cursor.execute(
		'''
		SELECT name, type, batch, observer, organization, location, roi
		FROM image_t
		ORDER BY batch DESC
		''')
	return cursor, count


def metadata_global_batch_iterable(connection, batch):
	'''batch may be None for NULL'''
	row = {'batch': batch}
	cursor = connection.cursor()
	count = batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT name, type, batch, observer, organization, location, roi
		FROM image_t
		WHERE batch = :batch
		ORDER BY name ASC
		''', row)
	return cursor, count

# -----------
# Image State
# -----------

def image_state_batch_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	count = batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT name, batch, type, state
		FROM image_t
		WHERE batch = :batch
		ORDER BY batch DESC, name ASC
		''', row)
	return cursor, count


def image_state_all_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	count = all_count(cursor)
	cursor.execute(
		'''
		SELECT name, batch, type, state
		FROM image_t
		ORDER BY batch DESC, name ASC
		''', row)
	return cursor, count

# -----------
# Image Data
# -----------

def image_data_batch_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	count = batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT 
			name, batch, 
			mean_signal_R1, vari_signal_R1,
			mean_signal_G2, vari_signal_G2,
			mean_signal_G3, vari_signal_G3,
			mean_signal_B4, vari_signal_B4
		FROM image_v
		WHERE batch = :batch
		ORDER BY name ASC
		''', row)
	return cursor, count


def image_data_all_iterable(connection, batch):
	cursor = connection.cursor()
	count = all_count(cursor)
	cursor.execute(
		'''
		SELECT 
			name, batch,
			mean_signal_R1, vari_signal_R1,
			mean_signal_G2, vari_signal_G2,
			mean_signal_G3, vari_signal_G3,
			mean_signal_B4, vari_signal_B4
		FROM image_v
		ORDER BY batch DESC, name ASC
		''', row)
	return cursor, count

# -------------
# Raw Image Data
# --------------

def image_raw_data_batch_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	count = batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT 
			name, batch, 
			mean_raw_signal_R1, vari_raw_signal_R1,
			mean_raw_signal_G2, vari_raw_signal_G2,
			mean_raw_signal_G3, vari_raw_signal_G3,
			mean_raw_signal_B4, vari_raw_signal_B4
		FROM image_t
		WHERE batch = :batch
		ORDER BY name ASC
		''', row)
	return cursor, count


def image_raw_data_all_iterable(connection, batch):
	cursor = connection.cursor()
	count = all_count(cursor)
	cursor.execute(
		'''
		SELECT 
			name, batch,
			mean_raw_signal_R1, vari_raw_signal_R1,
			mean_raw_signal_G2, vari_raw_signal_G2,
			mean_raw_signal_G3, vari_raw_signal_G3,
			mean_raw_signal_B4, vari_raw_signal_B4
		FROM image_t
		ORDER BY batch DESC, name ASC
		''', row)
	return cursor, count

# --------------
# Dark Image Data
# ---------------

def image_dark_data_batch_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	count = batch_count(cursor, batch)
	cursor.execute(
		'''
		SELECT 
			name, batch, 
			mean_dark_R1, vari_dark_R1,
			mean_dark_G2, vari_dark_G2,
			mean_dark_G3, vari_dark_G3,
			mean_dark_B4, vari_dark_B4
		FROM image_t
		WHERE batch = :batch
		ORDER BY name ASC
		''', row)
	return cursor, count


def image_dark_data_all_iterable(connection, batch):
	cursor = connection.cursor()
	count = all_count(cursor)
	cursor.execute(
		'''
		SELECT 
			name, batch, 
			mean_dark_R1, vari_dark_R1,
			mean_dark_G2, vari_dark_G2,
			mean_dark_G3, vari_dark_G3,
			mean_dark_B4, vari_dark_B4
		FROM image_t
		ORDER BY batch DESC, name ASC
		''', row)
	return cursor, count

				  
def naster_dark_all_iterable(connection, batch):
	cursor = connection.cursor()
	cursor.execute("SELECT COUNT(*) FROM master_dark_t")
	count = cursor.fetchone()[0]
	cursor.execute(
		'''
		SELECT 
			batch,              
			mean_R1, vari_R1,             
			mean_G2, vari_G2,         
			mean_G3, vari_G3,             
			mean_B4, vari_B4,             
			roi, N
		FROM master_dark_t
		ORDER BY batch DESC
		''')
	return cursor, count

def master_dark_batch_iterable(connection, batch):
	cursor = connection.cursor()
	row = {'batch': batch}
	cursor.execute("SELECT COUNT(*) FROM master_dark_t WHERE batch = :batch", row)
	count = cursor.fetchone()[0]
	cursor.execute(
		'''
		SELECT 
			batch,              
			mean_R1, vari_R1,             
			mean_G2, vari_G2,         
			mean_G3, vari_G3,             
			mean_B4, vari_B4,             
			roi, N
		FROM master_dark_t
		WHERE batch = :batch
		''', row)
	return cursor, count

MASTER_DARK_HEADERS = [
	"Batch", 
	"\u03BC R1", "\u03C3^2 R1", 
	"\u03BC G2", "\u03C3^2 G2", 
	"\u03BC G3", "\u03C3^2 G3",
	"\u03BC B4", "\u03C3^2 B4",
	"ROI",
	"# Darks",
]


def do_image_view(connection, batch, iterable, headers, options):
	cursor, count = iterable(connection, batch)
	paging(cursor, headers, maxsize=count, page_size=options.page_size)

# =====================
# Command esntry points
# =====================

# These display various data

def image_view(connection, options):
	batch = latest_batch(connection)
	if options.exif:
		headers = EXIF_HEADERS
		iterable = metadata_exif_all_iterable if options.all else metadata_exif_batch_iterable
	elif options.general:
		headers = GLOBAL_HEADERS
		iterable = metadata_global_all_iterable if options.all else metadata_global_batch_iterable
	elif options.state:
		headers = STATE_HEADERS
		iterable = image_state_all_iterable if options.all else image_state_batch_iterable
	elif options.data:
		headers = DATA_HEADERS
		iterable = image_data_all_iterable if options.all else image_data_batch_iterable
	elif options.raw_data:
		headers = RAW_DATA_HEADERS
		iterable = image_raw_data_all_iterable if options.all else image_raw_data_batch_iterable
	elif options.dark:
		headers = DARK_DATA_HEADERS
		iterable = image_dark_data_all_iterable if options.all else image_dark_data_batch_iterable
	elif options.master:
		headers = MASTER_DARK_HEADERS
		iterable = naster_dark_all_iterable if options.all else master_dark_batch_iterable
	else:
		return
	do_image_view(connection, batch, iterable, headers, options)


# These are the pipelien stages in execution order

def image_register(connection, options):
	batch = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
	do_image_register(connection, options.work_dir, batch, options)
	

def image_classify(connection, options):
	batch = latest_batch(connection)
	iterable = classify_all_iterable if options.all else classify_batch_iterable
	do_image_classify(connection, batch, classify_batch_iterable, options)


def image_stats(connection, options):
	batch = latest_batch(connection)
	iterable = stats_all_iterable if options.all else stats_batch_iterable
	do_image_stats(connection, batch, iterable, options)


def image_dark(connection, options):
	batch = latest_batch(connection)
	do_image_apply_dark(connection, batch, options)


def image_export(connection, options):
	batch = latest_batch(connection)
	iterable = export_all_iterable if options.all else export_batch_iterable
	do_image_export(connection, batch, iterable, options)


def image_reduce(connection, options):
	# Step 1
	if not options.all:
		batch = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
		do_image_register(connection, options.work_dir, batch, options)
	else:
		batch = latest_batch(connection)
	# Step 2
	iterable = classify_all_iterable if options.all else classify_batch_iterable
	do_image_classify(connection, batch, iterable, options)
	# Step 3
	iterable = stats_all_iterable if options.all else stats_batch_iterable
	do_image_stats(connection, batch, iterable, options)
	# Step 4
	do_image_apply_dark(connection, batch, options)
	# Step 5
	iterable = export_all_iterable if options.all else export_batch_iterable
	do_image_export(connection, batch, iterable, options)
