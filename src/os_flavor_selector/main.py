#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""main.py - CLI for the OpenStack flavor selector."""


import argparse
import json
import logging
from dataclasses import asdict

from rich.console import Console
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from .flavors import Flavors, get_all_flavors, get_openstack_connection
from .utils import is_valid_regex, setup_logging

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
        "--extra-spec",
        action="append",
        metavar="KEY=VALUE",
        help=(
            "Filter by extra_specs (can be used multiple times). "
            "Example: --extra-spec hw:cpu_policy=dedicated "
            "--extra-spec trait:HW_CPU_X86_AVX2=required"
        ),
    )
    parser.add_argument(
        "--name", help="Filter by name using a regular expression (case-insensitive)"
    )

    return parser.parse_args()


#############################################################################
# Return Rich table
#############################################################################
def create_table(*, flavors, show_details, sort_column, reverse):
    """Build and return a Rich table of (filtered, sorted) flavors.

    Args:
        flavors (Flavors): A `Flavors` instance
        show_details (bool): If True, include extra columns
        sort_column (str): Attribute name to sort by (e.g., "name", "vcpus")
        reverse (bool): Sort descending if True, ascending if False.

    Returns:
        rich.table.Table: A fully populated Rich table ready to render.
    """
    logging.debug(
        "show_details: %s sort_column: %s reverse: %s",
        show_details,
        sort_column,
        reverse,
    )

    table = Table(title="OpenStack Flavors", show_edge=False)

    table_cols = RICH_TABLE_COLUMNS_BASIC[:]
    if show_details:
        table_cols.extend(RICH_TABLE_COLUMNS_EXTRA)

    for col in table_cols:
        table.add_column(
            col["header"],
            style=col["style"],
            justify=col.get("justify"),
            no_wrap=col.get("no_wrap"),
        )

    sorted_flavors = flavors.sort_flavors(sort_column, reverse)
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
# Helper function to renders the status bar at the bottom of the screen
#############################################################################
def display_status_rule(console, flavors, table_state):
    """Render a one-line status rule summarizing active filters and sort state.

    Args:
        console (rich.console.Console): Console used to render the rule.
        flavors (Flavors): A `Flavors` instance
        table_state (dict): UI state with keys:
            - "sort_column" (str): Current sort column.
            - "sort_order" (str): "asc" or "desc".
            - "long" (bool): Whether detailed columns are shown.

    Side Effects:
        Prints a centered rule line to the provided console.
    """
    extra_specs_str = ",".join(
        f"{key}={value}" for key, value in flavors.extra_specs.items()
    )
    status = (
        f"[red]Filtering flavors ("
        f"name:[bold magenta]{flavors.filter_name}[/]/"
        f"VCPUs:[bold magenta]{flavors.vcpus_min}-{flavors.vcpus_max}[/]/"
        f"Mem:[bold magenta]{flavors.mem_min}-{flavors.mem_max}[/]/"
        f"Visibility:[bold magenta]{flavors.visibility}[/]/"
        f"Extra Specs:[bold magenta]{extra_specs_str or None}[/])  "
        f"[red]Sorting by:[bold magenta]{table_state['sort_column']}[/]  "
        f"[red]Sort order:[bold magenta]{table_state['sort_order']}[/]  "
        f"[red]Show details:[bold magenta]{table_state['long']}[/]"
    )
    console.rule(status, align="center")


