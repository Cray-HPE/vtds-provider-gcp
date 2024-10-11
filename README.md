# vtds-provider-gcp

The GCP provider layer implementation for vTDS allowing a vTDS cluster
to be built as a GCP project.

## Description

This repo provides the code and a base configuration to deploy a vTDS
cluster in a Google Cloud Platform (GCP) project within an existing
Google organization. It is intended as the GCP provider layer for vTDS
which is a provider and product neutral framework for building virtual
clusters to test and develop software. The provider layer defines the
configuration structure and software implementation required to
establish the lowest level resources needed for a vTDS cluster on a
given host provider, in this case GCP.

Each provider implementation contains provider specific code and a
fully defined base configuration capable of deploying the provider
resources of the cluster. The base configuration here, if used
unchanged, defines the resources needed to construct a vTDS platform
consisting of Ubuntu based linux GCP instances (Virtual Blades)
connected by GCP networks (Blade Interconnects) within a single VPC in
a single GCP region. Each GCP instance type is configured to permit
nested virtualization and with enough CPU and memory to host (at
least) a single nested virtual machine. The assignment of virtual
machines (Virtual Nodes) and Virtual Networks to these blade and
interconnect resources as well as the configuration of Virtual Blades
at the OS level is done at a higher layer in the stack.

For an overview of vTDS see the
[vTDS Core Repository](https://github.com/Cray-HPE/vtds-core).

## Getting Started with the GCP Provider Implementation

The vTDS GCP Provider implementation uses
[Terragrunt][(https://terragrunt.gruntwork.io/) and
[Terraform](https://www.terraform.io/) to construct the GCP project
that will be used for a vTDS cluster. The layer code manages the
versions of Terraform and Terragrunt using the Terraform Version
Manager (_tfenv_) and the Terragrunt Version Manager (_tgenv_). You
will need to install both of these before using the GCP Provider
Implementation.

Installation of the Terraform Version Manager is explained
[here](https://github.com/tfutils/tfenv#installation).

Installation of Terragrunt Version Manager is explained
[here](https://github.com/tgenv/tgenv/blob/main/README.md#installation-wrench).

The vTDS GCP Provider implementation also assumes that you have a GCP
organization set up and are able to log into that organization with
sufficient permissions to create and manage a vTDS cluster:

```
TBD GCP Permissions here...
```

Finally, the vTDS Provider implementation requires that the Google SDK
be installed on the local system from which you will be deploying and
managing vTDS clusters. Here are [instructions for installling the
Google SDK](https://cloud.google.com/sdk/docs/install).
