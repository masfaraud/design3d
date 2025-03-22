import matplotlib.pyplot as plt

import design3d as d3d
import design3d.faces as d3df

degree_u = 3
degree_v = 2

control_points = [d3d.Point3D(0, 0, 0), d3d.Point3D(0, 4, 0), d3d.Point3D(0, 8, -3),
                  d3d.Point3D(2, 0, 6), d3d.Point3D(2, 4, 0), d3d.Point3D(2, 8, 0),
                  d3d.Point3D(4, 0, 0), d3d.Point3D(4, 4, 0), d3d.Point3D(4, 8, 3),
                  d3d.Point3D(6, 0, 0), d3d.Point3D(6, 4, -3), d3d.Point3D(6, 8, 0)]

bezier_surface = d3df.BezierSurface3D(degree_u=degree_u, degree_v=degree_v,
                                     control_points=control_points, nb_u=4,
                                     nb_v=3, name='bezier curve 1')
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
bezier_surface.plot(ax=ax)
[p.plot(ax=ax) for p in control_points]
