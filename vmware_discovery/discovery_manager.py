# coding=utf-8

from nova import manager

from vmware_discovery.instance import instance_manager
from vmware_discovery.template import template_manager
from vmware_discovery.portgroup import portgroup_manager


class VMwareDiscoveryManager(manager.Manager):

    def __init__(self, *args, **kwargs):
        """
        Load configuration options and start periodic sync.

        :param compute_driver: the fully qualified name of the compute Driver
                               that will be used with this manager
        """
        super(VMwareDiscoveryManager, self).__init__(*args, **kwargs)

        # Set up periodic polling to sync instances
        self._start_periodic_sync()

    def _start_periodic_sync(self):
        """
        Initialize the periodic syncing of instances from VMware into the
        local OS. The instance_sync_interval config property determines
        how often the sync will occur, and the
        full_instance_sync_frequency config property determines the
        number of marked instance sync operations between full instance syncs.

        :param: context The security context
        """
        # Enforce some minimum values for the sync interval properties
        # TODO: Minimum values should at least be documented
        _instance_discovery = instance_manager.DiscoveryInstanceManager()
        _template_discovery = template_manager.DiscoveryTemplateManager()
        _portgroup_discovery = portgroup_manager.DiscoveryPortGroupManager()
        _instance_discovery.sync()
        _template_discovery.sync()
        _portgroup_discovery.sync()

# vim: tabstop=4 shiftwidth=4 softtabstop=4
