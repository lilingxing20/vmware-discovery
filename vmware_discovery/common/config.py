# coding=utf-8

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

"""Config file utility

"""
import constants

from oslo_cache import core as cache
from oslo_config import cfg
from nova import rpc
from nova import objects

CONF = cfg.CONF


FILE_OPTIONS = {
    '': [],
    'openstack': [
        # Keystone info
        cfg.StrOpt('auth_url', default='http://localhost:5000/v2.0/'),
        cfg.StrOpt('admin_user'),
        cfg.StrOpt('admin_password', secret=True),
        cfg.StrOpt('admin_tenant_name'),
        cfg.StrOpt('connection_cacert', default=None),
        cfg.BoolOpt('http_insecure', default=False),
        cfg.StrOpt('keystone_version', default="v3")
    ],
    'discovery_common': [
        cfg.StrOpt('discovery_manager',
                   default='vmware_discovery.discovery_manager.VMwareDiscoveryManager'),
        cfg.StrOpt('staging_project_name',
                   default=constants.DEFAULT_STAGING_PROJECT_NAME,
                   help=('Hosting OS staging project name. This project must '
                         'exist in the hosting OS')),
        cfg.StrOpt('staging_user',
                   default=constants.DEFAULT_STAGING_USER_NAME,
                   help=('The user should exist and have access to the project '
                         'identified by staging_project_name.')),
        cfg.StrOpt('tenant_name',
                   default='admin',
                   help='The name of tenant the network will imported into'),
        cfg.StrOpt('cluster_name', default=None,
                   help='Names of VMware Cluster ComputeResource.'
                        'Example:cluster_name=cluster1'),
        cfg.StrOpt('esxi_host', default=None,
                    help='Names of VMware ESXi host'),
        cfg.StrOpt('property_collector_max',
                   default=4000,
                   help='The number of objects return by the VMware property collector'),
        cfg.StrOpt('target_region', default='RegionOne',
                   help=('Target region for template discovery (used to select '
                         'correct glance endpoint)'))
    ],
    'template': [
        cfg.BoolOpt('allow_template_deletion', default=False,
                   help=('Allow deletion orphan template in glance which does '
                        'not exist in vCenter')),
        cfg.BoolOpt('allow_template_sync', default=True,
                   help=('Allow sync template in vCenter which does not exist '
                        'in openstack glance')),
        cfg.IntOpt('template_sync_interval', default=300,
                   help=('Template periodic sync interval specified in seconds.')),
        cfg.StrOpt('vmware_default_image_name', default='VMwareUnknownImage',
                   help=('Default name for image for discovered VMware instances')),
        cfg.StrOpt('image_prefix', default='DiscoveredImage-',
                    help=('The prefix that will be added to the name of '
                         'discovered image templates')),
        cfg.StrOpt('list_limit', default=500,
                   help='Number of images to list from glance')
    ],
    'portgroup': [
        cfg.BoolOpt('allow_neutron_deletion', default=False,
                   help=('Allow deletion orphan network in neutron which does '
                        'not exist in vCenter')),
        cfg.BoolOpt('allow_neutron_sync', default=True,
                   help=('Allow sync network in vCenter which does not exist '
                        'in openstack neutron')),
        cfg.IntOpt('portgroup_sync_interval', default=300,
                    help=('Portgroup periodic sync interval specified in '
                          'seconds.')),
        cfg.StrOpt('default_network_name', default="VMwareUnknownNetwork",
                   help=('Default name for network for discovered VMware instances')),
        cfg.StrOpt('default_vlan_id', default=4096,
                   help=('Default name for network vlan id for discovered VMware instances')),
        cfg.StrOpt('default_physical_dev', default='vmware_physical',
                   help=('Default name for network physical dev for discovered VMware instances')),
        cfg.StrOpt('network_prefix', default="DiscoveredNet-",
                    help=('The prefix that will be added to the name of '
                         'discovered networks')),
        cfg.StrOpt('neutron_connection', secret=True,
                   help=('The SQLAlchemy connection string used to connect to '
                        'the database')),
        cfg.ListOpt('physical_network_mappings', default=[],
                    help='_List of <physical_network>:<vswitch> '),
        cfg.ListOpt('port_group_filter_list', default=[],
                    help='List of [portgroup1,portgroup2]')
    ],
    'instance': [
        cfg.BoolOpt('allow_instance_deletion', default=False,
                     help=('Allow deletion orphan instances in openstack which'
                        ' does not exist in vCenter')),
        cfg.BoolOpt('allow_instance_sync', default=True,
                     help=('Allow sync instances in vCenter which does not exist '
                        'in openstack')),
        cfg.IntOpt('instance_sync_interval', default=20,
                    help=('Instance periodic sync interval specified in seconds.')),
        cfg.IntOpt('full_instance_sync_frequency', default=30,
                    help=('How many instance sync intervals between full instance '
                          'syncs. Only instances known to be out of sync are '
                          'synced on the interval except after this many '
                          'intervals when all instances are synced.')),
        cfg.StrOpt('instance_prefix', default='DiscoveredVM-',
                    help=('The prefix that will be added to the name of '
                         'discovered instances')),
        cfg.StrOpt('vmware_default_flavor_name', default='VMwareUnknownFlavor',
                   help=('Default name for flavor for discovered VMware instances')),
        cfg.ListOpt('vm_ignore_list', default=[],
                    help=('List of virtual machines to ignore, '
                          'Example: vm_ignore_list=[vm_name_1, vm_name_2 ...]')),
        cfg.StrOpt('resource_pool_path', default=None,
                    help='Names of VMware resource pool.Used together with'
                         'host name or esxi host. '
                         'If the user specifies a esxi host name and a resource '
                         'pool name, it means the resource pool under the host '
                         'is the target, '
                         'Example: resource_pool_path=host1:pool;'
                         'If the user specifies a cluster name and a resource '
                         'pool name, it means the resource pool under the '
                         'cluster is the target,'
                         'Example: resource_pool_path=cluster1:pool;')
    ],
}


