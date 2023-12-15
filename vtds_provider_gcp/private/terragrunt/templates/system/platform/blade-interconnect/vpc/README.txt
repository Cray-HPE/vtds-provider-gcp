# Blade Interconnect VPCs

Each Blade Interconnect in the GCP implementation of vTDS consists of an
IP subnet (the actual network the Virtual Blades are "plugged into") and
a Virtual Private Cloud (VPC) which hosts the subnet and other network
resources like routes and firewall rules associated with the Blade
Interconnect.

The template for creating the VPC for the Blade Interconnect is
contained in the `deploy` sub-directory here. The `terragrunt.hcl` file
contained in there is a Jinja template to be filled out by the vTDS
layer implementation and used to generate the Terragrunt control files
at the correct place in the build tree.
