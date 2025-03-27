# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 10:51:54 2020

@author: Mack Pro
"""


import math

import matplotlib.pyplot as plt

import volmdlr as d3d
import volmdlr.primitives3d as primitives3d
import volmdlr.step

radius = 5e-3 #Choose the radius
center = d3d.Point3D(0,0,0) #Choose the coordinate of the center
normal = d3d.Vector3D(0,0,1) #Choose the normal
cylinder = primitives3d.Cylinder(center, normal, radius, length=0.1, name='Cylinder')

h = 10e-3 #Height of cylinder
angle = 3*math.pi/2 #Arc's angle 

#You have to create a cutting pattern in 2D

# center2d = center.to_2d(center, plane.vectors[0], plane.vectors[1])
# segbh = d3d.LineSegment2D(center2d, center2d + d3d.Point2D((0,h)))
# circlestart = d3d.LineSegment2D(segbh.points[1], segbh.points[1]+d3d.Point2D((angle,0)))
# seghb = d3d.LineSegment2D(circlestart.points[1],circlestart.points[1]-segbh.points[1])
# circlend = d3d.LineSegment2D(seghb.points[1],segbh.points[0])
# edges = [segbh, circlestart, seghb, circlend]
# points = edges[0].points
# contours =  [d3d.Contour2D(edges)]
#
# cylinder = d3d.CylindricalFace3D(contours, cylindersurface3d, points)
#
# pts1, tangle1 = cylinder.triangulation(resolution=12)
# fig = plt.figure()
# ax = fig.add_subplot(111, projection='3d')
# [pt.MPLPlot(ax=ax) for pt in pts1]
# pt1 = d3d.Point3D((radius*math.cos(2*math.pi/3),
#                radius*math.sin(2*math.pi/3),
#                h/4))
# p1 = frame.OldCoordinates(pt1)
# p1.MPLPlot(ax=ax, color='r')

# shell = d3d.Shell3D([cylinder])
model = d3d.core.VolumeModel([cylinder], name='cylinder model')

model.to_step('cylinder.step')

# model.babylonjs()

# Reading own step
step = volmdlr.step.Step('cylinder.step')
model2 = step.to_volume_model()
model2.babylonjs()
