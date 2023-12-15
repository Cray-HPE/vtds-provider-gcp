# Internal Network (private VPC) Firewalls

Firewall rules in the GCP implementation of vTDS are associated with
there Blade Interconnect through the Blade Interconnect's VPC.

The template for creating a firewall is contained in the `deploy`
sub-directory here. The `terragrunt.hcl` file contained in there is a
Jinja template to be filled out by the vTDS layer implementation and
used to generate the Terragrunt control files at the correct place in
the build tree.

Because the firewall rules described here belong, ultimately, to the
blade interconnect containging the firewall, the value of `{{
config_path }}` here is the same as that of the parent blade
interconnect class.
