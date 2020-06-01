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

import os
import os.path
import logging
import datetime
import hashlib
import math
import re
import subprocess

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
import numpy as np
import jdcal

#--------------
# local imports
# -------------

from .           import DEF_CAMERA_TPL, DEF_TSTAMP
from .utils      import chop, Point, ROI
from .exceptions import ConfigError, MetadataError, TimestampError

# ----------------
# Module constants
# ----------------

# Array indexes in Bayer pattern
R1 = 0
G2 = 1
G3 = 2
B4 = 3


BG_X1 = 400
BG_Y1 = 200
BG_X2 = 550
BG_Y2 = 350

FRACTION_REGEXP = re.compile(r'(\d+)/(\d+)')


# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("azotea")

# ----------
# Exceptions
# ----------


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

    ExiftoolFixed = False

    HEADERS = [
            'tstamp'         ,
            'name'           ,
            'model'          ,
            'iso'            ,
            'roi'            ,
            'dark_roi'       ,
            'exptime'        ,
            'focal_length'   ,
            'f_number'       ,
            'bias'           ,
            'type'           ,
            'aver_signal_R1',
            'vari_signal_R1',
            'aver_signal_G2',
            'vari_signal_G2',
            'aver_signal_G3',
            'vari_signal_G3',
            'aver_signal_B4',
            'vari_signal_B4',
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
    

    def loadEXIF(self):
        '''Load EXIF metadata'''   
        #log.debug("%s: Loading EXIF metadata",self.name)
        with open(self.filepath, "rb") as f:
            logging.disable(logging.INFO)
            self.exif = exifread.process_file(f, details=False)
            logging.disable(logging.NOTSET)
        if not self.exif:
            self._exiftool()
            #raise MetadataError(self.filepath)

        self.metadata['name']         = self.name
        self.model                    = str(self.exif.get('Image Model'))
        self.metadata['model']        = self.model
        self.metadata['tstamp']       = self._iso8601(str(self.exif.get('Image DateTime', None)))
        self.metadata['iso']          = str(self.exif.get('EXIF ISOSpeedRatings', None))
        self.metadata['focal_length'] = self.getFocalLength()
        self.metadata['f_number']     = self.getFNumber()
        self.metadata['exptime'], self.metadata['type'] = self.getExposureTime()
        self.metadata['bias']         = 0   # Maybe one day we could extract is from EXIF
        self.metadata['night']        = self.night() 
        return self.metadata


    def getExposureTime(self):
        imagetyp = None
        exptime = str(self.exif.get('EXIF ExposureTime', None))
        exptime = self._fraction_to_float(exptime)
        if exptime < 1.0:
            log.warn("Image %s (t=%f) could serve as a BIAS image", self.name, exptime)
            imagetyp = "BIAS"
        return exptime, imagetyp


    def getFNumber(self):
        f_number = str(self.exif.get('EXIF FNumber', None))
        return self._fraction_to_float(f_number)


    def getFocalLength(self):
        temp = str(self.exif.get('EXIF FocalLength', None))
        if temp == '0':
            temp = None
        return self._fraction_to_float(temp)


    def read(self):
        '''Read RAW pixels''' 
        self._lookup()
        log.debug("%s: Loading RAW data from %s", self.name, self.model)
        self.image = rawpy.imread(self.filepath)
        #log.debug("%s: Color description is %s", self.name, self.image.color_desc)
        # R1 channel
        self.signal.append(self.image.raw_image[self.k[R1].x::self.step[R1], self.k[R1].y::self.step[R1]])
        # G2 channel
        self.signal.append(self.image.raw_image[self.k[G2].x::self.step[G2], self.k[G2].y::self.step[G2]])
        # G3 channel
        self.signal.append(self.image.raw_image[self.k[G3].x::self.step[G3], self.k[G3].y::self.step[G3]])
         # B4 channel
        self.signal.append(self.image.raw_image[self.k[B4].x::self.step[B4], self.k[B4].y::self.step[B4]])
        self._center_roi()


    def setROI(self, roi):
        if type(roi) == str:
            self.roi = ROI.strproi(roi_str)
        elif type(roi) == ROI:
            self.roi = roi


    def getJulianDate(self):
        jd2000, mjd = jdcal.gcal2jd(self._date.year, self._date.month, self._date.day)
        fraction = (self._date.hour*3600 + self._date.minute*60 + self._date.second)/86400.0
        return jd2000, mjd + fraction


    def night(self):
        '''Observation night as a grouping attribute'''
        jd2000, mjd = self.getJulianDate()
        mjd -= 0.5  # Take it 12 hours before and make sure it is the same YYYY-MM-DD
        year, month, day, fraction = jdcal.jd2gcal(jd2000, mjd)
        return "{0:04d}-{1:02d}-{2:02d}".format(year, month, day)

        
    def stats(self):
        r1_mean, r1_vari = self._region_stats(self.signal[R1], self.roi)
        g2_mean, g2_vari = self._region_stats(self.signal[G2], self.roi)
        g3_mean, g3_vari = self._region_stats(self.signal[G3], self.roi)
        b4_mean, b4_vari = self._region_stats(self.signal[B4], self.roi)
        result = {
            'name'            : self.name,
            'roi'             : str(self.roi),
            'aver_signal_R1'  : r1_mean,
            'vari_signal_R1'  : r1_vari,
            'aver_signal_G2'  : g2_mean,
            'vari_signal_G2'  : g2_vari,
            'aver_signal_G3'  : g3_mean,
            'vari_signal_G3'  : g3_vari,
            'aver_signal_B4'  : b4_mean,
            'vari_signal_B4'  : b4_vari,
        }
        if self.dkroi:
            self._extract_dark()
            self._add_dark_stats(result)
        
        mean  = [r1_mean, g2_mean, g3_mean, b4_mean]
        stdev = [
            round(math.sqrt(r1_vari),1), 
            round(math.sqrt(g2_vari),1), 
            round(math.sqrt(g3_vari),1), 
            round(math.sqrt(b4_vari),1)
        ]
        log.debug("%s: ROI = %s, \u03BC = %s, \u03C3 = %s ", self.name, self.roi, mean, stdev)
        return result

    # ============== #
    # helper methods #
    # ============== #

    def night(self):
        '''Observation night as a grouping attribute'''
        jd2000, mjd = self.getJulianDate()
        mjd -= 0.5  # Take it 12 hours before and make sure it is the same YYYY-MM-DD
        year, month, day, fraction = jdcal.jd2gcal(jd2000, mjd)
        return "{0:04d}-{1:02d}-{2:02d}".format(year, month, day)

    def _fraction_to_float(self, value):
        try:
            value = float(value)
        except TypeError:
            pass    # This handles when value is None
        except ValueError:
            matchobj = FRACTION_REGEXP.search(value)
            if matchobj:
                value = float(matchobj.group(1))/float(matchobj.group(2))
        return value


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


    def _region_stats(self, data, region):
        r = data[region.y1:region.y2, region.x1:region.x2]
        return round(r.mean(),1), round(r.var(),3)


    def _center_roi(self):
        '''Conditionally sets the Region of interest around the image center'''
        if self.roi.x1 == 0 and self.roi.y1 == 0:
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
        r1_aver_dark,   r1_vari_dark   = self._region_stats(self.dark[R1], self.dkroi)
        g2_aver_dark,   g2_vari_dark   = self._region_stats(self.dark[G2], self.dkroi)
        g3_aver_dark,   g3_vari_dark   = self._region_stats(self.dark[G3], self.dkroi)
        b4_aver_dark,   b4_vari_dark   = self._region_stats(self.dark[B4], self.dkroi)
        self.HEADERS.extend([
                'aver_dark_R1', 'vari_dark_R1', 'aver_dark_G2', 'vari_dark_G2',
                'aver_dark_G3', 'vari_dark_G3', 'aver_dark_B4', 'vari_dark_B4'
                ])
        mydict['aver_dark_R1'] = r1_aver_dark
        mydict['vari_dark_R1'] = r1_vari_dark
        mydict['aver_dark_G2'] = g2_aver_dark
        mydict['vari_dark_G2'] = g2_vari_dark
        mydict['aver_dark_G3'] = g3_aver_dark
        mydict['vari_dark_G3'] = g3_vari_dark
        mydict['aver_dark_B4'] = b4_aver_dark
        mydict['vari_dark_B4'] = b4_vari_dark

    def _exiftool(self):
        '''Load EXIF Data using exiftool subprocess'''
        result = subprocess.run(["exiftool", self.filepath],
                                stdout=subprocess.PIPE, check=True)
        lines = result.stdout.decode('utf-8').split('\n')
        # Parse lines using colon as delimiter
        # and updates the self.exif dictionary
        exif_re = re.compile(r'^([^:]+):(.+)')
        for line in lines:
            matchobj = exif_re.search(line)
            if matchobj:
                key   = matchobj.group(1).strip()
                value = matchobj.group(2).strip()
                self.exif[key] = value

        # Emulates the expected EXIF keywords used in the main EXIF library
        self.exif["Image Model"]          = self.exif["Camera Model Name"]
        self.exif["EXIF ISOSpeedRatings"] = self.exif["ISO"]
        self.exif["Image DateTime"]       = self.exif["Date/Time Original"]
        # Focal length requires additional parsing
        focal_re = re.compile(r'^([^ ]+)')
        matchobj = focal_re.search(self.exif["Focal Length"])
        focal = int(float(matchobj.group(1)))
        self.exif["EXIF FocalLength"]     = focal
        self.exif["EXIF FNumber"]         = self.exif["F Number"]
        self.exif["EXIF ExposureTime"]    = self.exif["Exposure Time"]
        CameraImage.ExiftoolFixed = True

       