#!/usr/bin/env python
# coding=utf-8

import sys
from vmware_discovery.common import config
config.parse_config(sys.argv, 'nova')
CONF = config.CONF

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from vmware_discovery.template import template_manager
template_discovery = template_manager.DiscoveryTemplateManager()
template_discovery._image_template_sync()
template_discovery.template_utils._session.logout()

# vim: tabstop=4 shiftwidth=4 softtabstop=4
