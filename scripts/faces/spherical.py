import design3d as vm
import design3d.edges as vme
import design3d.faces as vmf
import design3d.primitives3d as p3d
import design3d.wires as vmw
from design3d import surfaces

sphere = surfaces.SphericalSurface3D(vm.Frame3D(vm.O3D, vm.X3D, vm.Y3D, vm.Z3D), 0.3)
sphere.plot()
# sphere.babylonjs()

face = vmf.SphericalFace3D.from_surface_rectangular_cut(sphere, 0, 2.5, 0, 0.5)
face.babylonjs()
face.plot()

# Try to generate a sphere from revoltion
radius = 0.03
p1 = vm.Point2D(0, -radius)
p2 = vm.Point2D(radius, 0.)
p3 = vm.Point2D(0, radius)
arc = vme.Arc2D.from_3_points(p1, p2, p3)
line = vme.LineSegment2D(p3, p1)
contour = vmw.Contour2D([arc, line])
sphere_revolution = p3d.RevolvedProfile(vm.X3D, vm.X3D, vm.Y3D, contour,
                                        vm.X3D, vm.Y3D, angle=1.3)
sphere_revolution.babylonjs()
