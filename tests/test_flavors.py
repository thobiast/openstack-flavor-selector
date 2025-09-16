# -*- coding: utf-8 -*-
"""test flavors module."""

from argparse import Namespace

import pytest

from os_flavor_selector.flavors import Flavors


# pylint: disable=missing-class-docstring,too-few-public-methods
class DummyFlavor:
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(self, name, vcpus, memory, is_public=True, disk=0, extra_specs=None):
        self.name = name
        self.vcpus = vcpus
        self.memory = memory
        self.is_public = is_public
        self.disk = disk
        self.extra_specs = extra_specs or {}


@pytest.mark.parametrize(
    "name_re,vcpu_min,vcpu_max,mem_min,mem_max,expected",
    [
        (None, 1, 2, None, None, ["m1.small", "m1.medium"]),
        (None, 2, 2, None, None, ["m1.medium"]),
        (None, 2, 4, None, None, ["m1.medium", "m1.large", "c2.large"]),
        ("^m1\\.", 2, 4, None, None, ["m1.medium", "m1.large"]),
        ("^m1\\.", 2, 4, None, 8, ["m1.medium", "m1.large"]),
        ("large$", None, 4, 8, None, ["m1.large", "c2.large"]),
        ("large$", 4, 4, None, 8, ["m1.large"]),
        ("m1", 1, None, 3, 4, ["m1.medium"]),
        ("^m1\\.", 5, None, None, None, []),
    ],
)
# pylint: disable=too-many-arguments,too-many-positional-arguments
def test_filter_flavors_combined(
    name_re, vcpu_min, vcpu_max, mem_min, mem_max, expected
):
    flavors = [
        DummyFlavor("m1.small", vcpus=1, memory=2),
        DummyFlavor("m1.medium", vcpus=2, memory=4),
        DummyFlavor("m1.large", vcpus=4, memory=8),
        DummyFlavor("c2.large", vcpus=4, memory=16),
    ]

    args = Namespace(
        vcpus_min=vcpu_min,
        vcpus_max=vcpu_max,
        memory_min=mem_min,
        memory_max=mem_max,
        name=name_re,
        visibility="all",
    )

    flavors = Flavors(all_flavor_list=flavors, cli_args=args)
    result = sorted([f.name for f in flavors.get_filtered_flavors()])
    assert result == sorted(expected)


@pytest.mark.parametrize(
    "visibility,expected",
    [
        ("all", ["public.flavor", "private.flavor"]),
        ("public", ["public.flavor"]),
        ("private", ["private.flavor"]),
    ],
)
def test_filter_flavors_by_visibility(visibility, expected):
    flavors = [
        DummyFlavor("public.flavor", vcpus=1, memory=2, is_public=True),
        DummyFlavor("private.flavor", vcpus=1, memory=2, is_public=False),
    ]

    args = Namespace(
        vcpus_min=None,
        vcpus_max=None,
        memory_min=None,
        memory_max=None,
        name=None,
        visibility=visibility,
    )

    flavors = Flavors(all_flavor_list=flavors, cli_args=args)
    result = [f.name for f in flavors.get_filtered_flavors()]
    assert sorted(result) == sorted(expected)


@pytest.mark.parametrize(
    "extra_specs_filter,expected",
    [
        # subset (AND) semantics
        (
            {"hw:cpu_policy": "dedicated"},
            ["dedicated.flavor", "dedicated.large.flavor"],
        ),
        ({"hw:cpu_policy": "shared"}, ["shared.flavor"]),
        ({"trait:HW_CPU_X86_AVX2": "required"}, ["avx2.flavor"]),
        (
            {"hw:cpu_policy": "dedicated", "hw:mem_page_size": "large"},
            ["dedicated.large.flavor"],
        ),
        # no match
        ({"hw:cpu_policy": "invalid"}, []),
        # case-insensitive values
        (
            {"hw:cpu_policy": "DEDICATED"},
            ["dedicated.flavor", "dedicated.large.flavor"],
        ),
    ],
)
def test_filter_flavors_by_extra_specs(extra_specs_filter, expected):
    flavors = [
        DummyFlavor(
            "dedicated.flavor",
            vcpus=2,
            memory=4,
            extra_specs={"hw:cpu_policy": "dedicated"},
        ),
        DummyFlavor(
            "shared.flavor",
            vcpus=2,
            memory=4,
            extra_specs={"hw:cpu_policy": "shared"},
        ),
        DummyFlavor(
            "avx2.flavor",
            vcpus=2,
            memory=4,
            extra_specs={"trait:HW_CPU_X86_AVX2": "required"},
        ),
        DummyFlavor(
            "dedicated.large.flavor",
            vcpus=2,
            memory=4,
            extra_specs={"hw:cpu_policy": "dedicated", "hw:mem_page_size": "large"},
        ),
    ]

    args = Namespace(
        vcpus_min=None,
        vcpus_max=None,
        memory_min=None,
        memory_max=None,
        name=None,
        visibility="all",
    )

    f = Flavors(all_flavor_list=flavors, cli_args=args, extra_specs=extra_specs_filter)
    result = sorted([fl.name for fl in f.get_filtered_flavors()])
    assert result == sorted(expected)


# vim: ts=4
