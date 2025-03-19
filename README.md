<h1 align="center">
  <img src="https://raw.githubusercontent.com/masfaraud/design3d/master/design3d/assets/logos/design3d.jpg" style="width:300px"><br/>design3d
</h1>

<h4 align="center">
  A computations-oriented python VOLume MoDeLeR with STEP support for import and export
</h4>

<div align="center">
  <a href="https://gitHub.com/masfaraud/design3d/stargazers/"><img src="https://badgen.net/github/stars/masfaraud/design3d"></a>  
  <a href="https://pypi.org/project/design3d/"><img src="https://img.shields.io/pypi/v/design3d.svg"></a>
  <a href="https://github.com/masfaraud/design3d/graphs/contributors"><img src="https://img.shields.io/github/contributors/masfaraud/design3d.svg"></a>
  <a href="https://github.com/masfaraud/design3d/issues"><img src="https://img.shields.io/github/issues/masfaraud/design3d.svg"></a>
</div>

<div align="center">
  <a href="#description"><b>Description</b></a> |
  <a href="#features"><b>Features</b></a> |
  <a href="#user-installation"><b>User Installation</b></a> |
  <a href="#dev-installation"><b>Dev Installation</b></a> |
  <a href="https://github.com/masfaraud/design3d/tree/master/scripts"><b>Usage</b></a> |
  <a href="#licence"><b>Licence</b></a> |
  <a href="#contributors"><b>Contributors</b></a> |
</div>

## Description

design3d is a python 3d design package enabling CAD automations.
With it, you can easily create 3D models from python code.
Check the examples to see what you can do with this library.
A hard fork of the discontinued volmdlr project.

<p align="center"><img src="https://raw.githubusercontent.com/masfaraud/design3d/master/doc/source/images/casing.jpg" width="40%" /> <img src="https://raw.githubusercontent.com/masfaraud/design3d/master/doc/source/images/casing_contours.png" width="55%" /></p>
<i>A casing is defined by a 2D contour formed with the primitive RoundedLineSegment2D. This contour is offset by the casing width.</i><br/><br/><br/>

<p align="center"><img src="https://raw.githubusercontent.com/masfaraud/design3d/master/doc/source/images/sweep1.jpg" width="45%" /> <img src="https://raw.githubusercontent.com/masfaraud/design3d/master/doc/source/images/sweepMPLPlot.jpg" width="50%" /></p>
<i>A Sweep is pipes, created with Circle2D/Arc2D which is contained in a Contour2D. You have to create the neutral fiber, i.e., the pipe’s road, with the primitive RoundedLineSegment3D.</i><br/><br/><br/>

<p align="center"><img src="https://raw.githubusercontent.com/masfaraud/design3d/master/doc/source/images/polygon.jpg" width="47%" /></p>
<i>A polygon is defined out of points. Random points are sampled and the tested whether they are inside or outside the polygon. They are plotted with the Matplotlib binding MPLPlot with custom styles:
- red if they are outside,
- blue if they are inside
</i><br/><br/><br/>

<p align="center"><img src="https://raw.githubusercontent.com/masfaraud/design3d/master/doc/source/images/bspline_surface_split.png" width="47%" /></p>
<i>A 3D B-spline surface split by a 3D B-spline curve.</i><br/><br/><br/>

## Features

- [x] Generate 2D and 3D geometries from python
- [x] Handles complexe geometries : B-spline curves and surfaces
- [x] Primitives provide computational tasks : distances, belonging, union, intersections, etc.
- [x] STEP/STL imports and exports
- [x] Geometries display in your web browser with [babylon.js](https://www.babylonjs.com/)

## User Installation

```bash
pip install design3d
# or
pip3 install design3d
```

## Dev Installation

Before using design3d, be sure to have a C/C++ compiler (not necessary on Linux).  
N.B : With Windows you have to download one and allow it to read Python’s code.

First, [clone](https://docs.github.com/en/get-started/getting-started-with-git/about-remote-repositories) the package.
Then, enter the newly created design3d repository.
Finally, develop the setup.py file, and you are good to go !

```bash
git clone https://github.com/masfaraud/design3d.git

cd design3d

python3 setup.py develop --user
# or whatever version you are using :
python3.x setup.py develop --user
```

## Usage

See the [script](https://github.com/masfaraud/design3d/tree/master/scripts) folder for examples

## Documentation

Yet to be uploaded
Can be built from docs folder

## License

100% opensource on LGPL license. See LICENSE for more details.

## Team and contributors

Credits to the volmdlr project team.
