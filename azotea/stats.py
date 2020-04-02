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



def stats_analyze(directory, options):
    tstamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    directory = directory[:-1] if os.path.basename(directory) == '' else directory  
    metadata = {'session': tstamp, 'observer': options.observer, 'organization': options.organization, 'location': options.location}
    rows = []
    file_list = glob.glob(directory + '/' + options.filter)
    logging.info("Analyzing {0} files".format(len(file_list)))
    for filename in file_list:
        image = CameraImage(filename, options)
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


def stats_move(file_list, options):
    if not file_list:
        return
    directory = os.path.dirname(file_list[0])   # Pick one file to get the directory
    new_dir   = os.path.join(directory, "processed")
    try:
        os.mkdir(new_dir)
    except FileExistsError:
        pass
    except OSError:
        pass

    if (not options.do_not_move) and (not options.dry_run):
        for f in file_list:
            shutil.move(f, new_dir)
        logging.info("Moved {0} files to {1}".format(len(file_list), new_dir))



# =====================
# Command esntry points
# =====================


def stats_compute(options):
    rows, file_list = stats_analyze(options.work_dir, options)
    stats_write(rows, options)
    stats_move(file_list, options)
