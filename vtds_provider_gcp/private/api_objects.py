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
from subprocess import (
    Popen,
    TimeoutExpired
)
from socketserver import TCPServer
from socket import (
    socket,
    AF_INET,
    SOCK_STREAM
)
from time import sleep
from jinja2 import (
    Template,
    TemplateError
)

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
    BladeConnectionSet,
    BladeSSHConnection,
    BladeSSHConnectionSet,
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
    def connect_blade(self, blade_type, instance, remote_port):
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
        the list of BladeConnection objects representing the
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
            yield PrivateBladeConnectionSet(self.common, connections)
        finally:
            for connection in connections:
                # This is a layer private operation not really class
                # private. Treat this reference as friendly.
                connection._disconnect()  # pylint: disable=protected-access

    @contextmanager
    def ssh_connect_blade(self, blade_type, instance, remote_port=22):
        """Establish an external connection to the SSH server on the
        specified instance of the named Virtual Blade type. Return a
        context manager (suitable for use in a 'with' clause) yielding
        a BladeSSHConnection object for the connection. Upon leaving the
        'with' context, the connection in the BladeSSHConnection is
        closed.

        """
        connection = PrivateBladeSSHConnection(
            self.common, blade_type, instance,
            self.blade_ssh_key_paths(blade_type)[1],
            remote_port
        )
        try:
            yield connection
        finally:
            # This is a layer private operation not really class
            # private. Treat this reference as friendly.
            connection._disconnect()  # pylint: disable=protected-access

    @contextmanager
    def ssh_connect_blades(self, blade_types=None, remote_port=22):
        """Establish external connections to the SSH server on all the
        Virtual Blade instances on all the Virtual Blade types listed
        by name in 'blade_types'. If 'blade_types' is not provided or
        None, all available blade types are used. Return a context
        manager (suitable for use in a 'with' clause) yielding a
        BladeSSHConnectionSet object representing the
        connections. Upon leaving the 'with' context, all the
        connections create are closed.

        """
        blade_types = (
            self.blade_types() if blade_types is None else blade_types
        )
        connections = [
            PrivateBladeSSHConnection(
                self.common, blade_type, instance,
                self.blade_ssh_key_paths(blade_type)[1],
                remote_port
            )
            for blade_type in blade_types
            for instance in range(0, self.blade_count(blade_type))
        ]
        try:
            yield PrivateBladeSSHConnectionSet(self.common, connections)
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

    def remote_port(self):
        """Return the TCP port number on the on the Virtual blade to
        which the BladeConnection connects.

        """
        return self.rem_port

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


class PrivateBladeConnectionSet(BladeConnectionSet):
    """A class that contains multiple active BladeConnections to
    facilitate operations on multiple simultaneous blades. This class
    is just a wrapper for a list of BladeContainers and should be
    obtained using the VirtualBlades.connect_blades() method not
    directly.

    """
    def __init__(self, common, blade_connections):
        """Constructor

        """
        self.common = common
        self.blade_connections = blade_connections

    def list_connections(self, blade_type=None):
        """List the connections in the BladeConnectionSet filtered by
        'blade_type' if that is present. Otherwise imply list all of
        the connections.

        """
        return [
            blade_connection for blade_connection in self.blade_connections
            if blade_type is None or
            blade_connection.blade_type() == blade_type
        ]

    def get_connection(self, hostname):
        """Return the connection corresponding to the specified
        VirtualBlade hostname ('hostname') or None if the hostname is
        not found.

        """
        for blade_connection in self.blade_connections:
            if blade_connection.blade_hostname == hostname:
                return blade_connection
        return None


# The following is shared by PrivateBladeSSHConnection and
# PrivateBladeSSHConnectionSet. This should be treaded as private to
# this file. It is pulled out of both classes for easy sharing.
def wait_for_popen(subprocess, cmd, logpaths, timeout=None, **kwargs):
    """Wait for a Popen() object to reach completion and return
    the exit value.

    If 'check' is either omitted from the keyword arguments or is
    supplied in the keyword aguments and True, raise a
    ContextualError if the command exists with a non-zero exit
    value, otherwise simply return the exit value.

    If 'timeout' is supplied (in seconds) and exceeded kill the
    Popen() object and then raise a ContextualError indicating the
    timeout and reporting where the command logs can be found.

    """
    info_msg(
        "waiting for popen: "
        "subproc='%s', cmd='%s', logpaths='%s', timeout='%s', kwargs='%s'" % (
            str(subprocess), str(cmd), str(logpaths), str(timeout), str(kwargs)
        )
    )
    check = kwargs.get('check', True)
    time = timeout if timeout is not None else 0
    signaled = False
    while True:
        try:
            exitval = subprocess.wait(timeout=5)
            break
        except TimeoutExpired:
            time -= 5 if timeout is not None else 0
            if timeout is not None and time <= 0:
                if not signaled:
                    # First try to terminate the process
                    subprocess.terminate()
                    continue
                subprocess.kill()
                # pylint: disable=raise-missing-from
                raise ContextualError(
                    "SSH command '%s' timed out and did not terminate "
                    "as expected after %d seconds" % (str(cmd), time),
                    *logpaths
                )
            continue
    if check and exitval != 0:
        raise ContextualError(
            "SSH command '%s' terminated with a non-zero "
            "exit status '%d'" % (str(cmd), exitval),
            *logpaths
        )
    return exitval


