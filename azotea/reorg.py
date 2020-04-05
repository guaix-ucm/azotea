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

N_FILES = 50

# -----------------------
# Module global variables
# -----------------------


# -----------------------
# Module global functions
# -----------------------

def _copyfileobj_patched(fsrc, fdst, length=16*1024*1024):
    """Patches shutil method to improve big file copy speed on Linux"""
    while 1:
        buf = fsrc.read(length)
        if not buf:
            break
        fdst.write(buf)


shutil.copyfileobj = _copyfileobj_patched


def scan_images(options):
	count = 0
	output_dir_set = set()
	image_list = []
	filepath_iterable = glob.iglob(os.path.join(options.input_dir, '*'))
	for input_file_path in filepath_iterable:
		image = CameraImage(input_file_path, options)
		image.loadEXIF()
		date = image.getJulianDate()
		output_dir_path = os.path.join(options.output_dir,str(date))
		output_dir_set.add(output_dir_path)
		image_list.append((input_file_path, output_dir_path))
		count += 1
		if (count % N_FILES) == 0:
			logging.info("read {0} images".format(count))
	logging.info("read {0} images".format(count))
	return output_dir_set, image_list


def create_dest_directories(output_dir_set):
	logging.info("creating {0} output directories".format(len(output_dir_set)))
	for directory in output_dir_set:
		if not os.path.isdir(directory):
			os.makedirs(directory)


def copy_files(image_list):
	logging.info("copying images to output directories")
	count = 0
	for item in image_list:
		if sys.platform == 'win32':
			os.system('xcopy "{0}" "{1}"'.format(source, target))
		else:
			shutil.copy2(item[0], item[1])
		count += 1
		if (count % N_FILES) == 0:
			logging.info("copied {0} images".format(count))
	logging.info("copied {0} images".format(count))



# =====================
# Command esntry points
# =====================



def reorganize_images(connection, options):
	connection.close()
	output_dir_set, image_list = scan_images(options)
	create_dest_directories(output_dir_set)
	copy_files(image_list)
