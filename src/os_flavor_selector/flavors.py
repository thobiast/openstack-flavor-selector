# -*- coding: utf-8 -*-
"""Openstack flavor - filtering and retrieval utilities"""

import logging
import operator
import re
from dataclasses import dataclass

import openstack

from .utils import is_valid_regex


# pylint: disable=too-many-instance-attributes
@dataclass(order=True, frozen=True)
class Flavor:
    """Dataclass representing an OpenStack flavor."""

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
    """Manage a list of Flavor objects with filtering and sorting capabilities."""

    def __init__(self, *, all_flavor_list, cli_args=None, extra_specs=None):
        self._all_flavors = all_flavor_list

        self.filter_name = getattr(cli_args, "name", None)
        self.vcpus_min = getattr(cli_args, "vcpus_min", None)
        self.vcpus_max = getattr(cli_args, "vcpus_max", None)
        self.mem_min = getattr(cli_args, "memory_min", None)
        self.mem_max = getattr(cli_args, "memory_max", None)
        self.visibility = getattr(cli_args, "visibility", None)
        self.extra_specs = extra_specs or {}

    # pylint: disable=too-many-return-statements
    def _matches_filters(self, flavor):
        """
        Check whether a given flavor matches all defined filter criteria.

        Args:
            flavor (Flavor): The flavor to evaluate.

        Returns:
            bool: True if the flavor satisfies all active filters, False otherwise.
        """
        # name
        if self.filter_name:
            if not re.search(self.filter_name, flavor.name, flags=re.IGNORECASE):
                return False
        # vcpus
        if self.vcpus_min is not None and flavor.vcpus < self.vcpus_min:
            return False
        if self.vcpus_max is not None and flavor.vcpus > self.vcpus_max:
            return False

        # memory
        if self.mem_min is not None and flavor.memory < self.mem_min:
            return False
        if self.mem_max is not None and flavor.memory > self.mem_max:
            return False

        # visibility
        if self.visibility == "public" and not flavor.is_public:
            return False
        if self.visibility == "private" and flavor.is_public:
            return False

        # extra_specs
        if self.extra_specs:
            for key, value in self.extra_specs.items():
                expected_value_str = str(value).lower()
                flavor_value_str = str(flavor.extra_specs.get(key)).lower()
                if flavor_value_str != expected_value_str:
                    return False

        return True

    def get_filtered_flavors(self):
        """
        Returns a list of flavors that match all defined filter criteria.

        Returns:
            list[Flavor]: A list of flavors that satisfy all filter conditions.
        """
        if self.filter_name and not is_valid_regex(self.filter_name):
            logging.error("Invalid regex for name filter: %s", self.filter_name)
            return []

        return [f for f in self._all_flavors if self._matches_filters(f)]

    def sort_flavors(self, column="name", reverse=False):
        """
        Return filtered flavors sorted by the specified attribute.

        Args:
            column (str): Attribute name to sort by (e.g., "name", "vcpus", "memory").
                Defaults to "name".
            reverse (bool): If True, sort in descending order. Defaults to False.

        Returns:
            list[Flavor]: A list of filtered and sorted flavors.
        """
        return sorted(
            self.get_filtered_flavors(),
            key=operator.attrgetter(column, "name"),
            reverse=reverse,
        )


##############################################################################
# Return an openstack connection
##############################################################################
def get_openstack_connection(os_cloud):
    # disable openstacksdk logs
    openstack.enable_logging(debug=False)
    return openstack.connect(cloud=os_cloud)


##############################################################################
# Return a list with with all flavors
##############################################################################
def get_all_flavors(os_conn):
    """
    Retrieve all flavors from OpenStack environment.

    Args:
        os_conn (openstack.connection.Connection): An OpenStack connection.

    Returns:
        list[Flavor]: A list of Flavor objects
    """
    logging.debug("getting flavors")

    flavor_list = []
    for os_flavor in os_conn.compute.flavors():
        flavor_list.append(
            Flavor(
                flavor_id=os_flavor.id,
                name=os_flavor.name,
                vcpus=os_flavor.vcpus,
                memory=os_flavor.ram // 1024,
                disk=os_flavor.disk,
                swap=os_flavor.swap,
                ephemeral=os_flavor.ephemeral,
                description=os_flavor.description,
                is_public=os_flavor.is_public,
                rxtx_factor=os_flavor.rxtx_factor,
                extra_specs=os_flavor.extra_specs or {},
            )
        )
    return flavor_list


# vim: ts=4
