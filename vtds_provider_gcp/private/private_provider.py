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

from vtds_base import (
    ContextualError,
    expand_inheritance
)

# Import private classes
from .terragrunt import (
    Terragrunt,
    TerragruntConfig
)
from .virtual_blade import VirtualBlade
from .blade_interconnect import BladeInterconnect


class PrivateProvider:
    """PrivateProvider class, implements the GCP provider layer
    accessed through the python Provider API.

    """
    def __init__(self, stack, config, build_dir):
        """Constructor, stash the root of the provider tree and the
        digested and finalized provider configuration provided by the
        caller that will drive all activities at all layers.

        """
        self.config = config
        self.terragrunt = Terragrunt(build_dir)
        self.terragrunt_config = TerragruntConfig(self.terragrunt)
        self.stack = stack
        self.prepared = False

    def prepare(self):
        """Prepare operation. This drives creation of the provider
        layer Terragrunt configuration and Terragrunt / Terraform
        control tree used to deploy the GCP resources that will form
        the foundation of a platform for the vTDS.

        """
        self.terragrunt.initialize(self.config)
        blade_types = self.config.get('virtual_blades', None)
        if blade_types is None:
            raise ContextualError(
                "no virtual blade types found in vTDS provider configuration"
            )
        for key in blade_types:
            # Expand the inheritance tree for the blade type and put
            # the expanded result back into the configuration. That
            # way, when we write out the configuration we have the
            # full expansion there.
            blade_config = expand_inheritance(blade_types, key)
            blade_types[key] = blade_config
            if blade_config.get('pure_base_class', False):
                # Skip installation of pure base classes...
                continue
            virtual_blade = VirtualBlade(self.terragrunt)
            virtual_blade.initialize(key, blade_config)
        interconnect_types = self.config.get('blade_interconnects', None)
        if interconnect_types is None:
            raise ContextualError(
                "no blade interconnect types found in vTDS provider "
                "configuration"
            )
        for key in interconnect_types:
            interconnect_config = expand_inheritance(interconnect_types, key)
            interconnect_types[key] = interconnect_config
            if interconnect_config.get('pure_base_class', False):
                # Skip installation of pure base classes...
                continue
            blade_interconnect = BladeInterconnect(self.terragrunt)
            blade_interconnect.initialize(key, interconnect_config)
        # Now that we have fully expanded all of the inheritance and
        # set up the terragrunt controls for everything that is going
        # to get them, set up the terragrunt configuration.
        self.terragrunt_config.initialize(self.config)

        # All done with the preparations: make a note that we have
        # done them and return.
        self.prepared = True

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
        # pylint: disable=fixme
        # XXX - Implementation needed here!!!!

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
        # pylint: disable=fixme
        # XXX - implementation needed here!!!!

    def remove(self):
        """Remove operation. This will remove all resources
        provisioned for the provider layer.

        """
        # pylint: disable=fixme
        # XXX - implementation needed here!!!!
