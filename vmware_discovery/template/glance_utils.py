# coding=utf-8
# Copyright 2014 Vsettan Corp.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
from oslo_log import log as logger
from oslo_utils import encodeutils
from vmware_discovery.common import exception
from vmware_discovery.common import config
from glanceclient import Client as glanceClient
from keystoneclient.v2_0 import client as kc

CONF = config.CONF
LOG = logger.getLogger(__name__)

PROPERTY_CHECK_LIST = ['template_name', 'vmware_ostype', 'template_guestfullname',
                       'vmware_adaptertype', 'vmware_disktype', 'hw_vif_model',
                       'vmware_template', 'template_instanceuuid', 'vcenter_ip',
                       'vmware_path', 'vmware_toolsversion', 'nic_num',
                       'root_disk_size', 'size']

INT_ATTR_LIST = ['vmware_toolsversion', 'nic_num', 'root_disk_size', 'size']


class glanceImporter():
    def __init__(self):
        self._glanceapi = None
        self._glancev2api = None
        self._connect_glanceapi()

    def _connect_glanceapi(self):
        if self._glanceapi is None:
            keystoneAuthUrl = CONF.openstack.auth_url
            keystoneUserName = CONF.openstack.admin_user
            keystonePassword = CONF.openstack.admin_password
            keystoneTenant = CONF.openstack.admin_tenant_name
            osInsecure = CONF.openstack.http_insecure
            osCacert = CONF.openstack.connection_cacert
            target_region = CONF.discovery_common.target_region
            LOG.info("Obtain token for tenant %s through %s, with user %s",
                     keystoneTenant, keystoneAuthUrl, keystoneUserName)
            keystoneClient = kc.Client(username=keystoneUserName,
                                       password=keystonePassword,
                                       tenant_name=keystoneTenant,
                                       insecure=osInsecure,
                                       cacert=osCacert,
                                       auth_url=keystoneAuthUrl)

            glanceEndpoint = None
            possibleEndpoints = keystoneClient.service_catalog.\
                    get_endpoints(endpoint_type='publicURL')['image']

            # First check for a configured target region
            if target_region:
                for endpoint in possibleEndpoints:
                    if endpoint['region'] == target_region:
                        glanceEndpoint = endpoint['publicURL']
                        break

            # If no configured target region, check for environment variable OS_REGION_NAME
            if glanceEndpoint is None:
                envRegion = os.environ.get('OS_REGION_NAME')
                if envRegion and len(envRegion) > 0:
                    for endpoint in possibleEndpoints:
                        if endpoint['region'] == envRegion:
                            glanceEndpoint = endpoint['publicURL']
                            break

            # Finally, raise an exception
            if glanceEndpoint is None:
                raise exception.GlanceRegionEndpointNotFound(target_region=target_region,
                        os_region_name=os.environ.get('OS_REGION_NAME'))

            LOG.info("Connecting to glance service %s", glanceEndpoint)
            self._glanceapi = glanceClient(
                '1',
                endpoint=glanceEndpoint,
                token=keystoneClient.auth_ref.auth_token,
                insecure=osInsecure,
                cacert=osCacert)
            self._glancev2api = glanceClient(
                '2',
                endpoint=glanceEndpoint,
                token=keystoneClient.auth_ref.auth_token,
                insecure=osInsecure,
                cacert=osCacert)

    def retrieve_template_images(self):
        """
        Generates a dictionary that is keyed off the instanceuuid. This will help
        provide only VMware templates, instead of all the images in glance. In v2
        tags can be used to improve the performance by filtering
        """
        list_limit = CONF.template.list_limit
        imageList = self._glanceapi.images.list(limit=list_limit,
                                                 page_size=list_limit)
        imageDict = {}
        for image in imageList:
            if 'template_name' in image.properties:
                LOG.info("Found image for VMware templates %s", image.name)
                imageDict[image.id] = image
        LOG.info("Found %s VMware templates in glance", len(imageDict))
        return imageDict

    def hasImagePropertiesChanged(self, new_properties, old_properties):
        """
        This method will compare the core keys needed for template deploy:
        template_name, vmware_ostype, vmware_adaptertype, vmware_disktype,
        hw_vif_model, template_instanceuuid
        It will also account for removal of properties as well
        """
        new_keys = new_properties.keys()
        old_keys = old_properties.keys()

        for key in PROPERTY_CHECK_LIST:
            new_key = key in new_keys
            old_key = key in old_keys
            if old_key == new_key:
                # Key not exist for both Old and New
                if not new_key:
                    continue
                if key in INT_ATTR_LIST:
                    if int(old_properties[key]) != int(new_properties[key]):
                        return True
                else:
                    if encodeutils.safe_encode(old_properties[key]) != encodeutils.safe_encode(new_properties[key]):
                        return True
            else:
                return True
        return False

    def getClient(self):
        return self._glanceapi

    def getv2Client(self):
        return self._glancev2api

# vim: tabstop=4 shiftwidth=4 softtabstop=4
