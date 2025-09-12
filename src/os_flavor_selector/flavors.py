# -*- coding: utf-8 -*-
"""Openstack flavor."""

import logging
import operator
import re
from dataclasses import dataclass

import openstack


# pylint: disable=too-many-instance-attributes
@dataclass(order=True, frozen=True)
class Flavor:
    """Openstack flavor structure."""

    flavor_id: str
    name: str
    vcpus: int
    memory: int
    disk: int
    swap: int
    ephemeral: int
    description: str
    is_public: bool
    rxtx_factor: float
    extra_specs: dict

    def __hash__(self):
        return hash((self.name, self.flavor_id))


class Flavors:
    """Class to filter and sort flavors."""

    def __init__(self, *, all_flavor_list, cli_args=None):
        self._all_flavors = all_flavor_list

        self.filter_name = getattr(cli_args, "name", None)
        self.vcpus_min = getattr(cli_args, "vcpus_min", None)
        self.vcpus_max = getattr(cli_args, "vcpus_max", None)
        self.mem_min = getattr(cli_args, "memory_min", None)
        self.mem_max = getattr(cli_args, "memory_max", None)
        self.visibility = getattr(cli_args, "visibility", None)

    def get_filtered_flavors(self):
        filtered_list = self._all_flavors

        if self.filter_name:
            filtered_list = [
                f
                for f in filtered_list
                if re.search(self.filter_name, f.name, flags=re.IGNORECASE)
            ]
        if self.vcpus_min is not None:
            filtered_list = [f for f in filtered_list if f.vcpus >= self.vcpus_min]
        if self.vcpus_max is not None:
            filtered_list = [f for f in filtered_list if f.vcpus <= self.vcpus_max]
        if self.mem_min is not None:
            filtered_list = [f for f in filtered_list if f.memory >= self.mem_min]
        if self.mem_max is not None:
            filtered_list = [f for f in filtered_list if f.memory <= self.mem_max]

        if self.visibility == "public":
            filtered_list = [f for f in filtered_list if f.is_public]
        elif self.visibility == "private":
            filtered_list = [f for f in filtered_list if not f.is_public]

        return filtered_list

    @property
    def list_flavors(self):
        return self.get_filtered_flavors()

    def sort_flavors(self, column="name", reverse=False):
        return sorted(
            self.list_flavors, key=operator.attrgetter(column, "name"), reverse=reverse
        )


##############################################################################
# Return an openstack connection
##############################################################################
def get_openstack_connection(os_cloud):
    # disable openstacksdk logs
    openstack.enable_logging(debug=False)
    return openstack.connect(cloud=os_cloud)


##############################################################################
# Return a list withi with all flavors
##############################################################################
def get_all_flavors_list(os_conn):
    logging.debug("getting flavors")

    flavor_list = []
    for os_flavor in os_conn.compute.flavors():
        flavor_list.append(
            Flavor(
                flavor_id=os_flavor.id,
                name=os_flavor.name,
                vcpus=os_flavor.vcpus,
                memory=os_flavor.ram / 1024,
                disk=os_flavor.disk,
                swap=os_flavor.swap,
                ephemeral=os_flavor.ephemeral,
                description=os_flavor.description,
                is_public=os_flavor.is_public,
                rxtx_factor=os_flavor.rxtx_factor,
                extra_specs=os_flavor.extra_specs,
            )
        )
    return flavor_list


# vim: ts=4
