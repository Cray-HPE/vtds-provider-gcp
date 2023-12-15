# Virtual Blade (GCP VM Instance) Template

Virtual Blades are implemented in GCP using GCP VM Instances with nested
virtualization turned on. Nodes are then run as non-GCP managed VMs on
top of the Virtual Blades (orchestrated by the platform and cluster
layers). Terragrunt is used to build Virtual Blades of different
configurations, each of which can be defined as a 'class' of blade in
the system configuration. Each class of blade then gets its own
deployment tree in the build tree for the vTDS system.

There are three parts to setting up a Virtual Blade:

* the GCP Instance Template specification
* the GCP Compute Instance specification
* the GCP Service Account setup for the class of Virtual Blade

Each of these has its own templates in its own sub-tree of this
direxctory, and each is decribed further at the top of its sub-tree.

It is worth noting that, due to limitations in the way Terragrunt /
Terraform go about assigning internal IP addresses to GCP instances, a
given class of Virtual Blades can only live on one Blade Interconnect
subnet within one Internal Network. That said, different classes of
virtual blades can live on different subnets within a single Internal
Network, or can live on separate internal networks.
