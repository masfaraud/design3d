"""
Showcase of TriangleShell3D import / export.
"""

import json

from design3d.shells import ClosedTriangleShell3D
from design3d.stl import Stl

triangle_shell_1 = Stl.load_from_file("../stl/simple.stl").to_closed_shell()

mesh_data = triangle_shell_1.to_mesh_data(round_vertices=False)
triangle_shell_2 = ClosedTriangleShell3D.from_mesh_data(mesh_data[0], mesh_data[1])

with open("triangle_shell.json", "w", encoding="utf-8") as file:
    json.dump(triangle_shell_1.to_dict(), file)
triangle_shell_3 = ClosedTriangleShell3D.from_json("triangle_shell.json")

print(triangle_shell_3 == triangle_shell_1)
print(triangle_shell_2 == triangle_shell_1)
