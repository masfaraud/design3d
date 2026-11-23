Roadmap and current limitations
===============================

What's new
----------

The version 0.1.0 released on April 4, 2023 includes:

- a documentation
- method names follow the pep8 instructions, with possible backward
  compatibility

Current limitations
-------------------

Minimum distances
*****************

- Minimum distances between curved edges (BSpline curves, arcs, ellipses) are computed by numerical minimization.
  Results are accurate to about 1e-6 and may differ in the last digits from one platform to another.
- ``Face3D.face_minimum_distance`` falls back, when no specific method exists for the pair of faces, to the
  distance between the two face triangulations. This is an approximation: its error depends on the mesh
  refinement and is typically around 1e-4 relative. ``Shell3D.minimum_distance`` inherits this limitation.

Roadmap
-------

No future improvements are planned.
