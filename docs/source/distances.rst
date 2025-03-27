=================
D I S T A N C E S
=================

Distance between two points
***************************

.. plot::
    :include-source:
    :align: center

    import design3d


    point1 = design3d.Point2D(0.0, 0.0)
    point2 = design3d.Point2D(1.0, 1.0)

    distance_point1_point2 = point1.point_distance(point2)
    print(distance_point1_point2)

    ax = point1.plot(color='k')
    point2.plot(ax, color='c')


Distance between point and another object
*****************************************

To calculate the distance between a point and **any** other design3d object is enough to use just the `point_distance` method.
If an abject does not have yet a point_distance method, it you raise you an error.

Here are some examples:

Distance LineSegment2D to Point2D:

.. plot::
    :include-source:
    :align: center

    import design3d
    from design3d import edges
    from design3d.core import EdgeStyle

    point1 = design3d.Point2D(0.0, 0.0)
    linesegment2d = edges.LineSegment2D(design3d.Point2D(1.0, 1.0), design3d.Point2D(2.0, -1))

    distance_linesegment2d_point1, other_point = linesegment2d.point_distance(point1, return_other_point=True)

    ax = point1.plot()
    linesegment2d.plot(ax, EdgeStyle(color='c'))
    other_point.plot(ax, 'g')

.. code-block:: python

   print('distance_linesegment2d_point1: ', distance_linesegment2d_point1)
   >>> distance_linesegment2d_point1:  1.3416407864998738

Distance PlaneFace3D to Point2D:

.. plot::
    :include-source:
    :align: center

    import design3d
    from design3d import faces, surfaces
    from design3d.core import EdgeStyle

    plane = surfaces.Plane3D(design3d.OXYZ)
    face = faces.PlaneFace3D.from_surface_rectangular_cut(plane, -1, 1, -1, 1)
    point = design3d.Point3D(0.2, -0.3, 0.7)
    distance_face_point, pt = face.point_distance(point, True)
    ax = face.plot()
    point.plot(ax, 'r')
    pt.plot(ax, 'b')

.. code-block:: python

   print('distance_face_point: ', distance_face_point)
   >>> distance_face_point: 0.7

Distance between two edges
**************************

To calculate the distance between any two edges, it is enough to use just the `minimum_distance` method.

Here are some examples:

.. plot::
    :include-source:
    :align: center

    import design3d
    import design3d.nurbs.helpers as nurbs_helpers
    from design3d import edges
    from design3d.core import EdgeStyle

    #### DISTANCE BETWEEN A BSPLINECURVE2D AND A LINESEGMENT2D ####

    #Defining the BSplineCurve2D
    DEGREE = 3
    points = [design3d.Point2D(0, 0), design3d.Point2D(1, 1), design3d.Point2D(2, -1), design3d.Point2D(3, 0)]
    knotvector = nurbs_helpers.generate_knot_vector(DEGREE, len(points))
    knot_multiplicity = [1] * len(knotvector)
    bspline1 = edges.BSplineCurve2D(DEGREE, points, knot_multiplicity, knotvector, None, False)

    #Defining the LineSegment2D
    lineseg = edges.LineSegment2D(design3d.Point2D(1, .5), design3d.Point2D(3, 1))

    #plot
    ax = bspline1.plot()
    lineseg.plot(ax, EdgeStyle('g'))
    distance_bspline_linesegment, pt1, pt2 = bspline1.minimum_distance(lineseg, True)
    pt1.plot(ax, 'r')
    pt2.plot(ax, 'b')

.. code-block:: python

   print('distance_bspline_linesegment: ', distance_bspline_linesegment)
   >>> distance_bspline_linesegment: 0.26561504740059355

.. plot::
    :include-source:
    :align: center

    import design3d
    from design3d import edges, curves
    from design3d.core import EdgeStyle

    #### DISTANCE BETWEEN A ARC3D AND A ARCELLIPSE3D ####

    vector1 = design3d.Vector3D(1, 1, 1)
    vector1 = vector1.unit_vector()
    vector2 = vector1.deterministic_unit_normal_vector()
    vector3 = vector1.cross(vector2)

    #Defining the Arc3D
    circle3d = curves.Circle3D(design3d.Frame3D(design3d.O3D, vector1, vector2, vector3), 1)
    arc3d = edges.Arc3D(circle3d,
                        start=design3d.Point3D(0.5773502691896258, 0.5773502691896258, 0.5773502691896258),
                        end=design3d.Point3D(-0.9855985596534886, -0.11957315586905026, -0.11957315586905026))

    #Defining the Ellipse3D
    ellipse3d = curves.Ellipse3D(2, 1, design3d.Frame3D(design3d.Point3D(1, 0, 1), vector3, vector1, vector2))
    arcellipse3d = edges.ArcEllipse3D(ellipse3d,
                      start=design3d.Point3D(0.42264973081037405, -0.5773502691896255, 0.42264973081037427),
                      end=design3d.Point3D(1.577350269189626, 0.5773502691896254, 1.5773502691896257))

    #plot
    ax = arc3d.plot()
    arcellipse3d.plot(ax, EdgeStyle('g'))
    distance_arc3d_arcellipse3d, pt1, pt2 = arc3d.minimum_distance(arcellipse3d, True)
    pt1.plot(ax, 'r')
    pt2.plot(ax, 'b')

