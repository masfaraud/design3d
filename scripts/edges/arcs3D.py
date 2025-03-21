#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 23 18:06:45 2018

@author: steven
"""

import design3d
import design3d.edges

i = design3d.X3D.to_point()
e = i.rotation(design3d.O3D, design3d.Z3D, 1)
s = i.rotation(design3d.O3D, design3d.Z3D, -3.5)

a = design3d.edges.Arc3D.from_3_points(s, i, e)
assert a.angle == 4.5


# Random arc
i = design3d.Point3D.random(-1, 1, -1, 1, -1, 1)
e = design3d.Point3D.random(-1, 1, -1, 1, -1, 1)
s = design3d.Point3D.random(-1, 1, -1, 1, -1, 1)

a = design3d.edges.Arc3D.from_3_points(s, i, e)
ax = a.plot()

# for p in a.polygon_points():
#     p.plot(ax=ax)

s.plot(ax=ax, color='r')
e.plot(ax=ax, color='g')
i.plot(ax=ax, color='b')


arc1 = design3d.edges.Arc3D.from_3_points(design3d.Point3D(-0.03096, 0.001162, -0.02),
                                         design3d.Point3D(-0.03120, -0.000400635, -0.02),
                                         design3d.Point3D(-0.026119083, 0.0, -0.02),
                                         # design3d.Vector3D(0.0, 0.0, 0.001)
                                         )


ax = arc1.plot()
# for p in arc1.polygon_points():
#     p.plot(ax=ax)


arc1.start.plot(ax=ax, color='r')
arc1.end.plot(ax=ax, color='g')
arc1.circle.center.plot(ax=ax, color='m')
# ax.set_aspect('equal')

print(arc1.circle.center)
print(arc1.circle.center - design3d.Point3D(-0.030962035803739997, 0.0011626900994054661, -0.02))
print(arc1.circle.center - design3d.Point3D(-0.031209642286239472, -0.00040063570451895954, -0.02))
print(arc1.circle.center - design3d.Point3D(-0.026119083, 0.0, -0.02))
