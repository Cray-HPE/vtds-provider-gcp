# Blade Interconnect Subnet

The actual network used by Virtual Blades (GCP VM Instances) in the
GCP implementation of vTDS is the subnet defined in the associated
Blade Interconnect. Each Virtual Blade must be connected to exactly
one Blade Interconnect subnet using the `subnetwork` attribute of the
GCP VM Instance. Different classes of Virtual Blades may be connected
to different Blade Interconnects as needed to implement the desired
vTDS platform.

The template for creating the subnet is contained in the `deploy`
sub-directory here. The `terragrunt.hcl` file contained in there is a
Jinja template to be filled out by the vTDS layer implementation and
used to generate the Terragrunt control files at the correct place in
the build tree.

Because the subnet is part of the overall blade interconnect, its
configuration is found inside the class definition of the blade
interconnect class it belongs to, so `{{ config_path }}` expands to
the same value here as for the parent blade interconnect template.
