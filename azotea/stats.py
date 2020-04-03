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

from .camimage import  CameraImage
from .utils    import merge_two_dicts


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

def session_processed(connection, session):
    row = {'session': session}
    cursor = connection.cursor()
    cursor.execute('''
        SELECT COUNT(*) 
        FROM image_t 
        WHERE state IS NOT NULL
        AND session = :session
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


def last_session(connection):
    '''Get Last recorded session'''
    cursor = connection.cursor()
    cursor.execute('''
        SELECT MAX(session)
        FROM image_t 
        ''')
    return cursor.fetchone()[0]

# ------------------
# Database iterables
# ------------------

def to_classify_iterable(connection):
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT name, file_path
        FROM image_t
        WHERE type IS NULL
        ''')
    return cursor


def unprocessed_iterable(connection):
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT name, file_path
        FROM image_t
        WHERE state IS NULL
        ''')
    return cursor


def export_session_iterable(connection, session):
    row = {'session': session}
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
        AND   session = :session
        ''', row)
    return cursor

def export_global_iterable(connection):
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
                session, 
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
                :session, 
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
                session, 
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
                :session, 
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



def update_type(connection, rows):
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

# ----------------
# Processing steps
# ----------------

def stats_scan_preamble(connection, directory, session, options):
    file_list = insert_list(connection, directory, options)
    logging.info("Registering {0} new images".format(len(file_list)))
    metadata = {
        'session'     : session, 
        'observer'    : options.observer, 
        'organization': options.organization, 
        'location'    : options.location,
    }
    return file_list, metadata

def stats_scan_slow(connection,  file_list, metadata, options):
    
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


def stats_scan_fast(connection, file_list, metadata, options):
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
        logging.info("{0} images registered in database".format(len(rows)))
        
def stats_scan(connection, directory, session, options):
    file_list, metadata = stats_scan_preamble(connection, directory, session, options)
    if options.slow:
        stats_scan_slow(connection, file_list, metadata, options)
    else:
        stats_scan_fast(connection, file_list, metadata, options)


def stats_classify(connection, options):
    rows = []
    for name, file_path in to_classify_iterable(connection):
        row = classification_algorithm1(name, file_path, options)
        logging.info("{0} is type {1}".format(name,row['type']))
        rows.append(row)
    if rows:
        update_type(connection, rows)
    else:
        logging.info("No image type classification is needed")



def stats_stats(connection, options):
    rows = []
    for name, file_path in unprocessed_iterable(connection):
        image = CameraImage(file_path, options)
        image.loadEXIF()    # we need to find out the camera model before reading
        image.read()
        row = image.stats()
        row['state'] = RAW_STATS
        rows.append(row)
    if rows:
        update_stats(connection, rows)
    else:
        logging.info("No image statistics to be computed")


def do_export_csv(connection, session, options):
    fieldnames = ["session","observer","organization","location", "type"]
    fieldnames.extend(CameraImage.HEADERS)
    # Write a session CSV file
    session_csv_file = os.path.join(os.path.expanduser("~"), session + '.csv')
    with myopen(session_csv_file, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(fieldnames)
        writer.writerows(export_session_iterable(connection, session))
    logging.info("Saved data to session CSV file {0}".format(session_csv_file))
    # Update the global CSV file
    writeheader = not os.path.exists(options.global_csv_file)
    with myopen(options.global_csv_file, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(fieldnames)
        writer.writerows(export_global_iterable(connection))
    logging.info("Saved data to global  CSV file {0}".format(options.global_csv_file))


def stats_export(connection, session, options):
    if session_processed(connection, session):
        do_export_csv(connection, session, options)
    elif options.force_csv:
        session = last_session(connection)
        do_export_csv(connection, session, options)
    else:
        logging.info("No CSV file generation takes place")


# =====================
# Command esntry points
# =====================


def stats_compute(connection, options):
    session = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    stats_scan(connection, options.work_dir, session, options)
    stats_classify(connection, options)
    stats_stats(connection, options)
    stats_export(connection, session, options)
    if duplicated_file_paths:
        logging.warning("Images duplcated: {0}".format(duplicated_file_paths))

