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
from contextlib import contextmanager
from subprocess import Popen
from socketserver import TCPServer
from socket import (
    socket,
    AF_INET,
    SOCK_STREAM
)
from time import sleep

from vtds_base import (
    ContextualError,
    log_paths,
    logfile,
    info_msg
)
from ..api_objects import (
    VirtualBlades,
    BladeInterconnects,
    BladeConnection,
    Secrets
)


# pylint: disable=invalid-name
class PrivateVirtualBlades(VirtualBlades):
    """The external representation of a class of Virtual Blades and
    the public operations that can be performed on blades in that
    class. Virtual Blade operations refer to individual blades by
    their instance number which is an integer greater than or equal to
    0 and less that the number of blade instances in the class.

    """
    def __init__(self, common):
        """Constructor

        """
        self.common = common

    def blade_types(self):
        """Get a list of virtual blade types that are not pure base
        classes by name.

        """
        virtual_blades = self.common.get('virtual_blades', {})
        return [
            name for name in virtual_blades
            if not virtual_blades[name].get('pure_base_class', False)
        ]

    def blade_count(self, blade_type):
        """Get the number of Virtual Blade instances of the specified
        type.

        """
        return self.common.blade_count(blade_type)

    def blade_interconnects(self, blade_type):
        """Return the list of Blade Interconnects by name connected to
        the specified type of Virtual Blade.

        """
        return self.common.blade_interconnects(blade_type)

    def blade_hostname(self, blade_type, instance):
        """Get the hostname of a given instance of the specified type
        of Virtual Blade.

        """
        return self.common.blade_hostname(blade_type, instance)

    def blade_ip(self, blade_type, instance, interconnect):
        """Return the IP address (string) on the named Blade
        Interconnect of a specified instance of the named Virtual
        Blade type.

        """
        return self.common.blade_ip(blade_type, instance, interconnect)

    def blade_ssh_key_secret(self, blade_type):
        """Return the name of the secret containing the SSH key pair
        used to to authenticate with blades of the specified blade
        type.

        """
        return self.common.blade_ssh_key_secret(blade_type)

    def blade_ssh_key_paths(self, blade_type):
        """Return a tuple of paths to files containing the public and
        private SSH keys used to to authenticate with blades of the
        specified blade type. The tuple is in the form '(public_path,
        private_path)' The value of 'private_path' is suitable for use
        with the '-i' option of 'ssh'. Before returning this call will
        verify that both files can be opened for reading and will fail
        with a ContextualError if either cannot.

        """
        secret_name = self.common.blade_ssh_key_secret(blade_type)
        return self.common.ssh_key_paths(secret_name)

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
            self.common, blade_type, instance, remote_port
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
            PrivateBladeConnection(
                self.common, blade_type, instance, remote_port
            )
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
    def __init__(self, common):
        """Constructor

        """
        self.common = common

    def __interconnects_by_name(self):
        """Return a dictionary of non-pure-base-class interconnects
        indexed by 'network_name'

        """
        blade_interconnects = self.common.get("blade_interconnects", {})
        try:
            return {
                interconnect['network_name']: interconnect
                for _, interconnect in blade_interconnects.items()
                if not interconnect.get('pure_base_class', False)
            }
        except KeyError as err:
            # Since we are going to error out anyway, build a list of
            # interconnects without network names so we can give a
            # more useful error message.
            missing_names = [
                key for key, interconnect in blade_interconnects.items()
                if 'network_name' not in interconnect
            ]
            raise ContextualError(
                "provider config error: 'network_name' not specified in "
                "the following blade interconnects: %s" % str(missing_names)
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
    def __init__(self, common, blade_type, instance, remote_port):
        """Constructor

        """
        self.common = common
        self.b_type = blade_type
        self.instance = instance
        self.rem_port = remote_port
        self.hostname = self.common.blade_hostname(
            blade_type, instance
        )
        self.loc_ip = "127.0.0.1"
        self.loc_port = None
        self.subprocess = None
        self._connect()

    def _connect(self):
        """Layer private operation: establish the connection and learn
        the local IP and port of the connection.

        """
        # pylint: disable=protected-access
        zone = self.common.get_zone()

        # pylint: disable=protected-access
        project_id = self.common.get_project_id()

        out_path, err_path = log_paths(
            self.common.build_dir(),
            "connection-%s-port-%d" % (self.hostname, self.rem_port)
        )
        reconnects = 10
        while reconnects > 0:
            # Get a "free" port to use for the connection by briefly
            # binding a TCP server and then destroying it before it
            # listens on anything.
            with TCPServer((self.loc_ip, 0), None) as tmp:
                self.loc_port = tmp.server_address[1]

            with logfile(out_path) as out, logfile(err_path) as err:
                # Not using 'with' for the Popen because the Popen
                # object becomes part of this class instance for the
                # duration of the class instance's life cycle. The
                # instance itself is handed out through a context
                # manager which will disconnect and destroy the Popen
                # object when the context ends.
                #
                # pylint: disable=consider-using-with
                cmd = [
                    'gcloud', 'compute', '--project=%s' % project_id,
                    'start-iap-tunnel',
                    '--zone=%s' % zone,
                    '--local-host-port=%s:%s' % (self.loc_ip, self.loc_port),
                    self.hostname,
                    str(self.rem_port)
                ]
                self.subprocess = Popen(
                    cmd,
                    stdout=out, stderr=err,
                    text=True, encoding='UTF-8'
                )

            # Wait for the tunnel to be established before returning.
            retries = 60
            while retries > 0:
                # If the connection command fails, then break out of
                # the loop, since there is no point trying to connect
                # to a port that will never be there.
                exit_status = self.subprocess.poll()
                if exit_status is not None:
                    info_msg(
                        "IAP connection to '%s' on port %d "
                        "terminated with exit status %d [%s%s]" % (
                            self.hostname, self.rem_port, exit_status,
                            "retrying" if reconnects > 1 else "failing",
                            " - details in '%s'" % err_path if reconnects <= 1
                            else ""
                        )
                    )
                    break
                with socket(AF_INET, SOCK_STREAM) as tmp:
                    try:
                        tmp.connect((self.loc_ip, self.loc_port))
                        return
                    except ConnectionRefusedError:
                        sleep(1)
                        retries -= 1
                    except Exception as err:
                        self._disconnect()
                        raise ContextualError(
                            "internal error: failed attempt to connect to "
                            "service on IAP tunnel to '%s' port %d "
                            "(local port = %s, local IP = %s) "
                            "connect cmd was %s - %s" % (
                                self.hostname, self.rem_port,
                                self.loc_port, self.loc_ip,
                                str(cmd),
                                str(err)
                            ),
                            out_path, err_path
                        ) from err
            # If we got out of the loop either the connection command
            # terminated or we timed out trying to connect, keep
            # trying the connection from scratch a few times.
            reconnects -= 1
            self._disconnect()
            # If we timed out, we have waited long enough to reconnect
            # immediately. If not, give it some time to get better
            # then reconnect.
            if retries > 0:
                sleep(10)
        # The reconnect loop ended without a successful connection,
        # report the error and bail out...
        raise ContextualError(
            "internal error: timeout waiting for IAP connection to '%s' "
            "port %d to be ready (local port = %s, local IP = %s) "
            "- connect command was %s" % (
                self.hostname, self.rem_port,
                self.loc_port, self.loc_ip,
                str(cmd)
            ),
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
        return self.b_type

    def blade_hostname(self):
        """Return the hostname of the connected Virtual Blade.

        """
        return self.hostname

    def local_ip(self):
        """Return the locally reachable IP address of the connection
        to the Virtual Blade.

        """
        return self.loc_ip

    def local_port(self):
        """Return the TCP port number on the locally reachable IP
        address of the connection to the Virtual Blade.

        """
        return self.loc_port


class PrivateSecrets(Secrets):
    """Provider Layers Secrets API object. Provides ways to populate
    and retrieve secrets through the Provider layer. Secrets are
    created by the provider layer by declaring them in the Provider
    configuration for your vTDS system, and should be known by their
    names as filled out in various places and verious layers in your
    vTDS system. For example the SSH key pair used to talk to a
    particular set of Virtual Blades through a blade connection is
    stored in a secret configured in the Provider layer and the name
    of that secret can be obtained from a VirtualBlades API object
    using the blade_ssh_key_secret() method.

    """
    def __init__(self, secret_manager):
        """Construtor

        """
        self.secret_manager = secret_manager

    def store(self, name, value):
        """Store a value (string) in the named secret.

        """
        self.secret_manager.store(name, value)

    def read(self, name):
        """Read the value (string) stored in a named secret. If no
        value is present, return None.

        """
        return self.secret_manager.read(name)
