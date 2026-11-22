"""
Showcase of decimation of a STL file.
"""

import os

from design3d.stl import Stl

# STL model shipped with the scripts (avoids a network download)
FILE_NAME = os.path.join("..", "stl", "simple.stl")

# Load STL model using design3d
stl_model = Stl.load_from_file(FILE_NAME)
closed_triangle_shell = stl_model.to_closed_shell()

# Decimate and show model
decimated_closed_triangle_shell = closed_triangle_shell.decimate(50, verbose=True)
decimated_closed_triangle_shell.babylonjs()
