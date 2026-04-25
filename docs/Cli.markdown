# Command-Line Interface (CLI) Guide

The CLI provides headless processing commands and a launch point
for the GUI. It is ideal for batch processing and
scripting.

## Launching the GUI via CLI
To start the interactive PyQt graphical user interface, use the
`gui` command:

```bash
slurpy gui [OPTIONS]
```

**Options:**
* `-u, --ultrasound`: Path to a video file to open automatically
 .
* `-s, --seed`: Path to a seed spline CSV file to load
  automatically.

## Headless Processing
Process video files without launching the GUI using the `process`
command. You can process a single video or an entire
directory of videos (.mp4, .avi, .mkv) sequentially.

```bash
slurpy process [INPUT_PATH] [OPTIONS]
```

**Arguments and Options:**
* `INPUT_PATH`: A single video file or a directory.
* `-s, --seed`: Path to the seed spline CSV file (required for
  batch processing).
* `-o, --output`: Output CSV path (single file) or directory
 . Defaults to the input path with a `_tracked.csv`
  suffix.
```
