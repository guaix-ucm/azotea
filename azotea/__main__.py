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

#--------------
# local imports
# -------------

from .           import *
from .exceptions import *
from .           import __version__
from .config     import load_config_file, merge_options 
from .utils      import chop, Point, ROI, open_database, create_database
from .cfgcmds    import config_global, config_camera
from .database   import database_clear, database_purge, database_backup
from .backup     import backup_list, backup_delete, backup_restore
from .image      import image_list, image_export, image_reduce
from .reorg      import reorganize_images
from .session    import session_current, session_list
from .changed    import changed_observer, changed_location, changed_camera, changed_image

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("azotea")

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
	# Create a file handler Suitable for logrotate usage
	if options.log_file:
		#fh = logging.handlers.WatchedFileHandler(options.log_file)
		fh = logging.handlers.TimedRotatingFileHandler(options.log_file, when='midnight', interval=1, backupCount=365)
		fh.setFormatter(fmt)
		fh.setLevel(level)
		log.addHandler(fh)


def python2_warning():
	if sys.version_info[0] < 3:
		log.warning("This software des not run under Python 2 !")


def setup(options):
	configureLogging(options)
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
	if not os.path.exists(AZOTEA_DB_DIR):
		log.info("Creating {0} directory".format(AZOTEA_DB_DIR))
		os.mkdir(AZOTEA_DB_DIR)
	if not os.path.exists(AZOTEA_BAK_DIR):
		log.info("Creating {0} directory".format(AZOTEA_BAK_DIR))
		os.mkdir(AZOTEA_BAK_DIR)
	if not os.path.exists(AZOTEA_LOG_DIR):
		log.info("Creating {0} directory".format(AZOTEA_LOG_DIR))
		os.mkdir(AZOTEA_LOG_DIR)
	if not os.path.exists(DEF_CONFIG):
		shutil.copy2(DEF_CONFIG_TPL, DEF_CONFIG)
		log.info("Created {0} file, please review it".format(DEF_CONFIG))



def mkrect1(text):
	'''Make a rectangle of width and height'''
	l = chop(text,',')
	return ROI( x1=0, x2=int(l[0]), y1=0, y2=int(l[1]))


# =================== #
# THE ARGUMENT PARSER #
# =================== #

