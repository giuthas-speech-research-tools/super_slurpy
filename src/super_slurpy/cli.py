"""
Command-line interface for slurpy.

This module provides the main entry points for both the
headless processing commands and the optional interactive
graphical user interface (GUI).
"""

import sys

import click

# Adhering to separation of responsibilities by importing
# shared configuration and constants from a dedicated module.
from super_slurpy.constants import EXIT_MISSING_DEPS, GUI_MISSING_ERR_MSG


@click.group()
def run_cli() -> None:
    """
    Super-Slurpy: CLI and GUI for Python version of SLURP.

    This function acts as the main Click command group that
    binds all subcommands together.

    Returns
    -------
    None

    Examples
    --------
    >>> from super_slurpy.cli import run_cli
    >>> # Typically invoked via command line:
    >>> # $ slurpy --help
    """
    # The group function serves only as a router for Click
    # subcommands. Therefore, no execution logic is needed here.
    pass


@run_cli.command()
def gui() -> None:
    """
    Launch the interactive PyQt GUI.

    Attempts to load optional GUI dependencies and launch the
    main application window. Gracefully alerts the user if
    dependencies are not installed.

    Returns
    -------
    None

    Raises
    ------
    SystemExit
        Exits with an error code if required `[gui]` dependencies
        are missing.

    Examples
    --------
    >>> # Invoked via command line:
    >>> # $ slurpy gui
    """
    # We use a try-except block and a local, inline import here.
    # Why: This prevents an automatic `ImportError` from crashing
    # the entire CLI for headless users who skipped the GUI extras.
    try:
        from super_slurpy.gui import launch_gui
    except ImportError:
        # Use keyword arguments to print the centralized error
        # message in red and exit gracefully.
        click.secho(
            message=GUI_MISSING_ERR_MSG,
            fg="red",
            err=True,
        )
        sys.exit(EXIT_MISSING_DEPS)

    # Acknowledge the launch using keyword arguments.
    click.echo(message="Starting GUI...")
    launch_gui()


@run_cli.command()
@click.argument("input_path")
def process(input_path: str) -> None:
    """
    Batch process a file in headless mode.

    Processes a given input file without launching the GUI.
    Suitable for scripting and background tasks.

    Parameters
    ----------
    input_path : str
        The file path pointing to the data to be processed.

    Returns
    -------
    None

    Examples
    --------
    >>> # Invoked via command line:
    >>> # $ slurpy process /path/to/data.ext
    """
    # Print the initialization status. Keyword arguments are
    # used explicitly per project guidelines.
    click.echo(
        message=f"Processing {input_path} in headless mode..."
    )
