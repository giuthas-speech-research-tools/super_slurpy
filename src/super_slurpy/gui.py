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

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
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


class SnakeGUI(QMainWindow):
    """
    Main application window for the Slurpy Contour Editor.
    """

    def __init__(self) -> None:
        """
        Initialize the PyQt Main Window Application Frame.
        """
        super().__init__()
        self.setWindowTitle(title="Slurpy Contour Editor")
        self.model = SlurpyModel()

        self._drag_idx: int | None = None
        self._is_tracking: bool = False

        self._init_ui()
        self._init_menus()

    def _init_ui(self) -> None:
        """
        Construct the PyQt UI elements and Matplotlib canvas.
        """
        main_widget = QWidget(parent=self)
        self.setCentralWidget(widget=main_widget)
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

        self.slider = QSlider(orientation=Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(slot=self.on_slider_change)
        layout.addWidget(self.slider)

        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(figure=self.figure)
        self.ax = self.figure.add_subplot(111)

        self.figure.subplots_adjust(
            left=0, right=1, bottom=0, top=1, wspace=0, hspace=0
        )
        self.ax.set_axis_off()
        layout.addWidget(self.canvas)

        self.canvas.mpl_connect(
            s="button_press_event", func=self.on_mouse_press
        )
        self.canvas.mpl_connect(
            s="motion_notify_event", func=self.on_mouse_motion
        )
        self.canvas.mpl_connect(
            s="button_release_event", func=self.on_mouse_release
        )

        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_load.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_track.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_save.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _init_menus(self) -> None:
        """
        Initialize the application menu bar and actions.
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
            text="&Save current spline as default", parent=self
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
        self.action_apply_seed.setEnabled(
            self.model.seed_spline is not None
        )
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

    def _next_frame(self) -> None:
        """
        Advance exactly one frame index forward if valid.
        """
        if self._is_tracking:
            return
            
        current_val: int = self.slider.value()
        if current_val < self.slider.maximum():
            self.slider.setValue(value=current_val + 1)

    def _prev_frame(self) -> None:
        """
        Rollback exactly one frame index backward if valid.
        """
        if self._is_tracking:
            return
            
        current_val: int = self.slider.value()
        if current_val > self.slider.minimum():
            self.slider.setValue(value=current_val - 1)

    def keyPressEvent(self, event: Any) -> None:
        """
        Intercept application-wide keyboard pushes to override
        arrow-key traversals.
        """
        if not self.slider.isEnabled():
            return

        if event.key() == Qt.Key.Key_Left:
            new_val = max(0, self.slider.value() - 1)
            self.slider.setValue(value=new_val)
        elif event.key() == Qt.Key.Key_Right:
            new_val = min(self.slider.maximum(), self.slider.value() + 1)
            self.slider.setValue(value=new_val)
        else:
            super().keyPressEvent(event)

    def open_video(self) -> None:
        """
        Trigger file dialogue to target and parse a container video.
        """
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
        self.slider.setValue(value=start_frame)

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
        """
        if not self._is_tracking:
            if frame_idx in self.model.anchors_history:
                self.model.anchors = [
                    list(pt) for pt in self.model.anchors_history[frame_idx]
                ]

        self.model.read_frame(frame_idx=frame_idx)
        self.model.update_spline()
        
        if hasattr(self, "action_resample"):
            self.action_resample.setEnabled(len(self.model.anchors) >= 2)
            
        self._display_canvas()

    def on_slider_change(self, value: int) -> None:
        """
        Callback bound to the application's global video timeline track.
        """
        self._read_and_display_frame(frame_idx=value)

    def _display_canvas(self) -> None:
        """
        Calculate and map visual layers back up to the frontend UI array.
        """
        if self.model.frame is None:
            return

        self.ax.clear()
        self.ax.set_axis_off()

        height, width = self.model.frame.shape[:2]

        self.ax.imshow(
            X=self.model.frame, 
            aspect="equal", 
            extent=[0, width, height, 0]
        )
        self.ax.set_xlim(0, width)
        self.ax.set_ylim(height, 0)

        # Plot interpolated borders
        if self.model.contour is not None:
            self.ax.plot(
                self.model.contour[:, 0],
                self.model.contour[:, 1],
                color="blue",
                linestyle="-",
                linewidth=1,
            )

        # Plot user-defined points
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
        """
        if not self.model.anchors:
            return None

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
        """
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

        # Right click to delete mapped points
        if event.button == 3:
            if closest_idx is not None:
                self.model.anchors.pop(closest_idx)
                self.model.update_spline()
                self._display_canvas()
            return

        # Left click to define or grab a given anchor point mapping
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
        """
        if self._drag_idx is None or event.inaxes != self.ax:
            return

        if event.xdata is not None and event.ydata is not None:
            self.model.anchors[self._drag_idx] = [event.xdata, event.ydata]
            self.model.update_spline()
            self._display_canvas()

    def on_mouse_release(self, event: Any) -> None:
        """
        Release mapping targets when UI mouse interactions stop.
        """
        if event.button == 1:
            self._drag_idx = None

    def save_results_to_csv(self) -> None:
        """
        Invoke file writing interfaces via standardized OS save dialog.
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
        """
        if not self.model.anchors or self.model.container is None:
            return

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
            self.slider.setValue(value=frame_idx)
            QApplication.processEvents()
            self.model.process_frame(frame_idx=frame_idx)
            self._display_canvas()

        self.model.anchors = [list(a) for a in init_anchors]
        self.model.read_frame(frame_idx=start_idx)
        self.model.update_spline()

        for frame_idx in range(start_idx - 1, -1, -1):
            self.slider.setValue(value=frame_idx)
            QApplication.processEvents()
            self.model.process_frame(frame_idx=frame_idx)
            self._display_canvas()

        self._is_tracking = False
        
        self.slider.setEnabled(True)
        self.btn_track.setEnabled(True)
        self.action_track.setEnabled(True)
        self.btn_track_curr.setEnabled(True)
        self.action_track_curr.setEnabled(True)
        
        self.action_resample.setEnabled(len(self.model.anchors) >= 2)
        self.slider.setValue(value=start_idx)

    def track_current_frame_action(self) -> None:
        """
        Action callback to trigger frame-specific snake calculations.
        """
        if self.model.container is None:
            return
            
        self.model.track_current_frame()
        self._display_canvas()
        
        if hasattr(self, "action_resample"):
            self.action_resample.setEnabled(len(self.model.anchors) >= 2)

    def resample_splines(self) -> None:
        """
        Recalculate internal history arrays to re-pad spacing densities.
        """
        if not self.model.anchors or len(self.model.anchors) < 2:
            return

        current_count: int = len(self.model.anchors)

        num_points, ok = QInputDialog.getInt(
            self,
            "Resample Splines",
            "Number of control points:",
            current_count,
            2,
            500,
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
                parent=self, title="Error", text=f"Failed to save spline: {e}"
            )

    def load_seed_spline(self) -> None:
        """
        Trigger dialogue to inject formatted CSV files directly as seed map.
        """
        if len(self.model.anchors_history) > 1:
            reply = QMessageBox.question(
                self,
                "Confirm discard",
                "Loading a new seed spline will discard all current "
                "tracking data. Proceed?",
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
                
                if hasattr(self, "action_apply_seed"):
                    self.action_apply_seed.setEnabled(True)
                    
                self.model.update_spline()
                self._display_canvas()
                self.statusBar().showMessage(
                    "Success: Seed spline loaded.", 5000
                )

        except Exception as e:
            QMessageBox.critical(
                parent=self, 
                title="Format Error", 
                text=f"Failed to load spline correctly.\n\n{e}"
            )

    def apply_seed_spline(self) -> None:
        """
        Immediately replace all layer history mappings using template map.
        """
        if self.model.seed_spline is None:
            return

        if len(self.model.anchors_history) > 1:
            reply = QMessageBox.question(
                self,
                "Confirm apply",
                "Applying the seed spline will discard all "
                "current tracking data. Proceed?",
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
        """
        if self.model.anchors_history:
            reply = QMessageBox.question(
                self,
                "Confirm Clear",
                "This will discard all tracking data. Proceed?",
                buttons=(
                    QMessageBox.StandardButton.Yes | 
                    QMessageBox.StandardButton.No
                ),
                defaultButton=QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

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
    """
    app = QApplication(sys.argv)
    window = SnakeGUI()
    
    if seed_path:
        try:
            window.model.load_seed_spline_file(file_path=seed_path)
        except Exception as e:
            print(f"Warning: Failed to load CLI seed spline: {e}")
            
    if video_path:
        start_frame = window.model.open_video(file_path=video_path)
        window.slider.setRange(0, window.model.total_frames - 1)
        window.slider.setValue(value=start_frame)
        
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