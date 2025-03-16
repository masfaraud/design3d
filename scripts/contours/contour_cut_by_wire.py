#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 2 2022

@author: s.bendjebla
"""

# %% Libraries

import matplotlib.pyplot as plt

import design3d as d3d
import design3d.wires
from design3d.core import EdgeStyle

# %% Contour2d

p = [d3d.Point2D(-0.3, -0.2), d3d.Point2D(0.3, -0.2),
      d3d.Point2D(0.2, 0.2), d3d.Point2D(0, 0.3), d3d.Point2D(-0.2, 0.2)]

contour = d3d.wires.ClosedPolygon2D(p)

# %% Wire2d

primitives = [d3d.edges.LineSegment2D(d3d.Point2D(-0.35, -0.1), d3d.Point2D(-0.1, 0)),
              d3d.edges.LineSegment2D(d3d.Point2D(-0.1, 0), d3d.Point2D(0.2, 0.2)),
              d3d.edges.LineSegment2D(d3d.Point2D(0.2, 0.2), d3d.Point2D(0.3, 0.3))]

wire = d3d.wires.Wire2D(primitives)

# %% Cut_by_wire

contours = contour.cut_by_wire(wire)

# %% Plots

fig, axs = plt.subplots(1, 3)

titles = ["Initial Contour2d + Wire2d", "1st Cutted Contour2d 'green'", "2nd Cutted Contour2d 'blue'"]
colors = ['g', 'b']
for i in range(len(axs)):
    contour.plot(ax=axs[i])
    for prim in wire.primitives:
        prim.plot(ax=axs[i], edge_style=EdgeStyle(width=2, color='r'))
    axs[i].set_title(titles[i])
    if i !=0:
        for prim in contours[i-1].primitives:
            prim.plot(ax=axs[i], edge_style=EdgeStyle(width=2, color=colors[i-1]))
