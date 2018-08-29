#!/usr/bin/env python
# coding=utf-8

import sys
from vmware_discovery.common import config
config.parse_config(sys.argv, 'nova')
CONF = config.CONF

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from vmware_discovery.portgroup import portgroup_manager
portgroup_discovery = portgroup_manager.DiscoveryPortGroupManager()
portgroup_discovery._portgroup_sync()
portgroup_discovery._session.logout()

# vim: tabstop=4 shiftwidth=4 softtabstop=4
