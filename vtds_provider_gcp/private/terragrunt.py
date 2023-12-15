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
"""Private layer code to set up and use the Terragrunt / Terraform
configuration and control tree for deployment of a platform consisting
of Virtual Blades and Blade Interconnects (along with all of the
supporting elements of a GCP project) on a GCP cloud provider.

"""
# pylint: disable=consider-using-f-string
import shutil
import yaml
from vtds_base import ContextualError

from . import TERRAGRUNT_DIR


class Terragrunt:
    """A class that provides the locus of managing and using the
    Terragrunt / Terraform definition of a GCP provided platform.

    """
    def __init__(self, build_dir):
        """Constructor

        """
        self.build_dir = build_dir

    # pylint: disable=unused-argument
    def initialize(self, config):
        """Initialize the Terragrunt / Terraform control structures in
        the 'build' direcntory of the provider plug-in tree so we have
        the static content and are ready to absorb dynamic
        content. The 'config' argument provides the provider layer
        configuration to use.

        """
        src = "%s/framework" % (TERRAGRUNT_DIR)
        dst = "terragrunt"
        self.add_subtree(src, dst)

    def template_path(self, sub_path):
        """Given a sub-path in the Terragrunt templates tree, return a
        full path to that location.

        """
        return "%s/templates/%s" % (TERRAGRUNT_DIR, sub_path)

    def build_path(self, sub_path):
        """Given a sub-path to a file or directory within the provider
        layer build tree, return the absolute path.

        """
        return "%s/%s" % (self.build_dir, sub_path)

    def add_subtree(self, src, dst):
        """Copy a sub-tree into the 'build' tree in the provider
        plug-in directory.  The 'src' argument is a path to the source
        directory that is resolvable from the working directory of the
        caller. The 'dst' argument is a sub-tree path within the
        Provider layer's 'build' directory. Returns the path to the
        top of the added tree.

        """
        real_dst = self.build_path(dst)
        try:
            shutil.copytree(
                src=src,
                dst=real_dst,
                symlinks=False,
                ignore=None,
                dirs_exist_ok=True)
        except OSError as err:
            raise ContextualError(
                "error copying tree '%s' to '%s': %s" % (
                    src, real_dst, str(err)
                )
            ) from err
        return real_dst

    def add_file(self, src, dst):
        """Add a file to the 'build' tree in the provider plug-in
        tree.  The 'src' argument is a path to the source file that is
        resolvable from the working directory of the caller. The 'dst'
        argument is a location within the Provider layer's 'build'
        directory. Returns the path to the added file.

        """
        real_dst = self.build_path(dst)
        try:
            shutil.copy(src, real_dst)
        except OSError as err:
            raise ContextualError(
                "error copying '%s' to '%s': %s" % (src, real_dst, str(err))
            ) from err
        return real_dst


class TerragruntConfig:
    """A class that manages the terragrunt configuration used to drive
    deployment of resources to construct a vTDS platform on GCP using
    a specified Terragrunt environment.

    """
    def __init__(self, terragrunt):
        """Constructor

        """
        self.terragrunt_env = terragrunt

    def initialize(self, config):
        """Given the provider configuration data structure, Populate a
        Terragrunt / Terraform configuration in the 'build' tree of
        the provider plug-in tree.

        """
        # Add the 'provider' layer back to the config so that the
        # vtds.yaml has a config that parallels the full-stack
        # configuration from which it was taken.
        provider_config = {'provider': config}

        # Write out the vtds.yaml that results from the fully resolved
        # configuration.
        config_path = self.terragrunt_env.build_path("terragrunt/vtds.yaml")
        try:
            with open(config_path, 'w', encoding="UTF-8") as config_file:
                yaml.dump(provider_config, config_file)
        except OSError as err:
            raise ContextualError(
                "cannot install config file '%s': %s" % (config_path, str(err))
            ) from err
