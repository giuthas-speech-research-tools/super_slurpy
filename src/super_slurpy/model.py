"""
Core data model and tracking logic for slurpy.

This module isolates the application state (video processing,
anchor points history, and active contour tracking) from the
GUI, allowing it to be used in headless batch processing.
"""

import csv
import importlib.resources
from pathlib import Path
from typing import Any, Iterator

import av
import numpy as np
from scipy.interpolate import PchipInterpolator, interp1d
from scipy.ndimage import gaussian_filter1d

from super_slurpy.config import load_config, load_resource_config
from super_slurpy.constants import (
    DEFAULT_SEED_SPLINE,
    DEFAULT_SPLINE_POINTS,
)
from super_slurpy.core import make_snake


class SlurpyModel:
    """
    Manages the video state, tracking history, and snake execution.

    Attributes
    ----------
    config : super_slurpy.config.SuperSlurpyConfig
        The application configuration.
    video_path : Path | None
        Path to the loaded video.
    container : Any | None
        PyAV container.
    video_stream : Any | None
        The video stream.
    total_frames : int
        Total number of frames in the video.
    frame : np.ndarray | None
        The current RGB frame.
    current_frame_idx : int
        Index of the current frame.
    anchors : list[list[float]]
        Current active anchors.
    anchors_history : dict[int, list[list[float]]]
        Dictionary mapping frame index to anchor points.
    contour : np.ndarray | None
        The interpolated spline for the current anchors.
    seed_spline : list[list[float]] | None
        The loaded seed spline to apply to new videos.
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        """
        Initialize the model state.

        Parameters
        ----------
        config_dir : Path | None, optional
            Path to look for configurations. Defaults to None.
        """
        self.config = load_config(config_dir=config_dir)
        self.video_path: Path | None = None
        self.container: Any = None
        self.video_stream: Any = None
        self.total_frames: int = 0
        self.frame: np.ndarray | None = None
        self.current_frame_idx: int = 0

        self.anchors: list[list[float]] = []
        self.anchors_history: dict[int, list[list[float]]] = {}
        self.contour: np.ndarray | None = None

        self.seed_spline: list[list[float]] | None = None

        # Load the seed spline upon instantiation
        self._load_initial_seed_spline()

    def _load_initial_seed_spline(self) -> None:
        """
        Attempt to load the seed spline from package resources.

        Checks config paths and falls back to package data if missing.
        """
        filename = self.config.gui.seed_spline_file or DEFAULT_SEED_SPLINE
        if not filename:
            return

        # Check if the filename maps to a direct file path
        path = Path(filename)
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            self._parse_seed_csv(content=content)
            return

        # Fallback to resolving via importlib resources
        try:
            resource_path = importlib.resources.files(
                anchor="super_slurpy"
            ) / filename

            if resource_path.is_file():
                content = resource_path.read_text(encoding="utf-8")
                self._parse_seed_csv(content=content)

        except Exception as e:
            print(f"Warning: Failed to load package seed spline: {e}")

    def _parse_seed_csv(self, content: str) -> None:
        """
        Parse CSV content and set the seed spline.

        Parameters
        ----------
        content : str
            The raw string content of the CSV file.
        """
        reader = csv.reader(content.splitlines())

        # We manually invoke next to evaluate the header format
        header = next(reader, None)

        if header != ["point_id", "x", "y"]:
            return

        pts: list[list[float]] = []
        for row in reader:
            if len(row) == 3:
                pts.append([float(row[1]), float(row[2])])

        if pts:
            self.seed_spline = pts

    def load_seed_spline_file(self, file_path: str) -> None:
        """
        Load a seed spline from a specific file.

        Parameters
        ----------
        file_path : str
            The target file path.

        Raises
        ------
        FileNotFoundError
            If the target path is not a file.

        Examples
        --------
        >>> model = SlurpyModel()
        >>> model.load_seed_spline_file(file_path="seed.csv")
        """
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Seed file not found: {file_path}")

        self._parse_seed_csv(content=path.read_text(encoding="utf-8"))

    def reset_snake_parameters(self) -> None:
        """
        Reset the active contour parameters to the package defaults.

        Returns
        -------
        None

        Examples
        --------
        >>> model = SlurpyModel()
        >>> model.reset_snake_parameters()
        """
        default_config = load_resource_config()
        self.config.snake = default_config.snake

    def reset_particle_parameters(self) -> None:
        """
        Reset the particle model parameters to the package defaults.

        Returns
        -------
        None

        Examples
        --------
        >>> model = SlurpyModel()
        >>> model.reset_particle_parameters()
        """
        default_config = load_resource_config()
        self.config.particle = default_config.particle

    def open_video(self, file_path: str) -> int:
        """
        Open a video and calculate the starting frame based on config.

        Parameters
        ----------
        file_path : str
            The target path of the video file to be loaded.

        Returns
        -------
        int
            The calculated starting frame index.

        Examples
        --------
        >>> model = SlurpyModel()
        >>> start_idx = model.open_video(file_path="video.mp4")
        >>> print(start_idx)
        0
        """
        self.video_path = Path(file_path)
        self.container = av.open(file=str(self.video_path))
        self.video_stream = self.container.streams.video[0]

        self.total_frames = self.video_stream.frames

        # Fix 0 length containers by falling back to arbitrary large number
        if self.total_frames == 0:
            self.total_frames = 1000

        start_frame: int = 0
        if self.config.gui.default_frame is not None:
            start_frame = self.config.gui.default_frame
        elif self.config.gui.proportional_frame is not None:
            start_frame = int(
                self.config.gui.proportional_frame * (self.total_frames - 1)
            )

        return max(0, min(start_frame, self.total_frames - 1))

    def read_frame(self, frame_idx: int) -> None:
        """
        Read a specific frame and extract standard RGB formatting.

        Parameters
        ----------
        frame_idx : int
            The absolute frame index to seek and read.

        Examples
        --------
        >>> model = SlurpyModel()
        >>> model.open_video(file_path="video.mp4")
        >>> model.read_frame(frame_idx=10)
        """
        if self.container is None or self.video_stream is None:
            return

        self.current_frame_idx = frame_idx

        fps: float = float(self.video_stream.average_rate)
        time_base: float = float(self.video_stream.time_base)

        if fps > 0 and time_base > 0:
            target_sec: float = frame_idx / fps
            target_pts: int = int(target_sec / time_base)
            self.container.seek(offset=target_pts, stream=self.video_stream)

        # Grab only the very first returned frame
        for frame in self.container.decode(video=0):
            self.frame = frame.to_ndarray(format="rgb24")
            break

    def update_spline(self) -> None:
        """
        Calculate the interpolated contour and auto-save anchors.

        Uses PCHIP interpolation for smooth bounds and linear mappings
        for 2-point arrays. Updates internal contour state.

        Examples
        --------
        >>> model = SlurpyModel()
        >>> model.anchors = [[0.0, 0.0], [10.0, 10.0]]
        >>> model.update_spline()
        """
        n_anchors: int = len(self.anchors)

        self.anchors_history[self.current_frame_idx] = [
            list(pt) for pt in self.anchors
        ]

        if n_anchors < 2:
            self.contour = None
            return

        pts: np.ndarray = np.array(object=self.anchors)
        n_points: int = DEFAULT_SPLINE_POINTS

        diffs: np.ndarray = np.diff(a=pts, axis=0)
        dists: np.ndarray = np.linalg.norm(x=diffs, axis=1)
        k: np.ndarray = np.insert(arr=np.cumsum(a=dists), obj=0, values=0.0)
        k_new: np.ndarray = np.linspace(start=0, stop=k[-1], num=n_points)

        # Linear mapping vs piecewise cubic mappings based on length
        if n_anchors == 2:
            interp_func = interp1d(x=k, y=pts, axis=0)
        else:
            interp_func = PchipInterpolator(x=k, y=pts, axis=0)

        self.contour = interp_func(x=k_new)

    def _compute_egrad(
        self,
        img: np.ndarray,
        sigma: float = 1.0
    ) -> np.ndarray:
        """
        Calculate the normalized external gradient energy map.

        Parameters
        ----------
        img : np.ndarray
            The image matrix array.
        sigma : float, optional
            The Gaussian filter deviation. Defaults to 1.0.

        Returns
        -------
        np.ndarray
            The continuous normalized energy map gradient.
        """
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

    def _process_frame_snake(self, frame_idx: int) -> None:
        """
        Internal helper to run snake optimization for a single frame.

        Parameters
        ----------
        frame_idx : int
            The targeted frame index.
        """
        self.read_frame(frame_idx=frame_idx)
        if self.frame is None or not self.anchors:
            return

        current_pts: np.ndarray = np.array(
            object=self.anchors, dtype=np.float64
        )
        current_pts = np.ascontiguousarray(a=current_pts)
        n_anchors: int = current_pts.shape[0]

        delta: np.ndarray = np.full(
            shape=n_anchors, fill_value=10, dtype=np.int32
        )

        img_gray: np.ndarray = np.mean(a=self.frame, axis=2)
        img_double: np.ndarray = np.ascontiguousarray(
            a=img_gray, dtype=np.float64
        )

        # Acquire boundary detection mappings
        egrad: np.ndarray = self._compute_egrad(img=img_double)

        # Push to the custom optimized Cython wrapper extension
        results = make_snake(
            img_double,
            egrad,
            current_pts,
            delta,
            self.config.snake.band_penalty,
            self.config.snake.alpha,
            self.config.snake.lambda1,
            use_band_energy=0,
        )

        tracked_pts: np.ndarray = results[0]
        if tracked_pts.ndim == 1:
            current_pts = tracked_pts.reshape(n_anchors, 2)
        else:
            current_pts = tracked_pts

        self.anchors = current_pts.tolist()
        self.update_spline()

    def _process_frame_particle(
        self, frame_idx: int, base_anchors: list[list[float]]
    ) -> list[list[float]]:
        """
        Internal helper to run particle filter for a single frame.

        Parameters
        ----------
        frame_idx : int
            The targeted frame index.
        base_anchors : list[list[float]]
            The prior contour to base predictions on.

        Returns
        -------
        list[list[float]]
            The resulting optimized points.
        """
        from super_slurpy.motion import run_particle_filter

        self.read_frame(frame_idx=frame_idx)
        if self.frame is None or not base_anchors:
            return base_anchors

        num_particles = self.config.particle.num_particles
        noise_scale = self.config.particle.noise_scale

        base_contour = np.array(object=base_anchors, dtype=np.float64)

        # What: Generate particle hypotheses and fit the contour.
        # Why: Seeds the evaluation pool for contour fitting.
        particles = run_particle_filter(
            base_contour=base_contour,
            num_particles=num_particles,
            noise_scale=noise_scale,
        )

        # What: Assign the best particle to the current frame.
        # Why: Progresses the tracking sequence.
        best_particle = particles[0]
        self.anchors = best_particle.tolist()
        self.update_spline()

        return self.anchors

    def run_snake_tracking(self, start_idx: int) -> Iterator[int]:
        """
        Run snake tracking forward and backward from a starting frame.

        Parameters
        ----------
        start_idx : int
            The original initialization frame index.

        Yields
        ------
        int
            The frame index currently being processed.

        Examples
        --------
        >>> model = SlurpyModel()
        >>> model.anchors = [[0.0, 0.0], [10.0, 10.0]]
        >>> list(model.run_snake_tracking(start_idx=0))
        """
        if not self.anchors or self.container is None:
            return

        init_anchors: list[list[float]] = [list(a) for a in self.anchors]

        # Forward Pass evaluation loop
        for frame_idx in range(start_idx + 1, self.total_frames):
            self._process_frame_snake(frame_idx=frame_idx)
            yield frame_idx

        # Reset State and anchor data back to target zero
        self.anchors = [list(a) for a in init_anchors]
        self.read_frame(frame_idx=start_idx)
        self.update_spline()

        # Backward Pass evaluation loop
        for frame_idx in range(start_idx - 1, -1, -1):
            self._process_frame_snake(frame_idx=frame_idx)
            yield frame_idx

    def run_particle_tracking(self, start_idx: int) -> Iterator[int]:
        """
        Execute particle filter tracking across the entire video.

        Parameters
        ----------
        start_idx : int
            The index of the frame to begin tracking from.

        Yields
        ------
        int
            The frame index currently being processed.

        Examples
        --------
        >>> model = SlurpyModel()
        >>> list(model.run_particle_tracking(start_idx=10))
        """
        if not self.anchors or self.container is None:
            return

        init_anchors: list[list[float]] = [list(a) for a in self.anchors]
        current_anchors: list[list[float]] = [list(a) for a in self.anchors]

        # Forward Pass
        for frame_idx in range(start_idx + 1, self.total_frames):
            current_anchors = self._process_frame_particle(
                frame_idx=frame_idx, base_anchors=current_anchors
            )
            yield frame_idx

        # Reset State and anchor data back to target zero
        self.anchors = [list(a) for a in init_anchors]
        self.read_frame(frame_idx=start_idx)
        self.update_spline()

        # Backward Pass
        current_anchors = [list(a) for a in init_anchors]
        for frame_idx in range(start_idx - 1, -1, -1):
            current_anchors = self._process_frame_particle(
                frame_idx=frame_idx, base_anchors=current_anchors
            )
            yield frame_idx

    def track_current_frame_snake(self) -> None:
        """
        Run snake tracking on the current frame only.

        Examples
        --------
        >>> model = SlurpyModel()
        >>> model.track_current_frame_snake()
        """
        if not self.anchors:
            if self.seed_spline:
                self.anchors = [list(pt) for pt in self.seed_spline]
            else:
                return

        self._process_frame_snake(frame_idx=self.current_frame_idx)

    def track_current_frame_particle(self) -> None:
        """
        Run particle tracking on the current frame only.

        Examples
        --------
        >>> model = SlurpyModel()
        >>> model.track_current_frame_particle()
        """
        if not self.anchors:
            if self.seed_spline:
                self.anchors = [list(pt) for pt in self.seed_spline]
            else:
                return

        self._process_frame_particle(
            frame_idx=self.current_frame_idx, base_anchors=self.anchors
        )

    def save_csv(self, file_path: str) -> None:
        """
        Export history to CSV format.

        Parameters
        ----------
        file_path : str
            The targeted absolute save output path.

        Examples
        --------
        >>> model = SlurpyModel()
        >>> model.anchors_history[0] = [[0.0, 0.0], [10.0, 10.0]]
        >>> model.save_csv(file_path="output.csv")
        """
        with open(file=file_path, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["frame", "point_id", "x", "y"])
            for frame_idx in sorted(self.anchors_history.keys()):
                pts = self.anchors_history[frame_idx]
                for i, (x, y) in enumerate(pts):
                    writer.writerow([frame_idx, i, x, y])

    def load_csv(self, file_path: str) -> None:
        """
        Load history from CSV mapping formats.

        Parameters
        ----------
        file_path : str
            The absolute reading path for extraction.

        Examples
        --------
        >>> model = SlurpyModel()
        >>> model.load_csv(file_path="output.csv")
        """
        new_history: dict[int, list[list[float]]] = {}
        with open(file=file_path, mode="r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                frame = int(row["frame"])
                x = float(row["x"])
                y = float(row["y"])

                # Assign to correct frame matrix groupings
                if frame not in new_history:
                    new_history[frame] = []

                new_history[frame].append([x, y])

        self.anchors_history = new_history