def createParser():
	# create the top-level parser
	name = os.path.split(os.path.dirname(sys.argv[0]))[-1]
	parser    = argparse.ArgumentParser(prog=name, description="AZOTEA analysis tool")

	# Global options
	parser.add_argument('--version', action='version', version='{0} {1}'.format(name, __version__))
	group1 = parser.add_mutually_exclusive_group()
	group1.add_argument('-v', '--verbose', action='store_true', help='Verbose output.')
	group1.add_argument('-q', '--quiet',   action='store_true', help='Quiet output.')
	parser.add_argument('-nk','--no-console', action='store_true', help='Do not log to console.')
	parser.add_argument('--log-file', type=str, default=None, help='Optional log file')
	parser.add_argument('--camera', type=str, default=DEF_CAMERA, help='Optional alternate camera configuration file')
	parser.add_argument('--config', type=str, default=DEF_CONFIG, help='Optional alternate global configuration file')

	# --------------------------
	# Create first level parsers
	# --------------------------

	subparser = parser.add_subparsers(dest='command')

	parser_init     = subparser.add_parser('init', help='init command')
	parser_config   = subparser.add_parser('config', help='config commands')
	parser_image    = subparser.add_parser('image', help='image commands')
	parser_database = subparser.add_parser('database', help='database commands (mostly mainteinance)')
	parser_back     = subparser.add_parser('backup', help='backup management')
	parser_reorg    = subparser.add_parser('reorganize', help='reorganize commands')
	parser_session  = subparser.add_parser('session', help='session commands')
	parser_changed  = subparser.add_parser('changed', help='notify change commands (only for automatized use)')
   
	# ------------------------------------------
	# 'init' does not have a second level parser
	# ------------------------------------------

	# -----------------------------------------
	# Create second level parsers for 'changed'
	# -----------------------------------------

	subparser = parser_changed.add_subparsers(dest='subcommand')

	cho = subparser.add_parser('observer', help="Notify changes of observer metadata")
	cho.add_argument('-k', '--key',  type=str, required=True, help='who changed')
	
	chl = subparser.add_parser('location', help="Notify changes of location metadata")
	chl.add_argument('-k', '--key',  type=str, required=True, help='who changed')

	chc = subparser.add_parser('camera',   help="Notify changes of camera metadata")
	chc.add_argument('-k', '--key',  type=str, required=True, help='who changed')

	chi = subparser.add_parser('image',    help="Notify changes of image metadata")
	chi.add_argument('-k', '--key',  type=str, required=True, help='who changed')
	

	# -----------------------------------------
	# Create second level parsers for 'database'
	# -----------------------------------------

	subparser = parser_database.add_subparsers(dest='subcommand')

	dbc = subparser.add_parser('clear',  help="Clears the database (MAINTENANCE ONLY!)")
	dbcex = dbc.add_mutually_exclusive_group(required=True)
	dbcex.add_argument('-l', '--last',  action='store_true', help='clear last session')
	dbcex.add_argument('-a', '--all',   action='store_true' , help='clear all data')
	
	
	dbp = subparser.add_parser('purge',  help="Purge the database  (MAINTENANCE ONLY!)")

	dbp = subparser.add_parser('backup',  help="Database backup")
	dbp.add_argument('--comment', type=str,  help='Optional comment')

	# ----------------------------------------
	# Create second level parsers for 'backup'
	# ----------------------------------------

	subparser = parser_back.add_subparsers(dest='subcommand')

	bkl = subparser.add_parser('list',  help="List database backups")
	
	bkd = subparser.add_parser('delete',  help="Delete a given backup")
	bkd.add_argument('--bak-file', type=str, required=True , help='Backup file to deleta')

	bkr = subparser.add_parser('restore',  help="Restore database from backup")
	bkr.add_argument('--bak-file', type=str, required=True , help='Backup file from where to restore')
	bkr.add_argument('--non-interactive', action='store_true', help='Do not request confirmation')


	# ----------------------------------------
	# Create second level parsers for 'reorganize'
	# ----------------------------------------

	subparser = parser_reorg.add_subparsers(dest='subcommand')

	rgi = subparser.add_parser('images',  help="Reorganize images into observation nights")
	rgi.add_argument('-i', '--input-dir',  type=str, required=True , help='Images input directory')
	rgi.add_argument('-o','--output-dir', type=str, required=True , help='Images output base diretory')
	rgi.add_argument('-d', '--dry-run',   action='store_true', help='Show how many directories, do not copy.')


	# ----------------------------------------
	# Create second level parsers for 'session'
	# ----------------------------------------

	subparser = parser_session.add_subparsers(dest='subcommand')

	bcu = subparser.add_parser('current', help="session current list")
	bcu.add_argument('-x', '--extended',  action='store_true', help='Extended info')
	bcu.add_argument('--page-size',       type=int, default=10,  help="display page size")
   
	bli = subparser.add_parser('list', help="Batch list")
	bliex = bli.add_mutually_exclusive_group(required=True)
	bliex.add_argument('-b', '--session',  type=str , help='session identifier')
	bliex.add_argument('-a', '--all',  action='store_true' , help='all sessiones')
	bli.add_argument('-x', '--extended',  action='store_true', help='Extended info')
	bli.add_argument('--page-size',       type=int, default=10,  help="display page size")
   


	# -----------------------------------------
	# Create second level parsers for 'config'
	# -----------------------------------------

	subparser = parser_config.add_subparsers(dest='subcommand')

	cgl = subparser.add_parser('global',  help="Global configuration file actions")
	cglex = cgl.add_mutually_exclusive_group(required=True)
	cglex.add_argument('-c' ,'--create', action="store_true", help="Create global configuration file in user's HOME directory")
	cglex.add_argument('-l' ,'--list',   action="store_true", help="List current global configuration file template")
	cglex.add_argument('-d' ,'--diff',   action="store_true", help="Diff input config file with config file template")
	cgl.add_argument('-i', '--input-file', type=str , help='Input config file for diff')

	cca = subparser.add_parser('camera',  help="Create camera configuration file in user's HOME directory")
	ccaex = cca.add_mutually_exclusive_group(required=True)
	ccaex.add_argument('-c' ,'--create', action="store_true", help="Create camera configuration file in user's HOME directory")
	ccaex.add_argument('-l' ,'--list',   action="store_true", help="List current camera configuration file template")


	# ---------------------------------------
	# Create second level parsers for 'image'
	# ---------------------------------------
  
	subparser = parser_image.add_subparsers(dest='subcommand')
	parser_image.add_argument('--roi', type=mkrect1, metavar="<width,height>", help='Optional region of interest')


	ime = subparser.add_parser('list',    help='display image data')
	ime.add_argument('-a' ,'--all',       action="store_true", help="apply to all images in database")
	imeex = ime.add_mutually_exclusive_group(required=True)
	imeex.add_argument('--exif',      action="store_true", help="display EXIF metadata")
	imeex.add_argument('--generic',   action="store_true", help="display global metadata")
	imeex.add_argument('--state',     action="store_true", help="display processing state")
	imeex.add_argument('--data',      action="store_true", help="dark substracted signal averaged over roi")
	imeex.add_argument('--raw-data',  action="store_true", help="raw signal averaged over roi")
	imeex.add_argument('--dark',      action="store_true", help="raw signal of DARK images")
	imeex.add_argument('--dark-data', action="store_true", help="dark signal of LIGHT averaged over dark row or master dark")
	imeex.add_argument('--master',    action="store_true", help="display master dark data")
	ime.add_argument('--page-size',   type=int, default=10,  help="display page size")

	ird = subparser.add_parser('reduce',  help='run register/classify/stats</export pipeline')
	ird.add_argument('-w' ,'--work-dir',  type=str, required=True, help='Input working directory')
	ird.add_argument('-r' ,'--reset',     default=False, action="store_true",     help="Reprocess from start")
	ird.add_argument('-f' ,'--force-csv', default=False, action="store_true",     help="Force CSV file generration")
	ird.add_argument('-m' ,'--multiuser', default=False, action="store_true",     help="Multi-user reduction pipeline flag")
	ird.add_argument('-c', '--csv-dir',   type=str, default=AZOTEA_CSV_DIR,       help='Optional directory where the CSV is placed')

	iex = subparser.add_parser('export',  help='export the whole database to a CSV file')
	iex.add_argument('--csv-file',        type=str, default=DEF_GLOBAL_CSV,  help='Optional session CSV file to export')
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
		setup(options)
		log.info("======= AZOTEA {0} =======".format(__version__))
		connection = open_database(DEF_DBASE)
		create_database(connection, SQL_SCHEMA, SQL_DATA_DIR, SQL_TEST_STRING)
		command      = options.command
		if command == 'init':
			return
		subcommand   = options.subcommand
		# Call the function dynamically
		func = command + '_' + subcommand
		globals()[func](connection, options)
	except KeyboardInterrupt as e:
		log.critical("[%s] Interrupted by user ", __name__)
	except Exception as e:
		log.critical("[%s] Fatal error => %s", __name__, str(e) )
		traceback.print_exc()
	finally:
		pass

main()
