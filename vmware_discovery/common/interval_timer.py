# coding=utf-8

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
LOG = logger.getLogger(__name__)


class interval_timer(object):
    def __init__(self, timer, interval, name=''):
        self._timer_init = timer
        self._interval = interval
        self._timer_reset()
        self.name = name

    def _timer_reset(self):
        self._timer = self._timer_init

    """ Used to check an decrement the timer """
    def timer_rings(self):
        self._timer -= self._interval
        if self._timer < 1:
            self._timer_reset()
            LOG.info('Timer %s RuNG!', self.name)
            return True
        LOG.debug("Timer %s waiting: %ss", self.name, self._timer)
        return False

# vim: tabstop=4 shiftwidth=4 softtabstop=4
