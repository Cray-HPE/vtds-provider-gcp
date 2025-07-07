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
"""Private layer code to set up and use the Terragrunt / Terraform
configuration and control tree for deployment of a platform consisting
of Virtual Blades and Blade Interconnects (along with all of the
supporting elements of a GCP project) on a GCP cloud provider.

"""
# pylint: disable=consider-using-f-string
from shutil import (
    copy,
    copytree,
    rmtree
)
from os.path import join as path_join
from subprocess import Popen, TimeoutExpired, PIPE
import yaml
from vtds_base import (
    ContextualError,
    run,
    log_paths,
    logfile,
    write_out
)

from . import TERRAGRUNT_DIR


class VersionManager:
    """Base class for terraform and terragrunt version managers which
    contains the common data and functions used by both.

    """
    def __init__(self, common, mgr_cmd, mgr_subsystem, dummy_version):
        """Constructor

        """
        self.mgr_cmd = mgr_cmd
        self.mgr_subsystem = mgr_subsystem
        self.versions_installed = []
        self.version_inuse = None
        self.dummy_version = dummy_version
        self.common = common
        self.__init_version_info()

    def __init_version_info(self):
        """Initialize the list of installed versions and the currently
        used version by querying the version manager.

        """
        # Unfortunately, 'tfenv list' fails if no versions of
        # terraform are installed, so run '<cmd> install <dummy_version>'
        # to make sure something is installed.
        logs = log_paths(
            self.common.build_dir(),
            "prime-%s-version-manager" % (self.mgr_subsystem)
        )
        run([self.mgr_cmd, 'install', self.dummy_version], logs)

        # This builds both stdout and stderr log paths to pass to
        # run(), but we are going to override the stdout path by using
        # stdout=PIPE in the run call itself, so the output will be
        # captured in the result.
        logs = log_paths(
            self.common.build_dir(),
            "init-%s-version-manager" % (self.mgr_subsystem)
        )
        output = run([self.mgr_cmd, 'list'], logs, stdout=PIPE).stdout
        versions = output.split('\n')[:-1]
        # Find the version that starts with '* ' and make that the
        # version in use.
        inuse = [
            version.split(' ')[1]
            for version in versions
            if version[:2] == '* '
        ]
        self.version_inuse = inuse[0] if inuse else None
        # Grab all of the version and make those the versions
        # installed.
        self.versions_installed = [
            version.split(' ')[1] if version[0] == '*'
            else version.split(' ')[2]
            for version in versions
        ] if versions else []

    def __using_version(self, version):
        """Check whether the specified version is currently in use...

        """
        return version == self.version_inuse

    def __have_version(self, version):
        """Check whether the specified version is currently installed...

        """
        return version in self.versions_installed

    def __install_version(self, version):
        """Install the requested version

        """
        logs = log_paths(
            self.common.build_dir(),
            "install-%s-version-%s" % (self.mgr_subsystem, version)
        )
        run([self.mgr_cmd, 'install', version], logs)

    def __use_version(self, version):
        """Put the requested version into use

        """
        logs = log_paths(
            self.common.build_dir(),
            "use-%s-version-%s" % (self.mgr_subsystem, version)
        )
        run([self.mgr_cmd, 'use', version], logs)
        self.version_inuse = version

    def use_version(self, version):
        """Switch to using the specified version, installing it as
        needed.

        """
        if not self.__have_version(version):
            self.__install_version(version)
        if not self.__using_version(version):
            self.__use_version(version)


class TFEnv(VersionManager):
    """A class that provides access to the Terraform Version Manager
    with cached knowledge of what is installed and what is in use.

    """
    def __init__(self, common):
        """Constructor

        """
        dummy_version = (
            common
            .get("terragrunt", {})
            .get('terraform_dummy_version', "latest")
        )
        VersionManager.__init__(
            self, common, "tfenv", "terraform", dummy_version
        )


class TGEnv(VersionManager):
    """A class that provides access to the Terragrunt Version Manager
    with cached knowledge of what is installed and what is in use.

    """
    def __init__(self, common):
        """Constructor

        """
        dummy_version = (
            common
            .get("terragrunt", {})
            .get('terragrunt_dummy_version', "latest")
        )
        VersionManager.__init__(
            self, common, "tgenv", "terragrunt", dummy_version
        )


