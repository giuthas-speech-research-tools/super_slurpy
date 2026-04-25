# Graphical User Interface (GUI) Guide

The GUI provides an interactive environment for frame navigation,
video loading, and fully interactive anchor point management
.

## Starting the GUI
To launch the interface, use the CLI `gui` command:

```bash
slurpy gui
```

**Options:**
* `-u, --ultrasound`: Path to a video file to open automatically
 .
* `-s, --seed`: Path to a seed spline CSV file to load
  automatically.


## Interface Navigation
* **Open Video:** Use the `File -> Open Video` menu or toolbar to
  load a video.
* **Timeline Slider:** Scrub through the video frames manually
  using the slider at the bottom of the window.
* **Tracking Controls:** Track the entire video forwards and
  backwards, or track just the current frame.

## Mouse Controls for Splines
Manage contour anchor points directly on the canvas:
* **Left-Click:** Add a new anchor point.
* **Left-Click & Drag:** Move an existing anchor point.
* **Right-Click:** Delete the closest anchor point.
* **Double-Click:** Clear all anchor points on the current frame.

## Spline Management
* **Seed Splines:** Save your current contour as a reusable seed,
  or load and apply an existing seed spline. Note:
  Applying a seed spline overwrites current tracking data.
* **Resample Splines:** Normalize the spacing of generated or
  edited points by changing the control point count (2 to 500).

## Keyboard Shortcuts
* **Ctrl+O**: Open Video
* **Ctrl+S**: Save CSV
* **Ctrl+L**: Load CSV
* **Ctrl+T**: Track entire video
* **Ctrl+F**: Track current frame
* **Ctrl+R**: Resample Splines
* **Ctrl+W / Ctrl+Q**: Close Window / Quit
* **Left / Right Arrow**: Previous / Next Frame
```