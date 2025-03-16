#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 18 2022

@author: s.bendjebla
"""

# %% Libraries

import matplotlib.pyplot as plt

import design3d.edges
import design3d.wires

# %% Data

primitives = [
    design3d.edges.LineSegment2D(design3d.Point2D(0.001, 0.014),
                                design3d.Point2D(0.001, 0.0125)),

    design3d.edges.Arc2D(design3d.Point2D(0.001, 0.0125),
                        design3d.Point2D(0.009862829911410362, 0.007744326060968065),
                        design3d.Point2D(0.012539936203984454, 0.0)),

    design3d.edges.Arc2D(design3d.Point2D(0.012539936203984454, 0.0),
                        design3d.Point2D(0.0, -0.012539936203984454),
                        design3d.Point2D(-0.012539936203984454, 0.0)),

    design3d.edges.Arc2D(design3d.Point2D(-0.012539936203984454, 0.0),
                        design3d.Point2D(-0.00921384654213387, 0.008506176103162205),
                        design3d.Point2D(-0.001, 0.0125)),

    design3d.edges.LineSegment2D(design3d.Point2D(-0.001, 0.0125),
                                design3d.Point2D(-0.001, 0.014)),

    design3d.edges.LineSegment2D(design3d.Point2D(-0.001, 0.014),
                                design3d.Point2D(0.001, 0.014))
]
contour2d = design3d.wires.Contour2D(primitives)

point1 = design3d.Point2D(-0.007116025403784438, 0.010325317547305484)
point2 = design3d.Point2D(-0.005383974596215561, 0.011325317547305485)

# %% Wire.extract_without_primitives

extracted_primitives_inside_true = contour2d.extract_with_points(point1, point2, inside=True)

extracted_primitives_inside_false = contour2d.extract_with_points(point1, point2, inside=False)

extracted_primitives = [extracted_primitives_inside_true, extracted_primitives_inside_false]

# %% Plots

fig, axs = plt.subplots(1, 2)

titles = ["inside=True", "inside=False"]
colors = ['g', 'r']
for i in range(len(axs)):
    contour2d.plot(ax=axs[i])
    point1.plot(ax=axs[i])
    point2.plot(ax=axs[i])
    for prim in extracted_primitives[i]:
        prim.plot(ax=axs[i], edge_style=design3d.edges.EdgeStyle(color=colors[i]))
    axs[i].set_title(titles[i])
