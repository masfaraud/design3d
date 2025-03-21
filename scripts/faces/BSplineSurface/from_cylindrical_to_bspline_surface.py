#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: s.bendjebla
"""

# %% Libraries

import numpy as npy

import design3d as d3d
import design3d.faces as d3df
import design3d.step as d3ds
from design3d import surfaces

# %% Read Step file

file_path = 'cylindrical_surface_1.step'

# Chargement des fichiers step
# step_file = d3ds.Step(file_path)
step_file = d3ds.Step.from_file(file_path)

# Extraction des primitives et faces
model = step_file.to_volume_model()
primitives = model.primitives

faces = []
for primitive in primitives:
    faces.extend(primitive.faces)

# %% Cylindrical face

cylindrical_face = faces[0]

# %% Bspline-surface/face 

degree_u, degree_v = 3, 3

bspline_surface = surfaces.BSplineSurface3D.from_cylindrical_face(cylindrical_face, degree_u, degree_v, points_x=50, points_y=50)

bspline_face = d3df.BSplineFace3D.from_surface_rectangular_cut(bspline_surface, 0, 1, 0, 1)


# %% Display

cylindrical_face.color = [list(npy.random.choice(range(255), size=1))[0] / 256,
                          list(npy.random.choice(range(255), size=1))[0] / 256,
                          list(npy.random.choice(range(255), size=1))[0] / 256]

bspline_face.color = [list(npy.random.choice(range(255), size=1))[0] / 256,
                      list(npy.random.choice(range(255), size=1))[0] / 256,
                      list(npy.random.choice(range(255), size=1))[0] / 256]

d3d.core.VolumeModel([cylindrical_face, bspline_face]).babylonjs()
