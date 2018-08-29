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

import six
from sqlalchemy import Column, String, Integer, Boolean, BigInteger, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.ext.declarative import declarative_base

from vmware_discovery.common import config
import uuidutil

CONF = config.CONF

Base = declarative_base()


class CommonMethods(object):
    __table_initialized__ = False

    def update(self, values):
        """Make the model object behave like a dict."""
        for k, v in six.iteritems(values):
            setattr(self, k, v)

    def save(self, session):
        session.add(self)
        session.commit()

    def delete(self, session):
        session.delete(self)
        session.commit()


# TO-DO(lixx@vsettan.com.cn): Apply auto migration way
# in case of table schema changing
class Standardattribute(Base, CommonMethods):
    """Represents a neutron network."""

    __tablename__ = 'standardattributes'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    resource_type = Column(String(255), nullable=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    description = Column(String(255))


# TO-DO(yanfengxi@cn.ibm.com): Apply auto migration way
# in case of table schema changing
class Network(Base, CommonMethods):
    """Represents a neutron network."""

    __tablename__ = 'networks'
    id = Column(String(36),
                primary_key=True,
                default=uuidutil.generate_uuid)
    tenant_id = Column(String(255))
    name = Column(String(255))
    status = Column(String(16))
    admin_state_up = Column(Integer)
    standard_attr_id = Column(Integer)
    # #shared = Column(Boolean)


# TO-DO(yanfengxi@cn.ibm.com): Apply auto migration way
# in case of table schema changing
class Ml2Segment(Base, CommonMethods):

    __tablename__ = 'ml2_network_segments'

    id = Column(String(36),
                primary_key=True,
                default=uuidutil.generate_uuid)
    network_id = Column(String(36),
                        ForeignKey('networks.id', ondelete="CASCADE"),
                        nullable=False)
    network_type = Column(String(32), nullable=False)
    physical_network = Column(String(64))
    segmentation_id = Column(Integer)

# vim: tabstop=4 shiftwidth=4 softtabstop=4
