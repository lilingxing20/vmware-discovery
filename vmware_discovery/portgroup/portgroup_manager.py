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

from oslo_log import log as logger
from oslo_vmware import exceptions
from oslo_service import loopingcall

from vmware_discovery.common import config
from vmware_discovery.common import vmwareapi
from vmware_discovery.common.gettextutils import _

from network_util import PortGroupDB
import vmware_util
import uuidutil

LOG = logger.getLogger(__name__)

CONF = config.CONF


class DiscoveryPortGroupManager(object):
    """Class for port group sync."""

    def __init__(self):
        self._port_group_filters = CONF.portgroup.port_group_filter_list
        self.sync_interval = CONF.portgroup.portgroup_sync_interval
        self.allow_neutron_deletion = CONF.portgroup.allow_neutron_deletion
        self.allow_neutron_sync = CONF.portgroup.allow_neutron_sync
        self.network_prefix = CONF.portgroup.network_prefix
        self._cluster_name = CONF.discovery_common.cluster_name
        self._esxi_host = CONF.discovery_common.esxi_host
        self._load_physical_network_mappings()
        self._session = vmwareapi.VMwareAPISession()

    def sync(self):
        def _sync():
            LOG.debug(_('Syncing all port group on interval'))
            self._portgroup_sync()
        sync_call = loopingcall.FixedIntervalLoopingCall(_sync)
        sync_call.start(interval=self.sync_interval, initial_delay=self.sync_interval)

    def _portgroup_sync(self):
        if not self.allow_neutron_sync:
            LOG.info(_("Do not need synchronization network port group."))
            return

        pg_list = []
        if self._esxi_host:
            standard_pgs = self.get_standard_port_groups_on_host(self._esxi_host)
            dvs_pgs = self.get_dvs_port_groups_on_host(self._esxi_host)
            pg_list = standard_pgs + dvs_pgs

        elif self._cluster_name:
            standard_pgs = self.get_standard_port_groups_on_cluster(self._cluster_name)
            dvs_pgs = self.get_dvs_port_groups_on_cluster(self._cluster_name)
            pg_list = standard_pgs + dvs_pgs

        self._import_port_groups(pg_list)

    def _load_physical_network_mappings(self):
        self._physical_network_mappings = {}

        raw_mappings = CONF.portgroup.physical_network_mappings
        for mapping in raw_mappings:
            parts = mapping.split(':')
            if len(parts) != 2:
                LOG.debug('Invalid physical network mapping: %s', mapping)
            else:
                pattern = parts[0].strip()
                vswitch = parts[1].strip()
                self._physical_network_mappings[pattern] = vswitch
        if not self._physical_network_mappings:
            LOG.error("physical_network_mappings property is empty. "
                      "This property is required. Format is <physnet>:<vswitch>. "
                      "sample: "
                      "physical_network_mappings=physnet1:vswitch,physnet2:dvSwitch")
            raise exceptions.InvalidPropertyException

    def _filter_portgroup_by_mor(self, portgroup):
        """Filter port group.

        @param portgroup: port group Data Object
        @return: port group information in a dict
        """
        _spec = portgroup.spec

        portgroup_info = {"vswitchName": _spec.vswitchName,
                          "portgroup": _spec.name,
                          "vlanid": _spec.vlanId}

        return self._filter_portgroup_by_dict(portgroup_info)

    def _filter_portgroup_by_dict(self, portgroup_info):

        vswitch_name = portgroup_info["vswitchName"]
        pg_name = portgroup_info["portgroup"]
        vlanid = portgroup_info["vlanid"]

        portgroup_dict = {}

        def _revert_dict(dict):
            new_dict = {}
            for key in dict.keys():
                new_dict[dict[key]] = key

            return new_dict

        maps = _revert_dict(self._physical_network_mappings)
        filters = self._port_group_filters
        # If the vswitch has a physical device mapping
        # and the port group name passes the filter
        if vswitch_name in maps:
            if not filters or pg_name in filters:
                portgroup_dict["portgroup"] = pg_name
                portgroup_dict["vlanid"] = vlanid
                portgroup_dict["physical_dev"] = maps[vswitch_name]

        return portgroup_dict

    def _get_pg_name_list(self, port_groups):
        pg_name_list = []
        for pg in port_groups:
            pg_name_list.append(pg['portgroup'])
        return pg_name_list

    def _get_uuid_and_name(self, pg_name):
        if len(pg_name) >= 36:
            tail = pg_name[-36:]
            if uuidutil.is_uuid_like(tail):
                name = "" if len(pg_name) == 36 else pg_name[0:-37]
                return (tail, name)
        return (None, pg_name)

    def _get_pg_net_name_with_uuid(self, net):
        name = "%s-%s" % (net.name, net.id) if net.name else net.id
        return name

    def _get_nets_to_be_deleted(self, db_conn, local_nets, vmware_nets):
        deleted_nets = []
        for net in local_nets:
            sgm = db_conn.get_network_segments(net.id)
            net_dict = {}
            if sgm and self.network_prefix in net.name:
                net_dict = {
                    'portgroup': net.name[len(self.network_prefix):],
                    'vlanid': sgm.segmentation_id if sgm.segmentation_id else 0,
                    'physical_dev': sgm.physical_network
                }
            if net_dict and net_dict not in vmware_nets:
                deleted_nets.append(net)
        return deleted_nets

    def _get_discovered_name(self, orig_name):
        return "%s%s" % (self.network_prefix, orig_name)

    def _import_port_groups(self, port_groups):
        # Check the port group updates
        print "********************* start sync port group *********************"
        LOG.info("Going to import port groups: %s", port_groups)
        db_conn = PortGroupDB()
        existing_nets = db_conn.get_networks()
        deleted_nets = self._get_nets_to_be_deleted(db_conn, existing_nets, port_groups)

        for portgroup in port_groups:
            pg_name = portgroup["portgroup"]
            print 'found portgroup: %s' % pg_name

            uuid, name = self._get_uuid_and_name(pg_name)
            # if there is an uuid in the pg_name, the port group is created
            # by neutron dvs mechanism driver
            if uuid:
                LOG.info("Network '%s' is created by DVS Mechanism driver." % name)
                LOG.info("Start checking existence of network:'%s' in current Cloud.", name)
                net = db_conn.get_network_by_uuid(uuid)
                if net:
                    LOG.info("Network '%s' is created by current Cloud.", name)
                else:
                    discovered_name = self._get_discovered_name(pg_name)
                    LOG.info("Network '%s' is created by other Cloud, will sync it as %s."
                             % (name, discovered_name))
                    name = discovered_name
            else:
                discovered_name = self._get_discovered_name(name)
                LOG.info("Network '%s' is created by VCenter, will sync it as %s."
                         % (name, discovered_name))
                name = discovered_name

            portgroup['portgroup'] = name
            net = db_conn.get_network(portgroup)
            if not net:
                LOG.info("Network:'%s' doesn't exist, "
                         "now creating.", name)
                # Write the updated port groups into db
                print 'create net: %s' % name
                db_conn.create_network_and_segment(portgroup)
        if self.allow_neutron_deletion:
            for net in deleted_nets:
                LOG.info("Network:'%s' was deleted in vcenter, "
                         "now delete it from neutron", net.name)
                print 'remove net: %s' % name
                db_conn.create_network_and_segment(portgroup)
                db_conn.delete_network(net)
                LOG.info("Network:'%s' deletion completed." % net.name)
        db_conn.close()
        print "********************* end sync port group *********************"

    def get_standard_port_groups_on_cluster(self, cluster_name):
        """Sync standard port groups into neutron db.

        Get standard port groups in a cluster and import
        them into neutron db as network instances.
        """
        LOG.info("Start to get standard port "
                 "groups in cluster: %s", cluster_name)

        try:
            # Get cluster's mor from the given cluster name
            cluster_ref = vmware_util.get_cluster_ref_from_name(
                self._session,
                cluster_name)

            # Get the host mor list from the cluster
            host_ref_list = vmware_util.get_host_ref_list_from_cluster_ref(
                self._session,
                cluster_ref)

            # This dict is used to store port groups on all hosts
            port_group_dict_by_host = {}

            # Get all the port groups on all hosts
            for host in host_ref_list:
                # Get port group Data Objects on host
                portgroups = vmware_util.\
                    get_port_group_list_from_host_ref(
                        self._session,
                        host)

                # Get the port group name,vlanId,physical device
                # filter them and make them to a dict
                # and put them into a list
                portgroup_list = []
                for portgroup in portgroups:
                    # filtering
                    portgroup_dict = self._filter_portgroup_by_mor(portgroup)
                    if portgroup_dict:
                        portgroup_list.append(portgroup_dict)

                # Put the port group info into the dict key'ed by hostname
                port_group_dict_by_host[host.value] = portgroup_list
                LOG.info("<%(host)s> Got port group %(portgroup)s",
                         {"portgroup": portgroup_list,
                          "host": host.value})

            # Get common port groups among all the hosts
            common_port_groups = vmware_util.\
                get_common_port_groups(port_group_dict_by_host)

            if common_port_groups:
                return common_port_groups
            else:
                LOG.info("There are no standard port groups to "
                         "import and update.")
                return []

        except Exception as e:
            LOG.exception("Error occurred, message: %s" % e)

    def get_standard_port_groups_on_host(self, host_name):
        """Sync standard port groups into neutron db.

        Get standard port groups in a host and import
        them into neutron db as network instances.
        """
        LOG.info("Start to get standard port "
                 "groups in host: %s", host_name)
        try:
            host_ref = vmware_util.get_host_ref_from_name(self._session, host_name)
            portgroups = vmware_util.\
                    get_port_group_list_from_host_ref(
                        self._session,
                        host_ref)
            # Get the port group name,vlanId,physical device
            # filter them and make them to a dict
            # and put them into a list
            portgroup_list = []
            for portgroup in portgroups:
                # filtering
                portgroup_dict = self._filter_portgroup_by_mor(portgroup)
                if portgroup_dict:
                    portgroup_list.append(portgroup_dict)
            if portgroup_list:
                return portgroup_list
        except Exception as e:
            LOG.exception("Error occurred, message: %s" % e)

    def get_dvs_port_groups_on_cluster(self, cluster_name):
        """Sync Distributed port groups into neutron db.

        Get distributed port groups in a cluster and import
        them into neutron db as network instances.
        """
        LOG.info("Start to get distributed port "
                 "group in cluster %s", cluster_name)
        try:
            # Get cluster's mor from the given cluster name
            cluster_ref = vmware_util.get_cluster_ref_from_name(
                self._session,
                cluster_name)

            host_list = vmware_util.get_host_list_from_cluster_ref(
                self._session, cluster_ref)

            dvs_pg_list = vmware_util.get_dvs_pg_from_cluster(
                self._session, cluster_ref)

            dvs_pg_info_list = []
            for dvs_pg in dvs_pg_list:
                dvs_pg_name = vmware_util.get_dvs_pg_name(
                    self._session, dvs_pg)

                pg_hosts = vmware_util.get_host_on_dvpg(
                    self._session, dvs_pg)

                pg_hosts = set(pg_hosts)
                host_list = set(host_list)
                if pg_hosts.issuperset(host_list):
                    dvs = vmware_util.get_dvs_of_dvpg(self._session, dvs_pg)
                    vlanid = vmware_util.get_vlan_of_dvpg(
                        self._session, dvs_pg)
                    if not isinstance(vlanid, list):
                        dvs_pg_info = {"portgroup": dvs_pg_name,
                                       "vlanid": vlanid,
                                       "vswitchName": dvs}

                        dvs_pg_dict = self._filter_portgroup_by_dict(
                            dvs_pg_info)

                        if dvs_pg_dict:
                            dvs_pg_info_list.append(dvs_pg_dict)

            if dvs_pg_info_list:
                LOG.info("Got dvs port groups:%s to be imported.",
                         dvs_pg_info_list)
                return dvs_pg_info_list
            else:
                LOG.info("There are no distributed port groups to "
                         "import and update.")
                return []
        except Exception as e:
            LOG.exception("Error occurred, message: %s", e)

    def get_dvs_port_groups_on_host(self, host_name):
        try:
            host_ref = vmware_util.get_host_ref_from_name(self._session, host_name)
            dvs_pg_list = vmware_util.get_dvs_pg_from_host(
                    self._session, host_ref)

            dvs_pg_info_list = []

            for dvs_pg in dvs_pg_list:
                dvs_pg_name = vmware_util.get_dvs_pg_name(
                        self._session, dvs_pg)
                dvs = vmware_util.get_dvs_of_dvpg(self._session, dvs_pg)
                vlanid = vmware_util.get_vlan_of_dvpg(
                    self._session, dvs_pg)
                if not isinstance(vlanid, list):
                    dvs_pg_info = {"portgroup": dvs_pg_name,
                                   "vlanid": vlanid,
                                   "vswitchName": dvs}

                    dvs_pg_dict = self._filter_portgroup_by_dict(
                        dvs_pg_info)

                    if dvs_pg_dict:
                        dvs_pg_info_list.append(dvs_pg_dict)

                if dvs_pg_info_list:
                    LOG.info("Got dvs port groups:%s to be imported.",
                             dvs_pg_info_list)
                    return dvs_pg_info_list
                else:
                    LOG.info("There are no distributed port groups to "
                             "import and update.")
                    return []
        except Exception as e:
            LOG.exception("Error occurred, message: %s" % e)

# vim: tabstop=4 shiftwidth=4 softtabstop=4
