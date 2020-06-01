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
import os
import os.path
import glob
import logging
import shutil
import subprocess

# ---------------------
# Third party libraries
# ---------------------

import jdcal

#--------------
# local imports
# -------------

from .camera import CameraImage
from .utils  import LogCounter

# ----------------
# Module constants
# ----------------

N_FILES = 50

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("azotea")

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


def dir_name(jd2000, mjd):
	year, month, day, fraction = jdcal.jd2gcal(jd2000, mjd)
	return "{0:04d}-{1:02d}-{2:02d}".format(year, month, day)

def scan_images(options):
	output_dir_set = set()
	image_list = []
	counter = LogCounter(N_FILES)
	filepath_iterable = glob.iglob(os.path.join(options.input_dir, '*'))
	for input_file_path in filepath_iterable:
		image = CameraImage(input_file_path, options)
		image.loadEXIF()
		jd2000, mjd = image.getJulianDate()
		mjd -= 0.5	# Take it 12 hours before and make sure it is the same YYYY-MM-DD
		date_string = dir_name(jd2000, mjd)
		output_dir_path = os.path.join(options.output_dir, date_string)
		output_dir_set.add(output_dir_path)
		image_list.append((input_file_path, output_dir_path))
		counter.tick("Read %d images")
	counter.end("Read %d images")
	return output_dir_set, image_list


def create_dest_directories(output_dir_set):
	log.info("creating %d output directories", len(output_dir_set))
	for directory in output_dir_set:
		if not os.path.isdir(directory):
			os.makedirs(directory)


def copy_files(image_list):
	log.info("copying images to output directories")
	counter = LogCounter(N_FILES)
	for item in image_list:
		if sys.platform == 'win32':
			subprocess.call("xcopy",item[0], item[1])
		else:
			shutil.copy2(item[0], item[1])
		counter.tick("Copied %d images")
	counter.end("Copied %d images")


# =====================
# Command esntry points
# =====================



def reorganize_images(connection, options):
	connection.close()
	output_dir_set, image_list = scan_images(options)
	if not options.dry_run:
		create_dest_directories(output_dir_set)
		copy_files(image_list)
	else:
		log.info("Would create %d directories", len(output_dir_set))
