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

# ---------------------
# Third party libraries
# ---------------------

#--------------
# local imports
# -------------

from .           import AZOTEA_CSV_DIR
from .camera     import CameraImage, CameraCache, MetadataError
from .utils      import merge_two_dicts, paging
from .exceptions import NoBatchError, NoWorkDirectoryError
from .exceptions import MixingCandidates


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


def classification_algorithm1(name,  file_path, options):
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


def latest_batch(connection):
	'''Get Last recorded batch'''
	cursor = connection.cursor()
	cursor.execute('''
		SELECT MAX(batch)
		FROM image_t 
		''')
	return cursor.fetchone()[0]


### LO BUENO DE LAS UTILIDADES AQUI DEBAJO

def myopen(name, *args):
	if sys.version_info[0] < 3:
		return open(name, *args)
	else:
		return open(name,  *args, newline='')


def myhash(filepath):
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


def image_batch_state_reset(connection, batch):
	row = {'batch': batch, 'state': RAW_STATS, 'new_state': REGISTERED, 'type': UNKNOWN}
	cursor = connection.cursor()
	cursor.execute(
		'''
		UPDATE image_t
		SET state = :new_state, type = :type
		WHERE state >= :state
		AND batch = :batch
		''', row)
	connection.commit()


def create_candidates_temp_table(connection):
	cursor = connection.cursor()
	cursor.execute("CREATE TEMP TABLE candidate_t (name TEXT PRIMARY KEY)")
	connection.commit()


def work_dir_to_batch(connection, work_dir, filt):
	file_list  = glob.glob(os.path.join(work_dir, filt))
	names_list = [ {'name': os.path.basename(p)} for p in file_list ]
	logging.info("Found {0} candidates matching filter {1}".format(len(names_list), filt))
	cursor = connection.cursor()
	cursor.executemany("INSERT OR IGNORE INTO candidate_t (name) VALUES (:name)", names_list)
	connection.commit()
	# Common images to database and work-dir
	cursor.execute(
		'''
		SELECT MAX(batch), MAX(batch) == MIN(batch)
		FROM image_t
		WHERE name IN (SELECT name FROM candidate_t)
		'''
		)
	result = cursor.fetchall()
	if result:
		batches, flags = zip(*result)
		if flags[0] and not all(flags):
			raise MixingCandidates(names_common)
		batch = batches[0]
	else:
		batch = None

	return batch


def master_dark_for(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	cursor.execute('''
		SELECT COUNT(*) 
		FROM master_dark_t
		WHERE batch = :batch
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
				batch, 
				type,
				state
			) VALUES (
				:name, 
				:hash,
				:batch,
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
				batch,
				type,
				state
			) VALUES (
				:name, 
				:hash,
				:batch, 
				:type,
				:state
			)
			''', rows)
	connection.commit()


def candidates(connection, work_dir, filt, batch):
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
	row = {'batch': batch}
	cursor.execute(
		'''
		SELECT name
		FROM image_t
		WHERE name NOT IN (SELECT name FROM candidate_t)
		AND batch = :batch
		''', row)
	result = cursor.fetchall()
	if result:
		names_to_del, = zip(*result)
	else:
		names_to_del = []
	return names_to_add, names_to_del


def register_delete_images(connection, rows):
	'''fast version'''
	cursor = connection.cursor()
	cursor.executemany(
			'''
			DELETE FROM image_t 
			WHERE name  == :name
			AND   batch == :batch
			''', rows)
	connection.commit()



def register_slow(connection, work_dir, names_list, batch):
	logging.info("SLOW REGISTER")
	global duplicated_file_paths
	for name in names_list:
		file_path = os.path.join(work_dir, name)
		row  = {'batch': batch, 'state': REGISTERED, 'type': UNKNOWN,}
		row['name'] = name
		row['hash'] = myhash(file_path)
		try:
			register_insert_image(connection, row)
		except sqlite3.IntegrityError as e:
			connection.rollback()
			name2, = find_by_hash(connection, row['hash'])
			duplicated_file_paths.append({'original': name2, 'duplicated': file_path})
			logging.warn("Duplicate => {0} EQUALS {1}".format(file_path, name2))
		else:
			logging.info("{0} registered in database".format(row['name']))


def register_fast(connection, work_dir, names_list, batch):
	rows = []
	for name in names_list:
		file_path = os.path.join(work_dir, name)
		row  = {'batch': batch, 'state': REGISTERED, 'type': UNKNOWN,}
		row['name'] = name
		row['hash'] = myhash(file_path)
		rows.append(row)
		logging.info("{0} being registered in database".format(row['name']))
	register_insert_images(connection, rows)
	

def register_unregister(connection, names_list, batch):
	rows = []
	row  = {'batch': batch}
	for name in names_list:
		row['name']  = name
		row['batch'] = batch
		rows.append(row)
		logging.info("{0} being removed from database".format(row['name']))
	register_delete_images(connection, rows)
	

def do_register(connection, work_dir, filt, batch):
	names_to_add, names_to_del = candidates(connection, work_dir, filt, batch)
	if names_to_del:
		register_unregister(connection, names_to_del, batch)	
	if names_to_add:
		try:
			register_fast(connection, work_dir, names_to_add, batch)
		except sqlite3.IntegrityError as e:
			connection.rollback()
			register_slow(connection, work_dir, names_to_add, batch)
	logging.info("{0} new images registered in database".format(len(names_to_add)))
	logging.info("{0} images deleted from database".format(len(names_to_del)))



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



def classify_batch_iterable(connection, batch):
	row = {'batch': batch, 'type': UNKNOWN}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name
		FROM image_t
		WHERE type = :type
		AND batch = :batch
		''', row)
	return cursor


def do_classify(connection, batch, work_dir, options):
	rows = []
	for name, in classify_batch_iterable(connection, batch):
		file_path = os.path.join(work_dir, name)
		row = classification_algorithm1(name, file_path, options)
		logging.info("{0} is type {1}".format(name, row['type']))
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
		SET 
		    state               = :state,
		    roi                 = :roi, 
            model               = :model,	-- EXIF
            iso                 = :iso,     -- EXIF
            tstamp              = :tstamp,  -- EXIF
            exptime             = :exptime, -- EXIF
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



def stats_batch_iterable(connection, batch):
	row = {'batch': batch, 'state': RAW_STATS}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name
		FROM image_t
		WHERE state < :state
		AND batch = :batch
		''', row)
	return cursor


