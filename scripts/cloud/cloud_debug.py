# -*- coding: utf-8 -*-
"""

"""

import os

import matplotlib.pyplot as plt

import volmdlr as d3d
import volmdlr.cloud
import volmdlr.core
import volmdlr.edges as d3de
import volmdlr.faces as d3df
import volmdlr.wires as d3dw

faces = []
for file in os.listdir("E:/path/to/folder") :
    cloud = volmdlr.cloud.PointCloud3D.from_stl("E:/path/to/folder/" + file)
    cloud_faces = cloud.subdescription_2d()
    
    volum = volmdlr.core.VolumeModel(cloud_faces)
    print('len(cloud_faces)', len(cloud_faces))
    faces.extend(cloud_faces)
    # volum.save_to_file(file)
    print(file, len(faces))
    
volum = volmdlr.core.VolumeModel(faces)
volum.babylonjs()
        
################### READ STL

# cloud3d = volmdlr.cloud.PointCloud3D.from_stl(path)
# faces = cloud3d.subdescription_2d(resolution=20)

# volum = volmdlr.core.VolumeModel(faces)

# volum.babylonjs()
