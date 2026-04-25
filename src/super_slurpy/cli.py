"""
Command-line interface for slurpy.

This module provides the main entry points for both the
headless processing commands and the optional interactive
graphical user interface (GUI).
"""

import sys
from pathlib import Path

import click

from super_slurpy.constants import EXIT_MISSING_DEPS, GUI_MISSING_ERR_MSG
from super_slurpy.model import SlurpyModel


@click.group()
def run_cli() -> None:
    """
    Super-Slurpy: CLI and GUI for Python version of SLURP.
    """
    pass


@run_cli.command()
@click.option(
    "--ultrasound",
    "-u",
    type=click.Path(exists=True),
    help="Path to a video file to open automatically.",
)
@click.option(
    "--seed",
    "-s",
    type=click.Path(exists=True),
    help="Path to a seed spline CSV file to load automatically.",
)
def gui(ultrasound: str | None, seed: str | None) -> None:
    """
    Launch the interactive PyQt GUI.
    """
    try:
        from super_slurpy.gui import launch_gui
    except ImportError:
        click.secho(
            message=GUI_MISSING_ERR_MSG,
            fg="red",
            err=True,
        )
        sys.exit(EXIT_MISSING_DEPS)

    click.echo(message="Starting GUI...")
    launch_gui(video_path=ultrasound, seed_path=seed)


@run_cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "--seed",
    "-s",
    type=click.Path(exists=True),
    help="Path to the seed spline CSV file.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output CSV path. Defaults to input_path with _tracked.csv suffix.",
)
def process(input_path: str, seed: str | None, output: str | None) -> None:
    """
    Batch process a file in headless mode.
    """
    click.echo(message=f"Processing {input_path} in headless mode...")

    video_path = Path(input_path)
    # Prefer config file in the same directory as the video
    model = SlurpyModel(config_dir=video_path.parent)

    if seed:
        try:
            model.load_seed_spline_file(file_path=seed)
        except Exception as e:
            click.secho(message=f"Error loading seed: {e}", fg="red", err=True)
            sys.exit(1)

    if not model.seed_spline:
        click.secho(
            message="Error: A seed spline is required for batch processing.",
            fg="red",
            err=True,
        )
        sys.exit(1)

    try:
        start_frame = model.open_video(file_path=input_path)

        # Apply the seed spline to the starting frame
        model.anchors = [list(pt) for pt in model.seed_spline]
        model.read_frame(frame_idx=start_frame)
        model.update_spline()

        click.echo(message=f"Starting tracking from frame {start_frame}...")
        model.run_tracking(start_idx=start_frame)

        out_path = output if output else str(
            video_path.with_name(f"{video_path.stem}_tracked.csv"))
        model.save_csv(file_path=out_path)
        click.secho(
            message=f"Successfully saved results to {out_path}", fg="green")

    except Exception as e:
        click.secho(
            message=f"Error during processing: {e}", fg="red", err=True)
        sys.exit(1)
