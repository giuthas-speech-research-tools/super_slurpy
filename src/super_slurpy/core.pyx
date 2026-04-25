
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

import numpy as np
cimport numpy as cnp

# Import the C function we defined in the .pxd file
from .core cimport snake_create_adaptive

def make_snake(
    double[:, ::1] img,        # The ::1 ensures the array is C-contiguous in memory
    double[:, ::1] egrad,
    double[:, ::1] init_pts,
    int[::1] delta,
    double band_penalty,
    double alpha,
    double lambda1,
    int use_band_energy
):
    """
    Execute the adaptive snake (active contour) algorithm.
    
    Parameters
    ----------
    img : ndarray
        The input image as a 2D NumPy array of doubles.
    egrad : ndarray
        The external (gradient) energy data as a 2D NumPy array.
    init_pts : ndarray
        Initial anchor points for the snake (N x 2 array).
    delta : ndarray
        Search region values for each snaxel (1D array of ints).
    band_penalty : float
        Penalty value for band energy optimization.
    alpha : float
        Elasticity parameter (beta is calculated as 1 - alpha).
    lambda1 : float
        Weighting for energy components (lambda2 is 1 - lambda1).
    use_band_energy : int
        Integer (0 or 1) to toggle band energy optimization.

    Returns
    -------
    tuple
        (snake_pts, snake_energy, internal_energy, external_energy)
    """
    
    # 1. Extract dimensions directly from the memoryview
    cdef int rows = img.shape[0]
    cdef int cols = img.shape[1]
    cdef int ninit = init_pts.shape[0]

    # 2. Derived parameters
    cdef double beta = 1.0 - alpha
    cdef double lambda2 = 1.0 - lambda1

    # 3. Handle data layout (Interleaving X and Y)
    # Allocate a flat 1D numpy array for the C function
    cdef cnp.ndarray[cnp.float64_t, ndim=1] init_pts_c = np.empty(ninit * 2, dtype=np.float64)
    cdef int i
    
    # Fast Cython loop: This compiles to pure C to interleave the points
    for i in range(ninit):
        init_pts_c[i * 2] = init_pts[i, 0]
        init_pts_c[i * 2 + 1] = init_pts[i, 1]

    # 4. Allocate output buffers
    cdef cnp.ndarray[cnp.float64_t, ndim=1] snake_pts_c = np.empty(ninit * 2, dtype=np.float64)
    cdef cnp.ndarray[cnp.float64_t, ndim=1] snake_en = np.empty(ninit, dtype=np.float64)
    cdef cnp.ndarray[cnp.float64_t, ndim=1] snake_int_en = np.empty(ninit, dtype=np.float64)
    cdef cnp.ndarray[cnp.float64_t, ndim=1] snake_ext_en = np.empty(ninit, dtype=np.float64)

    # 5. Get raw C pointers from the Memoryviews/Arrays
    # Using &array[0,0] or &array[0] safely extracts the underlying C pointer
    cdef double* img_ptr = &img[0, 0]
    cdef double* egrad_ptr = &egrad[0, 0]
    cdef int* delta_ptr = &delta[0]
    
    cdef double* init_pts_ptr = &init_pts_c[0]
    cdef double* snake_pts_ptr = &snake_pts_c[0]
    cdef double* en_ptr = &snake_en[0]
    cdef double* int_en_ptr = &snake_int_en[0]
    cdef double* ext_en_ptr = &snake_ext_en[0]

    # 6. Execute the C function
    # 'with nogil' releases the GIL. Background threading in PyQt will now work perfectly.
    with nogil:
        snake_create_adaptive(
            img_ptr, egrad_ptr, cols, rows,
            init_pts_ptr, ninit, delta_ptr,
            alpha, beta, lambda1, lambda2,
            band_penalty, use_band_energy,
            snake_pts_ptr, en_ptr, int_en_ptr, ext_en_ptr
        )

    # 7. Reshape the flat 1D point array back to a (N, 2) 2D array
    cdef cnp.ndarray[cnp.float64_t, ndim=2] out_pts = snake_pts_c.reshape((ninit, 2))

    return out_pts, snake_en, snake_int_en, snake_ext_en
    