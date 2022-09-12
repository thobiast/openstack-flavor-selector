# os-flavor-selector - A tool to filter OpenStack flavors based on resource criteria

[![Build and Test](https://github.com/thobiast/openstack-flavor-selector/actions/workflows/build.yml/badge.svg?event=push)](https://github.com/thobiast/openstack-flavor-selector/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


# About
os-flavor-selector is a tool filter OpenStack flavors. When there are many flavors available,
it is sometimes dificult to find the correct one that fills our requirements.
The os-flavor-selector helps to navigate and filter the flavors.


# Example

```bash
$ os-flavor-selector --help
$ os-flavor-selector
$ os-flavor-selector --vcpus-min 4 --vcpus-max 8
$ os-flavor-selector --vcpus-min 4 --vcpus-max 8 --output json
$ os-flavor-selector --vcpus-min 4 --memory-max 16 --output text
```
![Interactive GIF](img/demo.gif)

# Installation
```bash
$ pip install os-flavor-selector
```

# Development mode
```bash
$ pip install -e .
```
