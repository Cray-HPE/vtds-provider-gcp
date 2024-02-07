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
from os.path import join as path_join
from os import makedirs
from sys import stdout
import subprocess
import yaml
from vtds_base import (
    ContextualError
)

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
        the 'build' directory of the provider plug-in tree so we have
        the static content and are ready to absorb dynamic
        content. The 'config' argument provides the provider layer
        configuration to use.

        """
        src = path_join(TERRAGRUNT_DIR, "framework")
        dst = "terragrunt"
        self.add_subtree(src, dst)

    def __run__(self, subdir, operation, tag, timeout=None):
        """Run a terragrunt command in the specified sub-directory of
        the build tree capturing the output in separate output and
        error logs for later analysis.

        """
        directory = path_join(self.build_dir, subdir)
        logs = path_join(self.build_dir, "logs")
        err_path = path_join(
            logs,
            "terragrunt_%s[%s]-err.txt" % (operation, tag))
        out_path = path_join(
            logs,
            "terragrunt_%s[%s]-out.txt" % (operation, tag))
        try:
            makedirs(logs, mode=0o755, exist_ok=True)
            with open(out_path, 'w', encoding='UTF-8') as out, \
                 open(err_path, 'w', encoding='UTF-8') as err:
                try:
                    stdout.write(
                        "running terragrunt '%s'[%s] in '%s' " % (
                            operation,
                            tag,
                            directory
                        )
                    )
                    stdout.flush()
                    with subprocess.Popen(
                        [
                            'terragrunt',
                            'run-all',
                            operation,
                            '--terragrunt-non-interactive'
                        ],
                        stdout=out,
                        stderr=err,
                        cwd=directory
                    ) as terragrunt:
                        time = 0
                        signaled = False
                        while True:
                            try:
                                exitval = terragrunt.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                time += 5
                                if timeout and time > timeout:
                                    if not signaled:
                                        # First try to terminate the process
                                        terragrunt.terminate()
                                        continue
                                    terragrunt.kill()
                                    print()
                                    # pylint: disable=raise-missing-from
                                    raise ContextualError(
                                        "terragrunt '%s' operation timed out and "
                                        "did not terminate as requested "
                                        "after %d seconds" % (operation, time),
                                        out_path,
                                        err_path
                                    )
                                stdout.write('.')
                                stdout.flush()
                                continue
                            # Didn't time out, so the wait is done.
                            break
                        print()
                except FileNotFoundError as err:
                    raise ContextualError(
                        "executing terragrunt '%s' operation failed "
                        "- %s" % (operation, str(err))
                    ) from err
                if exitval != 0:
                    fmt = (
                        "terragrunt '%s' operation failed" if not signaled
                        else "terragrunt '%s' terragrunt operation '%s' "
                        "timed out"
                    )
                    raise ContextualError(
                        fmt % operation,
                        out_path,
                        err_path
                    )
        except OSError as err:
            raise ContextualError(
                "failed to set up for terragrunt operation '%s' - %s" % (
                    operation, str(err)
                )
            ) from err

    def validate(self):
        """Run a `terragrunt plan` operation across the Terragrunt /
        Terraform control structures in the build directory to verify
        that it all should work.

        """
        self.__run__("terragrunt", "plan", "validate")

    def deploy(self):
        """Run a `terragrunt apply operation across the Terragrunt
        / Terraform control structures in the build directory to
        create all resources associated with the provider layer.

        """
        self.__run__("terragrunt", "apply", "deploy")

    def dismantle(self):
        """Run a `terragrunt destroy operation across the virtual
        blades in the Terragrunt / Terraform control structures in the
        build directory to remove virtual blades and their immediate
        supporting resources.

        """
        path = path_join(
            "terragrunt",
            "system",
            "platform",
            "virtual-blade"
        )
        self.__run__(path, "destroy", "dismantle")

    def restore(self):
        """Run a `terragrunt apply operation across the virtual blades
        in the Terragrunt / Terraform control structures in the build
        directory to create virtual blades and their supporting
        resources.

        """
        path = path_join(
            "terragrunt",
            "system",
            "platform",
            "virtual-blade"
        )
        self.__run__(path, "apply", "restore")

    def remove(self):
        """Run a `terragrunt destroy` operation across the Terragrunt
        / Terraform control structures in the build directory to
        remove all resources associated with the provider layer.

        """
        self.__run__("terragrunt", "destroy", "remove")

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
                # Make sure that we get a simple YAML file without
                # anchors and references.
                yaml.Dumper.ignore_aliases = lambda *args: True
                yaml.dump(
                    provider_config,
                    config_file,
                    default_flow_style=False
                )
        except OSError as err:
            raise ContextualError(
                "cannot install config file '%s': %s" % (config_path, str(err))
            ) from err
