#
# MIT License
#
# (C) Copyright 2023 Hewlett Packard Enterprise Development LP
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
}

dependency "service_project" {
  config_path = find_in_parent_folders("system/project/deploy")

  mock_outputs = {
    project_id                              = "gcp-terragrunt-mock-project"
    project_number                          = "12345678910"
    mock_outputs_allowed_terraform_commands = ["validate", "plan"]
  }
}

# This is the service account defined for this node class (in the
# node class "service_account" subtree). There is one per node
# class.
dependency "service_account" {
  config_path = find_in_parent_folders("service-account/deploy")

  mock_outputs = {
    email                                   = "serviceaccount@iam.google.com"
    mock_outputs_allowed_terraform_commands = ["validate", "plan"]
  }
}

dependency "{{ interconnect_name }}" {
  config_path = find_in_parent_folders("system/platform/blade-interconnect/{{ interconnect_name }}/subnet/deploy")
  skip_outputs = true
}

terraform {
  source = format("%s?%s", local.inputs_vars.source_module.url, local.inputs_vars.source_module.version)
}

inputs = {
  project_id                       = dependency.service_project.outputs.project_id
  name_prefix                      = local.vtds_vars.{{ config_path }}.name_prefix
  machine_type                     = local.vtds_vars.{{ config_path }}.vm.machine_type
  min_cpu_platform                 = local.vtds_vars.{{ config_path }}.vm.min_cpu_platform
  can_ip_forward                   = local.vtds_vars.{{ config_path }}.can_ip_forward
  tags                             = local.vtds_vars.{{ config_path }}.tags
  labels                           = local.vtds_vars.provider.project.labels
  preemptible                      = local.vtds_vars.{{ config_path }}.availability.preemptible
  spot                             = local.vtds_vars.{{ config_path }}.availability.spot
  automatic_restart                = local.vtds_vars.{{ config_path }}.availability.automatic_restart
  on_host_maintenance              = local.vtds_vars.{{ config_path }}.availability.on_host_maintenance
  spot_instance_termination_action = local.vtds_vars.{{ config_path }}.availability.spot_instance_termination_action
  region                           = local.vtds_vars.provider.project.region
  enable_nested_virtualization     = local.vtds_vars.{{ config_path }}.vm.enable_nested_virtualization
  threads_per_core                 = local.vtds_vars.{{ config_path }}.vm.threads_per_core
  resource_policies                = local.vtds_vars.{{ config_path }}.resource_policies
  source_image                     = local.vtds_vars.{{ config_path }}.vm.boot_disk.source_image
  source_image_family              = local.vtds_vars.{{ config_path }}.vm.boot_disk.source_image_family
  source_image_project             = local.vtds_vars.{{ config_path }}.vm.boot_disk.source_image_project
  disk_size_gb                     = local.vtds_vars.{{ config_path }}.vm.boot_disk.disk_size_gb
  disk_type                        = local.vtds_vars.{{ config_path }}.vm.boot_disk.disk_type
  disk_labels                      = local.vtds_vars.{{ config_path }}.vm.boot_disk.disk_labels
  disk_encryption_key              = local.vtds_vars.{{ config_path }}.vm.boot_disk.disk_encryption_key
  auto_delete                      = local.vtds_vars.{{ config_path }}.vm.boot_disk.auto_delete
  additional_disks                 = local.vtds_vars.{{ config_path }}.vm.additional_disks
  network                          = ""
  subnetwork                       = format("{{ interconnect_name }}-%s", local.vtds_vars.provider.project.region)
  subnetwork_project               = dependency.service_project.outputs.project_id
  nic_type                         = local.vtds_vars.{{ config_path }}.blade_interconnect.nic_type
  stack_type                       = local.vtds_vars.{{ config_path }}.blade_interconnect.stack_type
  additional_networks              = local.vtds_vars.{{ config_path }}.blade_interconnect.additional_networks
  total_egress_bandwidth_tier      = local.vtds_vars.{{ config_path }}.blade_interconnect.total_egress_bandwidth_tier
  startup_script                   = local.vtds_vars.{{ config_path }}.metadata.startup_script
  metadata                         = local.vtds_vars.{{ config_path }}.metadata.metadata
  service_account                  = { "email" = dependency.service_account.outputs.email, "scopes" = local.inputs_vars.scopes }
  enable_shielded_vm               = local.vtds_vars.{{ config_path }}.security.enable_shielded_vm
  shielded_instance_config         = local.vtds_vars.{{ config_path }}.security.shielded_instance_config
  enable_confidential_vm           = local.vtds_vars.{{ config_path }}.security.enable_confidential_vm
  access_config                    = local.vtds_vars.{{ config_path }}.access_config
  ipv6_access_config               = local.vtds_vars.{{ config_path }}.ipv6_access_config
  gpu                              = local.vtds_vars.{{ config_path }}.gpu
}
