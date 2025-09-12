# -*- coding: utf-8 -*-
"""Openstack flavor."""

import logging
import operator
from dataclasses import dataclass

import openstack

LOG = logging.getLogger(__name__)


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

    def __init__(
        self,
        *,
        filter_name=None,
        vcpus_min=None,
        vcpus_max=None,
        mem_min=None,
        mem_max=None,
        all_flavor_list=None,
    ):
        self.vcpus_min = vcpus_min
        self.vcpus_max = vcpus_max
        self.mem_min = mem_min
        self.mem_max = mem_max
        self.filter_name = filter_name
        self._all_flavors = all_flavor_list

    def get_filtered_flavors(self):
        filtered_list = self._all_flavors
        if self.filter_name:
            filtered_list = [f for f in filtered_list if self.filter_name in f.name]
        if self.vcpus_min is not None:
            filtered_list = [f for f in filtered_list if f.vcpus >= self.vcpus_min]
        if self.vcpus_max is not None:
            filtered_list = [f for f in filtered_list if f.vcpus <= self.vcpus_max]
        if self.mem_min is not None:
            filtered_list = [f for f in filtered_list if f.memory >= self.mem_min]
        if self.mem_max is not None:
            filtered_list = [f for f in filtered_list if f.memory <= self.mem_max]

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
def get_openstack_connection(args):
    # disable openstacksdk logs
    openstack.enable_logging(debug=False)
    return openstack.connect(options=args)


##############################################################################
# Return a instance of class Flavors with all flavors
##############################################################################
def get_flavors(os_conn):
    LOG.debug("getting flavors")

    flavor_list = []
    for os_flavor in os_conn.compute.flavors():
        flavor_list.append(
            Flavor(
                os_flavor.id,
                os_flavor.name,
                os_flavor.vcpus,
                os_flavor.ram / 1024,
                os_flavor.disk,
                os_flavor.swap,
                os_flavor.ephemeral,
                os_flavor.description,
                os_flavor.is_public,
                os_flavor.rxtx_factor,
                os_flavor.extra_specs,
            )
        )
    return Flavors(all_flavor_list=flavor_list)


# vim: ts=4
