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
import logging
import logging.handlers
import traceback
import shutil
import datetime
import hashlib
import zipfile

#--------------
# local imports
# -------------

from .           import *
from .           import __version__
from .exceptions import *
from .config     import load_config_file
from .zenodo     import zenodo_licenses, zenodo_list, zenodo_delete, zenodo_pipeline
# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("azotenodo")


# -----------------------
# Module global functions
# -----------------------

def configureLogging(options):
	if options.verbose:
		level = logging.DEBUG
	elif options.quiet:
		level = logging.WARN
	else:
		level = logging.INFO
	
	log.setLevel(level)
	# Log formatter
	#fmt = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] %(message)s')
	fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
	# create console handler and set level to debug
	if not options.no_console:
		ch = logging.StreamHandler()
		ch.setFormatter(fmt)
		ch.setLevel(level)
		log.addHandler(ch)
	# Create a file handler
	if options.log_file:
		#fh = logging.handlers.WatchedFileHandler(options.log_file)
		fh = logging.FileHandler(options.log_file)
		fh.setFormatter(fmt)
		fh.setLevel(level)
		log.addHandler(fh)


def python2_warning():
	if sys.version_info[0] < 3:
		log.warning("This software des not run under Python 2 !")


def setup(options):
	
	python2_warning()
	if not os.path.exists(AZOTEA_BASE_DIR):
		log.info("Creating {0} directory".format(AZOTEA_BASE_DIR))
		os.mkdir(AZOTEA_BASE_DIR)
	if not os.path.exists(AZOTEA_CFG_DIR):
		log.info("Creating {0} directory".format(AZOTEA_CFG_DIR))
		os.mkdir(AZOTEA_CFG_DIR)
	if not os.path.exists(AZOTEA_CSV_DIR):
		log.info("Creating {0} directory".format(AZOTEA_CSV_DIR))
		os.mkdir(AZOTEA_CSV_DIR)
	if not os.path.exists(AZOTEA_ZIP_DIR):
		log.info("Creating {0} directory".format(AZOTEA_ZIP_DIR))
		os.mkdir(AZOTEA_ZIP_DIR)
	if not os.path.exists(AZOTEA_LOG_DIR):
		log.info("Creating {0} directory".format(AZOTEA_LOG_DIR))
		os.mkdir(AZOTEA_LOG_DIR)
	if not os.path.exists(options.config):
		shutil.copy2(DEF_CONFIG_TPL, DEF_CONFIG)
		log.info("Created {0} file, please review it".format(DEF_CONFIG))


# =================== #
# THE ARGUMENT PARSER #
# =================== #

def createParser():
	# create the top-level parser
	name = os.path.split(os.path.dirname(sys.argv[0]))[-1]
	parser    = argparse.ArgumentParser(prog=name, description="AZOTEA export to ZENODO tool")

	# Global options
	parser.add_argument('--version', action='version', version='{0} {1}'.format(name, __version__))
	group1 = parser.add_mutually_exclusive_group()
	group1.add_argument('-v', '--verbose', action='store_true', help='Verbose output.')
	group1.add_argument('-q', '--quiet',   action='store_true', help='Quiet output.')
	parser.add_argument('-nk','--no-console', action='store_true', help='Do not log to console.')
	parser.add_argument('--log-file', type=str, default=None, help='Optional log file')
	parser.add_argument('--config', type=str, default=DEF_CONFIG, help='Optional alternate configuration file')
	parser.add_argument('-t', '--test',   action='store_true', help='Use the ZENODO Sandbox environment')


	subparser = parser.add_subparsers(dest='command')

	parser_list     = subparser.add_parser('list',      help='list contents')
	parser_licenses = subparser.add_parser('licenses',  help='list Zenodo available publication licenses')
	parser_delete   = subparser.add_parser('delete',    help='delete draft Zenodo depositions')
	parser_pipeline = subparser.add_parser('pipeline',  help='The full pipeline (deposit/upload/publish) with versioning')
	

	# -----------
	# List action
	# -----------
	parser_list.add_argument('--published', action='store_true', default=False, help='List published results only')
	parser_list.add_argument('--title', type=str, default=None,  help='Search by title')

	# -------------
	# Delete action
	# -------------
	parser_delete.add_argument('--id',type=int, required=True,  help='Zenodo ID to delete')

	# --------------
	# Pipeline action
	# --------------

	parser_pipeline.add_argument('--title',    type=str, nargs='+', default=AZOTEA_PUBL_TITLE, help='Optional Publication Title')
	parser_pipeline.add_argument('--csv-dir',  type=str, default=AZOTEA_CSV_DIR,    help='Optional CSV file dir')
	parser_pipeline.add_argument('--zip-file' ,type=str, default=DEF_ZIP_FILE,      help='Optional ZIP File to create with all CSV files')
	parser_pipeline.add_argument('--community',type=str, default=AZOTEA_COMMUNITY,  help='Optional community where to publish the dataset')
	parser_pipeline.add_argument('--version',  type=str, default=None,              help='Optional version string to tag, useful for tests')
	
	return parser




# ================ #
# MAIN ENTRY POINT #
# ================ #

def main():
	'''
	Utility entry point
	'''
	try:
		options = createParser().parse_args(sys.argv[1:])
		configureLogging(options)
		command  = options.command
		log.info("============== AZOTENODO {0} ==============".format(__version__))
		file_options = load_config_file(options.config)
		file_options = argparse.Namespace(**file_options)
		setup(options)
		globals()['zenodo_' + command](options, file_options)
	except KeyboardInterrupt as e:
		log.critical("[%s] Interrupted by user ", __name__)
	except Exception as e:
		log.critical("[%s] Fatal error => %s", __name__, str(e) )
		traceback.print_exc()
	finally:
		pass

main()
