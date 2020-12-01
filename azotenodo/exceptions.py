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

