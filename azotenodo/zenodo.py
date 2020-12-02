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
import argparse

#--------------
# local imports
# -------------

from .packer import make_new_release
# -----------------------
# Module global variables
# -----------------------

log     = logging.getLogger("azotenodo")

# -----------------------
# Module global functions
# -----------------------

def setup_context(options, file_options):
    context = argparse.Namespace()

    if options.test:
        context.url_prefix = SANDBOX_URL_PREFIX
        context.doi_prefix = SANDBOX_DOI_PREFIX
    else:
        context.url_prefix = PRODUCTION_URL_PREFIX
        context.doi_prefix = PRODUCTION_DOI_PREFIX
    context.access_token = file_options.api_key
        #context.file         = options.zip_file
    return context


        

def delete(options, file_options):
    pass

def upload(options, file_options):
    pass

def upload_publish(options, file_options):
    log.info("===== CUCUUUU ")
    print(context)
    
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}

    # Headers are not necessary here since "requests" automatically
    # adds "Content-Type: application/json", because we're using
    # the "json=" keyword argument
    # headers=headers,
    url = context.url_prefix + 'deposit/depositions'
    log.info("===== REQUESTINT TO {0} ".format(url))
    r = requests.post(url,
            params=params,
            json={},
            headers=headers)
    log.info("===== STATUS CODE = {0}".format(r.status_code))
    print(r.json())