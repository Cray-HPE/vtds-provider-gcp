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
"""Objects presented on the Layer API containing public information
and operations in the provider layer.

"""
from contextlib import contextmanager
from abc import (
    ABCMeta,
    abstractmethod
)


class VirtualBlades(metaclass=ABCMeta):
    """A class implementing public access to Virtual Blades and their
    operations.

    """
    @abstractmethod
    def blade_types(self):
        """Get a list of virtual blade types by name.

        """

    @abstractmethod
    def blade_count(self, blade_type):
        """Get the number of Virtual Blade instances of the specified
        type.

        """

    @abstractmethod
    def blade_interconnects(self, blade_type):
        """Return the list of Blade Interconnects by name connected to
        the specified type of Virtual Blade.

        """

    @abstractmethod
    def blade_hostname(self, blade_type, instance):
        """Get the hostname of a given instance of the specified type
        of Virtual Blade.

        """

    @abstractmethod
    def blade_ip(self, blade_type, instance, interconnect):
        """Return the IP address (string) on the named Blade
        Interconnect of a specified instance of the named Virtual
        Blade type.

        """

    @abstractmethod
    @contextmanager
    def connect_blade(self, remote_port, blade_type, instance):
        """Establish an external connection to the specified remote
        port on the specified instance of the named Virtual Blade
        type. Return a context manager (suitable for use in a 'with'
        clause) yielding an APIBladeConnection object for the
        connection. Upon leaving the 'with' context, the connection in
        the APIBladeConnection is closed.

        """

    @contextmanager
    @abstractmethod
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


class BladeInterconnects(metaclass=ABCMeta):
    """The external representation of the set of Blade Interconnects
    and public operations that can be performed on the interconnects.

    """
    @abstractmethod
    def interconnect_names(self):
        """Get a list of blade interconnects by name

        """

    @abstractmethod
    def ipv4_cidr(self, interconnect_name):
        """Return the (string) IPv4 CIDR (<IP>/<length>) for the
        network on the named interconnect.

        """


class BladeConnection(metaclass=ABCMeta):
    """A class containing the relevant information needed to use
    external connections to ports on a specific Virtual Blade.

    """
    @abstractmethod
    def blade_type(self):
        """Return the name of the Virtual Blade type of the connected
        Virtual Blade.

        """

    @abstractmethod
    def blade_hostname(self):
        """Return the hostname of the connected Virtual Blade.

        """

    @abstractmethod
    def local_ip(self):
        """Return the locally reachable IP address of the connection
        to the Virtual Blade.

        """

    @abstractmethod
    def local_port(self):
        """Return the TCP port number on the locally reachable IP
        address of the connection to the Virtual Blade.

        """
