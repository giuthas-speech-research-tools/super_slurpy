"""
Graphical User Interface for Super-Slurpy.

Provides an interactive PyQt6 window for loading videos,
navigating frames, and plotting spline points using Matplotlib.
"""

import sys
from typing import Any

import cv2
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QSpinBox, QVBoxLayout, QWidget
)

from super_slurpy.config import load_config, SuperSlurpyConfig


class SnakeGUI(QMainWindow):
    """
    Main application window for the Slurpy Contour Editor.

    Attributes
    ----------
    config : dict[str, Any]
        The application configuration loaded from YAML.
    video_path : str | None
        Path to the currently loaded video file.
    cap : cv2.VideoCapture | None
        OpenCV video capture object for reading frames.
    frame : np.ndarray | None
        The currently displayed video frame.
    points : list[list[float]]
        A list of [x, y] coordinates plotted by the user.
    """

    def __init__(self) -> None:
        """Initialize the main window and state variables."""
        super().__init__()

        # Window configuration
        self.setWindowTitle("Slurpy Contour Editor")
        self.config: SuperSlurpyConfig = load_config()

        # State management - explicitly typed per guidelines
        self.video_path: str | None = None
        self.cap: cv2.VideoCapture | None = None
        self.frame: np.ndarray | None = None
        self.points: list[list[float]] = []

        # Build the user interface components
        self._init_ui()

    def _init_ui(self) -> None:
        """
        Construct and layout the PyQt widgets and Matplotlib canvas.

        Returns
        -------
        None
        """
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Toolbar setup
        toolbar = QHBoxLayout()
        btn_open = QPushButton(text="Open Video")
        btn_open.clicked.connect(slot=self.open_video)

        self.points_input = QSpinBox()
        self.points_input.setRange(3, 100)
        self.points_input.setValue(20)

        # Assemble toolbar layout
        toolbar.addWidget(btn_open)
        toolbar.addWidget(QLabel(text="Spline Points:"))
        toolbar.addWidget(self.points_input)
        layout.addLayout(toolbar)

        # Matplotlib Canvas Integration
        self.fig = Figure(figsize=(8, 6))
        self.canvas = FigureCanvasQTAgg(figure=self.fig)
        self.ax = self.fig.add_subplot(111)

        self.canvas.mpl_connect(
            s="button_press_event",
            func=self.on_click
        )
        layout.addWidget(self.canvas)

    def open_video(self) -> None:
        """
        Open a file dialog to load a video and initialize playback.

        Reads configuration to determine which frame to display
        first (either absolute index or proportional).

        Returns
        -------
        None
        """
        # Prompt user for file selection
        file_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption="Open Video",
            directory="",
            filter="Videos (*.mp4 *.avi *.mkv)"
        )

        # Exit early if the user cancels the dialog
        if not file_path:
            return

        self.video_path = file_path
        self.cap = cv2.VideoCapture(filename=file_path)

        # Retrieve total frame count to calculate proportional starts
        total_frames: int = int(
            self.cap.get(propId=cv2.CAP_PROP_FRAME_COUNT)
        )

        # Determine starting frame based on config logic
        start_frame: int = 0

        # Access configuration attributes directly using dot notation
        if self.config.gui.default_frame is not None:
            start_frame = self.config.gui.default_frame
        elif self.config.gui.proportional_frame is not None:
            prop: float = self.config.gui.proportional_frame
            start_frame = int(total_frames * prop)

        # Seek to the calculated frame and read it
        self.cap.set(
            propId=cv2.CAP_PROP_POS_FRAMES,
            value=start_frame
        )
        ret, self.frame = self.cap.read()

        if ret:
            self.display_frame()

    def display_frame(self) -> None:
        """
        Render the current video frame and plot user points.

        Converts the BGR OpenCV image to RGB for Matplotlib,
        draws the frame, overlays points, and triggers a redraw.

        Returns
        -------
        None
        """
        # Ensure a frame exists before attempting to display
        if self.frame is None:
            return

        self.ax.clear()

        # OpenCV uses BGR by default, Matplotlib expects RGB
        rgb_frame = cv2.cvtColor(
            src=self.frame,
            code=cv2.COLOR_BGR2RGB
        )
        self.ax.imshow(X=rgb_frame)

        # Overlay user-clicked points if they exist
        if self.points:
            pts: np.ndarray = np.array(object=self.points)
            self.ax.plot(pts[:, 0], pts[:, 1], "ro-")

        self.canvas.draw()

    def on_click(self, event: Any) -> None:
        """
        Handle mouse click events on the Matplotlib canvas.

        Parameters
        ----------
        event : matplotlib.backend_bases.MouseEvent
            The event object containing click coordinates.

        Returns
        -------
        None
        """
        # Ignore clicks that occur outside the image axes
        if event.inaxes != self.ax:
            return

        # Append the new coordinates and update the display
        self.points.append([event.xdata, event.ydata])
        self.display_frame()


def launch_gui() -> None:
    """
    Application entry point for the GUI.

    Instantiates the QApplication and main window, then starts
    the Qt event loop.

    Returns
    -------
    None

    Examples
    --------
    >>> from super_slurpy.gui import launch_gui
    >>> launch_gui()
    """
    app = QApplication(sys.argv)
    window = SnakeGUI()
    window.show()
    sys.exit(app.exec())
