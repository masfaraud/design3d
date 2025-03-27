import time

import volmdlr as d3d
from volmdlr.primitives3d import Cylinder

cylinder1 = Cylinder(
    position=d3d.Point3D(0, 0.1, 0),
    axis=d3d.Vector3D(1, 0, 0),
    radius=0.01,
    length=0.1,
)

cylinder2 = Cylinder(
    position=d3d.Point3D(1, 0.11, 0.3),
    axis=d3d.Vector3D(1, 1, -6),
    radius=0.01,
    length=0.1,
)

N = 100

start = time.perf_counter()
for _ in range(N):
    dist = cylinder2.min_distance_to_other_cylinder(cylinder1)

print(f"time per operation: {((time.perf_counter() - start)/N)*1000}ms")
