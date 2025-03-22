# -*- coding: utf-8 -*-
"""
"""

import design3d as d3d
import design3d.edges as d3de
import design3d.faces as d3df
import design3d.primitives3d as p3d
import design3d.wires as d3dw

points = [d3d.Point3D(-0.51883, -0.39865, 0.5391699999999999),
          d3d.Point3D(-0.5502100000000001, -0.25545000000000007, 0.5352),
          d3d.Point3D(-0.42862035022394307, -0.23097502716802853, 0.45694632230872445),
           d3d.Point3D(-0.3779416142154201, -0.16043402099609375, 0.5017910926712679),
           d3d.Point3D(-0.38599218750000003, -0.16043402099609375, 0.5256149291992187),
           d3d.Point3D(-0.3110091552734375, -0.10281935119628904, 0.5621776123046875),
           d3d.Point3D(-0.2779786987304688, -0.04520467758178713, 0.6191567993164062),
           d3d.Point3D(-0.27749807039051816, -0.020624128269254388, 0.5906719135439563),
           d3d.Point3D(-0.18039562917956825, 0.11453519976962154, 0.6765962482987753)]#,
           # d3d.Point3D(-0.1670280102373628, 0.10003019655834136, 0.6798995263156462),
           # d3d.Point3D(-0.1598302, 0.10245, 0.6613972)]

bezier = d3de.BezierCurve3D(degree = 3, control_points = points)

ax = bezier.plot()


circle = d3dw.Contour2D([d3de.FullArc2D.from_curve(d3d.curves.Circle2D(d3d.OXY.translation(d3d.Vector2D(0,0)), 5e-3))])
primi_wire = d3dw.Wire3D([bezier])
sweepy = p3d.Sweep(circle, primi_wire)
sweepy.babylonjs()
