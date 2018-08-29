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

import urllib
from oslo_vmware import exceptions
from oslo_vmware import vim_util
from oslo_log import log as logger

from vmware_discovery.common import config

LOG = logger.getLogger(__name__)
CONF = config.CONF


class ResourceNotFoundException(exceptions.VimException):
    """Thrown when can not find a Cluster by a given name."""
    pass


def _get_token(results):
    """Get the token from the property results."""
    return getattr(results, 'token', None)


def _get_object_by_value(results, value):
    """Get object by value.

    Get the desired object from the given objects
    result by the given value.
    """
    if results is None:
        LOG.error(("Object set is empty, "
                   "got nothing by value %s"), value)
        return None

    for object in results.objects:
        if object.propSet[0].val == value:
            return object.obj


def _get_object_by_type(results, type_value):
    """Get object by type.

    Get the desired object from the given objects
    result by the given type.
    """
    return [obj for obj in results
            if obj._type == type_value]


def _get_object_from_results(session, results, value, func):
    """Get object from results.

    Get the desired object from the given objects
    result by the given value.
    """
    while results:
        object = func(results, value)
        if object:
            session.invoke_api(
                vim_util,
                "cancel_retrieval",
                session.vim,
                results)
            return object

        else:
            return None


def get_cluster_ref_from_name(session, cluster_name):
    """Get reference of Cluster MOR by the cluster name.

    @param session: VMwareAPISession used for vcenter api call
    @param cluster_name: the name of cluster to be fetched
    @return: the Managed Object Reference of Cluster
    """
    LOG.info("try to fetch cluster MOR by cluster name %s...",
             cluster_name)
    results = session.invoke_api(
        vim_util, 'get_objects', session.vim,
        "ClusterComputeResource",
        CONF.discovery_common.property_collector_max,
        ["name"])

    cluster_ref = _get_object_from_results(
        session, results, value=cluster_name,
        func=_get_object_by_value)

    if cluster_ref is None:
        LOG.warning("Could not get cluster MOR by cluster name %s.",
                 cluster_name)
        raise ResourceNotFoundException("Cluster %s not found!",
                                        cluster_name)
    else:
        LOG.info("Got cluster MOR by cluster name %s.",
                 cluster_name)

    return cluster_ref


def get_host_ref_from_name(session, host_name):
    """Get reference of Host MOR by the host name

    @param session: VMwareAPISession used for vcenter api call
    @param host_name: the name of host to be fetched
    @return: the Managed Object Reference of host
    """
    LOG.info("try to fetch host MOR by host name %s...",
             host_name)
    results = session.invoke_api(
        vim_util, 'get_objects', session.vim,
        "HostSystem",
        CONF.discovery_common.property_collector_max,
        ["name"])

    host_ref = _get_object_from_results(
        session, results, value=host_name,
        func=_get_object_by_value)

    if host_ref is None:
        LOG.warning("Could not get Host MOR by host name %s.",
                 host_name)
        raise ResourceNotFoundException("Host %s not found!",
                                        host_name)
    else:
        LOG.info("Got host MOR by host name %s.",
                 host_name)

    return host_ref


def get_host_ref_list_from_cluster_ref(session, cluster_ref):
    """Get reference of host MOR list from a given cluster_ref.

    @param session: VMwareAPISession used for vcenter api call
    @param cluster_ref: the reference of cluster to be fetched
    @return: The list of host MORs
    """
    LOG.info("Getting host MOR list on this cluster...")
    host_ref_list = None
    if cluster_ref:
        host_ref_list = session.invoke_api(vim_util,
                                           'get_object_property',
                                           session.vim,
                                           cluster_ref,
                                           "host")
        host_ref_list = getattr(host_ref_list,
                                "ManagedObjectReference",
                                None)

    if not host_ref_list:
        LOG.warning("No host MOR was found in cluster MOR")
        raise ResourceNotFoundException("Host not found!")

    return host_ref_list


def get_host_list_from_cluster_ref(session, cluster_ref):
    """Get list of host names from a given cluster_ref.

    @param session: VMwareAPISession used for vcenter api call
    @param cluster_ref: the reference of cluster to be fetched
    @return: The list of host names
    """
    host_ref_list = get_host_ref_list_from_cluster_ref(session, cluster_ref)
    return [h.value for h in host_ref_list]


def get_host_ref_list_from_cluster_name(session, cluster_name):
    """Get reference of host list in a given cluster_name.

    @param session: VMwareAPISession used for vcenter api call
    @param cluster_name: the name of cluster to be fetched
    @return: The list of host MORs
    """
    cluster_ref = get_cluster_ref_from_name(session, cluster_name)
    return get_host_ref_list_from_cluster_ref(session, cluster_ref)


def get_network_system_ref_from_host_ref(session, host_ref):
    """Get reference of networkSystem in a given host_ref.

    @param session: VMwareAPISession used for vcenter api call
    @param host_ref: the reference of host to be fetched
    @return: the network system MOR
    """
    return session.invoke_api(
        vim_util, 'get_object_property',
        session.vim, host_ref,
        "configManager.networkSystem")


