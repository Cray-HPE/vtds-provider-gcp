#
# MIT License
#
# (C) Copyright 2026 Hewlett Packard Enterprise Development LP
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
  vtds_vars   = yamldecode(file(find_in_parent_folders("vtds.yaml")))
  inputs_vars = yamldecode(file("inputs.yaml"))
  billing_account = local.vtds_vars.provider.organization.billing_account
}

dependency "service_account" {
  config_path = find_in_parent_folders("service-account/deploy")

  mock_outputs = {
    email                                   = "serviceaccount@iam.google.com"
    mock_outputs_allowed_terraform_commands = ["validate", "plan"]
  }
}

terraform {
  source = format("%s?%s", local.inputs_vars.source_module.url, local.inputs_vars.source_module.version)
}

inputs = {
  billing_account_ids = [ local.billing_account ]
  mode                = "additive"
  bindings = {
    {%- for role in service_account_iam.billing | default([]) %}
    "{{ role }}" = [
      format("serviceAccount:%s", dependency.service_account.outputs.email),
    ]
    {%- endfor %}
  }
}
