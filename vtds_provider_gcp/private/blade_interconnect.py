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
"""Private layer code to compose and work with dynamically created
Terragrunt / Terraform control structures that define the resources
associated with classes of vTDS Blade Interconnects for the purpose of
deploying Blade Interconnects implemented as GCP networks and the
associated GCP Virtual Private Clouds (VPCs) into a platform
implemented as a GCP project.

"""
from vtds_base import (
    ContextualError,
    render_templated_tree
)


class BladeInterconnect:
    """Class representing a single blade interconnect type as defined
    in the vTDS configuration and implemented in the vTDS Terragrunt
    configuration / constrol struture.

    """
    def __init__(self, terragrunt):
        """Constructor

        """
        self.terragrunt = terragrunt

    def initialize(self, key, interconnect_config):
        """Using the name of the blade interconnect configuration
        found in 'key' and the blade interconnect configuration found
        in 'interconnect_config' construct and inject a Blade
        Interconnect type into the Terragrunt control tree managed by
        'terragrunt'.

        """
        # Locate the top of the template for blade_interconnects
        template_dir = self.terragrunt.template_path(
            "system/platform/blade-interconnect"
        )

        # Copy the templates into the build tree before rendering them.
        build_dir = self.terragrunt.add_subtree(
            template_dir,
            "terragrunt/system/platform/blade-interconnect/%s" % (key)
        )

        # Compose the data to be used in rendering the templated files.
        try:
            render_data = {
                'network_name': interconnect_config['network_name'],
                'config_path': "provider.blade_interconnects.%s" % key,
            }
        except KeyError as err:
            raise ContextualError(
                "missing config in the Blade Interconnect class '%s': %s" % (
                    key, str(err)
                )
            ) from err

        # Render the templated files in the build tree.
        render_templated_tree(["*.hcl", "*.yaml"], render_data, build_dir)
