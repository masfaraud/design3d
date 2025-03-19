#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimum distance line between two lines
"""

import design3d as d3d
import design3d.primitives3d as primitives3d
from design3d import curves
#import numpy as npy

p11 = d3d.Point3D.random(-1,1,-1,1,-1,1)
p12 = d3d.Point3D.random(-1,1,-1,1,-1,1)
p21 = d3d.Point3D.random(-1,1,-1,1,-1,1)
p22 = d3d.Point3D.random(-1,1,-1,1,-1,1)

l1 = curves.Line3D(p11, p12)
l2 = curves.Line3D(p21, p22)

pmd1, pmd2 = l1.minimum_distance_points(l2)

u = p12 - p11 # vector of line1
v = p22 - p21 # vector of line2
w = pmd2 - pmd1

print(u.dot(w), v.dot(w))

m = d3d.core.VolumeModel([('', [l1, l2, pmd1, pmd2])])

m.MPLPlot() #Problem

#m.mpl_plot() ?
#m.babylonjs() ? 
