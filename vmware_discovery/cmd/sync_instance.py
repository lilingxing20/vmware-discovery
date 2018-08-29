#!/usr/bin/env python
# coding=utf-8

import traceback
import sys
from vmware_discovery.common import config
config.parse_config(sys.argv, 'nova')

from vmware_discovery.instance import instance_manager

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def main():
    try:
        instance_discovery = instance_manager.DiscoveryInstanceManager()
        instance_discovery._instance_sync()
        instance_discovery.driver._session.logout()
    except Exception:
        traceback.print_exc()
        raise


if __name__ == "__main__":
    sys.exit(main())

# vim: tabstop=4 shiftwidth=4 softtabstop=4
