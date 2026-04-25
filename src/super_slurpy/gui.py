"""
Graphical User Interface for Super-Slurpy.

Provides an interactive PyQt6 window replicating the functionality
of the legacy MATLAB SLURP.m script. It includes video loading,
frame navigation via sliders, and fully interactive anchor point
management (add, drag, delete, clear) with real-time splines.
"""

import csv
import sys
from typing import Any

import av
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
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
    current_frame_idx : int
        The index of the frame currently being viewed.
    anchors : list[list[float]]
        A list of user-defined anchor points [x, y].
    anchors_history : dict[int, list[list[float]]]
        A mapping of frame indices to their saved anchor points.
    contour : np.ndarray | None
        Interpolated spline points calculated from anchors.
    _drag_idx : int | None
        Index of the anchor currently being dragged, or None.
    _is_tracking : bool
        Flag indicating if the automated tracking loop is active.
    """

    def __init__(self) -> None:
        """Initialize the main window and state variables."""
        super().__init__()

        self.setWindowTitle("Slurpy Contour Editor")
        self.config: dict[str, Any] = load_config()

        # State management for video
        self.video_path: str | None = None
        self.container: Any = None
        self.video_stream: Any = None
        self.frame: np.ndarray | None = None
        self.current_frame_idx: int = 0

        # State management for contour points
        self.anchors: list[list[float]] = []
        self.anchors_history: dict[int, list[list[float]]] = {}
        self.contour: np.ndarray | None = None

        # Internal control flags
        self._drag_idx: int | None = None
        self._is_tracking: bool = False

        self._init_ui()
        self._init_shortcuts()

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

        btn_open = QPushButton(
            text="Open Video (Ctrl+O)",
            parent=main_widget,
        )
        btn_open.clicked.connect(slot=self.open_video)

        self.btn_track = QPushButton(
            text="Track (Ctrl+T)",
            parent=main_widget,
        )
        self.btn_track.clicked.connect(slot=self.run_tracking)
        self.btn_track.setEnabled(False)

        btn_save = QPushButton(
            text="Save CSV (Ctrl+S)",
            parent=main_widget,
        )
        btn_save.clicked.connect(slot=self.save_results_to_csv)

        btn_load = QPushButton(
            text="Load CSV (Ctrl+L)",
            parent=main_widget,
        )
        btn_load.clicked.connect(slot=self.load_results_from_csv)

        self.points_input = QSpinBox(parent=main_widget)
        self.points_input.setRange(3, 500)
        self.points_input.setValue(DEFAULT_SPLINE_POINTS)
        self.points_input.valueChanged.connect(slot=self._update_spline)

        toolbar.addWidget(btn_open)
        toolbar.addWidget(self.btn_track)
        toolbar.addWidget(btn_save)
        toolbar.addWidget(btn_load)
        toolbar.addWidget(QLabel(text="Spline Points:"))
        toolbar.addWidget(self.points_input)
        layout.addLayout(toolbar)

        # 2. Frame Navigation Slider
        self.slider = QSlider(orientation=Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider.valueChanged.connect(slot=self.on_slider_change)
        layout.addWidget(self.slider)

        # 3. Matplotlib Canvas Integration
        self.fig = Figure(figsize=(8, 6))
        self.canvas = FigureCanvasQTAgg(figure=self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_axis_off()
        layout.addWidget(self.canvas)

        # 4. Connect Matplotlib interactive events
        self.canvas.mpl_connect(
            s="button_press_event",
            func=self.on_mouse_press
        )
        self.canvas.mpl_connect(
            s="motion_notify_event",
            func=self.on_mouse_motion
        )
        self.canvas.mpl_connect(
            s="button_release_event",
            func=self.on_mouse_release
        )

    def _init_shortcuts(self) -> None:
        """
        Initialize application-wide keyboard shortcuts.

        Binds key sequences (like Ctrl+O, Ctrl+S) to their
        respective class methods to improve user efficiency.

        Returns
        -------
        None

        Examples
        --------
        >>> gui = SnakeGUI()
        >>> gui._init_shortcuts()
        """
        # Bind application exit to Ctrl+Q and Ctrl+W
        shortcut_quit = QShortcut(QKeySequence("Ctrl+Q"), self)
        shortcut_quit.activated.connect(slot=self.close)

        shortcut_close = QShortcut(QKeySequence("Ctrl+W"), self)
        shortcut_close.activated.connect(slot=self.close)

        # Bind file opening and tracking actions
        shortcut_open = QShortcut(QKeySequence("Ctrl+O"), self)
        shortcut_open.activated.connect(slot=self.open_video)

        shortcut_track = QShortcut(QKeySequence("Ctrl+T"), self)
        shortcut_track.activated.connect(slot=self.run_tracking)

        # Bind CSV input/output actions
        shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut_save.activated.connect(slot=self.save_results_to_csv)

        shortcut_load = QShortcut(QKeySequence("Ctrl+L"), self)
        shortcut_load.activated.connect(slot=self.load_results_from_csv)

    def keyPressEvent(self, event: Any) -> None:
        """
        Handle key press events for the main window.

        Specifically overrides default behavior to allow
        Left and Right arrow keys to step backward and
        forward through the video frames.

        Parameters
        ----------
        event : PyQt6.QtGui.QKeyEvent
            The key press event captured by the GUI.

        Returns
        -------
        None

        Examples
        --------
        >>> # This method is called automatically by PyQt6
        >>> # when a user presses a key.
        """
        # Ignore arrow keys if no video is loaded
        if not self.slider.isEnabled():
            return

        # Move to the previous frame on Left Arrow
        if event.key() == Qt.Key.Key_Left:
            new_val = max(0, self.slider.value() - 1)
            self.slider.setValue(new_val)

        # Move to the next frame on Right Arrow
        elif event.key() == Qt.Key.Key_Right:
            new_val = min(
                self.slider.maximum(),
                self.slider.value() + 1,
            )
            self.slider.setValue(new_val)

        # Propagate all other keystrokes up the inheritance chain
        else:
            super().keyPressEvent(event)

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
        self.container = av.open(file=file_path)
        self.video_stream = self.container.streams.video[0]

        # Configure slider bounds based on video length
        total_frames: int = self.video_stream.frames
        if total_frames == 0:
            total_frames = 1000

        # Calculate initial frame based on configuration precedence
        start_frame: int = 0
        if self.config.gui.default_frame is not None:
            # Priority 1: Absolute frame index from config
            start_frame = self.config.gui.default_frame
        elif self.config.gui.proportional_frame is not None:
            # Priority 2: Proportional position (0.0 to 1.0) from config
            start_frame = int(
                self.config.gui.proportional_frame * (total_frames - 1)
            )
        # Ensure calculated start_frame is within the actual video bounds
        start_frame = max(0, min(start_frame, total_frames - 1))

        self.slider.setRange(0, total_frames - 1)
        self.slider.setValue(start_frame)

        self.slider.setEnabled(True)
        self.btn_track.setEnabled(True)

        # Load and render the calculated starting frame
        self._read_and_display_frame(frame_idx=start_frame)

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

        self.current_frame_idx = frame_idx

        # If navigating manually, load the historical anchors if they exist.
        # If tracking is active, let the tracking loop propagate the anchors.
        if not self._is_tracking:
            if frame_idx in self.anchors_history:
                self.anchors = [
                    list(pt) for pt in self.anchors_history[frame_idx]
                ]

        # Calculate timestamp for PyAV seek (in stream time_base units)
        fps: float = float(self.video_stream.average_rate)
        time_base: float = float(self.video_stream.time_base)

        if fps > 0 and time_base > 0:
            target_sec: float = frame_idx / fps
            target_pts: int = int(target_sec / time_base)
            self.container.seek(offset=target_pts, stream=self.video_stream)

        # Decode frames until we grab the next available one
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

        Saves the current anchors to the frame history automatically.
        Uses piecewise cubic hermite interpolating polynomial (pchip).
        """
        n_anchors: int = len(self.anchors)

        # Auto-save current anchors into the history map
        self.anchors_history[self.current_frame_idx] = [
            list(pt) for pt in self.anchors
        ]

        if n_anchors < 2:
            self.contour = None
            self._display_canvas()
            return

        pts: np.ndarray = np.array(object=self.anchors)
        n_points: int = self.points_input.value()

        # Calculate cumulative distances to parameterize the spline
        diffs: np.ndarray = np.diff(a=pts, axis=0)
        dists: np.ndarray = np.linalg.norm(x=diffs, axis=1)
        k: np.ndarray = np.insert(arr=np.cumsum(a=dists), obj=0, values=0.0)

        k_new: np.ndarray = np.linspace(start=0, stop=k[-1], num=n_points)

        # Use linear interpolation for 2 points, pchip for 3+
        if n_anchors == 2:
            interp_func = interp1d(x=k, y=pts, axis=0)
        else:
            interp_func = PchipInterpolator(x=k, y=pts, axis=0)

        self.contour = interp_func(x=k_new)
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
            pts: np.ndarray = np.array(object=self.anchors)
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
        """Find the index of the anchor closest to the given coordinates."""
        if not self.anchors:
            return None

        pts: np.ndarray = np.array(object=self.anchors)
        click: np.ndarray = np.array(object=[x, y])
        dists: np.ndarray = np.linalg.norm(x=pts - click, axis=1)

        min_idx: int = int(np.argmin(a=dists))
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
        """Calculate the normalized external gradient energy map."""
        gx: np.ndarray = gaussian_filter1d(
            input=img, axis=1, sigma=sigma, order=1
        )
        gy: np.ndarray = gaussian_filter1d(
            input=img, axis=0, sigma=sigma, order=1
        )

        grad_mag: np.ndarray = np.sqrt(gx**2 + gy**2)

        max_val: float = float(np.max(a=grad_mag))
        if max_val > 0:
            grad_mag = grad_mag / max_val

        egrad: np.ndarray = 1.0 - grad_mag
        return np.ascontiguousarray(a=egrad)

    def save_results_to_csv(self) -> None:
        """
        Export tracked anchor points to a CSV file.

        Iterates over the tracking history and writes the
        frame index, point ID, and X/Y coordinates to disk.

        Returns
        -------
        None

        Examples
        --------
        >>> gui = SnakeGUI()
        >>> gui.save_results_to_csv()
        """
        # Ensure there is actually data to save
        if not self.anchors_history:
            QMessageBox.warning(
                parent=self,
                title="Warning",
                text="No tracking data to save.",
            )
            return

        # Prompt user for a save location
        file_path, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption="Save Tracking Results",
            directory="",
            filter="CSV Files (*.csv)",
        )

        # Abort if the user canceled the dialog
        if not file_path:
            return

        try:
            # Write the tracking history to the selected file
            with open(file=file_path, mode="w", newline="") as f:
                writer = csv.writer(f)

                # Write the header row
                writer.writerow(["frame", "point_id", "x", "y"])

                # Sort keys to ensure chronological order in CSV
                for frame_idx in sorted(self.anchors_history.keys()):
                    pts = self.anchors_history[frame_idx]
                    for i, (x, y) in enumerate(pts):
                        writer.writerow([frame_idx, i, x, y])

            QMessageBox.information(
                self,
                title="Success",
                text=f"Results saved to {file_path}",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                title="Error",
                text=f"Failed to save CSV: {e}",
            )

    def load_results_from_csv(self) -> None:
        """
        Import tracked anchor points from a CSV file.

        Reads a previously saved CSV file and restores the
        tracking history into the application state. Updates
        the current view if data exists for the current frame.

        Returns
        -------
        None

        Examples
        --------
        >>> gui = SnakeGUI()
        >>> gui.load_results_from_csv()
        """
        # Prompt user to select a CSV file
        file_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption="Load Tracking Results",
            directory="",
            filter="CSV Files (*.csv)",
        )

        # Abort if the user canceled the dialog
        if not file_path:
            return

        try:
            new_history: dict[int, list[list[float]]] = {}

            # Read the CSV and reconstruct the history dictionary
            with open(file=file_path, mode="r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    frame = int(row["frame"])
                    x = float(row["x"])
                    y = float(row["y"])

                    if frame not in new_history:
                        new_history[frame] = []
                    new_history[frame].append([x, y])

            # Apply the loaded history to the current state
            self.anchors_history = new_history

            # Update the UI if data covers the currently viewed frame
            if self.current_frame_idx in self.anchors_history:
                # Extract coordinates from the active frame
                pts = self.anchors_history[self.current_frame_idx]
                self.anchors = [list(pt) for pt in pts]

                # Render the updated spline
                self._update_spline()

            QMessageBox.information(
                parent=self,
                title="Success",
                text="Results loaded successfully.",
            )
        except Exception as e:
            QMessageBox.critical(
                parent=self,
                title="Error",
                text=f"Failed to load CSV: {e}",
            )

    def _execute_tracking(self, frame_indices: list[int]) -> None:
        """
        Internal loop to apply snake tracking over a sequence of frames.

        Parameters
        ----------
        frame_indices : list[int]
            The sequence of frame indices to process sequentially.

        Returns
        -------
        None

        Examples
        --------
        >>> gui = SnakeGUI()
        >>> gui._execute_tracking(frame_indices=[10, 11, 12])
        """
        # Seed the optimization with the current anchor positions
        current_pts: np.ndarray = np.array(
            object=self.anchors,
            dtype=np.float64
        )
        current_pts = np.ascontiguousarray(a=current_pts)
        n_anchors: int = current_pts.shape[0]

        # Define the local search window size for the snake algorithm
        delta: np.ndarray = np.full(
            shape=n_anchors,
            fill_value=10,
            dtype=np.int32
        )

        # Algorithm parameters (internal weighting)
        band_penalty: float = 1.0
        alpha: float = 0.5
        lambda1: float = 0.5
        use_band_energy: int = 0

        for frame_idx in frame_indices:
            # Update the slider; this triggers frame loading via signals
            self.slider.setValue(frame_idx)
            QApplication.processEvents()

            if self.frame is None:
                continue

            # Calculate gradient energy for the new frame
            img_gray: np.ndarray = np.mean(a=self.frame, axis=2)
            img_double: np.ndarray = np.ascontiguousarray(
                a=img_gray,
                dtype=np.float64
            )
            egrad: np.ndarray = self._compute_egrad(img=img_double)

            # Perform the deformation based on the energy map
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

            # Reshape coordinates if returned as a flat array
            tracked_pts: np.ndarray = results[0]
            if tracked_pts.ndim == 1:
                current_pts = tracked_pts.reshape(n_anchors, 2)
            else:
                current_pts = tracked_pts

            # Store the result and trigger spline recalculation/history save
            self.anchors = current_pts.tolist()
            self._update_spline()

    def run_tracking(self) -> None:
        """
        Run the active contour tracking both forward and backward.

        Starts from the current slider position and propagates the
        contour towards the end of the video, then returns to the
        manual starting point and propagates towards the beginning.

        Returns
        -------
        None

        Examples
        --------
        >>> gui = SnakeGUI()
        >>> gui.run_tracking()
        """
        if not self.anchors or self.container is None:
            return

        # Prevent user interference during the automated process
        self.slider.setEnabled(False)
        self.points_input.setEnabled(False)
        self.btn_track.setEnabled(False)

        self._is_tracking = True

        # Capture initial state to reset for the second (backward) pass
        start_idx: int = self.slider.value()
        init_anchors: list[list[float]] = [list(a) for a in self.anchors]

        try:
            # 1. Forward Pass: Process from next frame to video end
            max_idx: int = self.slider.maximum()
            fwd_range: list[int] = list(range(start_idx + 1, max_idx + 1))
            if fwd_range:
                self._execute_tracking(frame_indices=fwd_range)

            # 2. Reset State: Return to the user-defined starting point
            self.anchors = [list(a) for a in init_anchors]
            self._read_and_display_frame(frame_idx=start_idx)
            self._update_spline()

            # 3. Backward Pass: Process from previous frame to video start
            back_range: list[int] = list(range(start_idx - 1, -1, -1))
            if back_range:
                self._execute_tracking(frame_indices=back_range)

        except Exception as e:
            # Standard output for errors during headless iteration
            print(f"Tracking sequence failed: {e}")

        finally:
            # Restore UI functionality and return to start for verification
            self._is_tracking = False
            self.slider.setEnabled(True)
            self.points_input.setEnabled(True)
            self.btn_track.setEnabled(True)
            self.slider.setValue(start_idx)


def launch_gui() -> None:
    """Application entry point for the GUI."""
    app = QApplication(sys.argv)
    window = SnakeGUI()
    window.show()
    sys.exit(app.exec())