for section in FILE_OPTIONS:
    for option in FILE_OPTIONS[section]:
        if section:
            CONF.register_opt(option, group=section)
        else:
            CONF.register_opt(option)

CONF.import_opt('compute_manager', 'nova.service')
CONF.import_opt('compute_topic', 'nova.compute.rpcapi')
CONF.import_opt('default_availability_zone', 'nova.availability_zones')
CONF.import_opt('compute_driver', 'nova.virt.driver')
cache.configure(CONF)
objects.register_all()


def parse_discovery_config(argv, base_project, base_prog=None):
    """
    Loads configuration information from vmware.conf as well as a project
    specific file.  Expectation is that all vmware config options will be in
    the common vmware.conf file and the base_project will represent open stack
    component configuration like nova.conf or cinder.conf. A base_prog file
    name can be optionally specified as well. That is a specific file name to
    use from the specified open stack component. This function should only be
    called once, in the startup path of a component (probably as soon as
    possible since many modules will have a dependency on the config options).
    """
    # Ensure that we only try to load the config once. Loading it a second
    # time will result in errors.
    if hasattr(parse_discovery_config, 'discovery_config_loaded'):
        return

    if base_project and base_project.startswith('vmware-'):
        default_files = cfg.find_config_files(project='vmware-discovery',
                                              prog=base_project)
    else:
        default_files = cfg.find_config_files(project=base_project,
                                              prog=(base_project
                                                    if base_prog is None
                                                    else base_prog))
        default_files.extend(cfg.find_config_files(project='vmware-discovery',
                                                   prog='vmware-discovery'))
    # reduce duplicates
    default_files = list(set(default_files))
    CONF(argv[1:], default_config_files=default_files)
    parse_discovery_config.discovery_config_loaded = True


def parse_config(*args, **kwargs):
    rpc.set_defaults(control_exchange='nova')
    parse_discovery_config(*args, **kwargs)
    rpc.init(CONF)

# vim: tabstop=4 shiftwidth=4 softtabstop=4
