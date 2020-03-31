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

from . import __version__, DEF_WIDTH, DEF_HEIGHT, DEF_CONFIG
from .metadata import metadata_display
from .stats    import stats_compute
from .utils    import chop, Point, Rect


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
    return Rect( Point(), Point(x=int(l[0]), y=int(l[1])))

def mkrect2(text):
    '''make rectangle with bounding corners'''
    l = chop(text,',')
    return Rect( Point(x=int(l[0]), y=int(l[2]) ), Point(x=int(l[1]), y=int(l[3])) )


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

    # --------------------------
    # Create first level parsers
    # --------------------------

    subparser = parser.add_subparsers(dest='command')
    parser_meta  = subparser.add_parser('metadata', help='metadata commands')
    parser_stats = subparser.add_parser('stats', help='stats commands')


    # -----------------------------------------
    # Create second level parsers for 'metadata'
    # -----------------------------------------
  
    subparser = parser_meta.add_subparsers(dest='subcommand')
    mdi = subparser.add_parser('display',  help='display image metadata')
    mdiex = mdi.add_mutually_exclusive_group(required=True)
    mdiex.add_argument('-i', '--input-file', type=str, help='Input file')
    mdiex.add_argument('-w' ,'--work-dir',  type=str, help='Input working directory')
    mdi.add_argument('--filter', type=str, default='*.CR2', help='Optional input glob-style filter if input directory')

    # ---------------------------------------
    # Create second level parsers for 'stats'
    # ---------------------------------------
  
    subparser = parser_stats.add_subparsers(dest='subcommand')
    sdy = subparser.add_parser('compute',  help='compute image statistics')
    sdy.add_argument('--width',  type=int, default=DEF_WIDTH,  help='Optional image center width')
    sdy.add_argument('--height', type=int, default=DEF_HEIGHT, help='Optional image center height')
    sdy.add_argument('--fg-region', type=mkrect1, metavar="<width,height>", default=Rect( Point(), Point(DEF_WIDTH, DEF_HEIGHT) ), help='Optional foreground region')
    sdy.add_argument('--bg-region', type=mkrect2, metavar="<x1,x2,y1,y2>", default=Rect( Point(400,200), Point(550,350) ), help='Optional background region')
    sdy.add_argument('--config', type=str, default=DEF_CONFIG, help='Optional Camera configuration file')
    sdyex = sdy.add_mutually_exclusive_group(required=True)
    sdyex.add_argument('-i' ,'--input-file', type=str, help='Input file')
    sdyex.add_argument('-w' ,'--work-dir',   type=str, help='Input working directory')
    sdy.add_argument('--filter', type=str, default='*.CR2', help='Optional input glob-style filter if input directory')

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
        command    = options.command
        subcommand = options.subcommand
        # Call the function dynamically
        func = command + '_' + subcommand
        globals()[func](options)
    except KeyboardInterrupt as e:
        logging.error("[{0}] Interrupted by user ".format(__name__))
    except Exception as e:
        logging.error("[{0}] Fatal error => {1}".format(__name__, str(e) ))
        traceback.print_exc()
    finally:
        pass

main()
