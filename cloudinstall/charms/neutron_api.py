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

from cloudinstall.charms import CharmBase

log = logging.getLogger('cloudinstall.charms.neutron_api')


class CharmNeutronAPI(CharmBase):

    charm_name = 'neutron-api'
    charm_rev = 5
    display_name = 'Neutron API'
    menuable = True
    openstack_release_min = 'j'

    def set_relations(self):
        repoll = super().set_relations()
        if repoll:
            return True
        service = self.juju_state.service(self.charm_name)
        for other_serv, interface in [('rabbitmq-server', 'amqp'),
                                      ('mysql', 'shared-db'),
                                      ('nova-cloud-controller', 'neutron-api'),
                                      ('keystone', 'identity-service')]:

            if self.is_related(other_serv, service.relations):
                return False

            rel_this = "{}:{}".format(self.charm_name,
                                      interface)
            rel_other = "{}:{}".format(other_serv,
                                       interface)
            log.debug("calling add_relation({}, {})".format(rel_this,
                                                            rel_other))

            try:
                self.juju.add_relation(rel_this, rel_other)

            except:
                msg = ("Relation {}<->{} not ready, "
                       "requeueing.".format(rel_this, rel_other))
                log.info(msg)
                self.ui.status_info_message(msg)
                return True

        return False

__charm_class__ = CharmNeutronAPI
