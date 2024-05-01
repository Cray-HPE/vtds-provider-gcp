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
"""Private layer implementation module for the GCP provider.

"""
from os.path import dirname
from os import makedirs
from shutil import rmtree
from yaml import (
    YAMLError,
    safe_load,
    safe_dump
)

from vtds_base import (
    ContextualError,
    expand_inheritance,
    run,
    log_paths
)

# Import private classes
from .terragrunt import (
    Terragrunt,
    TerragruntConfig
)
from .virtual_blade import VirtualBlade
from .blade_interconnect import BladeInterconnect
from .api_objects import (
    PrivateVirtualBlades,
    PrivateBladeInterconnects,
    PrivateSecrets
)
from .common import Common
from .secret_manager import SecretManager


class PrivateProvider:
    """PrivateProvider class, implements the GCP provider layer
    accessed through the python Provider API.

    """
    def __init__(self, stack, config, build_dir):
        """Constructor, stash the root of the provider tree and the
        digested and finalized provider configuration provided by the
        caller that will drive all activities at all layers.

        """
        self.common = Common(config, build_dir)
        self.terragrunt = Terragrunt(self.common)
        self.terragrunt_config = TerragruntConfig(self.common, self.terragrunt)
        self.secret_manager = SecretManager(self.common)
        self.stack = stack
        self.prepared = False

    def __populate_blade_ssh_secret(self, secret_name):
        """Set up an SSH key pair and store it in the named secret.

        """
        pub_key, priv_key = self.common.ssh_key_paths(secret_name, True)
        ssh_dir = dirname(priv_key)

        # Make sure there is a fresh empty directory in place for the keys.
        rmtree(ssh_dir, ignore_errors=True)
        makedirs(ssh_dir, mode=0o700, exist_ok=True)

        # Make the keys.
        run(
            ['ssh-keygen', '-q', '-N', '', '-t', 'rsa', '-f', priv_key],
            log_paths(self.common.build_dir(), "make-ssh-key-%s" % secret_name)
        )

        # Stash the keys in the secret
        with open(priv_key, 'r', encoding='UTF-8') as private, \
             open(pub_key, 'r', encoding='UTF-8') as public:
            keys = {
                'private': private.read(),
                'public': public.read(),
            }
        secret = safe_dump(keys)
        self.secret_manager.store(secret_name, secret)

    def __authorize_blade_ssh_secret(self, secret_name):
        """For all blades using the specified secret as their SSH key,
        add the public key to the 'root' '.ssh/authorized_keys'
        contents.

        """
        data = self.secret_manager.read(secret_name)
        if data is None:
            raise ContextualError(
                "SSH key for secret '%s' is not yet populated" % secret_name
            )
        try:
            public_key = safe_load(data)['public']
        except KeyError as err:
            raise ContextualError(
                "data in SSH keys secret '%s' does not contain public key "
                "field (data not shown to protect secret)" % secret_name
            ) from err
        except YAMLError as err:
            raise ContextualError(
                "data in SSH keys secret '%s' is not parsable YAML "
                "(data and error not shown to protect secret)" % secret_name
            ) from err
        virtual_blades = self.get_virtual_blades()
        blades = [
            (blade_type, instance)
            for blade_type in virtual_blades.blade_types()
            if virtual_blades.blade_ssh_key_secret(blade_type) == secret_name
            for instance in range(0, virtual_blades.blade_count(blade_type))
        ]
        project_id = self.common.get_project_id()
        zone = self.common.get_zone()
        for blade_type, instance in blades:
            # Make sure SSH (port 22) is running on the remote
            # blade. This operation happens early in startup, so it is
            # necessary to let the blade boot and become ready. A side
            # effect of connect_blade() is that it waits until it can
            # establish a connection through the IAP connection before
            # returning, so this is a good way to achive that ready
            # wait.
            virtual_blades.connect_blade(22, blade_type, instance)
            # Append the public key to 'authorized_keys'
            hostname = virtual_blades.blade_hostname(blade_type, instance)
            run(
                [
                    'gcloud', 'compute', 'ssh', '--tunnel-through-iap',
                    '--project=%s' % project_id, '--zone=%s' % zone,
                    'root@%s' % hostname, '--',
                    'cat >> /root/.ssh/authorized_keys'
                ],
                log_paths(
                    self.common.build_dir(),
                    "authorize-%s-on-%s" % (secret_name, hostname)
                ),
                input=public_key
            )

    def __setup_blade_ssh_secrets(self):
        """For each unique secret used by a Virtual Blade type
        generate an SSH key pair (in the build tree for temporary
        storage) and store that key pair in the named secret. On
        return, there is an SSH key pair stored in each secret, and,
        for each secret, every blade using that secret has been set up
        to authorize the public key from that secret.

        """
        virtual_blades = self.get_virtual_blades()
        # Get all of the SSH key secret names for all blade types
        secret_names = [
            virtual_blades.blade_ssh_key_secret(blade_type)
            for blade_type in virtual_blades.blade_types()
        ]
        # Coerce the list to a set then back to a list to ensure each
        # name is unique in the final list.
        secret_names = list(set(secret_names))
        for secret_name in secret_names:
            self.__populate_blade_ssh_secret(secret_name)
            self.__authorize_blade_ssh_secret(secret_name)

    def prepare(self):
        """Prepare operation. This drives creation of the provider
        layer Terragrunt configuration and Terragrunt / Terraform
        control tree used to deploy the GCP resources that will form
        the foundation of a platform for the vTDS.

        """
        self.terragrunt.initialize()
        blade_types = self.common.get('virtual_blades', None)
        if blade_types is None:
            raise ContextualError(
                "no virtual blade types found in vTDS provider configuration"
            )
        for key in blade_types:
            # Expand the inheritance tree for the blade type and put
            # the expanded result back into the configuration. That
            # way, when we write out the configuration we have the
            # full expansion there.
            if blade_types[key].get('pure_base_class', False):
                # Skip inheritance and installation for pure base
                # classes since they have no parents, and they aren't
                # used for deployment.
                continue
            blade_config = expand_inheritance(blade_types, key)
            virtual_blade = VirtualBlade(self.terragrunt)
            blade_config = virtual_blade.initialize(key, blade_config)
            blade_types[key] = blade_config
        interconnect_types = self.common.get('blade_interconnects', None)
        if interconnect_types is None:
            raise ContextualError(
                "no blade interconnect types found in vTDS provider "
                "configuration"
            )
        for key in interconnect_types:
            if interconnect_types[key].get('pure_base_class', False):
                # Skip inheritance and installation for pure base
                # classes since they have no parents, and they aren't
                # used for deployment.
                continue
            interconnect_config = expand_inheritance(interconnect_types, key)
            blade_interconnect = BladeInterconnect(self.terragrunt)
            interconnect_config = blade_interconnect.initialize(
                key, interconnect_config
            )
            interconnect_types[key] = interconnect_config
        # Now that we have fully expanded all of the inheritance and
        # set up the terragrunt controls for everything that is going
        # to get them, set up the terragrunt configuration.
        self.terragrunt_config.initialize()

        # All done with the preparations: make a note that we have
        # done them and return.
        self.prepared = True

    def validate(self):
        """Run the terragrunt plan operation on a prepared GCP
        provider layer to make sure that the configuration produces a
        working result.

        """
        if not self.prepared:
            raise ContextualError(
                "cannot validate an unprepared provider, call prepare() first"
            )
        self.terragrunt.validate()

    def deploy(self):
        """Deploy operation. This drives the application of the
        terraform / terragrunt to create the provider layer
        resources. It can only be called after the prepare operation
        (prepare()) completes.

        """
        if not self.prepared:
            raise ContextualError(
                "cannot deploy an unprepared provider, call prepare() first"
            )
        self.terragrunt.deploy()
        self.secret_manager.deploy()
        self.__setup_blade_ssh_secrets()

    def shutdown(self, virtual_blade_names):
        """Shutdown operation. This will shut down (power off) the
        specified virtual blades, or, if none are specified, all
        virtual blades, in the provider, leaving them provisioned.

        """
        # pylint: disable=fixme
        # XXX - implementation needed here!!!!

    def startup(self, virtual_blade_names):
        """Startup operation. This will start up (power on) the
        specified virtual blades, or, if none are specified, all
        virtual blades, in the provider as long as they are
        provisioned.

        """
        # pylint: disable=fixme
        # XXX - implementation needed here!!!!

    def dismantle(self):
        """Dismantle operation. This will de-provision all virtual
        blades in the provider.

        """
        if not self.prepared:
            raise ContextualError(
                "cannot deploy an unprepared provider, call prepare() first"
            )
        self.terragrunt.dismantle()

    def restore(self):
        """Restore operation. This will re-provision all virtual
        blades in the provider removed by the 'dismantle' operation.

        """
        if not self.prepared:
            raise ContextualError(
                "cannot deploy an unprepared provider, call prepare() first"
            )
        self.terragrunt.restore()

    def remove(self):
        """Remove operation. This will remove all resources
        provisioned for the provider layer.

        """
        if not self.prepared:
            raise ContextualError(
                "cannot deploy an unprepared provider, call prepare() first"
            )
        self.terragrunt.remove()

    def get_virtual_blades(self):
        """Return a the VirtualBlades object containing all of the
        available non-pure-base-class Virtual Blades.

        """
        return PrivateVirtualBlades(self.common)

    def get_blade_interconnects(self):
        """Return a BladeInterconnects object containing all the
        available non-pure-base-class Blade Interconnects.

        """
        return PrivateBladeInterconnects(self.common)

    def get_secrets(self):
        """Return a Secrets API object that provides access to all
        available secrets.

        """
        return PrivateSecrets(self.secret_manager)
