# Network Templates

The templates in this tree provide the basis for constructing
Terragrunt control files for making networks (private VPCs) to contain
Blade Interconnect sub-networks in a vTDS system, attaching routes to
them and attaching firewall rules to them.

The following sub-directories contain templates:

* `vpc` contains the private VPC Terragrunt deployment template.
* `firewalls` contains Terragrunt deployment template for firewalls and
   rules associated with a blade interconnect by the VPCs name
* `static-routes` contains Terragrunt deployment template for static
   routes to be associated with the blade interconnect by the VPC's
   name.
