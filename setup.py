from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np
import os

# Path to our package source
pkg_path = os.path.join("src", "snake_lib")

extensions = [
    Extension(
        name="snake_lib.core",  # Note the dot notation for submodules
        sources=[
            os.path.join(pkg_path, "core.pyx"),
            os.path.join(pkg_path, "snake.c")
        ],
        include_dirs=[np.get_include(), pkg_path],
    )
]

setup(
    ext_modules=cythonize(
        extensions,
        compiler_directives={'language_level': "3"})
)
