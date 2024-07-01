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
associated with classes of vTDS Virtual Blades for the purpose of
deploying Virtual Blades implemented as GCP Compute Instances into a
platform implemented as a GCP project.

"""
from os.path import join as path_join
from vtds_base import (
    ContextualError,
    render_templated_tree
)


class VirtualBlade:
    """Class representing a single virtual blade type as defined in
    the vTDS configuration and implemented in the vTDS Terragrunt
    configuration / control struture.

    """
    def __init__(self, terragrunt):
        """Constructor

        """
        self.terragrunt = terragrunt

    def initialize(self, key, blade_config):
        """Using the name of the virtual blade class found in 'key'
        and the configuration found in 'blade_config' construct and
        inject a Virtual Blade type into the Terragrunt control tree
        managed by 'terragrunt'.

        """
        # Locate the top of the template for blade_interconnects
        template_dir = self.terragrunt.template_path(
            path_join("system", "platform", "virtual-blade")
        )

        # Copy the templates into the build tree before rendering them.
        build_dir = self.terragrunt.add_subtree(
            template_dir,
            path_join("terragrunt", "system", "platform", "virtual-blade", key)
        )

        # Compose the data to be used in rendering the templated files.
        try:
            interconnect = blade_config['blade_interconnect']
            boot_disk = blade_config.get('vm', {})['boot_disk']
            access_config = blade_config.get('access_config', [])
        except KeyError as err:
            raise ContextualError(
                "missing config in the Virtual Blade class '%s': %s" % (
                    key, str(err)
                )
            ) from err
        try:
            render_data = {
                'blade_class': key,
                'interconnect_name': interconnect['subnetwork'],
                'config_path': "provider.virtual_blades.%s" % key,
                'source_image_private': boot_disk['source_image_private'],
                'access_config': access_config,
            }
        except KeyError as err:
            raise ContextualError(
                "missing blade_interconnect or boot_disk config in the Virtual "
                "Blade class '%s': %s" % (
                    key, str(err)
                )
            ) from err

        # Render the templated files in the build tree.
        render_templated_tree(["*.hcl", "*.yaml"], render_data, build_dir)
        return blade_config

    def deploy(self):
        """Placeholder for a deploy operation...

        """
