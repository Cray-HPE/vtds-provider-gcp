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

# Include all settings from the root terragrunt.hcl file
include {
  path = find_in_parent_folders()
}

locals {
  vtds_vars      = yamldecode(file(find_in_parent_folders("vtds.yaml")))
  inputs_vars    = yamldecode(file("inputs.yaml"))
  activate_apis  = distinct(
      concat(
          local.vtds_vars.provider.project.activate_apis_default,
          local.inputs_vars.activate_extra_apis
      )
  )
  name              = format(
      "%s-%s",
      local.vtds_vars.provider.organization.name,
      local.vtds_vars.provider.project.base_name,
  )
}

terraform {
  source = format("%s?%s", local.inputs_vars.source_module.url, local.inputs_vars.source_module.version)
}

inputs = {
  activate_apis               = local.activate_apis
  disable_dependent_services  = local.inputs_vars.disable_dependent_services
  disable_services_on_destroy = local.inputs_vars.disable_services_on_destroy
  group_name                  = local.vtds_vars.provider.project.group_name
  group_role                  = local.vtds_vars.provider.project.group_role
  folder_id                   = local.vtds_vars.provider.project.folder_id
  labels                      = merge(local.vtds_vars.provider.project.labels, local.inputs_vars.labels)
  name                        = local.name
  project_id                  = local.name
  random_project_id           = local.vtds_vars.provider.project.random_project_id
  deletion_policy             = local.vtds_vars.provider.project.deletion_policy
}
