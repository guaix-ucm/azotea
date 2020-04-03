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

from .         import AZOTEA_DIR
from .camimage import  CameraImage
from .utils    import merge_two_dicts, paging


# ----------------
# Module constants
# ----------------

# values for the 'state' column in table

UNPROCESSED      = None
RAW_STATS        = "RAW STATS"
DARK_SUBSTRACTED = "DARK SUBSTRACTED"

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
	if name.upper().startswith("DARK"):
		result = {'name': name, 'type': "DARK"}
	else:
		result = {'name': name, 'type': "LIGHT"}
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


def last_batch(connection):
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
				exposure
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
				:exposure
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
				exposure
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
				:exposure
			)
			''', rows)
	connection.commit()



def db_update_type(connection, rows):
	cursor = connection.cursor()
	cursor.executemany(
		'''
		UPDATE image_t
		SET type = :type
		WHERE name = :name
		''', rows)
	connection.commit()


def update_stats(connection, rows):
	cursor = connection.cursor()
	cursor.executemany(
		'''
		UPDATE image_t
		SET state           = :state,
			roi             = :roi, 
			mean_signal_R1  = :mean_signal_R1, 
			mean_signal_G2  = :mean_signal_G2, 
			mean_signal_G3  = :mean_signal_G3,
			mean_signal_B4  = :mean_signal_B4,
			stdev_signal_R1 = :stdev_signal_R1,
			stdev_signal_G2 = :stdev_signal_G2,
			stdev_signal_G3 = :stdev_signal_G3,
			stdev_signal_B4 = :stdev_signal_B4 
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
		'batch'     : batch, 
		'observer'    : options.observer, 
		'organization': options.organization, 
		'location'    : options.location,
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
# Image metadata
# --------------

def metadata_exif_all_iterable(connection, batch):
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		''')
	count = cursor.fetchone()[0]
	cursor.execute(
		'''
		SELECT name, batch, tstamp, model, exposure, iso
		FROM image_t
		ORDER BY batch DESC
		''')
	return cursor, count


def metadata_exif_batch_iterable(connection, batch):
	'''batch may be None for NULL'''
	row = {'batch': batch}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		WHERE batch = :batch
		''', row)
	count = cursor.fetchone()[0]
	cursor.execute(
		'''
		SELECT name, batch, tstamp, model, exposure, iso
		FROM image_t
		WHERE batch = :batch
		ORDER BY batch DESC
		''', row)
	return cursor, count


def metadata_global_all_iterable(connection, batch):
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		''')
	count = cursor.fetchone()[0]
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
	cursor.execute(
		'''
		SELECT COUNT(*)
		FROM image_t
		WHERE batch = :batch
		''', row)
	count = cursor.fetchone()[0]
	cursor.execute(
		'''
		SELECT name, type, batch, observer, organization, location, roi
		FROM image_t
		WHERE batch = :batch
		ORDER BY batch DESC
		''', row)
	return cursor, count

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

def do_image_metadata(connection, batch, options):

    if options.exif:
    	headers = EXIF_HEADERS
    	iterable = metadata_exif_all_iterable if options.all else metadata_exif_batch_iterable
    elif options.general:
    	headers = GLOBAL_HEADERS
    	iterable = metadata_global_all_iterable if options.all else metadata_global_batch_iterable
    else:
    	return
    cursor, count = iterable(connection, batch)
    paging(cursor, headers, maxsize=count, page_size=options.page_size)


# --------------
# Image Classify
# --------------

def classify_all_iterable(connection, batch):
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name, file_path
		FROM image_t
		WHERE type IS NULL
		''')
	return cursor


def classify_batch_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name, file_path
		FROM image_t
		WHERE type IS NULL
		AND batch = :batch
		''', row)
	return cursor


def do_image_classify(connection, batch, src_iterable, options):
	rows = []
	for name, file_path in src_iterable(connection, batch):
		row = classification_algorithm1(name, file_path, options)
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
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name, file_path
		FROM image_t
		WHERE state IS NULL
		''')
	return cursor

