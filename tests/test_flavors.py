# -*- coding: utf-8 -*-
"""test flavors module."""

from unittest.mock import Mock

from os_flavor_selector.flavors import Flavors


def test_filter_by_vcpu():
    myflavor = Flavors()
    myflavor.filter_by_vcpu = Mock(return_value=["a", "b", "c", "d"])
    myflavor.filter_by_mem = Mock(return_value=["b", "c", "e"])
    myflavor.filter_by_name = Mock(return_value=["a", "b", "c", "e"])

    assert sorted(myflavor.list_flavors) == sorted(["b", "c"])


# vim: ts=4