class PrivateBladeSSHConnection(BladeSSHConnection, PrivateBladeConnection):
    """Specifically a connection to the SSH server on a blade (remote
    port 22 unless otherwise specified) with methods to copy files to
    and from the blade using SCP and to run commands on the blade
    using SSH.

    """
    def __init__(
        self,
        common, blade_type, instance,  private_key_path, remote_port=22,
        **kwargs
    ):
        PrivateBladeConnection.__init__(
            self,
            common, blade_type, instance, remote_port
        )
        default_opts = [
            '-o', 'BatchMode=yes',
            '-o', 'NoHostAuthenticationForLocalhost=yes',
            '-o', 'StrictHostKeyChecking=no',
        ]
        port_opt = [
            '-o', 'Port=%s' % str(self.loc_port),
        ]
        self.options = kwargs.get('options', default_opts)
        self.options += port_opt
        self.private_key_path = private_key_path

    def __run(
        self, cmd, blocking=True, out_path=None, err_path=None,  **kwargs
    ):
        """Run an arbitrary command under Popen() either synchronously
        or asynchronously letting exceptions bubble up to the caller.

        """
        with logfile(out_path) as out_file, logfile(err_path) as err_file:
            if blocking:
                with Popen(
                        cmd,
                        stdout=out_file, stderr=err_file,
                        **kwargs
                ) as subprocess:
                    return wait_for_popen(
                        subprocess, cmd, (out_path, err_path), None, **kwargs
                    )
            else:
                return Popen(
                    cmd,
                    stdout=out_file, stderr=err_file,
                    **kwargs
                )

    def _render_cmd(self, cmd):
        """Layer private: render the specified command string with
        Jinja to fill in the BladeSSHConnection specific data in a
        templated command.

        """
        jinja_values = {
            'blade_type': self.b_type,
            'instance': self.instance,
            'blade_hostname': self.hostname,
            'remote_port': self.rem_port,
            'local_ip': self.loc_ip,
            'local_port': self.loc_port
        }
        try:
            template = Template(cmd)
            return template.render(**jinja_values)
        except TemplateError as err:
            raise ContextualError(
                "error using Jinja to render command line '%s' - %s" % (
                    cmd,
                    str(err)
                )
            ) from err

    def copy_to(
            self, source, destination,
            recurse=False, blocking=True, logname=None, **kwargs
    ):
        """Copy a file from a path on the local machine ('source') to
        a path on the virtual blade ('dest'). The SCP operation is run
        under a subprocess.Popen() object, which is returned at the
        end of the call. If additional keyword arguments are supplied,
        they may be used to override defaults set up by this function
        and passed to subprocess.Popen() or simply passed on to
        subprocess.Popen() as keyword arguments.

        If the 'recurse' argument is 'True' and the source is a
        directory, the directory and all of its descendents will be
        copied. Otherwise, the source should be a file and it alone
        will be copied.

        If the 'blocking' option is True (default), copy_to() will
        block waiting for the copy to complete (or fail) and raise a
        ContextualError exception if it fails. If the 'blocking'
        option is False, copy_to() will return immediately once the
        Popen() object is created and let the caller manage the
        sub-process.

        If the 'logname' argument is provided and not None, use the
        string found there to compose a pair of log files to capture
        standard output and standard error. Otherwise a generic log
        name is created.

        """
        logname = (
            logname if logname is not None else
            "copy-to-%s-%s" % (source, destination)
        )
        logfiles = log_paths(
            self.common.build_dir(),
            "%s-%s" % (logname, self.blade_hostname())
        )
        recurse_option = ['-r'] if recurse else []
        cmd = [
            'scp', '-i', self.private_key_path, *recurse_option, *self.options,
            source,
            'root@%s:%s' % (self.loc_ip, destination)
        ]
        try:
            return self.__run(cmd, blocking, *logfiles, **kwargs)
        except ContextualError:
            # If it is one of ours just send it on its way to be handled
            raise
        except Exception as err:
            # Not one of ours, turn it into one of ours
            raise ContextualError(
                "failed to copy file '%s' to 'root@%s:%s' "
                "using command: %s - %s" % (
                    source, self.hostname, destination, str(cmd), str(err)
                ),
                *logfiles
            ) from err

    def copy_from(
        self, source, destination,
            recurse=False, blocking=True, logname=None, **kwargs
    ):
        """Copy a file from a path on the blade ('source') to a path
        on the local machine ('dest'). The SCP operation is run under
        a subprocess.Popen() object, which is returned at the end of
        the call. If additional keyword arguments are supplied, they
        may be used to override defaults set up by this function and
        passed to subprocess.Popen() or simply passed on to
        subprocess.Popen() as keyword arguments.

        If the 'recurse' argument is 'True' and the source is a
        directory, the directory and all of its descendents will be
        copied. Otherwise, the source should be a file and it alone
        will be copied.

        If the 'blocking' option is True (default), copy_from() will
        block waiting for the copy to complete (or fail) and raise a
        ContextualError exception if it fails. If the 'blocking'
        option is False, copy_from() will return immediately once the
        Popen() object is created and let the caller manage the
        sub-process.

        If the 'logname' argument is provided and not None, use the
        string found there to compose a pair of log files to capture
        standard output and standard error. Otherwise a generic log
        name is created.

        """
        logname = (
            logname if logname is not None else
            "copy-from-%s-%s" % (source, destination)
        )
        logfiles = log_paths(
            self.common.build_dir(),
            "%s-%s" % (logname, self.blade_hostname())
        )
        recurse_option = ['-r'] if recurse else []
        cmd = [
            'scp', '-i', self.private_key_path, *recurse_option, *self.options,
            'root@%s:%s' % (self.loc_ip, destination),
            source
        ]
        try:
            return self.__run(cmd, blocking, *logfiles, **kwargs)
        except ContextualError:
            # If it is one of ours just send it on its way to be handled
            raise
        except Exception as err:
            # Not one of ours, turn it into one of ours
            raise ContextualError(
                "failed to copy file '%s' from 'root@%s:%s' "
                "using command: %s - %s" % (
                    destination, self.hostname, source, str(cmd), str(err)
                ),
                *logfiles,
            ) from err

    def run_command(self, cmd, blocking=True, logfiles=None, **kwargs):
        """Using SSH, run the command in the string 'cmd'
        asynchronously on the blade. The string 'cmd' can be templated
        using Jinja templating to use any of the attributes of the
        underlying connection:

        - the blade type: 'blade_type'
        - the blade instance within its type: 'instance'
        - the blade hostname: 'blade_hostname'
        - the connection port on the blade: 'remote_port'
        - the local connection IP address: 'local_ip'
        - the local connection port: 'local_port'

        The resulting command will be executed by the shell on the
        blade under an SSH session by creating a subprocess.Popen()
        object. If additional keyword arguments are supplied, they may
        be used to override defaults set up by this function and
        passed to subprocess.Popen() or simply passed on to
        subprocess.Popen() as keyword arguments.

        If the 'logfiles' argument is provided, it contains a two
        element tuple telling run_command where to put standard output
        and standard error logging for the command respectively.
        Normally, these are specified as pathnames to log
        files. Either or both can also be a file object or None. If a
        file object is used, the output is written to the file. If
        None is used, the corresponding output is not redirected and
        the default Popen() behavior is used.

        If the 'blocking' option is True (default), run_command() will
        block waiting for the command to complete (or fail) and raise
        a ContextualError exception if it fails. If the 'blocking'
        option is False, run_command() will return immediately once the
        Popen() object is created and let the caller manage the
        sub-process.

        """
        cmd = self._render_cmd(cmd)
        logfiles = logfiles if logfiles is not None else (None, None)
        ssh_cmd = [
            'ssh', '-i', self.private_key_path, *self.options,
            'root@%s' % (self.loc_ip), cmd
        ]
        try:
            return self.__run(ssh_cmd, blocking, *logfiles, **kwargs)
        except ContextualError:
            # If it is one of ours just send it on its way to be handled
            raise
        except Exception as err:
            # Not one of ours, turn it into one of ours
            raise ContextualError(
                "failed to run command '%s' on '%s' - %s" % (
                    cmd, self.hostname, str(err)
                ),
                *logfiles
            ) from err


