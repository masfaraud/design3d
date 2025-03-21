#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: s.bendjebla
"""

# %% Libraries

import numpy as npy
from design3d import faces
from design3d.models import bspline_surfaces

# %% Read Step file

# files_path = ['bspline_surface_1.step', 'bspline_surface_2.step']
# bspline_faces = []

# for file_path in files_path:
#     step_file = d3ds.Step.from_file(file_path)

#     model = step_file.to_volume_model()
#     primitives = model.primitives

#     faces = []
#     for primitive in primitives:
#         faces.extend(primitive.faces)

#     bspline_faces.append(faces[0])

bspline_faces = [faces.BSplineFace3D.from_surface_rectangular_cut(bspline_surfaces.bspline_surface_1, 0, 1, 0, 1),
                 faces.BSplineFace3D.from_surface_rectangular_cut(bspline_surfaces.bspline_surface_2, 0, 1, 0, 1)]

# %% Merge faces/surfaces

merged_surface = bspline_surfaces.bspline_surface_1.merge_with(bspline_surfaces.bspline_surface_2)
bspline_faces.append(faces.BSplineFace3D.from_surface_rectangular_cut(merged_surface, 0, 1, 0, 1))


# %% Display
random_colors = []
for i in range(0, 3):
    random_colors.append([list(npy.random.choice(range(255), size=1))[0] / 256,
                          list(npy.random.choice(range(255), size=1))[0] / 256,
                          list(npy.random.choice(range(255), size=1))[0] / 256])

ax = bspline_faces[0].plot()
for i, face in enumerate(bspline_faces):
    face.color = random_colors[i]
    face.plot(ax=ax, color=face.color)

# d3d.core.VolumeModel(bspline_faces).babylonjs()
