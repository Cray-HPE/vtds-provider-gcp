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

# Include all settings from the root terragrunt.hcl file
include {
  path = find_in_parent_folders()
}

locals {
  vtds_vars      = yamldecode(file(find_in_parent_folders("vtds.yaml")))
  inputs_vars    = yamldecode(file("inputs.yaml"))
}

dependency "service_project" {
  config_path = find_in_parent_folders("system/project/deploy")

  mock_outputs = {
    project_id                              = "gcp-terragrunt-mock-project"
    mock_outputs_allowed_terraform_commands = ["validate", "plan"]
  }
}

terraform {
  source = format("%s?%s", local.inputs_vars.source_module.url, local.inputs_vars.source_module.version)
}

inputs = {
  project_id                               = dependency.service_project.outputs.project_id
  network_name                             = local.vtds_vars.{{ config_path }}.network_name
  description                              = local.vtds_vars.{{ config_path }}.description
  routing_mode                             = local.vtds_vars.{{ config_path }}.routing_mode
  shared_vpc_host                          = false
  auto_create_subnets                      = false
  mtu                                      = local.vtds_vars.{{ config_path }}.mtu
  enable_ipv6_ula                          = local.vtds_vars.{{ config_path }}.enable_ipv6_ula
  internal_ipv6_range                      = local.vtds_vars.{{ config_path }}.internal_ipv6_range
#  network_firewall_policy_enforcment_order = local.vtds_vars.{{ config_path }}.network_firewall_policy_enforcement_order
}
