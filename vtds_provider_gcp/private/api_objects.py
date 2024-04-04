#
# MIT License
#
# (C) Copyright [2024] Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
"""Private implementations of API objects.

"""
import re
from contextlib import contextmanager

from ..api_objects import (
    VirtualBlades,
    BladeInterconnects,
    BladeConnection
)

class __VirtualBlades(VirtualBlades):
    """The external representation of a class of Virtual Blades and
    the public operations that can be performed on blades in that
    class. Virtual Blade operations refer to individual blades by
    their instance number which is an integer greater than or equal to
    0 and less that the number of blade instances in the class.

    """
    def __init__(self, config):
        """Constructor

        """
        self.config = config

    def __get_blade(self, blade_type):
        """class private: retrieve the blade type deascription for the
        named type.

        """
        virtual_blades = (
            self.config.get('provider', {}).get('virtual_blades', {})
        )
        blade = virtual_blades.get(blade_type, None)
        if blade is None:
            raise ContextualError(
                "cannot find the virtual blade type '%s'" % blade_type
            )
        if blade.get('pure_base_class', False):
            raise ContextualError(
                "blade type '%s' is a pure pure base class" % blade_type
            )

    def __check_instance(blade_type, instance):
        """class private: Ensure that the specified instance number
        for a given blade type (blades) is legal.

        """
        if not isinstance(instance, int):
            raise ContextualError(
                "Virtual Blade instance number must be integer not '%s'" %
                type(instance)
            )
        blade = self.__get_blade(blade_type)
        count = int(blade.get('count'), 0)
        if instance < 0 or instance >= count:
            raise ContextualError(
                "instance number %d out of range for Virtual Blade "
                "type '%s' which has a count of %d" %
                (instance, blade_type, count)
            )

    def __get_interconnect(blade_type, interconnect):
        """class private: Get the named interconnect information from
        the specified Virtual Blade type.

        """
        blade = self.__get_blade(blade_type)
        blade_interconnect = blade.get('blade_interconnect', None)
        if blade_interconnect is None:
            raise ContextualError(
                "provider config error: Virtual Blade type '%s' has no "
                "blade interconnect configured" % blade_type
            )
        if blade_interconnect.get("subnetwork", None) != blade_type:
            raise ContextualError(
                "Virtual Blade type '%s' is not configured to use "
                "blade interconnect '%s'" % (blade_type, interconnect)
            )
        return blade_interconnect

    def __get_project_id(self):
        """class private: Retrieve the project ID for the current vTDS
        project.

        """
        organization_name = (
            self.config.get('provider', {})
            .get('organization', {})
            .get('name', None)
        )
        if organization_name is None:
            raise ContextualError(
                "provider config error: cannot find 'name' in "
                "'provider.organization'"
            )
        base_name = (
            self.config.get('provider', {})
            .get('project', {})
            .get('base_name', None)
        )
        if base_name is None:
            raise ContextualError(
                "provider config error: cannot find 'base_name' in "
                "'provider.project'"
            )
        project_name = "%s-%s" % (organization_name, base_name)
        with Popen(
                ['gcloud', 'projects', 'list', '--format=json'],
                stdout = PIPE,
                stderr = PIPE
        ) as cmd:
            projects = json.loads(cmd.stdout.read())
        project_ids = [
            project['projectID'] for project in projects
            if project.get('name', "") == project_name
        ]
        if not project_ids:
            raise ContextualError(
                "unable to find a project named '%s' in GCP organization "
                "'%s'" % (project_name, organization_name)
            )
        if len(project_ids) > 1:
            raise ContextualError(
                "found more than one project named '%s' in GCP organization "
                "'%s" %  (project_name, organization_name)
            )
        return project_ids[0]

    def blade_count(self, blade_type):
        """Get the number of Virtual Blade instances of the specified
        type.

        """
        blade = self.__get_blade(blade_type)
        return int(blade.get('count', 0))

    def blade_interconnects(self, blade_type):
        """Return the list of Blade Interconnects by name connected to
        the specified type of Virtual Blade.

        """
        blade = self.__get_blade(blade_type)
        # The GCP provider only lets us have one interconnect per
        # blade type, so we are just going to go grab that and make it
        # into a 'list' of one item.
        name = blade.get('blade_interconnect', {}).get('subnetwork', None)
        if name is None:
            raise ContextualError(
                "provider config error: no 'blade_interconnect.subnetwork' "
                "found in blade type '%s'" % blade_type
            )
        return [name]

    def blade_hostname(self, blade_type, instance):
        """Get the hostname of a given instance of the specified type
        of Virtual Blade.

        """
        self.__check_instance(blade_type, instance)
        blade = self.__get_blade(blade_type)
        if 'hostname' not in blade:
            raise ContextualError(
                "provider config error: no 'hostname' configured for "
                "Virtual Blade type '%s'" % blade_type
            )
        add_suffix = blade.get('add_hostname_suffix', self.count > 1)
        hostname = blade['hostname']
        separator = (
            self.config.get('hostname_suffix_separator', "")
            if add_suffix else ""
        )
        suffix = "%3.3d" % instance if add_suffix else ""
        return hostname + separator + suffix

    def blade_ip(self, blade_type, instance, interconnect):
        """Return the IP address (string) on the named Blade
        Interconnect of a specified instance of the named Virtual
        Blade type.

        """
        self.__check_instance(blade_type, instance)
        blade_interconnect = self.__get_interconnect(blade_type, interconnect)
        ip_addrs = blade_interconnect.get('ip_addrs', None)
        if not ip_addrs:
            raise ContextualError(
                "provider config error: Virtual Blade type '%s' has no "
                "'ip_addrs' configured"
            )
        if instance >= len(ip_addrs):
            raise ContextualError(
                "provider config error: Virtual Blade type is configured with "
                "fewer ip_addrs (%d) than blade instances (%d)" %
                (len(ip_addrs), self.blade_count(blade_type))
            )
        return ip_addrs[instance]

    @contextmanager
    def connect_blade(self, remote_port, blade_type, instance):
        """Establish an external connection to the specified remote
        port on the specified instance of the named Virtual Blade
        type. Return a context manager (suitable for use in a 'with'
        clause) yielding a BladeConnection object for the
        connection. Upon leaving the 'with' context, the connection in
        the BladeConnection is closed.

        """
        project_id = self._get_project_id()
        hostname = self.blade_hostname(blade_type, instance)
        connection = __BladeConnection(
            project_id, hostname, remote_port, blade_type
        )
        try:
            yield(connection)
        finally:
            connection._disconnect()

    @contextmanager
    def connect_blades(self, remote_port, blade_types=None):
        """Establish external connections to the specified remote port
        on all the Virtual Blade instances on all the Virtual Blade
        types listed by name in 'blade_types'. If 'blade_types' is not
        provided or None, all available blade types are used. Return a
        context manager (suitable for use in a 'with' clause) yielding
        the list of APIBladeConnection objects representing the
        connections. Upon leaving the 'with' context, all the
        connections in the resulting list are closed.

        """
        virtual_blades = (
            self.config.get('provider', {}).get('virtual_blades', {})
        )
        blade_types = (
            blade_types if blade_types is not None else
            [
                name for name in virtual_blades
                if not virtual_blades[name].get('pure_base_class', False)
            ]
        )
        project_id = self._get_project_id()
        connections = [
            __BladeConnection(
                project_id,
                self.blade_hostname(blade_type, instance),
                hostname, remote_port, blade_type
            )
            for blade_type in blade_types
            for instance in range(0, self.blade_count(blade_type))
        ]
        try:
            yield(connections)
        finally:
            for connection in connections:
                connection._disconnect()
    

