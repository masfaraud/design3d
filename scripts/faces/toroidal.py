#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 18 12:40:31 2020

@author: masfaraud
"""

import design3d as vm
from design3d import faces, surfaces


R = 0.2
r = 0.03
ts = surfaces.ToroidalSurface3D(vm.OXYZ, R, r)

tf = faces.ToroidalFace3D.from_surface_rectangular_cut(ts, 0, 0.6, 0., 1.3)

tf.babylonjs(debug=True, use_cdn=False)
