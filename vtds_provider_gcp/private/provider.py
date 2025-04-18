#
# MIT License
#
# (C) Copyright 2024-2025 Hewlett Packard Enterprise Development LP
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
"""Private layer implementation module for the GCP provider.

"""
import os
from os.path import dirname
from os import makedirs
from shutil import rmtree
from yaml import (
    safe_load,
    safe_dump
)

from vtds_base import (
    ContextualError,
    expand_inheritance,
    run,
    log_paths
)
from vtds_base.layers.provider import ProviderAPI

# Import private classes
from .terragrunt import (
    Terragrunt,
    TerragruntConfig
)
from .virtual_blade import VirtualBlade
from .blade_interconnect import BladeInterconnect
from .api_objects import (
    SiteConfig,
    VirtualBlades,
    BladeInterconnects,
    Secrets
)
from .common import Common
from .secret_manager import SecretManager


class Provider(ProviderAPI):
    """Provider class, implements the GCP provider layer accessed
    through the python Provider API.

    """
    def __init__(self, stack, config, build_dir):
        """Constructor, stash the root of the provider tree and the
        digested and finalized provider configuration provided by the
        caller that will drive all activities at all layers.

        """
        self.__doc__ = ProviderAPI.__doc__
        provider_config = config.get('provider', None)
        if provider_config is None:
            raise ContextualError(
                "no provider configuration found in top level configuration"
            )
        self.common = Common(provider_config, build_dir)
        self.terragrunt = Terragrunt(self.common)
        self.terragrunt_config = TerragruntConfig(self.common, self.terragrunt)
        self.secret_manager = SecretManager(self.common)
        self.stack = stack
        self.prepared = False

    def __read_key_secrets(self, secret_name):
        """Read SSH keys back from an SSH keys directory in the build
        tree based on the SSH key secret name for the secret that
        holds the keys.

        """
        pub_key, priv_key = self.common.ssh_key_paths(secret_name)
        # Read back the keys into a dictionary to return to the caller
        with open(priv_key, 'r', encoding='UTF-8') as private, \
             open(pub_key, 'r', encoding='UTF-8') as public:
            keys = {
                'private': private.read().rstrip(),
                'public': public.read().rstrip(),
            }
        return keys

    def __generate_blade_ssh_keys(self, secret_name):
        """Set up an SSH key pair and store it in the named secret.

        """
        # Make sure there is a fresh empty directory in place for the keys.
        _, priv_key = self.common.ssh_key_paths(secret_name, True)
        ssh_dir = dirname(priv_key)
        rmtree(ssh_dir, ignore_errors=True)
        makedirs(ssh_dir, mode=0o700, exist_ok=True)

        # Make the keys.
        run(
            ['ssh-keygen', '-q', '-N', '', '-t', 'rsa', '-f', priv_key],
            log_paths(self.common.build_dir(), "make-ssh-key-%s" % secret_name)
        )
        return self.__read_key_secrets(secret_name)

    def __cache_ssh_keys(self, secret_data, secret_name):
        """Store the SSH keys found in 'secret_data' in the build
        tree for use by commands that need SSH connections.

        """
        pub_key, priv_key = self.common.ssh_key_paths(secret_name, True)
        ssh_dir = dirname(priv_key)
        rmtree(ssh_dir, ignore_errors=True)
        makedirs(ssh_dir, mode=0o700, exist_ok=True)
        keys = safe_load(secret_data)

        # Make sure that the file is created with owner only 'rw'
        # permissions.
        def open_safe(path, flags):
            return os.open(path, flags, 0o600)

        with open(
            pub_key, mode='w', opener=open_safe, encoding='UTF-8'
        ) as pub_key_file:
            pub_key_file.write("%s\n" % keys['public'])
        with open(
                priv_key, mode='w', opener=open_safe, encoding='UTF-8'
        ) as priv_key_file:
            priv_key_file.write("%s\n" % keys['private'])
        return keys

    def __add_ssh_key(self, blade_class, blade_config):
        """Add the SSH public key from the blade's ssh_key_secret to
        the blade metadata so that when the blade is deployed it will
        have the proper authorized key for SSH access through a blade
        connection.

        """
        secret_name = blade_config.get("ssh_key_secret", None)
        if secret_name is None:
            raise ContextualError(
                "provider config error: no 'ssh_key_secret' "
                "found in blade class '%s'" % blade_class
            )
        secret_data = self.secret_manager.read(secret_name)
        keys = (
            self.__cache_ssh_keys(secret_data, secret_name)
            if secret_data is not None
            else self.__generate_blade_ssh_keys(secret_name)
        )
        # This weird little dance makes sure that 'metadata' is in
        # blade_config and has a sub-KV pair 'metadata' where we can
        # put the SSH public key(s).
        blade_config['metadata'] = blade_config.get('metadata', {})
        blade_config['metadata']['metadata'] = (
            blade_config['metadata'].get('metadata', {})
        )
        public_key = "root:%s\n" % keys['public']
        blade_config['metadata']['metadata']['ssh-keys'] = public_key

    def __create_blade_ssh_secrets(self):
        """For each unique SSH key secret in the configuration, read
        in the public and private keys from the build directory data,
        create a secret of the appropriate name in the project, and
        store the keys in the secret.

        """
        virtual_blades = self.get_virtual_blades()
        # Get all of the SSH key secret names for all blade classes in a
        # set so they are unique
        secret_names = {
            virtual_blades.blade_ssh_key_secret(blade_class)
            for blade_class in virtual_blades.blade_classes()
        }
        for secret_name in secret_names:
            keys = self.__read_key_secrets(secret_name)
            self.secret_manager.store(secret_name, safe_dump(keys))

    def consolidate(self):
        blade_classes = self.common.get('virtual_blades', None)
        if blade_classes is None:
            raise ContextualError(
                "no virtual blade classes found in vTDS provider configuration"
            )
        # Expand the inheritance tree for the blade classes and put
        # the expanded result back into the configuration. That way,
        # when we write out ro try to use the configuration we have
        # the full expansion there. Doing this in the consolidate()
        # phase means that other consolidate actions by subsequent
        # layers will work on the final working config.
        for blade_class in blade_classes:
            if blade_classes[blade_class].get('pure_base_class', False):
                # Skip inheritance and installation for pure base
                # classes since they have no parents, and they aren't
                # used for deployment.
                continue
            blade_config = expand_inheritance(
                blade_classes, blade_class
            )
            blade_classes[blade_class] = blade_config
        # Expand the inheritance tree for the interconnect types and
        # put the expanded result back into the configuration. That
        # way, when we write out or try to use the configuration we
        # have the full expansion there. Doing this in the
        # consolidate() phase means that other consolidate actions by
        # subsequent layers will work on the final working config.
        interconnect_types = self.common.get('blade_interconnects', None)
        if interconnect_types is None:
            raise ContextualError(
                "no blade interconnect types found in vTDS provider "
                "configuration"
            )
        for interconnect_type in interconnect_types:
            if interconnect_types[interconnect_type].get(
                    'pure_base_class', False
            ):
                # Skip inheritance and installation for pure base
                # classes since they have no parents, and they aren't
                # used for deployment.
                continue
            interconnect_config = expand_inheritance(
                interconnect_types, interconnect_type
            )
            interconnect_types[interconnect_type] = interconnect_config

    def prepare(self):
        self.terragrunt.initialize()
        blade_classes = self.common.get('virtual_blades', None)
        for blade_class in blade_classes:
            if blade_classes[blade_class].get('pure_base_class', False):
                # Skip inheritance and installation for pure base
                # classes since they have no parents, and they aren't
                # used for deployment.
                continue
            virtual_blade = VirtualBlade(self.terragrunt)
            blade_config = virtual_blade.initialize(
                blade_class, blade_classes[blade_class]
            )
            self.__add_ssh_key(blade_class, blade_config)
            blade_classes[blade_class] = blade_config
        interconnect_types = self.common.get('blade_interconnects', None)
        for interconnect_type in interconnect_types:
            if interconnect_types[interconnect_type].get(
                    'pure_base_class', False
            ):
                # Skip inheritance and installation for pure base
                # classes since they have no parents, and they aren't
                # used for deployment.
                continue
            blade_interconnect = BladeInterconnect(self.terragrunt)
            interconnect_config = blade_interconnect.initialize(
                interconnect_type, interconnect_types[interconnect_type]
            )
            interconnect_types[interconnect_type] = interconnect_config

        # Now that we have all the terragrunt controls set up, go
        # ahead and initialize terragrunt.
        self.terragrunt_config.initialize()

        # All done with the preparations: make a note that we have
        # done them and return.
        self.prepared = True

    def validate(self):
        if not self.prepared:
            raise ContextualError(
                "cannot validate an unprepared provider, call prepare() first"
            )
        self.terragrunt.validate()

    def deploy(self):
        if not self.prepared:
            raise ContextualError(
                "cannot deploy an unprepared provider, call prepare() first"
            )
        self.terragrunt.deploy()
        self.secret_manager.deploy()
        self.__create_blade_ssh_secrets()

    def remove(self):
        if not self.prepared:
            raise ContextualError(
                "cannot deploy an unprepared provider, call prepare() first"
            )
        self.terragrunt.remove()

    def get_virtual_blades(self):
        return VirtualBlades(self.common)

    def get_blade_interconnects(self):
        return BladeInterconnects(self.common)

    def get_secrets(self):
        return Secrets(self.secret_manager)

    def get_site_config(self):
        """Retrieve the SiteConfig API object from the Provider.

        """
        return SiteConfig(self.common)
