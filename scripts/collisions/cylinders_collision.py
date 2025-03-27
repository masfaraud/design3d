"""
Test code for intersections between cylinders
Generate random cylinders and create the casing for them
"""

from time import perf_counter

import volmdlr as d3d
import volmdlr.core
from volmdlr.primitives3d import Cylinder

cylinders = [
    Cylinder(
        position=d3d.Point3D(0, 0.1, 0),
        axis=d3d.Vector3D(1, 0, 0),
        radius=0.01,
        length=0.1,
        color=(1, 0, 0),
    ),
    Cylinder(
        position=d3d.Point3D(0, 0.05, 0),
        axis=d3d.Vector3D(1, 1, 0),
        radius=0.005,
        length=0.1,
        color=(0, 1, 0),
    ),
    Cylinder(
        position=d3d.Point3D(0, 0.159, 0),
        axis=d3d.Vector3D(1, 1, 0),
        radius=0.02,
        length=0.1,
        color=(0, 0, 1),
    ),
    Cylinder(
        position=d3d.Point3D(0, 0.1, 0.016),
        axis=d3d.Vector3D(0, 1, 0),
        radius=0.01,
        length=0.1,
        color=(1, 0, 1),
    ),
]

volume_model = d3d.core.VolumeModel(cylinders)
volume_model.babylonjs()

print("Collision detection methods")
start = perf_counter()

print(
    f"""\nRed & green:
min distance computed is {cylinders[0].min_distance_to_other_cylinder(cylinders[1])}m, 
collision: {cylinders[0].is_intersecting_other_cylinder(cylinders[1])}"""
)

print(
    f"""\nRed & blue:
min distance computed is {cylinders[0].min_distance_to_other_cylinder(cylinders[2])}m, 
collision: {cylinders[0].is_intersecting_other_cylinder(cylinders[2])}"""
)

print(
    f"""\nGreen & blue:
min distance computed is {cylinders[1].min_distance_to_other_cylinder(cylinders[2])}m, 
collision: {cylinders[1].is_intersecting_other_cylinder(cylinders[2])}"""
)

print(
    f"""\nRed & purple:
min distance computed is {cylinders[0].min_distance_to_other_cylinder(cylinders[3])}m, 
collision: {cylinders[0].is_intersecting_other_cylinder(cylinders[3])}"""
)

print(
    f"""\nGreen & purple:
min distance computed is {cylinders[1].min_distance_to_other_cylinder(cylinders[3])}m, 
collision: {cylinders[1].is_intersecting_other_cylinder(cylinders[3])}"""
)

print(
    f"""\nPurple & blue:
min distance computed is {cylinders[3].min_distance_to_other_cylinder(cylinders[2])}m,
collision: {cylinders[3].is_intersecting_other_cylinder(cylinders[2])}"""
)
# interpenetration: {cylinders[3].interference_volume_with_other_cylinder(cylinders[2])}

end = perf_counter()
print(f"\nTotal collision detection computation time: {end - start}s")
print(f"Time per collision: {((end - start)/12)*1000}ms")