def do_stats(connection, batch, work_dir, options):
	camera_cache = CameraCache(options.camera)
	rows = []
	for name, in stats_batch_iterable(connection, batch):
		file_path = os.path.join(work_dir, name)
		image = CameraImage(file_path, camera_cache)
		image.setROI(options.roi)
		try:
			metadata = image.loadEXIF()
		except MetadataError as e:
			logging.info(e)    # we need to find out the camera model before reading
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
			vari_B4,
			min_exptime,
			max_exptime
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
			SUM(vari_raw_signal_B4)/COUNT(*),
			MIN(exptime),
			MAX(exptime)
		FROM image_t
		WHERE type = :type
		AND   state >= :state
		GROUP BY batch
		''', row)
	connection.commit()


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
	if master_dark_for(connection, batch):
		logging.info("Applying dark substraction to current working directory")
		dark_update_columns(connection, batch)
	else:
		logging.info("No dark frame found for current working directory")

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

def export_batch_iterable(connection, batch):
	row = {'batch': batch, 'state': RAW_STATS, 'type': LIGHT_FRAME}
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



def get_file_path(connection, batch, work_dir, options):
	# respct user's wishes
	if options.csv_file:
		return options.csv_file
	name = "batch-" + os.path.basename(work_dir) + '.csv'
	return os.path.join(AZOTEA_CSV_DIR, name)


def var2std(item):
	'''From Variance to StdDev in seevral columns'''
	index, value = item
	return round(math.sqrt(value),1) if index in [13, 15, 17, 19] else value


def do_export_all(connection, batch, src_iterable, options):
	fieldnames = ["batch","observer","organization","location", "type"]
	fieldnames.extend(VIEW_HEADERS)
	with myopen(options.global_csv_file, 'w') as csvfile:
		writer = csv.writer(csvfile, delimiter=';')
		writer.writerow(fieldnames)
		for row in export_all_iterable(connection, batch):
			row = map(var2std, enumerate(row))
			writer.writerow(row)
	logging.info("Saved data to global CSV file {0}".format(options.global_csv_file))
	

def do_export_work_dir(connection, batch, work_dir, options):
	fieldnames = ["batch","observer","organization","location", "type"]
	fieldnames.extend(VIEW_HEADERS)
	if batch_processed(connection, batch):
		# Write a batch CSV file
		batch_csv_file = get_file_path(connection, batch, work_dir, options)
		with myopen(batch_csv_file, 'w') as csvfile:
			writer = csv.writer(csvfile, delimiter=';')
			writer.writerow(fieldnames)
			for row in export_batch_iterable(connection, batch):
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
		SELECT name, batch, tstamp, model, exptime, iso
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
		SELECT name, batch, tstamp, model, exptime, iso
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
			batch, N, roi,           
			(min_exptime == max_exptime) as good_flag,
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
	"Good?",
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


def image_export(connection, options):
	pass

def image_reduce(connection, options):
	
	create_candidates_temp_table(connection)
	old_batch = work_dir_to_batch(connection, options.work_dir, options.filter)
	new_batch = int(datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"))
	batch = new_batch if old_batch is None else old_batch

	# Step 1: registering
	do_register(connection, options.work_dir, options.filter, batch)
	
	if options.reset:
		image_batch_state_reset(connection, batch)
	# Step 2
	do_stats(connection, batch, options.work_dir, options)

	# Step 3
	#iterable = classify_all_iterable if options.all else classify_batch_iterable
	do_classify(connection, batch, options.work_dir, options)

	# Step 4
	do_apply_dark(connection, batch, options)
	# Step 5
	#iterable = export_all_iterable if options.all else export_batch_iterable
	#do_export(connection, batch, iterable, options)
	do_export_work_dir(connection, batch, options.work_dir, options)
