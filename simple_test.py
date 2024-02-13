# This is a very simple test that runs the GCP provider through
# a provider layer lifecycle using the test overlay configuration.
#
# Run it using:
#
#    $ python3 ./simple_test from this directory
#
# You will need to run:
#
#    $ pip install -e .
#
# In this directory to get the dependencies in place and install the
# provider layer this uses.
"""Simplified driver for quick manual testing of the GCP provider
layer.

"""

from vtds_base import (
    merge_configs,
    VTDSStack
)

# Create a vTDS stack with the provider and platform layers in it.
stack = VTDSStack(
    "vtds_application_ubuntu",
    "vtds_cluster_kvm",
    "vtds_platform_ubuntu",
    "vtds_provider_gcp"
)

# Get the test configuration from the stack.
config = stack.get_test_config()

# Initialize the FullStack item to tell all of the layers in it where
# the scratch directory for building is (in this case
# '/tmp/vtds_build') then get the provider API object from the stack.
stack.initialize(config, "/tmp/vtds_build")
provider_api = stack.get_provider_api()

# Run the 'prepare' phase on the vTDS stack. Currently there is only a
# provider, so this will only prepare the provider layer..
print("Preparing the vTDS for deployment")
stack.prepare()

# Run the 'validate' phase on the vTDS stack. Again, only provider for now.
print("Validating the vTDS...")
stack.validate()

# Run the 'deploy' phase on the vTDS stack. Again, only provider for now.
print("Deploying the vTDS...")
stack.deploy()

# For grins, tear down all the virtual blades in the provider layer...
print("Dismantling provider project...")
provider_api.dismantle()

# ...and put them all back.
print("Restoring provider project...")
provider_api.restore()

# Run the remove phase on the vTDS stack. Again, only provider for now.
print("Removing the vTDS...")
stack.remove()
