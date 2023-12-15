# Templates for Dynamically Configured Terragrunt

Terragrunt is good at configuring systems with basically static high
level topology (numbers and names of networks, types of nodes, and so
forth) but it does not provide much in the way of tools for configuring
a wider variety of topologies. The vTDS configuration and APIs use
templated examples of Terragrunt files to fill out a Terragrunt build
tree with all of the resources defined in the configuration. This allows
more complex and dynamic system creation to be configuration driven.

The directories found in this part of the layer implementation contain
the templates for different aspects of a vTDS deployment.
