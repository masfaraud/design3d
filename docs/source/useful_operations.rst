=================
Useful operations
=================

Export to json file
*******************

You can export any design3d object to a json file: its ``to_dict`` method returns a json-serializable dictionary.

Here is an example how you can save a plan face 3d to a .json file:

.. code-block:: python

    import json

    import design3d
    from design3d import surfaces, faces

    face = faces.PlaneFace3D.from_surface_rectangular_cut(surfaces.Plane3D(design3d.OXYZ), -1, 1, -1, 1)
    with open('path/to/where/to/save/your/file.json', 'w') as file:
        json.dump(face.to_dict(), file)


Import from json file
*********************

If you have a json file containing design3d objects, you can use the method ``design3d.base.SerializableObject.from_json`` to import it.

Example:

.. code-block:: python

    from design3d.base import SerializableObject

    design3d_object = SerializableObject.from_json('path/to/your/file.json')

Matplotlib plots
****************

To have a matplotlib visualization of a design3d object in 2D or 3D, you can call the ``plot`` method in any object. See the following example

.. plot::
    :include-source:
    :align: center

    import design3d
    from design3d import edges
    from design3d.core import EdgeStyle

    line_segment2d = edges.LineSegment2D(design3d.Point2D(1, 1), design3d.Point2D(-1, -2))
    line_segment2d.plot(edge_style=EdgeStyle('b'))

Model Visualization
*******************

To have a 3D visulaization of your model, most of the 3d objects has a babylonjs() method, which you can use to do so.
Babylon.js is an open-source, JavaScript framework and engine for creating and rendering 3D graphics and games in web browsers.
Here is an example on how you can do it.

.. code-block:: python

    import design3d
    from design3d import primitives3d

    block = primitives3d.Block(design3d.OXYZ, color=(1, 0.1, 0.1), alpha=0.6)
    block.babylonjs()

.. figure:: ../source/_static/index-images/block_babylonjs.png
