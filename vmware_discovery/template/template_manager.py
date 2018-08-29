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

"""
VMware Driver ImageManager service
"""

from oslo_service import loopingcall
from oslo_log import log as logger

from vmware_discovery.common import config
from vmware_discovery.common.gettextutils import _

import template_importer as vmu
import glance_utils as gu

CONF = config.CONF
LOG = logger.getLogger(__name__)


class DiscoveryTemplateManager(object):

    all_templates = None
    template_utils = vmu.VMwareTemplateImporter()

    def __init__(self):
        self.sync_interval = CONF.template.template_sync_interval
        self.allow_template_sync = CONF.template.allow_template_sync
        self.allow_template_deletion = CONF.template.allow_template_deletion

    def sync(self):
        def _sync():
            LOG.debug(_('Syncing all instance template on interval'))
            self._image_template_sync()
        sync_call = loopingcall.FixedIntervalLoopingCall(_sync)
        sync_call.start(interval=self.sync_interval, initial_delay=self.sync_interval)

    """ Main method that kicks of the reconciliation of templates """
    def _image_template_sync(self):

        if not self.allow_template_sync:
            LOG.info(_("Don't need to be synchronized virtual machine template."))
            return

        print "********************** start sync images **********************"
        glance_utils = gu.glanceImporter()

        """Get all the data we need to process VMware template_importer and glance images"""
        all_templates = self.all_templates
        if all_templates is None:
            all_templates = self.template_utils.retrieve_vm_templates()
        glance_images = glance_utils.retrieve_template_images()

        glance_image_template_names = \
                [value.properties['template_name'] for (key, value) in glance_images.items()]
        glance_image_template_instanceuuid = []
        for (key, value) in glance_images.items():
            if 'template_instanceuuid' in value.properties:
                glance_image_template_instanceuuid.append(value.properties['template_instanceuuid'])

        LOG.debug("template_names is %s", glance_image_template_names)
        LOG.debug("templdate instance uuid is %s", glance_image_template_instanceuuid)

        for template in all_templates:
            try:
                template_properties = None
                template_properties = self.template_utils.render_properties(template.propSet)
                template_properties.update({"vcenter_ip": CONF.vmware.host_ip})
                template_properties['vmware_path'] = "http://" + CONF.vmware.host_ip + template_properties.get('vmware_path', "")

                if template_properties['template_instanceuuid'] in glance_image_template_instanceuuid:
                    print "update glance image (%s) by instance uuid" % template_properties['template_name']
                    id = self._get_image_uuid_by_template_instance_uuid(template_properties['template_instanceuuid'],
                                                                         glance_images)
                    image = glance_images[id]
                    LOG.info("Found glance image: %s", image.name)

                    if image.size == 0 and template_properties['size'] > 0:
                        LOG.info("Found image size 0 image %s(%s), re-attempt to update its size.", image.name, image.id)
                        glance_utils.getClient().images.update(image.id, size=template_properties['size'])
                    elif glance_utils.hasImagePropertiesChanged(image.properties, template_properties):
                        LOG.info("Reconciling property mis-match original: {0!s} new: {1!s}".format(image.properties, template_properties))
                        glance_utils.getClient().images.update(image.id,
                                                               name=template_properties['template_name'],
                                                               properties=template_properties)
                    del glance_images[id]
                elif template_properties['template_name'] in glance_image_template_names:
                    print "update glance image (%s) by instance name" % template_properties['template_name']
                    id = self._get_image_uuid_by_template_name(template_properties['template_name'], glance_images)
                    image = glance_images[id]
                    LOG.info("Found glance image: %s", image.name)

                    if image.size == 0 and template_properties['size'] > 0:
                        LOG.info("Found image size 0 image %s(%s), re-attempt to update its size.", image.name, image.id)
                        glance_utils.getClient().images.update(image.id, properties=template_properties, size=template_properties['size'])
                    elif glance_utils.hasImagePropertiesChanged(image.properties, template_properties):
                        merged_properties = image.properties.copy()
                        merged_properties.update(template_properties)
                        LOG.info("Reconciling property mis-match original: {0!s} new: {1!s}".format(image.properties, merged_properties))
                        glance_utils.getClient().images.update(image.id,
                                                               name=template_properties['template_name'],
                                                               properties=merged_properties)
                    del glance_images[id]
                else:
                    LOG.info("Creating glance image: %s", template_properties['template_name'])
                    print "insert glance image: %s" % template_properties['template_name']
                    image = glance_utils.getClient().images.create(name=template_properties['template_name'],
                                                                   properties=template_properties,
                                                                   size=0,
                                                                   container_format="bare",
                                                                   disk_format='vmdk',
                                                                   is_public=True)
                    # After the image creation, update the image right way so as to write the size value.
                    glance_utils.getClient().images.update(image.id, size=template_properties['size'])

            except Exception as e:
                if template_properties:
                    LOG.warning("Template %(name)s(id:%(id)s) has errors when syncing, reason: %(reason)s",
                                {"name": template_properties['template_name'],
                                 "id": template_properties['template_instanceuuid'],
                                 "reason": e})
                else:
                    LOG.error("Template sync error: %s", e)

        LOG.info("Allow deletion for orphan template images: %s", self.allow_template_deletion)
        for orphan in glance_images.values():
            LOG.debug("orphan name: %s", orphan.name)
            if 'template_instanceuuid' in orphan.properties:
                try:
                    if self.template_utils.template_exists_as_vm(orphan.properties['template_instanceuuid']):
                        LOG.info("Template %s has been converted to a VM, will delete it if allow_template_deletion is enabled", orphan.name)
                    if self.allow_template_deletion:
                        if CONF.vmware.host_ip == orphan.properties.get('vcenter_ip'):
                            print "Removal of glance image %s for vcenter %s" % (orphan.name, CONF.vmware.host_ip)
                            LOG.info("Removal of glance image %s for vcenter %s", orphan.name, CONF.vmware.host_ip)
                            glance_utils.getClient().images.delete(orphan.id)
                        else:
                            LOG.info("Removal of glance image %s skipped due to template vcenter_ip %s does not match %s",
                                     orphan.name, orphan.properties.get('vcenter_ip'), CONF.vmware.host_ip)
                except Exception as e:
                        LOG.warning("Template %(name)s(id:%(id)s) has errors when syncing, reason: %(reason)s",
                                    {"name": orphan.name,
                                     "id": orphan.properties['template_instanceuuid'],
                                     "reason": e})

        print "********************** end sync images **********************"

    def _get_image_uuid_by_template_name(self, template_name, glance_images):
        for (key, value) in glance_images.items():
            if 'template_name' in value.properties:
                if value.properties['template_name'] == template_name:
                    return key
        return None

    def _get_image_uuid_by_template_instance_uuid(self, template_instanceuuid, glance_images):
        for (key, value) in glance_images.items():
            if 'template_instanceuuid' in value.properties:
                if value.properties['template_instanceuuid'] == template_instanceuuid:
                    return key
        return None

# vim: tabstop=4 shiftwidth=4 softtabstop=4