class Terragrunt:
    """A class that provides the locus of managing and using the
    Terragrunt / Terraform definition of a GCP provided platform.

    """
    def __init__(self, common):
        """Constructor

        """
        self.common = common
        self.tg_cmd = "terragrunt"

    # pylint: disable=unused-argument
    def initialize(self):
        """Initialize the Terragrunt / Terraform control structures in
        the 'build' directory of the provider plug-in tree so we have
        the static content and are ready to absorb dynamic
        content.

        """
        # Setup terraform and terragrunt versions to use based on the
        # config
        tf_version = (
            self.common.get("terragrunt", {})
            .get("terraform_version", None)
        )
        if tf_version is None:
            raise ContextualError(
                "provider.terraform.terraform_version not available"
            )
        tg_version = (
            self.common.get("terragrunt", {})
            .get("terragrunt_version", None)
        )
        if tg_version is None:
            raise ContextualError(
                "provider.terragrunt.terraform_version not available"
            )
        tf_env = TFEnv(self.common)
        tf_env.use_version(tf_version)
        tg_env = TGEnv(self.common)
        tg_env.use_version(tg_version)

        # Figure out the terragrunt command to use from the
        # configuration.
        self.tg_cmd = self.common.get("commands", {}).get(
            'terragrunt', "terragrunt"
        )

        # Clear out any old terragrunt tree from the build
        # directory. There is potential cached state that can become
        # corrupted and cause spurious failures.
        rmtree(self.build_path("terragrunt"), ignore_errors=True)

        # Put the initial structure of the terragrunt tree in place in
        # the build directory.
        src = path_join(TERRAGRUNT_DIR, "framework")
        dst = "terragrunt"
        self.add_subtree(src, dst)

    def __run(self, subdir, operation, tag, timeout=None):
        """Run a terragrunt command in the specified sub-directory of
        the build tree capturing the output in separate output and
        error logs for later analysis.

        """
        directory = path_join(self.common.build_dir(), subdir)
        out_path, err_path = log_paths(
            self.common.build_dir(),
            "terragrunt_%s[%s]" % (operation, tag)
        )
        with logfile(out_path) as out, logfile(err_path) as err:
            try:
                write_out(
                    "running terragrunt '%s'[%s] in "
                    "'%s' " % (operation, tag, directory)
                )
                with Popen(
                    [
                        self.tg_cmd,
                        'run-all',
                        operation,
                        '--terragrunt-non-interactive',
                        '--terragrunt-provider-cache'
                    ],
                    stdout=out, stderr=err, cwd=directory
                ) as terragrunt:
                    time = 0
                    signaled = False
                    while True:
                        try:
                            exitval = terragrunt.wait(timeout=5)
                        except TimeoutExpired:
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
                                    "terragrunt '%s' operation timed out "
                                    "and did not terminate as expected "
                                    "after %d seconds" % (operation, time),
                                    out_path, err_path
                                )
                            write_out('.')
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
                    "timed out and was killed"
                )
                raise ContextualError(
                    fmt % operation,
                    out_path,
                    err_path
                )

    def validate(self):
        """Run a `terragrunt plan` operation across the Terragrunt /
        Terraform control structures in the build directory to verify
        that it all should work.

        """
        self.__run("terragrunt", "plan", "validate")

    def deploy(self):
        """Run a `terragrunt apply operation across the Terragrunt
        / Terraform control structures in the build directory to
        create all resources associated with the provider layer.

        """
        self.__run("terragrunt", "apply", "deploy")

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
        self.__run(path, "destroy", "dismantle")

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
        self.__run(path, "apply", "restore")

    def remove(self):
        """Run a `terragrunt destroy` operation across the Terragrunt
        / Terraform control structures in the build directory to
        remove all resources associated with the provider layer.

        """
        self.__run("terragrunt", "destroy", "remove")

    def template_path(self, sub_path):
        """Given a sub-path in the Terragrunt templates tree, return a
        full path to that location.

        """
        return path_join(
            TERRAGRUNT_DIR, "templates", sub_path
        )

    def build_path(self, sub_path):
        """Given a sub-path to a file or directory within the provider
        layer build tree, return the absolute path.

        """
        return path_join(self.common.build_dir(), sub_path)

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
            copytree(
                src=src,
                dst=real_dst,
                symlinks=False,
                ignore=None,
                dirs_exist_ok=True
            )
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
            copy(src, real_dst)
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
    def __init__(self, common, terragrunt):
        """Constructor

        """
        self.common = common
        self.terragrunt_env = terragrunt

    def initialize(self):
        """Given the provider configuration data structure, Populate a
        Terragrunt / Terraform configuration in the 'build' tree of
        the provider plug-in tree.

        """
        # Add the 'provider' layer back to the config so that the
        # vtds.yaml has a config that parallels the full-stack
        # configuration from which it was taken.
        provider_config = {'provider': self.common.get_config()}

        # Write out the vtds.yaml that results from the fully resolved
        # configuration.
        config_path = self.terragrunt_env.build_path(
            path_join("terragrunt", "vtds.yaml")
        )
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
