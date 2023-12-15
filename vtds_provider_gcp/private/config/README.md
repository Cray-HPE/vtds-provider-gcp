# GCP Provider Layer Base Configuration

Base configuration supplied by the GCP implementation of the Provider
Layer for vTDS.

## Overview

The file `config.yaml` in this directory contains the settings that are
used to configure the vTDS creation using the GCP provider at the
provider layer. Most of the settings found here will work unchanged on
most vTDS deployments, but all of them can be overridden as needed in a
system configuration overlay provided by a user.

The configuration provided here is most of what you need to create a
GCP project with an application layer specified number of Virtual
Blades (GCP Instances) interconnected by a single Blade
Interconnect. Each Virtual Blade will be running Ubuntu Linux and will
be assigned a default layer specified IP address by GCP on the Blade
Interconnect.

The pieces that are configurable in the GCP provider are:

* Organization settings
* Project creation parameters
* Virtual Blade Classes
* Blade Interconnect Classes
* Provider Secrets

These are all described below.

### Organization Configuration

To create a vTDS system you must first put some infrastructure into
place in the form of a Google Billing Account and a vTDS seed
project. The billing account allows you to access and create GCP
resources for use in your vTDS systems. One billing account is
needed per Google customer that wants to use GCP hosted vTDS
systems. For more information on creating and managing your billing
account see
[Manage Your Billing Account](https://cloud.google.com/billing/docs/how-to/manage-billing-account)
in the Google documentation.

The vTDS seed project is a GCP project with only storage and Google
Secret resources associated with it. The storage in the seed project
provides a place for Terragrunt / Terraform to store vTDS project state
in a way that can outlive the vTDS project itself. This allows vTDS to,
for example, re-use the same vTDS project identifier when rebuilding a
project from scratch.

The required fields in the organization configuration are mostly derived
from your Billing Account and are identified in `config.yaml` by
comments.

### Project Configuration

Project configuration primarily contains the settings used to drive the
creation of a project through Terragrunt / Terraform. The default
settings here are comprehensive for the Terraform GCP Core Project
Factory except where a setting is derived from some other part of the
configuration, in which case that is noted by a comment. The values
chosen should work for most vTDS projects, but you are welcome to
override any setting in a system config overlay.

For more information on the project cofiguration settings, see
[the Terraform core_project_factory variables definition](https://github.com/terraform-google-modules/terraform-google-project-factory/blob/cb3b31731dbef844632f4fd4df7fa6d3c61cad74/modules/core_project_factory/variables.tf)

### Virtual Blade Classes

Virtual Blades are implemented by the GCP provider layer as GCP
instances. The number and kind of Virtual Blades is defined at layers
above the provider layer, but the configuration required to create a
given class of Virtual Blade is defined in the provider
configuration. Virtual Blade Classes provide that configuration
template. Each Virtual Blade Class is identified by its name. The
existence of the name is part of the API and can be referenced at other
layers of the system configuration. The base configuration provides a
Virtual Blade Class named `base` that contains a basic set of settings
that should work well, with minor adjustments, to create Virtual Blades
for any given vTDS. The content of `base` can be modified as needed in
your system configuration overlays without re-defining the whole thing.

To simplify system configuration overlays, Virtual Blade Classes can
inherit from other Virtual Blade Classes. Adjusting `base` in your
system configuration overlay and then using it as a parent class for
other Virtual Blade Classes you want to define makes it easy to tweak
only a few parameters in your system configuration overlay and set up a
rich set of Virtual Blade Classes of your own.

The unmodified `base` Virtual Blade Class will create small GCP
instances running Ubuntu Linux with nested virtualization and ip
forwarding enabled and connected to a single Blade Interconnect.

Note that Virtual Blade Classes are used to fill out Terragrunt
control files that start as a Jinja templates. Various template
variables are derived from the system configuration and replaced in
the generated Terragrunt control files to refer to the Virtual Blade
Class itself, the configuration of that Virtual Blade Class in the
system configuration and the GCP resources used by that Virtual Blade
class.

For more information on Virtual Blade (i.e. GCP instance) settings see
the following:

* [the Terraform GCP Instance Template module](https://github.com/Cray-HPE/terraform-google-vm/blob/057bc0c5c73f5e65484764dacc1e30f07f921d2b/modules/instance_template/variables.tf)
* [the Terraform GCP Compute Instance module](https://github.com/Cray-HPE/terraform-google-vm/blob/057bc0c5c73f5e65484764dacc1e30f07f921d2b/modules/compute_instance/variables.tf)
* [the Terraform GCP Service Accounts module](https://github.com/terraform-google-modules/terraform-google-service-accounts/blob/53a7bc5a84b0b8df0a2d342a2f5a42c6d9045514/modules/key-distributor/variables.tf)
* [the Terraform GCP Project IAM module](https://github.com/terraform-google-modules/terraform-google-iam/blob/991c5716b2c4f848e1e38bbe81d43d636faf1341/modules/projects_iam/variables.tf)

### Blade Interconnect Classes

Blade Interconnects are constructed as subnets within GCP private VPCs
in the vTDS GCP project. Specific Blade Interconnect instances are set
up in layers above the provider layer, but Blade Interconnect Classes
provide the template from which the GCP provider layer constructs
configuration to drive the Terragrunt creation of the VPC, routes,
firewall, and subnet for each Blade Interconnect in the vTDS system.

Similarly to Virtual Blade Classes, Blade Interconnect Classes can
inherit from other Blade Interconnect Classes, and, similar to Virtual
Blade Classes, a `base` Blade Interconnect Class is defined in the base
configuration found here. By modifying and inheriting from the `base`
class a system configuration overlay can be constructed with only small
direct tweaks to `base` and then define any number of system specific
Blade Interconnect Classes with minimal configuration content.

It is worth noting that Blade Interconnect Classes are used to create
Terragrunt control files from Jinja templates in which the template
variables are used to refer to the Blade Interconnect class itself, as
well as other resources used to construct the Blade Interconnect.

The `base` Blade Interconnect Class, unmodified, can be used to create
simle networks that connect Virtual Blades in the base vTDS
configuration.

For more information on settings in Blade Interconnect Classes, see the
following:

* [the Terraform GCP VPC module](https://github.com/terraform-google-modules/terraform-google-network/blob/4fd83005a98a293c2b0f5e774d1e680c80b8e70e/modules/vpc/variables.tf)
* [the Terraform GCP VPC Firewall Rules module](https://github.com/terraform-google-modules/terraform-google-network/blob/4fd83005a98a293c2b0f5e774d1e680c80b8e70e/modules/firewall-rules/variables.tf)
* [the Terraform GCP VPC Routes module](https://github.com/terraform-google-modules/terraform-google-network/blob/d80abef8778aacc3e396bdf91a85b0a0407e4c83/modules/routes/variables.tf)
* [the Terraform GCP Subnets module](https://github.com/terraform-google-modules/terraform-google-network/blob/4fd83005a98a293c2b0f5e774d1e680c80b8e70e/modules/subnets/variables.tf)

### Provider Secrets

In any system there will be information like initial passwords or other
credentials that are needed to make the system work but cannot be made
public or checked into a configuration file under source control. For
this, vTDS uses provider supplied secrets. In GCP secrets are kept as
Google Secrets and are set up separately from the system configuration
similarly to how the Billing Account and Seed Project are set up. They
may be stored within the vTDS project itself, within the Seed Project or
elsewhere in Google. If they are stored in the vTDS project itself, the
assumption is that their content is composed by the build process and
placed in the secret for future use. This is because the vTDS project is
subject to deletion or creation, so cannot be pre-populated with
secrets. Regardless of where the secrets are kept, what matters is that
the service account(s) or admin user(s) or group(s) used to build the
vTDS system has access to them and that the general public does not.

The provider secrets configuration tells the system where to look for
secrets so that the provider layer API can retrieve the secrets by
name. It does not specify the content of the secrets, only their
location.

In GCP, a secret is identified by two things:

* the project to which it belongs
* the name of the secret

In general, at the provider layer each secret is written or read as
raw data and left to the layer that created it or uses it for
interpretation.
