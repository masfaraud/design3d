import design3d as d3d
import design3d.primitives3d as primitives3d

resolution = 0.0010

box = primitives3d.Block(
    d3d.Frame3D(
        d3d.Point3D(0.1, 0.1, 0.1),
        d3d.Vector3D(0.15, 0.0, 0.0),
        d3d.Vector3D(0.0, 0.15, 0.0),
        d3d.Vector3D(0.0, 0.0, 0.15),
    ),
    alpha=0.6,
)

box = box.frame_mapping(
    d3d.Frame3D(d3d.Point3D(-0.07, -0.07, -0.07), d3d.X3D, d3d.Y3D, d3d.Z3D),
    side="old",
)

box_red = primitives3d.Block(
    d3d.Frame3D(
        d3d.Point3D(-0.04, -0.04, -0.04),
        d3d.Vector3D(0.1, 0.0, 0.0),
        d3d.Vector3D(0.0, 0.1, 0.0),
        d3d.Vector3D(0.0, 0.0, 0.1),
    ),
    color=(0.2, 1, 0.4),
    alpha=0.6,
)

assert box_red.is_intersecting_with(box)

vol = d3d.core.VolumeModel([box, box_red])
vol.babylonjs()
