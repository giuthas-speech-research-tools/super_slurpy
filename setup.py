"""
Setup script for compiling Cython extensions in Slurpy.
"""

import numpy as np
from Cython.Build import cythonize
from setuptools import Extension, setup

# Define the Cython extensions.
extensions = [
    Extension(
        name="super_slurpy.core",
        sources=[
            # 1. The Cython wrapper
            "src/super_slurpy/core.pyx",

            # 2. The core C algorithm files (from the old Makefile)
            "src/super_slurpy/_c_lib/snake.c",
            "src/super_slurpy/_c_lib/image.c",
            "src/super_slurpy/_c_lib/pnpoly.c",
            "src/super_slurpy/_c_lib/spline.c"
        ],
        include_dirs=[
            np.get_include(),
            "src/super_slurpy/_c_lib"  # To find snake.h, image.h, etc.
        ],
    )
]

# Run the compilation
setup(
    ext_modules=cythonize(
        module_list=extensions,
        compiler_directives={"language_level": "3"},
    )
)
