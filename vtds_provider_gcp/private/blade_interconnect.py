#
# MIT License
#
# (C) Copyright [2024] Hewlett Packard Enterprise Development LP
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
"""Private layer code to compose and work with dynamically created
Terragrunt / Terraform control structures that define the resources
associated with classes of vTDS Blade Interconnects for the purpose of
deploying Blade Interconnects implemented as GCP networks and the
associated GCP Virtual Private Clouds (VPCs) into a platform
implemented as a GCP project.

"""
from os.path import join as path_join
from vtds_base import (
    ContextualError,
    render_templated_tree
)


class BladeInterconnect:
    """Class representing a single blade interconnect type as defined
    in the vTDS configuration and implemented in the vTDS Terragrunt
    configuration / constrol struture.

    """
    def __init__(self, terragrunt):
        """Constructor

        """
        self.terragrunt = terragrunt

    @staticmethod
    def _make_old_style_rule(rule, direction):
        """Using a new style ingress or egress rule construct an
        old-style firewall rule for the soon to be deprecated 'rules'
        variable.

        """
        direction = "INGRESS" if direction == 'ingress_rules' else "EGRESS"
        range_type = (
            "source_ranges" if direction == "INGRESS" else "destination_ranges"
        )
        return {
            'name': rule.get('name', None),
            'description': rule.get('description', ""),
            'direction': direction,
            'disabled': rule.get('disabled', False),
            'priority': rule.get('priority', 100),
            'ranges': rule.get(range_type, []),
            'source_tags': rule.get('source_tags', []),
            'source_service_accounts': rule.get('source_service_accounts', []),
            'target_tags': rule.get('target_tags', []),
            'target_service_accounts': rule.get('target_service_accounts', []),
            'allow': rule.get('allow', []),
            'deny': rule.get('deny', []),
            'log_config': rule.get('log_config', {}),
        }

    @classmethod
    def __convert_firewalls(cls, interconnect_config):
        """Class Private: Convert ingress and egress firewall rules in
        a blade-interconnect configuration from maps to lists so that
        terragrunt can use them.

        """
        no_rules = {'ingress_rules': {}, 'egress_rules': {}}
        firewall = interconnect_config.get('firewall', no_rules)
        overall_rules = []
        for direction in ['ingress_rules', 'egress_rules']:
            rule_list = []
            rule_map = firewall.get(direction, {})
            for _, rule in rule_map.items():
                if rule.get('delete', False):
                    continue
                # 'delete' is not part of the firewall rule, it is
                # used to control whether rules are kept through
                # inheritance or not, so remove the key so it doesn't
                # confuse terragrunt / google.
                try:
                    del rule['delete']
                except KeyError:
                    pass
                rule_list.append(rule)
                overall_rules.append(cls._make_old_style_rule(rule, direction))
            # Replace the map (if any) with the list. If no map was there, it
            # is now an explicit empty list.
            firewall[direction] = rule_list
        # Add the soon to be deprecated 'rules' entry to the firewall too.
        firewall['rules'] = overall_rules
        return interconnect_config

    def initialize(self, key, interconnect_config):
        """Using the name of the blade interconnect configuration
        found in 'key' and the blade interconnect configuration found
        in 'interconnect_config' construct and inject a Blade
        Interconnect type into the Terragrunt control tree managed by
        'terragrunt'.

        """
        # Convert the firewall rule maps into lists for terragrunt
        interconnect_config = self.__convert_firewalls(interconnect_config)

        # Locate the top of the template for blade_interconnects
        template_dir = self.terragrunt.template_path(
            path_join("system", "platform", "blade-interconnect")
        )

        # Copy the templates into the build tree before rendering them.
        build_dir = self.terragrunt.add_subtree(
            template_dir,
            path_join(
                "terragrunt", "system", "platform", "blade-interconnect", key
            )
        )

        # Compose the data to be used in rendering the templated files.
        try:
            render_data = {
                'network_name': interconnect_config['network_name'],
                'config_path': "provider.blade_interconnects.%s" % key,
            }
        except KeyError as err:
            raise ContextualError(
                "missing config in the Blade Interconnect class '%s': %s" % (
                    key, str(err)
                )
            ) from err

        # Render the templated files in the build tree.
        render_templated_tree(["*.hcl", "*.yaml"], render_data, build_dir)
        return interconnect_config
