# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright (c) 2020
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------


# ----------
# Exceptions
# ----------

class NoUserInfoError(Exception):
    '''Working Directory does not contain user configuration data.'''
    def __str__(self):
        s = self.__doc__
        if self.args:
            s = "{0} \n".format(s, self.args[0])
        s = '{0}.'.format(s)
        return s

class MixingCandidates(Exception):
    '''Images processed in different directories.'''
    def __str__(self):
        s = self.__doc__
        if self.args:
            s = "{0} \n".format(s, self.args[0])
        s = '{0}.'.format(s)
        return s

class ConfigError(ValueError):
    '''This camera model is not yet supported by AZOTEA'''
    def __str__(self):
        s = self.__doc__
        if self.args:
            s = "{0}: '{1}'".format(s, self.args[0])
        s = '{0}.'.format(s)
        return s

class MetadataError(ValueError):
    '''Error reading EXIF metadata for image'''
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
