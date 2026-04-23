cdef extern from "snake.h":
    void snake_create_adaptive(
        double *img, double *egrad, int cols, int rows,
        double *init_pts, int ninit, int *delta,
        double alpha, double beta, double lambda1, double lambda2,
        double band_penalty, int use_band_energy,
        double *snake_pts, double *snake_energy,
        double *internal_snake_energy, double *external_snake_energy
    ) nogil