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
import os.path
import pprint
import json

#--------------
# local imports
# -------------

from .packer import make_new_release
from . import SANDBOX_DOI_PREFIX, SANDBOX_URL_PREFIX, PRODUCTION_URL_PREFIX, PRODUCTION_DOI_PREFIX
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

def zenodo_upload_publish(options, file_options):
    log.info("===== CUCUUUU ")
    print(context)
    
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}

    # Headers are not necessary here since "requests" automatically
    # adds "Content-Type: application/json", because we're using
    # the "json=" keyword argument
    # headers=headers,
    url = context.url_prefix + 'deposit/depositions'
    log.debug("===== REQUESTINT TO {0} ".format(url))
    r = requests.post(url,
            params=params,
            json={},
            headers=headers)
    log.info("===== STATUS CODE = {0}".format(r.status_code))
    print(r.json())

# ========
# COMMANDS
# ========

def zenodo_list(options, file_options):
    context = setup_context(options, file_options)
    headers = {"Content-Type": "application/json"}
    status = 'published' if options.published else 'draft' 
    params  = {'access_token': context.access_token, 'status':status}

    url = context.url_prefix + 'deposit/depositions'
    log.debug("Deposition List Request to {0} ".format(url))
    r = requests.get(url, params=params, headers=headers)
    log.debug("Status code {0} ".format(r.status_code))
    pp = pprint.PrettyPrinter(indent=2)
    print("="*80)
    pp.pprint(r.json())
    print("="*80)
    


def zenodo_delete(options, file_options):
    context = setup_context(options, file_options)
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}
    url = context.url_prefix + 'deposit/depositions/' + str(options.id)
    log.debug("Deposition Delete  Request to {0} ".format(url))
    r = requests.delete(url, params=params, headers=headers)
    log.debug("Status code {0} ".format(r.status_code))
    #print(r.json())


def zenodo_upload(options, file_options):
    changed, version = make_new_release(options)
    if not changed:
        log.info("No need to upload new version to Zendodo")
        return

    
    # -------------------------------------
    # First we create a new Entry in Zenodo
    # -------------------------------------

    log.info("Uploading new version {0} to Zendodo".format(version))
    context = setup_context(options, file_options)
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}
    url = context.url_prefix + 'deposit/depositions'
    log.debug("Deposition Upload Request to {0} ".format(url))
    r = requests.post(url, params=params, headers=headers, json={})
    log.debug("Status code {0} ".format(r.status_code))
    
    response = r.json()
    deposition_id = response['id']
    pp = pprint.PrettyPrinter(indent=2)
    print("="*80)
    pp.pprint(r.json())
    print("="*80)

    # -----------------------
    # Then we upload the file
    # -----------------------

    bucket_url = response["links"]["bucket"]
    filename = os.path.basename(options.zip_file)

    url = "{0}/{1}".format(bucket_url, filename)
    with open(options.zip_file, "rb") as fp:
        log.debug("File Upload Request to {0} ".format(url))
        r = requests.put(url, data=fp, params=params)
        pp.pprint(r.json())
        print("="*80)

    # ------------------------
    # Fianlly, we add metadata
    # ------------------------

    metadata = {
        'title' : 'AZOTEA dataset',
        'upload_type': 'dataset',
        'communities': [ {'identifier': 'AZOTEA'},],
        'creators' : [
            {'name': 'Zamorano, Jaime', 'affiliation': 'UCM', 'orcid': 'https://orcid.org/0000-0002-8993-5894'},
            {'name': 'González, Rafael','affiliation': 'UCM', 'orcid': 'https://orcid.org/0000-0002-3725-0586'}
        ],
        'description': 'Latest monthly AZOTEA reduced CSV files',
        'access_right': 'open',
    }

    data = {
        'metadata': {
            'title' : 'AZOTEA dataset',
            'upload_type': 'dataset',
            #'communities': [ {'identifier': 'AZOTEA'},],
            'creators' : [
                {'name': 'Zamorano, Jaime', 'affiliation': 'UCM', 'orcid': 'https://orcid.org/0000-0002-8993-5894'},
                {'name': 'González, Rafael','affiliation': 'UCM', 'orcid': 'https://orcid.org/0000-0002-3725-0586'}
            ],
            'description': 'Latest monthly AZOTEA reduced CSV files',
            'access_right': 'open',
        }
    }

    # data = {
    #    'metadata': {
    #         'title': 'My first upload',
    #          'upload_type': 'poster',
    #          'description': 'This is my first upload',
    #          'creators': [{'name': 'Doe, John',
    #                        'affiliation': 'Zenodo'}]
    #      }
    # }

    url = context.url_prefix + 'deposit/depositions/' + str(deposition_id)
    log.debug("Deposition Metadata Request to {0} ".format(url))
    r = requests.put(url, params=params, headers=headers, data=json.dumps(data))
    log.debug("Status code {0} ".format(r.status_code))
    



def zenodo_publish(options, file_options):
    pass


