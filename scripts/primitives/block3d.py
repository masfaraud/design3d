#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""

import design3d as d3d
import design3d.primitives3d as primitives3d
import design3d.step as d3d_step

resolution = 0.0010

box = primitives3d.Block(
    d3d.Frame3D(d3d.Point3D(0, 0, 0), d3d.Vector3D(0.3, 0, 0),
               d3d.Vector3D(0, 0.3, 0), d3d.Vector3D(0, 0, 0.3)),
    alpha=0.6)

box_red = primitives3d.Block(
    d3d.Frame3D(d3d.Point3D(0, 0, 0), d3d.Vector3D(0.4, 0, 0),
               d3d.Vector3D(0, 0.4, 0), d3d.Vector3D(0, 0, 0.4)),
    color=(0.2, 1, 0.4), alpha=0.6)

p1_ray = d3d.Point3D(-0.15, -0.15, -0.15)
p2_ray = d3d.Point3D(0.009855980224206917, 0.6250574317556334, -0.1407142090413507)

ray = d3d.edges.LineSegment3D(p1_ray, p2_ray)


ax = ray.plot(edge_style=d3d.edges.EdgeStyle(color='b'))
p1_ray.plot(ax=ax, color='b')
p2_ray.plot(ax=ax, color='b')
box_red.plot(ax=ax, color='r')
for face, inter_points in box_red.linesegment_intersections(ray):
    # print('ip', inter_point)
    face.plot(ax=ax, color='b')
    for inter_point in inter_points:
        inter_point.plot(ax=ax, color='r')


box_red.color = (1, 0.1, 0.1)
box_red.name = 'box_red'

box_green = box.frame_mapping(d3d.Frame3D(d3d.Point3D(0, 0.8, 0), d3d.Vector3D(1, 0, 0),
                         d3d.Vector3D(0, 1, 0), d3d.Vector3D(0, 0, 1)), 'new')

box_green.color = (0.1, 1, 0.1)
box_green.name = 'box_green'


box_blue = box.frame_mapping(d3d.Frame3D(d3d.Point3D(0, 0.2, 0), d3d.Vector3D(1, 0, 0),
                         d3d.Vector3D(0, 1, 0), d3d.Vector3D(0, 0, 1)), 'old')
box_blue.color = (0.1, 0.1, 1)
box_blue.name = 'box_blue'

assert box.faces[0] == box.faces[0]
print(box.minimum_distance(box_red))
print(box_green.is_intersecting_with(box_blue))
print(box_green.intersection_internal_aabb_volume(box_blue, resolution))
print(box_green.intersection_external_aabb_volume(box_blue, resolution))
model = d3d.core.VolumeModel([box, box_red, box_green, box_blue])
model.babylonjs(debug=True)

assert box.is_inside_shell(box_red) == True
assert box_red.is_inside_shell(box) == False

assert box.is_inside_shell(box_green) == False
assert box_green.is_inside_shell(box) == False

assert box.is_inside_shell(box_blue) == False
assert box_blue.is_inside_shell(box) == False

model = d3d.core.VolumeModel([box_red])
model.to_step('block.step')
step = d3d_step.Step.from_file('block.step')
model2 = step.to_volume_model()
new_box = box_red.union(box_blue)
for shell in new_box:
    shell.color = (1, 0.1, 0.1)
    shell.alpha = 0.6

d3d.core.VolumeModel(new_box).babylonjs()

orange_box = box.frame_mapping(d3d.Frame3D(d3d.Point3D(0, 0.1, 0.2),
                                          d3d.Vector3D(1.5, 0, 0),
                                          d3d.Vector3D(0, 2, 0),
                                          d3d.Vector3D(0, 0, 0.5)), 'old')
orange_box.color = (255/255, 127/255, 80/255)
orange_box.alpha = 0.6
d3d.core.VolumeModel([new_box[0], orange_box]).babylonjs()

redbox_union_orangebox = new_box[0].union(orange_box)
for shell in redbox_union_orangebox:
    shell.color = (1, 0.1, 0.1)
    shell.alpha = 0.6
d3d.core.VolumeModel(redbox_union_orangebox).babylonjs()

box = primitives3d.Block(
    d3d.Frame3D(d3d.Point3D(0, 0, 0), d3d.Vector3D(0.3, 0, 0),
               d3d.Vector3D(0, 0.3, 0), d3d.Vector3D(0, 0, 0.3)),
    alpha=0.6)
box_red = primitives3d.Block(
    d3d.Frame3D(d3d.Point3D(0, 0, 0), d3d.Vector3D(0.1, 0, 0),
               d3d.Vector3D(0, 0.1, 0), d3d.Vector3D(0, 0, 0.1)),
    color=(0.2, 1, 0.4), alpha=0.6)

for i in range(1):
    # print('----NEW STEP----', box_red.is_inside_shell(box, resolution))
    print('distance_to_shell', box.minimum_distance(box_red))
    # print('shell_intersection', box.shell_intersection(box_red, resolution))
    print('volume', box_red.bounding_box.volume(), box.bounding_box.volume())
    print('intersection_internal_aabb_volume', box.intersection_internal_aabb_volume(box_red, resolution), box_red.intersection_internal_aabb_volume(box, resolution))
    print('intersection_external_aabb_volume', box.intersection_external_aabb_volume(box_red, resolution), box_red.intersection_external_aabb_volume(box, resolution))

    box_red = box_red.translation(d3d.Vector3D(0.01, 0, 0))
#
#
model = d3d.core.VolumeModel([box, box_red])
model.babylonjs(debug=True)
