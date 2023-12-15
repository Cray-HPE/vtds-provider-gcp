# Blade Interconnects

Blade Interconnects in the GCP implementation of vTDS are the GCP
networks that connect Virtual Blades (GCP instances) together and
provide a backbone for the virtual networking set up by the Platform
and Cluster layers to support the Application layer. There can be
multiple Blade Interconnects defined for a given vTDS system as needed
for interconnecting various classes of Virtual Blades. Any given class
of Virtual Blade, however, can only reside on a single Blade
Interconnect. Routes and Firewalls defined by the Blade Interconnects
determine the reachability of Virtual Blades on different Blade
Interconnects.

This directory is a placeholder for filled out Blade Interconnect
templates which are placed here by interconnect name when this layer
is initialized.
