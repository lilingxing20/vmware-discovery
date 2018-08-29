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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vmware_discovery.common import config

CONF = config.CONF
_nova_engine = None
_neutron_engine = None


def get_nova_session():
    global _nova_engine
    if _nova_engine is None:
        _nova_engine = create_engine(CONF.database.connection)
    nova_session = sessionmaker(bind=_nova_engine)
    return nova_session()


def get_neutron_session():
    global _neutron_engine
    if _neutron_engine is None:
        _neutron_engine = create_engine(CONF.portgroup.neutron_connection)
    neutron_session = sessionmaker(bind=_neutron_engine)
    return neutron_session()

# vim: tabstop=4 shiftwidth=4 softtabstop=4
