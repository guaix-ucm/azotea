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

# ----------------------
# Module utility classes
# ----------------------

class Point:
    """ Point class represents and manipulates x,y coords. """
    def __init__(self, x=0, y=0):
        """ Create a new point at the origin """
        self.x = x
        self.y = y

    def __repr__(self):
        return "(x={0},y={1})".format(self.x, self.y)

class Rect:
    """ Rectangle defined by opposite points. """
    def __init__(self, p1=Point(), p2=Point()):
        self.P1 = p1
        self.P2 = p2

    def dimensions(self):
        '''returns width and height'''
        return abs(self.P1.x-self.P2.x), abs(self.P1.y-self.P2.y)
        
    def __repr__(self):
        return "[{0} - {1}]".format(self.P1, self.P2)

# -----------------------
# Module global functions
# -----------------------

def chop(string, sep=None):
    '''Chop a list of strings, separated by sep and 
    strips individual string items from leading and trailing blanks'''
    chopped = [ elem.strip() for elem in string.split(sep) ]
    if len(chopped) == 1 and chopped[0] == '':
        chopped = []
    return chopped


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
