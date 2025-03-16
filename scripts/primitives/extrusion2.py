#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar  5 22:01:35 2017

@author: steven


"""

import math

#import numpy as npy
import design3d as d3d
import design3d.core
import design3d.core as d3dc
import design3d.edges as d3de
import design3d.primitives2d as primitives2d
import design3d.primitives3d as primitives3d
import design3d.wires as d3dw

p1=d3d.Point2D(0, 0)
p2=d3d.Point2D(0.1, 0.)
p3=d3d.Point2D(0.1, 0.2)
p4=d3d.Point2D(0, 0.1)
p5=d3d.Point2D(-0.01, 0.05)

#p6=d3d.Point2D((0.1,0.3))

l1 = primitives2d.OpenedRoundedLineSegments2D([p1, p2, p3, p4], {2: 0.01})
l2 = d3de.Arc2D.from_3_points(p4, p5, p1)
c1 = d3dw.Contour2D([l1, l2])
c2 = c1.rotation(d3d.Point2D(0,0), math.pi)
ax = c1.plot()
c2.plot(ax=ax, edge_style=design3d.core.EdgeStyle(color='r'))
#c3 = d3d.Contour2D([c1, c2])
#c3.MPLPlot()




profile = primitives3d.ExtrudedProfile(d3d.OYZX, c1, [], 0.1)

model = d3dc.VolumeModel([profile])
model.babylonjs()

#profile.MPLPlot((0,0,0),(1,0,0),(0,1,0))

#model.MPLPlot()

#model.FreeCADExport('extrusion2')
