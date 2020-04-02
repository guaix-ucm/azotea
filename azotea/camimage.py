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
import os
import os.path
import logging
import errno
import datetime
import traceback
import hashlib

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

from .      import DEF_CAMERA, DEF_TSTAMP
from .utils import chop, Point, ROI

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



# ----------
# Exceptions
# ----------

class ConfigError(ValueError):
    '''This camera model is not supported by AZOTEA'''
    def __str__(self):
        s = self.__doc__
        if self.args:
            s = "{0}: '{1}'".format(s, self.args[0])
        s = '{0}.'.format(s)
        return s

class MetadataError(ValueError):
    '''TError reading metadata for image'''
    def __str__(self):
        s = self.__doc__
        if self.args:
            s = "{0}: '{1}'".format(s, self.args[0])
        s = '{0}.'.format(s)
        return s

class TimestampError(ValueError):
    '''EXIF timestamp not supported by AZOTEA'''
    def __str__(self):
        s = self.__doc__
        if self.args:
            s = "{0}: '{1}'".format(s, self.args[0])
        s = '{0}.'.format(s)
        return s

class CameraImage(object):

    HEADERS = [
            'tstamp'         ,
            'name'           ,
            'model'          ,
            'ISO'            ,
            'roi'            ,
            'dark_roi'       ,
            'exposure'       ,
            'mean_signal_R1' ,
            'stdev_signal_R1',
            'mean_signal_G2' ,
            'stdev_signal_G2',
            'mean_signal_G3' ,
            'stdev_signal_G3',
            'mean_signal_B4' ,
            'stdev_signal_B4',
        ]

    # ========== #
    # Public API #
    # ========== #

    def __init__(self, filepath, options):
        self.filepath   = filepath
        self.camerapath = options.camera
        self.extended   = options.extended
        self.roi        = options.roi  # foreground rectangular region where signal is estimated
        self.dkroi      = None  # dark rectangular region where bias is estimated
        self.exif       = None
        self.image      = None
        self.metadata   = {}  # Subset of EXIF metadata we are interested in
        self._name      = os.path.basename(self.filepath)
        self.signal     = []    # Bayer array for signal ROI
        self.dark       = []    # Bayer array for dark ROI
        self.path       = filepath  
        self.k          = [ Point(), Point(), Point(), Point()] # Array of Points to properly read each channel
        self.step       = [2, 2, 2, 2]
    

    def name(self):
        return self._name



    def hash(self):
        BLOCK_SIZE = 65536*65536 # The size of each read from the file
        file_hash = hashlib.sha256()
        with open(self.filepath, 'rb') as f:
            block = f.read(BLOCK_SIZE) 
            while len(block) > 0:
                file_hash.update(block)
                block = f.read(BLOCK_SIZE)
        return file_hash.digest()


    def loadEXIF(self):
        '''Load EXIF metadata'''   
        logging.debug("{0}: Loading EXIF metadata".format(self._name))
        with open(self.filepath, "rb") as f:
            self.exif = exifread.process_file(f)
        if not self.exif:
            raise MetadataError(self.filepath)
        self.model = str(self.exif.get('Image Model'))
        self.metadata['name']      = self._name
        self.metadata['file_path'] = self.filepath
        self.metadata['model']     = self.model
        self.metadata['tstamp']    = self._iso8601(str(self.exif.get('Image DateTime')))
        self.metadata['exposure']  = str(self.exif.get('EXIF ExposureTime'))
        self.metadata['iso']       = str(self.exif.get('EXIF ISOSpeedRatings'))
        return self.metadata

    def center_roi(self):
        '''image needs to be read'''
        if self.roi.x1 == 0 and self.roi.y1 == 0:
            self._center_roi()
        return self.roi
   

    def read(self):
        '''Read RAW data''' 
        self._lookup()
        logging.debug("{0}: Loading RAW data from {1}".format(self._name, self.model))
        self.image = rawpy.imread(self.filepath)
        logging.debug("{0}: Color description is {1}".format(self._name, self.image.color_desc))
        self._read()
        self._center_roi()
        
        
    def stats(self):
        logging.debug("{0}: Computing stats".format(self._name))
        r1_mean, r1_std = self._region_stats(self.signal[R1], self.roi)
        g2_mean, g2_std = self._region_stats(self.signal[G2], self.roi)
        g3_mean, g3_std = self._region_stats(self.signal[G3], self.roi)
        b4_mean, b4_std = self._region_stats(self.signal[B4], self.roi)
        result = {
            'name'            : self.metadata['name'],
            'tstamp'          : self.metadata['tstamp'],
            'model'           : self.metadata['model'],
            'ISO'             : self.metadata['iso'],
            'exposure'        : self.metadata['exposure'],
            'roi'             : str(self.roi),
            'dark_roi'        : str(self.dkroi),
            'mean_signal_R1'  : r1_mean,
            'stdev_signal_R1' : r1_std,
            'mean_signal_G2'  : g2_mean,
            'stdev_signal_G2' : g2_std,
            'mean_signal_G3'  : g3_mean,
            'stdev_signal_G3' : g3_std,
            'mean_signal_B4'  : b4_mean,
            'stdev_signal_B4' : b4_std,
        }
        if self.dkroi:
            self._extract_dark()
            self._add_dark_stats(result)
        logging.info("{0}: {2}, ROI = {1}, Dark ROI = {3}".format(self._name, self.roi, self.model, self.dkroi))
        if self.extended:
            logging.info("{0}: \u03BC = {1}, \u03C3 = {2} ".format(
                self._name, [r1_mean, g2_mean, g3_mean, b4_mean],[r1_std, g2_std, g3_std, b4_std]))
        return result

    # ============== #
    # helper methods #
    # ============== #


    def _iso8601(self, tstamp):
        date = None
        for fmt in ["%Y:%m:%d %H:%M:%S", "%Y:%m:%d %H:%M:%S"]:
            try:
                date = datetime.datetime.strptime(tstamp, fmt)
            except ValueError:
                continue
            else:
                break
        if not date:
            raise TimestampError(tstamp)
        else:
            return date.strftime(DEF_TSTAMP)

    def _lookup(self):
        '''
        Load camera configuration from configuration file
        '''
        if not (os.path.exists(self.camerapath)):
            logging.warning("No camera config file found at {0}, using default file".format(self.camerapath))
            self.camerapath = DEF_CAMERA

        parser  =  ConfigParser.RawConfigParser()
        # str is for case sensitive options
        parser.optionxform = str
        parser.read(self.camerapath)
        if not parser.has_section(self.metadata['model']):
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
        r = data[region.y1:region.y2, region.x1:region.x2]
        return round(r.mean(),1), round(r.std(),1)


    def _center_roi(self):
        '''Sets the Region of interest around the image center'''
        width, height = self.roi.dimensions()
        x = np.int(self.signal[G2].shape[1] / 2 - width//2)   # atento: eje X  shape[1]
        y = np.int(self.signal[G2].shape[0] / 2 - height//2)  # atento: eje Y  shape[0]
        self.roi += Point(x,y)  # Shift ROI using this point
        

    def _extract_dark(self):
        self.dark.append(self.signal[R1][-410: , -610:])   # No se de donde salen estos numeros
        self.dark.append(self.signal[G2][-410: , -610:])
        self.dark.append(self.signal[G3][-410: , -610:])
        self.dark.append(self.signal[B4][-410: , -610:])

    def _add_dark_stats(self, mydict):
        r1_mean_dark,   r1_std_dark   = self._region_stats(self.dark[R1], self.dkroi)
        g2_mean_dark,   g2_std_dark   = self._region_stats(self.dark[G2], self.dkroi)
        g3_mean_dark,   g3_std_dark   = self._region_stats(self.dark[G3], self.dkroi)
        b4_mean_dark,   b4_std_dark   = self._region_stats(self.dark[B4], self.dkroi)
        self.HEADERS.extend(['mean_dark_R1', 'stdev_dark_R1', 'mean_dark_G2', 'stdev_dark_G2',
                'mean_dark_G3', 'stdev_dark_G3', 'mean_dark_B4', 'stdev_dark_B4'])
        mydict['mean_dark_R1']  = r1_mean_dark
        mydict['stdev_dark_R1'] = r1_std_dark
        mydict['mean_dark_G2']  = g2_mean_dark
        mydict['stdev_dark_G2'] = g2_std_dark
        mydict['mean_dark_G3']  = g3_mean_dark
        mydict['stdev_dark_G3'] = g3_std_dark
        mydict['mean_dark_B4']  = b4_mean_dark
        mydict['stdev_dark_B4'] = b4_std_dark


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
