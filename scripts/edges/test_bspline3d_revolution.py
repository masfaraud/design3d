
import design3d
from design3d.models.edges import bspline_curve3d
bspline_curve_3d = bspline_curve3d()

face = bspline_curve_3d.revolution(design3d.O3D, design3d.X3D, design3d.TWO_PI)
face.babylonjs()
