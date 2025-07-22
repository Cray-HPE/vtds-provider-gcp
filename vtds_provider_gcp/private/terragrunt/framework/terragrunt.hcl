#
# MIT License
#
# (C) Copyright [2023] Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# terragrunt root hcl

locals {
  vtds_vars  = yamldecode(file("vtds.yaml"))
  terragrunt_version = format(
      "= %s",
      local.vtds_vars.provider.terragrunt.terragrunt_version
  )
  terraform_version = format(
      "= %s",
      local.vtds_vars.provider.terragrunt.terraform_version
  )
  trusted_cidrs = setunion(
      local.vtds_vars.provider.organization.trusted_cidrs,
      local.vtds_vars.provider.project.trusted_cidrs
  )
  bucket        = format(
      "%s-%s-tf-state",
      local.vtds_vars.provider.organization.name,
      local.vtds_vars.provider.project.base_name
  )
}

remote_state {
  backend = "gcs"
  config = {
    bucket                 = local.bucket
    prefix                 = path_relative_to_include()
    location               = local.vtds_vars.provider.project.location
    project                = local.vtds_vars.provider.organization.seed_project
    skip_bucket_creation   = false
    skip_bucket_versioning = true
    enable_bucket_policy_only = true
  }
  generate = {
    path      = "remotestate.tf"
    if_exists = "overwrite_terragrunt"
  }
}

inputs = {
  org_id                     = local.vtds_vars.provider.organization.org_id
  parent                     = local.vtds_vars.provider.organization.parent
  prefix                     = local.vtds_vars.provider.organization.name
  billing_account            = local.vtds_vars.provider.organization.billing_account
  gcloud_skip_download       = local.vtds_vars.provider.project.gcloud_skip_download
  orgpolicies_skip_execution = local.vtds_vars.provider.project.orgpolicies_skip_execution
  activate_apis_default      = local.vtds_vars.provider.project.activate_apis_default
  labels                     = local.vtds_vars.provider.project.labels
  trusted_cidrs              = local.trusted_cidrs
}
terraform_version_constraint  = local.terraform_version
terragrunt_version_constraint = local.terragrunt_version
