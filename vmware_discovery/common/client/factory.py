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

from vmware_discovery.common.client import service
from vmware_discovery.common.client.config import CONF
from vmware_discovery.common.client.config import OS_OPTS
from vmware_discovery.common.constants import SERVICE_TYPES

"""sample useage

List the services types on the local openstack host:

    known_lcl_service_types = factory.LOCAL.get_service_types()

"""

# global access to local openstack and vmware services
LOCAL = None

if LOCAL is None:
    keystone = service.KeystoneService(str(SERVICE_TYPES.identity),
                                       CONF['openstack']['keystone_version'],
                                       OS_OPTS['auth_url'], OS_OPTS,
                                       None).new_client()
    LOCAL = service.ClientServiceCatalog(OS_OPTS, keystone)
