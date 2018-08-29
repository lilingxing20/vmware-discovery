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
VMware Discovery Common Exceptions
"""

from vmware_discovery.common.gettextutils import _

_FATAL_EXCEPTION_FORMAT_ERRORS = False


class CommonException(Exception):
    """
    VMware Discovery Common Exception

    To correctly use this class, inherit from it and define a 'message'
    property. That message will get printed with the keyword arguments
    provided to the constructor.
    """
    message = _('An unknown exception occurred')

    def __init__(self, message=None, *args, **kwargs):
        if not message:
            message = self.message
        try:
            message = message % kwargs
        except Exception:
            if _FATAL_EXCEPTION_FORMAT_ERRORS:
                raise
            else:
                # at least get the core message out if something happened
                pass

        super(CommonException, self).__init__(message)


class StagingProjectNotFound(CommonException):
    """
    Exception thrown when the staging project specified in the conf cannot be
    found.

    :param name: The name of the staging project which was not found.
    """
    message = _('The staging project \'%(name)s\' was not found.')


class StagingUserNotFound(CommonException):
    """
    Exception thrown when the staging user specified in the conf cannot be
    found.

    :param name: The name of the staging user which was not found.
    """
    message = _('The staging user \'%(name)s\' was not found.')


class GlanceRegionEndpointNotFound(CommonException):
    """
    Exception thrown when the glance endpoint for the target region as specified in the conf or
    environment cannot be found.

    :param target_region: The value of the vmware_discovery target_conf configuration option
    :param os_region_name: The value of the environment variable OS_REGION_NAME
    """
    message = _("No glance endpoint matching target_name \'%(target_region)s\'"
                "or OS_REGION_NAME \'%(os_region_name)s\' was found.")
