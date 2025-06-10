# vtds-provider-gcp

The GCP provider layer implementation for vTDS allowing a vTDS cluster
to be built as a GCP project.

## Description

This repo provides the code and a base configuration to deploy a vTDS
cluster in a Google Cloud Platform (GCP) project within an existing
Google organization. It is intended as the GCP Provider Layer for vTDS
which is a provider and product neutral framework for building virtual
clusters to test and develop software. The Provider Layer defines the
configuration structure and software implementation required to
establish the lowest level resources needed for a vTDS cluster on a
given host provider, in this case GCP.

Each Provider Layer implementation contains provider specific code and
a fully defined base configuration capable of deploying the provider
resources of the cluster. The base configuration of the GCP Provider
Layer implementation, defines the default settings for resources
needed to construct a vTDS platform consisting of Ubuntu based linux
GCP instances (Virtual Blades) connected by a GCP provided network
(Blade Interconnect) within a single VPC in a single GCP region. The
Blade Interconnect and Virtual Blade configurations are provided as
templates or base-classes on which other configurations can be
built. Each GCP instance (Virtual Blade) is configured to permit
nested virtualization and with enough CPU and memory to host (at
least) a single nested virtual machine. The assignment of virtual
machines (Virtual Nodes) and Virtual Networks to these blade and
interconnect resources as well as the configuration of Virtual Blades
at the OS level are handled in higher layers of the vTDS stack.

NOTE: while the base configuration contains examples of every
configuration setting and its default value in a given context, this
config is not sufficient to deploy a Provider Layer for an actual vTDS
system. Three things are needed to complete a working configuration:

* The GCP Organization configuration of the system
* A Blade Interconnect configuration that is not a 'pure_base_class'
* A Virtual Blade configuration with at least one instance specified
  that is not a 'pure_base_class'

The GCP Organization overlay provides information specific to your GCP
Organization. There is more information on this in the Getting Started
Guide section of this README.

