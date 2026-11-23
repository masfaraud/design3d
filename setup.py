"""
Build script for the Cython extensions of design3d.

The package metadata are declared in pyproject.toml.
"""

import numpy as np
from setuptools import Extension, setup

from Cython.Build import cythonize  # isort: skip This prevent a build bug

extensions = [
    Extension(
        "design3d.core_compiled",
        ["src/design3d/core_compiled.pyx"],
        include_dirs=[np.get_include()],
    ),
    Extension(
        "design3d.nurbs.core",
        ["src/design3d/nurbs/core.pyx"],
        include_dirs=[np.get_include()],
    ),
    Extension(
        "design3d.nurbs.helpers",
        ["src/design3d/nurbs/helpers.pyx"],
        include_dirs=[np.get_include()],
    ),
    Extension(
        "design3d.nurbs.fitting",
        ["src/design3d/nurbs/fitting.py"],
        include_dirs=[np.get_include()],
    ),
    Extension(
        "design3d.nurbs.operations",
        ["src/design3d/nurbs/operations.py"],
        include_dirs=[np.get_include()],
    ),
]

setup(
    ext_modules=cythonize(extensions, language_level="3"),
    include_dirs=[np.get_include()],
)
