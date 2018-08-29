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

import string
import time
from oslo_log import log as logger
from oslo_vmware import vim_util

from vmware_discovery.common import config
from vmware_discovery.common import vmwareapi

CONF = config.CONF
LOG = logger.getLogger(__name__)

PROPERTY_FILTER = ['config.name', 'config.template', 'config.instanceUuid',
                   'config.uuid', 'config.guestId', 'config.guestFullName',
                   'config.hardware.device', 'config.files.vmPathName',
                   'config.tools.toolsVersion']

SCSI_DEVICE_TRANSFORM = {'VirtualLsiLogicSASController': 'lsiLogicsas',
                         'ParaVirtualSCSIController': 'paraVirtualscsi',
                         'VirtualBusLogicController': 'busLogic',
                         'VirtualLsiLogicController': 'lsiLogic'}

TRANSFORM_PROPERTIES = {'config.guestId': 'vmware_ostype',
                        'config.template': 'vmware_template',
                        'config.files.vmPathName': 'vmware_path',
                        'config.tools.toolsVersion': 'vmware_toolsversion'}

VNIC_TYPES = ['VirtualE1000', 'VirtualE1000e', 'VirtualPCNet32',
              'VirtualEthernetCard', 'VirtualVmxnet', 'VirtualVmxnet2',
              'VirtualVmxnet3']


class VMwareTemplateImporter(object):

    def __init__(self):
        self._session = None
        self._content = None
        self._init_session_content()

    def _init_session_content(self):
        if self._content is None:
            LOG.info("Create session for vCenter service.")
            self._session = vmwareapi.VMwareAPISession()
            if self._session:
                LOG.info("Retrieved session service content for vCenter queries")
                self._content = self._session.vim.service_content

    def _get_all_vms(self):
        """
        Find all virtual machines in the vCenter. Since templates and virtual machines look similar
        except for the config.templates property
        Get up to 3000 objects, get all objects = false
        """
        start_time = time.time()
        vmObjects = []
        temp_objects = vim_util.get_objects(self._session.vim,
                                            'VirtualMachine',
                                            CONF.discovery_common.property_collector_max,
                                            PROPERTY_FILTER,
                                            False)
        while temp_objects is not None:
            vmObjects += temp_objects.objects
            temp_objects = vim_util.continue_retrieval(self._session.vim, temp_objects)
        LOG.info("Found {0!s} Virtual machines and templates in VMware in \
                 {1!s}s".format(len(vmObjects), (time.time() - start_time)))
        return vmObjects

    def retrieve_vm_templates(self):
        """
        Create a list of Objects (virtual machine templates)
        The templates is identified by the config.templates boolean property
        Once the property is found, save the object to our return list and
        move to the next object
        """
        templatesOCs = []
        for objContent in self._get_all_vms():
            try:
                for propSet in objContent.propSet:
                    if propSet.name == "config.template" and propSet.val is True:
                        templatesOCs.append(objContent)
                        break
            except:
                LOG.info("No object property set for %s", objContent)
        LOG.info("Found %s VMware templates in VMware", len(templatesOCs))
        return templatesOCs

    def get_disk_size_in_byte(self, device):
        size = 0
        if hasattr(device, 'capacityInBytes'):
           size = int(device.capacityInBytes)
        else:
           size = int(device.capacityInKB) * 1024
        return size

    def render_properties(self, propSets):
        """
        This function takes the list of property sets from the collector
        and creates a new dictionary, with where each key has the prefix
        tempalte_ for use with the glance image
        """
        properties = {}
        properties['size'] = 0
        properties['root_disk_size'] = 0
        properties['nic_num'] = 0
        for propSet in propSets:
            propKey = 'template_' + string.lower(propSet.name[string.rindex(propSet.name, '.') + 1:])
            if propSet.name in TRANSFORM_PROPERTIES:
                propKey = TRANSFORM_PROPERTIES[propSet.name]
            if propSet.name == 'config.hardware.device':
                for device in propSet.val.VirtualDevice:
                    if device.__class__.__name__ in VNIC_TYPES:
                        properties['nic_num'] += 1
                    # Cover the different scsi controller types
                    if device.key == 1000 and device.__class__.__name__ in SCSI_DEVICE_TRANSFORM.keys():
                        properties['vmware_adaptertype'] = SCSI_DEVICE_TRANSFORM[device.__class__.__name__]
                    # Only root disk will be written to template property 'root_disk_size'
                    if device.__class__.__name__ == 'VirtualDisk' and device.deviceInfo.label == "Hard disk 1":
                        properties['root_disk_size'] = self.get_disk_size_in_byte(device)
                    # It is difficult to detect eagerZeroThick, so we just support Thin or preallocated
                    if device.key >= 2000 and device.key < 3000 and device.__class__.__name__ == 'VirtualDisk':
                        propKey = 'vmware_disktype'
                        if device.backing.thinProvisioned:
                            properties[propKey] = 'thin'
                        else:
                            properties[propKey] = 'preallocated'
                        properties['size'] += self.get_disk_size_in_byte(device)
                    if device.key >= 3000 and device.key < 4000 and device.__class__.__name__ == 'VirtualDisk':
                        properties['vmware_adaptertype'] = "ide"
                        properties['size'] += self.get_disk_size_in_byte(device)
                    # Cover the different network adapter types
                    if device.key == 4000:
                        properties['hw_vif_model'] = device.__class__.__name__
            elif propSet.name == 'config.files.vmPathName':
                properties[propKey] = propSet.val.replace("[", "/").\
                                                  replace('] ', "/").\
                                                  replace(" ", "_")
            else:
                if propKey == 'template_name':
                    properties[propKey] = CONF.template.image_prefix + unicode(propSet.val)
                else:
                    properties[propKey] = unicode(propSet.val)
        return properties

    def template_exists_as_vm(self, instance_uuid):
        template = self._session.invoke_api(self._session.vim,
                                            'FindByUuid',
                                            self._content.searchIndex,
                                            uuid=instance_uuid,
                                            vmSearch=True,
                                            instanceUuid=True)
        if template is None:
            return False
        return True

# vim: tabstop=4 shiftwidth=4 softtabstop=4
