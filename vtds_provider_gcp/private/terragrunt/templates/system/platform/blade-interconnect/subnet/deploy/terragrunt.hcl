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

dependency "vpc" {
  config_path = find_in_parent_folders("vpc/deploy")
  skip_outputs = true
}

terraform {
  source = format("%s?%s", local.inputs_vars.source_module.url, local.inputs_vars.source_module.version)
}

inputs = {
  project_id       = dependency.service_project.outputs.project_id
  network_name     = "{{ network_name }}"
  subnets = [
    {
      subnet_name                      = format("{{ network_name }}-%s", local.vtds_vars.provider.project.region)
      subnet_ip                        = local.vtds_vars.{{ config_path }}.ipv4_cidr
      subnet_region                    = local.vtds_vars.provider.project.region
      subnet_private_access            = local.vtds_vars.{{ config_path }}.private_access
      subnet_private_ipv6_access       = local.vtds_vars.{{ config_path }}.private_ipv6_access
      subnet_flow_logs                 = local.vtds_vars.{{ config_path }}.flow_logs
      subnet_flow_logs_interval        = local.vtds_vars.{{ config_path }}.flow_logs_interval
      subnet_flow_logs_sampling        = local.vtds_vars.{{ config_path }}.flow_logs_sampling
      subnet_flow_logs_metadata        = local.vtds_vars.{{ config_path }}.flow_logs_metadata
      subnet_flow_logs_filter          = local.vtds_vars.{{ config_path }}.flow_logs_filter
      subnet_flow_logs_metadata_fields = local.vtds_vars.{{ config_path }}.flow_logs_metadata_fields
      description                      = local.vtds_vars.{{ config_path }}.description
      purpose                          = local.vtds_vars.{{ config_path }}.description
      role                             = local.vtds_vars.{{ config_path }}.role
      stack_type                       = local.vtds_vars.{{ config_path }}.stack_type
      ipv6_access_type                 = local.vtds_vars.{{ config_path }}.ipv6_access_type
    }
  ]
  secondary_ranges = {}
}
