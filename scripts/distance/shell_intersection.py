import volmdlr as d3d
import volmdlr.primitives3d as primitives3d

resolution = 0.0010

box = primitives3d.Block(
    d3d.Frame3D(d3d.Point3D(0.1, 0.1, 0.1), d3d.Vector3D(0.15, 0.0, 0.0),
               d3d.Vector3D(0.0, 0.15, 0.0), d3d.Vector3D(0.0, 0.0, 0.15)),
    alpha=0.6)

box.frame_mapping_inplace(d3d.Frame3D(d3d.Point3D(-0.07, -0.07, -0.07),
                             d3d.Point3D(1, 0, 0),
                             d3d.Point3D(0, 1, 0),
                             d3d.Point3D(0, 0, 1)), side='old')

box_red = primitives3d.Block(
    d3d.Frame3D(d3d.Point3D(-0.04, -0.04, -0.04), d3d.Vector3D(0.1, 0.0, 0.0),
               d3d.Vector3D(0.0, 0.1, 0.0), d3d.Vector3D(0.0, 0.0, 0.1)),
    color=(0.2, 1, 0.4), alpha=0.6)

assert type(box_red.shell_intersection(box, resolution=0.001)) == tuple

vol = d3d.core.VolumeModel([box, box_red])
vol.babylonjs()
