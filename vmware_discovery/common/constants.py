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

"""
All Common VMware Discovery Constants
"""

# The default staging project name
DEFAULT_STAGING_PROJECT_NAME = 'public'

# The default staging user name
DEFAULT_STAGING_USER_NAME = 'admin'


class ServiceType(object):
    """Wrappers service type to project codename.
    """
    def __init__(self, svc_type, codename):
        self.svc_type = svc_type
        self.codename = codename

    def __str__(self):
        return self.svc_type

    def to_codename(self):
        """Returns the codename of this service.
        """
        return self.codename


class ServiceTypes(object):
    """The service types known to this infrastructure which can be
    referenced using attr based notation.
    """
    def __init__(self):
        self.volume = ServiceType('volume', 'cinder')
        self.compute = ServiceType('compute', 'nova')
        self.network = ServiceType('network', 'neutron')
        self.identity = ServiceType('identity', 'keystone')
        self.computev3 = ServiceType('computev3', 'nova')
        self.image = ServiceType('image', 'glance')
        self.s3 = ServiceType('s3', 'nova')
        self.ec2 = ServiceType('ec2', 'nova'),
        self.ttv = ServiceType('ttv', 'ttv')

    def __getitem__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        return None


SERVICE_TYPES = ServiceTypes()

# vim: tabstop=4 shiftwidth=4 softtabstop=4
