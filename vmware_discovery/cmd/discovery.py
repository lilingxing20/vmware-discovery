# coding=utf-8
"""
*************************************************************
Licensed Materials - Property of Vsettan

OCO Source Materials

(C) Copyright Vsettan Corp. 2016 All Rights Reserved

The source code for this program is not published or other-
wise divested of its trade secrets, irrespective of what has
been deposited with the U.S. Copyright Office.
*************************************************************
"""

import sys
import traceback

from oslo_log import log
from nova import service
from nova import utils

from vmware_discovery.common import config


def main():
    CONF = config.CONF
    try:
        log.register_options(CONF)
        config.parse_config(sys.argv, 'nova')
        log.setup(CONF, 'vmware')
        utils.monkey_patch()
        server = service.Service.create(manager=CONF.discovery_common.discovery_manager,
                                        binary='nova-vmware-discovery')
        service.serve(server)
        service.wait()
    except Exception:
        traceback.print_exc()
        raise

# vim: tabstop=4 shiftwidth=4 softtabstop=4
