The sub-trees in this directory specify IAM deployments for the
Virtual Blade Service Account that permit configured roles to be
granted to that Service Account on resources at various points in the
GCP hierarchy. The Provider Layer configuration contains the role
assignments categorized by resource to be applied and the templates
within the sub-trees configure Terragrunt to deploy the appropriate
IAM settings to grant the role assignments.

At present, the following resource categories are covered by the
configuration:

- Source Image: roles relating to using private source images sourced
  from a specific project within the vTDS cluster project.
- Billing: roles granted by the Billing Account for the vTDS cluster
- Organization: roles granted by the organization hosting the vTDS cluster
- Clusters Folder: roles granted by the GCP folder containing vTDS clusters
- Seed Project: roles granted by the Seed Project used by vTDS to deploy clusters
- Cluster Project: roles granted by the GCP project hosting the vTDS cluster

As the need for roles granted by other resources arises new
configuration and new IAM sub-trees will be needed to deploy them. The
configuration of IAM for a given Virtual Blade's service account is
found in the `iam` section of the Virtual Blade configuration and
sub-divided by resource.
