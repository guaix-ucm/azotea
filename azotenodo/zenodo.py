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

# ------------
# Real actions
# ------------

def do_zenodo_licenses(context):
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token,}
    url = "{0}/licenses/".format(context.url_prefix)
    log.debug("Licenses List Request to {0} ".format(url))
    r = requests.get(url, params=params, headers=headers)
    log.info("Licenses List Status Code {0} ".format(r.status_code))
    response = r.json()
    if context.verbose:
        print("="*80)
        context.pprinter.pprint(response)
        print("="*80)
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    return response


def do_zenodo_list(context):
    headers = {"Content-Type": "application/json"}
    status  = 'published' if context.published else 'draft' 
    params  = {'access_token': context.access_token, 'status':status}
    url = "{0}/deposit/depositions".format(context.url_prefix)
    log.debug("Deposition List Request to {0} ".format(url))
    r = requests.get(url, params=params, headers=headers)
    log.info("Deposition List Status Code {0} ".format(r.status_code))
    response = r.json()
    if context.verbose:
        print("=============== BEGIN DEPOSIT LISTING RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END DEPOSIT LISTING RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    return response


def do_zenodo_delete(context, identifier):
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}
    url = "{0}/deposit/depositions/{1}".format(context.url_prefix, identifier)
    log.debug("Deposition Delete  Request to {0} ".format(url))
    r = requests.delete(url, params=params, headers=headers)
    log.info("Deposition Delete Status Code {0} ".format(r.status_code))
    response = r.json()
    if context.verbose:
        print("=============== BEGIN DEPOSIT DELETION RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END DEPOSIT DELETETION RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    return response


def do_zenodo_deposit(context):
    log.info("Deposit new version {0} to Zendodo".format(context.version))
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}
    url = "{0}/deposit/depositions".format(context.url_prefix)
    log.debug("Deposition Request to {0} ".format(url))
    r = requests.post(url, params=params, headers=headers, json={})
    log.info("Deposition Status Code {0} ".format(r.status_code))
    response = r.json()
    if context.verbose:
        print("=============== BEGIN DEPOSIT CREATION RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END DEPOSIT CREATION RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    return response


def do_zenodo_metadata(context, identifier):
    log.info("Deposit Metadata for id {0} to Zendodo".format(identifier))
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}
    metadata = {
        'title' : context.title,
        'upload_type': 'dataset',
        'version' : context.version,
        'communities': [ {'identifier': context.community} ],
        'creators' : [
            {'name': 'Zamorano, Jaime', 'affiliation': 'UCM', 'orcid': 'https://orcid.org/0000-0002-8993-5894'},
            {'name': 'González, Rafael','affiliation': 'UCM', 'orcid': 'https://orcid.org/0000-0002-3725-0586'}
        ],
        'description': 'Latest monthly AZOTEA reduced CSV files',
        'access_right': 'open',
    }
    url = "{0}/deposit/depositions/{1}".format(context.url_prefix, identifier)
    log.debug("Deposition Metadata Request to {0} ".format(url))
    r = requests.put(url, params=params, headers=headers, json={'metadata':metadata})
    log.info("Deposition Metadata Status Code {0} ".format(r.status_code))
    response = r.json()
    if context.verbose:
        print("=============== BEGIN METADATA RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END METADATA RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    return response


def do_zenodo_upload(context, zip_file, bucket_url):
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}
    filename   = os.path.basename(zip_file)
    url = "{0}/{1}".format(bucket_url, filename)
    with open(zip_file, "rb") as fp:
        log.debug("Deposition File Upload Request to {0} ".format(url))
        r = requests.put(url, data=fp, params=params)
        log.info("Deposition File Upload Status Code {0} ".format(r.status_code))
    response = r.json()
    if context.verbose:
        print("=============== BEGIN FILE UPLOAD RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END FILE UPLOAD RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    return response


def do_zenodo_publish(context, identifier):
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}
    url = "{0}/deposit/depositions/{1}/actions/publish".format(context.url_prefix, identifier)
    log.debug("Deposition Publish Request to {0} ".format(url))
    r = requests.post(url, params=params, headers=headers, json={})
    log.info("Deposition Publish Status Code {0} ".format(r.status_code))
    response = r.json()
    if context.verbose:
        print("=============== BEGIN PUBLISH RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END PUBLISH RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    return context


def do_zenodo_newversion(context, latest_id):
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token,}
    url = "{0}/deposit/depositions/{1}/actions/newversion".format(context.url_prefix, latest_id)
    log.debug("Deposition New Version of {1} Request to {0} ".format(url, latest_id))
    r = requests.post(url, params=params, headers=headers, json={})
    log.info("Deposition New Version Request Status Code {0} ".format(r.status_code))
    response = r.json()
    if context.verbose:
        print("=============== BEGIN DEPOSITION NEW VERSION RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END DEPOSITION NEW VERSION RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    return response

# ========
# COMMANDS
# ========

def zenodo_licenses(options, file_options):
    context = setup_context(options, file_options)
    context.verbose  = options.verbose
    context.pprinter = pprint.PrettyPrinter(indent=2)
    do_zenodo_licenses(context)


def zenodo_list(options, file_options):
    context = setup_context(options, file_options)
    context.verbose   = options.verbose
    context.published = options.published
    context.pprinter  = pprint.PrettyPrinter(indent=2)
    do_zenodo_list(context)


def zenodo_delete(options, file_options):
    context = setup_context(options, file_options)
    context.verbose  = options.verbose
    context.pprinter = pprint.PrettyPrinter(indent=2)
    identifier       = options.id
    do_zenodo_delete(context, identifier)


def zenodo_pipeline(options, file_options):
    first_time, changed, version = make_new_release(options)
    if not changed:
        log.info("No need to upload new version to Zendodo")
        return

    context = setup_context(options, file_options)
    context.verbose   = options.verbose
    context.pprinter  = pprint.PrettyPrinter(indent=2)
    context.title     = options.title
    context.community = options.community
    context.version   = version if options.version is None else options.version
    zip_file          = options.zip_file

    if first_time:
        response = do_zenodo_deposit(context)
        new_id = response['id']
        response = do_zenodo_metadata(context, new_id)
        bucket_url = response["links"]["bucket"]
        response = do_zenodo_upload(context, zip_file, bucket_url)
        response = do_zenodo_publish(context, new_id)
    else:
        latest_id = options.id if options.id is not None else file_options.record_id
        response = do_zenodo_newversion(context, latest_id)
        new_id   = os.path.basename(response['links']['latest_draft'])
        response = do_zenodo_metadata(context, new_id)
        bucket_url = response["links"]["bucket"]
        response = do_zenodo_upload(context, zip_file, bucket_url)
        response = do_zenodo_publish(context, new_id)
