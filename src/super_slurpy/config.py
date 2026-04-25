"""
Configuration management for Super-Slurpy.

Handles the loading of the YAML configuration file from multiple
potential fallback locations and validates it using Pydantic.

Examples
--------
>>> from super_slurpy.config import load_config
>>> from pathlib import Path
>>> config = load_config(config_dir=Path("/path/to/data"))
>>> print(config.gui.proportional_frame)
0.5
"""

import importlib.resources
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from super_slurpy.constants import (
    CONFIG_FILENAME,
    USER_DIR_NAME,
)


class GuiConfig(BaseModel):
    """
    Configuration model for the Graphical User Interface.

    Attributes
    ----------
    default_frame : int | None
        The absolute frame number to start on, defaults to None.
    proportional_frame : float | None
        The proportional position to start on (0.0 to 1.0),
        defaults to 0.5.
    seed_spline_file : str | None
        Path or filename of the seed spline file, defaults to None.
    """

    default_frame: int | None = None
    proportional_frame: float | None = 0.5
    seed_spline_file: str | None = None


class SnakeConfig(BaseModel):
    """
    Configuration model for the Snake active contour algorithm.

    Attributes
    ----------
    alpha : float
        Continuity weight, defaults to 0.1.
    lambda1 : float
        Smoothness weight, defaults to 0.5.
    band_penalty : float
        Penalty for venturing outside the target band, defaults to 10.0.
    """

    alpha: float = 0.1
    lambda1: float = 0.5
    band_penalty: float = 10.0


class ParticleConfig(BaseModel):
    """
    Configuration model for Particle Filter tracking.

    Attributes
    ----------
    num_particles : int
        Number of particles to generate, defaults to 50.
    percent_var : float
        Variance percentage for PCA shape model, defaults to 0.98.
    noise_scale : float
        Scale of the noise applied to particles, defaults to 1.0.
    """

    num_particles: int = 50
    percent_var: float = 0.98
    noise_scale: float = 1.0


class SlurpyConfig(BaseModel):
    """
    Root configuration model for the application.

    Attributes
    ----------
    gui : GuiConfig
        Nested configuration for the GUI.
    snake : SnakeConfig
        Nested configuration for the algorithm.
    """

    gui: GuiConfig = Field(default_factory=GuiConfig)
    particle: ParticleConfig = Field(default_factory=ParticleConfig)
    snake: SnakeConfig = Field(default_factory=SnakeConfig)


def load_config(config_dir: Path | None = None) -> SlurpyConfig:
    """
    Load and validate the YAML configuration file.

    This function attempts to find the configuration file in the
    following order of precedence:
    1. The explicitly provided `config_dir` (e.g., video directory).
    2. Current working directory (cwd).
    3. User's home directory under `~/.slurpy/`.
    4. Bundled package resources via `importlib`.

    Parameters
    ----------
    config_dir : Path | None, optional
        A specific directory to check first for the configuration
        file. Defaults to None.

    Returns
    -------
    SlurpyConfig
        The validated configuration object populated with YAML data
        or default values if no file/data is found.

    Examples
    --------
    >>> from super_slurpy.config import load_config
    >>> from pathlib import Path
    >>> config = load_config(config_dir=Path("/path/to/data"))
    >>> print(config.gui.proportional_frame)
    0.5
    """
    raw_config: dict[str, Any] = {}

    # 1. Check explicitly provided directory (e.g., where video is)
    if config_dir is not None and (config_dir / CONFIG_FILENAME).exists():
        target_path: Path = config_dir / CONFIG_FILENAME
        with open(file=target_path, mode="r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(stream=f) or {}

    # 2. Check current working directory
    elif (Path.cwd() / CONFIG_FILENAME).exists():
        cwd_path: Path = Path.cwd() / CONFIG_FILENAME
        with open(file=cwd_path, mode="r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(stream=f) or {}

    # 3. Check user's home directory
    elif (Path.home() / USER_DIR_NAME / CONFIG_FILENAME).exists():
        user_path: Path = Path.home() / USER_DIR_NAME / CONFIG_FILENAME
        with open(file=user_path, mode="r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(stream=f) or {}

    # 4. Check package resources a.k.a. importlib.resources
    else:
        resource_path = importlib.resources.files(
            anchor="super_slurpy"
        ) / CONFIG_FILENAME

        if resource_path.is_file():
            content: str = resource_path.read_text(encoding="utf-8")
            raw_config = yaml.safe_load(stream=content) or {}

    return SlurpyConfig(**raw_config)


def load_resource_config() -> SlurpyConfig:
    """
    Load the default configuration strictly from the package resource.

    Returns
    -------
    SlurpyConfig
        The configuration populated exclusively from the internal YAML.

    Examples
    --------
    >>> from super_slurpy.config import load_resource_config
    >>> default_config = load_resource_config()
    >>> print(default_config.snake.alpha)
    0.1
    """
    # What: Target the internal package resource directly.
    # Why: Bypasses user and local files for a guaranteed factory reset.
    resource_path = importlib.resources.files(
        anchor="super_slurpy"
    ) / CONFIG_FILENAME

    raw_config: dict[str, Any] = {}
    if resource_path.is_file():
        content: str = resource_path.read_text(encoding="utf-8")
        raw_config = yaml.safe_load(stream=content) or {}

    return SlurpyConfig(**raw_config)
