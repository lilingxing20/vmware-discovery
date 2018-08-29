# coding=utf-8

# Copyright 2014 Vsettan Corp.
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

from sqlalchemy.orm import exc as orm_exc
from oslo_log import log as logger

from vmware_discovery.common import config
from vmware_discovery.common import db_session
from vmware_discovery.common.client import factory as clients
from vmware_discovery.common.gettextutils import _
from vmware_discovery.common.models import Standardattribute, Network, Subnet, Ml2Segment

LOG = logger.getLogger(__name__)

CONF = config.CONF


class PortGroupDB():
    def __init__(self):
        self._tenant_id = self._get_tenant_id()
        self._create_session()

    def _get_tenant_id(self):
        keystone = clients.LOCAL.keystone
        tenants = keystone.tenants.list()
        for tenant in tenants:
            if tenant.name == CONF.discovery_common.tenant_name:
                return tenant.id
        return None

    def _make_network_dict(self, network):
        net = {'id': network.id,
               'name': network.name,
               'tenant_id': network.tenant_id,
               'admin_state_up': network.admin_state_up,
               'status': network.status,
               # #'shared': network.shared
               }
        return net

    def _create_session(self):
        self.session = db_session.get_neutron_session()

    def close(self):
        self.session.close()

    def get_network_by_name(self, name):
        try:
            query = self.session.query(Network)
            data = query.filter(Network.name == name).one()
            return self._make_network_dict(data)
        except orm_exc.NoResultFound as e:
            LOG.exception("Error no result found, message: %s" % e)
            return None

    def get_network(self, pg):
        try:
            name = pg['portgroup']
            vlanid = pg['vlanid']
            physical_dev = pg['physical_dev']
            query = self.session.query(Network)
            data = query.filter(Network.name == name).all()
            for net in data:
                sgm = self.get_network_segments(net.id)
                sgm_id = sgm.segmentation_id if sgm.segmentation_id else 0
                if (sgm_id == vlanid and
                   sgm.physical_network == physical_dev):
                    return net
            return None
        except orm_exc.NoResultFound as e:
            LOG.exception("Error no result found, message: %s" % e)
            return None

    def get_network_by_uuid(self, uuid):
        try:
            query = self.session.query(Network)
            data = query.filter(Network.id == uuid).one()
            return self._make_network_dict(data)
        except orm_exc.NoResultFound as e:
            LOG.exception("Error no result found, message: %s" % e)
            return None

    def get_network_segments(self, network_id):
        try:
            query = self.session.query(Ml2Segment)
            data = query.filter(
                Ml2Segment.network_id == network_id).one()
            return data
        except orm_exc.NoResultFound as e:
            LOG.warning(_("No segment of network:%(net-id)s is found, "
                          "reason:%(reason)s"),
                        {"net-id": network_id,
                         "reason": e})
            return None

    def update_network_segments(self, portgroup, segment):
        vlan_id = portgroup["vlanid"]
        physical_dev = portgroup["physical_dev"]

        change_log = ""
        segment_dict = {}

        if vlan_id == 0:
            vlan_id = None

        if vlan_id != segment.segmentation_id:
            if not vlan_id:
                network_type = "flat"
                vlan_id = None
            else:
                network_type = "vlan"

            segment_dict["network_type"] = network_type
            segment_dict["segmentation_id"] = vlan_id
            change_log += ("network_type:changed to %s;"
                           "segmentation_id: changed from "
                           "%s to %s;"
                           ) % (network_type,
                                segment.segmentation_id,
                                vlan_id)

        if physical_dev != segment.physical_network:
            segment_dict["physical_network"] = physical_dev
            change_log += ("physical_network: changed from "
                           "%s to %s;") % (physical_dev,
                                           segment.physical_network)
        if segment_dict:
            segment.update(segment_dict)
            self.session.commit()
            LOG.info("Updated segment %s", segment.id)
            LOG.info("Changelog: %s" % change_log)

        else:
            LOG.info("No need to update segment %s", segment.id)

    def create_network_and_segment(self, portgroup):
        # Create network
        net = self.create_network(portgroup)
        # Create segment
        if net:
            self.create_segment(net['id'], portgroup)

    def create_segment(self, net_id, portgroup):
        vlan_id = portgroup["vlanid"]
        physical_dev = portgroup["physical_dev"]
        if vlan_id != 0:
            segment = {
                "network_type": "vlan",
                "physical_network": physical_dev,
                "segmentation_id": vlan_id}
        # if network type is flat
        else:
            segment = {
                "network_type": "flat",
                "physical_network": physical_dev,
                "segmentation_id": None}
        self._add_segment(net_id, segment)

    def create_network(self, portgroup):
        if not self._tenant_id:
            LOG.warning(_("Tenant Id can not be empty! Abort importing."))
            return None
        attribute = {'resource_type': 'networks'}
        attribute = self._add_standardattributes(attribute)
        if not attribute['id']:
            return None
        network = {"name": portgroup['portgroup'],
                   "tenant_id": self._tenant_id,
                   "admin_state_up": 1,
                   "standard_attr_id": attribute['id'],
                   # #"shared": True,
                   "status": "ACTIVE"}
        return self._add_network(network)

    def get_networks(self):
        return self.session.query(Network).all()

    def delete_network(self, net):
        try:
            net.delete(self.session)
        except Exception:
            _msg = ("Network deletion failed, because network is needed "
                    "by other resources(VM, port, subnet, etc.)")
            LOG.warning(_msg)
            self.session.rollback()

    def _add_network(self, network):
        if not network:
            return None

        net = Network(**network)
        net.save(self.session)

        network['id'] = getattr(net, 'id')
        LOG.info("Added network %s.", network['id'])
        return network

    def _add_standardattributes(self, attribute):
        if not attribute:
            return None

        attr = Standardattribute(**attribute)
        attr.save(self.session)

        attribute['id'] = getattr(attr, 'id')
        LOG.info("Added standardattribute %s.", attribute['id'])
        return attribute

    def _add_segment(self, net_id, segment):
        segment['network_id'] = net_id
        segm = Ml2Segment(**segment)
        segm.save(self.session)
        LOG.info("Added segment %s.", segm.id)
        return segment

# vim: tabstop=4 shiftwidth=4 softtabstop=4
