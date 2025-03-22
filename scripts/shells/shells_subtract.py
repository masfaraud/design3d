#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 14 2023

@author: s.bendjebla
"""

import numpy as npy

import volmdlr as d3d
import volmdlr.edges as edges
import volmdlr.primitives2d as primitives2d
import volmdlr.primitives3d as primitives3d
import volmdlr.wires as wires

def get_color():
    random_color = list(npy.random.choice(range(255), size=3))
    random_color = (random_color[0] / 256, random_color[1] / 256, random_color[2] / 256)
    return random_color

# %% Shell1

p1 = d3d.Point2D(0, 0)
p2 = d3d.Point2D(0.1, 0.)
p3 = d3d.Point2D(0.1, 0.2)
p4 = d3d.Point2D(0.05, 0.1)
p5 = d3d.Point2D(0.,0.21)

radius = {0: 0.01, 2: 0.01, 3: 0.015}

outer_profile = primitives2d.ClosedRoundedLineSegments2D([p1, p2, p3, p4, p5], radius)

profile=primitives3d.ExtrudedProfile(d3d.O3D, d3d.Y3D, d3d.Z3D, outer_profile, [], d3d.X3D*0.1, name = 'extrusion')

shell1 = d3d.shells.ClosedShell3D(profile.faces)

# %% Shell2

p6 = d3d.Point2D(-0.02, 0.05)
p7 = d3d.Point2D(0.12, 0.05)
p8 = d3d.Point2D(0.12, 0.10)
p9 = d3d.Point2D(-0.02, 0.10)

l1 = edges.LineSegment2D(p6, p7)
l2 = edges.LineSegment2D(p7, p8)
l3 = edges.LineSegment2D(p8, p9)
l4 = edges.LineSegment2D(p9, p6)

outer_profile = wires.Contour2D([l1, l2, l3, l4])

profile = primitives3d.ExtrudedProfile(d3d.Point3D(-0.1,0,0), d3d.Y3D, d3d.Z3D, outer_profile, [], d3d.X3D*0.3, name = 'extrusion')

shell2 = d3d.shells.ClosedShell3D(profile.faces)

# %% Model

for shell in [shell1, shell2]:
    shell.color = get_color()

d3d.core.VolumeModel([shell1, shell2]).babylonjs()

# %% Subtract

subtract_1 = shell1.subtract_to_closed_shell(shell2)

subtract_2 = shell1.subtract(shell2)

for result in [subtract_1, subtract_2]:
    for shell in result:
        shell.color = get_color()

    d3d.core.VolumeModel(result).babylonjs()
