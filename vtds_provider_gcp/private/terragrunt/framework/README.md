# Root of vTDS Terragrunt Deployment Tree

This directory contains the root Terragrunt configuration for vTDS in
`terragrunt.hcl` and is the root of the Terragrunt framework which
proceeds down from here in the `system` directory tree. This is also a
placeholder for the directory in the build tree where the generated vTDS
configuration `vtds.yaml` is placed by the provider layer
implementation. The generated `vtds.yaml` is derived from the master
configuration constructed by the vTDS core during the vTDS
`configure` phase.
