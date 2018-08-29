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

"""VMware Discovery related Utilities"""


def flavors_match(flavor1, flavor2):
    for prop in ['memory_mb', 'vcpus', 'root_gb', 'ephemeral_gb']:
        if flavor1.get(prop, 0) != flavor2.get(prop, 0):
            return False
    return True


def instance_needs_update(instance1, instance2):
    # # del  'ephemeral_device_name',
    for prop in ['hostname', 'memory_mb', 'vcpus', 'root_gb', 'ephemeral_gb',
                 'node', 'root_device_name', 'vm_state', 'task_state', 'os_type',
                 'power_state']:
        if instance1.get(prop) != instance2.get(prop):
            return True
    return False


def populate_flavor_from_instance(flavor, vmw_instance):
    flavor.memory_mb = vmw_instance.get('memory_mb')
    flavor.vcpus = vmw_instance.get('vcpus')
    flavor.root_gb = vmw_instance.get('root_gb', 0)
    flavor.ephemeral_gb = vmw_instance.get('ephemeral_gb', 0)
    flavor.is_public = True

# vim: tabstop=4 shiftwidth=4 softtabstop=4
