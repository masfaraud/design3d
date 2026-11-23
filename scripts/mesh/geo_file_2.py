#!/usr/bin/env python3
"""
Created on Thu Jun 16 2022

@author: s.bendjebla
"""

import design3d
import design3d as d3d
import design3d.edges
import design3d.primitives3d as primitives3d

# import gmsh

# %% Extrusion

edges = [
    design3d.edges.LineSegment2D(d3d.Point2D(0, 0), d3d.Point2D(0.1, 0.0)),
    design3d.edges.LineSegment2D(d3d.Point2D(0.1, 0.0), d3d.Point2D(0.1, 0.2)),
    design3d.edges.Arc2D.from_3_points(d3d.Point2D(0.1, 0.2), d3d.Point2D(0.05, 0.25), d3d.Point2D(0.0, 0.2)),
    design3d.edges.LineSegment2D(d3d.Point2D(0.0, 0.2), d3d.Point2D(0, 0)),
]

outer_profile = d3d.wires.Contour2D(edges)


profile = primitives3d.ExtrudedProfile(
    d3d.Frame3D(d3d.O3D, d3d.Y3D, d3d.Z3D, d3d.X3D), outer_profile, [], 0.1, name="extrusion"
)

model = d3d.core.VolumeModel([profile])

model.to_geo(file_name="model_2_geo", factor=0.5, curvature_mesh_size=0, min_points=None, initial_mesh_size=5)

# %% gmsh file generation

# gmsh.initialize()
# gmsh.open("model.geo")

# gmsh.model.geo.synchronize()
# gmsh.model.mesh.generate(2)

# gmsh.write("model.msh")

# gmsh.finalize()

# %% DIRECT: gmsh file generation

model.to_msh(
    file_name="model_2", mesh_dimension=2, factor=1, curvature_mesh_size=0, min_points=None, initial_mesh_size=5
)