#############################################################################
# Helper function to change prompt and change filter criteria
#############################################################################
def handle_filter_prompt(flavors, console):
    """Interactively update filter criteria for flavors.

    Prompts the user to select which filter to change (name, vCPUs, memory,
    visibility, or extra_specs) and updates the `flavors` instance accordingly.

    Args:
        flavors (Flavors): A `Flavors` instance
        console (rich.console.Console): Console used for prompts/feedback.

    Raises:
        None. Invalid inputs are handled by prompting again or clearing the filter.
    """
    filter_type = Prompt.ask(
        "Choose filter [bold]N[/]ame, V[bold]C[/]PUs, "
        "[bold]M[/]emory, [bold]V[/]isibility "
        "or [bold]E[/]xtra specs",
        choices=["n", "c", "m", "v", "e"],
    )
    if filter_type == "n":
        while True:
            pattern = Prompt.ask(
                "Enter name to filter [dim](Press Enter to clear the filter)[/]"
            )
            if not pattern.strip():
                flavors.filter_name = None
                break
            if is_valid_regex(pattern):
                flavors.filter_name = pattern
                break
            console.print("[red]Invalid regex. Please try again.[/]")
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
    if filter_type == "e":
        current_specs_str = ",".join(f"{k}={v}" for k, v in flavors.extra_specs.items())
        while True:
            prompt = (
                "Current extra specs: "
                f"[bold]{current_specs_str or None}[/]\n"
                "Enter new specs as a comma-separated list (e.g., key1=val1,key2=val2) "
                "[dim](Press Enter to clear the filter)[/]"
            )
            extra_specs = Prompt.ask(prompt)
            if not extra_specs.strip():
                flavors.extra_specs.clear()
                break
            try:
                new_specs = {}
                for spec in extra_specs.split(","):
                    key, value = spec.split("=", 1)
                    new_specs[key.strip()] = value.strip()
                flavors.extra_specs = new_specs
                break
            except ValueError:
                console.print("[red]Invalid format. Please use KEY=VALUE.[/]")


#############################################################################
# Run interactive mode
#############################################################################
def interactive(flavors):
    """
    Run the interactive to browse, filter, and sort flavors.

    Args:
        flavors (Flavors): Data source and mutable filter state.
    """
    sort_column_map = {"1": "name", "2": "vcpus", "3": "memory"}
    sort_order_map = {"asc": False, "desc": True}
    table_state = {"long": False, "sort_order": "asc", "sort_column": "name"}

    console = Console()
    user_option = None
    while True:
        if logging.getLogger().getEffectiveLevel() != logging.DEBUG:
            console.clear()

        table = create_table(
            flavors=flavors,
            show_details=table_state["long"],
            sort_column=table_state["sort_column"],
            reverse=sort_order_map[table_state["sort_order"]],
        )

        console.print(table, justify="center")
        display_status_rule(console, flavors, table_state)
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
            handle_filter_prompt(flavors, console)
        elif user_option == "o":
            table_state["sort_order"] = (
                "desc" if table_state["sort_order"] == "asc" else "asc"
            )
        elif user_option == "d":
            table_state["long"] = not table_state["long"]
        else:
            table_state["sort_column"] = sort_column_map[user_option]


##############################################################################
# Main
##############################################################################
def main():

    args = cli_args()

    log_level = logging.DEBUG if args.debug else logging.WARNING
    setup_logging(log_level)
    logging.debug("CMD line args: %s", args)

    # Normalize extra-specs into dict
    extra_specs = {}
    if args.extra_spec:
        try:
            for spec in args.extra_spec:
                key, value = spec.split("=", 1)
                extra_specs[key.strip()] = value.strip()
        except ValueError:
            print("Error: --extra-spec must be in KEY=VALUE format.")
            return

    os_conn = get_openstack_connection(args.os_cloud)

    all_flavors_list = get_all_flavors(os_conn)

    flavors = Flavors(
        all_flavor_list=all_flavors_list, cli_args=args, extra_specs=extra_specs
    )

    if args.output == "json":
        list_of_dicts = [asdict(f) for f in flavors.get_filtered_flavors()]
        print(json.dumps(list_of_dicts))
    elif args.output == "text":
        for flavor in flavors.get_filtered_flavors():
            print(asdict(flavor))
    else:
        interactive(flavors)


##############################################################################
# Run from command line
##############################################################################
if __name__ == "__main__":
    main()

# vim: ts=4
