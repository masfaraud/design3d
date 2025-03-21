#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 16 2022

@author: s.bendjebla
"""

import volmdlr
import volmdlr.gmsh_d3d

# %% 2D

file_path = 'model'

gmsh_parser = volmdlr.gmsh_d3d.GmshParser.from_file(file_path+'.msh')

mesh = gmsh_parser.define_triangular_element_mesh()

gmsh_parser.to_vtk(file_path)

mesh.plot()

# %% 3D

file_path = 'block'

gmsh_parser = volmdlr.gmsh_d3d.GmshParser.from_file(file_path+'.msh')

mesh = gmsh_parser.define_tetrahedron_element_mesh()

gmsh_parser.to_vtk(file_path)

# mesh.plot()

# %% 3D (Quadratic)

file_path = 'mesh_quadratic'

gmsh_parser = volmdlr.gmsh_d3d.GmshParser.from_file(file_path+'.msh')

mesh = gmsh_parser.define_quadratic_tetrahedron_element_mesh()

gmsh_parser.to_vtk(file_path)

# mesh.plot()
