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
import traceback


#--------------
# other imports
# -------------

from . import __version__
from . import  AZOTEA_BASE_DIR, AZOTEA_DB_DIR, AZOTEA_LOG_DIR, AZOTEA_CFG_DIR, AZOTEA_BAK_DIR
from . import DEF_WIDTH, DEF_HEIGHT, DEF_CAMERA, DEF_CONFIG, DEF_GLOBAL_CSV, DEF_DBASE, SQL_DATAMODEL
from .config   import load_config_file, merge_options 
from .utils    import chop, Point, ROI, open_database, create_database
from .cfgcmds  import config_global, config_camera
from .dbase    import dbase_clear, dbase_purge, dbase_backup
from .backup   import backup_list, backup_delete, backup_restore
from .image    import image_register, image_classify, image_dark, image_stats, image_export, image_reduce
from .image    import image_view
from .reorg    import reorganize_images
from .batch    import batch_current, batch_list

#
# -----------------------
# Module global variables
# -----------------------

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
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=level)


def mkrect1(text):
    '''Make a rectangle of width and height'''
    l = chop(text,',')
    return ROI( x1=0, x2=int(l[0]), y1=0, y2=int(l[1]))

def mkrect2(text):
    '''make rectangle with bounding corners'''
    l = chop(text,',')
    return ROI( x1=int(l[0]), y1=int(l[2]), x2=int(l[1]), y2=int(l[3]))


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
    parser.add_argument('--camera', type=str, default=DEF_CAMERA, help='Optional alternate camera configuration file')
    parser.add_argument('--config', type=str, default=DEF_CONFIG, help='Optional alternate global configuration file')

    # --------------------------
    # Create first level parsers
    # --------------------------

    subparser = parser.add_subparsers(dest='command')

    parser_config = subparser.add_parser('config', help='config commands')
    parser_image  = subparser.add_parser('image', help='image commands')
    parser_dbase  = subparser.add_parser('dbase', help='database commands (mostly mainteinance)')
    parser_back   = subparser.add_parser('backup', help='backup management')
    parser_reorg  = subparser.add_parser('reorganize', help='reorganize commands')
    parser_batch  = subparser.add_parser('batch', help='batch commands')
   
    # -----------------------------------------
    # Create second level parsers for 'dbase'
    # -----------------------------------------

    subparser = parser_dbase.add_subparsers(dest='subcommand')

    dbc = subparser.add_parser('clear',  help="Clears the database (MAINTENANCE ONLY!)")
    
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


    # ----------------------------------------
    # Create second level parsers for 'batch'
    # ----------------------------------------

    subparser = parser_batch.add_subparsers(dest='subcommand')

    bcu = subparser.add_parser('current', help="batch current list")
    bcu.add_argument('-x', '--extended',  action='store_true', help='Extended info')
    bcu.add_argument('--page-size',       type=int, default=10,  help="display page size")
   
    bli = subparser.add_parser('list', help="Batch list")
    bliex = bli.add_mutually_exclusive_group(required=True)
    bliex.add_argument('-b', '--batch',  type=str , help='batch identifier')
    bliex.add_argument('-a', '--all',  action='store_true' , help='all batches')
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

    cca = subparser.add_parser('camera',  help="Create camera configuration file in user's HOME directory")
    ccaex = cca.add_mutually_exclusive_group(required=True)
    ccaex.add_argument('-c' ,'--create', action="store_true", help="Create camera configuration file in user's HOME directory")
    ccaex.add_argument('-l' ,'--list',   action="store_true", help="List current camera configuration file template")


    # ---------------------------------------
    # Create second level parsers for 'image'
    # ---------------------------------------
  
    subparser = parser_image.add_subparsers(dest='subcommand')
    parser_image.add_argument('--roi', type=mkrect1, metavar="<width,height>", help='Optional region of interest')
    parser_image.add_argument('--global-csv-file', type=str, default=DEF_GLOBAL_CSV, help='Global output CSV file')

    ime = subparser.add_parser('view',    help='display image data')
    ime.add_argument('-a' ,'--all',       action="store_true", help="apply to all images in database")
    imeex = ime.add_mutually_exclusive_group(required=True)
    imeex.add_argument('--exif',  action="store_true", help="display EXIF metadata")
    imeex.add_argument('--general', action="store_true", help="display general metadata")
    imeex.add_argument('--state', action="store_true", help="display processing state")
    imeex.add_argument('--data',  action="store_true", help="dark substracted signal averaged over roi")
    imeex.add_argument('--raw-data',  action="store_true", help="raw signal averaged over roi")
    imeex.add_argument('--dark',  action="store_true", help="dark signal averaged over dark row or master dark")
    imeex.add_argument('--master',  action="store_true", help="display master dark data")
    ime.add_argument('--page-size',       type=int, default=10,  help="display page size")

    ire = subparser.add_parser('register', help='register images in the database')
    ire.add_argument('-n' ,'--new',        action="store_true", help="Generate a new batch of images")
    ire.add_argument('-w' ,'--work-dir',   required=True, type=str, help='Input working directory')
    ire.add_argument('-f' ,'--filter',     type=str, default='*.*', help='Optional input glob-style filter')
    ire.add_argument('-s' ,'--slow',       action="store_true", help="Use slow registering mode to detect duplicates")

    icl = subparser.add_parser('classify', help='classify LIGHT/DARK images')
    icl.add_argument('-a' ,'--all',       action="store_true", help="apply to all images in database")

    isb = subparser.add_parser('dark',    help='apply master DARK to LIGHT images')
    isb.add_argument('-a' ,'--all',        action="store_true", help="apply to all images in database")
    
    ist = subparser.add_parser('stats',   help='compute image statistics')
    ist.add_argument('-a' ,'--all',       action="store_true", help="apply to all images in database")
    ist.add_argument('-x' ,'--extended',  action="store_true", help="Show extended info (mean, stdev) per channel")
  
    iex = subparser.add_parser('export',  help='export to CSV')
    iex.add_argument('-a' ,'--all',       action="store_true", help="apply to all images in database")

    ird = subparser.add_parser('reduce',  help='run register/classify/stats</export pipeline')
    irdex = ird.add_mutually_exclusive_group()
    irdex.add_argument('-n' ,'--new',     action="store_true", help="Generate a new batch of images")
    irdex.add_argument('-a' ,'--all',     action="store_true", help="apply to all existing batches")
    ird.add_argument('-w' ,'--work-dir',  type=str, help='Input working directory')
    ird.add_argument('-f' ,'--filter',    type=str, default='*.*', help='Optional input glob-style filter')
    ird.add_argument('-x' ,'--extended',  action="store_true", help="Show extended info (mean, stdev) per channel")
    ird.add_argument('-s' ,'--slow',      action="store_true", help="Use slow registration mode")

    return parser


