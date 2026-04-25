# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

[//]: # (Possible headings in a release:)
[//]: # (Highlights for shiny new features.)
[//]: # (Added for new features.)
[//]: # (Changed for changes in existing functionality.)
[//]: # (Refactor when functionality does not change but moves.)
[//]: # (Documentation for updates to docs.)
[//]: # (Testing for updates to tests.)
[//]: # (Deprecated for soon-to-be removed features.)
[//]: # (Removed for now removed features.)
[//]: # (Bugs for any known issues, especially in use before 1.0.)
[//]: # (Fixed for any bug fixes.)
[//]: # (Security in case of vulnerabilities.)
[//]: # (New contributors for first contributions.)

[//]: # (And of course if a version needs to be YANKED:)
[//]: # (## [version number] [data] [YANKED])


## [Unreleased]

### Added

- v0.4.0 will add API documentation with sphinx.
- v1.0 will be released after documentation is updated and functionality has
  been integration tested.


## [0.3.0] - 2026-04-25

### Highlights

- The GUI is now functional.
- The command line interface (CLI) is now functional.
- There is a mechanism for saving the seed snake.
- Snake tracking parameters can be edited in the GUI.
- Splines can be saved and loaded to/from .csv files.

### Added

- A lot of copied GUI functionality based on the Matlab implementation.
- Basic command line interface for processing a single file or a all videos in
  a directory.
- Seed snake saving and loading mechanisms.
- Snake tracking parameters editor in the GUI. 
- Spline saving and loading functions.

### Bugs 

- The gui focus can get stuck in the parameter edit fields preventing use of
  left and right arrow keys to flip through the frames.



## [0.2.1] - 2026-04-23

### Highlights

- Trying to fix package building and release on pypi.

### Fixed

- Package building on github.


## [0.2.0] - 2026-04-23

### Highlights

- Linked C code into Python, no actual functionality yet.

### Added

- C bindings in Cython.
- Untested yaml config for selecting the seed frame and settings for the snake
  algorithm.
- `clean.sh` to clean generated files before rebuilding the C-bindings.

### Removed

- A lot of old code that is no longer in use.
  - If somebody wants to for some reason combine this project with the original
    Matlab project, the matlab code will need to be brought back.


## [0.2.0-alpha.0] - 2026-03-25

### Highlights

- Added C code from original SLURP.

### Added

- Added C code from original SLURP.


## [0.1.1] - 2026-03-22

### Highlights

- Initial release to reserve package name on pypi.

### Added

- Release automation for main releases to pypi.


## [0.1.0-alpha.1] - 2026-03-22

### Highlights

- Initial release to reserve package name on test.pypi.

### Added

- A lot of auxiliary files but no actual code yet.
