"""
Constants and globals for the Super-Slurpy project.

This module centralizes all configuration values, status codes,
and text messages to maintain a proper separation of concerns.
"""

# Exit status code indicating missing optional dependencies
EXIT_MISSING_DEPS: int = 1

# Multi-line error message shown when GUI packages are missing.
# Split into multiple strings to adhere strictly to the 79-char
# maximum line length PEP 8 limit.
GUI_MISSING_ERR_MSG: str = (
    "Error: GUI dependencies are missing.\n"
    "Please install the optional GUI packages using either:\n"
    "pip install super-slurpy[gui]\n"
    "or\n"
    "uv tool install super-slurpy[gui]"
)

# The standard name for the configuration file
CONFIG_FILENAME: str = "slurpy.yaml"

# The hidden directory name used in the user's home folder
USER_DIR_NAME: str = ".slurpy"

# Default number of interpolated spline points
DEFAULT_SPLINE_POINTS: int = 50

# Maximum distance in pixels to register a click on an existing anchor
ANCHOR_CLICK_RADIUS: float = 15.0

# Supported video file extensions for the file dialog
VIDEO_FILTER: str = "Videos (*.mp4 *.avi *.mkv)"
