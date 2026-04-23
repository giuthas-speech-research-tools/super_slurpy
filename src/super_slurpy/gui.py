"""
Graphical User Interface for Super-Slurpy.

Provides an interactive PyQt6 window replicating the functionality
of the legacy MATLAB SLURP.m script. It includes video loading,
frame navigation via sliders, and fully interactive anchor point
management (add, drag, delete, clear) with real-time splines.
"""

import sys
from typing import Any

import av
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QSlider, QSpinBox,
    QVBoxLayout, QWidget
)
from scipy.interpolate import PchipInterpolator, interp1d
from scipy.ndimage import gaussian_filter1d

from super_slurpy.config import load_config
from super_slurpy.constants import (
    ANCHOR_CLICK_RADIUS,
    DEFAULT_SPLINE_POINTS,
    VIDEO_FILTER
)
from super_slurpy.core import make_snake


class SnakeGUI(QMainWindow):
    """
    Main application window for the Slurpy Contour Editor.

    Handles video loading, frame traversal, and interactive contour
    drawing using Matplotlib's event system.

    Attributes
    ----------
    config : dict[str, Any]
        The application configuration loaded from YAML.
    video_path : str | None
        Path to the currently loaded video file.
    container : Any | None
        PyAV media container for reading video frames.
    video_stream : Any | None
        The primary video stream from the container.
    frame : np.ndarray | None
        The currently displayed video frame.
    anchors : list[list[float]]
        A list of user-defined anchor points [x, y].
    contour : np.ndarray | None
        Interpolated spline points calculated from anchors.
    _drag_idx : int | None
        Index of the anchor currently being dragged, or None.

    Examples
    --------
    >>> from PyQt6.QtWidgets import QApplication
    >>> import sys
    >>> app = QApplication(sys.argv)
    >>> window = SnakeGUI()
    >>> window.show()
    """

    def __init__(self) -> None:
        """Initialize the main window and state variables."""
        super().__init__()

        self.setWindowTitle("Slurpy Contour Editor")
        self.config: dict[str, Any] = load_config()

        # State management for video and points
        self.video_path: str | None = None
        self.container: Any = None
        self.video_stream: Any = None
        self.frame: np.ndarray | None = None
        self.anchors: list[list[float]] = []
        self.contour: np.ndarray | None = None

        # Tracks which point is being dragged by the user
        self._drag_idx: int | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        """
        Construct the PyQt UI elements and Matplotlib canvas.

        Builds the toolbars, sliders, and sets up the event callbacks
        for user interaction.
        """
        main_widget = QWidget(parent=self)
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 1. Toolbar Setup
        toolbar = QHBoxLayout()
        btn_open = QPushButton("Open Video", parent=main_widget)
        btn_open.clicked.connect(self.open_video)

        self.btn_track = QPushButton("Track Video", parent=main_widget)
        self.btn_track.clicked.connect(self.run_tracking)
        self.btn_track.setEnabled(False)

        self.points_input = QSpinBox(parent=main_widget)
        self.points_input.setRange(3, 500)
        self.points_input.setValue(DEFAULT_SPLINE_POINTS)
        self.points_input.valueChanged.connect(self._update_spline)

        toolbar.addWidget(btn_open)
        toolbar.addWidget(self.btn_track)
        toolbar.addWidget(QLabel("Spline Points:"))
        toolbar.addWidget(self.points_input)
        layout.addLayout(toolbar)

        # 2. Frame Navigation Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self.on_slider_change)
        layout.addWidget(self.slider)

        # 3. Matplotlib Canvas Integration
        self.fig = Figure(figsize=(8, 6))
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_axis_off()
        layout.addWidget(self.canvas)

        # 4. Connect Matplotlib interactive events
        self.canvas.mpl_connect(
            "button_press_event",
            self.on_mouse_press
        )
        self.canvas.mpl_connect(
            "motion_notify_event",
            self.on_mouse_motion
        )
        self.canvas.mpl_connect(
            "button_release_event",
            self.on_mouse_release
        )

    def open_video(self) -> None:
        """
        Open a file dialog to load a video and initialize playback.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption="Open Video",
            directory="",
            filter=VIDEO_FILTER
        )
        if not file_path:
            return

        self.video_path = file_path

        # Open video and grab the first video stream via PyAV
        self.container = av.open(file_path)
        self.video_stream = self.container.streams.video[0]

        # Configure slider bounds based on video length
        total_frames: int = self.video_stream.frames
        if total_frames == 0:
            # Fallback if the container lacks duration metadata
            total_frames = 1000

        self.slider.setRange(0, total_frames - 1)
        self.slider.setValue(0)

        # Enable relevant UI elements
        self.slider.setEnabled(True)
        self.btn_track.setEnabled(True)

        self._read_and_display_frame(frame_idx=0)

    def _read_and_display_frame(self, frame_idx: int) -> None:
        """
        Read a specific frame from the video and update the display.

        Parameters
        ----------
        frame_idx : int
            The index of the frame to retrieve.
        """
        if self.container is None or self.video_stream is None:
            return

        # Calculate timestamp for PyAV seek (in stream time_base units)
        fps: float = float(self.video_stream.average_rate)
        time_base: float = float(self.video_stream.time_base)

        if fps > 0 and time_base > 0:
            target_sec: float = frame_idx / fps
            target_pts: int = int(target_sec / time_base)
            self.container.seek(target_pts, stream=self.video_stream)

        # Decode frames until we grab the next available one.
        for frame in self.container.decode(video=0):
            self.frame = frame.to_ndarray(format="rgb24")
            break

        self._display_canvas()

    def on_slider_change(self, value: int) -> None:
        """
        Callback triggered when the frame slider is moved.

        Parameters
        ----------
        value : int
            The new frame index from the slider.
        """
        self._read_and_display_frame(frame_idx=value)

    def _update_spline(self) -> None:
        """
        Calculate the interpolated contour from the anchor points.

        Uses piecewise cubic hermite interpolating polynomial (pchip)
        to match MATLAB's default behavior, or linear if only 2 points
        are provided.
        """
        n_anchors: int = len(self.anchors)

        if n_anchors < 2:
            self.contour = None
            self._display_canvas()
            return

        pts: np.ndarray = np.array(self.anchors)
        n_points: int = self.points_input.value()

        # Calculate cumulative distances to parameterize the spline
        diffs: np.ndarray = np.diff(pts, axis=0)
        dists: np.ndarray = np.linalg.norm(diffs, axis=1)
        k: np.ndarray = np.insert(np.cumsum(dists), 0, 0.0)

        k_new: np.ndarray = np.linspace(0, k[-1], n_points)

        # Use linear interpolation for 2 points, pchip for 3+
        if n_anchors == 2:
            interp_func = interp1d(k, pts, axis=0)
        else:
            interp_func = PchipInterpolator(k, pts, axis=0)

        self.contour = interp_func(k_new)
        self._display_canvas()

    def _display_canvas(self) -> None:
        """Render the video frame, anchors, and spline to the canvas."""
        if self.frame is None:
            return

        self.ax.clear()
        self.ax.set_axis_off()

        # Frame is already RGB via PyAV to_ndarray
        self.ax.imshow(X=self.frame)

        # Draw the interpolated spline contour
        if self.contour is not None:
            self.ax.plot(
                self.contour[:, 0],
                self.contour[:, 1],
                color="blue",
                linestyle="-",
                linewidth=2
            )

        # Draw the interactive anchor points
        if self.anchors:
            pts: np.ndarray = np.array(self.anchors)
            self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color="red",
                marker="o",
                linestyle="None",
                markersize=6
            )

        self.canvas.draw_idle()

    def _get_closest_anchor(self, x: float, y: float) -> int | None:
        """
        Find the index of the anchor closest to the given coordinates.

        Parameters
        ----------
        x : float
            X-coordinate of the mouse click.
        y : float
            Y-coordinate of the mouse click.

        Returns
        -------
        int | None
            The index of the closest anchor, or None if no anchor
            is within the defined ANCHOR_CLICK_RADIUS.
        """
        if not self.anchors:
            return None

        pts: np.ndarray = np.array(self.anchors)
        click: np.ndarray = np.array([x, y])
        dists: np.ndarray = np.linalg.norm(pts - click, axis=1)

        min_idx: int = int(np.argmin(dists))
        if dists[min_idx] < ANCHOR_CLICK_RADIUS:
            return min_idx
        return None

    def on_mouse_press(self, event: Any) -> None:
        """Handle mouse click events for point creation and deletion."""
        if event.inaxes != self.ax or event.xdata is None:
            return

        # Double-click clears all anchors
        if event.dblclick:
            self.anchors.clear()
            self._update_spline()
            return

        closest_idx: int | None = self._get_closest_anchor(
            x=event.xdata,
            y=event.ydata
        )

        # Right-click (button 3): Delete point
        if event.button == 3:
            if closest_idx is not None:
                self.anchors.pop(closest_idx)
                self._update_spline()
            return

        # Left-click (button 1): Add or start dragging
        if event.button == 1:
            if closest_idx is not None:
                self._drag_idx = closest_idx
            else:
                self.anchors.append([event.xdata, event.ydata])
                self._update_spline()

    def on_mouse_motion(self, event: Any) -> None:
        """Handle mouse movement events for dragging anchors."""
        if self._drag_idx is None or event.inaxes != self.ax:
            return

        # Update the position of the dragged anchor
        if event.xdata is not None and event.ydata is not None:
            self.anchors[self._drag_idx] = [event.xdata, event.ydata]
            self._update_spline()

    def on_mouse_release(self, event: Any) -> None:
        """Handle mouse release events to stop dragging."""
        if event.button == 1:
            self._drag_idx = None

    def _compute_egrad(
        self, img: np.ndarray, sigma: float = 1.0
    ) -> np.ndarray:
        """
        Calculate the normalized external gradient energy map.

        Mirrors the MATLAB 'Egrad.m' script by computing Gaussian
        derivatives to find edges, then inverting so edges
        become energy minimums (valleys) for the snake.

        Parameters
        ----------
        img : np.ndarray
            The 2D grayscale image array.
        sigma : float
            Standard deviation for the Gaussian filter.

        Returns
        -------
        np.ndarray
            A 2D array representing the gradient energy map.
        """
        # Calculate gradients using SciPy Gaussian derivatives
        gx: np.ndarray = gaussian_filter1d(
            input=img, axis=1, sigma=sigma, order=1
        )
        gy: np.ndarray = gaussian_filter1d(
            input=img, axis=0, sigma=sigma, order=1
        )

        # Calculate gradient magnitude
        grad_mag: np.ndarray = np.sqrt(gx**2 + gy**2)

        # Normalize to [0, 1]
        max_val: float = float(np.max(grad_mag))
        if max_val > 0:
            grad_mag = grad_mag / max_val

        # Invert so edges represent minimum energy
        egrad: np.ndarray = 1.0 - grad_mag

        # Ensure array is safely contiguous in memory for Cython
        return np.ascontiguousarray(egrad)

    def run_tracking(self) -> None:
        """
        Run the active contour (snake) tracking on the whole video.

        Uses the currently placed anchors as the seed for the initial
        frame, and iteratively tracks the contour frame-by-frame
        until the end of the video. The GUI updates in real-time.

        Returns
        -------
        None
        """
        if not self.anchors or self.container is None:
            return

        # 1. Disable navigation during tracking
        self.slider.setEnabled(False)
        self.points_input.setEnabled(False)
        self.btn_track.setEnabled(False)

        # 2. Get frame bounds
        start_idx: int = self.slider.value()
        end_idx: int = self.slider.maximum()

        # 3. Initialize snake parameters
        current_pts: np.ndarray = np.array(self.anchors, dtype=np.float64)
        current_pts = np.ascontiguousarray(current_pts)

        n_anchors: int = current_pts.shape[0]

        # Search window for each snaxel (defaulting to 10 pixels)
        delta: np.ndarray = np.full(
            shape=n_anchors, fill_value=10, dtype=np.int32
        )

        # Hyperparameters for Cython execution
        band_penalty: float = 1.0
        alpha: float = 0.5
        lambda1: float = 0.5
        use_band_energy: int = 0

        # 4. Process each frame sequentially
        for frame_idx in range(start_idx, end_idx + 1):
            # Advance slider and read the frame
            self.slider.setValue(frame_idx)

            # Keep the GUI responsive and allow canvas to redraw
            QApplication.processEvents()

            if self.frame is None:
                continue

            # Convert RGB frame to 2D grayscale double array
            img_gray: np.ndarray = np.mean(self.frame, axis=2)
            img_double: np.ndarray = np.ascontiguousarray(
                img_gray, dtype=np.float64
            )

            # Compute the external energy map
            egrad: np.ndarray = self._compute_egrad(img=img_double)

            # 5. Execute the Cython backend
            try:
                results = make_snake(
                    img_double,
                    egrad,
                    current_pts,
                    delta,
                    band_penalty,
                    alpha,
                    lambda1,
                    use_band_energy
                )

                # Extract the updated points from the tuple returned
                tracked_pts: np.ndarray = results[0]

                # Handle possible 1D flattening from Cython
                if tracked_pts.ndim == 1:
                    current_pts = tracked_pts.reshape(n_anchors, 2)
                else:
                    current_pts = tracked_pts

                # 6. Update GUI state with the new anchors
                self.anchors = current_pts.tolist()
                self._update_spline()

            except Exception as e:
                print(f"Tracking interrupted at frame {frame_idx}: {e}")
                break

        # Re-enable navigation once tracking is complete
        self.slider.setEnabled(True)
        self.points_input.setEnabled(True)
        self.btn_track.setEnabled(True)


def launch_gui() -> None:
    """
    Application entry point for the GUI.

    Instantiates the QApplication and main window, then starts
    the Qt event loop.

    Examples
    --------
    >>> from super_slurpy.gui import launch_gui
    >>> launch_gui()
    """
    app = QApplication(sys.argv)
    window = SnakeGUI()
    window.show()
    sys.exit(app.exec())
