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

from . import __version__, DEF_WIDTH, DEF_HEIGHT, DEF_CAMERA, DEF_CONFIG, DEF_GLOBAL_CSV, DEF_DBASE, SQL_DATAMODEL
from .config   import load_config_file, merge_options 
from .metadata import metadata_display
from .stats    import stats_compute
from .utils    import chop, Point, ROI, open_database, create_database
from .cfgcmds  import config_global, config_camera
from .dbase    import dbase_clear, dbase_purge

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
    parser_meta   = subparser.add_parser('metadata', help='metadata commands')
    parser_stats  = subparser.add_parser('stats', help='stats commands')
    parser_config = subparser.add_parser('config', help='config commands')
    parser_dbase  = subparser.add_parser('dbase', help='database commands (MAINTENANCE ONLY!)')


    # -----------------------------------------
    # Create second level parsers for 'dbase'
    # -----------------------------------------

    subparser = parser_dbase.add_subparsers(dest='subcommand')

    dbc = subparser.add_parser('clear',  help="Clears the database (MAINTENANCE ONLY!)")
    
    dbp = subparser.add_parser('purge',  help="Purge the database  (MAINTENANCE ONLY!)")

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


    # -----------------------------------------
    # Create second level parsers for 'metadata'
    # -----------------------------------------
  
    subparser = parser_meta.add_subparsers(dest='subcommand')

    mdi = subparser.add_parser('display',  help='display image metadata')
    mdiex = mdi.add_mutually_exclusive_group(required=True)
    mdiex.add_argument('-i', '--input-file', type=str, help='Input file')
    mdiex.add_argument('-w','--work-dir',  type=str, help='Input working directory')
    mdi.add_argument('-f', '--filter', type=str, default='*.*', help='Optional input glob-style filter if input directory')

    # ---------------------------------------
    # Create second level parsers for 'stats'
    # ---------------------------------------
  
    subparser = parser_stats.add_subparsers(dest='subcommand')

    sdy = subparser.add_parser('compute',  help='compute image statistics')
    sdy.add_argument('--roi', type=mkrect1, metavar="<width,height>", help='Optional region of interest')
    sdy.add_argument('--global-csv-file', type=str, default=DEF_GLOBAL_CSV, help='Global output CSV file where all sessions are accumulated')
    sdy.add_argument('-w' ,'--work-dir',  type=str, help='Input working directory')
    sdy.add_argument('-f' ,'--filter',    type=str, default='*.*', help='Optional input glob-style filter')
    sdy.add_argument('-x' ,'--extended',  action="store_true", help="Show extended info (mean, stdev) per channel")
    sdyex = sdy.add_mutually_exclusive_group()
    sdyex.add_argument('-m' ,'--do-not-move',  action="store_true", help="Do not move files after processing")
    sdyex.add_argument('-d' ,'--dry-run',  action="store_true", help="Do not generate/update CSV files")

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
