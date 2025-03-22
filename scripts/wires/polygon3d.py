#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 10 17:02:36 2017

"""

import math
import time

import design3d as d3d
import design3d.wires as d3dw

p1 = d3d.Point3D(0, 0, 0)
p2 = d3d.Point3D(1, 0, 0.1)
p3 = d3d.Point3D(2, 1, -0.1)
p4 = d3d.Point3D(1, 0.5, 0.1)
p5 = d3d.Point3D(-0.5, 1, 0)
polygon = d3d.wires.ClosedPolygon3D([p1, p2, p3, p4, p5])
