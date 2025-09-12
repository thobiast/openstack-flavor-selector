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

from .flavors import Flavors, get_all_flavors_list, get_openstack_connection
from .utils import setup_logging

RICH_TABLE_COLUMNS_BASIC = [
    {"header": "ID", "attr": "flavor_id", "style": "green", "no_wrap": True},
    {"header": "Name", "attr": "name", "style": "magenta", "no_wrap": True},
    {"header": "VCPUs", "attr": "vcpus", "style": "cyan", "justify": "right"},
    {"header": "Mem (GiB)", "attr": "memory", "style": "cyan", "justify": "right"},
    {"header": "Disk", "attr": "disk", "style": "cyan", "justify": "right"},
    {"header": "Swap", "attr": "swap", "style": "cyan", "justify": "right"},
    {"header": "Ephemeral", "attr": "ephemeral", "style": "cyan", "justify": "right"},
    {"header": "Is_public", "attr": "is_public", "style": "cyan", "justify": "right"},
]

RICH_TABLE_COLUMNS_EXTRA = [
    {
        "header": "Description",
        "attr": "description",
        "style": "cyan",
        "justify": "right",
    },
    {
        "header": "rxtx_factor",
        "attr": "rxtx_factor",
        "style": "cyan",
        "justify": "right",
    },
    {
        "header": "extra_specs",
        "attr": "extra_specs",
        "style": "cyan",
        "justify": "right",
    },
]


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
        "--os-cloud",
        help=(
            "Name of the cloud to load from clouds.yaml. "
            "(Default '%(default)s', which uses OS_* env vars)"
        ),
        type=str,
        default="envvars",
        required=False,
    )
    parser.add_argument(
        "--output",
        default="interactive",
        choices=["interactive", "text", "json"],
        help="Output format (default: %(default)s)",
    )
    parser.add_argument(
        "--visibility",
        default="all",
        choices=["all", "public", "private"],
        help="Filter by flavor visibility (default: %(default)s)",
    )
    parser.add_argument("--memory-min", type=int, help="Minimum Amount of Memory")
    parser.add_argument("--memory-max", type=int, help="Maximum Amount of Memory")
    parser.add_argument("--vcpus-min", type=int, help="Minimum Amount of VCPUs")
    parser.add_argument("--vcpus-max", type=int, help="Maximum Amount of VCPUs")
    parser.add_argument(
        "--name", help="Filter by name using a regular expression (case-insensitive)"
    )

    return parser.parse_args()


#############################################################################
# Return Rich table
#############################################################################
def create_table(*, flavors, long, sort_column, sort_order):
    logging.debug(
        "long: %s sort_column: %s sort_order: %s", long, sort_column, sort_order
    )

    table = Table(title="OpenStack Flavors", show_edge=False)

    table_cols = RICH_TABLE_COLUMNS_BASIC
    if long:
        table_cols = RICH_TABLE_COLUMNS_BASIC + RICH_TABLE_COLUMNS_EXTRA

    for col in table_cols:
        table.add_column(
            col["header"],
            style=col["style"],
            justify=col.get("justify"),
            no_wrap=col.get("no_wrap"),
        )

    sorted_flavors = flavors.sort_flavors(sort_column, sort_order)
    for flavor in sorted_flavors:
        row_data = [str(getattr(flavor, col["attr"])) for col in table_cols]
        table.add_row(*row_data)
    return table


#############################################################################
# Helper function to ask user int
# Return None if number is less than 1
#############################################################################
def ask_user_int(message):
    user_number = IntPrompt.ask(message, default=0)
    return user_number if user_number > 0 else None


#############################################################################
# Helper function to change prompt and change filter criteria
#############################################################################
def handle_filter_prompt(flavors):
    filter_type = Prompt.ask(
        "Choose filter [bold]N[/]ame, V[bold]C[/]PUs, "
        "[bold]M[/]emory or [bold]V[/]isibility",
        choices=["n", "c", "m", "v"],
    )
    if filter_type == "n":
        flavors.filter_name = Prompt.ask("Enter name to filter")
    if filter_type == "c":
        flavors.vcpus_min = ask_user_int("Enter VCPUs Minimum (0 to reset)")
        flavors.vcpus_max = ask_user_int("Enter VCPUs Maximum (0 to reset)")
    if filter_type == "m":
        flavors.mem_min = ask_user_int("Enter Memory Minimum (0 to reset)")
        flavors.mem_max = ask_user_int("Enter Memory Maximum (0 to reset)")
    if filter_type == "v":
        flavors.visibility = Prompt.ask(
            "Choose visibility", choices=["all", "public", "private"], default="all"
        )


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
    while True:
        if logging.getLogger().getEffectiveLevel() != logging.DEBUG:
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
            f"Mem:[bold magenta]{flavors.mem_min}-{flavors.mem_max}[/]/"
            f"Visibility:[bold magenta]{flavors.visibility}[/])  "
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
        if user_option == "q":
            break
        if user_option == "f":
            handle_filter_prompt(flavors)
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

    log_level = logging.DEBUG if args.debug else logging.WARNING
    setup_logging(log_level)
    logging.debug("CMD line args: %s", args)

    os_conn = get_openstack_connection(args.os_cloud)

    all_flavors_list = get_all_flavors_list(os_conn)

    flavors = Flavors(all_flavor_list=all_flavors_list, cli_args=args)

    if args.output == "json":
        list_of_dicts = [asdict(f) for f in flavors.list_flavors]
        print(json.dumps(list_of_dicts))
    elif args.output == "text":
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