.. code-block:: python

   print('distance_arc3d_arcellipse3d: ', distance_arc3d_arcellipse3d)
   >>> distance_arc3d_arcellipse3d: 0.5340975460532926

Distances betweeen two faces
****************************

You can also calculate the distance between two faces. To do so, you can use the `face_minimum_distance` method.
It will work for any two faces.

.. plot::
    :include-source:
    :align: center

    import design3d
    from design3d import surfaces, faces

    R = 0.15
    cylindricalsurface = surfaces.CylindricalSurface3D(design3d.OXYZ, R)
    cylindricalface = faces.CylindricalFace3D.from_surface_rectangular_cut(cylindricalsurface, 0, design3d.TWO_PI, -.25, .25)
    u_vector = design3d.Vector3D(-1, -1, -1)
    u_vector = u_vector.unit_vector()
    v_vector = u_vector.deterministic_unit_normal_vector()
    w_vector = u_vector.cross(v_vector)
    cylindrical_face_ = cylindricalface.frame_mapping(design3d.Frame3D(design3d.Point3D(-.5, .5, -.1),
                                                                      u_vector, v_vector, w_vector), 'new')
    ax = cylindricalface.plot()
    cylindrical_face_.plot(ax, 'r')
    minimum_distance, pt1, pt2 = cylindricalface.face_minimum_distance(cylindrical_face_, True)
    pt1.plot(ax, 'y')
    pt2.plot(ax, 'b')

.. code-block:: python

   print('minimum_distance: ', minimum_distance)
   >>> minimum_distance: 0.3097688266437426

Distances betweeen two shells
*****************************

Likewise, you can calculate the distance between two shells as shown in the next example:

.. plot::
    :include-source:
    :align: center

    import design3d
    from design3d import edges, curves, surfaces, wires, faces, shells
    from design3d.core import EdgeStyle
    import math

    # Create a random shape shell's faces
    polygon1_vol1 = wires.ClosedPolygon3D([design3d.Point3D(-0.1, -0.05, 0), design3d.Point3D(-0.15, 0.1, 0),
                       design3d.Point3D(0.05, 0.2, 0), design3d.Point3D(0.12, 0.15, 0), design3d.Point3D(0.1, -0.02, 0)])

    polygon2_vol1 = polygon1_vol1.rotation(design3d.O3D, design3d.Z3D, math.pi).translation(0.2*design3d.Z3D)
    polygon3_vol1 = polygon2_vol1.rotation(design3d.O3D, design3d.Z3D, math.pi/8).translation(0.1*(design3d.Z3D+design3d.X3D+design3d.Y3D))
    faces_ = [faces.Triangle3D(*points) for points in polygon1_vol1.sewing(polygon2_vol1, design3d.X3D, design3d.Y3D)] \
                                                      + [faces.Triangle3D(*points)
                                        for points in polygon2_vol1.sewing(polygon3_vol1, design3d.X3D, design3d.Y3D)]
    bottom_surface3d = surfaces.Plane3D.from_plane_vectors(design3d.O3D, design3d.X3D, design3d.Y3D)
    bottom_surface2d = surfaces.Surface2D(polygon1_vol1.to_2d(design3d.O3D, design3d.X3D, design3d.Y3D),[])

    top_surface3d = surfaces.Plane3D.from_plane_vectors((0.3*design3d.Z3D).to_point(), design3d.X3D, design3d.Y3D)
    top_surface2d = surfaces.Surface2D(polygon3_vol1.to_2d(design3d.O3D, design3d.X3D, design3d.Y3D),[])

    bottom_face = faces.PlaneFace3D(bottom_surface3d, bottom_surface2d)
    top_face = faces.PlaneFace3D(top_surface3d, top_surface2d)
    faces_ += [bottom_face, top_face]

    #Instanciate shell
    shell1 = shells.ClosedShell3D(faces_)

    #Create a second shell from the first one, by rotating and translating it.
    shell2 = shell1.rotation(design3d.O3D, design3d.X3D, math.pi / 5)
    shell2 = shell2.translation(design3d.Vector3D(.5, .5, .5))

    #Search mimimum distance
    minimum_distance_between_two_shells, point1, point2 = shell1.minimum_distance(shell2, True)

    #plot
    ax = shell1.plot()
    shell2.plot(ax, 'r')
    point1.plot(ax, 'b')
    point2.plot(ax, 'g')

.. code-block:: python

   print('minimum_distance_between_two_shells: ', minimum_distance_between_two_shells)
   >>> minimum_distance_between_two_shells: 0.3374259086917476
