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

    def __get_blade_interconnect(self, blade_type, interconnect):
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

    def __check_blade_instance(self, blade_type, instance):
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

    def blade_hostname(self, blade_type, instance):
        """Get the hostname of a given instance of the specified type
        of Virtual Blade.

        """
        self.__check_blade_instance(blade_type, instance)
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
        self.__check_blade_instance(blade_type, instance)
        blade_interconnect = self.__get_blade_interconnect(
            blade_type, interconnect
        )
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

    def blade_ssh_key_secret(self, blade_type):
        """Return the name of the secret used to store the SSH key
        pair used to reach blades of the specified type through a
        tunneled SSH connection.

        """
        blade = self.__get_blade(blade_type)
        # The GCP provider only lets us have one interconnect per
        # blade type, so we are just going to go grab that and make it
        # into a 'list' of one item.
        secret_name = blade.get('ssh_key_secret', None)
        if secret_name is None:
            raise ContextualError(
                "provider config error: no 'ssh_key_secret' "
                "found in blade type '%s'" % blade_type
            )
        return secret_name

    def ssh_key_paths(self, secret_name, ignore_missing=False):
        """Return a tuple of paths to files containing the public and
        private SSH keys used to to authenticate with blades of the
        specified blade type. The tuple is in the form '(public_path,
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
                # pylint: disable=consider-using-with
                open(public_path, 'r', encoding='UTF-8').close()
                # pylint: disable=consider-using-with
                open(private_path, 'r', encoding='UTF-8').close()
            except OSError as err:
                raise ContextualError(
                    "failed to open SSH key file for reading "
                    "(verification) - %s" % str(err)
                ) from err
        return (public_path, private_path)
