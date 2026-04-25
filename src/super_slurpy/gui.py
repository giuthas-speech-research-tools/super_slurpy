"""
GUI for slurpy.

Provides an interactive PyQt6 window replicating the functionality
of the legacy MATLAB SLURP.m script. It includes video loading,
frame navigation via sliders, and fully interactive anchor point
management (add, drag, delete, clear) with real-time splines.

Examples
--------
>>> # The GUI is typically launched via the CLI module:
>>> # from super_slurpy.gui import launch_gui
>>> # launch_gui()
"""

import csv
import sys
from typing import Any

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QDoubleValidator, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from scipy.interpolate import PchipInterpolator, interp1d

from super_slurpy.constants import (
    ANCHOR_CLICK_RADIUS,
    VIDEO_FILTER,
)
from super_slurpy.model import SlurpyModel


class SlurpyGui(QMainWindow):
    """
    Main application window for the Slurpy Contour Editor.

    This class encapsulates the entirely of the visual and interactive
    elements used for tracking and correcting contour points.

    Examples
    --------
    >>> # Start the application and initialize the main window
    >>> app = QApplication(sys.argv)
    >>> window = SlurpyGui()
    >>> window.show()
    """

    def __init__(self) -> None:
        """
        Initialize the PyQt Main Window Application Frame.

        Sets up the core model, interactive states, and triggers
        the construction of the UI layout and menus.

        Returns
        -------
        None

        Examples
        --------
        >>> window = SnakeGUI()
        """
        # What: Initialize the base QMainWindow class.
        # Why: Required to inherit the Qt main window properties.
        super().__init__()
        self.setWindowTitle("Slurpy Contour Editor")
        self.model = SlurpyModel()

        # What: Track which point is being actively dragged.
        # Why: Enables interactive movement of contour nodes.
        self._drag_idx: int | None = None
        self._is_tracking: bool = False

        # What: Initialize the view components.
        # Why: Separating UI logic keeps the constructor clean.
        self._init_ui()
        self._init_menus()

    def _init_ui(self) -> None:
        """
        Construct the PyQt UI elements and Matplotlib canvas.

        Builds the toolbars, buttons, video timeline slider, and
        the interactive Matplotlib figure canvas.

        Returns
        -------
        None

        Examples
        --------
        >>> # Internally called during initialization
        >>> # window._init_ui()
        """
        # What: Create a central widget and layout.
        # Why: QMainWindow requires a central widget for custom layouts.
        main_widget = QWidget(parent=self)
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        toolbar = QHBoxLayout()

        self.btn_open = QPushButton(
            text="Open Video (Ctrl+O)", parent=main_widget
        )
        self.btn_open.clicked.connect(slot=self.open_video)

        self.btn_track = QPushButton(
            text="Track (Ctrl+T)", parent=main_widget
        )
        self.btn_track.clicked.connect(slot=self.run_tracking)
        self.btn_track.setEnabled(False)

        self.btn_track_curr = QPushButton(
            text="Track this frame (Ctrl+F)", parent=main_widget
        )
        self.btn_track_curr.clicked.connect(
            slot=self.track_current_frame_action
        )
        self.btn_track_curr.setEnabled(False)
        self.btn_track_curr.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.btn_save = QPushButton(
            text="Save CSV (Ctrl+S)", parent=main_widget
        )
        self.btn_save.clicked.connect(slot=self.save_results_to_csv)

        self.btn_load = QPushButton(
            text="Load CSV (Ctrl+L)", parent=main_widget
        )
        self.btn_load.clicked.connect(slot=self.load_results_from_csv)

        toolbar.addWidget(self.btn_open)
        toolbar.addWidget(self.btn_track)
        toolbar.addWidget(self.btn_track_curr)
        toolbar.addWidget(self.btn_save)
        toolbar.addWidget(self.btn_load)
        layout.addLayout(toolbar)

        # What: Create the timeline slider.
        # Why: Allows the user to scrub through the video frames.
        self.slider = QSlider(orientation=Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(slot=self.on_slider_change)
        layout.addWidget(self.slider)

        # What: Setup Matplotlib canvas inside PyQt.
        # Why: Enables rendering numpy arrays and plotting splines.
        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(figure=self.figure)
        self.ax = self.figure.add_subplot(111)

        self.figure.subplots_adjust(
            left=0, right=1, bottom=0, top=1, wspace=0, hspace=0
        )
        self.ax.set_axis_off()
        layout.addWidget(self.canvas)

        # What: Bind mouse events to the canvas.
        # Why: Provides user interactivity for points.
        self.canvas.mpl_connect(
            s="button_press_event", func=self.on_mouse_press
        )
        self.canvas.mpl_connect(
            s="motion_notify_event", func=self.on_mouse_motion
        )
        self.canvas.mpl_connect(
            s="button_release_event", func=self.on_mouse_release
        )

        self._init_snake_controls(layout=layout)

        # What: Remove focus policy from interactive buttons.
        # Why: Prevents arrow keys from shifting focus instead of
        # changing frames.
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_load.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_track.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_save.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _init_menus(self) -> None:
        """
        Initialize the application menu bar and actions.

        Binds keyboard shortcuts and standard actions to the top menu.

        Returns
        -------
        None

        Examples
        --------
        >>> # Internally called during initialization
        >>> # window._init_menus()
        """
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        action_open = QAction(text="&Open Video", parent=self)
        action_open.setShortcut(QKeySequence("Ctrl+O"))
        action_open.triggered.connect(slot=self.open_video)
        file_menu.addAction(action_open)

        action_save = QAction(text="&Save CSV", parent=self)
        action_save.setShortcut(QKeySequence("Ctrl+S"))
        action_save.triggered.connect(slot=self.save_results_to_csv)
        file_menu.addAction(action_save)

        action_load = QAction(text="&Load CSV", parent=self)
        action_load.setShortcut(QKeySequence("Ctrl+L"))
        action_load.triggered.connect(slot=self.load_results_from_csv)
        file_menu.addAction(action_load)

        file_menu.addSeparator()

        action_load_seed_spline = QAction(
            text="&Load seed spline...", parent=self
        )
        action_load_seed_spline.triggered.connect(
            slot=self.load_seed_spline
        )
        file_menu.addAction(action_load_seed_spline)

        action_save_spline = QAction(
            text="&Save current spline as seed", parent=self
        )
        action_save_spline.triggered.connect(slot=self.save_seed_spline)
        file_menu.addAction(action_save_spline)

        file_menu.addSeparator()

        action_close = QAction(text="&Close Window", parent=self)
        action_close.setShortcut(QKeySequence("Ctrl+W"))
        action_close.triggered.connect(slot=self.close)
        file_menu.addAction(action_close)

        action_quit = QAction(text="&Quit", parent=self)
        action_quit.setShortcut(QKeySequence("Ctrl+Q"))
        action_quit.triggered.connect(slot=self.close)
        file_menu.addAction(action_quit)

        action_menu = menu_bar.addMenu("&Action")

        self.action_track = QAction(text="&Track", parent=self)
        self.action_track.setShortcut(QKeySequence("Ctrl+T"))
        self.action_track.triggered.connect(slot=self.run_tracking)
        self.action_track.setEnabled(False)
        action_menu.addAction(self.action_track)

        self.action_track_curr = QAction(
            text="Track &current frame", parent=self
        )
        self.action_track_curr.setShortcut(QKeySequence("Ctrl+F"))
        self.action_track_curr.triggered.connect(
            slot=self.track_current_frame_action
        )
        self.action_track_curr.setEnabled(False)
        action_menu.addAction(self.action_track_curr)

        self.action_resample = QAction(
            text="&Resample Splines...", parent=self
        )
        self.action_resample.setShortcut(QKeySequence("Ctrl+R"))
        self.action_resample.triggered.connect(slot=self.resample_splines)
        self.action_resample.setEnabled(False)
        action_menu.addAction(self.action_resample)

        action_menu.addSeparator()

        self.action_apply_seed = QAction(
            text="&Apply seed spline", parent=self
        )
        self.action_apply_seed.triggered.connect(
            slot=self.apply_seed_spline
        )
        self.action_apply_seed.setEnabled(False)
        action_menu.addAction(self.action_apply_seed)

        self.action_clear_splines = QAction(
            text="&Clear All Splines", parent=self
        )
        self.action_clear_splines.triggered.connect(
            slot=self.clear_all_splines
        )
        action_menu.addAction(self.action_clear_splines)

        nav_menu = menu_bar.addMenu("&Navigation")

        action_prev = QAction(text="&Previous Frame", parent=self)
        action_prev.setShortcut(QKeySequence(Qt.Key.Key_Left))
        action_prev.triggered.connect(slot=self._prev_frame)
        nav_menu.addAction(action_prev)

        action_next = QAction(text="&Next Frame", parent=self)
        action_next.setShortcut(QKeySequence(Qt.Key.Key_Right))
        action_next.triggered.connect(slot=self._next_frame)
        nav_menu.addAction(action_next)

    def _init_snake_controls(self, layout: QVBoxLayout) -> None:
        """
        Construct and bind text entry controls for the snake parameters.

        Parameters
        ----------
        layout : QVBoxLayout
            The parent layout to append the controls into.

        Returns
        -------
        None

        Examples
        --------
        >>> # Called internally during UI construction
        """
        controls_layout = QHBoxLayout()

        # What: Ensure inputs are positive floating-point numbers.
        # Why: Negative weights will destabilize the energy function.
        validator = QDoubleValidator(
            bottom=0.0, top=float("inf"), decimals=4, parent=self
        )
        validator.setNotation(
            QDoubleValidator.Notation.StandardNotation
        )

        lbl_alpha = QLabel(text="Alpha:", parent=self)
        self.edit_alpha = QLineEdit(parent=self)
        self.edit_alpha.setValidator(validator)
        self.edit_alpha.setText(str(self.model.config.snake.alpha))
        self.edit_alpha.editingFinished.connect(slot=self._update_params)

        lbl_lambda1 = QLabel(text="Lambda1:", parent=self)
        self.edit_lambda1 = QLineEdit(parent=self)
        self.edit_lambda1.setValidator(validator)
        self.edit_lambda1.setText(str(self.model.config.snake.lambda1))
        self.edit_lambda1.editingFinished.connect(slot=self._update_params)

        lbl_band = QLabel(text="Band Penalty:", parent=self)
        self.edit_band = QLineEdit(parent=self)
        self.edit_band.setValidator(validator)
        self.edit_band.setText(str(self.model.config.snake.band_penalty))
        self.edit_band.editingFinished.connect(slot=self._update_params)

        self.btn_reset_params = QPushButton(
            text="Reset Params", parent=self
        )
        self.btn_reset_params.clicked.connect(slot=self._reset_params)

        controls_layout.addWidget(lbl_alpha)
        controls_layout.addWidget(self.edit_alpha)
        controls_layout.addWidget(lbl_lambda1)
        controls_layout.addWidget(self.edit_lambda1)
        controls_layout.addWidget(lbl_band)
        controls_layout.addWidget(self.edit_band)
        controls_layout.addWidget(self.btn_reset_params)

        layout.addLayout(controls_layout)

    def _update_params(self) -> None:
        """
        Parse valid text entries back into the model configuration.

        Returns
        -------
        None
        """
        # What: Safely cast text to floats and update the model state.
        # Why: Applies the user's manual parameter tuning to the algorithm.
        try:
            alpha = float(self.edit_alpha.text())
            lambda1 = float(self.edit_lambda1.text())
            band = float(self.edit_band.text())

            self.model.config.snake.alpha = alpha
            self.model.config.snake.lambda1 = lambda1
            self.model.config.snake.band_penalty = band
        except ValueError:
            self.statusBar().showMessage(
                "Error: Parameter fields cannot be empty.", 5000
            )

    def _reset_params(self) -> None:
        """
        Restore the parameter states to their factory defaults.

        Returns
        -------
        None
        """
        # What: Overwrite current parameters with resource defaults.
        # Why: Allows quick recovery if the manual tracking breaks.
        self.model.reset_snake_parameters()

        self.edit_alpha.setText(str(self.model.config.snake.alpha))
        self.edit_lambda1.setText(str(self.model.config.snake.lambda1))
        self.edit_band.setText(str(self.model.config.snake.band_penalty))

        self.statusBar().showMessage(
            "Success: Snake parameters reset to resource defaults.", 5000
        )

    def _next_frame(self) -> None:
        """
        Advance exactly one frame index forward if valid.

        Returns
        -------
        None

        Examples
        --------
        >>> # Triggered by the "Next Frame" menu action
        >>> # window._next_frame()
        """
        # What: Prevent UI jumping while tracking is running.
        # Why: Interaction during processing causes state corruption.
        if self._is_tracking:
            return

        current_val: int = self.slider.value()
        if current_val < self.slider.maximum():
            self.slider.setValue(current_val + 1)

    def _prev_frame(self) -> None:
        """
        Rollback exactly one frame index backward if valid.

        Returns
        -------
        None

        Examples
        --------
        >>> # Triggered by the "Previous Frame" menu action
        >>> # window._prev_frame()
        """
        if self._is_tracking:
            return

        current_val: int = self.slider.value()
        if current_val > self.slider.minimum():
            self.slider.setValue(current_val - 1)

    def keyPressEvent(self, event: Any) -> None:
        """
        Intercept application-wide keyboard pushes to override
        arrow-key traversals.

        Parameters
        ----------
        event : Any
            The PyQt key press event data.

        Returns
        -------
        None

        Examples
        --------
        >>> # Triggered internally by PyQt on keystrokes
        """
        if not self.slider.isEnabled():
            return

        # What: Map left and right arrows to slider manipulation.
        # Why: Improves user accessibility and speed of navigation.
        if event.key() == Qt.Key.Key_Left:
            new_val = max(0, self.slider.value() - 1)
            self.slider.setValue(new_val)
        elif event.key() == Qt.Key.Key_Right:
            new_val = min(self.slider.maximum(), self.slider.value() + 1)
            self.slider.setValue(new_val)
        else:
            # Pass all other keys up the hierarchy
            super().keyPressEvent(event)

    def open_video(self) -> None:
        """
        Trigger file dialogue to target and parse a container video.

        Extracts the required length and configures the tracking timeline.

        Returns
        -------
        None

        Examples
        --------
        >>> # Triggered by the open video button click
        >>> # window.open_video()
        """
        # What: Prompt user for input video file.
        # Why: Defines the data source for processing.
        file_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption="Open video",
            directory="",
            filter=VIDEO_FILTER
        )

        if not file_path:
            return

        start_frame = self.model.open_video(file_path=file_path)

        self.slider.setRange(0, self.model.total_frames - 1)
        self.slider.setValue(start_frame)

        # What: Enable track controls now that media is loaded.
        # Why: Prevents operations on empty models.
        self.slider.setEnabled(True)
        self.btn_track.setEnabled(True)
        self.action_track.setEnabled(True)
        self.btn_track_curr.setEnabled(True)
        self.action_track_curr.setEnabled(True)

        self._read_and_display_frame(frame_idx=start_frame)

        if self.model.seed_spline:
            self.action_apply_seed.setEnabled(True)

    def _read_and_display_frame(self, frame_idx: int) -> None:
        """
        Command rendering updates on internal data states per frame.

        Parameters
        ----------
        frame_idx : int
            The target frame index to load and map.

        Returns
        -------
        None

        Examples
        --------
        >>> # Triggered when timeline slider moves
        >>> # window._read_and_display_frame(frame_idx=5)
        """
        # What: Fetch history if we are manually jumping frames.
        # Why: Keeps user edits intact instead of overwriting them.
        if not self._is_tracking:
            if frame_idx in self.model.anchors_history:
                self.model.anchors = [
                    list(pt) for pt in self.model.anchors_history[frame_idx]
                ]

        self.model.read_frame(frame_idx=frame_idx)
        self.model.update_spline()

        self.action_resample.setEnabled(len(self.model.anchors) >= 2)

        self._display_canvas()

    def on_slider_change(self, value: int) -> None:
        """
        Callback bound to the application's global video timeline track.

        Parameters
        ----------
        value : int
            The new frame index from the slider.

        Returns
        -------
        None

        Examples
        --------
        >>> # Triggered when user scrubs the UI slider
        >>> # window.on_slider_change(value=10)
        """
        self._read_and_display_frame(frame_idx=value)

    def _display_canvas(self) -> None:
        """
        Calculate and map visual layers back up to the frontend UI array.

        Returns
        -------
        None

        Examples
        --------
        >>> # Internally triggers a screen redraw
        >>> # window._display_canvas()
        """
        if self.model.frame is None:
            return

        self.ax.clear()
        self.ax.set_axis_off()

        height, width = self.model.frame.shape[:2]

        # What: Render the background video frame layer.
        # Why: Provides visual context for point placement.
        self.ax.imshow(
            X=self.model.frame,
            aspect="equal",
            extent=[0, width, height, 0]
        )
        self.ax.set_xlim(0, width)
        self.ax.set_ylim(height, 0)

        # What: Plot the interpolated snake boundary.
        # Why: Shows the user the current model interpretation.
        if self.model.contour is not None:
            self.ax.plot(
                self.model.contour[:, 0],
                self.model.contour[:, 1],
                color="blue",
                linestyle="-",
                linewidth=1,
            )

        # What: Plot the interactive user anchor nodes.
        # Why: Allows direct manipulation.
        if self.model.anchors:
            pts: np.ndarray = np.array(object=self.model.anchors)
            self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color="red",
                marker="o",
                linestyle="None",
                markersize=3,
            )

        self.canvas.draw()

    def _get_closest_anchor(self, x: float, y: float) -> int | None:
        """
        Evaluate if user clicks exist within hit-box distances of data.

        Parameters
        ----------
        x : float
            The x-coordinate of the mouse event.
        y : float
            The y-coordinate of the mouse event.

        Returns
        -------
        int | None
            Index of the closest anchor, or None if none are near.

        Examples
        --------
        >>> # Resolves click targeting
        >>> # idx = window._get_closest_anchor(x=10.0, y=20.0)
        """
        if not self.model.anchors:
            return None

        # What: Calculate Euclidean distances from click to all nodes.
        # Why: Required to snap mouse interactions to points.
        pts: np.ndarray = np.array(object=self.model.anchors)
        click: np.ndarray = np.array(object=[x, y])
        dists: np.ndarray = np.linalg.norm(x=pts - click, axis=1)

        min_idx: int = int(np.argmin(a=dists))
        if dists[min_idx] < ANCHOR_CLICK_RADIUS:
            return min_idx

        return None

    def on_mouse_press(self, event: Any) -> None:
        """
        Callback mapped onto GUI left and right mouse click triggers.

        Parameters
        ----------
        event : Any
            The Matplotlib mouse press event object.

        Returns
        -------
        None

        Examples
        --------
        >>> # Handled by Matplotlib backend events
        """
        # What: Filter out off-canvas interactions.
        # Why: Prevents crashing when clicking on menus/borders.
        if event.inaxes != self.ax or event.xdata is None:
            return

        if event.dblclick:
            self.model.anchors.clear()
            self.model.update_spline()
            self._display_canvas()
            return

        closest_idx: int | None = self._get_closest_anchor(
            x=event.xdata, y=event.ydata
        )

        # What: Handle right-click deletions.
        # Why: Standard UI pattern for point removal.
        if event.button == 3:
            if closest_idx is not None:
                self.model.anchors.pop(closest_idx)
                self.model.update_spline()
                self._display_canvas()
            return

        # What: Handle left-click additions and drag initiation.
        # Why: UI entry point for defining/moving anchor nodes.
        if event.button == 1:
            if closest_idx is not None:
                self._drag_idx = closest_idx
            else:
                self.model.anchors.append([event.xdata, event.ydata])
                self.model.update_spline()
                self._display_canvas()

    def on_mouse_motion(self, event: Any) -> None:
        """
        Follow mouse vector mapping strings while UI triggers are held.

        Parameters
        ----------
        event : Any
            The Matplotlib mouse motion event object.

        Returns
        -------
        None

        Examples
        --------
        >>> # Handled continuously during point dragging
        """
        if self._drag_idx is None or event.inaxes != self.ax:
            return

        # What: Actively update the position of the dragged point.
        # Why: Provides real-time visual feedback.
        if event.xdata is not None and event.ydata is not None:
            self.model.anchors[self._drag_idx] = [event.xdata, event.ydata]
            self.model.update_spline()
            self._display_canvas()

    def on_mouse_release(self, event: Any) -> None:
        """
        Release mapping targets when UI mouse interactions stop.

        Parameters
        ----------
        event : Any
            The Matplotlib mouse release event object.

        Returns
        -------
        None

        Examples
        --------
        >>> # Drops the node lock when mouse unclicks
        """
        # What: Clear the drag target variable.
        # Why: Finalizes the point interaction cleanly.
        if event.button == 1:
            self._drag_idx = None

    def save_results_to_csv(self) -> None:
        """
        Invoke file writing interfaces via standardized OS save dialog.

        Returns
        -------
        None

        Examples
        --------
        >>> # Opens the native file explorer to save states
        >>> # window.save_results_to_csv()
        """
        if not self.model.anchors_history:
            self.statusBar().showMessage(
                "Warning: No tracking data to save.", 5000
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption="Save Tracking Results",
            directory="",
            filter="CSV Files (*.csv)",
        )

        if not file_path:
            return

        self.model.save_csv(file_path=file_path)
        self.statusBar().showMessage(
            f"Success: Results saved to {file_path}", 5000
        )

    def load_results_from_csv(self) -> None:
        """
        Invoke file reading interfaces via standardized OS load dialog.

        Returns
        -------
        None

        Examples
        --------
        >>> # Overwrites current session with loaded CSV state
        >>> # window.load_results_from_csv()
        """
        file_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption="Load tracking results",
            directory="",
            filter="CSV Files (*.csv)",
        )

        if not file_path:
            return

        try:
            self.model.load_csv(file_path=file_path)

            if self.model.current_frame_idx in self.model.anchors_history:
                pts = self.model.anchors_history[
                    self.model.current_frame_idx
                ]
                self.model.anchors = [list(pt) for pt in pts]
                self.model.update_spline()
                self._display_canvas()

            self.statusBar().showMessage(
                "Success: Results loaded successfully.", 5000
            )

        except Exception as e:
            self.statusBar().showMessage(
                f"Error: Failed to load CSV: {e}", 5000
            )

    def run_tracking(self) -> None:
        """
        Temporarily disable interactions while executing the Cython
        algorithm tracking bounds pass forwards and backward.

        Returns
        -------
        None

        Examples
        --------
        >>> # Starts full pipeline automation pass
        >>> # window.run_tracking()
        """
        if not self.model.anchors or self.model.container is None:
            return

        # What: Lock the UI buttons and menus.
        # Why: Prevents concurrent modifications to data maps.
        self.slider.setEnabled(False)
        self.btn_track.setEnabled(False)
        self.action_track.setEnabled(False)
        self.btn_track_curr.setEnabled(False)
        self.action_track_curr.setEnabled(False)
        self.action_resample.setEnabled(False)

        self._is_tracking = True
        start_idx: int = self.slider.value()

        init_anchors: list[list[float]] = [list(a) for a in self.model.anchors]

        for frame_idx in range(start_idx + 1, self.model.total_frames):
            self.slider.setValue(frame_idx)
            QApplication.processEvents()
            self.model.process_frame(frame_idx=frame_idx)
            self._display_canvas()

        self.model.anchors = [list(a) for a in init_anchors]
        self.model.read_frame(frame_idx=start_idx)
        self.model.update_spline()

        for frame_idx in range(start_idx - 1, -1, -1):
            self.slider.setValue(frame_idx)
            QApplication.processEvents()
            self.model.process_frame(frame_idx=frame_idx)
            self._display_canvas()

        self._is_tracking = False

        # What: Restore UI interactions.
        # Why: Tracking cycle finished successfully.
        self.slider.setEnabled(True)
        self.btn_track.setEnabled(True)
        self.action_track.setEnabled(True)
        self.btn_track_curr.setEnabled(True)
        self.action_track_curr.setEnabled(True)

        self.action_resample.setEnabled(len(self.model.anchors) >= 2)
        self.slider.setValue(start_idx)

    def track_current_frame_action(self) -> None:
        """
        Action callback to trigger frame-specific snake calculations.

        Returns
        -------
        None

        Examples
        --------
        >>> # Executes isolated single-frame active contour logic
        >>> # window.track_current_frame_action()
        """
        if self.model.container is None:
            return

        self.model.track_current_frame()
        self._display_canvas()

        self.action_resample.setEnabled(len(self.model.anchors) >= 2)

    def resample_splines(self) -> None:
        """
        Recalculate internal history arrays to re-pad spacing densities.

        Returns
        -------
        None

        Examples
        --------
        >>> # Normalizes spacing of generated/edited points
        >>> # window.resample_splines()
        """
        if not self.model.anchors or len(self.model.anchors) < 2:
            return

        current_count: int = len(self.model.anchors)

        # What: Present input box for custom density sizes.
        # Why: Users may need high fidelity curves for specific data.
        num_points, ok = QInputDialog.getInt(
            self,
            "Resample splines",
            "Number of control points:",
            value=current_count,
            min=2,
            max=500,
        )

        if not ok or num_points == current_count:
            return

        for frame_idx, pts_list in self.model.anchors_history.items():
            pts: np.ndarray = np.array(object=pts_list, dtype=np.float64)
            n_pts: int = len(pts)
            if n_pts < 2:
                continue

            diffs: np.ndarray = np.diff(a=pts, axis=0)
            dists: np.ndarray = np.linalg.norm(x=diffs, axis=1)
            k: np.ndarray = np.insert(
                arr=np.cumsum(a=dists), obj=0, values=0.0
            )
            k_new: np.ndarray = np.linspace(
                start=0, stop=k[-1], num=num_points
            )

            # Linear vs cubic evaluation based on point volume
            if n_pts == 2:
                interp_func = interp1d(x=k, y=pts, axis=0)
            else:
                interp_func = PchipInterpolator(x=k, y=pts, axis=0)

            new_pts: np.ndarray = interp_func(x=k_new)
            self.model.anchors_history[frame_idx] = new_pts.tolist()

        if self.model.current_frame_idx in self.model.anchors_history:
            self.model.anchors = [
                list(pt) for pt in
                self.model.anchors_history[self.model.current_frame_idx]
            ]

        self.model.update_spline()
        self._display_canvas()
        self.statusBar().showMessage(
            f"Success: Resampled splines to {num_points} control points.",
            5000
        )

    def save_seed_spline(self) -> None:
        """
        Record the active mapping points layer directly as a CSV template.

        Returns
        -------
        None

        Examples
        --------
        >>> # Exports the active contour to be reused later
        >>> # window.save_seed_spline()
        """
        if not self.model.anchors:
            self.statusBar().showMessage("Warning: No spline to save.", 5000)
            return

        file_path, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption="Save seed spline",
            directory="",
            filter="CSV Files (*.csv)",
        )

        if not file_path:
            return

        try:
            with open(file=file_path, mode="w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["point_id", "x", "y"])
                for i, (x, y) in enumerate(self.model.anchors):
                    writer.writerow([i, x, y])

            self.statusBar().showMessage(
                f"Success: Spline saved to {file_path}", 5000
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to save spline: {e}"
            )

    def load_seed_spline(self) -> None:
        """
        Trigger dialogue to inject formatted CSV files directly as seed map.

        Returns
        -------
        None

        Examples
        --------
        >>> # Imports and applies a new starting contour template
        >>> # window.load_seed_spline()
        """
        # What: Enforce data protection blocks before applying new seeds.
        # Why: Applying a new master seed wipes active manual sessions.
        if len(self.model.anchors_history) > 1:
            reply = QMessageBox.question(
                self,
                "Confirm discard",
                (
                    "Loading a new seed spline will discard all current "
                    "tracking data. Proceed?"
                ),
                buttons=(
                    QMessageBox.StandardButton.Yes |
                    QMessageBox.StandardButton.No
                ),
                defaultButton=QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        file_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption="Load Spline",
            directory="",
            filter="CSV Files (*.csv)",
        )

        if not file_path:
            return

        try:
            self.model.load_seed_spline_file(file_path=file_path)
            if self.model.seed_spline:
                self.model.anchors = [
                    list(pt) for pt in self.model.seed_spline
                ]
                self.model.anchors_history.clear()
                self.model.anchors_history[self.model.current_frame_idx] = [
                    list(pt) for pt in self.model.anchors
                ]

                if self.model.total_frames > 0:
                    self.action_apply_seed.setEnabled(True)

                self.model.update_spline()
                self._display_canvas()
                self.statusBar().showMessage(
                    "Success: Seed spline loaded.", 5000
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Format Error",
                f"Failed to load spline correctly.\n\n{e}"
            )

    def apply_seed_spline(self) -> None:
        """
        Immediately replace all layer history mappings using template map.

        Returns
        -------
        None

        Examples
        --------
        >>> # Overwrites the active points with the master seed template
        >>> # window.apply_seed_spline()
        """
        if self.model.seed_spline is None:
            return

        # What: Enforce data protection blocks before applying new seeds.
        # Why: Applying a new master seed wipes active manual sessions.
        if len(self.model.anchors_history) > 1:
            reply = QMessageBox.question(
                self,
                "Confirm apply",
                (
                    "Applying the seed spline will discard all "
                    "current tracking data. Proceed?"
                ),
                buttons=(
                    QMessageBox.StandardButton.Yes |
                    QMessageBox.StandardButton.No
                ),
                defaultButton=QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self.model.anchors = [list(pt) for pt in self.model.seed_spline]
        self.model.anchors_history.clear()
        self.model.anchors_history[self.model.current_frame_idx] = [
            list(pt) for pt in self.model.anchors
        ]

        self.model.update_spline()
        self._display_canvas()
        self.statusBar().showMessage("Success: Seed spline applied.", 5000)

    def clear_all_splines(self) -> None:
        """
        Delete all history variables after a standard prompt.

        Returns
        -------
        None
        """
        if self.model.anchors_history:
            reply = QMessageBox.question(
                self,
                "Confirm clear",
                "This will discard all tracking data. Proceed?",
                buttons=(
                    QMessageBox.StandardButton.Yes |
                    QMessageBox.StandardButton.No
                ),
                defaultButton=QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # What: Wipe current variables empty.
        # Why: Ensures visual state reset.
        self.model.anchors.clear()
        self.model.anchors_history.clear()
        self.model.contour = None

        self._display_canvas()
        self.statusBar().showMessage("Success: All splines cleared.", 5000)


def launch_gui(
    video_path: str | None = None,
    seed_path: str | None = None
) -> None:
    """
    Application entry point for the GUI.

    Parameters
    ----------
    video_path : str | None, optional
        Automatically bind video on load. Defaults to None.
    seed_path : str | None, optional
        Automatically load configured seed splines. Defaults to None.

    Returns
    -------
    None

    Examples
    --------
    >>> from super_slurpy.gui import launch_gui
    >>> launch_gui(video_path="input.mp4", seed_path="seed.csv")
    """
    app = QApplication(sys.argv)
    window = SlurpyGui()

    if seed_path:
        try:
            window.model.load_seed_spline_file(file_path=seed_path)
        except Exception as e:
            print(f"Warning: Failed to load CLI seed spline: {e}")

    # What: Initialize the loaded video directly on startup.
    # Why: Enables direct drag-and-drop or CLI booting pipelines.
    if video_path:
        start_frame = window.model.open_video(file_path=video_path)
        window.slider.setRange(0, window.model.total_frames - 1)
        window.slider.setValue(start_frame)

        window.slider.setEnabled(True)
        window.btn_track.setEnabled(True)
        window.action_track.setEnabled(True)
        window.btn_track_curr.setEnabled(True)
        window.action_track_curr.setEnabled(True)

        window._read_and_display_frame(frame_idx=start_frame)
        if window.model.seed_spline:
            window.action_apply_seed.setEnabled(True)

    window.show()
    sys.exit(app.exec())
