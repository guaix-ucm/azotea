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
    log.info("===== TRASSSS ")

	# headers = {"Content-Type": "application/json"}
 #    params = {'access_token': apikey}

#     r = requests.post('https://sandbox.zenodo.org/api/deposit/depositions',
#                    params=params,
#                    json={},
#                    # Headers are not necessary here since "requests" automatically
#                    # adds "Content-Type: application/json", because we're using
#                    # the "json=" keyword argument
#                    # headers=headers,
#                    headers=headers)
# >>> r.status_code
# 201
# >>> r.json()