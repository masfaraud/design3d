#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 12 10:04:09 2017

@author: steven
"""

import volmdlr as d3d
import volmdlr.mesh as d3dmesh

l=0.1

p1=d3d.Point2D((0,0))
p2=d3d.Point2D((l,0))
p3=d3d.Point2D((l,l))
p4=d3d.Point2D((0,l))

tr2=d3dmesh.TriangularElement([p1,p3,p4])
tr1=d3dmesh.TriangularElement([p1,p2,p3])

Triangles=[tr1,tr2]

Elements=d3dmesh.ElementsGroup(Triangles,'first_element')

mesh=d3dmesh.Mesh([Elements])

# l1=d3d.LineSegment2D(p1,p2)
# l2=d3d.LineSegment2D(p2,p3)
# l3=d3d.LineSegment2D(p3,p4)
# l4=d3d.LineSegment2D(p4,p1)

# p5=d3d.Point2D((l/2,l/2))
# c1=d3d.Circle2D(p5,l/5)



 # ct1=d3d.Contour2D([l4,l3,l2,l1])
 # ct2=d3d.Contour2D([c1])
 # mesh=d3d.Mesh2D([ct1,ct2],{},0.01)

print(mesh.GeoScript('mesh2D.geo'))
