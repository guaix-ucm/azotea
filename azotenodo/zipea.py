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

import logging
import requests


#--------------
# local imports
# -------------


# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("azotenodo")

# -----------------------
# Module global functions
# -----------------------

def upload_to_zenodo(context):
    log.info("===== CUCUUUU ")
    print(context)
    
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}

    # Headers are not necessary here since "requests" automatically
    # adds "Content-Type: application/json", because we're using
    # the "json=" keyword argument
    # headers=headers,
    r = requests.post(context.url_prefix + 'deposit/depositions',
            params=params,
            json={},
            headers=headers)
    log.info("===== STATUS CODE = {0}".format(r.status_code))
    print(r.json())