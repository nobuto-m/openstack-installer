#
# charms.py - Charm instructions to Cloud Installer
#
# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import yaml
from os.path import expanduser, exists
import sys
from queue import Queue
import time

from cloudinstall import pegasus, utils
from cloudinstall.juju.client import JujuClient
from cloudinstall.juju import JujuState

log = logging.getLogger('cloudinstall.charms')

CHARM_CONFIG_FILENAME = expanduser("~/.cloud-install/charmconf.yaml")
CHARM_CONFIG = {}
if exists(CHARM_CONFIG_FILENAME):
    with open(CHARM_CONFIG_FILENAME) as f:
        CHARM_CONFIG = yaml.load(f.read())


class DisplayPriorities:
    """A fake enum"""
    Core = 0
    Compute = 10
    Storage = 20
    Other = 30


def get_charm(charm_name, juju_state):
    """ returns single charm class

    :param str charm_name: name of charm to query
    :param juju_state: status of juju
    :rtype: Charm
    :returns: charm class
    """
    for charm in utils.load_charms():
        c = charm.__charm_class__(juju_state)
        if charm_name == c.name():
            return c


class CharmBase:
    """ Base charm class """

    charm_name = None
    display_name = None
    related = []
    isolate = False
    constraints = None
    deploy_priority = sys.maxsize
    display_priority = DisplayPriorities.Core
    allow_multi_units = False
    optional = False
    disabled = False
    machine_id = False

    def __init__(self, juju_state=None, machine=None):
        """ initialize

        :param state: :class:JujuState
        :param machine: :class:Machine
        """
        self.charm_path = None
        self.exposed = False
        self.juju_state = juju_state
        assert isinstance(self.juju_state, JujuState)
        self.machine = machine
        self.client = JujuClient()

    @property
    def is_single(self):
        return pegasus.SINGLE_SYSTEM

    @property
    def is_multi(self):
        return pegasus.MULTI_SYSTEM

    def openstack_password(self):
        PASSWORD_FILE = expanduser('~/.cloud-install/openstack.passwd')
        try:
            with open(PASSWORD_FILE) as f:
                OPENSTACK_PASSWORD = f.read().strip()
        except IOError:
            OPENSTACK_PASSWORD = 'password'
        return OPENSTACK_PASSWORD

    def is_related(self, charm, relations):
        """ test for existence of charm relation

        :param str charm: charm to verify
        :param list relations: related charms
        :returns: True if existing relation found, False otherwise
        :rtype: bool
        """
        try:
            list(filter(lambda r: charm in r.charms,
                        relations))[0]
            return True
        except IndexError:
            return False

    @classmethod
    def name(class_):
        """ Return charm name

        :returns: name of charm
        :rtype: lowercase str
        """
        if class_.charm_name:
            return class_.charm_name
        return class_.__name__.lower()

    def setup(self):
        """ Deploy charm and configuration options

        The default should be sufficient but if more functionality
        is needed this should be overridden.
        """
        kwds = {}
        kwds['machine_id'] = self.machine_id

        if self.charm_name in CHARM_CONFIG:
            kwds['configfile'] = CHARM_CONFIG_FILENAME

        if self.isolate:
            kwds['machine_id'] = None
            kwds['instances'] = 1
            kwds['constraints'] = self.constraints
            self.client.deploy(self.charm_name, kwds)
        else:
            self.client.deploy(self.charm_name, kwds)

    def set_relations(self):
        """ Setup charm relations

        Override in charm specific.
        """
        if len(self.related) > 0:
            services = self.juju_state.service(self.charm_name)
            for charm in self.related:
                if not self.is_related(charm, services.relations):
                    err = self.client.add_relation(self.charm_name,
                                                   charm)
                    if err:
                        log.error("Relation not ready for "
                                  "{c}, requeueing.".format(c=self.charm_name))
                        return True
        return False

    def post_proc(self):
        """ Perform any post processing

        i.e. setting configuration variables for a charm

        Override in charm classes
        """
        pass

    def __repr__(self):
        return self.name()


class CharmQueue:
    """ charm queue for handling relations in the background
    """
    def __init__(self):
        self.charm_relations_q = Queue()
        self.charm_setup_q = Queue()
        self.is_running = False

    def add_relation(self, charm):
        self.charm_relations_q.put(charm)

    def add_setup(self, charm):
        self.charm_setup_q.put(charm)

    @utils.async
    def watch_setup(self):
        log.debug("Starting charm setup watcher.")
        while True:
            charm = self.charm_setup_q.get()
            err = charm.setup()
            if err:
                self.charm_setup_q.put(charm)
            self.charm_setup_q.task_done()
            time.sleep(1)

    @utils.async
    def watch_relations(self):
        log.debug("Starting charm relations watcher.")
        while True:
            charm = self.charm_relations_q.get()
            err = charm.set_relations()
            if err:
                self.charm_relations_q.put(charm)
            else:
                charm.post_proc()
            self.charm_relations_q.task_done()
            time.sleep(1)
