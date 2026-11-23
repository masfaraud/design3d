"""
Some conical surfaces models to perform unit test.
"""

import math

import design3d
from design3d import surfaces

conical_surface1 = surfaces.ConicalSurface3D(design3d.OXYZ, math.pi / 3)

frame_cone = design3d.Frame3D(design3d.Point3D(0.0, 0.0, 0.1), design3d.X3D, -design3d.Y3D, -design3d.Z3D)
conical_surface2 = surfaces.ConicalSurface3D(frame_cone, 0.336674819387)

frame = design3d.Frame3D(design3d.Point3D(0.0, 0.0, -0.0022143719324716786), design3d.X3D, design3d.Y3D, design3d.Z3D)
conical_surface3 = surfaces.ConicalSurface3D(frame, 1.0471975511966)
