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
import sqlite3

#--------------
# local imports
# -------------

from .packer import make_new_release
from . import SANDBOX_DOI_PREFIX, SANDBOX_URL_PREFIX, PRODUCTION_URL_PREFIX, PRODUCTION_DOI_PREFIX, DEF_DBASE
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
        context.access_token = file_options.api_key_sandbox
    else:
        context.url_prefix = PRODUCTION_URL_PREFIX
        context.doi_prefix = PRODUCTION_DOI_PREFIX
        context.access_token = file_options.api_key_production
    return context


def open_database(dbase_path):
    if not os.path.exists(dbase_path):
        with open(dbase_path, 'w') as f:
            pass
        log.info("Created database file {0}".format(dbase_path))
    return sqlite3.connect(dbase_path)


def select_contributors(connection):
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT DISTINCT obs_surname, obs_family_name, organization
        FROM image_t
        WHERE obs_surname IS NOT NULL
        AND obs_family_name IS NOT NULL
        ORDER BY obs_surname ASC
        ''')
    return cursor


def get_contributors(connection):
    contributors = []
    for surname, family_name, organization in select_contributors(connection):
        record = {
            'name': "{0}, {1}".format(surname, family_name),
            'type': 'DataCollector',
            }
        if organization is not None:
            record['affiliation'] = organization
        contributors.append(record)
    return contributors


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


def do_zenodo_list(context, title, published):
    headers = {"Content-Type": "application/json"}
    status  = 'published' if published else 'draft' 
    query = 'type:dataset AND title:{0}'.format(title)
    query = 'title:{0}'.format(title)
    
    params  = {'access_token': context.access_token, 'status':status, 'sort': 'mostrecent', 'q': query}
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

def do_zenodo_search(context, title, published):
    headers = {"Content-Type": "application/json"}
    status  = 'published'
    params  = {'access_token': context.access_token, 'status':status, 'sort': 'mostrecent',}
    url = "{0}/deposit/depositions".format(context.url_prefix)
    
    log.info("Searching dataset with title {0}".format(title))
    log.debug("Deposition List Request to {0} ".format(url))
    r = requests.get(url, params=params, headers=headers)
    response = r.json()
    response = list(filter(lambda item: item['title'] == title, response))
    log.info("Deposition search OK, HTTP status code {0} ".format(r.status_code))
    if context.verbose:
        print("=============== BEGIN DEPOSITION SEARCH BY TITLE RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END DEPOSITION SEARCH BY TITLE RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    return response[0]


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
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}
    log.info("Creating new Deposition for title {0}, version {1} ".format(context.title, context.version))
    url = "{0}/deposit/depositions".format(context.url_prefix)
    log.debug("Deposition Request to {0} ".format(url))
    r = requests.post(url, params=params, headers=headers, json={})
    response = r.json()
    if context.verbose:
        print("=============== BEGIN DEPOSIT CREATION RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END DEPOSIT CREATION RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    log.info("Deposition created with id {0}, HTTP status code {1}".format(response['id'], r.status_code))
    return response


def do_zenodo_metadata(context, identifier):
    log.info("Deposit Metadata for id {0} to Zenodo".format(identifier))

    connection   = open_database(DEF_DBASE)
    contributors = get_contributors(connection)

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
        'contributors': contributors,
        'description': 'Latest monthly AZOTEA reduced CSV files',
        'access_right': 'open',
    }
    url = "{0}/deposit/depositions/{1}".format(context.url_prefix, identifier)
    log.debug("Deposition Metadata Request to {0} ".format(url))
    r = requests.put(url, params=params, headers=headers, json={'metadata':metadata})
    response = r.json()
    if context.verbose:
        print("=============== BEGIN METADATA RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END METADATA RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    log.info("Metadata updated for id {0}, HTTP status code {1}".format(identifier, r.status_code))
    return response


def do_zenodo_upload(context, zip_file, bucket_url):
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}
    filename   = os.path.basename(zip_file)
    url = "{0}/{1}".format(bucket_url, filename)
    with open(zip_file, "rb") as fp:
        log.debug("Deposition File Upload Request to {0} ".format(url))
        r = requests.put(url, data=fp, params=params)
    response = r.json()
    if context.verbose:
        print("=============== BEGIN FILE UPLOAD RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END FILE UPLOAD RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    log.info("Deposition File Upload succesful for {0}, HTTP status code {1} ".format(zip_file, r.status_code))
    return response


def do_zenodo_publish(context, identifier):
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token}
    url = "{0}/deposit/depositions/{1}/actions/publish".format(context.url_prefix, identifier)
    log.info("Publish new dataset for {0}".format(identifier))
    log.debug("Deposition Publish Request to {0} ".format(url))
    r = requests.post(url, params=params, headers=headers, json={})
    response = r.json()
    if context.verbose:
        print("=============== BEGIN PUBLISH RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END PUBLISH RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    log.info("Publication succesful doi = {0}, HTTP status code {1} ".format(response['doi'], r.status_code))
    return context


def do_zenodo_newversion(context, latest_id):
    headers = {"Content-Type": "application/json"}
    params  = {'access_token': context.access_token,}
    url = "{0}/deposit/depositions/{1}/actions/newversion".format(context.url_prefix, latest_id)
    log.info("Creating New Version deposition from {0}".format(latest_id))
    log.debug("Deposition New Version of {1} Request to {0} ".format(url, latest_id))
    r = requests.post(url, params=params, headers=headers, json={})
    response = r.json()
    if context.verbose:
        print("=============== BEGIN DEPOSITION NEW VERSION RESPONSE ===============")
        context.pprinter.pprint(response)
        print("=============== END DEPOSITION NEW VERSION RESPONSE ===============")
    if 400 <= r.status_code <= 599:
        raise Exception(response)
    new_id   = os.path.basename(response['links']['latest_draft'])
    log.info("Deposition New Version succesful, new id = {0}, HTTP status code {1} ".format(new_id, r.status_code))
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
    context.pprinter  = pprint.PrettyPrinter(indent=2)
    context.title     = ' '.join(options.title) # allows Multiword titles
    do_zenodo_list2(context, context.title, options.published)


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
    context.title     = ' '.join(options.title) # allows Multiword titles
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
        response = do_zenodo_search(context, context.title, True)
        latest_id = response['id']
        response = do_zenodo_newversion(context, latest_id)
        new_id   = os.path.basename(response['links']['latest_draft'])
        response = do_zenodo_metadata(context, new_id)
        bucket_url = response["links"]["bucket"]
        response = do_zenodo_upload(context, zip_file, bucket_url)
        response = do_zenodo_publish(context, new_id)
