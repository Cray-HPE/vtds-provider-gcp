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
import re
from subprocess import PIPE
from vtds_base import (
    ContextualError,
    log_paths,
    run
)


class SecretManager:
    """Class providing operations for creating and removing secrets as
    needed from a the GCP secret manager.

    """
    def __init__(self, common):
        """Constructor

        """
        self.common = common
        secrets = self.common.get('secrets', {})
        try:
            self.secrets = {
                secret['name']: secret for _, secret in secrets.items()
            }
        except KeyError as err:
            # No harm compiling a list since we are going to error out
            # anyway. This will provide a more useful error.
            missing_names = [
                key for key, secret in secrets.items() if 'name' not in secret
            ]
            raise ContextualError(
                "configuration error: the following secrets (by key) in the "
                "config do not define a 'name' field: %s" % str(missing_names)
            ) from err
        self.cache = {}

    @staticmethod
    def __expand_kvs(secret_name, dict_name, dictionary):
        """Class private: expand a dictionary of key-value pairs into
        a string of the form: '<key>=<value>[,<key>=<value>][,...]'
        for use in 'gcloud' commands. Neither a key nor a value may
        contain whitespace.

        """
        valid = re.compile(r"^[^\s]*$")
        result = ""
        for key, value in dictionary.items():
            if not valid.match(key) or not valid.match(value):
                raise ContextualError(
                    "secret '%s' has whitespace in '%s' entry ['%s':'%s']" % (
                        secret_name, dict_name, key, value
                    )
                )
            result += "," if result else ""
            result += "%s=%s" % (key, value)
        return result

    def __create_secret(self, secret):
        """Class private: register the specified secret in the GCP
        Secret Manager.

        """
        # I didn't get here if any of the secrets don't have names, so
        # no need to protect this reference.
        name = secret['name']
        project_id = "--project=%s" % self.common.get_project_id()
        cmd = ['gcloud', 'secrets', 'create', name, project_id]
        # Set up the option to add labels if there are any needed
        labels = (
            "--labels=%s" % self.__expand_kvs(name, "labels", secret['labels'])
            if secret.get('labels', None) else
            ""
        )
        if labels:
            cmd.append(labels)
        # Set up the option to add annotations if there are any needed
        annotations = (
            "--set-annotations=%s" % self.__expand_kvs(
                name, "annotations", secret['annotations']
            )
            if secret.get('annotations', None) else
            ""
        )
        if annotations:
            cmd.append(annotations)
        logname = "create-secret-%s" % name
        run(cmd, log_paths(self.common.build_dir(), logname))

    def __remove_secret(self, secret):
        """Class private: register the specified secret in the GCP
        Secret Manager.

        """
        # I didn't get here if any of the secrets don't have names, so
        # no need to protect this reference.
        name = secret['name']
        project_id = "--project=%s" % self.common.get_project_id()
        logname = "remove-secret-%s" % name
        run(
            ['gcloud', 'secrets', 'delete', name, project_id, '--quiet'],
            log_paths(self.common.build_dir(), logname)
        )

    def __store_secret(self, secret, data):
        """Store the specified data in a secret (actually a secret
        version in GCP).

        """
        # I didn't get here if any of the secrets don't have names, so
        # no need to protect this reference.
        name = secret['name']
        project_id = "--project=%s" % self.common.get_project_id()
        logname = "store-secret-%s" % name
        run(
            [
                'gcloud', 'secrets', 'versions', 'add', project_id,
                '--data-file=-', name,
            ],
            log_paths(self.common.build_dir(), logname),
            input=data
        )
        # Keep a write-through cache of secrets that have been stored
        # to expedite retrieving them in the future.
        self.cache[name] = data

    def __read_secret(self, secret):
        """Read the 'latest' version data from the specified secret
        and return it as a 'UTF-8' encoded string.

        """
        # I didn't get here if any of the secrets don't have names, so
        # no need to protect this reference.
        name = "--secret=%s" % secret['name']
        # Try reading the secret from the cache, if it doesn't work go
        # ahead and get it from GCP instead.
        try:
            return self.cache[name]
        except KeyError:
            # Not in the cache, keep looking...
            pass
        project_id = "--project=%s" % self.common.get_project_id()
        logname = "read-secret-%s" % secret['name']
        result = run(
            [
                'gcloud', 'secrets', 'versions', 'access', 'latest',
                project_id, name,
            ],
            log_paths(self.common.build_dir(), logname),
            stdout=PIPE
        )
        self.cache[name] = result.stdout.rstrip()
        return self.cache[name]

    def deploy(self):
        """Deploy all secrets declared by any layer during the
        'prepare' phase to the GCP Secret Manager. This creates the
        secrets as place holders for content. It is up to the users of
        the secrets to fill them with data (create versions in GCP
        parlance) by calling into the provider API for storing data in
        secrets.

        """
        for _, secret in self.secrets.items():
            self.__create_secret(secret)

    def remove(self):
        """Remove all secrets declared by any layer during the
        'prepare' phase from the GCP Secret Manager.

        """
        for _, secret in self.secrets.items():
            self.__remove_secret(secret)

    def store(self, name, value):
        """Store a value in the named secret. The value should be a
        UTF-8 encoded string.

        """
        secret = self.secrets.get(name, None)
        if secret is None:
            raise ContextualError(
                "attempt to store value in unknown secret '%s'" % name
            )
        self.__store_secret(secret, value)

    def read(self, name):
        """Read the value of the named secret.

        """
        secret = self.secrets.get(name, None)
        if secret is None:
            raise ContextualError(
                "attempt to store value in unknown secret '%s'" % name
            )
        return self.__read_secret(secret)
