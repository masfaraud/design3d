# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## v0.1.0 [Future]

### New Features

- primitives3D: Loft

### Fixed

- BSplineSurface3D: point inversion no longer gets stuck when it starts on the seam of a periodic surface
- BSplineSurface3D: parametric coordinate of an edge start/end lying on a singularity is taken from its neighbour
  parametric point, instead of an ill-conditioned point inversion
- BSplineSurface3D: point inversion near a singularity no longer depends on rounding to pick its starting point,
  which could give an open face contour on some platforms
- BSplineSurface3D: changing the sample size now resets the points evaluated on the previous sampling grid
- Vector3D.plot: the arrow is drawn with recent Matplotlib versions, which require `do_3d_projection` on 3D artists
- Package metadata: the license is the LGPL 2.1 of the LICENSE file, not a Creative Commons license

### Build

- moved source to src folder
