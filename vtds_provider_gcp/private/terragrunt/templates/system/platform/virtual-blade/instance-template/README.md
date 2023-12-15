# Virtual Blade Instance Template

GCP uses Instance Templates to define many of the characteristics of a
GCP VM instance that are common across all instances of a given
class. The Instance Template when combined with a Compute Instance
specification (and the Terragrunt Logic to deploy multiple VM
instances using a single Compute Instance specification) allows VM
instances to be replicated easily within the constraints of the
Instance Template.

vTDS recognizes the need for multiple different classes of Virtual
Blades within a single vTDS system, so each class of Virtual Blade has
its own configuration that drives creation of GCP Instance Templates
for a given class of Virtual Blade. The `deploy` directory here
contains the templates used by the GCP provider layer to populate
Terragrunt control files based on configuration and API calls.