class PrivateBladeSSHConnectionSet(
        BladeSSHConnectionSet, PrivateBladeConnectionSet
):
    """A class to wrap multiple BladeSSHConnections and provide
    operations that run in parallel across multiple connections.

    """
    def __init__(self, common, connections):
        """Constructor
        """
        PrivateBladeConnectionSet.__init__(self, common, connections)

    def copy_to(
        self, source, destination,
        recurse=False, logname=None, blade_type=None
    ):
        """Copy the file at a path on the local machine ('source') to
        a path ('dest') on all of the selected blades (based on
        'blade_type'). If 'blade_type is not specified or None, copy
        the file to all connected blades. Wait until all copies
        complete or fail. If any of the copies fail, collect the
        errors they produce to raise a ContextualError exception
        describing the failures.

        If the 'recurse' option is True and the local file is a
        directory, the directory and all of its descendants will be
        copied.

        If the 'logname' argument is provided, use the string found
        there to compose the 'logfiles' argument to be passed to each
        copy operation.

        """
        logname = (
            logname if logname is not None else
            "parallel-copy-to-%s-%s" % (source, destination)
        )
        # Okay, this is big and weird. It composes the arguments to
        # pass to wait_for_popen() for each copy operation. Note
        # that, normally, the 'cmd' argument in wait_for_popen() is
        # the Popen() 'cmd' argument (i.e. a list of command
        # compoinents. Here it is simply a descriptive string. This is
        # okay because wait_for_popen() only uses that information
        # for error generation.
        wait_args_list = [
            (
                blade_connection.copy_to(
                    source, destination, recurse=recurse, blocking=False,
                    logname=logname
                ),
                "scp %s to root@%s:%s" % (
                    source,
                    blade_connection.blade_hostname(),
                    destination
                ),
                log_paths(
                    self.common.build_dir(),
                    "%s-%s" % (logname, blade_connection.blade_hostname())
                )
            )
            for blade_connection in self.blade_connections
            if blade_type is None or
            blade_connection.blade_type() == blade_type
        ]
        # Go through all of the copy operations and collect (if
        # needed) any errors that are raised by
        # wait_for_popen(). This acts as a barrier, so when we are
        # done, we know all of the copies have completed.
        errors = []
        for wait_args in wait_args_list:
            try:
                wait_for_popen(*wait_args)
            # pylint: disable=broad-exception-caught
            except Exception as err:
                errors.append(str(err))
        if errors:
            raise ContextualError(
                "errors reported while copying '%s' to '%s' on %s\n"
                "    %s" % (
                    source,
                    destination,
                    "all Virtual Blades" if blade_type is None else
                    "Virtual Blades of type %s" % blade_type,
                    "\n\n    ".join(errors)
                )
            )

    def run_command(self, cmd, logname=None, blade_type=None):
        """Using SSH, run the command in the string 'cmd'
        asynchronously on all connected blades filtered by
        'blade_type'. If 'blade_type' is unspecified or None, run on
        all connected blades. The string 'cmd' can be templated using
        Jinja templating to use any of the attributes of the
        underlying connection. In this case, the connection in which
        the command is being run will be used for the templating, so,
        for example, 'blade_hostname' will match the blade on which
        the command runs:

        - the blade type: 'blade_type'
        - the blade hostname: 'blade_hostname'
        - the connection port on the blade: 'remote_port'
        - the local connection IP address: 'local_ip'
        - the local connection port: 'local_port'

        Wait until all commands complete or fail. If any of the
        commands fail, collect the errors they produce to raise a
        ContextualError exception describing the failures.

        If the 'logname' argument is provided, use the string found
        there to compose paths to two files, one that will contain the
        standard output from the command and one that will contain the
        standard input. The paths to these files will be included in
        any error reporting from the operation.

        """
        logname = (
            logname if logname is not None else
            "parallel-run-%s" % (cmd.split()[0])
        )
        # Okay, this is big and weird. It composes the arguments to
        # pass to wait_for_popen() for each copy operation. Note
        # that, normally, the 'cmd' argument in wait_for_popen() is
        # the Popen() 'cmd' argument. Here is is simply the shell
        # command being run under SSH. This is okay because
        # wait_for_popen() only uses that information for error
        # generation.
        wait_args_list = [
            (
                blade_connection.run_command(
                    cmd, False,
                    log_paths(
                        self.common.build_dir(),
                        "%s-%s" % (logname, blade_connection.blade_hostname())
                    )
                ),
                cmd,
                log_paths(
                    self.common.build_dir(),
                    "%s-%s" % (logname, blade_connection.blade_hostname())
                )
            )
            for blade_connection in self.blade_connections
            if blade_type is None or
            blade_connection.blade_type() == blade_type
        ]
        # Go through all of the copy operations and collect (if
        # needed) any errors that are raised by
        # wait_for_popen(). This acts as a barrier, so when we are
        # done, we know all of the copies have completed.
        errors = []
        for wait_args in wait_args_list:
            try:
                wait_for_popen(*wait_args)
            # pylint: disable=broad-exception-caught
            except Exception as err:
                errors.append(str(err))
        if errors:
            raise ContextualError(
                "errors reported running command '%s' on %s\n"
                "    %s" % (
                    cmd,
                    "all Virtual Blades" if blade_type is None else
                    "Virtual Blades of type %s" % blade_type,
                    "\n\n    ".join(errors)
                )
            )


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
