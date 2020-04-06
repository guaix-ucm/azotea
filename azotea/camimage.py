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

from math import sqrt

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
import jdcal

#--------------
# local imports
# -------------

from .      import DEF_CAMERA_TPL, DEF_TSTAMP
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


# =======
# CLASSES
# =======

class CameraCache(object):

    def __init__(self, camerapath):
        self._points_cache = {}
        self._steps_cache = {}
        self._camerapath = camerapath

    def lookup(self, model):
        '''
        Load camera configuration from configuration file
        '''
        if model in self._points_cache.keys():
            return self._points_cache[model], self._steps_cache[model]

        if not (os.path.exists(self._camerapath)):
            logging.debug("No camera config file found at {0}, using default file".format(self._camerapath))
            self._camerapath = DEF_CAMERA_TPL

        parser  =  ConfigParser.RawConfigParser()
        # str is for case sensitive options
        parser.optionxform = str
        parser.read(self._camerapath)
        if not parser.has_section(model):
            raise ConfigError(model)

        r1 = chop(parser.get(model,"R1"),',')
        g2 = chop(parser.get(model,"G2"),',')
        g3 = chop(parser.get(model,"G3"),',')
        b4 = chop(parser.get(model,"B4"),',')

        points = [ 
            Point(x=int(r1[0]), y=int(r1[1])),
            Point(x=int(g2[0]), y=int(g2[1])),
            Point(x=int(g3[0]), y=int(g3[1])),
            Point(x=int(b4[0]), y=int(b4[1])),
        ]
        steps = [ int(r1[2]), int(g2[2]),  int(g3[2]), int(b4[2])]

        self._points_cache[model] = points
        self._steps_cache[model] = steps
        return points, steps


        



