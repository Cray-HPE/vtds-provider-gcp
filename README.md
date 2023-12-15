# vtds-provider-gcp

The GCP provider layer implementation for vTDS allowing a vTDS cluster
to be built as a GCP project.

## Description This repo provides the code and a base configuration to
deploy a Virtual Test and Development System (vTDS) cluster in a
Google Cloud Platform (GCP) project within an existing Google
organization. It is intended as the GCP provider layer for vTDS which
is a provider and product neutral framework for building virtual
clusters to test and develop software. The provider layer defines the
configuration structure and software implementation required to
establish the lowest level resources needed for a vTDS cluster on a
given host provider, in this case GCP.

Each provider implementation contains provider specific code and a fully
defined base configuration capable of deploying the provider resources
of the cluster. The base configuration here, if used unchanged, defines
the resources needed to construct a vTDS platform consisting of Ubuntu
based linux GCP instances connected by GCP networks within a single VPC
in a single GCP region. Each GCP instance type is configured to permit
nested virtualization and with enough CPU and memory to host (at least)
a single nested virtual machine. The number, naming, addressing, and so
forth of the instances, as well as any creation of virtual machines,
virtual networks or other constructs is driven by one of the higher
layers in the vTDS architecture.

The core driver mechanism and a brief introduction to the vTDS
architecture and concepts can be found in the [vTDS Core Project
Repository](https://github.com/Cray-HPE/vtds-core/tree/main).

