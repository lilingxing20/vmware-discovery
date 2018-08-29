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
from oslo_log import log as logging
import exception
import os
import sys
import threading

from oslo_utils import importutils

from vmware_discovery.common import config
from vmware_discovery.common import constants
from vmware_discovery.common.client import factory
from vmware_discovery.common.gettextutils import _

LOG = logging.getLogger(__name__)

CONF = config.CONF

__lock = threading.Lock()
__utils = None


def get_utils():
    """
    Returns a singleton Utils object
    """
    global __lock
    global __utils
    if __utils is not None:
        return __utils
    with __lock:
        if __utils is not None:
            return __utils
        __utils = Utils()
    return __utils


class Utils(object):
    """
    This Utils class leverages the keystone client to provide
    access to the staging project and user IDs

    Usage sample:

        utils = utils.Utils()
        stp = utils.get_local_staging_project_id()
        stu = utils.get_local_staging_user_id()
    """
    def __init__(self):
        self._localkeystoneclient = factory.LOCAL.new_client(
            str(constants.SERVICE_TYPES.identity))

    def get_local_staging_project_id(self):
        """
        Get the local hosting OS staging project Id. If a staging
        project name is not found, a exception.StagingProjectNotFound
        exception will be raised. If no staging project is specified in
        the conf, the default value will be used as specified in constants.

        :returns: The local hosting OS staging project Id
        """
        ks_client = self._localkeystoneclient
        stagingname = CONF.discovery_common.staging_project_name or \
            constants.DEFAULT_STAGING_PROJECT_NAME
        try:
            project_list = None
            if ks_client.version == 'v3':
                project_list = ks_client.projects.list()
            else:
                project_list = ks_client.tenants.list()
            for tenant in project_list:
                projectname = tenant.name
                projectid = tenant.id
                if projectname == stagingname:
                    LOG.debug(_('The staging_project_name %s has id %s'),
                              stagingname, projectid)
                    return projectid
        except Exception as e:
            LOG.debug(_('An error occurred getting the tenant list: %s.'), e)
        LOG.debug(_('Unable to find staging project: %s'), stagingname)
        raise exception.StagingProjectNotFound(name=stagingname)

    def get_local_staging_user_id(self):
        """
        Get the local hosting OS staging user Id which defaults to
        constants.DEFAULT_STAGING_USERNAME if not set in the conf.
        If a staging user name is not found, a StagingUserNotFound
        exception will be raised.

        :returns: The local hosting OS staging user Id
        """
        ks_client = self._localkeystoneclient
        staginguser = CONF.discovery_common.staging_user or \
            constants.DEFAULT_STAGING_USER_NAME
        try:
            for user in ks_client.users.list():
                username = user.name
                userid = user.id
                if staginguser == username:
                    LOG.debug(_('The staging_user %s has id %s'),
                              staginguser, userid)
                    return userid
        except Exception as e:
            LOG.debug(_('An error occurred getting the user list: %s'), e)
        LOG.debug(_('Unable to find staging user: %s'), staginguser)
        raise exception.StagingUserNotFound(name=staginguser)


def import_relative_module(relative_import_str, import_str):
    """
    Imports a module relative to another. Can be used when more
    than 1 module of the given name exists in the python path
    to resolve any discrepency in multiple paths.

    :param relative_import_str: a module import string which
    neighbors the actual import. for example 'glanceclient'.
    :param import_str: the module import string. for example
    'tests.utils'

    example:
    utils = import_relative_module('glanceclient', 'tests.utils')
    fapi = utils.FakeAPI(...)
    """
    mod = importutils.import_module(relative_import_str)
    mpath = os.path.dirname(os.path.dirname(os.path.realpath(mod.__file__)))
    if not sys.path[0] is mpath:
        sys.path.insert(0, mpath)
    return importutils.import_module(import_str)


class StagingCache(object):
    """
    Provides a lazy cache around the local staging user and project.
    Consumers can use the staging_user_and_project property to retrieve the
    (user_id, project_id) pair for the staging user. These values are
    lazily fetched at most once
    """

    def __init__(self):
        super(StagingCache, self).__init__()
        self.utils = get_utils()
        self.staging_user = None
        self.staging_project = None

    @property
    def is_valid(self):
        uid, pid = self.get_staging_user_and_project()
        return uid is not None and pid is not None

    def get_staging_user_and_project(self, raise_on_invalid=False):
        try:
            if not self.staging_user:
                self.staging_user = self.utils.get_local_staging_user_id()
            if not self.staging_project:
                self.staging_project = \
                    self.utils.get_local_staging_project_id()
            return (self.staging_user, self.staging_project)
        except exception.StagingProjectNotFound as e:
            if raise_on_invalid:
                raise e
            return (None, None)
        except exception.StagingUserNotFound as e:
            if raise_on_invalid:
                raise e
            return (None, None)

# vim: tabstop=4 shiftwidth=4 softtabstop=4
