#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import os

# import design3d as d3d
import design3d.step

# import design3d.cloud as d3dcd

for step_file in [
    "tore1.step",
    "cone1.step",
    "cone2.step",
    "cylinder.step",
    "block.step",
    "strange_gasket.step",
    "assembly.step",
    # '2_bspline_faces.stp'# Uncomment when bug of delta fixed!
]:
    print("Reading step file: ", step_file)
    # filepath = os.path.join('step', step_file)
    step = design3d.step.Step.from_file(filepath=step_file)
    model = step.to_volume_model()
    assert len(model.primitives) > 0.0
    model.to_step(step_file + "_reexport")
    model.primitives[0].alpha = 0.6
    model.primitives[0].color = (1, 0.1, 0.1)
    model.babylonjs()

    file_io = io.FileIO(step_file, "r")
    step = design3d.step.Step.from_stream(stream=file_io)
    model = step.to_volume_model()
    assert len(model.primitives) > 0.0
    model.to_step(step_file + "_reexport")

    model2 = model.copy()

    # model2 = model.copy()
    # assert model == model2

    # Serialization round trip
    design3d.core.VolumeModel.dict_to_object(model.to_dict())
