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

# -----------------------
# Module global variables
# -----------------------


if sys.version_info[0] == 2:
    import errno
    class FileExistsError(OSError):
        def __init__(self, msg):
            super(FileExistsError, self).__init__(errno.EEXIST, msg)

# -----------------------
# Module global functions
# -----------------------

def myopen(name, *args):
    if sys.version_info[0] < 3:
        return open(name, *args)
    else:
        return open(name,  *args, newline='')


def already_in_database(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT file_path FROM image_t")
    return [item[0] for item in cursor]

def insert_new_images(connection, rows):
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

def candidates(directory, options):
    '''candidate list of images to be inserted in the database'''
    file_list = glob.glob(directory + '/' + options.filter)
    logging.info("Found {0} candidate images".format(len(file_list)))
    return file_list


def insert_list(connection, directory, options):
    '''Returns the list of file mpaths that must be really inserted in the database'''
    return list(set(candidates(directory, options)) - set(already_in_database(connection)))


def to_classify_iterable(connection):
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT name, file_path
        FROM image_t
        WHERE type IS NULL
        ''')
    return cursor

def update_type(connection, rows):
    cursor = connection.cursor()
    cursor.executemany(
        '''
        UPDATE image_t
        SET type = :type
        WHERE name = :name
        AND type IS NULL
        ''', rows)
    connection.commit()


def stats_scan(connection, directory, session, options):
    file_list = insert_list(connection, directory, options)
    logging.info("Registering {0} new images".format(len(file_list)))
    metadata = {
        'session'     : session, 
        'observer'    : options.observer, 
        'organization': options.organization, 
        'location'    : options.location,
    }
    rows = []
    for file_path in file_list:
        image = CameraImage(file_path, options)
        exif_metadata = image.loadEXIF()
        image.read()
        metadata['file_path'] = file_path
        metadata['hash']      = image.hash()
        metadata['roi']       = str(image.center_roi())
        row   = merge_two_dicts(metadata, exif_metadata)
        rows.append(row)
        logging.info("{0} Registered".format(image.name()))
    insert_new_images(connection, rows)


def classification_algorithm1(name, file_path, options):
    if name.upper().startswith("DARK"):
        result = {'name': name, 'type': "DARK"}
    else:
        result = {'name': name, 'type': "LIGHT"}
    return result


def stats_classify(connection, options):
    rows = []
    for name, file_path in to_classify_iterable(connection):
        row = classification_algorithm1(name, file_path, options)
        logging.info("{0} is type {1}".format(name,row['type']))
        rows.append(row)
    if rows:
        update_type(connection, rows)





def stats_stats(directory, options):
    tstamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    directory = directory[:-1] if os.path.basename(directory) == '' else directory  
    metadata = {'session': tstamp, 'observer': options.observer, 'organization': options.organization, 'location': options.location}
    rows = []
    file_list = glob.iglob(directory + '/' + options.filter)
    #logging.info("Analyzing {0} files".format(len(file_list)))
    for filename in file_list:
        image = CameraImage(filename, options)
        image.loadEXIF()
        image.read()
        row = image.stats()
        row.update(metadata)
        rows.append(row)
    return rows, file_list

    
def stats_write(rows, options):
    if not rows:
        logging.warning("No files to analyze.")
        return
    if options.dry_run:
        logging.info("Dry run, do not generate/update CSV files")
        return
    fieldnames = ["session","observer","organization","location"]
    fieldnames.extend(CameraImage.HEADERS)
    # Write a session CSV file
    session_csv_file = os.path.join(os.path.expanduser("~"), rows[0]['session'] + '.csv')
    with myopen(session_csv_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    logging.info("Saved data to session CSV file {0}".format(session_csv_file))
    # Update the global CSV file
    writeheader = not os.path.exists(options.global_csv_file)
    with myopen(options.global_csv_file, 'a') as csvfile:
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
        if writeheader:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)
    logging.info("Saved data to global CSV file {0}".format(options.global_csv_file))




# =====================
# Command esntry points
# =====================


def stats_compute(connection, options):
    session = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    stats_scan(connection, options.work_dir, session, options)
    stats_classify(connection, options)

