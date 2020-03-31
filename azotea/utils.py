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

# ---------------------
# Third party libraries
# ---------------------

# Access  template withing the package
from pkg_resources import resource_filename

import exifread
import tabulate

#--------------
# local imports
# -------------

from . import __version__


# Python3 catch
try:
    raw_input
except:
    raw_input = input 


# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

# -----------------------
# Module global functions
# -----------------------

if sys.version_info[0] < 3:
    # Python 2 version
    def packet_generator(iterable, size):
        '''Generates a sequence of 'size' items from an iterable'''
        finished = False
        while not finished:
            acc = []
            for i in range(0,size):
                try:
                    obj = iterable.next()
                except AttributeError:
                    iterable = iter(iterable)
                    obj = iterable.next()
                    acc.append(obj)
                except StopIteration:
                    finished = True
                    break
                else:
                    acc.append(obj)
            if len(acc):
                yield acc
else:
    # Python 3 version
    def packet_generator(iterable, size):
        '''Generates a sequence of 'size' items from an iterable'''
        finished = False
        while not finished:
            acc = []
            for i in range(0,size):
                try:
                    obj = iterable.__next__()
                except AttributeError:
                    iterable = iter(iterable)
                    obj = iterable.__next__()
                    acc.append(obj)
                except StopIteration:
                    finished = True
                    break
                else:
                    acc.append(obj)
            if len(acc):
                yield acc



def paging(iterable, headers, maxsize=10, page_size=10):
    '''
    Pages query output and displays in tabular format
    '''
    for rows in packet_generator(iterable, page_size):
        print(tabulate.tabulate(rows, headers=headers, tablefmt='grid'))
        maxsize -= page_size
        if len(rows) == page_size and maxsize > 0:
            raw_input("Press <Enter> to continue or [Ctrl-C] to abort ...")
        else:
            break



def mpl_style():
    mpl.rcParams['text.latex.unicode'] = True
    mpl.rcParams['text.usetex']        = False
    plt.rcParams['font.family']        = 'sans-serif'
    plt.rcParams['font.sans-serif']    = ['Verdana']
    plt.rcParams['font.size']          = 8  
    plt.rcParams['lines.linewidth']    = 4.
    plt.rcParams['axes.labelsize']     = 'small'
    plt.rcParams['grid.linewidth']     = 1.0
    plt.rcParams['grid.linestyle']     = ':'
    plt.rcParams['xtick.minor.size']   = 4
    plt.rcParams['xtick.major.size']   = 8
    plt.rcParams['ytick.minor.size']   = 4
    plt.rcParams['ytick.major.size']   = 8
    plt.rcParams['figure.figsize']     = 18,9
    plt.rcParams['figure.subplot.bottom'] = 0.15
    plt.rcParams['ytick.labelsize']     = 10
    plt.rcParams['xtick.labelsize']     = 10
    mpl.rcParams['xtick.direction']     = 'out'
