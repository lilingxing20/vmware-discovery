COPYRIGHT = """
*************************************************************
Licensed Materials - Property of Vsettan

OCO Source Materials

(C) Copyright Vsettan Corp. 2016 All Rights Reserved

The source code for this program is not published or other-
wise divested of its trade secrets, irrespective of what has
been deposited with the U.S. Copyright Office.
*************************************************************
"""

from vmware_discovery.common import config
from vmware_discovery.common import netutils

CONF = config.CONF

# http client opts from config file normalized
# to keystone client form
OS_OPTS = None


def _build_base_http_opts(config_section, opt_map):
    configuration = CONF[config_section]
    opt_map['tenant_name'] = configuration['admin_tenant_name']
    opt_map['username'] = configuration['admin_user']
    opt_map['password'] = configuration['admin_password']
    opt_map['cacert'] = configuration['connection_cacert']
    opt_map['insecure'] = configuration['http_insecure']
    if opt_map['insecure'] is False:
        opt_map['auth_url'] = netutils.hostname_url(configuration['auth_url'])
    else:
        opt_map['auth_url'] = configuration['auth_url']
    return opt_map


# init client opts for vmware and openstack only once
if OS_OPTS is None:
    OS_OPTS = _build_base_http_opts('openstack', {})
