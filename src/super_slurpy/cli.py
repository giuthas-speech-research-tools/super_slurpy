"""
Command-line interface for slurpy.

This module provides the main entry points for both the
headless processing commands and the optional interactive
graphical user interface (GUI).
"""

import sys
from pathlib import Path

import click
from tqdm import tqdm

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
    output_path: Path | None = None,
    method: str = "snake"
) -> Path:
    """
    Execute headless sequence tracking for a single video.

    Parameters
    ----------
    video_path : pathlib.Path
        The absolute or relative path to the input video.
    seed : str
        The path to the seed spline CSV file.
    output_path : pathlib.Path | None, optional
        Where to save the results. If None, saves next to the video.
    method : str, optional
        The tracking algorithm to apply ('snake' or 'particle').
        Defaults to 'snake'.

    Returns
    -------
    Path
        The path where the .csv was saved
    """
    # What: Initialize the model, favoring local directory configs.
    # Why: Ensures batch processing can use different params per folder.
    model = SlurpyModel(config_dir=video_path.parent)

    if seed is not None:
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

    model.open_video(file_path=str(video_path))

    # Determine target starting frame based on config
    start_idx: int = 0
    if model.config.gui.default_frame is not None:
        start_idx = model.config.gui.default_frame
    elif model.config.gui.proportional_frame is not None:
        start_idx = int(
            (model.total_frames - 1) * model.config.gui.proportional_frame
        )

    match method:
        case "particle":
            tracking_generator = model.run_particle_tracking(
                start_idx=start_idx)
        case "snake":
            tracking_generator = model.run_snake_tracking(start_idx=start_idx)
        case _:
            click.secho(
                message=f"Unrecognised tracking method: {method}", fg="red")
            sys.exit()

    # tracking_generator does the work while tqdm provides a progress bar.
    for _ in tqdm(
        iterable=tracking_generator,
        total=model.total_frames,
        desc=video_path.name,
        unit="frames",
        leave=False
    ):
        pass

    # Resolve output path
    if output_path is None:
        output_path = video_path.with_name(
            f"{video_path.stem}_tracked.csv"
        )

    model.save_csv(file_path=str(output_path))
    return output_path


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
        "Target directory for mass processing, "
        "or target file for single files."
    ),
)
@click.option(
    "--method",
    "-m",
    type=click.Choice(choices=["snake", "particle"], case_sensitive=False),
    default="snake",
    show_default=True,
    help="The tracking algorithm to execute.",
)
def track(
    input_path: str,
    seed: str | None,
    output: str | None,
    method: str
) -> None:
    """
    Headless batch tracking of ultrasound sequence boundaries.

    INPUT_PATH can be a direct path to a video file (.mp4, .avi) or a
    directory containing multiple videos to evaluate in sequence.

    SEED must point to a valid comma separated seed spline file.
    Ideal for scripting, background tasks, or mass evaluations.
    """
    target_path = Path(input_path)

    # What: Branch execution for single files vs entire folders.
    # Why: Reuses the same command gracefully for mass processing.
    if target_path.is_file():
        out_path = Path(output) if output else None
        out_path = _process_single_video(
            video_path=target_path,
            seed=seed,
            output_path=out_path,
            method=method
        )
        written_files: list[Path] = [out_path,]

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

        written_files: list[Path] = []
        for video_file in tqdm(
            iterable=video_files,
            desc="Batch processing videos",
            unit="video"
        ):
            file_out = (
                out_dir / f"{video_file.stem}_tracked.csv"
                if out_dir else None
            )
            written_file = _process_single_video(
                video_path=video_file,
                seed=seed,
                output_path=file_out,
                method=method
            )
            written_files.append(written_file)

    click.secho(
        message="\nBatch processing complete. Generated files:",
        fg="green",
        bold=True
    )
    for f in written_files:
        click.echo(message=f"  - {f.resolve()}")
