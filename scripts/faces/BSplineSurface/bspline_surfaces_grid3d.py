#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: s.bendjebla
"""

# %% Libraries

import design3d as d3d
import design3d.grid
from design3d.models import bspline_surfaces
from design3d import faces


bspline_faces = [faces.BSplineFace3D.from_surface_rectangular_cut(bspline_surfaces.bspline_surface_1, 0,1,0,1),
                 faces.BSplineFace3D.from_surface_rectangular_cut(bspline_surfaces.bspline_surface_2, 0,1,0,1)]


# %% Bspline surfaces

bspline_surfaces = [bspline_surfaces.bspline_surface_1, bspline_surfaces.bspline_surface_2]


# %% Grdi3d initial

points_x, points_y, xmin, xmax, ymin, ymax = 5, 5, 0, 1, 0, 1
grid2d = design3d.grid.Grid2D.from_properties((xmin, xmax), (ymin, ymax), (points_x, points_y))

points3d = []
for i, bspline in enumerate(bspline_surfaces):
    grid3d = bspline.grid3d(grid2d)
    points3d.append(grid3d)


# %%% Display

ax1 = points3d[0][0].plot()
for i, points in enumerate(points3d):
    for k,p in enumerate(points):
        if k<points_x:
            if k == 0:
                p.plot(ax=ax1, color='g')  
            else:
                p.plot(ax=ax1, color='r')
        else:
            p.plot(ax=ax1)


# %% Grdi3d with directions

corresponding_directions, grid2d_direction = bspline_faces[0].pair_with(bspline_faces[1])
points_x, points_y, xmin, xmax, ymin, ymax = 5, 5, 0, 1, 0, 1

points3d = []
for i, bspline in enumerate(bspline_surfaces):
    grid2d = design3d.grid.Grid2D.from_properties((xmin, xmax), (ymin, ymax),
                                                 (points_x, points_y), grid2d_direction[i])
    grid3d = bspline.grid3d(grid2d)
    points3d.append(grid3d)


# %%% Display

ax1 = points3d[0][0].plot()
for i, points in enumerate(points3d):
    for k, p in enumerate(points):
        if k < points_x:
            if k == 0:
                p.plot(ax=ax1, color='g')
            else:
                p.plot(ax=ax1, color='r')
        else:
            p.plot(ax=ax1)
