#
# MIT License
#
# (C) Copyright [2021-2022] Hewlett Packard Enterprise Development LP
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
  ips            = local.vtds_vars.{{ config_path }}.blade_interconnect.ip_addrs
  static_ips     = slice(local.ips, 0, local.vtds_vars.{{ config_path }}.count)
}

dependency "service_project" {
  config_path = find_in_parent_folders("system/project/deploy")

  mock_outputs = {
    project_id                              = "gcp-terragrunt-mock-project"
    project_number                          = "12345678910"
    mock_outputs_allowed_terraform_commands = ["validate", "plan"]
  }
}

dependency "{{ interconnect_name }}" {
  config_path = find_in_parent_folders("blade-interconnect/{{ interconnect_name }}/subnet/deploy")
  skip_outputs = true
}

dependency "instance_template" {
  config_path = find_in_parent_folders("instance-template/deploy")

  mock_outputs = {
    self_link                               = "/projects/gcp-terragrunt-mock-project/instance-templates/my-instance-template"
    mock_outputs_allowed_terraform_commands = ["validate", "plan"]
  }
}

terraform {
  source = format("%s?%s", local.inputs_vars.source_module.url, local.inputs_vars.source_module.version)
}

inputs = {
  project_id           = dependency.service_project.outputs.project_id
  instance_template    = dependency.instance_template.outputs.self_link
  region               = local.vtds_vars.provider.project.region
  zone                 = local.vtds_vars.provider.project.zone
  num_instances        = local.vtds_vars.{{ config_path }}.count
  static_ips           = local.static_ips
  network              = ""
  subnetwork           = format("{{ interconnect_name }}-%s", local.vtds_vars.provider.project.region)
  subnetwork_project   = dependency.service_project.outputs.project_id
  {% if access_config %}
  access_config        = local.vtds_vars.{{ config_path }}.access_config
  {% endif %}
  add_hostname_suffix  = local.vtds_vars.{{ config_path }}.add_hostname_suffix
  hostname_suffix_separator = local.vtds_vars.{{ config_path }}.hostname_suffix_separator
  hostname             = local.vtds_vars.{{ config_path }}.hostname
}