class CameraImage(object):

    HEADERS = [
            'tstamp'         ,
            'name'           ,
            'model'          ,
            'iso'            ,
            'roi'            ,
            'dark_roi'       ,
            'exposure'       ,
            'mean_raw_signal_R1',
            'vari_raw_signal_R1',
            'mean_raw_signal_G2',
            'vari_raw_signal_G2',
            'mean_raw_signal_G3',
            'vari_raw_signal_G3',
            'mean_raw_signal_B4',
            'vari_raw_signal_B4',
        ]
                
               

    # ========== #
    # Public API #
    # ========== #

    def __init__(self, filepath, cache):
        self.filepath   = filepath
        self.cache      = cache # Camera reading parameters cache
        self.roi        = None  # foreground rectangular region where signal is estimated
        self.dkroi      = None  # dark rectangular region where bias is estimated
        self.exif       = None
        self.image      = None
        self.metadata   = {}  # Subset of EXIF metadata we are interested in
        self.name       = os.path.basename(self.filepath)
        self.signal     = []    # Bayer array for signal ROI
        self.dark       = []    # Bayer array for dark ROI
        self.path       = filepath  
        self.k          = [ Point(), Point(), Point(), Point()] # Array of Points to properly read each channel
        self.step       = [2, 2, 2, 2]
    

    def setROI(self, roi):
        if type(roi) == str:
            self.roi = ROI.strproi(roi_str)
        elif type(roi) == ROI:
            self.roi = roi


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
        logging.debug("{0}: Loading EXIF metadata".format(self.name))
        with open(self.filepath, "rb") as f:
            self.exif = exifread.process_file(f)
        if not self.exif:
            raise MetadataError(self.filepath)
        self.model = str(self.exif.get('Image Model'))
        self.metadata['name']      = self.name
        self.metadata['model']     = self.model
        self.metadata['tstamp']    = self._iso8601(str(self.exif.get('Image DateTime')))
        self.metadata['exposure']  = str(self.exif.get('EXIF ExposureTime'))
        self.metadata['iso']       = str(self.exif.get('EXIF ISOSpeedRatings'))
        return self.metadata


    def getJulianDate(self):
        return int(sum(jdcal.gcal2jd(self._date.year, self._date.month, self._date.day)))


    def center_roi(self):
        '''image needs to be read'''
        if self.roi.x1 == 0 and self.roi.y1 == 0:
            self._center_roi()
        return self.roi
   

    def read(self):
        '''Read RAW data''' 
        self._lookup()
        logging.debug("{0}: Loading RAW data from {1}".format(self.name, self.model))
        self.image = rawpy.imread(self.filepath)
        logging.debug("{0}: Color description is {1}".format(self.name, self.image.color_desc))
        self._read()
        self._center_roi()
        
        
    def stats(self):
        logging.debug("{0}: Computing stats".format(self.name))
        r1_mean, r1_vari = self._region_stats(self.signal[R1], self.roi)
        g2_mean, g2_vari = self._region_stats(self.signal[G2], self.roi)
        g3_mean, g3_vari = self._region_stats(self.signal[G3], self.roi)
        b4_mean, b4_vari = self._region_stats(self.signal[B4], self.roi)
        result = {
            'name'            : self.name,
            'roi'             : str(self.roi),
            'mean_raw_signal_R1'  : r1_mean,
            'vari_raw_signal_R1'  : r1_vari,
            'mean_raw_signal_G2'  : g2_mean,
            'vari_raw_signal_G2'  : g2_vari,
            'mean_raw_signal_G3'  : g3_mean,
            'vari_raw_signal_G3'  : g3_vari,
            'mean_raw_signal_B4'  : b4_mean,
            'vari_raw_signal_B4'  : b4_vari,
        }
        if self.dkroi:
            self._extract_dark()
            self._add_dark_stats(result)
        
        mean  = [r1_mean, g2_mean, g3_mean, b4_mean]
        stdev = [round(sqrt(r1_vari),1), round(sqrt(g2_vari),1), round(sqrt(g3_vari),1), round(sqrt(b4_vari),1)]
        logging.info("{0}: ROI = {1}, \u03BC = {2}, \u03C3 = {3} ".format(self.name, self.roi, mean, stdev))
        return result

    # ============== #
    # helper methods #
    # ============== #


    def _iso8601(self, tstamp):
        date = None
        for fmt in ["%Y:%m:%d %H:%M:%S", "%Y:%m:%d %H:%M:%S"]:
            try:
                self._date = datetime.datetime.strptime(tstamp, fmt)
            except ValueError:
                continue
            else:
                break
        if not self._date:
            raise TimestampError(tstamp)
        else:
            return self._date.strftime(DEF_TSTAMP)

    def _lookup(self):
        '''
        Load camera configuration from configuration file
        '''

        self.k, self.step = self.cache.lookup(self.model)

        # if not (os.path.exists(self.camerapath)):
        #     logging.debug("No camera config file found at {0}, using default file".format(self.camerapath))
        #     self.camerapath = DEF_CAMERA_TPL

        # parser  =  ConfigParser.RawConfigParser()
        # # str is for case sensitive options
        # parser.optionxform = str
        # parser.read(self.camerapath)
        # if not parser.has_section(self.metadata['model']):
        #     raise ConfigError(self.model)

        # r1 = chop(parser.get(self.model,"R1"),',')
        # g2 = chop(parser.get(self.model,"G2"),',')
        # g3 = chop(parser.get(self.model,"G3"),',')
        # b4 = chop(parser.get(self.model,"B4"),',')
        # self.k[R1].x, self.k[R1].y, self.step[R1] = int(r1[0]), int(r1[1]), int(r1[2])
        # self.k[G2].x, self.k[G2].y, self.step[G2] = int(g2[0]), int(g2[1]), int(g2[2])
        # self.k[G3].x, self.k[G3].y, self.step[G3] = int(g3[0]), int(g3[1]), int(g3[2])
        # self.k[B4].x, self.k[B4].y, self.step[B4] = int(b4[0]), int(b4[1]), int(b4[2])


    def _region_stats(self, data, region):
        r = data[region.y1:region.y2, region.x1:region.x2]
        return round(r.mean(),1), round(r.var(),2)


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
        r1_mean_dark,   r1_vari_dark   = self._region_stats(self.dark[R1], self.dkroi)
        g2_mean_dark,   g2_vari_dark   = self._region_stats(self.dark[G2], self.dkroi)
        g3_mean_dark,   g3_vari_dark   = self._region_stats(self.dark[G3], self.dkroi)
        b4_mean_dark,   b4_vari_dark   = self._region_stats(self.dark[B4], self.dkroi)
        self.HEADERS.extend(['mean_dark_R1', 'vari_dark_R1', 'mean_dark_G2', 'vari_dark_G2',
                'mean_dark_G3', 'vari_dark_G3', 'mean_dark_B4', 'vari_dark_B4'])
        mydict['mean_dark_R1'] = r1_mean_dark
        mydict['vari_dark_R1'] = r1_vari_dark
        mydict['mean_dark_G2'] = g2_mean_dark
        mydict['vari_dark_G2'] = g2_vari_dark
        mydict['mean_dark_G3'] = g3_mean_dark
        mydict['vari_dark_G3'] = g3_vari_dark
        mydict['mean_dark_B4'] = b4_mean_dark
        mydict['vari_dark_B4'] = b4_vari_dark


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
