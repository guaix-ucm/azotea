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

    def __add__(self, rect):
        return NotImplemented

    def __repr__(self):
        return "({0},{1})".format(self.x, self.y)

class ROI:
    """ Region of interest  """
    def __init__(self, x1 ,x2, y1, y2):
        self.x1 = min(x1,x2)
        self.y1 = min(y1,y2)
        self.x2 = max(x1,x2)
        self.y2 = max(y1,y2)

    def dimensions(self):
        '''returns width and height'''
        return abs(self.x2 - self.x1), abs(self.y2 - self.y1)

    def __add__(self, point):
        return ROI(self.x1 + point.x, self.x2 + point.x, self.y1 + point.y, self.y2 + point.y)

    def __radd__(self, point):
        return self.__add__(point)
        
    def __repr__(self):
        return "[{0}:{1},{2}:{3}]".format(self.x1, self.x2, self.y1, self.y2)

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
