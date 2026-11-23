""" """

import os

import design3d.cloud
import design3d.core

faces = []
for file in os.listdir("E:/path/to/folder"):
    cloud = design3d.cloud.PointCloud3D.from_stl("E:/path/to/folder/" + file)
    cloud_faces = cloud.subdescription_2d()

    volum = design3d.core.VolumeModel(cloud_faces)
    print("len(cloud_faces)", len(cloud_faces))
    faces.extend(cloud_faces)
    # volum.save_to_file(file)
    print(file, len(faces))

volum = design3d.core.VolumeModel(faces)
volum.babylonjs()

################### READ STL

# cloud3d = design3d.cloud.PointCloud3D.from_stl(path)
# faces = cloud3d.subdescription_2d(resolution=20)

# volum = design3d.core.VolumeModel(faces)

# volum.babylonjs()
