# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 14:09:52 2020

@author: Mack Pro
"""


import math

import volmdlr as d3d

Gradius = 8e-3 #Grand radius
Sradius = 3e-3 #Small radius
h = 20e-3 #Height of the Ellipse

center = d3d.Point3D([0,0,0]) #Choose the coordinate of the center
normal = d3d.Vector3D([1,1,1]) #Choose the normal
normal = normal.unit_vector() #Normalize the normal if it is not the case
plane = d3d.Plane3D.from_normal(center, normal) #Create a plane to give us two others vector
Gdir = plane.vectors[0] #Gradius direction
Sdir = plane.vectors[1] #Sradius direction 

ellipse = d3d.Ellipse3D(Gradius, Sradius, center, normal, Gdir)
bsplinextru = d3d.BSplineExtrusion(ellipse, -normal) #Perhaps the normal needs to be the opposite

angle = 5*math.pi/4 #Angle of pint if start=end

# position of point in ellipse with an angle
# Gradius*d3d.Point3D(Gdir.vector)*math.cos(angle)+Sradius*d3d.Point3D(Sdir.vector)*math.sin(angle)+center


pointellipse = center + Gradius*Gdir #Point on Ellipse
pint = Gradius*d3d.Point3D(Gdir.vector)*math.cos(angle)+Sradius*d3d.Point3D(Sdir.vector)*math.sin(angle)+center
extra1 = Gradius*d3d.Point3D(Gdir.vector)*math.cos(math.pi/2)+Sradius*d3d.Point3D(Sdir.vector)*math.sin(math.pi/2)+center

segbh = d3d.LineSegment3D(pointellipse, pointellipse + d3d.Point3D([i*h for i in normal.vector])) #point on the ellipse not on the center

#IF you want to do a complete ellipse, you need to add an 'extra' point ---> see angle

ellipse1 = d3d.ArcEllipse3D(pointellipse, pint, pointellipse, center,Gdir, normal, 'ellipse1', extra = extra1)
seghb = d3d.LineSegment3D(segbh.points[1], segbh.points[0])

center2 = center + d3d.Point3D([i*h for i in normal.vector])
pointellipse2 = center2 + Gradius*Gdir
pint2 = pint + d3d.Point3D([i*h for i in normal.vector])
extra2 = extra1 + d3d.Point3D([i*h for i in normal.vector])
ellipse2 = d3d.ArcEllipse3D(pointellipse2, pint2, pointellipse2, center2, Gdir, normal, 'ellipse2',extra = extra2)

edges = [segbh, ellipse1, seghb, ellipse2]
points = segbh.points+ellipse1.points+seghb.points+ellipse2.points
contours = [d3d.Contour3D(edges)]

EllipseFace = d3d.BSplineFace3D(contours, bsplinextru, points)

shell = d3d.Shell3D([EllipseFace])
m = d3d.VolumeModel([shell])
m.babylonjs()
