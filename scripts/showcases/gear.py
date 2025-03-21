#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  6 14:51:21 2017

@author: steven
"""

import math

import numpy as npy

import volmdlr as d3d
import volmdlr.primitives2d as primitives2D
import volmdlr.primitives3d as primitives3D

r1=0.032
r2=0.04
Z=12
theta=2*math.pi/Z
theta1=0.4*theta
theta2=0.4*theta
theta3=theta-theta1-theta2
r3=0.001
e=0.030
r4=0.015

pc=d3d.Point2D((0,0))

p1=d3d.Point2D((0,r2))
p2=p1.rotation(pc,0.5*theta1)
p3=p1.rotation(pc,theta1)
a1=d3d.Arc2D(p1,p2,p3)

p4=d3d.Point2D((0,r1))
p4.rotation_inplace(pc,theta1+theta3)
p5=p4.rotation(pc,theta2)
p6=p1.rotation(pc,theta)

l1=primitives2D.OpenedRoundedLineSegments2D([p3,p4,p5,p6],{1:r3,2:r3})

#l1=primitives2D.RoundedLines2D([p1,p2,p3,p4],{0:0.01,2:0.01})
#l2=d3d.Circle2D(p5,0.01)
L=[a1,l1]
for i in range(Z-1):
    thetar=(i+1)*theta
    L.append(a1.rotation(pc,thetar))
    L.append(l1.rotation(pc,thetar))
#p7=d3d.Point2D((0,r4))
l2=d3d.Circle2D(pc,r4)

c1=d3d.Contour2D(L)
c2=d3d.Contour2D([l2])

po=d3d.Point3D((0,0,0))
xp=d3d.Vector3D((1,0,0))
yp=d3d.Vector3D((0,1,0))



#c1.MPLPlot()
#extr_vect=d3d.Vector3D((0,0,e))

profile_straight = primitives3D.ExtrudedProfile(po,xp,yp, c1, [c2], (0,0,e),
                                                name='straight')
#
#model_straight=d3d.VolumeModel([profile_straight])

profile_helical = primitives3D.HelicalExtrudedProfile(po, xp, yp, 
                                                    d3d.Vector3D((0,0,0)),
                                                    d3d.Vector3D((0,0,e)),
                                                    28*3.14/180, c1, [c2],
                                                    name='helical')

model = d3d.VolumeModel([profile_helical, profile_straight])
model.to_stl('gear.stl')

#resp=model_straight.FreeCADExport('python','gear-straight','/usr/lib/freecad/lib/',['stl','fcstd'])
#print(resp)

# resp=model.FreeCADExport('gear')
# print(resp)
