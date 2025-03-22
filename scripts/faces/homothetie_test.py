# -*- coding: utf-8 -*-
"""

"""

import math

from scipy.optimize import bisect, minimize

import design3d
import design3d.cloud
import design3d.faces as d3df
import design3d.primitives3d as p3d
import design3d.stl as d3ds

stl = d3ds.Stl.from_file('C:\\Users\\Mack_Pro\\Documents\\git\\Renault\\DynamicLoop\Mise a jour GMP S30\\jeu2\\forbi_disc\\new_HR18 FDU piece chaude.stl')
shell3d = stl.to_closed_shell()

points1 = stl.extract_points()
mid_pt1 = design3d.O3D
for pt in points1 :
    mid_pt1 += pt
center1 = mid_pt1/(len(points1))


frame = design3d.Frame3D(design3d.O3D, design3d.X3D*1.5, design3d.Y3D*1.5, design3d.Z3D*1.5)
new_shell = shell3d.frame_mapping(frame, 'old')
new_shell.alpha = 0.4
new_shell.color = (250,0,0)

center2 = center1.frame_mapping(frame, 'old')
new_shell_displaced = new_shell.translation(center1-center2)

vol = design3d.core.VolumeModel([shell3d, new_shell_displaced])
vol.babylonjs()

dmin = shell3d.faces[0].point1.point_distance(new_shell_displaced.faces[0].point1)
for face1, face2 in zip(shell3d.faces, new_shell_displaced.faces):
    
    p1, p2, p3 = face1.point1, face1.point2, face1.point3
    p12, p22, p32 = face2.point1, face2.point2, face2.point3
    
    if p1.point_distance(p12) < dmin :
        dmin = p1.point_distance(p12)
        
    if p2.point_distance(p22) < dmin :
        dmin = p2.point_distance(p22)
        
    if p3.point_distance(p32) < dmin :
        dmin = p3.point_distance(p32)
        
        
print(dmin)

objectif = 100e-3


def homothetie_x(x) :
    frame = design3d.Frame3D(design3d.O3D, design3d.X3D*x[0], design3d.Y3D*x[0], design3d.Z3D*x[0])
    new_shell = shell3d.frame_mapping(frame, 'old')
    
    center2 = center1.frame_mapping(frame, 'old')
    new_shell_displaced = new_shell.translation(center1-center2) 
    
    dmin_x = abs(shell3d.faces[0].point1.dot(design3d.X3D)-new_shell_displaced.faces[0].point1.dot(design3d.X3D))
    
    for face1, face2 in zip(shell3d.faces, new_shell_displaced.faces):
        p1, p2, p3 = face1.point1, face1.point2, face1.point3
        p12, p22, p32 = face2.point1, face2.point2, face2.point3
        mid1, mid12 = (p1+p2+p3)/3, (p12+p22+p32)/3
        
        dist = []
        for pt1, pt2 in zip([p1,p2,p3,mid1], [p12,p22,p32,mid12]):
            dist.append(pt1.point_distance(pt2))
            
        if min(dist) < dmin_x :
            dmin_x = min(dist)
    
    return abs(objectif-dmin_x)

def homothetie_y(x) :
    frame = design3d.Frame3D(design3d.O3D, design3d.X3D*x[0], design3d.Y3D*x[0], design3d.Z3D*x[0])
    new_shell = shell3d.frame_mapping(frame, 'old')
    
    center2 = center1.frame_mapping(frame, 'old')
    new_shell_displaced = new_shell.translation(center1-center2) 
    
    dmin_y = abs(shell3d.faces[0].point1.dot(design3d.Y3D)-new_shell_displaced.faces[0].point1.dot(design3d.Y3D))
    for face1, face2 in zip(shell3d.faces, new_shell_displaced.faces):
        p1, p2, p3 = face1.point1, face1.point2, face1.point3
        p12, p22, p32 = face2.point1, face2.point2, face2.point3
        mid1, mid12 = (p1+p2+p3)/3, (p12+p22+p32)/3
        
        dist = []
        for pt1, pt2 in zip([p1,p2,p3,mid1], [p12,p22,p32,mid12]):
            dist.append(pt1.point_distance(pt2))
            
        if min(dist) < dmin_y :
            dmin_y = min(dist)
    
    return abs(objectif-dmin_y)

