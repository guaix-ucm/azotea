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

def do_change(connection, key, state):
	config_path  = os.path.join(AZOTEA_CFG_DIR, key + '.ini')
	file_options = load_config_file(config_path)
	observer     = file_options['observer']
	row          = {'observer': observer, 'state': state }
	cursor       = connection.cursor()
	cursor.execute(
		'''
		UPDATE image_t
		SET state = :state
		WHERE observer == :observer
		AND state > :state
		''', row)
	connection.commit()
	if cursor.rowcount > 0:
		log.info("Updated for %03d images with metadata".cursor.rowcount)
	

# =====================
# Command esntry points
# =====================


def changed_observer(connection, options):
	log.info("Changed observer metadata in %s", options.key)
	do_change(connection, options.key, STATS_COMPUTED)

def changed_location(connection, options):
	log.info("Changed location metadata in %s", options.key)
	do_change(connection, options.key, STATS_COMPUTED)

def changed_camera(connection, options):
	log.info("Changed camera metadata in %s", options.key)
	do_change(connection, options.key, STATS_COMPUTED)

def changed_image(connection, options):
	log.info("Changed image metadata in %s", options.key)
	do_change(connection, options.key, REGISTERED)