def stats_batch_iterable(connection, batch):
	row = {'batch': batch}
	cursor = connection.cursor()
	cursor.execute(
		'''
		SELECT name, file_path
		FROM image_t
		WHERE state IS NULL
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
		update_stats(connection, rows)
	else:
		logging.info("No image statistics to be computed")


# -----------
# Image Export
# -----------

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
				stdev_signal_R1, 
				mean_signal_G2, 
				stdev_signal_G2, 
				mean_signal_G3, 
				stdev_signal_G3, 
				mean_signal_B4, 
				stdev_signal_B4
		FROM image_t
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
				stdev_signal_R1, 
				mean_signal_G2, 
				stdev_signal_G2, 
				mean_signal_G3, 
				stdev_signal_G3, 
				mean_signal_B4, 
				stdev_signal_B4
		FROM image_t
		WHERE state IS NOT NULL
		''')
	return cursor

def image_export_csv(connection, batch, options):
	fieldnames = ["batch","observer","organization","location", "type"]
	fieldnames.extend(CameraImage.HEADERS)
	# Write a batch CSV file
	batch_csv_file = os.path.join(AZOTEA_DIR, batch + '.csv')
	with myopen(batch_csv_file, 'w') as csvfile:
		writer = csv.writer(csvfile, delimiter=';')
		writer.writerow(fieldnames)
		writer.writerows(export_batch_iterable(connection, batch))
	logging.info("Saved data to batch  CSV file {0}".format(batch_csv_file))
	# Update the global CSV file
	writeheader = not os.path.exists(options.global_csv_file)
	with myopen(options.global_csv_file, 'w') as csvfile:
		writer = csv.writer(csvfile, delimiter=';')
		writer.writerow(fieldnames)
		writer.writerows(export_all_iterable(connection))
	logging.info("Saved data to global CSV file {0}".format(options.global_csv_file))


def do_image_export(connection, batch, src_iterable, options):
	fieldnames = ["batch","observer","organization","location", "type"]
	fieldnames.extend(CameraImage.HEADERS)
	if options.all:
		with myopen(options.global_csv_file, 'w') as csvfile:
			writer = csv.writer(csvfile, delimiter=';')
			writer.writerow(fieldnames)
			writer.writerows(src_iterable(connection, batch))
		logging.info("Saved data to global CSV file {0}".format(options.global_csv_file))
	elif batch_processed(connection, batch):
		# Write a batch CSV file
		batch_csv_file = os.path.join(AZOTEA_DIR, batch + '.csv')
		with myopen(batch_csv_file, 'w') as csvfile:
			writer = csv.writer(csvfile, delimiter=';')
			writer.writerow(fieldnames)
			writer.writerows(export_batch_iterable(connection, batch))
		logging.info("Saved data to batch  CSV file {0}".format(batch_csv_file))
	else:
		logging.info("No new CSV file generation")
	
	


# =====================
# Command esntry points
# =====================


def image_register(connection, options):
	batch = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
	do_image_register(connection, options.work_dir, batch, options)
	

def image_metadata(connection, options):
	batch = last_batch(connection)
	do_image_metadata(connection, batch, options)


def image_classify(connection, options):
	batch = last_batch(connection)
	iterable = classify_all_iterable if options.all else classify_batch_iterable
	do_image_classify(connection, batch, classify_batch_iterable, options)


def image_stats(connection, options):
	batch = last_batch(connection)
	iterable = stats_all_iterable if options.all else stats_batch_iterable
	do_image_stats(connection, batch, iterable, options)


def image_export(connection, options):
	batch = last_batch(connection)
	iterable = export_all_iterable if options.all else export_batch_iterable
	do_image_export(connection, batch, iterable, options)


def image_reduce(connection, options):
	if not options.all:
		batch = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
		do_image_register(connection, options.work_dir, batch, options)
	else:
		batch = last_batch(connection)
	iterable = classify_all_iterable if options.all else classify_batch_iterable
	do_image_classify(connection, batch, iterable, options)
	iterable = stats_all_iterable if options.all else stats_batch_iterable
	do_image_stats(connection, batch, iterable, options)
	iterable = export_all_iterable if options.all else export_batch_iterable
	do_image_export(connection, batch, iterable, options)
