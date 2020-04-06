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

class NoBatchError(ValueError):
    '''No batch to operate upon.'''
    def __str__(self):
        s = self.__doc__
        if self.args:
            s = "{0} \nre-run '{1} --new --work-dir WORK_DIR'".format(s, self.args[0])
        s = '{0}.'.format(s)
        return s

class NoWorkDirectoryError(ValueError):
    '''No working directory specified.'''
    def __str__(self):
        s = self.__doc__
        if self.args:
            s = "{0} \nre-run '{1} --new --work-dir WORK_DIR'".format(s, self.args[0])
        s = '{0}.'.format(s)
        return s