# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## v0.1.0 [Future]

### Added

- Loft primitive: a solid interpolating planar sections, each given by a 2D contour and a frame
- primitives3d.loft_faces: B-spline faces interpolating 3D wires (open or closed), to build open shells
- BSplineSurface3D.from_parametrized_points_interpolation: surface interpolation through points at imposed parameters
- primitives2d: parametric profiles `RoundedRectangle2D`, `RegularPolygon2D` and `Slot2D`, placed by a center and an
  angle. Copies and rigid transformations keep the class and its parameters
- primitives2d: `CirclesConvexHull2D`, the exact contour enveloping circles (arcs joined by their external
  tangents) for crank webs, connecting rods or levers. Its offset is the hull of the offset circles
- babylonjs viewer: a scene tree panel replaces the babylonjs inspector. It shows the hierarchy of the model
  (assemblies, compounds, shells and their faces when `merge_meshes=False`), with per-node visibility, opacity,
  color, focus and isolation, selection from the tree or by clicking in the 3D view, a name filter, standard views,
  edges, wireframe and axes toggles, and keyboard shortcuts. The inspector stays available from the toolbar, and is
  opened at startup with `debug=True`
- babylonjs viewer: orthographic projection by default, the perspective projection being available from the
  toolbar (P key), and a chamfered view cube in the top right corner replacing the standard view buttons: its faces,
  edges and corners align the view on 26 directions with a short animation, and dragging it orbits the camera
- `babylon_data` of volume models, assemblies and compounds has a `tree` entry describing the hierarchy of the
  primitives
- ExtrudedProfile: `draft_angle`, `inner_draft_angles` and `symmetric` options. A draft shrinks the section away
  from the sketch plane, with planar faces on line segments and conical faces on arcs. The holes take the draft
  angle by default, as for a molded part, or their own angles, for instance to keep the thickness of stamped walls.
  A symmetric extrusion spans half its length on each side of the sketch plane, which is the neutral plane of the
  draft

### Fixed

- babylonjs: pages generated with `use_cdn=False` no longer fail on the `$` characters of the embedded javascript
  libraries
- MovingVolumeModel: babylonjs pages are no longer blank with numpy 2, which wrote the scene size as `np.float64(...)`
- Block: the bounding box encloses the block when its frame is not aligned with the axes, for instance a block
  placed in an assembly with a rotated frame, instead of being flattened
- STEP export: conical surfaces whose apex is not on their axis are no longer reimported with a radius divided by
  1000 (`ConicalSurface3D.to_step` wrote `ref_radius` in meters in a file declared in millimeters)
- STEP export: cones narrowing along their axis are written with a positive `semi_angle`, as required by STEP, by
  reversing their axis
- Arc3D: the bounding box is exact, instead of being computed on discretization points that miss the extrema of
  the arc
- Arc2D: the bounding rectangle is exact, instead of being computed on discretization points that miss the extrema
  of the arc. Bounding rectangles of 2D wires and contours, `Contour2D.bounding_points` and
  `Contour2D.point_inside` no longer reject points on or near the extreme points of arcs, such as the ends of a slot
- ArcEllipse2D, FullArcEllipse2D: the bounding rectangle is exact, instead of being computed on discretization points
  that miss the extrema of the arc
- ToroidalFace3D: the bounding box includes the extrema of the coordinates inside the face, such as the outer equator
  of a band around the torus, instead of only its boundary contour
- BSplineFace3D: triangulation of faces with few control points has interior vertices, instead of triangles joining
  distant boundary points away from the surface
- BSplineSurface3D: point inversion no longer gets stuck when it starts on the seam of a periodic surface
- BSplineSurface3D: parametric coordinate of an edge start/end lying on a singularity is taken from its neighbour
  parametric point, instead of an ill-conditioned point inversion
- BSplineSurface3D: point inversion near a singularity no longer depends on rounding to pick its starting point,
  which could give an open face contour on some platforms
- BSplineSurface3D: changing the sample size now resets the points evaluated on the previous sampling grid
- Vector3D.plot: the arrow is drawn with recent Matplotlib versions, which require `do_3d_projection` on 3D artists
- Package metadata: the license is the LGPL 2.1 of the LICENSE file, not a Creative Commons license
- Measure2D.plot: `ax` and `edge_style` are optional, as for other edges, and the axes are returned
- BoundingBox.center and BSplineSurface3D.decompose no longer keep the objects alive in a global cache
- BSplineCurve2D: `straight_line_area` is signed, as for arcs, and `straight_line_center_of_mass` is the center of
  mass of this area. Contour2D.center_of_mass is right for contours with B-spline edges
- Contour2D.area: holes joined to the outer loop at one point are subtracted, and full arcs, elliptic arcs and
  B-spline curves use their area instead of a triangulation of the discretized contour
- Arc2D.axial_symmetry: the arc lies on the symmetric circle, instead of the original one
- ClosedPolygon2D: the `name` argument is kept, instead of being passed as the reference path
- OpenedRoundedLineSegments2D and ClosedRoundedLineSegments2D: `invert` no longer fails, and keeps each radius on
  its point
- ClosedPolygon2D.offset: the sides are moved by the offset distance, instead of a distance depending on the angles
- Arc2D.direction_vector follows the direction of travel of clockwise arcs, instead of always turning
  counterclockwise
- Wire2D.offset and Contour2D.offset: contours with arcs tangent to their neighbouring edges, such as rounded
  profiles, are offset instead of failing
- RoundedLineSegments2D.offset_lines: a single line is offset, instead of being left in place, adjacent sides
  parallel to each other and the closing line of a closed contour no longer make it fail, and a free end of an
  opened wire moves along the normal of the lines

### Changed

- RoundedLineSegments2D: `offset` and `offset_lines` follow the convention of Wire2D, Contour2D and
  ClosedPolygon2D: a positive offset moves to the right of the direction of travel, which enlarges a counterclockwise
  contour. The sign of existing calls must be inverted
- design3d requires Python 3.12 or later
- Library messages go through `warnings` or `logging` instead of `print`, and warnings point to the calling code
- FlatElementError gives the element area in its message instead of printing it and plotting the element

### Removed

- `design3d.core.determinant`, `Surface2D.split_at_centers` and `Point3D.babylon_script`, which were unused
- `RoundedLineSegments2D.get_offset_normal_vectors` and `RoundedLineSegments2D.get_offset_new_points`, helpers of
  `offset_lines` replaced by a simpler computation

### Build

- moved source to src folder
- package metadata moved from setup.py to pyproject.toml, version computed from git tags by setuptools-scm
- ruff replaces black and pylint for formatting and linting, configured in pyproject.toml
