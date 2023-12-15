# Internal Network (private VPC) Routes

Routes in the GCP implementation of vTDS are associated with their
Blade Interconnect through the Blade Interconnect's VPC.

The template for creating a route is contained in the `deploy`
sub-directory here. The `terragrunt.hcl` file contained in there is a
Jinja template to be filled out by the vTDS layer implementation and
used to generate the Terragrunt control files at the correct place in
the build tree.

Because the routes described here belong, ultimately, to the blade
interconnect containging the subnet that the routes are assigned to,
the value of `{{ config_path }}` here is the same as that of the
parent blade interconnect class.
