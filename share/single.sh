#
# single.sh - Single install interface
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

setupSingleInstall()
{
	mkdir -m 0700 -p "/home/$INSTALL_USER/.cloud-install"
	touch "/home/$INSTALL_USER/.cloud-install/single"
	echo "$openstack_password" \
	    > "/home/$INSTALL_USER/.cloud-install/openstack.passwd"
	chmod 0600 "/home/$INSTALL_USER/.cloud-install/openstack.passwd"
	chown -R "$INSTALL_USER:$INSTALL_USER" \
	    "/home/$INSTALL_USER/.cloud-install"
}

singleInstall()
{
	dialogGaugeStart Installing "Please wait" 8 70 0
	{
		dialogGaugePrompt 2 "Setting up install"
		setupSingleInstall

		dialogAptInstall 4 40 cloud-install-single

		dialogGaugePrompt 42 "Generating SSH keys"
		generateSshKeys

		dialogGaugePrompt 80 "Bootstrapping Juju"
		configureJuju configLocalEnvironment
                (
                  cd "/home/$INSTALL_USER"
                  sudo -H -u "$INSTALL_USER" juju bootstrap
                  #sudo -H -u "$INSTALL_USER" juju set-constraints mem=2G
                )
		echo 99

		dialogGaugePrompt 100 "Installation complete"
		sleep 2
	} > "$TMP/gauge"
	dialogGaugeStop
}
