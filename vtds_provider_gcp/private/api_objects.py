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
from os.path import join as path_join
from os import makedirs
from contextlib import contextmanager
from subprocess import (
    Popen,
    PIPE
)
from socketserver import TCPServer
from socket import (
    socket,
    AF_INET,
    SOCK_STREAM
)
from time import sleep

from vtds_base import (
    ContextualError,
    logfile
)
from ..api_objects import (
    VirtualBlades,
    BladeInterconnects,
    BladeConnection
)


# pylint: disable=invalid-name
class PrivateVirtualBlades(VirtualBlades):
    """The external representation of a class of Virtual Blades and
    the public operations that can be performed on blades in that
    class. Virtual Blade operations refer to individual blades by
    their instance number which is an integer greater than or equal to
    0 and less that the number of blade instances in the class.

    """
    def __init__(self, config, build_dir):
        """Constructor

        """
        self.config = config
        self.build_dir = build_dir
        self.project_id = None

    def __get_blade(self, blade_type):
        """class private: retrieve the blade type deascription for the
        named type.

        """
        virtual_blades = (
            self.config.get('virtual_blades', {})
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
        return blade

    def __check_instance(self, blade_type, instance):
        """class private: Ensure that the specified instance number
        for a given blade type (blades) is legal.

        """
        if not isinstance(instance, int):
            raise ContextualError(
                "Virtual Blade instance number must be integer not '%s'" %
                type(instance)
            )
        blade = self.__get_blade(blade_type)
        count = int(blade.get('count', 0))
        if instance < 0 or instance >= count:
            raise ContextualError(
                "instance number %d out of range for Virtual Blade "
                "type '%s' which has a count of %d" %
                (instance, blade_type, count)
            )

    def __get_interconnect(self, blade_type, interconnect):
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
        if blade_interconnect.get("subnetwork", None) != interconnect:
            raise ContextualError(
                "Virtual Blade type '%s' is not configured to use "
                "blade interconnect '%s'" % (blade_type, interconnect)
            )
        return blade_interconnect

    def _get_project_id(self):
        """layer private: Retrieve the project ID for the current vTDS
        project.

        """
        if self.project_id is not None:
            return self.project_id
        organization_name = (
            self.config.get('organization', {}).get('name', None)
        )
        if organization_name is None:
            raise ContextualError(
                "provider config error: cannot find 'name' in "
                "'provider.organization'"
            )
        base_name = (
            self.config.get('project', {}).get('base_name', None)
        )
        if base_name is None:
            raise ContextualError(
                "provider config error: cannot find 'base_name' in "
                "'provider.project'"
            )
        project_name = "%s-%s" % (organization_name, base_name)
        with Popen(
                [
                    'gcloud', 'projects', 'list',
                    '--filter=name=%s' % project_name,
                    '--format=value(PROJECT_ID)'
                ],
                stdout=PIPE,
                stderr=PIPE,
                text=True, encoding='UTF-8'
        ) as cmd:
            self.project_id = cmd.stdout.readline()[:-1]
        return self.project_id

    def _get_zone(self):
        """Layer private: get the configured zone in which resources
        for this project reside.

        """
        zone = self.config.get('project', {}).get('zone', None)
        if zone is None:
            raise ContextualError(
                "provider config error: cannot find 'zone' in "
                "'provider.project'"
            )
        return zone

    def _get_build_dir(self):
        """Layer private: get the build directory for this run of the
        vTDS tool.

        """
        return self.build_dir

    def _log_paths(self, logname):
        """Layer private: an 'out' path and an 'error' path based on
        the base name 'logname' and return both to the caller.

        """
        directory = path_join(self.build_dir, "virtual_blades")
        logs = path_join(directory, "logs")
        try:
            makedirs(logs, mode=0o755, exist_ok=True)
        except OSError as err:
            raise ContextualError(
                "failed to create log directory '%s' - %s" % (
                    logs, str(err)
                )
            ) from err
        out_path = path_join(
            logs,
            "%s-out.txt" % (logname)
        )
        err_path = path_join(
            logs,
            "%s-err.txt" % (logname)
        )
        return out_path, err_path

    def blade_types(self):
        """Get a list of virtual blade types that are not pure base
        classes by name.

        """
        virtual_blades = self.config.get('virtual_blades', {})
        return [
            name for name in virtual_blades
            if not virtual_blades[name].get('pure_base_class', False)
        ]

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
        count = self.blade_count(blade_type)
        add_suffix = blade.get('add_hostname_suffix', count > 1)
        hostname = blade['hostname']
        separator = (
            blade.get('hostname_suffix_separator', "") if add_suffix else ""
        )
        # Suffixes are 1 based, not 0 based, instances are 0 based
        suffix = "%3.3d" % (instance + 1) if add_suffix else ""
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
        connection = PrivateBladeConnection(
            self, blade_type, instance, remote_port
        )
        try:
            yield connection
        finally:
            # This is a layer private operation not really class
            # private. Treat this reference as friendly.
            connection._disconnect()  # pylint: disable=protected-access

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
        blade_types = (
            self.blade_types() if blade_types is None else blade_types
        )
        connections = [
            PrivateBladeConnection(self, blade_type, instance, remote_port)
            for blade_type in blade_types
            for instance in range(0, self.blade_count(blade_type))
        ]
        try:
            yield connections
        finally:
            for connection in connections:
                # This is a layer private operation not really class
                # private. Treat this reference as friendly.
                connection._disconnect()  # pylint: disable=protected-access


class PrivateBladeInterconnects(BladeInterconnects):
    """The external representation of the set of Blade Interconnects
    and public operations that can be performed on the interconnects.

    """
    def __init__(self, config, build_dir):
        """Constructor

        """
        self.config = config
        self.build_dir = build_dir

    def __interconnects_by_name(self):
        """Return a dictionary of non-pure-base-class interconnects
        indexed by 'network_name'

        """
        blade_interconnects = self.config.get("blade_interconnects", {})
        try:
            return {
                interconnect['network_name']: interconnect
                for _, interconnect in blade_interconnects.items()
                if not interconnect.get('pure_base_class', False)
            }
        except KeyError as err:
            # Unfortunately, because of the comprehension above, I don't
            # know which network had the problem, but I can at least report
            # which key was bad...
            raise ContextualError(
                "provider config error: 'network_name' not specified in "
                "one of the interconnects configured under "
                "'provider.blade_interconnects'"
            ) from err

    def interconnect_names(self):
        """Get a list of blade interconnects by name

        """
        return self.__interconnects_by_name().keys()

    def ipv4_cidr(self, interconnect_name):
        """Return the (string) IPv4 CIDR (<IP>/<length>) for the
        network on the named interconnect.

        """
        blade_interconnects = self.__interconnects_by_name()
        if interconnect_name not in blade_interconnects:
            raise ContextualError(
                "requesting ipv4_cidr of unknown blade interconnect '%s'" %
                interconnect_name
            )
        interconnect = blade_interconnects.get(interconnect_name, {})
        if 'ipv4_cidr' not in interconnect:
            raise ContextualError(
                "provider layer configuration error: no 'ipv4_cidr' found in "
                "blade interconnect named '%s'" % interconnect_name
            )
        return interconnect['ipv4_cidr']


# pylint: disable=invalid-name
class PrivateBladeConnection(BladeConnection):
    """A class containing the relevant information needed to use
    external connections to ports on a specific Virtual Blade.

    """
    def __init__(self, virtual_blades, blade_type, instance, remote_port):
        """Constructor

        """
        self.virtual_blades = virtual_blades
        self.blade_type = blade_type
        self.instance = instance
        self.remote_port = remote_port
        self.hostname = self.virtual_blades.blade_hostname(
            blade_type, instance
        )
        self.local_ip = "127.0.0.1"
        self.loc_port = None
        self.subprocess = None
        self._connect()

    def _connect(self):
        """Layer private operation: establish the connection and learn
        the local IP and port of the connection.

        """
        # Get a "free" port to use for the connection by briefly
        # binding a TCP server and then destroying it before it
        # listens on anything.
        with TCPServer((self.local_ip, 0), None) as tmp:
            self.loc_port = tmp.server_address[1]

        # pylint: disable=protected-access
        zone = self.virtual_blades._get_zone()

        # pylint: disable=protected-access
        project_id = self.virtual_blades._get_project_id()

        logname = "connection-%s-port-%d" % (self.hostname, self.remote_port)
        # pylint: disable=protected-access
        out_path, err_path = self.virtual_blades._log_paths(logname)
        with logfile(out_path) as out, logfile(err_path) as err:
            # Not using 'with' for the Popen because the Popen object
            # becomes part of this class instance for the duration of
            # the class instance's life cycle. The instance itself is
            # handed out through a context manager which will
            # disconnect and destroy the Popen object when the context
            # ends.
            #
            # pylint: disable=consider-using-with
            self.subprocess = Popen(
                [
                    'gcloud', 'compute', '--project=%s' % project_id,
                    'start-iap-tunnel',
                    '--zone=%s' % zone,
                    self.hostname,
                    str(self.remote_port),
                    '--local-host-port=%s:%s' % (self.local_ip, self.loc_port)
                ],
                stdout=out, stderr=err,
                text=True, encoding='UTF-8'
            )

        # Wait for the tunnel to be established before returning.
        retries = 60
        while retries > 0:
            with socket(AF_INET, SOCK_STREAM) as tmp:
                try:
                    tmp.connect((self.local_ip, self.loc_port))
                    return
                except ConnectionRefusedError:
                    sleep(1)
                    retries -= 1
                except Exception as err:
                    self._disconnect()
                    raise ContextualError(
                        "internal error: failed attempt to connect to "
                        "service on IAP tunnel to '%s' port %d - %s" % (
                            self.hostname, self.remote_port, str(err)
                        ),
                        out_path, err_path
                    ) from err
        # If we got out of the loop we timed out trying to connect...
        self._disconnect()
        raise ContextualError(
            "internal error: timeout waiting for IAP connection to '%s' "
            "port %d to be ready" % (self.hostname, self.remote_port),
            out_path, err_path
        )

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
