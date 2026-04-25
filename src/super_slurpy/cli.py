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
    Launch the interactive PyQt graphical user interface.

    Attempts to load optional GUI dependencies and launch the main
    application window. Gracefully alerts the user if dependencies
    are not installed.
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


def _process_single_video(
    video_path: Path,
    seed: str | None,
    output_path: Path | None
) -> None:
    """
    Process a single video file using the active contour model.

    Parameters
    ----------
    video_path : Path
        The path to the input video file.
    seed : str | None
        The path to the seed spline CSV file.
    output_path : Path | None
        The explicit output path for the tracked CSV.

    Returns
    -------
    None
    """
    click.echo(message=f"Processing {video_path} in headless mode...")

    # What: Initialize the model, favoring local directory configs.
    # Why: Ensures batch processing can use different params per folder.
    model = SlurpyModel(config_dir=video_path.parent)

    if seed:
        try:
            model.load_seed_spline_file(file_path=seed)
        except Exception as e:
            click.secho(
                message=f"Error loading seed for {video_path}: {e}",
                fg="red",
                err=True
            )
            # Return instead of sys.exit so batch directory loops continue
            return

    if not model.seed_spline:
        click.secho(
            message="Error: A seed spline is required for batch processing.",
            fg="red",
            err=True,
        )
        sys.exit(1)

    try:
        start_frame = model.open_video(file_path=str(video_path))

        # Apply the seed spline to the starting frame
        model.anchors = [list(pt) for pt in model.seed_spline]
        model.read_frame(frame_idx=start_frame)
        model.update_spline()

        click.echo(message=f"Starting tracking from frame {start_frame}...")
        model.run_tracking(start_idx=start_frame)

        # What: Resolve the final output path.
        # Why: Respect explicit targets or fallback to a standard suffix.
        out_path = output_path if output_path else video_path.with_name(
            f"{video_path.stem}_tracked.csv"
        )

        model.save_csv(file_path=str(out_path))
        click.secho(
            message=f"Successfully saved results to {out_path}",
            fg="green"
        )

    except Exception as e:
        click.secho(
            message=f"Error during processing {video_path}: {e}",
            fg="red",
            err=True
        )


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
    help=(
        "Output CSV path (single file) or directory (batch). "
        "Defaults to input_path with _tracked.csv suffix."
    ),
)
def process(input_path: str, seed: str | None, output: str | None) -> None:
    """
    Process video files without launching the GUI.

    INPUT_PATH can be a single video file or a directory containing
    multiple videos. If a directory is provided, it will scan for
    standard video formats (.mp4, .avi, .mkv) and process them
    sequentially.

    This command is ideal for scripting, background tasks, or mass
    evaluations.
    """
    target_path = Path(input_path)

    # What: Branch execution for single files vs entire folders.
    # Why: Reuses the same command gracefully for mass processing.
    if target_path.is_file():
        out_path = Path(output) if output else None
        _process_single_video(
            video_path=target_path,
            seed=seed,
            output_path=out_path
        )

    elif target_path.is_dir():
        click.echo(
            message=f"Scanning directory {target_path} for videos..."
        )

        # What: Enforce file extension screening.
        # Why: Prevents crashing when evaluating non-video data.
        valid_exts: tuple[str, ...] = (".mp4", ".avi", ".mkv")
        video_files = [
            p for p in target_path.iterdir()
            if p.is_file() and p.suffix.lower() in valid_exts
        ]

        if not video_files:
            click.secho(message="No video files found.", fg="yellow")
            return

        out_dir = Path(output) if output else None
        if out_dir and not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)

        for video_file in video_files:
            file_out = (
                out_dir / f"{video_file.stem}_tracked.csv"
                if out_dir else None
            )
            _process_single_video(
                video_path=video_file,
                seed=seed,
                output_path=file_out
            )
