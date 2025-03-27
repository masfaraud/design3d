import design3d as d3d
import design3d.edges as d3de
import design3d.faces as d3df
import design3d.primitives3d as p3d
import design3d.wires as d3dw
from design3d import surfaces

sphere = surfaces.SphericalSurface3D(d3d.Frame3D(d3d.O3D, d3d.X3D, d3d.Y3D, d3d.Z3D), 0.3)
sphere.plot()
# sphere.babylonjs()

face = d3df.SphericalFace3D.from_surface_rectangular_cut(sphere, 0, 2.5, 0, 0.5)
face.babylonjs()
face.plot()

# Try to generate a sphere from revoltion
radius = 0.03
p1 = d3d.Point2D(0, -radius)
p2 = d3d.Point2D(radius, 0.)
p3 = d3d.Point2D(0, radius)
arc = d3de.Arc2D.from_3_points(p1, p2, p3)
line = d3de.LineSegment2D(p3, p1)
contour = d3dw.Contour2D([arc, line])
sphere_revolution = p3d.RevolvedProfile(d3d.X3D, d3d.X3D, d3d.Y3D, contour,
                                        d3d.X3D, d3d.Y3D, angle=1.3)
sphere_revolution.babylonjs()
