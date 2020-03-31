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

try:
    # Python 2
    import ConfigParser
except:
    import configparser as ConfigParser


# ---------------------
# Third party libraries
# ---------------------

import exifread
import rawpy
import tabulate
import numpy as np

#--------------
# local imports
# -------------

from .utils import chop, Point, Rect

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

class ConfigError(Exception):
    '''This camera model is not supported by AZOTEA'''
    def __str__(self):
        s = self.__doc__
        if self.args:
            s = "{0}: '{1}'".format(s, self.args[0])
        s = '{0}.'.format(s)
        return s


class CameraImage(object):

    HEADERS = [
            'date'               ,
            'name'               ,
            'model'              ,
            'ISO'                ,
            'exposure'           ,
            'mean_signal_R1'     ,
            'stdev_signal_R1'    ,
            'mean_background_R1' ,
            'stdev_background_R1',
            'mean_signal_G2'     ,
            'stdev_signal_G2'    ,
            'mean_background_G2' ,
            'stdev_background_G2',
            'mean_signal_G3'     ,
            'stdev_signal_G3'    ,
            'mean_background_G3' ,
            'stdev_background_G3',
            'mean_signal_B4'     ,
            'stdev_signal_B4'    ,
            'mean_background_B4' ,
            'stdev_background_B4',
        ]

    # ========== #
    # Public API #
    # ========== #

    def __init__(self, filepath, options):
        self.filepath   = filepath
        self.configpath = options.config
        self.fgregion   = options.fg_region  # foreground rectangular region where signal is estimated
        self.bgregion   = options.bg_region  # background rectangular region where bias is estimated
        self.metadata   = None
        self.image      = None
        self.model      = None
        self._name      = os.path.basename(filepath)
        self.signal     = []    # Array of Bayer signal
        self.background = []    # Array of Bayer background
        self.path       = filepath  
        self.k          = [ Point(), Point(), Point(), Point()] # Array of Points to properly read each channel
        self.step       = [ 2, 2, 2, 2]
    

    def name(self):
        return self._name


    def loadEXIF(self):
        '''Load EXIF metadata'''   
        logging.debug("{0}: Loading EXIF metadata".format(self._name))
        with open(self.filepath, "rb") as f:
            self.metadata = exifread.process_file(f)
        self.model = str(self.metadata.get('Image Model'))
        return self.metadata


    def read(self):
        '''Read RAW data''' 
        self.loadEXIF()
        self._lookup()
        logging.info("{0}: Loading RAW data from {1}".format(self._name, self.model))
        self.image = rawpy.imread(self.filepath)
        logging.debug("{0}: Color description is {1}".format(self._name, self.image.color_desc))
        self._read()
        
        
    def stats(self):
        logging.debug("{0}: Computing stats".format(self._name))
        self._extract_background()
        self._foreground_region()
        r1_mean_center, r1_std_center = self._region_stats(self.signal[R1],     self.fgregion)
        r1_mean_back,   r1_std_back   = self._region_stats(self.background[R1], self.bgregion)
        g2_mean_center, g2_std_center = self._region_stats(self.signal[G2],     self.fgregion)
        g2_mean_back,   g2_std_back   = self._region_stats(self.background[G2], self.bgregion)
        g3_mean_center, g3_std_center = self._region_stats(self.signal[G3],     self.fgregion)
        g3_mean_back,   g3_std_back   = self._region_stats(self.background[G3], self.bgregion)
        b4_mean_center, b4_std_center = self._region_stats(self.signal[B4],     self.fgregion)
        b4_mean_back,   b4_std_back   = self._region_stats(self.background[B4], self.bgregion)
        return {
            'name'               : self._name,
            'date'               : self.metadata.get('Image DateTime'),
            'model'              : self.model,
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
    

    # ============== #
    # helper methods #
    # ============== #

    def _lookup(self):
        '''
        Load camera configuration from configuration file
        '''
        if not (os.path.exists(self.configpath)):
            raise IOError(errno.ENOENT,"No such file or directory", path)

        parser  =  ConfigParser.RawConfigParser()
        # str is for case sensitive options
        parser.optionxform = str
        parser.read(self.configpath)
        if not parser.has_section(self.model):
            raise ConfigError(self.model)

        r1 = chop(parser.get(self.model,"R1"),',')
        g2 = chop(parser.get(self.model,"G2"),',')
        g3 = chop(parser.get(self.model,"G3"),',')
        b4 = chop(parser.get(self.model,"B4"),',')
        self.k[R1].x, self.k[R1].y, self.step[R1] = int(r1[0]), int(r1[1]), int(r1[2])
        self.k[G2].x, self.k[G2].y, self.step[G2] = int(g2[0]), int(g2[1]), int(g2[2])
        self.k[G3].x, self.k[G3].y, self.step[G3] = int(g3[0]), int(g3[1]), int(g3[2])
        self.k[B4].x, self.k[B4].y, self.step[B4] = int(b4[0]), int(b4[1]), int(b4[2])

    def _region_stats(self, data, region):
        r = data[region.P1.y:region.P2.y, region.P1.x:region.P2.x]
        return round(r.mean(),1), round(r.std(),1)
       

    def _foreground_region(self):
        width, height = self.fgregion.dimensions()
        self.fgregion.P1.x = np.int(self.signal[G2].shape[1] / 2 - width//2)   # atento: eje X  shape[1]
        self.fgregion.P1.y = np.int(self.signal[G2].shape[0] / 2 - height//2)  # atento: eje Y  shape[0]
        self.fgregion.P2.x = self.fgregion.P1.x + width
        self.fgregion.P2.y = self.fgregion.P1.y + height
        logging.info("{0}: Illuminated region of interest is {1}".format(self._name, self.fgregion))


    def _extract_background(self):
        logging.info("{0}: Background  region of interest is {1}".format(self._name, self.bgregion))
        self.background.append(self.signal[R1][-410: , -610:])   # No se de donde salen estos numeros
        self.background.append(self.signal[G2][-410: , -610:])
        self.background.append(self.signal[G3][-410: , -610:])
        self.background.append(self.signal[B4][-410: , -610:])


    def _read(self):
        # R1 channel
        self.signal.append(self.image.raw_image[self.k[R1].x::self.step[R1], self.k[R1].y::self.step[R1]])
        # G2 channel
        self.signal.append(self.image.raw_image[self.k[G2].x::self.step[G2], self.k[G2].y::self.step[G2]])
        # G3 channel
        self.signal.append(self.image.raw_image[self.k[G3].x::self.step[G3], self.k[G3].y::self.step[G3]])
         # B4 channel
        self.signal.append(self.image.raw_image[self.k[B4].x::self.step[B4], self.k[B4].y::self.step[B4]])
       





# -----------------------
# Module global functions
# -----------------------
