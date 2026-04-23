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
