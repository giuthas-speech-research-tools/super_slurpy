"""
Active Shape Model (ASM) and Principal Component Analysis (PCA).

This module provides functionalities to learn the characteristic
shapes of tracked objects from training data.
"""

import numpy as np


def perform_pca(
    data_matrix: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Perform Principal Component Analysis using SVD.

    Parameters
    ----------
    data_matrix : np.ndarray
        M x N matrix with M the vector length and N the datasets.

    Returns
    -------
    tuple[np.ndarray, np.ndarray, np.ndarray]
        Eigenvalues, Eigenvectors, and the mean vector.

    Examples
    --------
    >>> import numpy as np
    >>> from super_slurpy.shape import perform_pca
    >>> data = np.random.rand(10, 5)
    >>> evals, evecs, mean_vec = perform_pca(data_matrix=data)
    """
    # What: Calculate the number of datasets.
    # Why: Needed to compute mean and normalize the matrix.
    n_sets = data_matrix.shape[1]

    # What: Compute the mean shape across all datasets.
    # Why: ASM requires mean-centered data for PCA.
    mean_vec = np.sum(a=data_matrix, axis=1, keepdims=True) / n_sets

    # What: Subtract mean and scale.
    # Why: Prepares data for SVD to yield true principal components.
    centered = (data_matrix - mean_vec) / np.sqrt(n_sets - 1)

    # What: Execute Singular Value Decomposition.
    # Why: Extracts the eigen structure without computing covariance.
    u_mat, s_mat, _ = np.linalg.svd(a=centered, full_matrices=False)

    evals = s_mat ** 2

    # What: Align eigenvector signs.
    # Why: Ensures deterministic outputs across different runs.
    signs = np.sign(x=u_mat[0, :])
    evecs = u_mat * signs

    return evals, evecs, mean_vec


class ActiveShapeModel:
    """
    Constructs and manages an Active Shape Model in 2D.

    Attributes
    ----------
    mean_shape : np.ndarray | None
        The mean vector of the aligned training shapes.
    eigenvectors : np.ndarray | None
        The principal modes of shape variation.
    eigenvalues : np.ndarray | None
        The variance explained by each principal component.
    """

    def __init__(self) -> None:
        self.mean_shape: np.ndarray | None = None
        self.eigenvectors: np.ndarray | None = None
        self.eigenvalues: np.ndarray | None = None

    def fit(
        self,
        training_data: list[np.ndarray],
        ref_type: str = "mean",
    ) -> None:
        """
        Align training shapes and compute the shape model.

        Parameters
        ----------
        training_data : list[np.ndarray]
            List of N x 2 arrays representing contour vertices.
        ref_type : str, optional
            Alignment reference, either "mean" or "first".
            Defaults to "mean".

        Examples
        --------
        >>> import numpy as np
        >>> from super_slurpy.shape import ActiveShapeModel
        >>> model = ActiveShapeModel()
        >>> shapes = [np.random.rand(20, 2) for _ in range(5)]
        >>> model.fit(training_data=shapes, ref_type="mean")
        """
        aligned_shapes = []

        for shape in training_data:
            # What: Calculate the total path length of the shape.
            # Why: Used to normalize scale across different samples.
            diffs = np.diff(a=shape, axis=0)
            length_avg = np.sum(a=np.sqrt(np.sum(a=diffs**2, axis=1)))

            aligned = np.copy(a=shape)

            # What: Remove translation based on the reference type.
            # Why: Centers all shapes to a common coordinate origin.
            if ref_type == "mean":
                aligned[:, 0] -= np.mean(a=shape[:, 0])
                aligned[:, 1] -= np.mean(a=shape[:, 1])
            elif ref_type == "first":
                aligned[:, 0] -= shape[0, 0]
                aligned[:, 1] -= shape[0, 1]

            # What: Normalize scale using the path length.
            # Why: Ensures shape variations are scale-invariant.
            aligned /= length_avg
            aligned_shapes.append(aligned.flatten())

        # What: Stack aligned shapes into an M x N matrix.
        # Why: Required format for PCA computation.
        data_matrix = np.column_stack(tup=aligned_shapes)

        evals, evecs, mean_vec = perform_pca(data_matrix=data_matrix)
        self.eigenvalues = evals
        self.eigenvectors = evecs
        self.mean_shape = mean_vec