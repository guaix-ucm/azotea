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
import os.path
import logging
import shutil
import difflib

# ---------------------
# Third party libraries
# ---------------------


#--------------
# local imports
# -------------

from . import DEF_CAMERA_TPL, DEF_CONFIG_TPL, AZOTEA_CFG_DIR

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("azotea")

# -----------------------
# Module global functions
# -----------------------

def config_list(filename):
	print('\n')
	with open(filename, 'r') as f:
		shutil.copyfileobj(f, sys.stdout)


def config_create(filename):
	dest = os.path.join(AZOTEA_CFG_DIR, os.path.basename(filename))
	shutil.copy2(filename, dest)
	log.info("Created {0} file".format(dest))


def config_diff(template_file, input_file):
	with open(template_file,'r') as tpl_file:
		tpl_contents = tpl_file.readlines()
	with open(input_file,'r') as inp_file:
		inp_contents = inp_file.readlines()
	tpl_contents = [line.rstrip() for line in tpl_contents]
	inp_contents = [line.rstrip() for line in inp_contents]
	for line in difflib.context_diff(tpl_contents, inp_contents, 
			fromfile=AZOTEA_CFG_DIR, tofile=input_file):
		print(line)


# =====================
# Command esntry points
# =====================


def config_global(connection, options):
	if options.list:
		config_list(DEF_CONFIG_TPL)
	elif options.create:
		config_create(DEF_CONFIG_TPL)
	elif options.diff:
		config_diff(DEF_CONFIG_TPL, options.input_file)


def config_camera(connection, options):
	if options.list:
		config_list(DEF_CAMERA_TPL)
	elif options.create:
		config_create(DEF_CAMERA_TPL)