Canned configuration overlays for all layers of vTDS that are
appropriate for various different applications can be found in the
[vtds-configs](https://github.com/Cray-HPE/vtds-configs)
GitHub repository. Canned configuration overlays that offer GCP Provider Layer specific configuration of Blade Interconnects and Virtual Blades (among other things) are available in the
[layers/provider/gcp](https://github.com/Cray-HPE/vtds-configs/tree/main/layers/provider/gcp)
sub-directory of that repository.

An overview of vTDS is available in the
[vTDS Core Repository](https://github.com/Cray-HPE/vtds-core/blob/main/README.md).

## Getting Started with the GCP Provider Implementation

### GCP Resources, Roles and Tools

As its name suggests, the GCP Provider Layer Implementation uses
Google Cloud Platform (GCP) to implement a vTDS Provider Layer. To be
able to use GCP, the user must have access to the resources of a GCP
Organization, must be assigned a set of roles related to those
resources and must have installed the necessary GCP related tools on
their local system. Much of this is administrative preparation that
the user does not control. In order to make it possible to set up,
though, it is described here.

#### GCP Organization and Administrative Setup

The GCP Provider Layer requires you to have access to GCP through a
GCP
[organization](https://cloud.google.com/resource-manager/docs/creating-managing-organization#acquiring).
You will need to arrange to create one, which will also involve
setting up [Google Cloud
Identity](https://cloud.google.com/identity/docs/set-up-cloud-identity-admin)
or
[Google Workspace](https://support.google.com/a/answer/53926)
if you don't already have one. As part of setting that up, a billing
account will be created and associated with your organization. The
billing account will have a name, which name can be anything, but for
this guide, we will name it `gcp-billing`.

The administrator of your organization must also create a folder for
vTDS projects within your organization. They may name the folder
anything they like, but for the sake of this guide, we will use the
name `vtds-systems`.

Within the `vtds-systems` folder, your administrator must create a
'seed project' for vTDS deployments. The seed project is a GCP project
that has no compute instances and serves as a persistent well known
place to store vTDS system state using Google Cloud Storage. This
project may also be named anything, but for this guide we will use
`vtds-seed`.

Finally, your administrator should set up a Google Group within your
organization. This group will permit its members to obtain the
permissions needed to create, destroy and use vTDS systems. This group
can be named anything, but for this guide we will use
`vtds-users`, which, when fully qualified will be
```vtds-users@myorganization.net```
if your organization's domain name is `myorgaization.net`. This group
needs the following access roles:

- On the `gcp-billing` billing account, the `vtds-users` group needs
  to be a pricipal with the `Billing User` role.

- At the GCP Organization level the `vtds-users` group needs the `viewer`
  role.

- On the `vtds-systems` folder the `vtds-users` group needs the
  following roles:

  - Project Creator

  - Project Deleter

  - Project IAM Admin

  - Project Billing Manager

- On the `vtds-seed` project the `vtds-users` group needs the
  `storage-admin` role.

#### GCP User Requirements and SDK Installation

As a vTDS user, you will need an account within your organization that
is a member of the `vtds-users` group.

As a vTDS user you need to have the
[Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
installed on your local system.

As a vTDS user you will need to be logged into your GCP account both
as an SDK user and as an application user (portions of the vTDS code
have to use the `gcloud` command instead of GCP client libraries,
which forces vTDS to require both). To do this, run the following two
commands on your local system:
```
gcloud auth login
```
and
```
gcloud auth application-default login
```

These will (typically) pop up a browser and let you log into your
account and authorize access. The first authorizes SDK (`gcloud`
command) access. The second authorizes application client library (in
this case, primarily terraform) access.

### Terraform and Terragrunt Preparation

The vTDS GCP Provider implementation uses
[Terragrunt](https://terragrunt.gruntwork.io/) and
[Terraform](https://www.terraform.io/)
to construct the GCP project that will be used for a vTDS cluster. The
layer code manages the versions of Terraform and Terragrunt using the
Terraform Version Manager (`tfenv`) and the Terragrunt Version Manager
(`tgenv`). You will need to install both of these before using the GCP
Provider Implementation.

Installation of the Terraform Version Manager is explained
[here](https://github.com/tfutils/tfenv#installation).

Installation of Terragrunt Version Manager is explained
[here](https://github.com/tgenv/tgenv/blob/main/README.md#installation-wrench).

### Using the GCP Provider Layer Implementation

To use the GCP Provider Layer Implementation in your vTDS stack, edit
the core configuration you are using to deploy your vTDS system and
configure the Provider Layer to pull in `vtds-provider-gcp`. The GCP
Provider Layer Implementation is available as a stream of stable
releases from PyPI or in source form from GitHub. When pulling from
PyPI the version can be null, in which case the latest version will be
used, or it can specify any of the published stable versions. When
pulling from GitHub the version can be null, in which case the `main`
branch will be used, or set to a tag, branch or digest indicating a
git version.

#### Pulling from PyPI

Here is the form of the configuration for pulling the GCP Provider
Layer Implementation from PyPI:

```
    provider:
      package: vtds-provider-gcp
      module: vtds_provider_gcp
      source_type: pypi
      metadata:
        version: null
```

#### Pulling from GitHub

Here is the form of the configuration for pulling the GCP Provider
Layer Implementation from GitHub:

```
    provider:
      package: vtds-provider-gcp
      module: vtds_provider_gcp
      source_type: git
      metadata:
        url: "git@github.com:Cray-HPE/vtds-provider-gcp.git"
        version: null
```

Generally speaking, there will be a canned core configuration for your
vTDS application available in
[the core configurations provided by vtds-configs](https://github.com/Cray-HPE/vtds-configs/tree/main/layers/provider/gcp)
that will already be set up to pull in the GCP Provider Layer
Implementation, so you should be able to simply copy and modify that. Instructions for setting up to deploy your vTDS system can be found in the
[vTDS Core Getting Started guide](https://github.com/Cray-HPE/vtds-core/blob/VSHA-652/README.md#getting-started-with-vtds).

#### Using an Organization Config Overlay

The canned core configurations generally split the Provider Layer
configuration into two separate overlays. One that provides the
desired application specific configuration of the layer and another
that provides information about the organization hosting the vTDS
system. By decoupling organization information, these two
configuration overlays allow multiple core configurations to share the
same organization config for different applications, and multiple
organizations to share the same application specific configuration
overlay without conflict. This approach also allows an organization to
host its organization configuration separately from the canned
configurations. You will need to create an organization configuration
overlay and make it available somewhere. You have the choice of simply
adding the necessary content to your core configuration, making a
separate file and using it locally through command line options to the
`vtds` commands, hosting the file at a simple URL of your choosing, or
hosting the file in a GitHub or private remote Git repository. In any
case, your organization configuration should be based on this
[annotated example Organization configuration
overlay](https://github.com/Cray-HPE/vtds-configs/blob/main/layers/provider/gcp/provider-gcp-example-org.yaml).

Once you have the Organization configuration overlay prepared and
hosted, assuming you are not putting it in the core configuration or
in a local file, modify your core configuration file to pull in the
Organization configuration overlay.
