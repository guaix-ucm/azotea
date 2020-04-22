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

import os.path
import logging

# ---------------------
# Third party libraries
# ---------------------


#--------------
# local imports
# -------------

from .        import AZOTEA_CFG_DIR
from .config  import load_config_file
from .image   import REGISTERED, STATS_COMPUTED, METADATA_UPDATED, DARK_SUBSTRACTED
from .image   import NO_CHANGES, CAMERA_CHANGES, OBSERVER_CHANGES

# ----------------
# Module constants
# ----------------

# values for the 'state' column in table


# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("azotea")

# -----------------------
# Module global functions
# -----------------------


def do_change(connection, key, state, change):
	config_path  = os.path.join(AZOTEA_CFG_DIR, key + '.ini')
	file_options = load_config_file(config_path)
	observer     = file_options['observer']
	row          = {'observer': observer, 'state': state }
	cursor       = connection.cursor()
	cursor.execute('''
			SELECT meta_changes
			FROM image_t
			WHERE observer = :observer
			AND state > :state
			LIMIT 1
			''', row)
	flags = cursor.fetchone()
	if flags is not None:
		flags = flags[0]
		flags += change
		row['changes'] = flags
		cursor.execute(
			'''
			UPDATE image_t
			SET state = :state, meta_changes = :changes
			WHERE observer == :observer
			AND state > :state
			''', row)
		connection.commit()
	if cursor.rowcount > 0:
		log.info("Updated processing state of %03d images for %s", cursor.rowcount, key)
	

# =====================
# Command esntry points
# =====================


def changed_observer(connection, options):
	log.info("Changed observer metadata in %s", options.key)
	do_change(connection, options.key, STATS_COMPUTED, OBSERVER_CHANGES)

def changed_location(connection, options):
	log.info("Changed location metadata in %s", options.key)
	do_change(connection, options.key, STATS_COMPUTED, OBSERVER_CHANGES)

def changed_camera(connection, options):
	log.info("Changed camera metadata in %s", options.key)
	do_change(connection, options.key, STATS_COMPUTED, CAMERA_CHANGES)

def changed_image(connection, options):
	log.info("Changed image metadata in %s", options.key)
	do_change(connection, options.key, REGISTERED, NO_CHANGES)
