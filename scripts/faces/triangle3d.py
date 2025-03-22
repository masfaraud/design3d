#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""


"""

import design3d as d3d
import design3d.core as d3dc
import design3d.faces as faces

p1 = d3d.Point3D.random(0, 0.1, 0, 0.1, -0.1, 0)
p2 = d3d.Point3D.random(0, 0.1, 0, 0.1, -0.1, 0)
p3 = d3d.Point3D.random(0, 0.1, 0, 0.1, -0.1, 0)


tri = faces.Triangle3D(p1, p2, p3)
# tri.babylonjs()
# tri.subdescription()

# d3dc.VolumeModel([faces.OpenShell3D([tri])])


subtriangles = tri.subdescription_to_triangles(resolution = 5e-2)

ax = tri.plot(color='r')
for tritri in subtriangles :
    tritri.plot(ax=ax)
tri.plot(ax=ax, color='r')


subdescription = tri.subdescription(resolution = 1e-2)
ax = tri.plot(color='r')
for pt in subdescription:
    pt.plot(ax=ax)
