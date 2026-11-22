"""
Showcase of decimation of a STL file.
"""

import os

from design3d.display import Mesh3D

# STL model shipped with the scripts (avoids a network download in CI)
FILE_NAME = os.path.join("..", "stl", "simple.stl")

# Load STL model using design3d
mesh = Mesh3D.from_stl_file(FILE_NAME)

# Decimate and show model
decimated_mesh = mesh.decimate(500, verbose=True)
decimated_mesh = decimated_mesh.split_shared_vertices()  # for display purpose
decimated_mesh.babylonjs()