def get_port_group_list_from_host_ref(session, host_ref):
    """Get reference of port group list from a given host_ref.

    @param session: VMwareAPISession used for vcenter api call
    @param host_ref: the reference of host to be fetched
    @return: the port group Data Object on this host
    """

    LOG.info("Getting port groups on a given host %s",
             host_ref.value)
    network_system_ref = get_network_system_ref_from_host_ref(
        session, host_ref)

    return session.invoke_api(
        vim_util, 'get_object_property',
        session.vim, network_system_ref,
        "networkInfo.portgroup").HostPortGroup


def get_dvs_pg_from_cluster(session, cluster_ref):
    """Get reference of dvs port group list from a given cluster.

    @param session: VMwareAPISession used for vcenter api call
    @param cluster_ref: the reference of cluster to be fetched
    @return: the dvs port group Data Object on this cluster
    """
    LOG.info("Getting dvs portgroups...")
    net_list = session.invoke_api(vim_util,
                                  'get_object_property',
                                  session.vim,
                                  cluster_ref,
                                  "network")
    net_list = getattr(net_list,
                       "ManagedObjectReference",
                       None)

    if net_list:
        type_value = "DistributedVirtualPortgroup"
        return _get_object_by_type(net_list, type_value)
    return []


def get_dvs_pg_from_host(session, host_ref):
    """Get reference of dvs port group list from a given cluster.

    @param session: VMwareAPISession used for vcenter api call
    @param cluster_ref: the reference of cluster to be fetched
    @return: the dvs port group Data Object on this cluster
    """
    LOG.info("Getting dvs portgroups...")
    net_list = session.invoke_api(vim_util,
                                  'get_object_property',
                                  session.vim,
                                  host_ref,
                                  "network")
    net_list = getattr(net_list,
                       "ManagedObjectReference",
                       None)

    if net_list:
        type_value = "DistributedVirtualPortgroup"
        return _get_object_by_type(net_list, type_value)
    return []


def get_dvs_pg_name(session, dvs_pg_ref):
    """Get the name of a dvs port group."""
    pg_name =session.invoke_api(
        vim_util, 'get_object_property', session.vim,
        dvs_pg_ref, "name")
    return urllib.unquote(pg_name)


def get_host_on_dvpg(session, dvs_pg_ref):
    """Get the hosts that the given dvs port group covers."""
    hosts = session.invoke_api(vim_util,
                               'get_object_property',
                               session.vim,
                               dvs_pg_ref,
                               "host")
    hosts = getattr(hosts, "ManagedObjectReference", None)
    if hosts:
        return [h.value for h in hosts]
    return []


def get_dvs_of_dvpg(session, dvs_pg_ref):
    """Get the dvs of given dvs port group."""
    dvs = session.invoke_api(
        vim_util, 'get_object_property', session.vim,
        dvs_pg_ref, "config.distributedVirtualSwitch")
    return session.invoke_api(
        vim_util, 'get_object_property', session.vim,
        dvs, "name")


def get_vlan_of_dvpg(session, dvs_pg_ref):
    """Get the vlan id of give dvs port group."""
    config = session.invoke_api(
        vim_util, 'get_object_property', session.vim,
        dvs_pg_ref, "config.defaultPortConfig")
    return config.vlan.vlanId


def get_common_port_groups(port_group_list_by_host):
    """Get common groups among all the hosts.

    @param port_group_list_by_host: the dictionary of port
    groups on each host, the format is
    {hostname1:[
    {"portgroup":pg1l,"vlanid":vlanId11,"physical_dev":dev11},
    {"portgroup":pg12,"vlanid":vlanId12,"physical_dev":dev12}],
     hostname2:[
    {"portgroup":pg2l,"vlanid":vlanId21,"physical_dev":dev21},
    {"portgroup":pg22,"vlanid":vlanId22,"physical_dev":dev22}]}.

    For example:
    {"host1":[
    {"portgroup":"br-1","vlanid":1,"physical_dev":phy1},
    {"portgroup":"br-2","vlanid":2,"physical_dev":phy2}],
     hostname2:[
    {"portgroup":"br-1","vlanid":1,"physical_dev":phy1},
    {"portgroup":"br-3","vlanid":2,"physical_dev":phy2}]}.

    @return: the common port groups on all hosts,
    example: {"portgroup":"br-1","vlanid":1,"physical_dev":phy1}
    """

    LOG.info("Getting common port groups among all the host...")
    if not port_group_list_by_host:
        return {}

    common_port_group_list = []

    # Get the all the hosts as the keys
    host_keys = port_group_list_by_host.keys()

    # Get the port groups on first host, and make it as the compare base
    port_groups_on_first_host = port_group_list_by_host[host_keys[0]]

    # Compare the port groups on the first host to those on the rest hosts.
    for portgroup in port_groups_on_first_host:
        is_common = True
        for i in range(1, len(host_keys)):
            port_groups_on_curr_host = port_group_list_by_host[host_keys[i]]

            if portgroup not in port_groups_on_curr_host:
                is_common = False
                break

    # If a port group is on all the host and has same port group name,
    # vlan id and physical device name, it is a common port group
        if is_common:
            common_port_group_list.append(portgroup)
    LOG.info("Got common port groups:%s", common_port_group_list)
    return common_port_group_list

# vim: tabstop=4 shiftwidth=4 softtabstop=4
