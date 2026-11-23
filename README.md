<h1 align="center">
  <img src="https://raw.githubusercontent.com/masfaraud/design3d/master/src/design3d/assets/logos/design3d.jpg" style="width:300px"><br/>design3d
</h1>

<h4 align="center">
  A computation-oriented Python 3D modeler based on B-Rep, with STEP and STL import and export
</h4>

<div align="center">
  <a href="https://github.com/masfaraud/design3d/actions/workflows/test.yml"><img src="https://github.com/masfaraud/design3d/actions/workflows/test.yml/badge.svg?branch=master"></a>
  <a href="https://github.com/masfaraud/design3d/stargazers/"><img src="https://badgen.net/github/stars/masfaraud/design3d"></a>
  <a href="https://pypi.org/project/design3d/"><img src="https://img.shields.io/pypi/v/design3d.svg"></a>
  <a href="https://github.com/masfaraud/design3d/graphs/contributors"><img src="https://img.shields.io/github/contributors/masfaraud/design3d.svg"></a>
  <a href="https://github.com/masfaraud/design3d/issues"><img src="https://img.shields.io/github/issues/masfaraud/design3d.svg"></a>
</div>

<div align="center">
  <a href="#description"><b>Description</b></a> |
  <a href="#features"><b>Features</b></a> |
  <a href="#user-installation"><b>User Installation</b></a> |
  <a href="#dev-installation"><b>Dev Installation</b></a> |
  <a href="#usage"><b>Usage</b></a> |
  <a href="#license"><b>License</b></a> |
  <a href="#team-and-contributors"><b>Contributors</b></a>
</div>

## Description

design3d is a python 3d design package enabling CAD automations.
With it, you can easily create 3D models from python code.
Check the examples to see what you can do with this library.
A hard fork of the discontinued volmdlr project.

<p align="center"><img src="https://raw.githubusercontent.com/masfaraud/design3d/master/docs/source/images/casing.jpg" width="40%" /> <img src="https://raw.githubusercontent.com/masfaraud/design3d/master/docs/source/images/casing_contours.png" width="55%" /></p>
<i>A casing is defined by a 2D contour formed with the primitive RoundedLineSegment2D. This contour is offset by the casing width.</i><br/><br/><br/>

<p align="center"><img src="https://raw.githubusercontent.com/masfaraud/design3d/master/docs/source/images/sweep1.jpg" width="45%" /> <img src="https://raw.githubusercontent.com/masfaraud/design3d/master/docs/source/images/sweepMPLPlot.jpg" width="50%" /></p>
<i>A Sweep is pipes, created with Circle2D/Arc2D which is contained in a Contour2D. You have to create the neutral fiber, i.e., the pipe’s road, with the primitive RoundedLineSegment3D.</i><br/><br/><br/>

<p align="center"><img src="https://raw.githubusercontent.com/masfaraud/design3d/master/docs/source/images/polygon.jpg" width="47%" /></p>
<i>A polygon is defined out of points. Random points are sampled and the tested whether they are inside or outside the polygon. They are plotted with the Matplotlib binding MPLPlot with custom styles:
- red if they are outside,
- blue if they are inside
</i><br/><br/><br/>

<p align="center"><img src="https://raw.githubusercontent.com/masfaraud/design3d/master/docs/source/images/bspline_surface_split.png" width="47%" /></p>
<i>A 3D B-spline surface split by a 3D B-spline curve.</i><br/><br/><br/>

## Features

- [x] Generate 2D and 3D geometries from python
- [x] Handles complex geometries: B-spline curves and surfaces
- [x] Primitives provide computational tasks: distances, belonging, union, intersections, etc.
- [x] STEP/STL imports and exports
- [x] Geometries display in your web browser with [babylon.js](https://www.babylonjs.com/)

## User Installation

```bash
pip install design3d
```

design3d requires Python 3.12 or later.

## Dev Installation

Building design3d compiles Cython extensions, so you need a C/C++ compiler (usually already available on Linux and
macOS; on Windows, install the Microsoft C++ Build Tools).

```bash
git clone https://github.com/masfaraud/design3d.git
cd design3d
pip install -e '.[test,doc]'
pre-commit install
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to run the tests and checks before opening a pull request.

## Usage

```python
import design3d
from design3d import primitives3d
from design3d.core import VolumeModel

# A 30 cm cube centered on the origin
block = primitives3d.Block(
    design3d.Frame3D(design3d.O3D, 0.3 * design3d.X3D, 0.3 * design3d.Y3D, 0.3 * design3d.Z3D),
    name="block",
)
print(block.volume())  # 0.027

model = VolumeModel([block])
model.to_step("block.step")  # export to STEP
model.babylonjs()  # display in your web browser
```

More examples are in the [scripts](https://github.com/masfaraud/design3d/tree/master/scripts) folder.

## Documentation

The documentation is not published online yet. To build it locally:

```bash
pip install '.[doc]'
make -C docs html
```

Then open `docs/build/html/index.html`.

## License

100% open source under the LGPL 2.1 license. See [LICENSE](LICENSE) for more details.

## Team and contributors

design3d is a hard fork of the discontinued [volmdlr](https://github.com/Dessia-tech/volmdlr) project: credits to the
volmdlr project team.
