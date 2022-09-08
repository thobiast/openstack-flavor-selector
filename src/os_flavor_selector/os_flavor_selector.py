#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Openstack flavor selector."""


import argparse
import json
import logging
from dataclasses import asdict

from rich.console import Console
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from .flavors import get_flavors, get_openstack_connection
from .utils import setup_logging

LOG = setup_logging()


##############################################################################
# Parses the command line
##############################################################################
def cli_args():
    epilog = """
    Example of use:
        %(prog)s
        %(prog)s --vcpus-min 4
        %(prog)s --vcpus-min 4 --vcpus-max 8
        %(prog)s --vcpus-min 4 --vcpus-max 8 --output json
    """
    # Create the argparse object and define global options
    parser = argparse.ArgumentParser(
        description="A tool to filter OpenStack flavors based on resource criteria",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", dest="debug", help="debug flag"
    )
    parser.add_argument(
        "--output",
        default="interactive",
        choices=["interactive", "text", "json"],
        help="Output format (default: %(default)s)",
    )
    parser.add_argument("--memory-min", type=int, help="Minimum Amount of Memory")
    parser.add_argument("--memory-max", type=int, help="Maximum Amount of Memory")
    parser.add_argument("--vcpus-min", type=int, help="Minimum Amount of VCPUs")
    parser.add_argument("--vcpus-max", type=int, help="Maximum Amount of VCPUs")
    parser.add_argument("--name", help="Filter by name")

    return parser


#############################################################################
# Return Rich table
#############################################################################
def create_table(*, flavors, long, sort_column, sort_order):
    LOG.debug("long: %s sort_column: %s sort_order: %s", long, sort_column, sort_order)

    table = Table(title="OpenStack Flavors", show_edge=False)

    table.add_column("ID", style="green", no_wrap=True)
    table.add_column("Name", style="magenta", no_wrap=True)
    table.add_column("VCPUs", justify="right", style="cyan")
    table.add_column("Mem (GiB)", justify="right", style="cyan")
    table.add_column("Disk", justify="right", style="cyan")
    table.add_column("Swap", justify="right", style="cyan")
    table.add_column("Ephemeral", justify="right", style="cyan")
    table.add_column("Is_public", justify="right", style="cyan")
    if long:
        table.add_column("Description", justify="right", style="cyan")
        table.add_column("rxtx_factor", justify="right", style="cyan")
        table.add_column("extra_specs", justify="right", style="cyan")

    for flavor in flavors.sort_flavors(sort_column, sort_order):
        row = [
            flavor.flavor_id,
            flavor.name,
            str(flavor.vcpus),
            str(flavor.memory),
            str(flavor.disk),
            str(flavor.swap),
            str(flavor.ephemeral),
            str(flavor.is_public),
        ]
        if long:
            row.extend(
                [flavor.description, str(flavor.rxtx_factor), str(flavor.extra_specs)]
            )
        table.add_row(*row)

    return table


#############################################################################
# Helper function to ask user int
# Return None if number is less than 1
#############################################################################
def ask_user_int(message):
    user_number = IntPrompt.ask(message)
    return user_number if user_number > 0 else None


#############################################################################
# Run interactive mode
#############################################################################
def interactive(flavors):
    sort_column_map = {"1": "name", "2": "vcpus", "3": "memory"}
    sort_by_column = "1"
    sort_order_map = {"asc": False, "desc": True}
    sort_order = "asc"

    console = Console()
    long = False
    user_option = None
    while user_option != "q":
        if not LOG.isEnabledFor(logging.DEBUG):
            console.clear()

        table = create_table(
            flavors=flavors,
            long=long,
            sort_column=sort_column_map[sort_by_column],
            sort_order=sort_order_map[sort_order],
        )

        console.print(table, justify="center")
        console.rule(
            f"[red]Filtering flavors ("
            f"name:[bold magenta]{flavors.filter_name}[/]/"
            f"VCPUs:[bold magenta]{flavors.vcpus_min}-{flavors.vcpus_max}[/]/"
            f"Mem:[bold magenta]{flavors.mem_min}-{flavors.mem_max}[/])  "
            f"[red]Sorting by:[bold magenta]{sort_column_map[sort_by_column]}[/]  "
            f"[red]Sort order:[bold magenta]{sort_order}[/]  "
            f"[red]Show all details:[bold magenta]{long}[/]",
            align="center",
        )
        console.print(
            "[white]1 [bold blue]Sort by Name  "
            "[white]2 [bold blue]Sort by VCPUs  "
            "[white]3 [bold blue]Sort by Memory "
            "[white]f [bold blue]Change Filter "
            "[white]o [bold blue]Sort order  "
            "[white]d [bold blue]Show details  "
            "[white]q [bold blue]Quit[/]"
        )
        user_option = Prompt.ask(
            "Choose the option:", choices=["1", "2", "3", "f", "o", "d", "q"]
        )
        if user_option == "f":
            filter_type = Prompt.ask(
                "Choose filter [bold]N[/]ame, V[bold]C[/]PUs or [bold]M[/]emory",
                choices=["n", "c", "m"],
            )
            if filter_type == "n":
                flavors.filter_name = Prompt.ask("Enter name to filter")
            if filter_type == "c":
                flavors.vcpus_min = ask_user_int("Enter VCPUs Minimum (0 to reset)")
                flavors.vcpus_max = ask_user_int("Enter VCPUs Maximum (0 to reset)")
            if filter_type == "m":
                flavors.mem_min = ask_user_int("Enter Memory Minimum (0 to reset)")
                flavors.mem_max = ask_user_int("Enter Memory Maximum (0 to reset)")
        elif user_option == "o":
            sort_order = "asc" if sort_order == "desc" else "desc"
        elif user_option == "d":
            long = not long
        else:
            sort_by_column = user_option


##############################################################################
# Main
##############################################################################
def main():

    args = cli_args()
    os_conn = get_openstack_connection(args)

    # parser arguments
    args_parsed = args.parse_args()
    # enable debug
    if not args_parsed.debug:
        logging.disable()

    flavors = get_flavors(os_conn)

    # Configure flavors with cli filter parameters
    flavors.vcpus_min = args_parsed.vcpus_min
    flavors.vcpus_max = args_parsed.vcpus_max
    flavors.mem_min = args_parsed.memory_min
    flavors.mem_max = args_parsed.memory_max
    flavors.filter_name = args_parsed.name

    if args_parsed.output == "json":
        for flavor in flavors.list_flavors:
            print(json.dumps(vars(flavor)))
    elif args_parsed.output == "text":
        for flavor in flavors.list_flavors:
            print(asdict(flavor))
    else:
        interactive(flavors)


##############################################################################
# Run from command line
##############################################################################
if __name__ == "__main__":
    main()

# vim: ts=4
