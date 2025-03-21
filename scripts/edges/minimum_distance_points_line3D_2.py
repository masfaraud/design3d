#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 12 17:14:06 2020

@author: masfaraud
"""


import random

import matplotlib.pyplot as plt
import numpy as npy

import design3d as design3d
import design3d.core as design3dc
import design3d.primitives2d as primitives2D
import design3d.primitives3d as primitives3D

radius_circle = 0.008
c = design3d.wires.Circle2D(design3d.Point2D(0, 0), radius_circle)
contour = design3d.wires.Contour2D([c])
pt0 = design3d.Point3D(0.01, 0.04, 0.16)
pt1 = design3d.Point3D(0.03, 0, 0.2)
pt2 = design3d.Point3D(0.45, 0.01, 0.1)
pt3 = design3d.Point3D(0.45, 0, -0.1)
pt4 = design3d.Point3D(0.3, 0.04, -0.02)
pts = [pt0, pt1, pt2, pt3, pt4]
radius = {1: 0.03, 2: 0.01, 3: 0.07}
rl = primitives3D.OpenRoundedLineSegments3D(pts, radius, adapt_radius=True, name='wire')
sweep = primitives3D.Sweep(contour, rl, name='pipe')


pt10 = design3d.Point3D(0.02, 0.22, 0.25)
pt11 = design3d.Point3D(0.02, 0.24, 0.25)
pt12 = design3d.Point3D(0.6, 0.24, 0.20)
pt13 = design3d.Point3D(0.40, 0.17, 0.13)
pts1 = [pt10, pt11, pt12, pt13]
radius1 = {1: 0.01, 2: 0.05}

rl1 = primitives3D.OpenRoundedLineSegments3D(pts1, radius1, adapt_radius=True, name='wire1')
sweep1 = primitives3D.Sweep(contour, rl1, name='pipe1')
# fig = plt.figure()
# ax = fig.add_subplot(111, projection='3d')
# for prim in rl.primitives :
#     prim.MPLPlot(ax=ax)
# for prim1 in rl1.primitives :
#     prim1.MPLPlot(ax=ax)

l1 = rl.primitives[2]
l2 = rl1.primitives[2]

p1, p2 = l1.Matrix_distance(l2)


mes = primitives3D.Measure3D(p1, p2)
ll = primitives3D.OpenRoundedLineSegments3D([p1, p2], {}, name='mesure')


# mes.MPLPlot(ax=ax)

model = design3d.core.VolumeModel([rl1, rl, ll])
# model.FreeCADExport('lines')

ll2 = primitives3D.OpenRoundedLineSegments3D([p1, p2], {}, name='mesure')
