"""
Configuration management for Super-Slurpy.

Handles the loading of the YAML configuration file from multiple
potential fallback locations and validates it using Pydantic.
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
        The proportional position to start on (0.0 to 1.0), defaults to 0.5.
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


class SuperSlurpyConfig(BaseModel):
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
    snake: SnakeConfig = Field(default_factory=SnakeConfig)


def load_config() -> SuperSlurpyConfig:
    """
    Load and validate the YAML configuration file.

    This function attempts to find the configuration file in the
    following order of precedence:
    1. Current working directory (cwd).
    2. User's home directory under `~/.slurpy/`.
    3. Bundled package resources via `importlib`.

    Returns
    -------
    SuperSlurpyConfig
        The validated configuration object populated with YAML data
        or default values if no file/data is found.

    Examples
    --------
    >>> from super_slurpy.config import load_config
    >>> config = load_config()
    >>> print(config.gui.proportional_frame)
    0.5
    """
    raw_config: dict[str, Any] = {}

    # Check current working directory
    cwd_path: Path = Path.cwd() / CONFIG_FILENAME
    if cwd_path.exists():
        with open(file=cwd_path, mode="r", encoding="utf-8") as f:
            # Fallback to empty dict if the file is completely empty
            raw_config = yaml.safe_load(stream=f) or {}

    # Check user's home directory
    elif (Path.home() / USER_DIR_NAME / CONFIG_FILENAME).exists():
        user_path: Path = Path.home() / USER_DIR_NAME / CONFIG_FILENAME
        with open(file=user_path, mode="r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(stream=f) or {}

    # 3. Check package resources a.k.a. importlib.resources
    else:
        # try:
        # try commented out because missing files should crash the
        # program rather than 'fail gracefully'
        resource_path = importlib.resources.files(
            anchor="super_slurpy"
        ) / CONFIG_FILENAME

        if resource_path.is_file():
            content: str = resource_path.read_text(
                encoding="utf-8"
            )
            raw_config = yaml.safe_load(stream=content) or {}

        # except (ModuleNotFoundError, FileNotFoundError):
        #     # Fail gracefully if the package structure is unexpected
        #     pass

    return SuperSlurpyConfig(**raw_config)
