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
        mem_max=None
    ):
        self.vcpus_min = vcpus_min
        self.vcpus_max = vcpus_max
        self.mem_min = mem_min
        self.mem_max = mem_max
        self.filter_name = filter_name
        self.flavors = []

    def add_flavor(self, *args):
        LOG.debug("adding flavors: %s", args)
        self.flavors.append(Flavor(*args))

    def filter_by_vcpu(self):
        tmp_flavors = self.flavors
        if self.vcpus_min:
            tmp_flavors = [i for i in tmp_flavors if i.vcpus >= self.vcpus_min]
        if self.vcpus_max:
            tmp_flavors = [i for i in tmp_flavors if i.vcpus <= self.vcpus_max]

        return tmp_flavors

    def filter_by_mem(self):
        tmp_flavors = self.flavors
        if self.mem_min:
            tmp_flavors = [i for i in tmp_flavors if i.memory >= self.mem_min]
        if self.mem_max:
            tmp_flavors = [i for i in tmp_flavors if i.memory <= self.mem_max]

        return tmp_flavors

    def filter_by_name(self):
        if self.filter_name:
            return [i for i in self.flavors if self.filter_name in i.name]
        return self.flavors

    @property
    def list_flavors(self):
        f_cpu = self.filter_by_vcpu()
        f_mem = self.filter_by_mem()
        f_name = self.filter_by_name()
        return list(set(f_cpu) & set(f_mem) & set(f_name))

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
# Return list with flavors
##############################################################################
def get_flavors(os_conn):
    LOG.debug("getting flavors")

    flavors = Flavors()
    for os_flavor in os_conn.compute.flavors():
        flavors.add_flavor(
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
    return flavors


# vim: ts=4
