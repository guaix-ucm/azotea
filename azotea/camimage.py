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
import rawpy
import tabulate
import numpy     as np

#--------------
# local imports
# -------------

from . import __version__


# ----------------
# Module constants
# ----------------

# Array indexes in Bayer pattern
R1 = 0
G2 = 1
G3 = 2
B4 = 3

# -----------------------
# Module global variables
# -----------------------

BG_X1 = 400
BG_Y1 = 200
BG_X2 = 550
BG_Y2 = 350

WIDTH  = 500
HEIGHT = 400


class Point:
    """ Point class represents and manipulates x,y coords. """
    def __init__(self):
        """ Create a new point at the origin """
        self.x = 0
        self.y = 0

    def __repr__(self):
        return "(x={0},y={1})".format(self.x, self.y)

class Rect:
    """ Rectangle defined by opposite points. """
    def __init__(self):
        self.P0 = Point()
        self.P1 = Point()

    def __repr__(self):
        return "[{0} - {1}]".format(self.P0, self.P1)


class CameraImage(object):

    def __init__(self, filepath):
        self.filepath   = filepath
        self.metadata   = None
        self.image      = None
        self._name       = os.path.basename(filepath)
        self.signal     = []    # Array of Bayer signal
        self.background = []    # Array of Bayer background
        self.path       = filepath  
        self.fgregion   = Rect()  # foreground rectangular region
        self.bgregion   = Rect()  # background rectangular region were bias is estimated


    def name(self):
        return self._name


    def loadEXIF(self):   
        with open(self.filepath, "rb") as f:
            self.metadata = exifread.process_file(f)
        return self.metadata


    def foreground_region(self, width, height):
        self.fgregion.P0.x = np.int(self.signal[G2].shape[1] / 2 - width//2)   # atento: eje X  shape[1]
        self.fgregion.P0.y = np.int(self.signal[G2].shape[0] / 2 - height//2)  # atento: eje Y  shape[0]
        self.fgregion.P1.x = self.fgregion.P0.x + width
        self.fgregion.P1.y = self.fgregion.P0.y + height


    def background_region(self, x1, x2, y1, y2):
        self.bgregion.P0.x = x1
        self.bgregion.P0.y = y1
        self.bgregion.P1.x = x2
        self.bgregion.P1.y = y2


    def region_stats(self, data, region):
        r = data[region.P0.y:region.P1.y,region.P0.x:region.P1.x]
        return r.mean(), r.std()
       

    def extract_background(self):
        self.background.append(self.signal[R1][-410:,-610:])   # No se de donde salen estos numeros
        self.background.append(self.signal[G2][-410:,-610:])
        self.background.append(self.signal[G3][-410:,-610:])
        self.background.append(self.signal[B4][-410:,-610:])

        
    def stats(self):
        r1_mean_center, r1_std_center = self.region_stats(self.signal[R1],     self.fgregion)
        r1_mean_back,   r1_std_back   = self.region_stats(self.background[R1], self.bgregion)
        g2_mean_center, g2_std_center = self.region_stats(self.signal[G2],     self.fgregion)
        g2_mean_back,   g2_std_back   = self.region_stats(self.background[G2], self.bgregion)
        g3_mean_center, g3_std_center = self.region_stats(self.signal[G3],     self.fgregion)
        g3_mean_back,   g3_std_back   = self.region_stats(self.background[G3], self.bgregion)
        b4_mean_center, b4_std_center = self.region_stats(self.signal[B4],     self.fgregion)
        b4_mean_back,   b4_std_back   = self.region_stats(self.background[B4], self.bgregion)
        return {
            'name'               : self._name,
            'date'               : self.metadata.get('Image DateTime'),
            'model'              : self.metadata.get('Image Model'),
            'ISO'                : self.metadata.get('EXIF ISOSpeedRatings'),
            'exposure'           : self.metadata.get('EXIF ExposureTime'),
            'mean_signal_R1'     : r1_mean_center,
            'stdev_signal_R1'    : r1_std_center,
            'mean_signal_G2'     : g2_mean_center,
            'stdev_signal_G2'    : g2_std_center,
            'mean_signal_G3'     : g3_mean_center,
            'stdev_signal_G3'    : g3_std_center,
            'mean_signal_B4'     : b4_mean_center,
            'stdev_signal_B4'    : b4_std_center,
            'mean_background_R1' : r1_mean_back,
            'stdev_background_R1': r1_std_back,
            'mean_background_G2' : g2_mean_back,
            'stdev_background_G2': g2_std_back,
            'mean_background_G3' : g3_mean_back,
            'stdev_background_G3': g3_std_back,
            'mean_background_B4' : b4_mean_back,
            'stdev_background_B4': b4_std_back,
        }
    

    def read(self):
        logging.info("{0}: Loading EXIF metadata".format(self._name))
        self.loadEXIF()
        logging.info("{0}: Loading RAW data for".format(self._name))
        self.image = rawpy.imread(self.filepath)
        self.doRead()
        self.extract_background()
        self.foreground_region(WIDTH, HEIGHT)
        self.background_region(BG_X1, BG_X2, BG_Y1, BG_Y2)
        logging.info("{0}: Illuminated region of interest is {1}".format(self._name, self.fgregion))
        logging.info("{0}: Background region of interest is {1}".format(self._name, self.bgregion))
        logging.info("{0}: Computing stats".format(self._name))
        return self.stats()



       

class CanonEOS450EDImage(CameraImage):

    def doRead(self):
        # R1 channel
        self.signal.append(self.image.raw_image[::2,::2])
        # G2 channel
        self.signal.append(self.image.raw_image[::2,1::2])
        # G3 channel
        self.signal.append(self.image.raw_image[1::2,::2])
        # R4 channel
        self.signal.append(self.image.raw_image[1::2,1::2])
        


class CanonEOS550EDImage(CameraImage):

    def doRead(self):
        # R1 channel
        self.signal.append(image.raw_image[1::2,::2])
        # G2 channel
        self.signal.append(image.raw_image[::2,::2])
        # G3 channel
        self.signal.append(image.raw_image[1::2,1::2])
        # R4 channel
        self.signal.append(image.raw_image[::2,1::2])
       


# -----------------------
# Module global functions
# -----------------------
