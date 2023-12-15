# Terragrunt Supporting Content

The GCP provider layer implementation uses terragrunt / terraform to
deploy GCP resources driven by calls into the provider layer API and
by the system configuration. The system configuration contains classes
of Virtual Blades, Blade Interconnects and so forth for which
Terragrunt needs up-front deployment data on a per-class basis. Since
it is difficult to adapt Terragrunt to respond dynamically to things
that it expects as static up-front data, the GCP provider code
composes a Terragrunt deployment tree on the fly prior to running the
Terragrunt phases to manage a vTDS system. This composition is driven
by higher layers (platform, cluster or application) during the the
`initialize` stage of the vTDS Core driver execution.

This directory suuports generation of the overall Terragrunt deployment
by providing the following:

* the vTDS terragrunt framework in the `framework` sub-tree
* a set of templated generic sub-deployment modules

The framework is static and is copied into place in the `build`
directory (differentiated by system name) in the root of the
repository tree at the start of building a new vTDS system.  The
provider layer code uses the templated sub-deployment modules to build
sub-deployments within the framework to implement distinct classes for
things like Virtual Blades and Blade Interconnects and their
constituent GCP constructs. When the `initialize` phase finishes a
full Terragrunt deployment tree is in-place and ready to be used.