def homothetie_z(x) :
    frame = design3d.Frame3D(design3d.O3D, design3d.X3D*x[0], design3d.Y3D*x[0], design3d.Z3D*x[0])
    new_shell = shell3d.frame_mapping(frame, 'old')
    
    center2 = center1.frame_mapping(frame, 'old')
    new_shell_displaced = new_shell.translation(center1-center2) 
    
    dmin_z = abs(shell3d.faces[0].point1.dot(design3d.Z3D)-new_shell_displaced.faces[0].point1.dot(design3d.Z3D))
    for face1, face2 in zip(shell3d.faces, new_shell_displaced.faces):
        p1, p2, p3 = face1.point1, face1.point2, face1.point3
        p12, p22, p32 = face2.point1, face2.point2, face2.point3
        mid1, mid12 = (p1+p2+p3)/3, (p12+p22+p32)/3
        
        dist = []
        for pt1, pt2 in zip([p1,p2,p3,mid1], [p12,p22,p32,mid12]):
            dist.append(pt1.point_distance(pt2))
            
        if min(dist) < dmin_z :
            dmin_z = min(dist)
            
    return abs(objectif-dmin_z)



res_x = minimize(homothetie_x, (2),
               options={'eps': 1e-6})

res_y = minimize(homothetie_y, (2),
                options={'eps': 1e-6})

res_z = minimize(homothetie_z, (2),
                options={'eps': 1e-6})

print(res_x)
print(res_y)
print(res_z)

spheres = []
for pt in points1:
    spheres.append(p3d.Sphere(pt, objectif))
    

frameres = design3d.Frame3D(design3d.O3D, design3d.X3D*res_x.x[0], design3d.Y3D*res_y.x[0], design3d.Z3D*res_z.x[0])
new_shell = shell3d.frame_mapping(frameres, 'old')
new_shell.alpha = 0.4
new_shell.color = (0,0,0)

center2 = center1.frame_mapping(frameres, 'old')
new_shell_displaced = new_shell.translation(center1-center2)




frameresx = design3d.Frame3D(design3d.O3D, design3d.X3D*res_x.x[0], design3d.Y3D, design3d.Z3D)
new_shell = shell3d.frame_mapping(frameresx, 'old')
new_shell.alpha = 0.4
new_shell.color = (250,0,0)

center2 = center1.frame_mapping(frameresx, 'old')
new_shell_displaced_x = new_shell.translation(center1-center2)


frameresy = design3d.Frame3D(design3d.O3D, design3d.X3D, design3d.Y3D*res_y.x[0], design3d.Z3D)
new_shell = shell3d.frame_mapping(frameresy, 'old')
new_shell.alpha = 0.4
new_shell.color = (0,250,0)

center2 = center1.frame_mapping(frameresy, 'old')
new_shell_displaced_y = new_shell.translation(center1-center2)


frameresz = design3d.Frame3D(design3d.O3D, design3d.X3D, design3d.Y3D, design3d.Z3D*res_z.x[0])
new_shell = shell3d.frame_mapping(frameresz, 'old')
new_shell.alpha = 0.4
new_shell.color = (0,0,250)

center2 = center1.frame_mapping(frameresz, 'old')
new_shell_displaced_z = new_shell.translation(center1-center2)

vol = design3d.core.VolumeModel([shell3d, new_shell_displaced, new_shell_displaced_x, new_shell_displaced_y,new_shell_displaced_z]+spheres)
vol.babylonjs()