class __BladeInterconnects(BladeInterconnects):
    """The external representation of the set of Blade Interconnects
    and public operations that can be performed on the interconnects.

    """
    def __init__(self, config):
        """Constructor

        """
        self.config = config

    def ipv4_cidr(self, interconnect_name):
        """Return the (string) IPv4 CIDR (<IP>/<length>) for the
        network on the named interconnect.

        """
        blade_interconnects = (
            config.get("provider", {}).get("blade_interconnects", {})
        )
        if interconnect_name not in blade_interconnects:
            raise ContextualError(
                "requestiong ipv4_cidr of unknown blade interconnect '%s'" %
                interconnect_name
            )
        interconnect = blade_interconnects.get(interconnect_name, {})
        if 'ipv4_cidr' not in interconnect:
            raise ContextualError(
                "provider layer configuration error: no 'ipv4_cidr' found in "
                "blade interconnect named '%s'" % interconnect_name
            )
        return interconnect['ipv4_cidr']


class __BladeConnection(BladeConnection):
    """A class containing the relevant information needed to use
    external connections to ports on a specific Virtual Blade.

    """
    def __init__(self, project_id, hostname, remote_port, blade_type):
        """Constructor

        """
        self.hostname = hostname
        self.blade_type = blade_type
        self.remote_port = remote_port
        self.project_id = project_id
        self.local_ip = "127.0.0.1"
        self.loc_port = None
        self.subprocess = None
        self._connect()

    def _connect(self):
        """Layer private operation: establish the connection and learn
        the local IP and port of the connection.

        """
        self.subprocess = Popen(
            [
                'gcloud', 'compute', '--project=%s' % self.project_id,
                'start-iap-tunnel',
                self.blade_name(blade_type, instance),
                str(remote_port)
            ],
            stdout=PIPE, stderr=PIPE,
            bufsize=1,   # line buffering
            text=True, encoding='UTF-8'
        )
        listening = self.subprocess.stdout.readline()[:-1]
        expr = re.compile(r"^Listening on port [[](?P<port>[0-9]+)[]][.]$")
        try:
            self.loc_port = int(expr.match(line).group('port'))
        except Exception as err:
            raise ContextualError(
                "unexpected failure of 'start-iap-tunnel' no port number "
                "found in output: '%s' - %s" % (line, str(err))
            ) from err

    def _disconnect(self):
        """Layer private operation: drop the connection.
        """
        self.subprocess.kill()
        self.subprocess = None
        self.loc_port = None

    def blade_type(self):
        """Return the name of the Virtual Blade type of the connected
        Virtual Blade.

        """
        return self.blade_type

    def blade_hostname(self):
        """Return the hostname of the connected Virtual Blade.

        """
        return self.hostname

    def local_ip(self):
        """Return the locally reachable IP address of the connection
        to the Virtual Blade.

        """
        return self.local_ip

    def local_port(self):
        """Return the TCP port number on the locally reachable IP
        address of the connection to the Virtual Blade.

        """
        return self.loc_port
