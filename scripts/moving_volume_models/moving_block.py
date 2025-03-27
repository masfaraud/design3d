#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 10:54:45 2020

@author: masfaraud
"""

import volmdlr as d3d
import volmdlr.primitives3D as primitives3D

block1 = primitives3D.Block(d3d.Frame3D(d3d.O3D.copy(),
                                       d3d.X3D.copy(), d3d.Y3D.copy(), d3d.Z3D.copy()),
                            color=(0.8, 0.1, 0.1),
                            alpha=0.5,
                            name='Block 1')

block2 = block1.copy()
block2.color = [0.1, 0.1, 0.8]
block2.name = 'Block 2'


f1 = d3d.OXYZ.copy()

f2 = f1.rotation(d3d.Z3D, 0.1)
f2.translation_inplace(0.1 * d3d.X3D)

f3 = f2.rotation(d3d.Z3D, 0.1)
f3.translation_inplace(0.1 * d3d.X3D)

f4 = f3.rotation(d3d.Z3D, 0.1)
f4.translation_inplace(0.1 * d3d.X3D)

f5 = f4.rotation(d3d.Z3D, 0.1)
f5.translation_inplace(0.1 * d3d.X3D)


model = d3d.MovingVolumeModel([block1, block2], [[f1, -f1], [f2, -f2], [f3, -f3], [f4, -f4], [f5, -f5]])
model.babylonjs()

# Fetching baybylon data to put custom labels
babylon_data = model.babylon_data()

for i, d in enumerate(babylon_data['steps']):
    d['label'] = 'custom label {}'.format(i + 1)

model.babylonjs_from_babylon_data(babylon_data)
