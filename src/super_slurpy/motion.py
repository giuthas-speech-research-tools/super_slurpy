"""
Motion Model and Particle Filter Tracking.

This module provides the statistical motion modeling and the
particle filter implementation for contour tracking.
"""

import numpy as np


class MotionModel:
    """
    Creates a motion model from sequential state variations.

    Attributes
    ----------
    variance : np.ndarray | None
        Standard deviation of the state differences.
    correlation : np.ndarray | None
        Correlation coefficient matrix of the state differences.
    """

    def __init__(self) -> None:
        self.variance: np.ndarray | None = None
        self.correlation: np.ndarray | None = None

    def fit(self, state_vectors: np.ndarray) -> None:
        """
        Compute the variance and correlation of state changes.

        Parameters
        ----------
        state_vectors : np.ndarray
            M x F matrix where M is the state dimension and F
            is the number of frames.

        Examples
        --------
        >>> import numpy as np
        >>> from super_slurpy.motion import MotionModel
        >>> model = MotionModel()
        >>> states = np.random.rand(5, 10)
        >>> model.fit(state_vectors=states)
        """
        # What: Calculate differences between consecutive frames.
        # Why: Represents the motion velocity of the contour.
        motion = np.diff(a=state_vectors, n=1, axis=1)

        # What: Compute standard deviation along the frame axis.
        # Why: Represents the expected magnitude of motion noise.
        self.variance = np.std(a=motion, axis=1, ddof=0)

        # What: Compute the correlation matrix of the motion.
        # Why: Captures relationships between state variables.
        self.correlation = np.corrcoef(x=motion)


def run_particle_filter(
    base_contour: np.ndarray,
    num_particles: int,
    noise_scale: float,
) -> list[np.ndarray]:
    """
    Generate perturbed contours for particle filter evaluation.

    Parameters
    ----------
    base_contour : np.ndarray
        The N x 2 array of the current contour vertices.
    num_particles : int
        The number of particles (contours) to generate.
    noise_scale : float
        Multiplier for the random noise applied to particles.

    Returns
    -------
    list[np.ndarray]
        A list of perturbed contour arrays.

    Examples
    --------
    >>> import numpy as np
    >>> from super_slurpy.motion import run_particle_filter
    >>> contour = np.random.rand(20, 2)
    >>> particles = run_particle_filter(
    ...     base_contour=contour,
    ...     num_particles=5,
    ...     noise_scale=1.0,
    ... )
    """
    particles = []

    for _ in range(num_particles):
        # What: Generate Gaussian noise matching the contour shape.
        # Why: Simulates potential state variations.
        noise = np.random.normal(
            loc=0.0,
            scale=noise_scale,
            size=base_contour.shape,
        )

        # What: Apply the noise to the base contour.
        # Why: Creates a new unique particle hypothesis.
        new_particle = base_contour + noise
        particles.append(new_particle)

    return particles