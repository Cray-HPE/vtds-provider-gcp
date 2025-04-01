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
"""A class that provides common tools based on configuration
and so forth that relate to the GCP vTDS provider.

"""
from os.path import join as path_join
from subprocess import (
    PIPE
)

from vtds_base import (
    ContextualError,
    run,
    log_paths
)


class Common:
    """A class that provides common tools based on configuration and
    so forth that relate to the GCP vTDS provider.

    """
    # For caching purposes, once a project ID has been computed it
    # will be shared among all instances. Worst case (in case of
    # multi-threading) we compute this twice before one of the threads
    # assigns a value to it. The value will be the same no matter who
    # assigns it, and assignment itself should be atomic, so no real
    # threading issues to worry about.
    project_id = None

    def __init__(self, config, build_dir):
        """Constructor.

        """
        self.config = config
        self.build_directory = build_dir

    def __get_blade(self, blade_class):
        """class private: retrieve the blade class deascription for the
        named class.

        """
        virtual_blades = (
            self.config.get('virtual_blades', {})
        )
        blade = virtual_blades.get(blade_class, None)
        if blade is None:
            raise ContextualError(
                "cannot find the virtual blade class '%s'" % blade_class
            )
        if blade.get('pure_base_class', False):
            raise ContextualError(
                "blade class '%s' is a pure pure base class" % blade_class
            )
        return blade

    def __get_blade_interconnect(self, blade_class, interconnect):
        """class private: Get the named interconnect information from
        the specified Virtual Blade class.

        """
        blade = self.__get_blade(blade_class)
        blade_interconnect = blade.get('blade_interconnect', None)
        if blade_interconnect is None:
            raise ContextualError(
                "provider config error: Virtual Blade class '%s' has no "
                "blade interconnect configured" % blade_class
            )
        if blade_interconnect.get("subnetwork", None) != interconnect:
            raise ContextualError(
                "Virtual Blade class '%s' is not configured to use "
                "blade interconnect '%s'" % (blade_class, interconnect)
            )
        return blade_interconnect

    def __check_blade_instance(self, blade_class, instance):
        """class private: Ensure that the specified instance number
        for a given blade class (blades) is legal.

        """
        if not isinstance(instance, int):
            raise ContextualError(
                "Virtual Blade instance number must be integer not '%s'" %
                type(instance)
            )
        blade = self.__get_blade(blade_class)
        count = int(blade.get('count', 0))
        if instance < 0 or instance >= count:
            raise ContextualError(
                "instance number %d out of range for Virtual Blade "
                "class '%s' which has a count of %d" %
                (instance, blade_class, count)
            )

    def get_config(self):
        """Get the full config data stored here.

        """
        return self.config

    def get(self, key, default):
        """Perform a 'get' operation on the top level 'config' object
        returning the value of 'default' if 'key' is not found.

        """
        return self.config.get(key, default)

    def build_dir(self):
        """Return the 'build_dir' provided at creation.

        """
        return self.build_directory

    def get_project_id(self):
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
        result = run(
            [
                'gcloud', 'projects', 'list',
                '--filter=name=%s' % project_name,
                '--format=value(PROJECT_ID)'
            ],
            log_paths(self.build_directory, "common-get-project-id"),
            stdout=PIPE,
            check=False
        )
        # Reference the class variable using the class name to set it.
        Common.project_id = result.stdout.rstrip()
        Common.project_id = Common.project_id if Common.project_id else None
        return self.project_id

    def get_zone(self):
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

    def blade_application_metadata(self, blade_class):
        """Get the 'application_metadata' section of a named blade
        class.

        """
        blade = self.__get_blade(blade_class)
        return blade.get('application_metadata', {})

    def blade_hostname(self, blade_class, instance):
        """Get the hostname of a given instance of the specified class
        of Virtual Blade.

        """
        self.__check_blade_instance(blade_class, instance)
        blade = self.__get_blade(blade_class)
        if 'hostname' not in blade:
            raise ContextualError(
                "provider config error: no 'hostname' configured for "
                "Virtual Blade class '%s'" % blade_class
            )
        count = self.blade_count(blade_class)
        add_suffix = blade.get('add_hostname_suffix', count > 1)
        hostname = blade['hostname']
        separator = (
            blade.get('hostname_suffix_separator', "") if add_suffix else ""
        )
        # Suffixes are 1 based, not 0 based, instances are 0 based
        suffix = "%3.3d" % (instance + 1) if add_suffix else ""
        return hostname + separator + suffix

    def blade_ip(self, blade_class, instance, interconnect):
        """Return the IP address (string) on the named Blade
        Interconnect of a specified instance of the named Virtual
        Blade class.

        """
        self.__check_blade_instance(blade_class, instance)
        blade_interconnect = self.__get_blade_interconnect(
            blade_class, interconnect
        )
        ip_addrs = blade_interconnect.get('ip_addrs', None)
        if not ip_addrs:
            raise ContextualError(
                "provider config error: Virtual Blade class '%s' has no "
                "'ip_addrs' configured"
            )
        if instance >= len(ip_addrs):
            raise ContextualError(
                "provider config error: Virtual Blade class is configured "
                "with fewer ip_addrs (%d) than blade instances (%d)" %
                (len(ip_addrs), self.blade_count(blade_class))
            )
        return ip_addrs[instance]

    def blade_count(self, blade_class):
        """Get the number of Virtual Blade instances of the specified
        class.

        """
        blade = self.__get_blade(blade_class)
        return int(blade.get('count', 0))

    def blade_interconnects(self, blade_class):
        """Return the list of Blade Interconnects by name connected to
        the specified class of Virtual Blade.

        """
        blade = self.__get_blade(blade_class)
        # The GCP provider only lets us have one interconnect per
        # blade class, so we are just going to go grab that and make it
        # into a 'list' of one item.
        name = blade.get('blade_interconnect', {}).get('subnetwork', None)
        if name is None:
            raise ContextualError(
                "provider config error: no 'blade_interconnect.subnetwork' "
                "found in blade class '%s'" % blade_class
            )
        return [name]

    def blade_ssh_key_secret(self, blade_class):
        """Return the name of the secret used to store the SSH key
        pair used to reach blades of the specified class through a
        tunneled SSH connection.

        """
        blade = self.__get_blade(blade_class)
        secret_name = blade.get('ssh_key_secret', None)
        if secret_name is None:
            raise ContextualError(
                "provider config error: no 'ssh_key_secret' "
                "found in blade class '%s'" % blade_class
            )
        return secret_name

    def ssh_key_paths(self, secret_name, ignore_missing=False):
        """Return a tuple of paths to files containing the public and
        private SSH keys used to to authenticate with blades of the
        specified blade class. The tuple is in the form '(public_path,
        private_path)' The value of 'private_path' is suitable for use
        with the '-i' option of 'ssh'. If 'ignore_missing' is set, to
        True, the path names will be generated, but no check will be
        done to verify that the files exist. By default, or if
        'ignore_missing' is set to False, this function will verify
        that the files can be opened for reading and raise a
        ContextualError if they cannot.

        """
        ssh_dir = path_join(self.build_dir(), 'blade_ssh_keys', secret_name)
        private_path = path_join(ssh_dir, "id_rsa")
        public_path = path_join(ssh_dir, "id_rsa.pub")
        if not ignore_missing:
            try:
                # Verify that we can open both paths. No need to do
                # anything with them.
                with open(public_path, 'r', encoding='UTF-8') as _:
                    pass
                with open(private_path, 'r', encoding='UTF-8') as _:
                    pass
            except OSError as err:
                raise ContextualError(
                    "failed to open SSH key file for reading "
                    "(verification) - %s" % str(err)
                ) from err
        return (public_path, private_path)

    def system_name(self):
        """Get the system name used to create the cluster on the
        provider. Returns a string representing the system name.

        """
        name = (
            self.config.get('project', {}).get('base_name', None)
        )
        if name is None:
            raise ContextualError(
                "provider config error: cannot find 'base_name' in "
                "'provider.project' when trying to construct the system "
                "name"
            )
        return name

    def site_ntp_server(self, address_family):
        """Get the hostname / address of the NTP server offered by the
        provider or site in the specified address family. The
        'address_family' parameter is a string specifies the address
        family of the address to be returned, with a default value of
        'AF_INET'. Returns a dictionary containing the following
        fields:

        - 'address_family' - the requested address family as passed in
        - 'hostname' - the host name of the NTP server if known, None if not
        - 'address' - the address within the address family of the NTP
          server if known, None if not

        Returns an empty dictionary if the specified 'address_family'
        is not supported by the provider or not configured in the
        Provider configuration.

        """
        servers = (
            self.config.get('project', {})
            .get('site', {})
            .get('ntp', None)
            .get(address_family, [])
        )
        return [
            {
                'address_family': address_family,
                'hostname': server.get('hostname', None),
                'address': server.get('address', None)
            }
            for server in servers
        ]

    def site_dns_servers(self, address_family='AF_INET'):
        """Get the address of the DNS server offered by the provider
        or site on the specified address family. The address_family'
        parameter is a string specifies the address family of the
        address to be returned, with a default value of
        'AF_INET'. Returns a list of dictionaries containing the
        following fields:

        - 'address_family' - the requested address family as passed in
        - 'address' - the address within the address family of the NTP
          server if known, None if not

        Returns an empty list if the specified 'address_family'
        is not supported by the provider or not configured in the
        Provider configuration.

        """
        servers = (
            self.config.get('project', {})
            .get('site', {})
            .get('dns', None)
            .get(address_family, [])
        )
        return [
            {
                'address_family': address_family,
                'address': server.get('address', None)
            }
            for server in servers
        ]
