#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: s.bendjebla
"""

# %% Libraries

import numpy as npy

import design3d as d3d
from design3d.models import bspline_surfaces
from design3d import surfaces, faces

#%%  BSpline-surface definition

# script = 'bspline_surface_definition.py'
# print('\n## Executing script {}'.format(script))
# exec(open(script).read())

bspline_surface = bspline_surfaces.bspline_surface_1

#%% (1) BSpline-surface split - u_split
# split the bspline_surface at the input parametric coordinate (u) on the u-direction, into 2 surfaces

u = 0.2
splitted_surfaces = bspline_surface.split_surface_u(u)

random_colors = []
splitted_faces = []
for i, s in enumerate(splitted_surfaces):
    splitted_faces.append(faces.BSplineFace3D.from_surface_rectangular_cut(s, 0, 1, 0, 1))
    random_colors.append([list(npy.random.choice(range(255), size=1))[0] / 256,
                          list(npy.random.choice(range(255), size=1))[0] / 256,
                          list(npy.random.choice(range(255), size=1))[0] / 256])
    splitted_faces[i].color = random_colors[i]

# %%% Display

ax = faces.BSplineFace3D.from_surface_rectangular_cut(bspline_surface, 0, 1, 0, 1).plot()
for f in splitted_faces:
    f.plot(ax=ax, color=f.color)

# d3d.core.VolumeModel(splitted_faces).babylonjs()

# %% (2) BSpline-surface split - v_split
# split the bspline_surface at the input parametric coordinate (v) on the v-direction, into 2 surfaces

v = 0.4
splitted_surfaces = bspline_surface.split_surface_v(v)

splitted_faces = []
for i, s in enumerate(splitted_surfaces):
    splitted_faces.append(faces.BSplineFace3D.from_surface_rectangular_cut(s, 0, 1, 0, 1))
    splitted_faces[i].color = random_colors[i]

# %%% Display

ax = faces.BSplineFace3D.from_surface_rectangular_cut(bspline_surface, 0, 1, 0, 1).plot()
for f in splitted_faces:
    f.plot(ax=ax, color=f.color)

# d3d.core.VolumeModel(splitted_faces).babylonjs()

# %% (3) BSpline-surface split - bspline_curve_split
# split the bspline_surface, into 2 surfaces, using a bspline curve

# %%% Bspline-curve definition

points2d = [d3d.Point2D(0, 0.1),
            d3d.Point2D(0.2, 0.3),
            d3d.Point2D(0.4, 0.4),
            d3d.Point2D(0.5, 0.6),
            d3d.Point2D(0.6, 0.7),
            d3d.Point2D(0.8, 0.8),
            d3d.Point2D(1, 0.9)]

bspline_curve3d = bspline_surface.bsplinecurve2d_to_3d(d3d.edges.BSplineCurve2D.from_points_interpolation(points2d, 2))[0]

# %%% Split surface

splitted_surfaces = bspline_surface.split_surface_with_bspline_curve(bspline_curve3d)

splitted_faces = []
for i, s in enumerate(splitted_surfaces):
    splitted_faces.append(faces.BSplineFace3D.from_surface_rectangular_cut(s, 0, 1, 0, 1))
    splitted_faces[i].color = random_colors[i]
    
# %%% Display

ax = faces.BSplineFace3D.from_surface_rectangular_cut(bspline_surface, 0, 1, 0, 1).plot()
for f in splitted_faces:
    f.plot(ax=ax, color=f.color)
