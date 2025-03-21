#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 10 14:11:53 2021

@author: dasilva
"""

import os

import numpy as np
from scipy.spatial import ConvexHull

import volmdlr.cloud
import volmdlr.core
import volmdlr.stl as d3dstl

# import volmdlr as d3d
# import volmdlr.wires as d3dw
# import volmdlr.faces as d3df
# import volmdlr.edges as d3de
# import matplotlib.pyplot as plt

shells = []
path = os.getcwd()
stl_path = path
os.chdir(stl_path)
print('os.listdir(stl_path) :', os.listdir(stl_path))
for stl_file in os.listdir(stl_path):
    if len(stl_file.split('.')) > 1:
        if stl_file.split('.')[1] == 'stl':
            stl = volmdlr.stl.Stl.from_file(stl_file)
            stl.name = stl_file
            print('name :', stl.name)
            # list_points = stl.extract_points_BIS()
            list_points = stl.extract_points()
            print("list_points :", len(list_points))
            pointcloud3d = volmdlr.cloud.PointCloud3D(list_points)
            if len(list_points) < 10000:
                alpha = 0.035
                number_point_samples = 100
            elif len(list_points) < 100000:
                alpha = 0.08
                number_point_samples = 300
            elif len(list_points) < 200000:
                alpha = 0.2
                number_point_samples = 500
            else:
                alpha = 0.5
                number_point_samples = 10000
            shell = pointcloud3d.alpha_shape(alpha, number_point_samples)
            shell.color = (1, 0.1, 0.1)
            shell.alpha = 0.6
            volum = volmdlr.core.VolumeModel([shell])
            volum.babylonjs()
            shells.append(shell)
            break

    
# volum = volmdlr.core.VolumeModel(shells)
# volum.babylonjs()
