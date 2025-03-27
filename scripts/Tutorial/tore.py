# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 15:25:47 2020

@author: Mack Pro
"""


import math

import volmdlr as d3d

# import matplotlib.pyplot as plt

r1 = 10e-3 #Radius of the generative arc3D
r2 = 3e-3 #Radius of the arc3d generated

center = d3d.Point3D([0,0,0]) #Choose the coordinate of the center
normal1 = d3d.Vector3D([0,0,1]) #Choose the normal of the generative
normal1 = normal1.unit_vector() #Normalize the normal if it is not the case
vec1 = normal1.deterministic_unit_normal_vector()


frame = d3d.Frame3D(center, vec1, normal1.Cross(vec1), normal1) #Frame in the center of the generative arc3D
toroidalsurface3d = d3d.ToroidalSurface3D(frame, r1, r2)

theta = 4*math.pi/3 #Tore's length
phi = 2*math.pi #angle of circle 
offset_theta = math.pi/4 #Theta's offset if you want to turn it with normal's reference
offset_phi = math.pi #Idem but with circle's normal

#You have to create a cutting pattern in 2D

pt1, pt2, pt3, pt4 = d3d.Point2D((offset_theta, offset_phi)), d3d.Point2D((offset_theta, offset_phi+phi)), d3d.Point2D((offset_theta+theta, offset_phi+phi)), d3d.Point2D((offset_theta+theta, offset_phi))
seg1, seg2, seg3, seg4 = d3d.LineSegment2D(pt1, pt2), d3d.LineSegment2D(pt2, pt3), d3d.LineSegment2D(pt3, pt4), d3d.LineSegment2D(pt4, pt1) 
edges = [seg1, seg2, seg3, seg4]
contours2d =  [d3d.Contour2D(edges)]
points = [theta, phi] 



toroidalface = d3d.ToroidalFace3D(contours2d, toroidalsurface3d, points)

shell = d3d.Shell3D([toroidalface])
m = d3d.VolumeModel([shell])
m.babylonjs(debug=True)