# --------------------------
# Configuration file loading
# --------------------------

from argparse import Namespace

def loadConfig(filepath):
    
        '''Load EXIF metadata'''   
        logging.debug("{0}: Loading EXIF metadata".format(self._name))
        with open(self.filepath, "rb") as f:
            self.metadata = exifread.process_file(f)
        self.model = str(self.metadata.get('Image Model'))
        return self.metadata
# --------
# Database
# --------



# ================ #
# MAIN ENTRY POINT #
# ================ #

def main():
    '''
    Utility entry point
    '''
    try:
        if not os.path.exists(AZOTEA_BASE_DIR):
            logging.info("Creating directories under {0}".format(AZOTEA_BASE_DIR))
            os.mkdir(AZOTEA_BASE_DIR)
            os.mkdir(AZOTEA_CFG_DIR)
            os.mkdir(AZOTEA_DB_DIR)
            os.mkdir(AZOTEA_BAK_DIR)
            os.mkdir(AZOTEA_LOG_DIR)
        options = createParser().parse_args(sys.argv[1:])
        configureLogging(options)
        connection = open_database(DEF_DBASE)
        create_database(connection, SQL_DATAMODEL, "SELECT COUNT(*) FROM image_t")
        command      = options.command
        subcommand   = options.subcommand
        if not command in ["config"]: 
            file_options = load_config_file(DEF_CONFIG)
            options      = merge_options(options, file_options)
        # Call the function dynamically
        func = command + '_' + subcommand
        globals()[func](connection, options)
    except KeyboardInterrupt as e:
        logging.error("[{0}] Interrupted by user ".format(__name__))
    except Exception as e:
        logging.error("[{0}] Fatal error => {1}".format(__name__, str(e) ))
        traceback.print_exc()
    finally:
        pass

main()
