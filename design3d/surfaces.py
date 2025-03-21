"""design3d module for 3D Surfaces."""
import math
import traceback
import warnings
from collections import deque
from functools import cached_property, lru_cache
from itertools import chain
from typing import List, Union

import numpy as np
from numpy.typing import NDArray
import matplotlib.pyplot as plt
import triangle as triangle_lib

from geomdl import NURBS, BSpline
from scipy.linalg import lu_factor, lu_solve
from scipy.optimize import least_squares, minimize

import design3d.nurbs.helpers as nurbs_helpers
from design3d.nurbs.helpers import generate_knot_vector
import design3d.core
import design3d.geometry
import design3d.utils.common_operations as d3d_common_operations
import design3d.utils.intersections as d3d_utils_intersections
import design3d.utils.parametric as d3d_parametric
from design3d import display, edges, grid, wires, curves
from design3d.core import EdgeStyle
from design3d.nurbs.core import evaluate_surface, derivatives_surface, point_inversion
from design3d.nurbs.fitting import approximate_surface, interpolate_surface
from design3d.nurbs.operations import (split_surface_u, split_surface_v, decompose_surface,
                                      extract_surface_curve_u, extract_surface_curve_v)
from design3d.utils.parametric import (array_range_search, repair_start_end_angle_periodicity, angle_discontinuity,
                                      find_parametric_point_at_singularity, is_isocurve,
                                      verify_repeated_parametric_points, repair_undefined_brep)


def knots_vector_inv(knots_vector):
    """
    Compute knot-elements and multiplicities based on the global knot vector.

    """

    knots = sorted(set(knots_vector))
    multiplicities = [knots_vector.count(knot) for knot in knots]

    return knots, multiplicities


class Surface2D:
    """
    A surface bounded by an outer contour.

    """

    def __init__(self, outer_contour: wires.Contour2D,
                 inner_contours: List[wires.Contour2D],
                 name: str = 'name'):
        self.outer_contour = outer_contour
        self.inner_contours = inner_contours
        self._area = None

        self.name=name

    def __hash__(self):
        """
        Calculate the hash value for Surface2D.

        This method is used to generate a hash value for instances of the
        current class, which can be used for hash-based data structures like
        dictionaries and sets.

        The hash value is computed based on the combined hash of the outer
        contour and a tuple of hash values for the inner contours. This
        ensures that objects with equivalent contours will have the same
        hash value, allowing them to be efficiently compared and retrieved
        from hash-based collections.

        :return: A hash value representing the object's state.
        :rtype: int
        """
        return hash((self.outer_contour, tuple(self.inner_contours)))

    def _data_hash(self):
        return hash(self)

    def __eq__(self, other):
        return self.outer_contour == other.outer_contour and self.inner_contours == other.inner_contours

    def copy(self, deep=True, memo=None):
        """
        Copies the surface2d.

        """
        return self.__class__(outer_contour=self.outer_contour.copy(deep=deep, memo=memo),
                              inner_contours=[c.copy(deep, memo) for c in self.inner_contours],
                              name='copy_' + self.name)

    def area(self):
        """
        Computes the area of the surface.

        """
        if not self._area:
            self._area = self.outer_contour.area() - sum(contour.area() for contour in self.inner_contours)
        return self._area

    def second_moment_area(self, point: design3d.Point2D):
        """
        Computes the second moment area of the surface.

        """
        i_x, i_y, i_xy = self.outer_contour.second_moment_area(point)
        for contour in self.inner_contours:
            i_xc, i_yc, i_xyc = contour.second_moment_area(point)
            i_x -= i_xc
            i_y -= i_yc
            i_xy -= i_xyc
        return i_x, i_y, i_xy

    def center_of_mass(self):
        """
        Compute the center of mass of the 2D surface.

        :return: The center of mass of the surface.
        :rtype: :class:`design3d.Point2D`
        """
        center = self.outer_contour.area() * self.outer_contour.center_of_mass()
        for contour in self.inner_contours:
            center -= contour.area() * contour.center_of_mass()
        return center / self.area()

    def point_belongs(self, point2d: design3d.Point2D, include_edge_points: bool = True):
        """
        Check whether a point belongs to the 2D surface.

        :param point2d: The point to check.
        :type point2d: :class:`design3d.Point2D`
        :return: True if the point belongs to the surface, False otherwise.
        :rtype: bool
        """
        if not self.outer_contour.point_inside(point2d, include_edge_points=include_edge_points):
            return False

        for inner_contour in self.inner_contours:
            if inner_contour.point_inside(point2d, include_edge_points=False):
                return False
        return True

    def random_point_inside(self):
        """
        Generate a random point inside the 2D surface.

        Taking into account any inner contours (holes) it may have.

        :return: A random point inside the surface.
        :rtype: :class:`design3d.Point2D`
        """
        point_inside_outer_contour = None
        center_of_mass = self.center_of_mass()
        if self.point_belongs(center_of_mass, False):
            point_inside_outer_contour = center_of_mass
        if not point_inside_outer_contour:
            point_inside_outer_contour = self.outer_contour.random_point_inside()
        while True:
            inside_inner_contour = False
            for inner_contour in self.inner_contours:
                if inner_contour.point_inside(point_inside_outer_contour):
                    inside_inner_contour = True
            if not inside_inner_contour and \
                    point_inside_outer_contour is not None:
                break
            point_inside_outer_contour = self.outer_contour.random_point_inside()

        return point_inside_outer_contour

    @staticmethod
    def triangulation_without_holes(vertices, segments, points_grid, tri_opt):
        """
        Triangulates a surface without holes.

        :param vertices: vertices of the surface.
        :param segments: segments defined as tuples of vertices.
        :param points_grid: to do.
        :param tri_opt: triangulation option: "p"
        :return:
        """
        vertices_grid = [(p.x, p.y) for p in points_grid]
        vertices.extend(vertices_grid)
        tri = {'vertices': np.array(vertices).reshape((-1, 2)),
               'segments': np.array(segments).reshape((-1, 2)),
               }
        triagulation = triangle_lib.triangulate(tri, tri_opt)
        return display.Mesh2D(vertices=triagulation['vertices'], triangles=triagulation['triangles'])

    def triangulation(self, number_points_x: int = 15, number_points_y: int = 15):
        """
        Triangulates the Surface2D using the Triangle library.

        :param number_points_x: Number of discretization points in x direction.
        :type number_points_x: int
        :param number_points_y: Number of discretization points in y direction.
        :type number_points_y: int
        :return: The triangulated surface as a display mesh.
        :rtype: :class:`design3d.display.Mesh2D`
        """
        area = self.bounding_rectangle().area()
        tri_opt = "p"
        if math.isclose(area, 0., abs_tol=1e-12):
            return None

        triangulates_with_grid = number_points_x > 0 and number_points_y > 0
        discretize_line = number_points_x > 0 or number_points_y > 0
        if not triangulates_with_grid:
            tri_opt = "p"

        discretize_line_direction = "xy"
        if number_points_y == 0 or number_points_x > 25 * number_points_y:
            discretize_line_direction = "x"
        elif number_points_y > 20 * number_points_x:
            discretize_line_direction = "y"
        outer_polygon = self.outer_contour.to_polygon(angle_resolution=15, discretize_line=discretize_line,
                                                      discretize_line_direction=discretize_line_direction)

        if not self.inner_contours and not triangulates_with_grid:
            return outer_polygon.triangulation()

        points_grid, x, y, grid_point_index = outer_polygon.grid_triangulation_points(number_points_x=number_points_x,
                                                                                      number_points_y=number_points_y)
        points = outer_polygon.points.copy()
        points_set = set(points)
        if len(points_set) < len(points):
            return None
        vertices = [(point.x, point.y) for point in points]
        n = len(points)
        segments = [(i, i + 1) for i in range(n - 1)]
        segments.append((n - 1, 0))

        if not self.inner_contours:  # No holes
            return self.triangulation_without_holes(vertices, segments, points_grid, tri_opt)

        point_index = {p: i for i, p in enumerate(points)}
        holes = []
        for inner_contour in self.inner_contours:
            inner_polygon = inner_contour.to_polygon(angle_resolution=10, discretize_line=discretize_line,
                                                     discretize_line_direction=discretize_line_direction)
            inner_polygon_nodes = inner_polygon.points.copy()
            for point in inner_polygon_nodes:
                if point not in point_index:
                    points.append(point)
                    vertices.append((point.x, point.y))
                    point_index[point] = n
                    n += 1

            for point1, point2 in zip(inner_polygon_nodes[:-1],
                                      inner_polygon_nodes[1:]):
                segments.append((point_index[point1], point_index[point2]))
            segments.append((point_index[inner_polygon_nodes[-1]], point_index[inner_polygon_nodes[0]]))
            rpi = inner_polygon.barycenter()
            if not inner_polygon.point_inside(rpi, include_edge_points=False):
                rpi = inner_polygon.random_point_inside(include_edge_points=False)
            holes.append([rpi.x, rpi.y])

            if triangulates_with_grid:
                # removes with a region search the grid points that are in the inner contour
                xmin, xmax, ymin, ymax = inner_polygon.bounding_rectangle.bounds()
                x_grid_range = array_range_search(x, xmin, xmax)
                y_grid_range = array_range_search(y, ymin, ymax)
                for i in x_grid_range:
                    for j in y_grid_range:
                        point = grid_point_index.get((i, j))
                        if not point:
                            continue
                        if inner_polygon.point_inside(point):
                            points_grid.remove(point)
                            grid_point_index.pop((i, j))

        if triangulates_with_grid:
            vertices_grid = [(p.x, p.y) for p in points_grid]
            vertices.extend(vertices_grid)

        tri = {'vertices': np.array(vertices).reshape((-1, 2)),
               'segments': np.array(segments).reshape((-1, 2)),
               'holes': np.array(holes).reshape((-1, 2))
               }
        triangulation = triangle_lib.triangulate(tri, tri_opt)
        return display.Mesh2D(vertices=triangulation['vertices'], triangles=triangulation['triangles'])

    def split_by_lines(self, lines):
        """
        Returns a list of cut surfaces given by the lines provided as argument.
        """
        cutted_surfaces = []
        iteration_surfaces = self.cut_by_line(lines[0])

        for line in lines[1:]:
            iteration_surfaces2 = []
            for surface in iteration_surfaces:
                line_cutted_surfaces = surface.cut_by_line(line)

                llcs = len(line_cutted_surfaces)

                if llcs == 1:
                    cutted_surfaces.append(line_cutted_surfaces[0])
                else:
                    iteration_surfaces2.extend(line_cutted_surfaces)

            iteration_surfaces = iteration_surfaces2[:]

        cutted_surfaces.extend(iteration_surfaces)
        return cutted_surfaces

    def split_regularly(self, n):
        """
        Split in n slices.
        """
        bounding_rectangle = self.outer_contour.bounding_rectangle
        lines = []
        for i in range(n - 1):
            xi = bounding_rectangle[0] + (i + 1) * (bounding_rectangle[1] - bounding_rectangle[0]) / n
            lines.append(curves.Line2D(design3d.Point2D(xi, 0),
                                       design3d.Point2D(xi, 1)))
        return self.split_by_lines(lines)

    def cut_by_line(self, line: curves.Line2D):
        """
        Returns a list of cut Surface2D by the given line.

        :param line: The line to cut the Surface2D with.
        :type line: :class:`curves.Line2D`
        :return: A list of 2D surfaces resulting from the cut.
        :rtype: List[:class:`design3d.faces.Surface2D`]
        """
        surfaces = []
        splitted_outer_contours = self.outer_contour.cut_by_line(line)
        splitted_inner_contours_table = []
        for inner_contour in self.inner_contours:
            splitted_inner_contours = inner_contour.cut_by_line(line)
            splitted_inner_contours_table.append(splitted_inner_contours)

        # First part of the external contour
        for outer_split in splitted_outer_contours:
            inner_contours = []
            for splitted_inner_contours in splitted_inner_contours_table:
                for inner_split in splitted_inner_contours:
                    inner_split.order_contour()
                    point = inner_split.random_point_inside()
                    if outer_split.point_inside(point):
                        inner_contours.append(inner_split)

            if inner_contours:
                surface2d = self.from_contours(outer_split, inner_contours)
                surfaces.append(surface2d)
            else:
                surfaces.append(Surface2D(outer_split, []))
        return surfaces

    def line_crossings(self, line: curves.Line2D):
        """
        Find intersection points between a line and the 2D surface.

        :param line: The line to intersect with the shape.
        :type line: :class:`curves.Line2D`
        :return: A list of intersection points sorted by increasing abscissa
            along the line. Each intersection point is a tuple
            (point, primitive) where point is the intersection point and
            primitive is the intersected primitive.
        :rtype: List[Tuple[:class:`design3d.Point2D`,
            :class:`design3d.core.Primitive2D`]]

        """
        intersection_points = []
        for primitive in self.outer_contour.primitives:
            for point in primitive.line_crossings(line):
                if (point, primitive) not in intersection_points:
                    intersection_points.append((point, primitive))
        for inner_contour in self.inner_contours:
            for primitive in inner_contour.primitives:
                for point in primitive.line_crossings(line):
                    if (point, primitive) not in intersection_points:
                        intersection_points.append((point, primitive))
        return sorted(intersection_points, key=lambda ip: line.abscissa(ip[0]))

    def split_at_centers(self):
        """
        Split in n slices.

        # TODO: is this used ?
        """

        cutted_contours = []
        center_of_mass1 = self.inner_contours[0].center_of_mass()
        center_of_mass2 = self.inner_contours[1].center_of_mass()
        cut_line = curves.Line2D(center_of_mass1, center_of_mass2)

        iteration_contours2 = []

        surface_cut = self.cut_by_line(cut_line)

        iteration_contours2.extend(surface_cut)

        iteration_contours = iteration_contours2[:]
        cutted_contours.extend(iteration_contours)

        return cutted_contours

    def bounding_rectangle(self):
        """
        Returns bounding rectangle.

        :return: Returns a python object with useful methods
        :rtype: :class:`design3d.core.BoundingRectangle
        """

        return self.outer_contour.bounding_rectangle

    @classmethod
    def from_contours(cls, outer_contour, inner_contours):
        """
        Create a Surface2D object from an outer contour and a list of inner contours.

        :param outer_contour: The outer contour that bounds the surface.
        :type outer_contour: wires.Contour2D
        :param inner_contours: The list of inner contours that define the holes of the surface.
        :type inner_contours : List[wires.Contour2D]
        :return: Surface2D defined by the given contours.
        """
        surface2d_inner_contours = []
        surface2d_outer_contour = outer_contour
        for inner_contour in inner_contours:
            if surface2d_outer_contour.shared_primitives_extremities(
                    inner_contour):
                # inner_contour will be merged with outer_contour
                merged_contours = surface2d_outer_contour.merge_with(
                    inner_contour)
                if len(merged_contours) >= 2:
                    raise NotImplementedError
                surface2d_outer_contour = merged_contours[0]
            else:
                # inner_contour will be added to the inner contours of the
                # Surface2D
                surface2d_inner_contours.append(inner_contour)
        return cls(surface2d_outer_contour, surface2d_inner_contours)

    def plot(self, ax=None, edge_style: EdgeStyle = EdgeStyle(color='grey', alpha=0.5, equal_aspect=False), **kwargs):
        """Plot surface 2d using Matplotlib."""

        if ax is None:
            _, ax = plt.subplots()
        self.outer_contour.plot(ax=ax, edge_style=edge_style)
        for inner_contour in self.inner_contours:
            inner_contour.plot(ax=ax, edge_style=edge_style)

        if edge_style.equal_aspect:
            ax.set_aspect('equal')

        ax.margins(0.1)
        return ax

    def axial_symmetry(self, line):
        """
        Finds out the symmetric 2D surface according to a line.

        """

        outer_contour = self.outer_contour.axial_symmetry(line)
        inner_contours = []
        if self.inner_contours:
            inner_contours = [contour.axial_symmetry(line) for contour in self.inner_contours]

        return self.__class__(outer_contour=outer_contour,
                              inner_contours=inner_contours)

    def rotation(self, center, angle):
        """
        Surface2D rotation.

        :param center: rotation center.
        :param angle: angle rotation.
        :return: a new rotated Surface2D.
        """

        outer_contour = self.outer_contour.rotation(center, angle)
        if self.inner_contours:
            inner_contours = [contour.rotation(center, angle) for contour in self.inner_contours]
        else:
            inner_contours = []

        return self.__class__(outer_contour, inner_contours)

    def translation(self, offset: design3d.Vector2D):
        """
        Surface2D translation.

        :param offset: translation vector.
        :return: A new translated Surface2D.
        """
        outer_contour = self.outer_contour.translation(offset)
        inner_contours = [contour.translation(offset) for contour in self.inner_contours]
        return self.__class__(outer_contour, inner_contours)

    def frame_mapping(self, frame: design3d.Frame2D, side: str):
        """Frame mapping of a surface 2d."""
        outer_contour = self.outer_contour.frame_mapping(frame, side)
        inner_contours = [contour.frame_mapping(frame, side) for contour in self.inner_contours]
        return self.__class__(outer_contour, inner_contours)

    def geo_lines(self):  # , mesh_size_list=None):
        """
        Gets the lines that define a Surface2D in a .geo file.
        """

        i, i_p = None, None
        lines, line_surface, lines_tags = [], [], []
        point_account, line_account, line_loop_account = 0, 0, 1
        for outer_contour, contour in enumerate(list(chain(*[[self.outer_contour], self.inner_contours]))):
            if isinstance(contour, curves.Circle2D):
                points = [design3d.Point2D(contour.center.x - contour.radius, contour.center.y),
                          contour.center,
                          design3d.Point2D(contour.center.x + contour.radius, contour.center.y)]
                index = []
                for i, point in enumerate(points):
                    lines.append(point.get_geo_lines(tag=point_account + i + 1,
                                                     point_mesh_size=None))
                    index.append(point_account + i + 1)

                lines.append('Circle(' + str(line_account + 1) +
                             ') = {' + str(index[0]) + ', ' + str(index[1]) + ', ' + str(index[2]) + '};')
                lines.append('Circle(' + str(line_account + 2) +
                             ') = {' + str(index[2]) + ', ' + str(index[1]) + ', ' + str(index[0]) + '};')

                lines_tags.append(line_account + 1)
                lines_tags.append(line_account + 2)

                lines.append('Line Loop(' + str(outer_contour + 1) + ') = {' + str(lines_tags)[1:-1] + '};')
                line_surface.append(line_loop_account)

                point_account = point_account + 2 + 1
                line_account, line_loop_account = line_account + 1 + 1, line_loop_account + 1
                lines_tags = []

            elif isinstance(contour, (wires.Contour2D, wires.ClosedPolygon2D)):
                if not isinstance(contour, wires.ClosedPolygon2D):
                    contour = contour.to_polygon(1)
                for i, point in enumerate(contour.points):
                    lines.append(point.get_geo_lines(tag=point_account + i + 1,
                                                     point_mesh_size=None))

                for i_p, primitive in enumerate(contour.primitives):
                    if i_p != len(contour.primitives) - 1:
                        lines.append(primitive.get_geo_lines(tag=line_account + i_p + 1,
                                                             start_point_tag=point_account + i_p + 1,
                                                             end_point_tag=point_account + i_p + 2))
                    else:
                        lines.append(primitive.get_geo_lines(tag=line_account + i_p + 1,
                                                             start_point_tag=point_account + i_p + 1,
                                                             end_point_tag=point_account + 1))
                    lines_tags.append(line_account + i_p + 1)

                lines.append('Line Loop(' + str(outer_contour + 1) + ') = {' + str(lines_tags)[1:-1] + '};')
                line_surface.append(line_loop_account)
                point_account = point_account + i + 1
                line_account, line_loop_account = line_account + i_p + 1, line_loop_account + 1
                lines_tags = []

        lines.append('Plane Surface(' + str(1) + ') = {' + str(line_surface)[1:-1] + '};')

        return lines

    def mesh_lines(self,
                   factor: float,
                   curvature_mesh_size: int = None,
                   min_points: int = None,
                   initial_mesh_size: float = 5):
        """
        Gets the lines that define mesh parameters for a Surface2D, to be added to a .geo file.

        :param factor: A float, between 0 and 1, that describes the mesh quality
        (1 for coarse mesh - 0 for fine mesh)
        :type factor: float
        :param curvature_mesh_size: Activate the calculation of mesh element sizes based on curvature
        (with curvature_mesh_size elements per 2*Pi radians), defaults to 0
        :type curvature_mesh_size: int, optional
        :param min_points: Check if there are enough points on small edges (if it is not, we force to have min_points
        on that edge), defaults to None
        :type min_points: int, optional
        :param initial_mesh_size: If factor=1, it will be initial_mesh_size elements per dimension, defaults to 5
        :type initial_mesh_size: float, optional

        :return: A list of lines that describe mesh parameters
        :rtype: List[str]
        """

        lines = []
        if factor == 0:
            factor = 1e-3

        size = (math.sqrt(self.area()) / initial_mesh_size) * factor

        if min_points:
            lines.extend(self.get_mesh_lines_with_transfinite_curves(
                [[self.outer_contour], self.inner_contours], min_points, size))

        lines.append('Field[1] = MathEval;')
        lines.append('Field[1].F = "' + str(size) + '";')
        lines.append('Background Field = 1;')
        if curvature_mesh_size:
            lines.append('Mesh.MeshSizeFromCurvature = ' + str(curvature_mesh_size) + ';')

        return lines

    @staticmethod
    def get_mesh_lines_with_transfinite_curves(lists_contours, min_points, size):
        """Gets Surface 2d mesh lines with transfinite curves."""
        lines, primitives, primitives_length = [], [], []
        circle_class_ = getattr(wires, 'Circle' + lists_contours[0][0].__class__.__name__[-2:])
        for contour in list(chain(*lists_contours)):
            if isinstance(contour, circle_class_):
                primitives.append(contour)
                primitives.append(contour)
                primitives_length.append(contour.length() / 2)
                primitives_length.append(contour.length() / 2)
            else:
                for primitive in contour.primitives:
                    if (primitive not in primitives) and (primitive.reverse() not in primitives):
                        primitives.append(primitive)
                        primitives_length.append(primitive.length())

        for i, length in enumerate(primitives_length):
            if length < min_points * size:
                lines.append('Transfinite Curve {' + str(i) + '} = ' +
                             str(min_points) + ' Using Progression 1;')
        return lines

    def to_geo(self, file_name: str,
               factor: float, **kwargs):
        # curvature_mesh_size: int = None,
        # min_points: int = None,
        # initial_mesh_size: float = 5):
        """
        Gets the .geo file for the Surface2D.
        """

        for element in [('curvature_mesh_size', 0), ('min_points', None), ('initial_mesh_size', 5)]:
            if element[0] not in kwargs:
                kwargs[element[0]] = element[1]

        lines = self.geo_lines()
        lines.extend(self.mesh_lines(factor, kwargs['curvature_mesh_size'],
                                     kwargs['min_points'], kwargs['initial_mesh_size']))

        with open(file_name + '.geo', 'w', encoding="utf-8") as file:
            for line in lines:
                file.write(line)
                file.write('\n')
        file.close()

    def to_msh(self, file_name: str, mesh_dimension: int, mesh_order: int,
               factor: float, **kwargs):
        # curvature_mesh_size: int = 0,
        # min_points: int = None,
        # initial_mesh_size: float = 5):
        """
        Gets .msh file for the Surface2D generated by gmsh.

        :param file_name: The msh. file name
        :type file_name: str
        :param mesh_dimension: The mesh dimension (1: 1D-Edge, 2: 2D-Triangle, 3D-Tetrahedra)
        :type mesh_dimension: int
        :param factor: A float, between 0 and 1, that describes the mesh quality
        (1 for coarse mesh - 0 for fine mesh)
        :type factor: float
        :param curvature_mesh_size: Activate the calculation of mesh element sizes based on curvature
        (with curvature_mesh_size elements per 2*Pi radians), defaults to 0
        :type curvature_mesh_size: int, optional
        :param min_points: Check if there are enough points on small edges (if it is not, we force to have min_points
        on that edge), defaults to None
        :type min_points: int, optional
        :param initial_mesh_size: If factor=1, it will be initial_mesh_size elements per dimension, defaults to 5
        :type initial_mesh_size: float, optional

        :return: A txt file
        :rtype: .txt
        """

        for element in [('curvature_mesh_size', 0), ('min_points', None), ('initial_mesh_size', 5)]:
            if element[0] not in kwargs:
                kwargs[element[0]] = element[1]

        self.to_geo(file_name=file_name, mesh_dimension=mesh_dimension,
                    factor=factor, curvature_mesh_size=kwargs['curvature_mesh_size'],
                    min_points=kwargs['min_points'], initial_mesh_size=kwargs['initial_mesh_size'])

        design3d.core.VolumeModel.generate_msh_file(file_name, mesh_dimension, mesh_order)

class Surface3D:
    """
    Abstract class.

    """
    x_periodicity = None
    y_periodicity = None
    face_class = None

    def __init__(self, frame: design3d.Frame3D = None, name: str = ''):
        self.frame = frame
        self.name=name

    @property
    def u_domain(self):
        """The parametric domain of the surface in the U direction."""
        return -math.inf, math.inf

    @property
    def v_domain(self):
        """The parametric domain of the surface in the V direction."""
        return -math.inf, math.inf

    @property
    def domain(self):
        """Returns u and v bounds."""
        umin, umax = self.u_domain
        d3din, d3dax = self.v_domain
        return umin, umax, d3din, d3dax

    def plot(self, ax=None, edge_style: EdgeStyle = EdgeStyle(color='grey', alpha=0.5), **kwargs):
        """
        Abstract method.
        """
        raise NotImplementedError(f"plot method is not implemented for {self.__class__.__name__}")

    def point2d_to_3d(self, point2d):
        """
        Abstract method.
        """
        raise NotImplementedError(f'point2d_to_3d is abstract and should be implemented in {self.__class__.__name__}')

    def point3d_to_2d(self, point3d):
        """
        Abstract method. Convert a 3D point to a 2D parametric point.

        :param point3d: The 3D point to convert, represented by 3 coordinates (x, y, z).
        :type point3d: `design3d.Point3D`
        :return: NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError(f'point3d_to_2d is abstract and should be implemented in {self.__class__.__name__}')

    def face_from_contours3d(self, contours3d: List[wires.Contour3D], name: str = ''):
        """Deprecated method, 'Use Face3D from_contours3d method'."""
        raise AttributeError('Use Face3D from_contours3d method')

    def repair_primitives_periodicity(self, primitives2d, primitives_mapping):
        """
        Repairs the continuity of the 2D contour while using contour3d_to_2d on periodic surfaces.

        :param primitives2d: The primitives in parametric surface domain.
        :type primitives2d: list
        :param primitives_mapping: It is a dictionary that stores the correspondence between primitives
         in the parametric domain with their equivalent primitive in 3D space.
        :type primitives_mapping: dict
        :return: A list of primitives.
        :rtype: list
        """
        # pylint: disable= too-many-locals
        tol = 1e-2
        if self.__class__.__name__ == "ExtrusionSurface3D":
            tol = 5e-6
        x_periodicity = self.x_periodicity if self.x_periodicity else -1
        y_periodicity = self.y_periodicity if self.y_periodicity else -1

        if x_periodicity or y_periodicity:
            if self.is_undefined_brep(primitives2d[0]):
                old_primitive = primitives2d[0]
                primitives2d[0] = self.fix_undefined_brep_with_neighbors(primitives2d[0], primitives2d[-1],
                                                                         primitives2d[1])
                primitives_mapping[primitives2d[0]] = primitives_mapping.pop(old_primitive)
        self._helper_repair_primitives_periodicity(primitives2d, primitives_mapping,
                                                   [x_periodicity, y_periodicity], tol)
        if self.__class__.__name__ in ("SphericalSurface3D", "ConicalSurface3D", "RevolutionSurface3D"):
            delta = primitives2d[-1].end - primitives2d[0].start
            if (math.isclose(abs(delta.x), x_periodicity, abs_tol=tol) or
                    math.isclose(abs(delta.y), y_periodicity, abs_tol=tol)):
                last_end_3d = self.point2d_to_3d(primitives2d[-1].end)
                first_start_3d = self.point2d_to_3d(primitives2d[0].start)
                if last_end_3d.is_close(first_start_3d, 1e-6) and not self.is_singularity_point(last_end_3d):
                    old_primitive = primitives2d[0]
                    primitives2d[0] = primitives2d[0].translation(delta)
                    primitives_mapping[primitives2d[0]] = primitives_mapping.pop(old_primitive)
                    self._helper_repair_primitives_periodicity(primitives2d, primitives_mapping,
                                                               [x_periodicity, y_periodicity], tol)
        self.check_parametric_contour_end(primitives2d, tol)

    def _helper_repair_primitives_periodicity(self, primitives2d, primitives_mapping, periodicities, tol):
        """Helper function to repair_primitives_periodicity."""
        x_periodicity, y_periodicity = periodicities
        i = 1
        while i < len(primitives2d):
            delta = primitives2d[i - 1].end - primitives2d[i].start
            distance = delta.norm()

            if not math.isclose(distance, 0, abs_tol=tol):
                if math.isclose(primitives2d[i].length(), x_periodicity, abs_tol=tol) or \
                        math.isclose(primitives2d[i].length(), y_periodicity, abs_tol=tol):
                    delta_end = primitives2d[i - 1].end - primitives2d[i].end
                    delta_min_index, _ = min(enumerate([distance, delta_end.norm()]), key=lambda x: x[1])
                    if self.is_undefined_brep(primitives2d[i]):
                        repair_undefined_brep(self, primitives2d, primitives_mapping, i, primitives2d[i - 1])
                    elif self.is_singularity_point(self.point2d_to_3d(primitives2d[i - 1].end)) and \
                            self.is_singularity_point(self.point2d_to_3d(primitives2d[i].start)):
                        self.repair_singularity(primitives2d, i, primitives2d[i - 1])
                    elif primitives2d[i].end.is_close(primitives2d[i - 1].end, tol=tol):
                        self.repair_reverse(primitives2d, primitives_mapping, i)
                    elif delta_min_index == 0:
                        self.repair_translation(primitives2d, primitives_mapping, i, delta)
                    else:
                        old_primitive = primitives2d[i]
                        new_primitive = primitives2d[i].reverse()
                        primitives2d[i] = new_primitive.translation(delta_end)
                        primitives_mapping[primitives2d[i]] = primitives_mapping.pop(old_primitive)

                elif primitives2d[i].end.is_close(primitives2d[i - 1].end, tol=tol):
                    self.repair_reverse(primitives2d, primitives_mapping, i)
                elif self.is_undefined_brep(primitives2d[i]):
                    repair_undefined_brep(self, primitives2d, primitives_mapping, i, primitives2d[i - 1])
                elif self.is_singularity_point(self.point2d_to_3d(primitives2d[i - 1].end), tol=1e-5) and \
                        self.is_singularity_point(self.point2d_to_3d(primitives2d[i].start), tol=1e-5):
                    self.repair_singularity(primitives2d, i, primitives2d[i - 1])
                else:
                    self.repair_translation(primitives2d, primitives_mapping, i, delta)
            i += 1

    def check_parametric_contour_end(self, primitives2d, tol):
        """Helper function to repair_primitives_periodicity."""
        previous_primitive = primitives2d[-1]
        delta = previous_primitive.end - primitives2d[0].start
        distance = delta.norm()
        is_connected = math.isclose(distance, 0, abs_tol=tol)
        if not is_connected and self.is_singularity_point(self.point2d_to_3d(previous_primitive.end)) and \
                self.is_singularity_point(self.point2d_to_3d(primitives2d[0].start)):
            primitives2d.append(edges.LineSegment2D(previous_primitive.end, primitives2d[0].start,
                                                    name="construction"))

    @staticmethod
    def repair_singularity(primitives2d, i, previous_primitive):
        """Helper function to repair_primitives_periodicity."""
        primitives2d.insert(i, edges.LineSegment2D(previous_primitive.end, primitives2d[i].start,
                                                   name="construction"))
        if i < len(primitives2d):
            i += 1

    @staticmethod
    def repair_reverse(primitives2d, primitives_mapping, i):
        """Helper function to repair_primitives_periodicity."""
        old_primitive = primitives2d[i]
        primitives2d[i] = primitives2d[i].reverse()
        primitives_mapping[primitives2d[i]] = primitives_mapping.pop(old_primitive)

    @staticmethod
    def repair_translation(primitives2d, primitives_mapping, i, delta):
        """Helper function to repair_primitives_periodicity."""
        old_primitive = primitives2d[i]
        primitives2d[i] = primitives2d[i].translation(delta)
        primitives_mapping[primitives2d[i]] = primitives_mapping.pop(old_primitive)

    def connect_contours(self, outer_contour, inner_contours):
        """
        Abstract method. Repair 2D contours of a face on the parametric domain.

        :param outer_contour: Outer contour 2D.
        :type inner_contours: wires.Contour2D
        :param inner_contours: List of 2D contours.
        :type inner_contours: list
        :return: NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError(f'connect_contours is abstract and should be implemented in '
                                  f'{self.__class__.__name__}')

    @staticmethod
    def update_primitives_mapping(primitives_mapping, primitives, primitive3d):
        """
        Helper function to contour3d_to_2d.
        """
        for primitive in primitives:
            primitives_mapping[primitive] = primitive3d

    def parametric_points_to_3d(self, points: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Transform parametric coordinates to 3D points on the surface.

        Given a set of parametric coordinates `(u, v)` representing points on the surface,
        this method returns the corresponding 3D points on the surface.

        :param points: Parametric coordinates in the form of a numpy array with shape (n, 2),
                       where `n` is the number of points, and each row corresponds to `(u, v)`.
        :type points: numpy.ndarray[np.float64]

        :return: Array of 3D points representing the surface in Cartesian coordinates.
        :rtype: numpy.ndarray[np.float64]
        """
        points3d = [self.point2d_to_3d(design3d.Point2D(*point)) for point in points]

        return np.array(points3d)

    def primitives3d_to_2d(self, primitives3d):
        """
        Helper function to perform conversion of 3D primitives into B-Rep primitives.

        :param primitives3d: List of 3D primitives from a 3D contour.
        :type primitives3d: List[edges.Edge]
        :return: A list of 2D primitives on parametric domain.
        :rtype: List[edges.Edge]
        """
        primitives2d = []
        primitives_mapping = {}
        for primitive3d in primitives3d:
            method_name = f'{primitive3d.__class__.__name__.lower()}_to_2d'
            if hasattr(self, method_name):
                primitives = getattr(self, method_name)(primitive3d)
                if primitives is None:
                    continue
                self.update_primitives_mapping(primitives_mapping, primitives, primitive3d)
                primitives2d.extend(primitives)
            else:
                raise AttributeError(f'Class {self.__class__.__name__} does not implement {method_name}')
        return primitives2d, primitives_mapping

    def contour3d_to_2d(self, contour3d, return_primitives_mapping: bool = False):
        """
        Transforms a Contour3D into a Contour2D in the parametric domain of the surface.

        :param contour3d: The contour to be transformed.
        :type contour3d: :class:`wires.Contour3D`
        :param return_primitives_mapping: If True, returns a dictionary containing the correspondence between 2D and 3D
         primitives
        :type return_primitives_mapping: bool
        :return: A 2D contour object.
        :rtype: :class:`wires.Contour2D`
        """
        primitives2d, primitives_mapping = self.primitives3d_to_2d(contour3d.primitives)

        wire2d = wires.Wire2D(primitives2d)
        is_wire = False
        if self.x_periodicity and not self.is_singularity_point(self.point2d_to_3d(wire2d.primitives[0].start)) and \
                not self.is_singularity_point(self.point2d_to_3d(wire2d.primitives[-1].end)):
            delta_x = abs(wire2d.primitives[0].start.x - wire2d.primitives[-1].end.x)
            if math.isclose(delta_x, self.x_periodicity, rel_tol=0.01) and wire2d.is_ordered(1e-3):
                is_wire = True
        if self.y_periodicity and not self.is_singularity_point(self.point2d_to_3d(wire2d.primitives[0].start)) and \
                not self.is_singularity_point(self.point2d_to_3d(wire2d.primitives[-1].end)):
            delta_y = abs(wire2d.primitives[0].start.y - wire2d.primitives[-1].end.y)
            if math.isclose(delta_y, self.y_periodicity, rel_tol=0.01) and wire2d.is_ordered(1e-3):
                is_wire = True
        # Fix contour
        if not is_wire and (self.x_periodicity or self.y_periodicity):
            self.repair_primitives_periodicity(primitives2d, primitives_mapping)
        if return_primitives_mapping:
            return wires.Contour2D(primitives2d), primitives_mapping
        return wires.Contour2D(primitives2d)

    def contour2d_to_3d(self, contour2d, return_primitives_mapping: bool = False):
        """
        Transforms a Contour2D in the parametric domain of the surface into a Contour3D in Cartesian coordinate.

        :param contour2d: The contour to be transformed.
        :type contour2d: :class:`wires.Contour2D`
        :param return_primitives_mapping: If True, returns a dictionary containing the correspondence between 2D and 3D
         primitives
        :type return_primitives_mapping: bool
        :return: A 3D contour object.
        :rtype: :class:`wires.Contour3D`
        """
        primitives3d = []
        primitives_mapping = {}
        for primitive2d in contour2d.primitives:
            if self.is_degenerated_brep(primitive2d):
                continue
            method_name = f'{primitive2d.__class__.__name__.lower()}_to_3d'
            if hasattr(self, method_name):
                try:
                    primitives = getattr(self, method_name)(primitive2d)
                    if primitives is None:
                        continue
                    primitives3d.extend(primitives)
                    primitives_mapping[primitive2d] = primitives[0]
                except AttributeError:
                    print(traceback.format_exc())
                    print(f'Class {self.__class__.__name__} does not implement {method_name}'
                          f'with {primitive2d.__class__.__name__}')
            else:
                raise AttributeError(
                    f'Class {self.__class__.__name__} does not implement {method_name}')
        if not primitives3d:
            raise ValueError("no primitives to create contour")
        if return_primitives_mapping:
            return wires.Contour3D(primitives3d), primitives_mapping
        return wires.Contour3D(primitives3d)

    def linesegment3d_to_2d(self, linesegment3d):
        """
        A line segment on a surface will be in any case a line in 2D?.

        """
        return [edges.LineSegment2D(self.point3d_to_2d(linesegment3d.start),
                                    self.point3d_to_2d(linesegment3d.end))]

    def bsplinecurve3d_to_2d(self, bspline_curve3d):
        """
        Is this right?.
        """
        n = bspline_curve3d.ctrlpts.shape[0]
        points = [self.point3d_to_2d(p)
                  for p in bspline_curve3d.discretization_points(number_points=n)]
        return [edges.BSplineCurve2D.from_points_interpolation(points, bspline_curve3d.degree)]

    def bsplinecurve2d_to_3d(self, bspline_curve2d):
        """
        Is this right?.

        """
        n = len(bspline_curve2d.control_points)
        points = [self.point2d_to_3d(p)
                  for p in bspline_curve2d.discretization_points(number_points=n)]
        return [edges.BSplineCurve3D.from_points_interpolation(points, bspline_curve2d.degree, centripetal=True)]

    def normal_from_point2d(self, point2d):
        """
        Evaluates the normal vector of the bspline surface at this 2D point.
        """
        raise NotImplementedError('NotImplemented')

    def normal_from_point3d(self, point3d):
        """
        Evaluates the normal vector of the bspline surface at this 3D point.
        """

        return (self.normal_from_point2d(self.point3d_to_2d(point3d)))[1]

    def geodesic_distance_from_points2d(self, point1_2d: design3d.Point2D,
                                        point2_2d: design3d.Point2D, number_points: int = 50):
        """
        Approximation of geodesic distance via line segments length sum in 3D.
        """
        # points = [point1_2d]
        current_point3d = self.point2d_to_3d(point1_2d)
        distance = 0.
        for i in range(number_points):
            next_point3d = self.point2d_to_3d(point1_2d + (i + 1) / number_points * (point2_2d - point1_2d))
            distance += next_point3d.point_distance(current_point3d)
            current_point3d = next_point3d
        return distance

    def geodesic_distance(self, point1_3d: design3d.Point3D, point2_3d: design3d.Point3D):
        """
        Approximation of geodesic distance between 2 3D points supposed to be on the surface.
        """
        point1_2d = self.point3d_to_2d(point1_3d)
        point2_2d = self.point3d_to_2d(point2_3d)
        return self.geodesic_distance_from_points2d(point1_2d, point2_2d)

    def point_projection(self, point3d):
        """
        Returns the projection of the point on the surface.

        :param point3d: Point to project.
        :type point3d: design3d.Point3D
        :return: A point on the surface
        :rtype: design3d.Point3D
        """
        return self.point2d_to_3d(self.point3d_to_2d(point3d))

    def point_distance(self, point3d: design3d.Point3D):
        """
        Calculates the minimal distance from a given point and the surface.

        :param point3d: point to verify distance.
        :type point3d: design3d.Point3D
        :return: point distance to the surface.
        :rtype: float
        """
        proj_point = self.point_projection(point3d)
        return proj_point.point_distance(point3d)

    def edge_intersections(self, edge):
        """
        Gets intersections between a Surface 3D, and an edge 3D.

        :param edge: any 3D edge.
        :return: list of points.
        """
        intersections = []
        method_name = f'{edge.__class__.__name__.lower()[:-2]}_intersections'
        if hasattr(self, method_name):
            intersections = getattr(self, method_name)(edge)
        return intersections

    def contour_intersections(self, contour3d: wires.Contour3D):
        """
        Gets intersections between a contour 3D and a Surface 3D.

        :param contour3d: other contour get intersections with.
        :return: list of intersecting points.
        """
        outer_contour_intersections_with_plane = []
        for primitive in contour3d.primitives:
            primitive_plane_intersections = self.edge_intersections(primitive)
            for primitive_plane_intersection in primitive_plane_intersections:
                if not primitive_plane_intersection.in_list(outer_contour_intersections_with_plane):
                    outer_contour_intersections_with_plane.append(primitive_plane_intersection)
        return outer_contour_intersections_with_plane

    def is_singularity_point(self, *args, **kwargs):
        """Verifies if point is on the surface singularity."""
        return False

    @staticmethod
    def is_undefined_brep(*args):
        """Verifies if the edge is contained within the periodicity boundary."""
        return False

    def surface_intersections(self, other_surface: 'Surface3D'):
        """
        Gets intersections between two surfaces.

        :param other_surface: other surface to get intersections with.
        :return: a list containing all intersections between the two surfaces 3d.
        """
        method_name = f'{other_surface.__class__.__name__.lower()[:-2]}_intersections'
        if hasattr(self, method_name):
            return getattr(self, method_name)(other_surface)
        method_name = f'{self.__class__.__name__.lower()[:-2]}_intersections'
        if hasattr(other_surface, method_name):
            return getattr(other_surface, method_name)(self)
        raise NotImplementedError(f'No method available for calculating intersections between {self.__class__} and '
                                  f'{other_surface.__class__}')

    def line_intersections(self, line: curves.Line3D):
        """Gets intersections between a line and a Surface 3D."""
        raise NotImplementedError(f'line_intersections method not implemented by {self.__class__.__name__}')

    def frame_mapping(self, frame, side: str):
        """Frame mapping for Surface 3D."""
        raise NotImplementedError(f'frame_mapping method not implemented by {self.__class__.__name__}')

    def linesegment_intersections(self, linesegment3d: edges.LineSegment3D, abs_tol: float = 1e-6):
        """
        Calculates the intersection points between a 3D line segment and a surface 3D.

        The method calculates the intersection points between a 3D line segment and a 3d Surface by first
        finding the intersection points between the infinite line containing the line segment and the Surface,
        and then filtering out the points that are not within the line segment. It returns a list of intersection
        points, which can be empty if there are no intersections. The intersection points are represented as
        3D points using the `design3d.Point3D` class.
        Note: The method assumes that the line segment and the Surface are in the same coordinate system.

        :param linesegment3d: The 3D line segment object to intersect with the Surface.
        :type linesegment3d: edges.LineSegment3D.
        :param abs_tol: tolerance.
        :type abs_tol: float.
        :return: A list of intersection points between the line segment and the Surface.
        The list may be empty if there are no intersections.
        :rtype: List[design3d.Point3D]:
        """
        line_intersections = self.line_intersections(linesegment3d.line)
        linesegment_intersections = [inters for inters in line_intersections
                                     if linesegment3d.point_belongs(inters, abs_tol)]
        return linesegment_intersections

    def plane_intersections(self, plane3d: 'Plane3D'):
        """Gets intersections between a line and a Surface 3D."""
        raise NotImplementedError(f'line_intersections method not implemented by {self.__class__.__name__}')

    def curve_intersections(self, curve):
        """
        Calculates the intersections between a conical surface and a curve 3D.

        :param curve: other circle to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        if not self.frame.origin.is_close(design3d.O3D) or not self.frame.w.is_close(design3d.Z3D):
            local_surface = self.frame_mapping(self.frame, 'new')
            local_curve = curve.frame_mapping(self.frame, 'new')
            local_intersections = local_surface.curve_intersections(local_curve)
            global_intersections = []
            for intersection in local_intersections:
                global_intersections.append(self.frame.local_to_global_coordinates(intersection))
            return global_intersections
        curve_plane = Plane3D(curve.frame)
        curve_plane_intersections = self.plane_intersections(curve_plane)
        if not curve_plane_intersections:
            return []
        intersections = []
        for curve_plane_intersection in curve_plane_intersections:
            inters = curve_plane_intersection.intersections(curve)
            for intersection in inters:

                if not intersection.in_list(intersections):
                    intersections.append(intersection)
        return intersections

    def circle_intersections(self, circle: curves.Circle3D):
        """
        Calculates the intersections between a surface 3d and a Circle 3D.

        :param circle: other circle to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        return self.curve_intersections(circle)

    def ellipse_intersections(self, ellipse: curves.Ellipse3D):
        """
        Calculates the intersections between a conical surface and an ellipse 3D.

        :param ellipse: other ellipse to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        return self.curve_intersections(ellipse)

    def hyperbola_intersections(self, hyperbola: curves.Hyperbola3D):
        """
        Calculates the intersections between a conical surface and a hyperbola 3D.

        :param hyperbola: other hyperbola to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        return self.curve_intersections(hyperbola)

    def parabola_intersections(self, parabola: curves.Parabola3D):
        """
        Calculates the intersections between a conical surface and a parabola 3D.

        :param parabola: other parabola to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        return self.curve_intersections(parabola)

    def fullarc_intersections(self, fullarc: edges.FullArc3D):
        """
        Calculates the intersections between a conical surface and a full arc 3D.

        :param fullarc: other fullarc to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        return self.curve_intersections(fullarc.circle)

    def arc_intersections(self, arc3d: edges.Arc3D):
        """
        Calculates the intersections between a conical surface and an arc 3D.

        :param arc3d: other arc to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        circle_intersections = self.curve_intersections(arc3d.circle)
        intersections = []
        for intersection in circle_intersections:
            if arc3d.point_belongs(intersection):
                intersections.append(intersection)
        return intersections

    def fullarcellipse_intersections(self, fullarcellipse: edges.FullArcEllipse3D):
        """
        Calculates the intersections between a conical surface and a fullarcellipse 3D.

        :param fullarcellipse: other fullarcellipse to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        return self.ellipse_intersections(fullarcellipse.ellipse)

    def arcellipse_intersections(self, arcellipse: edges.ArcEllipse3D):
        """
        Calculates the intersections between a conical surface and an arcellipse 3D.

        :param arcellipse: other arcellipse to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        ellipse_intersections = self.curve_intersections(arcellipse.ellipse)
        intersections = []
        for intersection in ellipse_intersections:
            if arcellipse.point_belongs(intersection):
                intersections.append(intersection)
        return intersections

    def brep_connectivity_check(self, brep: wires.Contour2D, tol: float = 1e-6) -> bool:
        """Checks the topology of 2D BREP in 3D space."""
        if len(brep.primitives) == 2 and brep.primitives[0].direction_independent_is_close(brep.primitives[1]):
            return False
        if self.x_periodicity:
            distance = brep.primitives[-1].end.point_distance(brep.primitives[0].start)
            if distance >= (0.99 * self.x_periodicity):
                return False
        if self.y_periodicity:
            distance = brep.primitives[-1].end.point_distance(brep.primitives[0].start)
            if distance >= (0.99 * self.y_periodicity):
                return False
        for prim1, prim2 in zip(brep.primitives, brep.primitives[1:] + [brep.primitives[0]]):
            end = self.point2d_to_3d(prim1.end)
            start = self.point2d_to_3d(prim2.start)
            if not end.is_close(start, tol):
                return False
        return True

    def is_degenerated_brep(self, *args):
        """
        An edge is said to be degenerated when it corresponds to a single 3D point.
        """
        return False

    def point_belongs(self, point3d, abs_tol: float = 1e-6):
        """
        Verifies if point is on Toroidal Surface 3D.

        :param point3d: other point.
        :param abs_tol: tolerance.
        :return: True or False.
        """
        if self.point_distance(point3d) < abs_tol:
            return True
        return False


class Plane3D(Surface3D):
    """
    Defines a plane 3d.

    :param frame: u and v of frame describe the plane, w is the normal
    """
    face_class = 'PlaneFace3D'

    def __init__(self, frame: design3d.Frame3D, name: str = ''):
        Surface3D.__init__(self, frame=frame, name=name)

    def __hash__(self):
        return hash(('plane 3d', self.frame))

    def __eq__(self, other_plane):
        if other_plane.__class__.__name__ != self.__class__.__name__:
            return False
        return self.frame == other_plane.frame

    @property
    def normal(self):
        """Gets the plane normal vector."""
        return self.frame.w

    @classmethod
    def from_step(cls, arguments, object_dict, **kwargs):
        """
        Converts a step primitive to a Plane3D.

        :param arguments: The arguments of the step primitive.
        :type arguments: list
        :param object_dict: The dictionary containing all the step primitives
            that have already been instantiated
        :type object_dict: dict
        :return: The corresponding Plane3D object.
        :rtype: :class:`design3d.faces.Plane3D`
        """
        frame = object_dict[arguments[1]]
        frame = frame.normalize()
        return cls(frame, arguments[0][1:-1])

    def to_step(self, current_id):
        """
        Converts the object to a STEP representation.

        :param current_id: The ID of the last written primitive.
        :type current_id: int
        :return: The STEP representation of the object and the last ID.
        :rtype: tuple[str, list[int]]
        """
        content, frame_id = self.frame.to_step(current_id)
        plane_id = frame_id + 1
        content += f"#{plane_id} = PLANE('{self.name}',#{frame_id});\n"
        return content, [plane_id]

    @classmethod
    def from_3_points(cls, *args, name: str = ''):
        """
        Point 1 is used as origin of the plane.
        """
        point1, point2, point3 = args
        vector1 = point2 - point1
        vector1 = vector1.to_vector()
        vector2 = point3 - point1
        vector2 = vector2.to_vector()
        vector1 = vector1.unit_vector()
        vector2 = vector2.unit_vector()
        normal = vector1.cross(vector2)
        normal = normal.unit_vector()
        frame = design3d.Frame3D(point1, vector1, normal.cross(vector1), normal)
        return cls(frame, name=name)

    @classmethod
    def from_normal(cls, point, normal, name: str = ''):
        """Creates a Plane 3D form a point and a normal vector."""
        v1 = normal.deterministic_unit_normal_vector()
        v2 = v1.cross(normal)
        return cls(design3d.Frame3D(point, v1, v2, normal), name=name)

    @classmethod
    def from_plane_vectors(cls, plane_origin: design3d.Point3D,
                           plane_x: design3d.Vector3D, plane_y: design3d.Vector3D, name: str = ''):
        """
        Initializes a 3D plane object with a given plane origin and plane x and y vectors.

        :param plane_origin: A design3d.Point3D representing the origin of the plane.
        :param plane_x: A design3d.Vector3D representing the x-axis of the plane.
        :param plane_y: A design3d.Vector3D representing the y-axis of the plane.
        :param name: object's name.
        :return: A Plane3D object initialized from the provided plane origin and plane x and y vectors.
        """
        normal = plane_x.cross(plane_y)
        return cls(design3d.Frame3D(plane_origin, plane_x, plane_y, normal), name=name)

    @classmethod
    def from_points(cls, points, name: str = ''):
        """
        Returns a 3D plane that goes through the 3 first points on the list.

        Why for more than 3 points we only do some check and never raise error?
        """
        if len(points) < 3:
            raise ValueError
        if len(points) == 3:
            return cls.from_3_points(points[0],
                                     points[1],
                                     points[2], name=name)
        points = [p.copy() for p in points]
        indexes_to_del = []
        for i, point in enumerate(points[1:]):
            if point.is_close(points[0]):
                indexes_to_del.append(i)
        for index in indexes_to_del[::-1]:
            del points[index + 1]

        origin = points[0]
        vector1 = points[1] - origin
        vector1 = vector1.unit_vector()
        vector2_min = points[2] - origin
        vector2_min = vector2_min.unit_vector()
        dot_min = abs(vector1.dot(vector2_min))
        for point in points[3:]:
            vector2 = point - origin
            vector2 = vector2.unit_vector()
            dot = abs(vector1.dot(vector2))
            if dot < dot_min:
                vector2_min = vector2
                dot_min = dot
        return cls.from_3_points(origin, vector1 + origin, vector2_min + origin, name=name)

    def angle_between_planes(self, plane2):
        """
        Get angle between 2 planes.

        :param plane2: the second plane.
        :return: the angle between the two planes.
        """
        angle = math.acos(self.frame.w.dot(plane2.frame.w))
        return angle

    def point_belongs(self, point3d, abs_tol: float = 1e-6):
        """
        Return if the point belongs to the plane at a tolerance of 1e-6.

        """
        if math.isclose(self.frame.w.dot(point3d - self.frame.origin), 0,
                        abs_tol=abs_tol):
            return True
        return False

    def point_distance(self, point3d):
        """
        Calculates the distance of a point to plane.

        :param point3d: point to verify distance.
        :return: a float, point distance to plane.
        """
        return d3d_common_operations.get_plane_point_distance(self.frame, point3d)

    def line_intersections(self, line):
        """
        Find the intersection with a line.

        :param line: Line to evaluate the intersection
        :type line: :class:`edges.Line`
        :return: ADD DESCRIPTION
        :rtype: List[design3d.Point3D]
        """
        return d3d_utils_intersections.get_plane_line_intersections(self.frame, line)

    def linesegment_intersections(self, linesegment3d: edges.LineSegment3D, abs_tol: float = 1e-6) \
            -> List[design3d.Point3D]:
        """
        Gets the intersections of a plane a line segment 3d.

        :param linesegment3d: other line segment.
        :param abs_tol: tolerance allowed.
        :return: a list with the intersecting point.
        """
        return d3d_utils_intersections.get_plane_linesegment_intersections(self.frame, linesegment3d, abs_tol)

    def bsplinecurve_intersections(self, bspline_curve):
        """
        Calculates the intersections between a Plane 3D and a Bspline Curve 3D.

        :param bspline_curve: bspline_curve to verify intersections.
        :return: list of intersections: List[design3d.Point3D].
        """
        return d3d_utils_intersections.get_bsplinecurve_intersections(self, bspline_curve)

    def equation_coefficients(self):
        """
        Returns the a,b,c,d coefficient from equation ax+by+cz+d = 0.

        """
        return d3d_common_operations.get_plane_equation_coefficients(self.frame)

    def plane_intersections(self, plane3d):
        """
        Computes intersection points between two Planes 3D.

        """
        plane_intersections = d3d_utils_intersections.get_two_planes_intersections(self.frame, plane3d.frame)
        if plane_intersections:
            return [curves.Line3D(plane_intersections[0], plane_intersections[1])]
        return []

    def cylindricalsurface_intersections(self, cylindrical_surface: 'CylindricalSurface3D'):
        """
        Gets intersections between plane and cylindrical surface.

        :param cylindrical_surface: cylindrical surface to get intersections with.
        :return: List containing all intersections between plane and cylindrical surface.
        """
        return cylindrical_surface.plane_intersections(self)

    def is_coincident(self, plane2, abs_tol: float = 1e-6):
        """
        Verifies if two planes are parallel and coincident.

        """
        if not isinstance(self, plane2.__class__):
            return False
        if self.is_parallel(plane2, abs_tol):
            if plane2.point_belongs(self.frame.origin, abs_tol):
                return True
        return False

    def is_parallel(self, plane2, abs_tol: float = 1e-6):
        """
        Verifies if two planes are parallel.

        """
        if self.frame.w.is_colinear_to(plane2.frame.w, abs_tol):
            return True
        return False

    @classmethod
    def plane_between_two_planes(cls, plane1, plane2, name: str = ''):
        """
        Calculates a plane between two other planes.

        :param plane1: plane1.
        :param plane2: plane2.
        :param name: object's name.
        :return: resulting plane.
        """
        plane1_plane2_intersection = plane1.plane_intersections(plane2)[0]
        u = plane1_plane2_intersection.unit_direction_vector()
        v = plane1.frame.w + plane2.frame.w
        v = v.unit_vector()
        w = u.cross(v)
        point = (plane1.frame.origin + plane2.frame.origin) / 2
        return cls(design3d.Frame3D(point, u, w, v), name=name)

    def rotation(self, center: design3d.Point3D, axis: design3d.Vector3D, angle: float):
        """
        Plane3D rotation.

        :param center: rotation center
        :param axis: rotation axis
        :param angle: angle rotation
        :return: a new rotated Plane3D
        """
        new_frame = self.frame.rotation(center=center, axis=axis, angle=angle)
        return Plane3D(new_frame)

    def translation(self, offset: design3d.Vector3D):
        """
        Plane3D translation.

        :param offset: translation vector
        :return: A new translated Plane3D
        """
        new_frame = self.frame.translation(offset)
        return Plane3D(new_frame)

    def frame_mapping(self, frame: design3d.Frame3D, side: str):
        """
        Changes frame_mapping and return a new Frame3D.

        :param frame: Frame of reference
        :type frame: `design3d.Frame3D`
        :param side: 'old' or 'new'
        """
        new_frame = self.frame.frame_mapping(frame, side)
        return Plane3D(new_frame, self.name)

    def copy(self, deep=True, memo=None):
        """Creates a copy of the plane."""
        new_frame = self.frame.copy(deep, memo)
        return Plane3D(new_frame, self.name)

    def plane_grid(self, grid_size: int, length: float = 1.):
        """
        Plane's grid.

        """
        plane_grid = []
        for i in range(grid_size):
            for v1, v2 in [(self.frame.u, self.frame.v), (self.frame.v, self.frame.u)]:
                start = self.frame.origin - 0.5 * length * v1 + (-0.5 + i / (grid_size - 1)) * length * v2
                end = self.frame.origin + 0.5 * length * v1 + (-0.5 + i / (grid_size - 1)) * length * v2
                plane_grid.append(edges.LineSegment3D(start, end))
        return plane_grid

    def plot(self, ax=None, edge_style: EdgeStyle = EdgeStyle(color='grey'), length: float = 1., **kwargs):
        """
        Plot the cylindrical surface in the local frame normal direction.

        :param ax: Matplotlib Axes3D object to plot on. If None, create a new figure.
        :type ax: Axes3D or None
        :param edge_style: edge styles.
        :type edge_style: EdgeStyle.
        :param length: plotted length
        :type length: float
        :return: Matplotlib Axes3D object containing the plotted wire-frame.
        :rtype: Axes3D
        """
        grid_size = 10

        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
            ax.set_aspect('auto')

        self.frame.plot(ax=ax, ratio=length)
        for edge in self.plane_grid(grid_size, length):
            edge.plot(ax, edge_style=edge_style)
        return ax

    def point2d_to_3d(self, point2d):
        """
        Converts a 2D parametric point into a 3D point on the surface.
        """
        return point2d.to_3d(self.frame.origin, self.frame.u, self.frame.v)

    def parametric_points_to_3d(self, points: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Transform parametric coordinates to 3D points on the plane.

        Given a set of parametric coordinates `(u, v)` representing points on the surface,
        this method returns the corresponding 3D points on the plane.

        :param points: Parametric coordinates in the form of a numpy array with shape (n, 2),
                       where `n` is the number of points, and each row corresponds to `(u, v)`.
        :type points: numpy.ndarray[np.float64]

        :return: Array of 3D points representing the plane in Cartesian coordinates.
        :rtype: numpy.ndarray[np.float64]
        """
        center = np.array(self.frame.origin)
        x = np.array([self.frame.u[0], self.frame.u[1], self.frame.u[2]])
        y = np.array([self.frame.v[0], self.frame.v[1], self.frame.v[2]])

        points = points.reshape(-1, 2, 1)

        u_values = points[:, 0]
        v_values = points[:, 1]

        return center + u_values * x + v_values * y

    def point3d_to_2d(self, point3d):
        """
        Converts a 3D point into a 2D parametric point.
        """
        return point3d.to_2d(self.frame.origin, self.frame.u, self.frame.v)

    def contour2d_to_3d(self, contour2d, return_primitives_mapping: bool = False):
        """
        Transforms a Contour2D in the parametric domain of the surface into a Contour3D in Cartesian coordinate.

        :param contour2d: The contour to be transformed.
        :type contour2d: :class:`wires.Contour2D`
        :param return_primitives_mapping: If True, returns a dictionary containing the correspondence between 2D and 3D
         primitives
        :type return_primitives_mapping: bool
        :return: A 3D contour object.
        :rtype: :class:`wires.Contour3D`
        """
        contour3d = contour2d.to_3d(self.frame.origin, self.frame.u, self.frame.v)
        if return_primitives_mapping:
            primitives_mapping = dict(zip(contour2d.primitives, contour3d.primitives))
            return contour3d, primitives_mapping
        return contour3d

    def contour3d_to_2d(self, contour3d, return_primitives_mapping: bool = False):
        """
        Transforms a Contour3D into a Contour2D in the parametric domain of the surface.

        :param contour3d: The contour to be transformed.
        :type contour3d: :class:`wires.Contour3D`
        :param return_primitives_mapping: If True, returns a dictionary containing the correspondence between 2D and 3D
         primitives
        :type return_primitives_mapping: bool
        :return: A 2D contour object.
        :rtype: :class:`wires.Contour2D`
        """
        primitives2d = []
        primitives_mapping = {}
        for primitive3d in contour3d.primitives:
            method_name = f'{primitive3d.__class__.__name__.lower()}_to_2d'
            if hasattr(self, method_name):
                primitives = getattr(self, method_name)(primitive3d)
                if primitives is None:
                    continue
                self.update_primitives_mapping(primitives_mapping, primitives, primitive3d)
                primitives2d.extend(primitives)
            else:
                primitive = primitive3d.to_2d(self.frame.origin, self.frame.u, self.frame.v)
                if primitive is None:
                    continue
                self.update_primitives_mapping(primitives_mapping, [primitive], primitive3d)
                primitives2d.append(primitive)
        if return_primitives_mapping:
            return wires.Contour2D(primitives2d), primitives_mapping
        return wires.Contour2D(primitives2d)

    def arc3d_to_2d(self, arc3d):
        """Converts primitive from 3D cartesian space to surface parametric space."""
        arc = None
        if arc3d.circle.frame.w.is_colinear_to(self.frame.w, 1e-5):
            arc = [arc3d.to_2d(self.frame.origin, self.frame.u, self.frame.v)]
        else:
            start = self.point3d_to_2d(arc3d.start)
            end = self.point3d_to_2d(arc3d.end)
            if not start.is_close(end):
                arc = [edges.LineSegment2D(start, end)]
        return arc

    def bsplinecurve3d_to_2d(self, bspline_curve3d):
        """
        Converts a 3D B-Spline in spatial domain into a 2D B-Spline in parametric domain.

        :param bspline_curve3d: The B-Spline curve to perform the transformation.
        :type bspline_curve3d: edges.BSplineCurve3D
        :return: A 2D B-Spline.
        :rtype: edges.BSplineCurve2D
        """
        control_points = [self.point3d_to_2d(p)
                          for p in bspline_curve3d.control_points]
        return [edges.BSplineCurve2D(
            bspline_curve3d.degree,
            control_points=control_points,
            knot_multiplicities=bspline_curve3d.knot_multiplicities,
            knots=bspline_curve3d.knots,
            weights=bspline_curve3d.weights)]

    def bsplinecurve2d_to_3d(self, bspline_curve2d):
        """
        Converts a 2D B-Spline in parametric domain into a 3D B-Spline in spatial domain.

        :param bspline_curve2d: The B-Spline curve to perform the transformation.
        :type bspline_curve2d: edges.BSplineCurve2D
        :return: A 3D B-Spline.
        :rtype: edges.BSplineCurve3D
        """
        control_points = [self.point2d_to_3d(point)
                          for point in bspline_curve2d.control_points]
        return [edges.BSplineCurve3D(
            bspline_curve2d.degree,
            control_points=control_points,
            knot_multiplicities=bspline_curve2d.knot_multiplicities,
            knots=bspline_curve2d.knots,
            weights=bspline_curve2d.weights)]

    def rectangular_cut(self, x1: float, x2: float,
                        y1: float, y2: float, name: str = ''):
        """Deprecated method, Use PlaneFace3D from_surface_rectangular_cut method."""

        raise AttributeError('Use PlaneFace3D from_surface_rectangular_cut method')

    def u_iso(self, u: float) -> curves.Line3D:
        """
        Returns the u-iso curve of the surface.

        :param u: The value of u where to extract the curve.
        :type u: float
        :return: A line 3D
        :rtype: :class:`curves.Line3D`
        """

        point_at_u = self.point2d_to_3d(design3d.Point2D(u, 0.0))

        return curves.Line3D.from_point_and_vector(point_at_u, self.frame.v)

    def v_iso(self, v: float) -> curves.Line3D:
        """
        Returns the v-iso curve of the surface.

        :param v: The value of u where to extract the curve.
        :type v: float
        :return: A line 3D
        :rtype: :class:`curves.Line3D`
        """

        point_at_v = self.point2d_to_3d(design3d.Point2D(0.0, v))

        return curves.Line3D.from_point_and_vector(point_at_v, self.frame.u)

    def normal_at_point(self, point):
        """
        Gets Normal vector at a given point on the surface.

        :param point: point on the surface.
        :return:
        """
        if not self.point_belongs(point):
            raise ValueError(f'Point {point} not on this surface.')
        return self.frame.w


PLANE3D_OXY = Plane3D(design3d.OXYZ)
PLANE3D_OYZ = Plane3D(design3d.OYZX)
PLANE3D_OZX = Plane3D(design3d.OZXY)
PLANE3D_OXZ = Plane3D(design3d.Frame3D(design3d.O3D, design3d.X3D, design3d.Z3D, design3d.Y3D))


class UPeriodicalSurface(Surface3D):
    """
    Abstract class for surfaces with two-pi periodicity that creates some problems.
    """

    def point2d_to_3d(self, point2d):
        """
        Abstract method.
        """
        raise NotImplementedError(f'point2d_to_3d is abstract and should be implemented in {self.__class__.__name__}')

    def point3d_to_2d(self, point3d):
        """
        Abstract method. Convert a 3D point to a 2D parametric point.

        :param point3d: The 3D point to convert, represented by 3 coordinates (x, y, z).
        :type point3d: `design3d.Point3D`
        :return: NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError(f'point3d_to_2d is abstract and should be implemented in {self.__class__.__name__}')

    def v_iso(self, v):
        """
        Abstract method.
        """
        raise NotImplementedError(f'v_iso is abstract and should be implemented in {self.__class__.__name__}')

    def _align_contours(self, inner_contour, theta_contours, z_outer_contour, z_inner_contour):
        """
        Helper function to align contours' BREP on periodical surfaces that need to be connected.
        """
        outer_contour_theta, inner_contour_theta = theta_contours
        overlapping_theta, outer_contour_side, inner_contour_side, side = self._get_overlapping_theta(
            outer_contour_theta,
            inner_contour_theta)
        line = curves.Line2D(design3d.Point2D(overlapping_theta, z_outer_contour),
                             design3d.Point2D(overlapping_theta, z_inner_contour))
        cutted_contours = inner_contour.split_by_line(line)
        number_contours = len(cutted_contours)
        if number_contours == 2:
            contour1, contour2 = cutted_contours
            increasing_theta = inner_contour_theta[0] < inner_contour_theta[1]
            # side = 0 --> left  side = 1 --> right
            if (not side and increasing_theta) or (
                    side and not increasing_theta):
                theta_offset = outer_contour_theta[outer_contour_side] - contour2.primitives[0].start.x
                contour2_positionned = contour2.translation(offset=design3d.Vector2D(theta_offset, 0))
                theta_offset = contour2_positionned.primitives[-1].end.x - contour1.primitives[0].start.x
                contour1_positionned = contour1.translation(offset=design3d.Vector2D(theta_offset, 0))

            else:
                theta_offset = outer_contour_theta[outer_contour_side] - contour1.primitives[-1].end.x
                contour1_positionned = contour1.translation(offset=design3d.Vector2D(theta_offset, 0))
                theta_offset = contour1_positionned.primitives[0].start.x - contour2.primitives[-1].end.x
                contour2_positionned = contour2.translation(offset=design3d.Vector2D(theta_offset, 0))
            old_innner_contour_positioned = wires.Wire2D(contour2_positionned.primitives +
                                                         contour1_positionned.primitives).order_wire(tol=1e-2)
        elif number_contours == 1:
            theta_offset = outer_contour_theta[outer_contour_side] - inner_contour_theta[inner_contour_side]
            translation_vector = design3d.Vector2D(theta_offset, 0)
            old_innner_contour_positioned = cutted_contours[0].translation(offset=translation_vector)

        else:
            raise NotImplementedError

        return old_innner_contour_positioned

    @staticmethod
    def _get_closing_points(old_outer_contour_positioned, old_innner_contour_positioned):
        """
        Helper function to get points to connect contours with line segments.
        """
        point1 = old_outer_contour_positioned.primitives[0].start
        point2 = old_outer_contour_positioned.primitives[-1].end
        point3 = old_innner_contour_positioned.primitives[0].start
        point4 = old_innner_contour_positioned.primitives[-1].end

        outer_contour_direction = point1.x < point2.x
        inner_contour_direction = point3.x < point4.x
        if outer_contour_direction == inner_contour_direction:
            old_innner_contour_positioned = old_innner_contour_positioned.invert()
            point3 = old_innner_contour_positioned.primitives[0].start
            point4 = old_innner_contour_positioned.primitives[-1].end
        if not math.isclose(point2.x, point3.x, abs_tol=1e-4) or \
                not math.isclose(point4.x, point1.x, abs_tol=1e-4):
            ideal_x = []
            delta = math.inf
            found = False
            for x1 in [point2.x, point3.x]:
                for x2 in [point4.x, point1.x]:
                    delta_x = abs(abs(x1 - x2) - design3d.TWO_PI)
                    if delta_x == 0.0:
                        ideal_x = [x1, x2]
                        found = True
                        break
                    if delta_x < delta:
                        delta = delta_x
                        ideal_x = [x1, x2]
                if found:
                    break
            x1, x2 = ideal_x
            point2.x = x1
            point3.x = x1
            point4.x = x2
            point1.x = x2

        return point1, point2, point3, point4

    def connect_contours(self, outer_contour, inner_contours):
        """
        Repair contours on parametric domain.

        :param outer_contour: Outer contour 2D.
        :type inner_contours: wires.Contour2D
        :param inner_contours: List of 2D contours.
        :type inner_contours: list
        """
        new_inner_contours = []
        point1 = outer_contour.primitives[0].start
        point2 = outer_contour.primitives[-1].end

        theta1, z1 = point1
        theta2, _ = point2

        new_outer_contour = outer_contour
        for inner_contour in inner_contours:
            theta3, z3 = inner_contour.primitives[0].start
            theta4, _ = inner_contour.primitives[-1].end

            if not inner_contour.is_ordered():
                # Contours are aligned
                if (math.isclose(theta1, theta3, abs_tol=1e-3) and math.isclose(theta2, theta4, abs_tol=1e-3)) \
                        or (math.isclose(theta1, theta4, abs_tol=1e-3) and math.isclose(theta2, theta3, abs_tol=1e-3)):
                    old_innner_contour_positioned = inner_contour

                else:
                    old_innner_contour_positioned = self._align_contours(inner_contour, [[theta1, theta2],
                                                                                         [theta3, theta4]], z1, z3)
                point1, point2, point3, point4 = self._get_closing_points(outer_contour,
                                                                          old_innner_contour_positioned)
                closing_linesegment1 = edges.LineSegment2D(point2, point3)
                closing_linesegment2 = edges.LineSegment2D(point4, point1)
                new_outer_contour_primitives = outer_contour.primitives + [closing_linesegment1] + \
                                               old_innner_contour_positioned.primitives + [closing_linesegment2]
                new_outer_contour = wires.Contour2D(primitives=new_outer_contour_primitives)
                if not new_outer_contour.is_ordered():
                    try:
                        new_outer_contour = new_outer_contour.order_contour(
                            tol=min(1e-2, 0.1 * closing_linesegment1.length(), 0.1 * closing_linesegment2.length()))
                    except NotImplementedError:
                        pass
            else:
                new_inner_contours.append(inner_contour)
        return new_outer_contour, new_inner_contours

    @staticmethod
    def _get_overlapping_theta(outer_contour_startend_theta, inner_contour_startend_theta):
        """
        Find overlapping theta domain between two contours on periodical Surfaces.
        """
        oc_xmin_index, outer_contour_xmin = min(enumerate(outer_contour_startend_theta), key=lambda x: x[1])
        oc_xmax_index, outer_contour_xman = max(enumerate(outer_contour_startend_theta), key=lambda x: x[1])
        ic_xmin_index, inner_contour_xmin = min(enumerate(inner_contour_startend_theta), key=lambda x: x[1])
        ic_xmax_index, inner_contour_xmax = max(enumerate(inner_contour_startend_theta), key=lambda x: x[1])

        # check if tetha3 or theta4 is in [theta1, theta2] interval
        overlap = outer_contour_xmin <= inner_contour_xmax and outer_contour_xman >= inner_contour_xmin

        if overlap:
            if inner_contour_xmin < outer_contour_xmin:
                overlapping_theta = outer_contour_startend_theta[oc_xmin_index]
                side = 0
                return overlapping_theta, oc_xmin_index, ic_xmin_index, side
            overlapping_theta = outer_contour_startend_theta[oc_xmax_index]
            side = 1
            return overlapping_theta, oc_xmax_index, ic_xmax_index, side

        # if not direct intersection -> find intersection at periodicity
        if inner_contour_xmin < outer_contour_xmin:
            overlapping_theta = outer_contour_startend_theta[oc_xmin_index] - 2 * math.pi
            side = 0
            return overlapping_theta, oc_xmin_index, ic_xmin_index, side
        overlapping_theta = outer_contour_startend_theta[oc_xmax_index] + 2 * math.pi
        side = 1
        return overlapping_theta, oc_xmax_index, ic_xmax_index, side

    def _reference_points(self, edge):
        """
        Helper function to return points of reference on the edge to fix some parametric periodical discontinuities.
        """
        length = edge.length()
        point_after_start = self.point3d_to_2d(edge.point_at_abscissa(0.01 * length))
        point_before_end = self.point3d_to_2d(edge.point_at_abscissa(0.98 * length))
        theta3, _ = point_after_start
        theta4, _ = point_before_end
        if abs(theta3) == math.pi or abs(theta3) == 0.5 * math.pi:
            point_after_start = self.point3d_to_2d(edge.point_at_abscissa(0.02 * length))
        if abs(theta4) == math.pi or abs(theta4) == 0.5 * math.pi:
            point_before_end = self.point3d_to_2d(edge.point_at_abscissa(0.97 * length))
        return point_after_start, point_before_end

    def _verify_start_end_angles(self, edge, theta1, theta2):
        """
        Verify if there is some incoherence with start and end angles. If so, return fixed angles.
        """
        length = edge.length()
        theta3, _ = self.point3d_to_2d(edge.point_at_abscissa(0.001 * length))
        # make sure that the reference angle is not undefined
        if abs(theta3) == math.pi or abs(theta3) == 0.5 * math.pi:
            theta3, _ = self.point3d_to_2d(edge.point_at_abscissa(0.002 * length))

        # Verify if theta1 or theta2 point should be -pi because atan2() -> ]-pi, pi]
        # And also atan2 discontinuity in 0.5 * math.pi
        if math.isclose(abs(theta1), math.pi, abs_tol=1e-4) or abs(theta1) == 0.5 * math.pi:
            theta1 = repair_start_end_angle_periodicity(theta1, theta3)
        if abs(theta2) == math.pi or abs(theta2) == 0.5 * math.pi:
            theta4, _ = self.point3d_to_2d(edge.point_at_abscissa(0.98 * length))
            # make sure that the reference angle is not undefined
            if math.isclose(abs(theta2), math.pi, abs_tol=1e-4) or abs(theta4) == 0.5 * math.pi:
                theta4, _ = self.point3d_to_2d(edge.point_at_abscissa(0.97 * length))
            theta2 = repair_start_end_angle_periodicity(theta2, theta4)

        return theta1, theta2

    def _helper_fix_angle_discontinuity(self, points, index_angle_discontinuity, i):
        sign = round(points[index_angle_discontinuity - 1][i] / abs(points[index_angle_discontinuity - 1][i]), 2)
        if i == 0:
            points = [p + design3d.Point2D(sign * design3d.TWO_PI, 0) if i >= index_angle_discontinuity else p
                      for i, p in enumerate(points)]
        else:
            points = [p + design3d.Point2D(0, sign * design3d.TWO_PI) if i >= index_angle_discontinuity else p
                      for i, p in enumerate(points)]
        return points

    def _fix_angle_discontinuity_on_discretization_points(self, points, indexes_angle_discontinuity, direction):
        i = 0 if direction == "x" else 1
        if len(indexes_angle_discontinuity) == 1:
            index_angle_discontinuity = indexes_angle_discontinuity[0]
            points = self._helper_fix_angle_discontinuity(points, index_angle_discontinuity, i)
        else:
            stack = deque(indexes_angle_discontinuity)
            while stack:
                index_angle_discontinuity = stack.popleft()
                if stack:
                    next_angle_discontinuity_index = stack[0]
                    temp_points = points[:next_angle_discontinuity_index]
                    temp_points = self._helper_fix_angle_discontinuity(temp_points, index_angle_discontinuity, i)
                    points = temp_points + points[next_angle_discontinuity_index:]
                else:
                    temp_points = points
                    points = self._helper_fix_angle_discontinuity(temp_points, index_angle_discontinuity, i)
                _, indexes_angle_discontinuity = angle_discontinuity([point.x for point in points])
                stack = deque(indexes_angle_discontinuity)
        return points

    def _helper_arc3d_to_2d_periodicity_verifications(self, arc3d, start):
        """
        Verifies if arc 3D contains discontinuity and undefined start/end points on parametric domain.
        """
        point_theta_discontinuity = self.point2d_to_3d(design3d.Point2D(math.pi, start.y))
        discontinuity = arc3d.point_belongs(point_theta_discontinuity) and not \
            arc3d.is_point_edge_extremity(point_theta_discontinuity)

        undefined_start_theta = arc3d.start.is_close(point_theta_discontinuity)
        undefined_end_theta = arc3d.end.is_close(point_theta_discontinuity)
        return discontinuity, undefined_start_theta, undefined_end_theta

    def linesegment3d_to_2d(self, linesegment3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.

        For cylindrical or conical surfaces, a line segment in 3D space is typically projected onto
        the 2D parametric space as a vertical line segment. This is because a 3D line that lies on a
        cylindrical or conical surface corresponds to a generatrix of the surface, and it extends along
        the height of the surface without bending or deviating in the other directions.
        Therefore, the BREP of a line segment on cylindrical or conical surface is a vertical line segment.
        """
        start = self.point3d_to_2d(linesegment3d.start)
        end = self.point3d_to_2d(linesegment3d.end)
        _, _, z1 = self.frame.global_to_local_coordinates(linesegment3d.start)
        _, _, z2 = self.frame.global_to_local_coordinates(linesegment3d.end)
        if math.isclose(z1, z2, rel_tol=0.005):
            # special case when there is a small line segment that should be a small arc of circle instead
            return [edges.LineSegment2D(start, end)]
        if start.x != end.x:
            end = design3d.Point2D(start.x, end.y)
        if not start.is_close(end):
            return [edges.LineSegment2D(start, end)]
        return None

    def arc3d_to_2d(self, arc3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.

        The BREP of an arc of circle on a cylindrical or a conical surface is a horizontal line segment.
        """
        start = self.point3d_to_2d(arc3d.start)
        end = self.point3d_to_2d(arc3d.end)
        point_after_start, point_before_end = self._reference_points(arc3d)
        discontinuity, undefined_start_theta, undefined_end_theta = self._helper_arc3d_to_2d_periodicity_verifications(
            arc3d, start)
        start, end = d3d_parametric.arc3d_to_cylindrical_coordinates_verification(
            [start, end], [undefined_start_theta, undefined_end_theta],
            [point_after_start.x, point_before_end.x], discontinuity)
        return [edges.LineSegment2D(start, end)]

    def fullarc3d_to_2d(self, fullarc3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.

        The BREP of a circle on a cylindrical or a conical surface is a horizontal line segment with length of two pi.
        """
        start = self.point3d_to_2d(fullarc3d.start)
        end = self.point3d_to_2d(fullarc3d.end)

        if self.frame.w.is_colinear_to(fullarc3d.circle.normal):
            normal_dot_product = self.frame.w.dot(fullarc3d.circle.normal)
            start, end = d3d_parametric.fullarc_to_cylindrical_coordinates_verification(start, end, normal_dot_product)
            return [edges.LineSegment2D(start, end)]
        raise NotImplementedError("This case must be treated in child class.")

    def bsplinecurve3d_to_2d(self, bspline_curve3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        n = bspline_curve3d.ctrlpts.shape[0]
        points3d = bspline_curve3d.discretization_points(number_points=n)
        points = [self.point3d_to_2d(point) for point in points3d]
        if self.is_singularity_point(bspline_curve3d.start) or self.is_singularity_point(bspline_curve3d.end):
            points = self._fix_start_end_singularity_point_at_parametric_domain(bspline_curve3d, points, points3d)
        theta1, z1 = points[0]
        theta2, z2 = points[-1]
        theta1, theta2 = self._verify_start_end_angles(bspline_curve3d, theta1, theta2)
        points[0] = design3d.Point2D(theta1, z1)
        points[-1] = design3d.Point2D(theta2, z2)

        theta_list = [point.x for point in points]
        theta_discontinuity, indexes_theta_discontinuity = angle_discontinuity(theta_list)
        if theta_discontinuity:
            points = self._fix_angle_discontinuity_on_discretization_points(points,
                                                                            indexes_theta_discontinuity, "x")

        return [edges.BSplineCurve2D.from_points_interpolation(points, degree=bspline_curve3d.degree)]

    def arcellipse3d_to_2d(self, arcellipse3d):
        """
        Transformation of a 3D arc of ellipse to a 2D primitive in a cylindrical surface.

        """
        points = [self.point3d_to_2d(p)
                  for p in arcellipse3d.discretization_points(number_points=50)]

        theta1, z1 = points[0]
        theta2, z2 = points[-1]

        # theta3, _ = self.point3d_to_2d(arcellipse3d.point_at_abscissa(0.001 * length))
        theta3, _ = points[1]
        # make sure that the reference angle is not undefined
        if abs(theta3) == math.pi:
            theta3, _ = points[1]

        # Verify if theta1 or theta2 point should be -pi because atan2() -> ]-pi, pi]
        if abs(theta1) == math.pi:
            theta1 = d3d_parametric.repair_start_end_angle_periodicity(theta1, theta3)
        if abs(theta2) == math.pi:
            theta4, _ = points[-2]
            # make sure that the reference angle is not undefined
            if abs(theta4) == math.pi:
                theta4, _ = points[-3]
            theta2 = d3d_parametric.repair_start_end_angle_periodicity(theta2, theta4)

        points[0] = design3d.Point2D(theta1, z1)
        points[-1] = design3d.Point2D(theta2, z2)

        theta_list = [point.x for point in points]
        theta_discontinuity, indexes_theta_discontinuity = angle_discontinuity(theta_list)
        if theta_discontinuity:
            points = self._fix_angle_discontinuity_on_discretization_points(points,
                                                                            indexes_theta_discontinuity, "x")

        return [edges.BSplineCurve2D.from_points_interpolation(points, degree=2, name="parametric.arcellipse")]

    def fullarcellipse3d_to_2d(self, fullarcellipse3d):
        """
        Transformation of a 3D arc ellipse to 2D, in a cylindrical surface.

        """
        points = [self.point3d_to_2d(p)
                  for p in fullarcellipse3d.discretization_points(number_points=72)]
        start, end = points[0], points[-1]
        normal_dot_product = self.frame.w.dot(fullarcellipse3d.ellipse.normal)
        start, end = d3d_parametric.fullarc_to_cylindrical_coordinates_verification(start, end, normal_dot_product)
        theta1, z1 = start
        theta2, z2 = end
        theta1, theta2 = self._verify_start_end_angles(fullarcellipse3d, theta1, theta2)

        theta_list = [point.x for point in points]
        theta_discontinuity, indexes_theta_discontinuity = angle_discontinuity(theta_list)
        if theta_discontinuity:
            points = self._fix_angle_discontinuity_on_discretization_points(points,
                                                                            indexes_theta_discontinuity, "x")
        points[0] = design3d.Point2D(theta1, z1)
        points[-1] = design3d.Point2D(theta2, z2)

        return [edges.BSplineCurve2D.from_points_interpolation(points, degree=3,
                                                               name="parametric.fullarcellipse")]

    def bsplinecurve2d_to_3d(self, bspline_curve2d):
        """
        Is this right?.
        """
        n = len(bspline_curve2d.control_points)
        points = [self.point2d_to_3d(p)
                  for p in bspline_curve2d.discretization_points(number_points=n)]
        return [edges.BSplineCurve3D.from_points_interpolation(points, bspline_curve2d.degree, centripetal=True)]

    def linesegment2d_to_3d(self, linesegment2d):
        """
        Converts a BREP line segment 2D onto a 3D primitive on the surface.
        """

        if linesegment2d.name == "construction" or self.is_degenerated_brep(linesegment2d):
            return None

        theta1, param_z1 = linesegment2d.start
        theta2, param_z2 = linesegment2d.end
        start3d = self.point2d_to_3d(linesegment2d.start)
        end3d = self.point2d_to_3d(linesegment2d.end)

        if math.isclose(theta1, theta2, abs_tol=1e-4):
            if start3d.is_close(end3d):
                return None
            return [edges.LineSegment3D(start3d, end3d)]

        if math.isclose(param_z1, param_z2, abs_tol=1e-4):
            circle3d = self.v_iso(param_z1)
            if theta1 > theta2:
                circle3d = circle3d.reverse()
            return [circle3d.trim(start3d, end3d)]
        if start3d.is_close(end3d):
            return None
        n = int(54 * abs(theta2 - theta1)/math.pi)
        points = [self.point2d_to_3d(p)
                  for p in linesegment2d.discretization_points(number_points=n)]
        return [edges.BSplineCurve3D.from_points_interpolation(points, 7)]

    @staticmethod
    def is_undefined_brep(edge):
        """Returns True if the edge is contained within the periodicity boundary."""
        if isinstance(edge.simplify, edges.LineSegment2D) and \
                edge.simplify.line.unit_direction_vector().is_colinear_to(design3d.Y2D) \
                and math.isclose(abs(edge.start.x), math.pi, abs_tol=1e-6):
            return True
        return False

    def is_degenerated_brep(self, *args):
        """
        An edge is said to be degenerated when it corresponds to a single 3D point.
        """
        edge = args[0]
        start3d = self.point2d_to_3d(edge.start)
        end3d = self.point2d_to_3d(edge.end)
        return bool(self.is_singularity_point(start3d) and start3d.is_close(end3d))

    def fix_undefined_brep_with_neighbors(self, edge, previous_edge, next_edge):
        """Uses neighbors edges to fix edge contained within the periodicity boundary."""
        delta_previous = previous_edge.end - edge.start
        delta_next = next_edge.start - edge.end
        if not self.is_undefined_brep(previous_edge) and \
                math.isclose(delta_previous.norm(), self.x_periodicity, abs_tol=1e-3):
            edge = edge.translation(delta_previous)
        elif not self.is_undefined_brep(next_edge) and \
                math.isclose(delta_next.norm(), self.x_periodicity, abs_tol=1e-3):
            edge = edge.translation(delta_next)
        elif (math.isclose(delta_previous.x, delta_next.x, abs_tol=1e-3) and
              math.isclose(abs(delta_previous.x), self.x_periodicity, abs_tol=1e-3)):
            edge = edge.translation(delta_next)
        return edge

    def _fix_start_end_singularity_point_at_parametric_domain(self, edge3d, points, points3d):
        """
        Helper function.

        Uses local discretization and line intersection with the tangent line at the point just before the undefined
        point on the BREP of the 3D edge to find the real values on parametric domain.
        """

        def get_local_discretization_points(start_point, end_points):
            distance = start_point.point_distance(end_points)
            maximum_linear_distance_reference_point = 1e-4
            if distance < maximum_linear_distance_reference_point:
                return []
            number_points = max(int(distance / maximum_linear_distance_reference_point), 2)

            local_discretization = [self.point3d_to_2d(point)
                                    for point in edge3d.local_discretization(
                    start_point, end_points, number_points)]
            return local_discretization

        def get_temp_edge2d(_points):
            theta_list = [point.x for point in _points]
            theta_discontinuity, indexes_theta_discontinuity = angle_discontinuity(theta_list)
            if theta_discontinuity:
                _points = self._fix_angle_discontinuity_on_discretization_points(_points,
                                                                                 indexes_theta_discontinuity, "x")
            if len(_points) == 2:
                edge2d = edges.LineSegment2D(_points[0], _points[1])
            else:
                edge2d = edges.BSplineCurve2D.from_points_interpolation(_points, 2)
            return edge2d

        if self.is_singularity_point(points3d[0]):
            local_discretization_points = get_local_discretization_points(start_point=points3d[0],
                                                                          end_points=points3d[1])
            if local_discretization_points:
                temp_points = local_discretization_points[1:] + points[2:]
            else:
                temp_points = points
            temp_edge2d = get_temp_edge2d(temp_points)
            singularity_lines = self.get_singularity_lines()
            if len(singularity_lines) > 1:
                singularity_line = min(singularity_lines, key=lambda x: x.point_distance(temp_points[0]))
            else:
                singularity_line = singularity_lines[0]
            points[0] = find_parametric_point_at_singularity(temp_edge2d, abscissa=0,
                                                             singularity_line=singularity_line, domain=self.domain)
        if self.is_singularity_point(points3d[-1]):
            local_discretization_points = get_local_discretization_points(start_point=points3d[-2],
                                                                          end_points=points3d[-1])
            if local_discretization_points:
                temp_points = points[:-2] + local_discretization_points[:-1]
            else:
                temp_points = points[:-1]
            temp_edge2d = get_temp_edge2d(temp_points)
            singularity_lines = self.get_singularity_lines()
            if len(singularity_lines) > 1:
                singularity_line = min(singularity_lines, key=lambda x: x.point_distance(temp_points[-1]))
            else:
                singularity_line = singularity_lines[0]
            points[-1] = find_parametric_point_at_singularity(temp_edge2d, abscissa=temp_edge2d.length(),
                                                              singularity_line=singularity_line, domain=self.domain)
        return points


class UVPeriodicalSurface(UPeriodicalSurface):
    """
    Abstract class for surfaces with two-pi periodicity in both u and v parametric directions.
    """

    def point2d_to_3d(self, point2d):
        """
        Abstract method.
        """
        raise NotImplementedError(f'point2d_to_3d is abstract and should be implemented in {self.__class__.__name__}')

    def point3d_to_2d(self, point3d):
        """
        Abstract method. Convert a 3D point to a 2D parametric point.

        :param point3d: The 3D point to convert, represented by 3 coordinates (x, y, z).
        :type point3d: `design3d.Point3D`
        :return: NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError(f'point3d_to_2d is abstract and should be implemented in {self.__class__.__name__}')

    def u_iso(self, u):
        """
        Abstract method.
        """
        raise NotImplementedError(f'u_iso is abstract and should be implemented in {self.__class__.__name__}')

    def v_iso(self, v):
        """
        Abstract method.
        """
        raise NotImplementedError(f'u_iso is abstract and should be implemented in {self.__class__.__name__}')

    def linesegment2d_to_3d(self, linesegment2d):
        """
        Converts the parametric boundary representation into a 3D primitive.
        """
        if linesegment2d.name == "construction" or self.is_degenerated_brep(linesegment2d):
            return None

        theta1, phi1 = linesegment2d.start
        theta2, phi2 = linesegment2d.end

        start3d = self.point2d_to_3d(linesegment2d.start)
        end3d = self.point2d_to_3d(linesegment2d.end)
        if math.isclose(theta1, theta2, abs_tol=1e-4):
            circle = self.u_iso(theta1)
            if phi1 > phi2:
                circle = circle.reverse()
            return [circle.trim(start3d, end3d)]
        if math.isclose(phi1, phi2, abs_tol=1e-4):
            circle = self.v_iso(phi1)
            if theta1 > theta2:
                circle = circle.reverse()
            return [circle.trim(start3d, end3d)]
        points = [self.point2d_to_3d(point2d) for point2d in linesegment2d.discretization_points(number_points=10)]
        return [edges.BSplineCurve3D.from_points_interpolation(points, degree=3).simplify]


class CylindricalSurface3D(UPeriodicalSurface):
    """
    The local plane is defined by (theta, z).

    :param frame: frame.w is axis, frame.u is theta=0 frame.v theta=pi/2
    :param frame:
    :param radius: Cylinder's radius
    :type radius: float
    """
    face_class = 'CylindricalFace3D'
    x_periodicity = design3d.TWO_PI
    y_periodicity = None

    def __init__(self, frame, radius: float, name: str = ''):
        self.radius = radius
        UPeriodicalSurface.__init__(self, frame=frame, name=name)

    def __hash__(self):
        return hash((self.__class__.__name__, self.frame, self.radius))

    def __eq__(self, other):
        if self.__class__.__name__ != other.__class__.__name__:
            return False
        if self.frame == other.frame and self.radius == other.radius:
            return True
        return False

    @property
    def u_domain(self):
        """The parametric domain of the surface in the U direction."""
        return -math.pi, math.pi

    @property
    def v_domain(self):
        """The parametric domain of the surface in the V direction."""
        return -math.inf, math.inf

    def get_generatrices(self, number_lines: int = 30, length: float = 1):
        """
        Retrieve line segments representing the generatrices of a cylinder.

        Generates a specified number of line segments along the surface of the cylinder,
        each representing a generatrix.

        :param number_lines: The number of generatrices to generate. Default is 30
        :type number_lines: int
        :param length: The length of the cylinder along the z-direction. Default is 1.
        :type length: float
        :return: A list of LineSegment3D instances representing the generatrices of the cylinder.
        :rtype: List[LineSegment3D]
        """
        list_generatrices = []
        for i in range(number_lines):
            theta = i / (number_lines - 1) * design3d.TWO_PI
            start = self.point2d_to_3d(design3d.Point2D(theta, -0.5 * length))
            end = self.point2d_to_3d(design3d.Point2D(theta, 0.5 * length))
            generatrix = edges.LineSegment3D(start, end)
            list_generatrices.append(generatrix)
        return list_generatrices

    def get_circle_generatrices(self, number_circles: int = 10, length: float = 1.0):
        """
        Retrieve circles representing the generatrices of a cylinder.

        Generates a specified number of circles along the surface of the cylinder,
        each representing a generatrix.

        :param number_circles: The number of generatrices to generate. Default is 10
        :type number_circles: int
        :param length: The length of the cylinder along the z-direction. Default is 1.
        :type length: float
        :return: A list of Circle3D instances representing the generatrices of the cylinder.
        :rtype: List[Circle3D]
        """
        return [self.v_iso((-0.5 + j / (number_circles - 1)) * length) for j in range(number_circles)]

    def plot(self, ax=None, edge_style: EdgeStyle = EdgeStyle(color='grey', alpha=0.5),
             length=None, **kwargs):
        """
        Plot the cylindrical surface in the local frame normal direction.

        :param ax: Matplotlib Axes3D object to plot on. If None, create a new figure.
        :type ax: Axes3D or None
        :param edge_style: edge styles.
        :type edge_style: EdgeStyle.
        :param length: plotted length
        :type length: float
        :return: Matplotlib Axes3D object containing the plotted wire-frame.
        :rtype: Axes3D
        """
        ncircles = 50
        nlines = 50

        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
        if length is None:
            length = self.radius

        self.frame.plot(ax=ax, color=edge_style.color, ratio=self.radius)
        for edge in self.get_generatrices(nlines, length):
            edge.plot(ax=ax, edge_style=edge_style)

        circles = self.get_circle_generatrices(ncircles, length)
        for circle in circles:
            circle.plot(ax=ax, edge_style=edge_style)
        return ax

    def point2d_to_3d(self, point2d: design3d.Point2D):
        """
        Coverts a parametric coordinate on the surface into a 3D spatial point (x, y, z).

        :param point2d: Point at the ToroidalSuface3D
        :type point2d: `design3d.`Point2D`
        """

        point = design3d.Point3D(self.radius * math.cos(point2d.x),
                                self.radius * math.sin(point2d.x),
                                point2d.y)
        return self.frame.local_to_global_coordinates(point)

    def parametric_points_to_3d(self, points: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Transform parametric coordinates to 3D points on the cylindrical surface.

        Given a set of parametric coordinates `(u, v)` representing points on the surface,
        this method returns the corresponding 3D points on the cylindrical surface.

        :param points: Parametric coordinates in the form of a numpy array with shape (n, 2),
                       where `n` is the number of points, and each row corresponds to `(u, v)`.
        :type points: numpy.ndarray[np.float64]

        :return: Array of 3D points representing the cylindrical surface in Cartesian coordinates.
        :rtype: numpy.ndarray[np.float64]
        """
        center = np.array(self.frame.origin)
        x = np.array([self.frame.u[0], self.frame.u[1], self.frame.u[2]])
        y = np.array([self.frame.v[0], self.frame.v[1], self.frame.v[2]])
        z = np.array([self.frame.w[0], self.frame.w[1], self.frame.w[2]])

        points = points.reshape(-1, 2, 1)

        u_values = points[:, 0]
        v_values = points[:, 1]

        x_component = np.cos(u_values) * x
        y_component = np.sin(u_values) * y
        z_component = v_values * z

        return center + self.radius * (x_component + y_component) + z_component

    def point3d_to_2d(self, point3d):
        """
        Returns the cylindrical coordinates design3d.Point2D(theta, z) of a Cartesian coordinates point (x, y, z).

        :param point3d: Point at the CylindricalSuface3D
        :type point3d: `design3d.`Point3D`
        """
        x, y, z = self.frame.global_to_local_coordinates(point3d)
        # Do not delete this, mathematical problem when x and y close to zero but not 0
        if abs(x) < 1e-12:
            x = 0
        if abs(y) < 1e-12:
            y = 0

        theta = math.atan2(y, x)
        if abs(theta) < 1e-9:
            theta = 0.0

        return design3d.Point2D(theta, z)

    @classmethod
    def from_step(cls, arguments, object_dict, **kwargs):
        """
        Converts a step primitive to a CylindricalSurface3D.

        :param arguments: The arguments of the step primitive.
        :type arguments: list
        :param object_dict: The dictionary containing all the step primitives
            that have already been instantiated
        :type object_dict: dict
        :return: The corresponding CylindricalSurface3D object.
        :rtype: :class:`design3d.faces.CylindricalSurface3D`
        """

        length_conversion_factor = kwargs.get("length_conversion_factor", 1)
        frame = object_dict[arguments[1]]
        radius = float(arguments[2]) * length_conversion_factor
        return cls(frame, radius, arguments[0][1:-1])

    def to_step(self, current_id):
        """
        Converts the object to a STEP representation.

        :param current_id: The ID of the last written primitive.
        :type current_id: int
        :return: The STEP representation of the object and the last ID.
        :rtype: tuple[str, list[int]]
        """
        content, frame_id = self.frame.to_step(current_id)
        current_id = frame_id + 1
        content += f"#{current_id} = CYLINDRICAL_SURFACE('{self.name}',#{frame_id},{round(1000 * self.radius, 4)});\n"
        return content, [current_id]

    def frame_mapping(self, frame: design3d.Frame3D, side: str):
        """
        Changes frame_mapping and return a new CylindricalSurface3D.

        :param side: 'old' or 'new'
        """
        new_frame = self.frame.frame_mapping(frame, side)
        return CylindricalSurface3D(new_frame, self.radius,
                                    name=self.name)

    def rectangular_cut(self, theta1: float, theta2: float,
                        param_z1: float, param_z2: float, name: str = ''):
        """Deprecated method, Use CylindricalFace3D from_surface_rectangular_cut method."""
        raise AttributeError('Use CylindricalFace3D from_surface_rectangular_cut method')

    def rotation(self, center: design3d.Point3D, axis: design3d.Vector3D, angle: float):
        """
        CylindricalFace3D rotation.

        :param center: rotation center.
        :param axis: rotation axis.
        :param angle: angle rotation.
        :return: a new rotated Plane3D.
        """
        new_frame = self.frame.rotation(center=center, axis=axis,
                                        angle=angle)
        return CylindricalSurface3D(new_frame, self.radius)

    def translation(self, offset: design3d.Vector3D):
        """
        CylindricalFace3D translation.

        :param offset: translation vector.
        :return: A new translated CylindricalFace3D.
        """
        return CylindricalSurface3D(self.frame.translation(offset), self.radius)

    def grid3d(self, grid2d: grid.Grid2D):
        """
        Generate 3d grid points of a Cylindrical surface, based on a Grid2D.

        """

        points_2d = grid2d.points
        points_3d = [self.point2d_to_3d(point2d) for point2d in points_2d]

        return points_3d

    def line_intersections(self, line: curves.Line3D):
        """Gets intersections between a line and a Cylindrical Surface 3D."""
        line_2d = line.to_2d(self.frame.origin, self.frame.u, self.frame.v)
        if line_2d is None:
            return []
        origin2d = self.frame.origin.to_2d(self.frame.origin, self.frame.u, self.frame.v)
        distance_line2d_to_origin = line_2d.point_distance(origin2d)
        if distance_line2d_to_origin > self.radius:
            return []
        a_prime = line_2d.point1
        b_prime = line_2d.point2
        a_prime_minus_b_prime = a_prime - b_prime
        t_param = a_prime.dot(a_prime_minus_b_prime) / a_prime_minus_b_prime.dot(a_prime_minus_b_prime)
        k_param = math.sqrt(
            (self.radius ** 2 - distance_line2d_to_origin ** 2) / a_prime_minus_b_prime.dot(a_prime_minus_b_prime))
        intersection1 = line.point1 + (t_param + k_param) * (line.direction_vector())
        intersection2 = line.point1 + (t_param - k_param) * (line.direction_vector())
        if intersection1 == intersection2:
            return [intersection1]

        return [intersection1, intersection2]

    def parallel_plane_intersection(self, plane3d):
        """
        Cylinder plane intersections when plane's normal is perpendicular with the cylinder axis.

        :param plane3d: intersecting plane
        :return: list of intersecting curves
        """
        distance_plane_cylinder_axis = plane3d.point_distance(self.frame.origin)
        if distance_plane_cylinder_axis > self.radius:
            return []
        if math.isclose(self.frame.w.dot(plane3d.frame.u), 0, abs_tol=1e-6):
            line = curves.Line3D(plane3d.frame.origin, plane3d.frame.origin + plane3d.frame.u)
        else:
            line = curves.Line3D(plane3d.frame.origin, plane3d.frame.origin + plane3d.frame.v)
        line_intersections = self.line_intersections(line)
        lines = []
        for intersection in line_intersections:
            lines.append(curves.Line3D(intersection, intersection + self.frame.w))
        return lines

    def perpendicular_plane_intersection(self, plane3d):
        """
        Cylinder plane intersections when plane's normal is parallel with the cylinder axis.

        :param plane3d: intersecting plane
        :return: list of intersecting curves
        """
        line = curves.Line3D(self.frame.origin, self.frame.origin + self.frame.w)
        center3d_plane = plane3d.line_intersections(line)[0]
        circle3d = curves.Circle3D(design3d.Frame3D(center3d_plane, plane3d.frame.u,
                                                   plane3d.frame.v, plane3d.frame.w), self.radius)
        return [circle3d]

    def concurrent_plane_intersection(self, plane3d: Plane3D):
        """
        Cylindrical plane intersections when plane's normal is concurrent with the cone's axis, but not orthogonal.

        :param plane3d: intersecting plane.
        :return: list of intersecting curves.
        """
        plane_normal = self.frame.w.cross(plane3d.frame.w)
        plane2 = Plane3D.from_normal(self.frame.origin, plane_normal)
        plane2_plane3d_intersections = plane3d.plane_intersections(plane2)
        line_intersections = self.line_intersections(plane2_plane3d_intersections[0])
        if not line_intersections:
            return []
        ellipse_center = (line_intersections[0] + line_intersections[1]) / 2
        line2 = curves.Line3D.from_point_and_vector(ellipse_center, plane_normal)
        line_intersections2 = self.line_intersections(line2)
        major_dir = (line_intersections[0] - ellipse_center).unit_vector()
        major_axis = ellipse_center.point_distance(line_intersections[0])
        minor_dir = (line_intersections2[0] - ellipse_center).unit_vector()
        minor_axis = ellipse_center.point_distance(line_intersections2[0])
        if minor_axis > major_axis:
            major_axis, minor_axis = minor_axis, major_axis
            major_dir, minor_dir = minor_dir, major_dir
        ellipse = curves.Ellipse3D(major_axis, minor_axis,
                                   design3d.Frame3D(ellipse_center, major_dir,
                                                   minor_dir, plane3d.frame.w))
        return [ellipse]

    def plane_intersections(self, plane3d):
        """
        Cylinder intersections with a plane.

        :param plane3d: intersecting plane.
        :return: list of intersecting curves.
        """
        if math.isclose(abs(plane3d.frame.w.dot(self.frame.w)), 0, abs_tol=1e-6):
            return self.parallel_plane_intersection(plane3d)
        if math.isclose(abs(plane3d.frame.w.dot(self.frame.w)), 1, abs_tol=1e-6):
            return self.perpendicular_plane_intersection(plane3d)
        return self.concurrent_plane_intersection(plane3d)

    def conicalsurface_intersections(self, conical_surface: 'ConicalSurface3D'):
        """
        Cylinder Surface intersections with a Conical surface.

        :param conical_surface: intersecting plane.
        :return: list of intersecting curves.
        """

        def _list_generatrices_intersections(surface, other_surface):
            linesegments = other_surface.get_generatrices(50, 2)
            all_generatrices_intersecting = True
            lists_intersections = [[], []]
            for generatrix in linesegments:
                linseg_intersections = surface.line_intersections(generatrix.line)
                if not linseg_intersections:
                    all_generatrices_intersecting = False
                for index, point in enumerate(linseg_intersections):
                    if other_surface.point_distance(point) < 1e-6 and \
                            not point.in_list(lists_intersections[index]):
                        lists_intersections[index].append(point)
            return lists_intersections, all_generatrices_intersecting

        cone_generatrices_point_intersections, all_cone_generatrices_intersecting_cylinder = \
            _list_generatrices_intersections(self, conical_surface)
        cylinder_generatrices_point_intersections, all_cylinder_generatrices_intersecting_cone = \
            _list_generatrices_intersections(conical_surface, self)
        if all_cylinder_generatrices_intersecting_cone:
            intersections_points = cylinder_generatrices_point_intersections
        elif all_cone_generatrices_intersecting_cylinder:
            intersections_points = cone_generatrices_point_intersections
            if not cone_generatrices_point_intersections[1]:
                intersections_points = [[]]
                for point in (
                        cylinder_generatrices_point_intersections[0] + cylinder_generatrices_point_intersections[1] +
                        cone_generatrices_point_intersections[0] + cone_generatrices_point_intersections[1]):
                    if not point.in_list(intersections_points[0]):
                        intersections_points[0].append(point)
        elif not all_cone_generatrices_intersecting_cylinder:
            intersections_points = [[]]
            for point in (cylinder_generatrices_point_intersections[0] + cylinder_generatrices_point_intersections[1] +
                          cone_generatrices_point_intersections[0] + cone_generatrices_point_intersections[1]):
                if not point.in_list(intersections_points[0]):
                    intersections_points[0].append(point)
        list_curves = []
        for list_points in intersections_points:
            order_ed_points = d3d_common_operations.order_points_list_for_nearest_neighbor(list_points)
            bspline = edges.BSplineCurve3D.from_points_interpolation(order_ed_points + [order_ed_points[0]], 4,
                                                                     centripetal=False)
            list_curves.append(bspline)
        return list_curves

    def is_coincident(self, surface3d, abs_tol: float = 1e-6):
        """
        Verifies if two CylindricalSurfaces are coincident.

        :param surface3d: surface to verify.
        :param abs_tol: tolerance.
        :return: True if they are coincident, False otherwise.
        """
        if not isinstance(self, surface3d.__class__):
            return False
        line = curves.Line3D.from_point_and_vector(surface3d.frame.origin, surface3d.frame.w)
        distance_to_self_origin = line.point_distance(self.frame.origin)

        if math.isclose(abs(self.frame.w.dot(surface3d.frame.w)), 1.0, abs_tol=abs_tol) and \
                math.isclose(distance_to_self_origin, 0.0, abs_tol=abs_tol) and self.radius == surface3d.radius:
            return True
        return False

    def point_belongs(self, point3d, abs_tol: float = 1e-5):
        """
        Verifies if a given point is on the CylindricalSurface3D.

        :param point3d: Point to verify.
        :param abs_tol: Tolerance.
        :return: True if point on surface, False otherwise.
        """
        new_point = self.frame.global_to_local_coordinates(point3d)
        if math.isclose(new_point.x ** 2 + new_point.y ** 2, self.radius ** 2, abs_tol=abs_tol):
            return True
        return False

    def _sphere_cylinder_tangent_intersections(self, frame, distance_axis_sphere_center):
        """
        Gets the intersections between a sphere tangent to the cylinder.

        :param frame: frame for local calculations. Frame is such that w is the cylinder axis,
        and u passes through the sphere's center.
        :param distance_axis_sphere_center: distance of sphere's center to cylinder axis.
        :return: return a list with the intersecting curves.
        """
        curves_ = []
        for phi_range in [(0, math.pi), (math.pi, 2 * math.pi), (2 * math.pi, 3 * math.pi),
                          (3 * math.pi, 4 * math.pi)]:
            phi = np.linspace(phi_range[0], phi_range[1], 100)
            intersection_points = [design3d.Point3D(x_comp, y_comp, z_comp)
                                   for x_comp, y_comp, z_comp in zip(
                    self.radius * np.cos(phi), self.radius * np.sin(phi),
                    2 * math.sqrt(distance_axis_sphere_center * self.radius) * np.cos(phi / 2))]
            bspline = edges.BSplineCurve3D.from_points_interpolation(intersection_points, 4, centripetal=False)
            curves_.append(bspline)
        global_intersections = [edge.frame_mapping(frame, 'old') for edge in curves_]
        return global_intersections

    def _helper_spherical_intersections_points(self, spherical_surface, distance_axis_sphere_center):
        """
        Helper method to get spherical intersections points.

        :param spherical_surface: spherical surface.
        :param distance_axis_sphere_center: distance cylinder axis to sphere center.
        :return: intersection points.
        """
        b = (spherical_surface.radius ** 2 - self.radius ** 2 -
             distance_axis_sphere_center ** 2) / (2 * distance_axis_sphere_center)

        if spherical_surface.radius > self.radius + distance_axis_sphere_center:
            phi_0, phi_1, two_curves = 0, 2 * math.pi, True
        else:
            phi_0 = math.acos(-b / self.radius)
            phi_1 = phi_0 - 0.000001
            phi_0 = -phi_0 + 0.000001
            two_curves = False

        phi = np.linspace(phi_0, phi_1, 400)
        x_components = self.radius * np.cos(phi)
        y_components = self.radius * np.sin(phi)
        z_components1 = np.sqrt(2 * distance_axis_sphere_center * (b + x_components))

        inters_points = [[design3d.Point3D(x_comp, y_comp, z_comp)
                          for x_comp, y_comp, z_comp in zip(x_components, y_components, z_components1)],
                         [design3d.Point3D(x_comp, y_comp, -z_comp)
                          for x_comp, y_comp, z_comp in zip(x_components, y_components, z_components1)]]
        if not two_curves:
            inters_points = d3d_common_operations.separate_points_by_closeness(inters_points[0] + inters_points[1])
        return inters_points

    def sphericalsurface_intersections(self, spherical_surface: 'SphericalSurface3D'):
        """
        Cylinder Surface intersections with a Spherical surface.

        :param spherical_surface: intersecting sphere.
        :return: list of intersecting curves.
        """
        line_axis = curves.Line3D.from_point_and_vector(self.frame.origin, self.frame.w)
        distance_axis_sphere_center = line_axis.point_distance(spherical_surface.frame.origin)

        if distance_axis_sphere_center < self.radius:
            if distance_axis_sphere_center + spherical_surface.radius < self.radius:
                return []
            if math.isclose(distance_axis_sphere_center, 0.0, abs_tol=1e-6):
                if math.isclose(self.radius, spherical_surface.radius):
                    return [spherical_surface.get_circle_at_z(0)]
                z_plane_position = math.sqrt(spherical_surface.radius ** 2 - self.radius ** 2)
                circle1 = spherical_surface.get_circle_at_z(z_plane_position)
                circle2 = spherical_surface.get_circle_at_z(-z_plane_position)
                return [circle1, circle2]

        if distance_axis_sphere_center - spherical_surface.radius > self.radius:
            return []

        point_projection, _ = line_axis.point_projection(spherical_surface.frame.origin)
        vector = (spherical_surface.frame.origin - point_projection).unit_vector()
        frame = design3d.Frame3D(point_projection, vector, self.frame.w.cross(vector), self.frame.w)

        if math.isclose(distance_axis_sphere_center + self.radius, spherical_surface.radius, abs_tol=1e-6):
            return self._sphere_cylinder_tangent_intersections(frame, distance_axis_sphere_center)

        inters_points = self._helper_spherical_intersections_points(spherical_surface, distance_axis_sphere_center)

        curves_ = [edges.BSplineCurve3D.from_points_interpolation(points, 4, centripetal=False)
                   for points in inters_points]
        return [edge.frame_mapping(frame, 'old') for edge in curves_]

    def _cylindrical_intersection_points(self, cylindricalsurface: 'SphericalSurface3D'):
        """
        Gets the points of intersections between two cylindrical surfaces.

        :param cylindricalsurface: other Cylindrical surface 3d.
        :return: points of intersections.
        """
        cyl_generatrices = self.get_generatrices(200, self.radius * 10) + \
                           self.get_circle_generatrices(200, self.radius * 10)
        intersection_points = []
        for gene in cyl_generatrices:
            intersections = cylindricalsurface.edge_intersections(gene)
            for intersection in intersections:
                if not design3d.core.point_in_list(intersection, intersection_points):
                    intersection_points.append(intersection)
        return intersection_points

    def cylindricalsurface_intersections(self, cylindricalsurface: 'CylindricalSurface3D'):
        """
        Gets intersections between two cylindrical surfaces 3d.

        :param cylindricalsurface: other cylindrical surface.
        :return: a list containing the resulting intersections, if there are any.
        """
        curves_ = []
        if self.frame.w.is_colinear_to(cylindricalsurface.frame.w):
            circle1 = curves.Circle3D(self.frame, self.radius).to_2d(self.frame.origin, self.frame.u, self.frame.v)
            circle2 = curves.Circle3D(cylindricalsurface.frame, cylindricalsurface.radius).to_2d(
                self.frame.origin, self.frame.u, self.frame.v)
            circle2d_intersections = circle1.circle_intersections(circle2)
            for point in circle2d_intersections:
                point3d = point.to_3d(self.frame.origin, self.frame.u, self.frame.v)
                curves_.append(curves.Line3D.from_point_and_vector(point3d, self.frame.w))
            return curves_

        intersection_points = self._cylindrical_intersection_points(cylindricalsurface)
        if not intersection_points:
            return []
        inters_points = d3d_common_operations.separate_points_by_closeness(intersection_points)
        for list_points in inters_points:
            bspline = edges.BSplineCurve3D.from_points_interpolation(list_points, 4, centripetal=False)
            curves_.append(bspline)
        return curves_

    def u_iso(self, u: float) -> curves.Line3D:
        """
        Returns the u-iso curve of the surface.

        :param u: The value of u where to extract the curve.
        :type u: float
        :return: A line 3D
        :rtype: :class:`curves.Line3D`
        """

        point_at_u = self.point2d_to_3d(design3d.Point2D(u, 0.0))

        return curves.Line3D.from_point_and_vector(point_at_u, self.frame.w)

    def v_iso(self, v: float) -> curves.Circle3D:
        """
        Returns the v-iso curve of the surface.

        :param v: The value of u where to extract the curve.
        :type v: float
        :return: A Circle 3D
        :rtype: :class:`curves.Circle3D`
        """
        frame = self.frame.translation(self.frame.w * v)
        return curves.Circle3D(frame, self.radius)

    def normal_at_point(self, point: design3d.Point3D):
        """
        Gets normal vector at given point on the surface.

        :param point: point to be verified.
        :return: normal
        """
        if not self.point_belongs(point):
            raise ValueError('Point given not on surface.')
        theta, _ = self.point3d_to_2d(point)
        normal = math.cos(theta) * self.frame.u + math.sin(theta) * self.frame.v
        return normal


class ToroidalSurface3D(UVPeriodicalSurface):
    """
    The local plane is defined by (theta, phi).

    Theta is the angle around the big (R) circle and phi around the small (r).

    :param frame: Tore's frame: origin is the center, u is pointing at theta=0.
    :param major_radius: Tore's radius.
    :param r: Circle to revolute radius.

    See Also Definitions of R and r according to https://en.wikipedia.org/wiki/Torus.

    """
    face_class = 'ToroidalFace3D'
    x_periodicity = design3d.TWO_PI
    y_periodicity = design3d.TWO_PI

    def __init__(self, frame: design3d.Frame3D, major_radius: float, minor_radius: float, name: str = ''):
        self.major_radius = major_radius
        self.minor_radius = minor_radius
        UVPeriodicalSurface.__init__(self, frame=frame, name=name)

        self._bbox = None

    def __hash__(self):
        return hash((self.__class__.__name__, self.frame, self.major_radius, self.minor_radius))

    def __eq__(self, other):
        if self.__class__.__name__ != other.__class__.__name__:
            return False
        if self.frame == other.frame and \
                self.major_radius == other.major_radius and \
                self.minor_radius == other.minor_radius:
            return True
        return False

    @property
    def u_domain(self):
        """The parametric domain of the surface in the U direction."""
        return -math.pi, math.pi

    @property
    def v_domain(self):
        """The parametric domain of the surface in the V direction."""
        return -math.pi, math.pi

    @cached_property
    def outer_radius(self):
        """Get torus outer radius."""
        return self.major_radius + self.minor_radius

    @cached_property
    def inner_radius(self):
        """Get torus inner radius."""
        return self.major_radius - self.minor_radius

    def torus_arcs(self, number_arcs: int = 50):
        """
        Retrieve torus arcs representing the generatrices of a Torus.

        :param number_arcs: The number of generatrices to generate. Default is 30
        :type number_arcs: int
        :return: A list of Circle3D instances representing the generatrices of the torus.
        :rtype: List[Circle3D]
        """
        return [self.u_iso(i / number_arcs * design3d.TWO_PI) for i in range(number_arcs)]

    def _torus_circle_generatrices_xy(self, number_arcs: int = 50):
        """
        Retrieve circle generatrices in cutting planes parallel to the XY plane of the torus local system.

        :param number_arcs: The number of generatrices to generate. Default is 50.
        :type number_arcs: int
        :return: A list of Circle3D instances representing the generatrices in the XY plane.
        :rtype: List[Circle3D]
        """
        initial_point = self.frame.origin
        circles = []
        phis = np.linspace(-0.5 * math.pi, 0.5 * math.pi, number_arcs)
        z_positions = self.minor_radius * np.sin(phis)
        r_cossines = self.minor_radius * np.cos(phis)
        radiuses1 = self.major_radius - r_cossines
        radiuses2 = self.major_radius + r_cossines
        for i, radius1, radius2 in zip(z_positions, radiuses1, radiuses2):
            i_center = initial_point.translation(self.frame.w * i)
            frame = design3d.Frame3D(i_center, self.frame.u, self.frame.v, self.frame.w)
            circles.append(curves.Circle3D(frame, radius1))
            if radius1 == radius2:
                continue
            circles.append(curves.Circle3D(frame, radius2))
        return circles

    @classmethod
    def dict_to_object(cls, dict_, **kwargs) -> 'ToroidalSurface3D':
        """Creates a ToroidalSurface3D from a dictionary."""
        frame = design3d.Frame3D.dict_to_object(dict_['frame'])
        name = dict_['name']
        if 'tore_radius' in dict_:
            # fix done 26/10/2023
            major_radius = dict_['tore_radius']
            minor_radius = dict_['small_radius']
        else:
            major_radius = dict_['major_radius']
            minor_radius = dict_['minor_radius']
        return cls(frame, major_radius, minor_radius, name)

    @property
    def bounding_box(self):
        """
        Returns the surface bounding box.
        """
        if not self._bbox:
            self._bbox = self._bounding_box()
        return self._bbox

    def _bounding_box(self):
        """
        Calculates the BoundingBox for the complete Toroidal Surface 3D.

        :return: surface bounding box.
        """
        distance = self.major_radius + self.minor_radius
        point1 = self.frame.origin + \
                 self.frame.u * distance + self.frame.v * distance + self.frame.w * self.minor_radius
        point2 = self.frame.origin + \
                 self.frame.u * distance + self.frame.v * distance - self.frame.w * self.minor_radius
        point3 = self.frame.origin + \
                 self.frame.u * distance - self.frame.v * distance + self.frame.w * self.minor_radius
        point4 = self.frame.origin + \
                 self.frame.u * distance - self.frame.v * distance - self.frame.w * self.minor_radius
        point5 = self.frame.origin - \
                 self.frame.u * distance + self.frame.v * distance + self.frame.w * self.minor_radius
        point6 = self.frame.origin - \
                 self.frame.u * distance + self.frame.v * distance - self.frame.w * self.minor_radius
        point7 = self.frame.origin - \
                 self.frame.u * distance - self.frame.v * distance + self.frame.w * self.minor_radius
        point8 = self.frame.origin - \
                 self.frame.u * distance - self.frame.v * distance - self.frame.w * self.minor_radius

        return design3d.core.BoundingBox.from_points(
            [point1, point2, point3, point4, point5, point6, point7, point8])

    def point2d_to_3d(self, point2d: design3d.Point2D):
        """
        Coverts a parametric coordinate on the surface into a 3D spatial point (x, y, z).

        :param point2d: Point at the ToroidalSuface3D
        :type point2d: `design3d.`Point2D`
        """
        theta, phi = point2d

        x = (self.major_radius + self.minor_radius * math.cos(phi)) * math.cos(theta)
        y = (self.major_radius + self.minor_radius * math.cos(phi)) * math.sin(theta)
        z = self.minor_radius * math.sin(phi)
        return self.frame.local_to_global_coordinates(design3d.Point3D(x, y, z))

    def point3d_to_2d(self, point3d):
        """
        Transform a 3D spatial point (x, y, z) into a 2D spherical parametric point (theta, phi).
        """
        x, y, z = self.frame.global_to_local_coordinates(point3d)
        z = min(self.minor_radius, max(-self.minor_radius, z))

        # Do not delete this, mathematical problem when x and y close to zero (should be zero) but not 0
        # Generally this is related to uncertainty of step files.

        if abs(x) < 1e-12:
            x = 0.0
        if abs(y) < 1e-12:
            y = 0.0
        if abs(z) < 1e-6:
            z = 0.0

        z_r = z / self.minor_radius
        phi = math.asin(z_r)
        if abs(phi) < 1e-9:
            phi = 0

        u = self.major_radius + math.sqrt((self.minor_radius ** 2) - (z ** 2))
        u1, u2 = x / u, y / u
        theta = math.atan2(u2, u1)

        vector_to_tube_center = design3d.Vector3D(abs(self.major_radius) * math.cos(theta),
                                                 abs(self.major_radius) * math.sin(theta), 0)
        vector_from_tube_center_to_point = design3d.Vector3D(x, y, z) - vector_to_tube_center
        phi2 = design3d.geometry.vectors3d_angle(vector_to_tube_center, vector_from_tube_center_to_point)

        if phi >= 0 and phi2 > 0.5 * math.pi:
            phi = math.pi - phi
        elif phi < 0 and phi2 > 0.5 * math.pi:
            phi = -math.pi - phi
        if abs(theta) < 1e-9:
            theta = 0.0
        if abs(phi) < 1e-9:
            phi = 0.0
        if self.major_radius < self.minor_radius:
            phi_self_intersection = math.acos(-self.major_radius / self.minor_radius)
            if abs(phi) > phi_self_intersection:
                if theta >= 0.0:
                    theta -= math.pi
                else:
                    theta += math.pi
        return design3d.Point2D(theta, phi)

    def parametric_points_to_3d(self, points: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Transform parametric coordinates to 3D points on the toroidal surface.

        Given a set of parametric coordinates `(u, v)` representing points on the surface,
        this method returns the corresponding 3D points on the toroidal surface.

        :param points: Parametric coordinates in the form of a numpy array with shape (n, 2),
                       where `n` is the number of points, and each row corresponds to `(u, v)`.
        :type points: numpy.ndarray[np.float64]

        :return: Array of 3D points representing the toroidal surface in Cartesian coordinates.
        :rtype: numpy.ndarray[np.float64]
        """
        center = np.array(self.frame.origin)
        x = np.array([self.frame.u[0], self.frame.u[1], self.frame.u[2]])
        y = np.array([self.frame.v[0], self.frame.v[1], self.frame.v[2]])
        z = np.array([self.frame.w[0], self.frame.w[1], self.frame.w[2]])

        points = points.reshape(-1, 2, 1)

        u_values = points[:, 0]
        v_values = points[:, 1]

        common_term = self.major_radius + self.minor_radius * np.cos(v_values)
        x_component = np.cos(u_values) * x
        y_component = np.sin(u_values) * y
        z_component = self.minor_radius * np.sin(v_values) * z

        return center + common_term * (x_component + y_component) + z_component

    @classmethod
    def from_step(cls, arguments, object_dict, **kwargs):
        """
        Converts a step primitive to a ToroidalSurface3D.

        :param arguments: The arguments of the step primitive.
        :type arguments: list
        :param object_dict: The dictionary containing all the step primitives
            that have already been instantiated.
        :type object_dict: dict
        :return: The corresponding ToroidalSurface3D object.
        :rtype: :class:`design3d.faces.ToroidalSurface3D`
        """

        length_conversion_factor = kwargs.get("length_conversion_factor", 1)

        frame = object_dict[arguments[1]]
        rcenter = abs(float(arguments[2])) * length_conversion_factor
        rcircle = abs(float(arguments[3])) * length_conversion_factor
        return cls(frame, rcenter, rcircle, arguments[0][1:-1])

    def to_step(self, current_id):
        """
        Converts the object to a STEP representation.

        :param current_id: The ID of the last written primitive.
        :type current_id: int
        :return: The STEP representation of the object and the last ID.
        :rtype: tuple[str, list[int]]
        """
        content, frame_id = self.frame.to_step(current_id)
        current_id = frame_id + 1
        content += f"#{current_id} = TOROIDAL_SURFACE('{self.name}',#{frame_id}," \
                   f"{round(1000 * self.major_radius, 4)},{round(1000 * self.minor_radius, 4)});\n"
        return content, [current_id]

    def frame_mapping(self, frame: design3d.Frame3D, side: str):
        """
        Changes frame_mapping and return a new ToroidalSurface3D.

        :param frame: The new frame to map to.
        :type frame: `design3d.Frame3D
        :param side: Indicates whether the frame should be mapped to the 'old' or 'new' frame.
            Acceptable values are 'old' or 'new'.
        :type side: str
        """
        new_frame = self.frame.frame_mapping(frame, side)
        return ToroidalSurface3D(new_frame, self.major_radius, self.minor_radius, name=self.name)

    def rectangular_cut(self, theta1: float, theta2: float, phi1: float, phi2: float, name: str = ""):
        """Deprecated method, Use ToroidalFace3D from_surface_rectangular_cut method."""
        raise AttributeError('Use ToroidalFace3D from_surface_rectangular_cut method')

    def bsplinecurve2d_to_3d(self, bspline_curve2d):
        """
        Converts the parametric boundary representation into a 3D primitive.
        """
        n = len(bspline_curve2d.control_points)
        points = [self.point2d_to_3d(p)
                  for p in bspline_curve2d.discretization_points(number_points=n)]
        return [edges.BSplineCurve3D.from_points_interpolation(points, bspline_curve2d.degree, centripetal=True)]

    def _helper_arc3d_to_2d_periodicity_verifications(self, arc3d, start, end):
        """
        Verifies if arc 3D contains discontinuity and undefined start/end points on parametric domain.
        """

        point_theta_discontinuity = self.point2d_to_3d(design3d.Point2D(math.pi, start.y))
        theta_discontinuity = (arc3d.point_belongs(point_theta_discontinuity) and
                               not arc3d.is_point_edge_extremity(point_theta_discontinuity) and
                               not self.frame.w.is_perpendicular_to(arc3d.frame.w))
        point_phi_discontinuity = self.point2d_to_3d(design3d.Point2D(start.x, math.pi))
        phi_discontinuity = (arc3d.point_belongs(point_phi_discontinuity) and
                             not arc3d.is_point_edge_extremity(point_phi_discontinuity) and
                             not self.frame.w.is_colinear_to(arc3d.frame.w))
        undefined_start_theta = arc3d.start.is_close(point_theta_discontinuity) or abs(start.x) == math.pi
        undefined_end_theta = arc3d.end.is_close(point_theta_discontinuity) or abs(end.x) == math.pi
        undefined_start_phi = arc3d.start.is_close(point_phi_discontinuity) or start.y == math.pi
        undefined_end_phi = arc3d.end.is_close(point_phi_discontinuity) or end.y == math.pi

        return theta_discontinuity, phi_discontinuity, undefined_start_theta, undefined_end_theta, \
            undefined_start_phi, undefined_end_phi

    def fullarc3d_to_2d(self, fullarc3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        start = self.point3d_to_2d(fullarc3d.start)
        end = self.point3d_to_2d(fullarc3d.end)
        point_after_start, point_before_end = self._reference_points(fullarc3d)
        theta_discontinuity, phi_discontinuity, undefined_start_theta, undefined_end_theta, \
            undefined_start_phi, undefined_end_phi = self._helper_arc3d_to_2d_periodicity_verifications(
            fullarc3d, start, end)
        start, end = d3d_parametric.arc3d_to_toroidal_coordinates_verification(
            [start, end],
            [undefined_start_theta, undefined_end_theta, undefined_start_phi, undefined_end_phi],
            [point_after_start, point_before_end],
            [theta_discontinuity, phi_discontinuity])

        theta1, phi1 = start
        theta3, phi3 = point_after_start
        if self.frame.w.is_colinear_to(fullarc3d.circle.normal, abs_tol=1e-4):
            if theta1 > theta3:
                end = design3d.Point2D(theta1 - design3d.TWO_PI, phi1)
            elif theta1 < theta3:
                end = design3d.Point2D(theta1 + design3d.TWO_PI, phi1)
            return [edges.LineSegment2D(start, end)]
        if phi1 > phi3:
            end = design3d.Point2D(theta1, phi1 - design3d.TWO_PI)
        elif phi1 < phi3:
            end = design3d.Point2D(theta1, phi1 + design3d.TWO_PI)
        return [edges.LineSegment2D(start, end)]

    def arc3d_to_2d(self, arc3d):
        """
        Converts the arc from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        start = self.point3d_to_2d(arc3d.start)
        end = self.point3d_to_2d(arc3d.end)

        point_after_start, point_before_end = self._reference_points(arc3d)
        theta_discontinuity, phi_discontinuity, undefined_start_theta, undefined_end_theta, \
            undefined_start_phi, undefined_end_phi = self._helper_arc3d_to_2d_periodicity_verifications(arc3d,
                                                                                                        start, end)
        start, end = d3d_parametric.arc3d_to_toroidal_coordinates_verification(
            [start, end],
            [undefined_start_theta, undefined_end_theta, undefined_start_phi, undefined_end_phi],
            [point_after_start, point_before_end],
            [theta_discontinuity, phi_discontinuity])
        return [edges.LineSegment2D(start, end)]

    def bsplinecurve3d_to_2d(self, bspline_curve3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        point_after_start, point_before_end = self._reference_points(bspline_curve3d)
        theta3, phi3 = point_after_start
        theta4, phi4 = point_before_end
        n = bspline_curve3d.ctrlpts.shape[0]
        points3d = bspline_curve3d.discretization_points(number_points=n)
        points = [self.point3d_to_2d(p) for p in points3d]
        theta1, phi1 = points[0]
        theta2, phi2 = points[-1]

        # Verify if theta1 or theta2 point should be -pi because atan2() -> ]-pi, pi]
        if abs(theta1) == math.pi:
            theta1 = repair_start_end_angle_periodicity(theta1, theta3)
        if abs(theta2) == math.pi:
            theta2 = repair_start_end_angle_periodicity(theta2, theta4)

        # Verify if phi1 or phi2 point should be -pi because phi -> ]-pi, pi]
        if abs(phi1) == math.pi:
            phi1 = repair_start_end_angle_periodicity(phi1, phi3)
        if abs(phi2) == math.pi:
            phi2 = repair_start_end_angle_periodicity(phi2, phi4)

        points[0] = design3d.Point2D(theta1, phi1)
        points[-1] = design3d.Point2D(theta2, phi2)

        theta_list = [point.x for point in points]
        phi_list = [point.y for point in points]
        theta_discontinuity, indexes_theta_discontinuity = angle_discontinuity(theta_list)
        phi_discontinuity, indexes_phi_discontinuity = angle_discontinuity(phi_list)

        if theta_discontinuity:
            points = self._fix_angle_discontinuity_on_discretization_points(points,
                                                                            indexes_theta_discontinuity, "x")
        if phi_discontinuity:
            points = self._fix_angle_discontinuity_on_discretization_points(points,
                                                                            indexes_phi_discontinuity, "y")
        points = verify_repeated_parametric_points(points)
        return [edges.BSplineCurve2D.from_points_interpolation(points, bspline_curve3d.degree)]

    def triangulation(self):
        """
        Triangulation.

        :rtype: display.Mesh3D
        """
        face = self.rectangular_cut(0, design3d.TWO_PI, 0, design3d.TWO_PI)
        return face.triangulation()

    def translation(self, offset: design3d.Vector3D):
        """
        ToroidalSurface3D translation.

        :param offset: translation vector
        :return: A new translated ToroidalSurface3D
        """
        return ToroidalSurface3D(self.frame.translation(
            offset), self.major_radius, self.minor_radius)

    def rotation(self, center: design3d.Point3D, axis: design3d.Vector3D, angle: float):
        """
        ToroidalSurface3D rotation.

        :param center: rotation center.
        :param axis: rotation axis.
        :param angle: angle rotation.
        :return: a new rotated ToroidalSurface3D.
        """
        new_frame = self.frame.rotation(center=center, axis=axis,
                                        angle=angle)
        return self.__class__(new_frame, self.major_radius, self.minor_radius)

    def plot(self, ax=None, edge_style: EdgeStyle = EdgeStyle(color='grey', alpha=0.5), **kwargs):
        """Plot torus arcs."""
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')

        self.frame.plot(ax=ax, ratio=self.major_radius)
        circles = self.torus_arcs(100) + self._torus_circle_generatrices_xy(30)
        for circle in circles:
            circle.plot(ax=ax, edge_style=edge_style)

        return ax

    def point_projection(self, point3d):
        """
        Returns the projection of the point on the toroidal surface.

        :param point3d: Point to project.
        :type point3d: design3d.Point3D
        :return: A point on the surface
        :rtype: design3d.Point3D
        """
        x, y, z = self.frame.global_to_local_coordinates(point3d)

        if abs(x) < 1e-12:
            x = 0
        if abs(y) < 1e-12:
            y = 0

        theta = math.atan2(y, x)

        vector_to_tube_center = design3d.Vector3D(self.major_radius * math.cos(theta),
                                                 self.major_radius * math.sin(theta), 0)
        vector_from_tube_center_to_point = design3d.Vector3D(x, y, z) - vector_to_tube_center
        phi = design3d.geometry.vectors3d_angle(vector_to_tube_center, vector_from_tube_center_to_point)
        if z < 0:
            phi = 2 * math.pi - phi
        if abs(theta) < 1e-9:
            theta = 0.0
        if abs(phi) < 1e-9:
            phi = 0.0
        return self.point2d_to_3d(design3d.Point2D(theta, phi))

    def _reference_points(self, edge):
        """
        Helper function to return points of reference on the edge to fix some parametric periodical discontinuities.
        """
        length = edge.length()
        point_after_start = self.point3d_to_2d(edge.point_at_abscissa(0.01 * length))
        point_before_end = self.point3d_to_2d(edge.point_at_abscissa(0.98 * length))
        theta3, phi3 = point_after_start
        theta4, phi4 = point_before_end
        if abs(theta3) == math.pi or abs(theta3) == 0.5 * math.pi or \
                abs(phi3) == math.pi or abs(phi3) == 0.5 * math.pi:
            point_after_start = self.point3d_to_2d(edge.point_at_abscissa(0.02 * length))
        if abs(theta4) == math.pi or abs(theta4) == 0.5 * math.pi or \
                abs(phi4) == math.pi or abs(phi4) == 0.5 * math.pi:
            point_before_end = self.point3d_to_2d(edge.point_at_abscissa(0.97 * length))
        return point_after_start, point_before_end

    def _get_line_intersections_solution_roots(self, line):
        """
        Line intersections helper: get roots.

        :param line: other line.
        :return: roots.
        """
        vector = line.unit_direction_vector()
        coeff_a = vector.x ** 2 + vector.y ** 2 + vector.z ** 2
        coeff_b = 2 * (line.point1.x * vector.x + line.point1.y * vector.y + line.point1.z * vector.z)
        coeff_c = (line.point1.x ** 2 + line.point1.y ** 2 + line.point1.z ** 2
                   + self.major_radius ** 2 - self.minor_radius ** 2)
        coeff_d = vector.x ** 2 + vector.y ** 2
        coeff_e = 2 * (line.point1.x * vector.x + line.point1.y * vector.y)
        coeff_f = line.point1.x ** 2 + line.point1.y ** 2
        solutions = np.roots([(coeff_a ** 2), 2 * coeff_a * coeff_b,
                              (2 * coeff_a * coeff_c + coeff_b ** 2 - 4 * coeff_d * self.major_radius ** 2),
                              (2 * coeff_b * coeff_c - 4 * self.major_radius ** 2 * coeff_e),
                              coeff_c ** 2 - 4 * self.major_radius ** 2 * coeff_f])
        return solutions

    def line_intersections(self, line: curves.Line3D):
        """
        Calculates the intersections between the toroidal surface and an infinite line.

        :param line: other line.
        :return: intersections.
        """
        if not self.frame.origin.is_close(design3d.O3D) or not self.frame.w.is_close(design3d.Z3D):
            frame_mapped_surface = self.frame_mapping(self.frame, 'new')
            frame_mapped_line = line.frame_mapping(self.frame, 'new')
            local_intersections = frame_mapped_surface.line_intersections(frame_mapped_line)
            global_intersections = [self.frame.local_to_global_coordinates(point) for point in local_intersections]
            return global_intersections

        vector = line.unit_direction_vector()
        solutions = self._get_line_intersections_solution_roots(line)
        intersections = []
        for sol_param in sorted(solutions):
            if isinstance(sol_param, np.complex128):
                if sol_param.imag == 0.0:
                    intersections.append(line.point1 + sol_param.real * vector)
            else:
                intersections.append(line.point1 + sol_param * vector)
        return intersections

    def circle_intersections(self, circle: curves.Circle3D):
        """
        Calculates the intersections between a toroidal surface 3d and a Circle 3D.

        :param circle: other circle to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        toroidal_plane = Plane3D(self.frame)
        if toroidal_plane.point_distance(circle.center) >= circle.radius + self.minor_radius:
            return []
        circle2_ = curves.Circle3D(self.frame, self.major_radius)
        circle_distance = circle.circle_distance(circle2_, False)
        if circle_distance > self.minor_radius:
            return []
        return self.curve_intersections(circle)

    def _helper_parallel_plane_intersections_through_origin(self, plane3d):
        """
        Helper method to get intersection between torus and plane through the origin.

        :param plane3d: other plane.
        :return: two circles.
        """
        plane1 = Plane3D(self.frame)
        plane_intersections = plane1.plane_intersections(plane3d)
        center1 = self.frame.origin + plane_intersections[0].unit_direction_vector() * self.major_radius
        center2 = self.frame.origin - plane_intersections[0].unit_direction_vector() * self.major_radius
        circle1 = curves.Circle3D(
            design3d.Frame3D(center1, plane3d.frame.u, plane3d.frame.v, plane3d.frame.w), self.minor_radius)
        circle2 = curves.Circle3D(
            design3d.Frame3D(center2, plane3d.frame.u, plane3d.frame.v, plane3d.frame.w), self.minor_radius)
        return [circle1, circle2]

    def parallel_plane_intersection(self, plane3d: Plane3D):
        """
        Toroidal plane intersections when plane's normal is perpendicular with the cylinder axis.

        :param plane3d: intersecting plane.
        :return: list of intersecting curves.
        """
        distance_plane_cylinder_axis = plane3d.point_distance(self.frame.origin)
        if distance_plane_cylinder_axis >= self.outer_radius:
            return []
        if plane3d.point_belongs(self.frame.origin):
            return self._helper_parallel_plane_intersections_through_origin(plane3d)
        if distance_plane_cylinder_axis > self.inner_radius:
            return self.concurrent_plane_intersection(plane3d, 1)
        point_projection = plane3d.point_projection(self.frame.origin)
        points = self._plane_intersection_points(plane3d)
        vector = (point_projection - self.frame.origin).unit_vector()
        frame = design3d.Frame3D(point_projection, vector, self.frame.w, vector.cross(self.frame.w))
        local_points = [frame.global_to_local_coordinates(point) for point in points]
        lists_points = [[], []]
        for i, local_point in enumerate(local_points):
            if local_point.z > 0:
                lists_points[0].append(points[i])
            elif local_point.z < 0:
                lists_points[1].append(points[i])
        if math.isclose(distance_plane_cylinder_axis, self.inner_radius, abs_tol=1e-6):
            curves_ = []
            for points in lists_points:
                points_ = d3d_common_operations.order_points_list_for_nearest_neighbor(points + [point_projection])
                points_ = points_[points_.index(point_projection):] + points_[:points_.index(point_projection)]
                edge = edges.BSplineCurve3D.from_points_interpolation(points_ + [points_[0]], 6)
                curves_.append(edge)
            return curves_
        curves_ = []
        for points in lists_points:
            points_ = d3d_common_operations.order_points_list_for_nearest_neighbor(points)
            edge = edges.BSplineCurve3D.from_points_interpolation(points_ + [points_[0]], 6)
            curves_.append(edge)
        return curves_

    def perpendicular_plane_intersection(self, plane3d):
        """
        Toroidal plane intersections when plane's normal is parallel with the cylinder axis.

        :param plane3d: intersecting plane.
        :return: list of intersecting curves.
        """
        distance_plane_cylinder_axis = plane3d.point_distance(self.frame.origin)
        if distance_plane_cylinder_axis > self.minor_radius:
            return []
        if plane3d.point_belongs(self.frame.origin):
            circle1 = curves.Circle3D(self.frame, self.outer_radius)
            circle2 = curves.Circle3D(self.frame, self.inner_radius)
            return [circle1, circle2]
        plane1 = plane3d.rotation(plane3d.frame.origin, plane3d.frame.u, math.pi / 4)
        plane_intersections = plane3d.plane_intersections(plane1)
        torus_line_intersections = self.line_intersections(plane_intersections[0])
        torus_line_intersections = plane_intersections[0].sort_points_along_curve(torus_line_intersections)
        center = plane3d.point_projection(self.frame.origin)
        if not torus_line_intersections and math.isclose(distance_plane_cylinder_axis,
                                                         self.minor_radius, abs_tol=1e-6):
            circle = curves.Circle3D(
                design3d.Frame3D(center, plane3d.frame.u, plane3d.frame.v, plane3d.frame.w), self.major_radius)
            return [circle]
        radius1 = center.point_distance(torus_line_intersections[0])
        circle1 = curves.Circle3D(
            design3d.Frame3D(center, plane3d.frame.u, plane3d.frame.v, plane3d.frame.w), radius1)
        if len(torus_line_intersections) == 4:
            radius2 = center.point_distance(torus_line_intersections[1])
            circle2 = curves.Circle3D(
                design3d.Frame3D(center,
                                plane3d.frame.u, plane3d.frame.v, plane3d.frame.w), radius2)
            return [circle1, circle2]
        return [circle1]

    def _plane_intersection_points(self, plane3d):
        """
        Gets the points of intersections between the plane and the toroidal surface.

        :param plane3d: other plane 3d.
        :return: points of intersections.
        """
        axis_angle = math.degrees(design3d.geometry.vectors3d_angle(self.frame.w, plane3d.frame.w))
        if 0 < axis_angle <= math.degrees(math.atan(self.minor_radius / self.major_radius)):
            torus_circles = self.torus_arcs(80)
        elif axis_angle < 45:
            torus_circles = self.torus_arcs(80) + self._torus_circle_generatrices_xy(80)
        else:
            torus_circles = self._torus_circle_generatrices_xy(80)
        points_intersections = []
        for arc in torus_circles:
            inters = plane3d.curve_intersections(arc)
            for i in inters:
                if not i.in_list(points_intersections):
                    points_intersections.append(i)
        return points_intersections

    def get_villarceau_circles(self, plane3d):
        """
        The concurrent intersecting plane touches the torus in two isolated points.

        :param plane3d: concurrent plane.
        :return: two circles.
        """
        plane1 = Plane3D(self.frame)
        plane_intersections1 = plane1.plane_intersections(plane3d)
        torus_line_interections1 = self.line_intersections(plane_intersections1[0])
        points = torus_line_interections1
        radius1 = points[0].point_distance(points[2]) / 2
        circle1 = curves.Circle3D(design3d.Frame3D((points[0] + points[2]) / 2, plane3d.frame.u,
                                                  plane3d.frame.v, plane3d.frame.w), radius1)
        radius2 = points[1].point_distance(points[3]) / 2
        circle2 = curves.Circle3D(design3d.Frame3D((points[1] + points[3]) / 2, plane3d.frame.u,
                                                  plane3d.frame.v, plane3d.frame.w), radius2)
        return [circle1, circle2]

    def concurrent_plane_intersection(self, plane3d, number_curves: int = None):
        """
        Toroidal plane intersections when plane's normal is concurrent with the cone's axis, but not orthogonal.

        :param plane3d: intersecting plane.
        :param number_curves: the number of resulting curves, if known.
        :return: list of intersecting curves.
        """
        if plane3d.point_distance(self.frame.origin) > self.inner_radius:
            torus_origin_plane = Plane3D(self.frame)
            projected_point_plane3d = plane3d.point_projection(self.frame.origin)
            torus_plane_projection = torus_origin_plane.point_projection(projected_point_plane3d)
            point = self.frame.origin + (torus_plane_projection - self.frame.origin).unit_vector() * self.major_radius
            if plane3d.point_distance(point) > self.minor_radius:
                return []

        points_intersections = self._plane_intersection_points(plane3d)
        if not plane3d.point_belongs(self.frame.origin, 1e-6):
            point_projection = plane3d.point_projection(self.frame.origin)
            vector = (point_projection - self.frame.origin).unit_vector()
            frame = design3d.Frame3D(point_projection, vector, self.frame.w, vector.cross(self.frame.w))
            plane_intersections = d3d_utils_intersections.get_two_planes_intersections(plane3d.frame, frame)
            line = curves.Line3D(plane_intersections[0], plane_intersections[1])
            line_intersections = self.line_intersections(line)
            for inter in self.line_intersections(line):
                if not inter.in_list(points_intersections):
                    points_intersections.append(inter)
            if line_intersections:
                number_curves = 1

        if number_curves == 1:
            ordered_points = d3d_common_operations.order_points_list_for_nearest_neighbor(points_intersections)
            inters_points = [ordered_points + [ordered_points[0]]]
        else:
            inters_points = d3d_common_operations.separate_points_by_closeness(points_intersections)
        if len(inters_points) == 1 and plane3d.point_belongs(self.frame.origin):
            return self.get_villarceau_circles(plane3d)
        return [edges.BSplineCurve3D.from_points_interpolation(list_points, 8, centripetal=False)
                for list_points in inters_points]

    def plane_intersections(self, plane3d):
        """
        Toroidal intersections with a plane.

        :param plane3d: intersecting plane.
        :return: list of intersecting curves.
        """
        projected_origin = plane3d.point_projection(self.frame.origin)
        translated_to_local_plane3d = plane3d.translation((projected_origin - plane3d.frame.origin).to_vector())
        if math.isclose(abs(translated_to_local_plane3d.frame.w.dot(self.frame.w)), 0, abs_tol=1e-6):
            return self.parallel_plane_intersection(translated_to_local_plane3d)
        if math.isclose(abs(translated_to_local_plane3d.frame.w.dot(self.frame.w)), 1, abs_tol=1e-6):
            return self.perpendicular_plane_intersection(translated_to_local_plane3d)
        return self.concurrent_plane_intersection(translated_to_local_plane3d)

    def _cylinder_intersection_points(self, cylindrical_surface: CylindricalSurface3D):
        """
        Gets the points of intersections between the cylindrical surface and the toroidal surface.

        :param cylindrical_surface: other Cylindrical 3d.
        :return: points of intersections.
        """
        arcs = self.torus_arcs(200) + self._torus_circle_generatrices_xy(200)
        points_intersections = []
        for arc in arcs:
            intersections = cylindrical_surface.circle_intersections(arc)
            for intersection in intersections:
                if not intersection.in_list(points_intersections):
                    points_intersections.append(intersection)
        for edge in cylindrical_surface.get_generatrices(300, self.outer_radius * 3):
            intersections = self.line_intersections(edge.line)
            for point in intersections:
                if not point.in_list(points_intersections):
                    points_intersections.append(point)
        return points_intersections

    def cylindricalsurface_intersections(self, cylindrical_surface: CylindricalSurface3D):
        """
        Gets the intersections between a toroidal surface and cylindrical surface.

        :param cylindrical_surface: other cylindrical surface.
        :return: List os curves intersecting Torus.
        """
        line = curves.Line3D.from_point_and_vector(cylindrical_surface.frame.origin, cylindrical_surface.frame.w)
        distance_to_self_origin = line.point_distance(self.frame.origin)

        if math.isclose(abs(self.frame.w.dot(cylindrical_surface.frame.w)), 1.0, abs_tol=1e-6) and \
                math.isclose(distance_to_self_origin, 0.0, abs_tol=1e-6):
            if cylindrical_surface.radius < self.minor_radius:
                return []
            if math.isclose(cylindrical_surface.radius, self.minor_radius, abs_tol=1e-6):
                return [curves.Circle3D(self.frame, self.minor_radius)]
        intersection_points = self._cylinder_intersection_points(cylindrical_surface)
        inters_points = d3d_common_operations.separate_points_by_closeness(intersection_points)
        curves_ = []
        for list_points in inters_points:
            bspline = edges.BSplineCurve3D.from_points_interpolation(list_points, 7, centripetal=False)
            if isinstance(bspline.simplify, edges.FullArc3D):
                curves_.append(bspline.simplify)
                continue
            curves_.append(bspline)

        return curves_

    def is_coincident(self, surface3d, abs_tol: float = 1e-6):
        """
        Verifies if two ToroidalSurfaces are coincident.

        :param surface3d: surface to verify.
        :param abs_tol: tolerance.
        :return: True if they are coincident, False otherwise.
        """
        if not isinstance(self, surface3d.__class__):
            return False
        if math.isclose(abs(self.frame.w.dot(surface3d.frame.w)), 1.0, abs_tol=abs_tol) and \
                math.isclose(self.major_radius, surface3d.major_radius, abs_tol=abs_tol) and \
                math.isclose(self.minor_radius, surface3d.minor_radius, abs_tol=abs_tol):
            return True
        return False

    def _conical_intersection_points(self, conical_surface: 'ConicalSurface3D'):
        """
        Gets the points of intersections between the cylindrical surface and the toroidal surface.

        :param conical_surface: other Conical Surface 3d.
        :return: points of intersections.
        """
        arcs = self.torus_arcs(200)
        points_intersections = []
        for arc in arcs:
            intersections = conical_surface.circle_intersections(arc)
            points_intersections.extend(intersections)
        point1 = conical_surface.frame.global_to_local_coordinates(design3d.Point3D(0, 0, self.bounding_box.zmin))
        point2 = conical_surface.frame.global_to_local_coordinates(design3d.Point3D(0, 0, self.bounding_box.zmax))
        for edge in conical_surface.get_generatrices(300, self.outer_radius * 3) + \
                    conical_surface.get_circle_generatrices(100, max(point1.z, 0), max(point2.z, 0)):
            intersections = self.edge_intersections(edge)
            for point in intersections:
                if not point.in_list(points_intersections):
                    points_intersections.append(point)
        return points_intersections

    def conicalsurface_intersections(self, conical_surface: 'ConicalSurface3D'):
        """
        Gets the intersections between a toroidal surface and cylindrical surface.

        :param conical_surface: other Conical Surface 3d.
        :return: List os curves intersecting Torus.
        """
        intersection_points = self._conical_intersection_points(conical_surface)
        if not intersection_points:
            return []
        inters_points = d3d_common_operations.separate_points_by_closeness(intersection_points)
        curves_ = []
        for list_points in inters_points:
            bspline = edges.BSplineCurve3D.from_points_interpolation(list_points, 4, centripetal=False)
            if isinstance(bspline.simplify, edges.FullArc3D):
                curves_.append(bspline.simplify)
                continue
            curves_.append(bspline)

        return curves_

    def _spherical_intersection_points(self, spherical_surface: 'SphericalSurface3D'):
        """
        Gets the points of intersections between the spherical surface and the toroidal surface.

        :param spherical_surface: other Spherical Surface 3d.
        :return: points of intersections.
        """
        arcs = self.torus_arcs(300) + self._torus_circle_generatrices_xy(100)
        intersection_points = []
        for arc in arcs:
            intersections = spherical_surface.circle_intersections(arc)
            intersection_points.extend(intersections)
        return intersection_points

    def sphericalsurface_intersections(self, spherical_surface: 'SphericalSurface3D'):
        """
        Gets the intersections between a toroidal surface and spherical surface.

        :param spherical_surface: other spherical Surface 3d.
        :return: List os curves intersecting Torus.
        """
        intersection_points = self._spherical_intersection_points(spherical_surface)
        if not intersection_points:
            return []
        inters_points = d3d_common_operations.separate_points_by_closeness(intersection_points)
        curves_ = []
        for list_points in inters_points:
            bspline = edges.BSplineCurve3D.from_points_interpolation(list_points, 4, centripetal=False)
            if isinstance(bspline.simplify, edges.FullArc3D):
                curves_.append(bspline.simplify)
                continue
            curves_.append(bspline)
        return curves_

    def _toroidal_intersection_points(self, toroidal_surface):
        """
        Gets the points of intersections between the spherical surface and the toroidal surface.

        :param toroidal_surface: other Toroidal Surface 3d.
        :return: points of intersections.
        """
        arcs = self.torus_arcs(300) + self._torus_circle_generatrices_xy(200)
        intersection_points = []
        for arc in arcs:
            intersections = toroidal_surface.circle_intersections(arc)
            for intersection in intersections:
                if not intersection.in_list(intersection_points):
                    intersection_points.append(intersection)

        return intersection_points

    def toroidalsurface_intersections_profile_profile(self, toroidal_surface):
        """
        Get intersections between two parallel toroidal surfaces, if there are any.

        :param toroidal_surface: other toroidal surface.
        :return:
        """
        local_self = self.frame_mapping(self.frame, 'new')
        local_other_toroidal_surface = toroidal_surface.frame_mapping(self.frame, 'new')

        circle = local_self.torus_arcs(1)[0]
        circle_intersections = local_other_toroidal_surface.circle_intersections(circle)
        circles = []
        for intersection in circle_intersections:
            center = design3d.Point3D(0, 0, intersection.z)
            circles_frame = design3d.Frame3D(center, local_self.frame.u, local_self.frame.v, local_self.frame.w)
            circles.append(curves.Circle3D(circles_frame, intersection.point_distance(center)))
        return circles

    def _yvone_villarceau_circles(self, toroidal_surface):
        """
        Gets the Yvone-Villarceau circles from two toroidal surfaces intersections.

        """
        circle_r1 = curves.Circle3D(self.frame, self.minor_radius)
        circle_r2 = curves.Circle3D(toroidal_surface.frame, toroidal_surface.minor_radius)
        circle_intersections = circle_r1.circle_intersections(circle_r2)
        intersections = []
        for intersection in circle_intersections:
            x_comp, y_comp, _ = intersection
            cos_s = x_comp / self.minor_radius
            sin_s = y_comp / self.minor_radius
            if toroidal_surface.frame.u.z != 0.0 and toroidal_surface.frame.v.z != 0.0:
                sin_t = (y_comp -
                         toroidal_surface.frame.origin.y +
                         (toroidal_surface.frame.origin.z *
                          toroidal_surface.frame.u.y / toroidal_surface.frame.u.z)) * (1 / (
                        (toroidal_surface.frame.v.y - (
                                toroidal_surface.frame.v.z / toroidal_surface.frame.u.z)
                         ) * toroidal_surface.minor_radius))
                cos_t = -toroidal_surface.frame.origin.z / (
                        toroidal_surface.minor_radius * toroidal_surface.frame.u.z
                ) - sin_t * (
                                toroidal_surface.frame.v.z / toroidal_surface.frame.u.z)
            elif toroidal_surface.frame.origin.z == 0:
                sin_t = (y_comp - toroidal_surface.frame.origin.y
                         ) * (1 / (toroidal_surface.frame.v.y * toroidal_surface.minor_radius))
                cos_t = math.cos(math.asin(sin_t))
            else:
                raise NotImplementedError
            for sign in [1, -1]:

                normal1 = design3d.Vector3D(-(self.minor_radius / self.major_radius) * sin_s,
                                           (self.minor_radius / self.major_radius) * cos_s,
                                           sign * math.sqrt(
                                               1 - (self.minor_radius / self.major_radius) ** 2)
                                           ).unit_vector()
                normal2 = -(toroidal_surface.minor_radius / toroidal_surface.major_radius
                            ) * sin_t * toroidal_surface.frame.u + (
                                  toroidal_surface.minor_radius / toroidal_surface.major_radius
                          ) * cos_t * toroidal_surface.frame.v + sign * math.sqrt(
                    1 - (toroidal_surface.minor_radius / toroidal_surface.major_radius) ** 2
                ) * toroidal_surface.frame.w
                if abs(abs(normal1.dot(normal2.unit_vector())) - 1.0) < 1e-6:
                    intersections.append(curves.Circle3D.from_center_normal(
                        intersection, normal1, self.major_radius))
            vector = (intersection - self.frame.origin).unit_vector()
            plane = Plane3D(design3d.Frame3D(intersection, self.frame.w, vector.cross(self.frame.w), vector))
            intersections.extend(self.plane_intersections(plane))
        return intersections

    def outer_radius_tangent_inner_radius_toroidalsurface_intersections(self, toroidal_surface):
        """
        Calculates the intersections between two toroidal surfaces.

        Case where the outer radius of one toroidal surface is touching inner radius of the other toroidal surface.

        :param toroidal_surface: other toroidal surface.
        :return:
        """
        intersections = []

        distance_origin_to_other_axis = self.frame.origin.point_distance(toroidal_surface.frame.origin)
        intersection_points = self._toroidal_intersection_points(toroidal_surface)

        vector = (toroidal_surface.frame.origin - self.frame.origin).unit_vector()

        point1 = self.frame.origin - vector * self.inner_radius
        if not point1.in_list(intersection_points):
            intersection_points.append(point1)

        point2 = self.frame.origin + vector * (distance_origin_to_other_axis + toroidal_surface.inner_radius)
        if not point2.in_list(intersection_points):
            intersection_points.append(point2)

        if not intersection_points:
            return intersections

        inters_points = d3d_common_operations.separate_points_by_closeness(intersection_points)

        frame = design3d.Frame3D(self.frame.origin, vector, self.frame.w, vector.cross(self.frame.w))
        curves_ = []

        for points in inters_points:
            local_points = [frame.global_to_local_coordinates(point) for point in points]

            lists_points = [[], []]
            first_point = None

            for i, local_point in enumerate(local_points):
                if local_point.z > 0:
                    lists_points[0].append(points[i])
                elif local_point.z < 0:
                    lists_points[1].append(points[i])
                else:
                    first_point = points[i]

            if not first_point:
                raise NotImplementedError

            for list_points in lists_points:
                points_ = d3d_common_operations.order_points_list_for_nearest_neighbor(
                    [first_point] + list(set(list_points)))
                points_ = points_[points_.index(first_point):] + points_[:points_.index(first_point)]
                edge = edges.BSplineCurve3D.from_points_interpolation(points_ + [points_[0]], 8)
                curves_.append(edge)
        return curves_

    def toroidalsurface_intersections(self, toroidal_surface):
        """
        Gets the intersections between two toroidal surface.

        :param toroidal_surface: other toroidal Surface 3d.
        :return: List os curves intersecting Torus.
        """
        intersections = []

        axis_line = curves.Line3D.from_point_and_vector(self.frame.origin, self.frame.w)

        distance_origin_to_other_axis = self.frame.origin.point_distance(toroidal_surface.frame.origin)
        is_minor_same = abs(self.minor_radius - toroidal_surface.minor_radius) < 1e-6
        is_major_same = abs(self.major_radius - toroidal_surface.major_radius) < 1e-6

        if math.isclose(abs(self.frame.w.dot(toroidal_surface.frame.w)), 1.0, abs_tol=1e-6):
            if d3d_common_operations.get_plane_point_distance(self.frame, toroidal_surface.frame.origin) > \
                    self.minor_radius + toroidal_surface.minor_radius:
                return []

            if axis_line.point_distance(toroidal_surface.frame.origin) < 1e-6:
                return self.toroidalsurface_intersections_profile_profile(toroidal_surface)

            if is_minor_same and \
                    abs(distance_origin_to_other_axis - self.major_radius - toroidal_surface.major_radius) < 1e-6:
                vector = (toroidal_surface.frame.origin - self.frame.origin).unit_vector()
                center = self.frame.origin + vector * self.major_radius

                circle = curves.Circle3D(design3d.Frame3D(center, vector,
                                                         self.frame.w, vector.cross(self.frame.w)), self.minor_radius)
                if is_major_same:
                    plane = Plane3D(design3d.Frame3D(center, self.frame.w, vector.cross(self.frame.w), vector))
                    intersections.extend(self.plane_intersections(plane))
                intersections.append(circle)
            elif is_major_same and \
                    abs(distance_origin_to_other_axis - self.minor_radius - toroidal_surface.minor_radius) < 1e-6:
                if is_minor_same:
                    intersections = self._yvone_villarceau_circles(toroidal_surface)
                    if intersections:
                        return intersections

                return self.outer_radius_tangent_inner_radius_toroidalsurface_intersections(toroidal_surface)
            elif (is_minor_same and
                  abs(self.frame.w.dot((toroidal_surface.frame.origin - self.frame.origin).unit_vector())) < 1e-6 and
                  distance_origin_to_other_axis - self.outer_radius < toroidal_surface.inner_radius):
                circle_bigr1 = curves.Circle3D(self.frame, self.major_radius + self.minor_radius)
                circle_bigr2 = curves.Circle3D(toroidal_surface.frame,
                                               toroidal_surface.major_radius + toroidal_surface.minor_radius)

                circle_intersections = circle_bigr1.circle_intersections(circle_bigr2)

                if circle_intersections:
                    center = (circle_intersections[0] + circle_intersections[1]) / 2
                    vector = (center - self.frame.origin).unit_vector()
                    plane = Plane3D(design3d.Frame3D(center, self.frame.w, vector.cross(self.frame.w), vector))
                    intersections = self.plane_intersections(plane)

        intersection_points = self._toroidal_intersection_points(toroidal_surface)

        if not intersection_points:
            return intersections

        if intersections:
            intersection_points = [point for point in intersection_points if not any(
                intersection.point_belongs(point, 1e-4) for intersection in intersections)]

        inters_points = d3d_common_operations.separate_points_by_closeness(intersection_points)
        for list_points in inters_points:
            bspline = edges.BSplineCurve3D.from_points_interpolation(list_points, 8, centripetal=False)
            intersections.append(bspline)
        return intersections

    def u_iso(self, u: float) -> curves.Circle3D:
        """
        Returns the u-iso curve of the surface.

        :param u: The value of u where to extract the curve.
        :type u: float
        :return: A circle 3D
        :rtype: :class:`curves.Circle3D`
        """

        center_u0 = self.frame.origin + self.frame.u * self.major_radius
        center = center_u0.rotation(self.frame.origin, self.frame.w, u)
        u_vector = (center - self.frame.origin).unit_vector()
        frame = design3d.Frame3D(center, u_vector, self.frame.w, u_vector.cross(self.frame.w))
        return curves.Circle3D(frame, self.minor_radius)

    def v_iso(self, v: float) -> curves.Circle3D:
        """
        Returns the v-iso curve of the surface.

        :param v: The value of u where to extract the curve.
        :type v: float
        :return: A Circle 3D
        :rtype: :class:`curves.Circle3D`
        """
        z = self.minor_radius * math.sin(v)
        frame = self.frame.translation(self.frame.w * z)
        radius = abs(self.major_radius + self.minor_radius * math.cos(v))
        return curves.Circle3D(frame, radius)

    def normal_at_point(self, point: design3d.Point3D):
        """
        Gets normal vector at given point on the surface.

        :param point: point to be verified.
        :return: normal
        """
        if not self.point_belongs(point):
            raise ValueError('Point given not on surface.')
        theta, phi = self.point3d_to_2d(point)
        normal = math.cos(phi) * (math.cos(theta) * self.frame.u +
                                  math.sin(theta) * self.frame.v) + math.sin(phi) * self.frame.w
        return normal


class ConicalSurface3D(UPeriodicalSurface):
    """
    Describes a cone.

    A cone is defined by the half-angle, and is positioned in space by a frame and a reference radius.
    The main axis of the frame is the axis of revolution of the cone.
    The plane defined by the origin, the x direction and the y direction of the frame is the
    plane of the cone. The intersection of the cone with this reference plane is a circle of radius equal
    to the reference radius.
    The apex of the cone is on the negative side of the main axis of the frame if the half-angle
    is positive, and on the positive side if the half-angle is negative. This frame is the
    "local coordinate system" of the cone. The following apply:
        Rotation around its main axis, in the trigonometric sense given by the x direction and the y direction,
        defines the u parametric direction and the x-axis gives the origin for the u parameter.
        The z axis defines the v parametric direction of the cone and the origin of the frame is the origin
        of the v parameter.
        The parametric range of the two parameters is:
            - [ 0, 2.*Pi ] for u, and
            - ] -infinity, +infinity [ for v

    The parametric equation of the cone is:
    P(u, v) = O + (R + v*tan(ang)) * (cos(u)*x + sin(u)*y) + v*z
    where:
        - O, x, y and z are respectively the origin, the x, y and z direction of the cone's local coordinate system
        - ang is the half-angle at the apex of the cone
        - R is the reference radius.

    :param frame: Cone's local coordinate system.
    :param semi_angle: half-angle at the apex of the cone.
    :param ref_radius: radius of the circle formed by the intersection of the cone with the reference plane.
    """
    face_class = 'ConicalFace3D'
    x_periodicity = design3d.TWO_PI
    y_periodicity = None

    def __init__(self, frame: design3d.Frame3D, semi_angle: float, ref_radius: float = 0.0,
                 name: str = ''):
        self.semi_angle = semi_angle
        self.ref_radius = ref_radius
        UPeriodicalSurface.__init__(self, frame=frame, name=name)

    def __hash__(self):
        return hash((self.__class__.__name__, self.frame, self.semi_angle, self.ref_radius))

    def __eq__(self, other):
        if self.__class__.__name__ != other.__class__.__name__:
            return False
        if self.frame == other.frame and self.semi_angle == other.semi_angle and self.ref_radius == self.ref_radius:
            return True
        return False

    @property
    def u_domain(self):
        """The parametric domain of the surface in the U direction."""
        return -math.pi, math.pi

    @property
    def v_domain(self):
        """The parametric domain of the surface in the V direction."""
        return -math.inf, math.inf

    @property
    def domain(self):
        """Returns u and v bounds."""
        return -math.pi, math.pi, -math.inf, math.inf

    @property
    def apex(self):
        """
        Computes the apex of the cone.

         It is on the negative side of the axis of revolution of this cone if the half-angle at the apex is positive,
          and on the positive side of the "main axis" if the half-angle is negative.
        """
        origin = self.frame.origin
        return origin + (-self.ref_radius / math.tan(self.semi_angle)) * self.frame.w

    def get_generatrices(self, number_lines: int = 36, z: float = 1):
        """
        Gets Conical Surface 3D generatrix lines.

        :param z: cone's z height.
        :param number_lines: number of generatrix lines.
        :return:
        """
        v = z - self.ref_radius / math.tan(self.semi_angle)
        point1 = self.apex
        point2 = self.point2d_to_3d(design3d.Point2D(0.0, v))
        generatrix = edges.LineSegment3D(point1, point2)
        list_generatrices = [generatrix]
        for i in range(1, number_lines):
            theta = i / number_lines * design3d.TWO_PI
            wire = generatrix.rotation(self.frame.origin, self.frame.w, theta)
            list_generatrices.append(wire)
        return list_generatrices

    def get_circle_generatrices(self, number_circles: int, z1, z2):
        """
        Get circles generatrix of the cone.

        :param z1: Initial height of cone.
        :param z2: Final height of cone.
        :param number_circles: number of expected circles.
        """
        circles = []
        for i_z in np.linspace(z1, z2, number_circles):
            circle = self.v_iso(i_z)
            if circle is None:
                continue
            circles.append(circle)
        return circles

    def plot(self, ax=None, edge_style: EdgeStyle = EdgeStyle(color='grey', alpha=0.5), **kwargs):
        """
        Plots the ConicalSurface3D.
        """
        z = kwargs.get("z", 1)
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
        self.frame.plot(ax)
        line_generatrices = self.get_generatrices(36, z)
        _, z_apex = self.point3d_to_2d(self.apex)
        circle_generatrices = self.get_circle_generatrices(50, z_apex, z_apex + z)

        for edge in line_generatrices + circle_generatrices:
            edge.plot(ax, edge_style)
        return ax

    @classmethod
    def from_step(cls, arguments, object_dict, **kwargs):
        """
        Converts a step primitive to a ConicalSurface3D.

        :param arguments: The arguments of the step primitive.
        :type arguments: list
        :param object_dict: The dictionary containing all the step primitives
            that have already been instantiated.
        :type object_dict: dict
        :return: The corresponding ConicalSurface3D object.
        :rtype: :class:`design3d.faces.ConicalSurface3D`
        """

        length_conversion_factor = kwargs.get("length_conversion_factor", 1)
        angle_conversion_factor = kwargs.get("angle_conversion_factor", 1)

        frame = object_dict[arguments[1]]
        radius = float(arguments[2]) * length_conversion_factor
        semi_angle = float(arguments[3]) * angle_conversion_factor
        return cls(frame, semi_angle, radius, name=arguments[0][1:-1])

    def is_coincident(self, surface3d, abs_tol: float = 1e-6):
        """
        Verifies if two conical surfaces are coincident.

        :param surface3d: other surface 3d.
        :param abs_tol: tolerance.
        :return: True if they are coincident, False otherwise.
        """
        if not isinstance(surface3d, ConicalSurface3D):
            return False
        if math.isclose(self.frame.w.dot(surface3d.frame.w), 1.0, abs_tol=abs_tol) and \
                self.frame.origin.is_close(surface3d.frame.origin) and \
                math.isclose(self.semi_angle, surface3d.semi_angle, abs_tol=abs_tol) and \
                math.isclose(self.ref_radius, surface3d.ref_radius, abs_tol=abs_tol):
            return True
        return False

    def to_step(self, current_id):
        """
        Converts the object to a STEP representation.

        :param current_id: The ID of the last written primitive.
        :type current_id: int
        :return: The STEP representation of the object and the last ID.
        :rtype: tuple[str, list[int]]
        """
        content, frame_id = self.frame.to_step(current_id)
        current_id = frame_id + 1
        content += f"#{current_id} = CONICAL_SURFACE('{self.name}',#{frame_id},{self.ref_radius},{self.semi_angle});\n"
        return content, [current_id]

    def frame_mapping(self, frame: design3d.Frame3D, side: str):
        """
        Changes frame_mapping and return a new ConicalSurface3D.

        :param side: 'old' or 'new'
        """
        new_frame = self.frame.frame_mapping(frame, side)
        return ConicalSurface3D(new_frame, self.semi_angle, self.ref_radius, name=self.name)

    def point2d_to_3d(self, point2d: design3d.Point2D):
        """
        Coverts a parametric coordinate on the surface into a 3D spatial point (x, y, z).

        :param point2d: Point at the ConicalSuface3D
        :type point2d: `design3d.`Point2D`
        """
        theta, z = point2d
        radius = math.tan(self.semi_angle) * z + self.ref_radius
        new_point = design3d.Point3D(radius * math.cos(theta),
                                    radius * math.sin(theta),
                                    z)
        return self.frame.local_to_global_coordinates(new_point)

    def point3d_to_2d(self, point3d: design3d.Point3D):
        """
        Returns the cylindrical coordinates design3d.Point2D(theta, z) of a Cartesian coordinates point (x, y, z).

        :param point3d: Point at the CylindricalSuface3D.
        :type point3d: :class:`design3d.`Point3D`
        """
        x, y, z = self.frame.global_to_local_coordinates(point3d)
        # Do not delete this, mathematical problem when x and y close to zero (should be zero) but not 0
        # Generally this is related to uncertainty of step files.
        if x != 0.0 and abs(x) < 1e-12:
            x = 0.0
        if y != 0.0 and abs(y) < 1e-12:
            y = 0.0
        if x == 0.0 and y == 0.0:
            theta = 0.0
        else:
            theta = math.atan2(y, x)
        if abs(theta) < 1e-16:
            theta = 0.0
        if abs(z) < 1e-16:
            z = 0.0

        return design3d.Point2D(theta, z)

    def parametric_points_to_3d(self, points: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Transform parametric coordinates to 3D points on the conical surface.

        Given a set of parametric coordinates `(u, v)` representing points on the surface,
        this method returns the corresponding 3D points on the conical surface.

        :param points: Parametric coordinates in the form of a numpy array with shape (n, 2),
                       where `n` is the number of points, and each row corresponds to `(u, v)`.
        :type points: numpy.ndarray[np.float64]

        :return: Array of 3D points representing the conical surface in Cartesian coordinates.
        :rtype: numpy.ndarray[np.float64]
        """
        center = np.array(self.frame.origin)
        x = np.array([self.frame.u[0], self.frame.u[1], self.frame.u[2]])
        y = np.array([self.frame.v[0], self.frame.v[1], self.frame.v[2]])
        z = np.array([self.frame.w[0], self.frame.w[1], self.frame.w[2]])

        points = points.reshape(-1, 2, 1)

        u_values = points[:, 0]
        v_values = points[:, 1]

        x_component = np.cos(u_values) * x
        y_component = np.sin(u_values) * y

        return (center + (v_values * math.tan(self.semi_angle) + self.ref_radius) * (x_component + y_component)
                + v_values * z)

    def rectangular_cut(self, theta1: float, theta2: float,
                        param_z1: float, param_z2: float, name: str = ''):
        """Deprecated method, Use ConicalFace3D from_surface_rectangular_cut method."""
        raise AttributeError("ConicalSurface3D.rectangular_cut is deprecated."
                             "Use the class_method from_surface_rectangular_cut in ConicalFace3D instead")

    def linesegment3d_to_2d(self, linesegment3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        start = self.point3d_to_2d(linesegment3d.start)
        end = self.point3d_to_2d(linesegment3d.end)
        if math.isclose(start.y, end.y, rel_tol=0.005):
            # special case when there is a small line segment that should be a small arc of circle instead
            return [edges.LineSegment2D(start, end)]
        if start.x != end.x:
            end = design3d.Point2D(start.x, end.y)
        if start != end:
            return [edges.LineSegment2D(start, end)]
        return None

    def contour3d_to_2d(self, contour3d, return_primitives_mapping: bool = False):
        """
        Transforms a Contour3D into a Contour2D in the parametric domain of the surface.

        :param contour3d: The contour to be transformed.
        :type contour3d: :class:`wires.Contour3D`
        :param return_primitives_mapping: If True, returns a dictionary containing the correspondence between 2D and 3D
         primitives
        :type return_primitives_mapping: bool
        :return: A 2D contour object.
        :rtype: :class:`wires.Contour2D`
        """
        contour3d = self.check_primitives_order(contour3d)
        primitives2d, primitives_mapping = self.primitives3d_to_2d(contour3d.primitives)

        wire2d = wires.Wire2D(primitives2d)
        delta_x = abs(wire2d.primitives[0].start.x - wire2d.primitives[-1].end.x)
        if math.isclose(delta_x, design3d.TWO_PI, abs_tol=1e-3) and wire2d.is_ordered():
            if len(primitives2d) > 1:
                # very specific conical case due to the singularity in the point z = 0 on parametric domain.
                if self.is_singularity_point(self.point2d_to_3d(primitives2d[-2].start)):
                    self.repair_primitives_periodicity(primitives2d, primitives_mapping)
            if return_primitives_mapping:
                return wires.Contour2D(primitives2d), primitives_mapping
            return wires.Contour2D(primitives2d)
        # Fix contour
        self.repair_primitives_periodicity(primitives2d, primitives_mapping)
        if return_primitives_mapping:
            return wires.Contour2D(primitives2d), primitives_mapping
        return wires.Contour2D(primitives2d)

    def translation(self, offset: design3d.Vector3D):
        """
        ConicalSurface3D translation.

        :param offset: translation vector.
        :return: A new translated ConicalSurface3D.
        """
        return self.__class__(self.frame.translation(offset),
                              self.semi_angle, self.ref_radius)

    def rotation(self, center: design3d.Point3D,
                 axis: design3d.Vector3D, angle: float):
        """
        ConicalSurface3D rotation.

        :param center: rotation center.
        :param axis: rotation axis.
        :param angle: angle rotation.
        :return: a new rotated ConicalSurface3D.
        """
        new_frame = self.frame.rotation(center=center, axis=axis, angle=angle)
        return self.__class__(new_frame, self.semi_angle, self.ref_radius)

    def circle_intersections(self, circle: curves.Circle3D):
        """
        Calculates the intersections between a conical surface and a Circle 3D.

        :param circle: other circle to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        if not self.frame.origin.is_close(design3d.O3D) or not self.frame.w.is_close(design3d.Z3D):
            local_surface = self.frame_mapping(self.frame, 'new')
            local_curve = circle.frame_mapping(self.frame, 'new')
            local_intersections = local_surface.circle_intersections(local_curve)
            global_intersections = []
            for intersection in local_intersections:
                global_intersections.append(self.frame.local_to_global_coordinates(intersection))
            return global_intersections
        if circle.bounding_box.zmax < self.frame.origin.z:
            return []
        z_max = circle.bounding_box.zmax
        radius = z_max * math.tan(self.semi_angle) + self.ref_radius
        line = curves.Line3D.from_point_and_vector(self.frame.origin, self.frame.w)
        if line.point_distance(circle.center) > radius + circle.radius:
            return []
        intersections = [point for point in self.curve_intersections(circle) if point.z >= 0]
        return intersections

    def _full_line_intersections(self, line: curves.Line3D):
        """
        Calculates the intersections between a conical surface and a Line 3D, for the two lobes of the cone.

        :param line: other line to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        apex = self.apex
        if line.point_belongs(apex):
            return [apex]
        line_direction_vector = line.unit_direction_vector()
        plane_normal = line_direction_vector.cross((apex - line.point1).to_vector()).unit_vector()
        if self.frame.w.dot(plane_normal) > 0:
            plane_normal = - plane_normal
        plane = Plane3D.from_normal(apex, plane_normal)
        cos_theta = math.sqrt(1 - (plane_normal.dot(self.frame.w) ** 2))
        if cos_theta >= math.cos(self.semi_angle):
            plane_h = Plane3D.from_normal(apex + self.frame.w, self.frame.w)
            circle = self.perpendicular_plane_intersection(plane_h)[0]
            line_p = plane_h.plane_intersections(plane)[0]
            circle_line_p_intersections = circle.line_intersections(line_p)
            intersections = []
            for intersection in circle_line_p_intersections:
                line_v_x = curves.Line3D(apex, intersection)
                line_inter = line_v_x.intersection(line)
                if not line_inter:
                    continue
                intersections.append(line_inter)
            return line.sort_points_along_curve(intersections)
        return []

    def line_intersections(self, line: curves.Line3D):
        """
        Calculates the intersections between a conical surface and a Line 3D.

        :param line: other line to verify intersections.
        :return: a list of intersection points, if there exists any.
        """
        line_intersections = self._full_line_intersections(line)
        positive_lobe_intersections = []
        for point in line_intersections:
            local_point = self.frame.global_to_local_coordinates(point)
            zmin = - self.ref_radius / math.tan(self.semi_angle)
            if local_point.z < zmin:
                continue
            positive_lobe_intersections.append(point)
        return positive_lobe_intersections

    def _helper_parallel_plane_intersection_through_origin(self, plane):
        """
        Conical plane intersections when plane's normal is perpendicular with the Cone's axis passing through origin.

        :param plane: intersecting plane.
        :return: list of intersecting curves
        """
        direction = self.frame.w.cross(plane.normal)
        point1 = self.frame.origin + direction
        point2 = self.frame.origin - direction
        theta1 = math.atan2(point1.y, point1.x)
        theta2 = math.atan2(point2.y, point2.x)
        point1_line1 = self.point2d_to_3d(design3d.Point2D(theta1, -0.1))
        point2_line1 = self.point2d_to_3d(design3d.Point2D(theta1, 0.1))
        point1_line2 = self.point2d_to_3d(design3d.Point2D(theta2, -0.1))
        point2_line2 = self.point2d_to_3d(design3d.Point2D(theta2, 0.1))
        return [curves.Line3D(point1_line1, point2_line1), curves.Line3D(point1_line2, point2_line2)]

    def _hyperbola_helper(self, plane3d, hyperbola_center, hyperbola_positive_vertex):
        semi_major_axis = hyperbola_center.point_distance(hyperbola_positive_vertex)
        circle = self.v_iso(2 * semi_major_axis)
        hyperbola_points = plane3d.circle_intersections(circle)
        if not hyperbola_points:
            return []

        semi_major_dir = (hyperbola_positive_vertex - hyperbola_center).unit_vector()
        frame = design3d.Frame3D(hyperbola_center, semi_major_dir,
                                plane3d.frame.w.cross(semi_major_dir), plane3d.frame.w)
        local_point = frame.global_to_local_coordinates(hyperbola_points[0])
        return [curves.Hyperbola3D(frame, semi_major_axis,
                                   math.sqrt((local_point.y ** 2) / (local_point.x ** 2 / semi_major_axis ** 2 - 1)))]

    def _parallel_plane_intersections_hyperbola_helper(self, plane):
        """
        Conical plane intersections when plane's normal is perpendicular with the Cone's axis.

        :param plane: intersecting plane.
        :return: list containing the resulting intersection hyperbola curve.
        """
        hyperbola_center = plane.point_projection(self.apex)
        z = ((math.sqrt(hyperbola_center.x ** 2 + hyperbola_center.y ** 2) - self.ref_radius)
             / math.tan(self.semi_angle))
        hyperbola_positive_vertex = self.frame.local_to_global_coordinates(
            design3d.Point3D(hyperbola_center.x, hyperbola_center.y, z))
        return self._hyperbola_helper(plane, hyperbola_center, hyperbola_positive_vertex)

    def parallel_plane_intersection(self, plane3d: Plane3D):
        """
        Conical plane intersections when plane's normal is perpendicular with the Cone's axis.

        :param plane3d: intersecting plane
        :return: list of intersecting curves
        """
        if plane3d.point_belongs(self.frame.origin):
            return self._helper_parallel_plane_intersection_through_origin(plane3d)

        if not self.frame.w.is_close(design3d.Z3D):
            local_surface = self.frame_mapping(self.frame, 'new')
            local_plane = plane3d.frame_mapping(self.frame, 'new')
            local_intersections = local_surface.parallel_plane_intersection(local_plane)
            return [intersection.frame_mapping(self.frame, 'old') for intersection in local_intersections]
        return self._parallel_plane_intersections_hyperbola_helper(plane3d)

    def perpendicular_plane_intersection(self, plane3d):
        """
        Cone plane intersections when plane's normal is parallel with the cone axis.

        :param plane3d: Intersecting plane.
        :return: List of intersecting curves.
        """
        center3d_plane = plane3d.point_projection(self.frame.origin)
        radius = self.frame.origin.point_distance(center3d_plane) * math.tan(self.semi_angle) + self.ref_radius
        circle3d = curves.Circle3D(design3d.Frame3D(center3d_plane, plane3d.frame.u,
                                                   plane3d.frame.v, plane3d.frame.w), radius)
        return [circle3d]

    def _concurrent_plane_intersection_parabola(self, plane3d, parabola_vertex):
        """
        Calculates parabola for Cone and concurrent plane intersections.

        :param plane3d: intersecting plane.
        :param parabola_vertex: parabla vertex point.
        :return: list of intersecting curves.
        """
        distance_plane_vertex = parabola_vertex.point_distance(self.apex)
        circle = self.perpendicular_plane_intersection(
            Plane3D(design3d.Frame3D(self.frame.origin + distance_plane_vertex * 5 * self.frame.w,
                                    self.frame.u, self.frame.v, self.frame.w)))[0]
        line_circle_intersecting_plane = d3d_utils_intersections.get_two_planes_intersections(
            plane3d.frame, circle.frame)
        line_circle_intersecting_plane = curves.Line3D(line_circle_intersecting_plane[0],
                                                       line_circle_intersecting_plane[1])
        parabola_points = circle.line_intersections(line_circle_intersecting_plane)
        v_vector = ((parabola_points[0] + parabola_points[1]) / 2 - parabola_vertex).unit_vector()
        frame = design3d.Frame3D(parabola_vertex, v_vector.cross(plane3d.frame.w), v_vector, plane3d.frame.w)
        local_point = frame.global_to_local_coordinates(parabola_points[0])
        vrtx_equation_a = local_point.y / local_point.x ** 2
        parabola = curves.Parabola3D(frame, 1 / (4 * vrtx_equation_a))
        return [parabola]

    def concurrent_plane_intersection(self, plane3d: Plane3D):
        """
        Cone plane intersections when plane's normal is concurrent with the cone's axis, but not orthogonal.

        :param plane3d: intersecting plane.
        :return: list of intersecting curves.
        """
        plane_normal = self.frame.w.cross(plane3d.frame.w)
        plane2 = Plane3D.from_normal(plane3d.frame.origin, plane_normal)
        plane2_plane3d_intersections = plane3d.plane_intersections(plane2)
        line_intersections = self.line_intersections(plane2_plane3d_intersections[0])
        if 1 > len(line_intersections) or len(line_intersections) > 2:
            return []
        angle_plane_cones_direction = abs(design3d.geometry.vectors3d_angle(self.frame.w, plane3d.frame.w)
                                          - math.pi / 2)
        if math.isclose(angle_plane_cones_direction, self.semi_angle, abs_tol=1e-8):
            return self._concurrent_plane_intersection_parabola(plane3d, line_intersections[0])
        if len(line_intersections) == 1:
            full_line_intersections = self._full_line_intersections(plane2_plane3d_intersections[0])
            if len(full_line_intersections) == 1:
                return []
            hyperbola_center = (full_line_intersections[0] + full_line_intersections[1]) / 2
            return self._hyperbola_helper(plane3d, hyperbola_center, line_intersections[0])
        if len(line_intersections) != 2:
            return []
        ellipse_center = (line_intersections[0] + line_intersections[1]) / 2
        line_intersections2 = self.line_intersections(curves.Line3D.from_point_and_vector(
            ellipse_center, plane_normal))
        major_dir = (line_intersections[0] - ellipse_center).unit_vector()
        major_axis = ellipse_center.point_distance(line_intersections[0])
        minor_dir = (line_intersections2[0] - ellipse_center).unit_vector()
        minor_axis = ellipse_center.point_distance(line_intersections2[0])

        if minor_axis > major_axis:
            major_axis, minor_axis = minor_axis, major_axis
            major_dir, minor_dir = minor_dir, major_dir
        return [curves.Ellipse3D(major_axis, minor_axis, design3d.Frame3D(
            ellipse_center, major_dir, minor_dir, plane3d.frame.w))]

    def plane_intersections(self, plane3d):
        """
        Gets the intersections between a plane 3d and a conical surface 3d.

        :param plane3d: other plane, to verify intersections.
        :return:
        """
        if math.isclose(abs(plane3d.frame.w.dot(self.frame.w)), 0, abs_tol=1e-6):
            return self.parallel_plane_intersection(plane3d)
        if math.isclose(abs(plane3d.frame.w.dot(self.frame.w)), 1, abs_tol=1e-6):
            return self.perpendicular_plane_intersection(plane3d)
        return self.concurrent_plane_intersection(plane3d)

    def is_singularity_point(self, point, *args, **kwargs):
        """Verifies if point is on the surface singularity."""
        tol = kwargs.get("tol", 1e-6)
        return self.apex.is_close(point, tol)

    def check_primitives_order(self, contour):
        """
        If contours passes at the cone singularity this makes sure that the contour is not in an undefined order.
        """
        pos = 0
        for i, primitive in enumerate(contour.primitives):
            if self.is_singularity_point(primitive.start):
                pos = i
                break
        if pos:
            contour.primitives = contour.primitives[pos:] + contour.primitives[:pos]
        return contour

    @staticmethod
    def get_singularity_lines():
        """
        Return lines that are parallel and coincident with surface singularity at parametric domain.
        """
        return [curves.Line2D(design3d.Point2D(-math.pi, 0), design3d.Point2D(math.pi, 0))]

    def _spherical_intersection_points(self, spherical_surface: 'SphericalSurface3D'):
        """
        Gets the points of intersections between the spherical surface and the toroidal surface.

        :param spherical_surface: other Spherical Surface 3d.
        :return: points of intersections.
        """
        point1 = self.frame.global_to_local_coordinates(design3d.Point3D(0, 0, spherical_surface.bounding_box.zmin))
        point2 = self.frame.global_to_local_coordinates(design3d.Point3D(0, 0, spherical_surface.bounding_box.zmax))
        cone_generatrices = self.get_generatrices(200, spherical_surface.radius * 4) + \
                            self.get_circle_generatrices(200, max(point1.z, 0), max(point2.z, 0))
        intersection_points = []
        for gene in cone_generatrices:
            intersections = spherical_surface.edge_intersections(gene)
            for intersection in intersections:
                if not intersection.in_list(intersection_points):
                    intersection_points.append(intersection)
        return intersection_points

    def sphericalsurface_intersections(self, spherical_surface: 'SphericalSurface3D'):
        """
        Conical Surface intersections with a Spherical surface.

        :param spherical_surface: intersecting sphere.
        :return: list of intersecting curves.
        """
        intersection_points = self._spherical_intersection_points(spherical_surface)
        if not intersection_points:
            return []
        inters_points = d3d_common_operations.separate_points_by_closeness(intersection_points)
        curves_ = []
        for list_points in inters_points:
            bspline = edges.BSplineCurve3D.from_points_interpolation(list_points, 4, centripetal=False)
            if isinstance(bspline.simplify, edges.FullArc3D):
                curves_.append(bspline.simplify)
                continue
            curves_.append(bspline)
        return curves_

    def _conical_intersection_points(self, conical_surface: 'ConicalSurface3D', length: float):
        """
        Gets the points of intersections between the spherical surface and the toroidal surface.

        :param conical_surface: other Spherical Surface 3d.
        :return: points of intersections.
        """
        cone_generatrices = self.get_generatrices(max(100, int((length / 2) * 10)), length) + \
                            self.get_circle_generatrices(max(200, int((length / 2) * 20)), 0, length)
        intersection_points = []
        for gene in cone_generatrices:
            intersections = conical_surface.edge_intersections(gene)
            for intersection in intersections:
                if not intersection.in_list(intersection_points):
                    intersection_points.append(intersection)
        return intersection_points

    def parallel_conicalsurface_intersections(self, conical_surface):
        """
        Get Conical Surface intersections with another conical surface, when their axis are parallel.

        :param conical_surface: intersecting conical surface.
        :return: list of intersecting curves.
        """
        generatrix = conical_surface.get_generatrices(z=2, number_lines=1)[0]
        line_intersections = self.line_intersections(generatrix.line)
        if line_intersections:
            local_surface = self.frame_mapping(self.frame, 'new')
            local_point = self.frame.global_to_local_coordinates(line_intersections[0])
            local_circle = local_surface.v_iso(local_point.z)
            return [local_circle.frame_mapping(self.frame, 'old')]
        axis_line = curves.Line3D.from_point_and_vector(self.frame.origin, self.frame.w)
        if axis_line.point_distance(conical_surface.frame.origin) < 1e-6:
            return []
        intersections_points = [self.circle_intersections(circle) for circle in
                                [conical_surface.v_iso(1), conical_surface.v_iso(2)]]
        plane = Plane3D.from_3_points(intersections_points[0][0], intersections_points[0][1],
                                      intersections_points[1][0])
        return self.plane_intersections(plane)

    def same_apex_conicalsurface_intersections(self, conical_surface):
        """
        Gets Conical Surface intersections with another conical surface, sharing the same apex.

        :param conical_surface: intersecting conical surface.
        :return: list of intersecting curves.
        """
        circle = self.v_iso(1)
        circle_intersections = conical_surface.circle_intersections(circle)
        if not circle_intersections:
            return []
        apex = self.apex
        return [curves.Line3D(apex, circle_intersections[0]),
                curves.Line3D(apex, circle_intersections[1])]

    def conicalsurface_intersections(self, conical_surface):
        """
        Conical Surface intersections with another conical surface.

        :param conical_surface: intersecting conical surface.
        :return: list of intersecting curves.
        """
        if self.frame.w.is_colinear_to(conical_surface.frame.w):
            return self.parallel_conicalsurface_intersections(conical_surface)
        if self.apex.is_close(conical_surface.apex):
            return self.same_apex_conicalsurface_intersections(conical_surface)
        if self.semi_angle + conical_surface.semi_angle > design3d.geometry.vectors3d_angle(
                self.frame.w, conical_surface.frame.w):
            intersection_points = self._conical_intersection_points(conical_surface, 5)
            local_intersections = [self.frame.global_to_local_coordinates(point) for point in intersection_points]
            max_z_point = design3d.O3D
            for point in local_intersections:
                if point.z > max_z_point.z:
                    max_z_point = point
            point_index = local_intersections.index(max_z_point)
            removed_point = intersection_points.pop(point_index)
            intersection_points.insert(0, removed_point)
            list_points = d3d_common_operations.order_points_list_for_nearest_neighbor(intersection_points)
            bspline = edges.BSplineCurve3D.from_points_interpolation(list_points, 3, centripetal=True)
            return [bspline]
        intersection_points = self._conical_intersection_points(conical_surface, 5)
        if not intersection_points:
            return []
        inters_points = d3d_common_operations.separate_points_by_closeness(intersection_points)
        curves_ = []
        for list_points in inters_points:
            bspline = edges.BSplineCurve3D.from_points_interpolation(list_points, 4, centripetal=False)
            curves_.append(bspline)
        return curves_

    def u_iso(self, u: float) -> curves.Line3D:
        """
        Returns the u-iso curve of the surface.

        :param u: The value of u where to extract the curve.
        :type u: float
        :return: A line 3D
        :rtype: :class:`curves.Line3D`
        """

        point1_at_u = self.point2d_to_3d(design3d.Point2D(u, 0.0))
        point2_at_u = self.point2d_to_3d(design3d.Point2D(u, 0.001))
        return curves.Line3D(point1_at_u, point2_at_u)

    def v_iso(self, v: float) -> curves.Circle3D:
        """
        Returns the v-iso curve of the surface.

        :param v: The value of u where to extract the curve.
        :type v: float
        :return: A Circle 3D
        :rtype: :class:`curves.Circle3D`
        """
        radius = abs(self.ref_radius + v * math.tan(self.semi_angle))
        if radius < 1e-15:
            return None
        frame = self.frame.translation(self.frame.w * v)
        return curves.Circle3D(frame, radius)

    def normal_at_point(self, point: design3d.Point3D):
        """
        Gets normal vector at given point on the surface.

        :param point: point to be verified.
        :return: normal
        """
        if not self.point_belongs(point):
            raise ValueError('Point given not on surface.')
        theta, z_apex = self.point3d_to_2d(point)

        normal = (math.cos(theta) * self.frame.u + math.sin(theta) * self.frame.v -
                  math.tan(self.semi_angle) * self.frame.w) / (math.sqrt(1 + math.tan(self.semi_angle)**2))
        if self.ref_radius + z_apex * math.tan(self.semi_angle) < 0:
            return - normal
        return normal


class SphericalSurface3D(UVPeriodicalSurface):
    """
    Defines a spherical surface.

    :param frame: Sphere's frame to position it
    :type frame: design3d.Frame3D
    :param radius: Sphere's radius
    :type radius: float
    """
    face_class = 'SphericalFace3D'
    x_periodicity = design3d.TWO_PI
    y_periodicity = math.pi

    def __init__(self, frame, radius, name=''):
        self.radius = radius
        UVPeriodicalSurface.__init__(self, frame=frame, name=name)

        # Hidden Attributes
        self._bbox = None

    def __hash__(self):
        return hash((self.__class__.__name__, self.frame, self.radius))

    def __eq__(self, other):
        if self.__class__.__name__ != other.__class__.__name__:
            return False
        if self.frame == other.frame and self.radius == other.radius:
            return True
        return False

    @property
    def domain_u(self):
        """The parametric domain of the surface in the U direction."""
        return -math.pi, math.pi

    @property
    def domain_v(self):
        """The parametric domain of the surface in the V direction."""
        return -math.pi, math.pi

    def _circle_generatrices(self, number_circles: int):
        """
        Gets the sphere circle generatrices.

        :param number_circles: number of circles to be created.
        :return: List of Circle 3D.
        """
        return [self.u_iso(theta) for theta in np.linspace(0, math.pi, number_circles)]

    def _circle_generatrices_xy(self, number_circles: int):
        """
        Gets the sphere circle generatrices in parallel planes.

        :param number_circles: number of circles to be created.
        :return: List of Circle 3D.
        """
        phi_angles = np.linspace(-0.5 * math.pi, 0.5 * math.pi, number_circles + 2)
        return [self.v_iso(phi) for phi in phi_angles[1:-1]]

    @property
    def domain(self):
        """Returns u and v bounds."""
        return -math.pi, math.pi, -0.5 * math.pi, 0.5 * math.pi

    @property
    def bounding_box(self):
        """Bounding Box for Spherical Surface 3D."""

        if not self._bbox:
            self._bbox = self._bounding_box()
        return self._bbox

    def _bounding_box(self):
        points = [self.frame.origin + design3d.Point3D(-self.radius,
                                                      -self.radius,
                                                      -self.radius),
                  self.frame.origin + design3d.Point3D(self.radius,
                                                      self.radius,
                                                      self.radius),

                  ]
        return design3d.core.BoundingBox.from_points(points)

    def get_circle_at_z(self, z_position: float):
        """
        Gets a circle on the sphere at given z position < radius.

        :param z_position: circle's z position.
        :return: circle 3D at given z position.
        """
        center1 = self.frame.origin.translation(self.frame.w * z_position)
        circle_radius = math.sqrt(self.radius ** 2 - center1.point_distance(self.frame.origin) ** 2)
        circle = curves.Circle3D(design3d.Frame3D(center1, self.frame.u, self.frame.v, self.frame.w), circle_radius)
        return circle

    def contour2d_to_3d(self, contour2d, return_primitives_mapping: bool = False):
        """
        Transforms a Contour2D in the parametric domain of the surface into a Contour3D in Cartesian coordinate.

        :param contour2d: The contour to be transformed.
        :type contour2d: :class:`wires.Contour2D`
        :param return_primitives_mapping: If True, returns a dictionary containing the correspondence between 2D and 3D
         primitives
        :type return_primitives_mapping: bool
        :return: A 3D contour object.
        :rtype: :class:`wires.Contour3D`
        """
        primitives3d = []
        primitives_mapping = {}
        for primitive2d in contour2d.primitives:
            if self.is_degenerated_brep(primitive2d) or primitive2d.name == "construction":
                continue
            method_name = f'{primitive2d.__class__.__name__.lower()}_to_3d'
            if hasattr(self, method_name):
                try:
                    primitives_list = getattr(self, method_name)(primitive2d)
                    if primitives_list:
                        primitives3d.extend(primitives_list)
                    else:
                        continue
                    primitives_mapping[primitive2d] = primitives_list[0]
                except AttributeError:
                    print(f'Class {self.__class__.__name__} does not implement {method_name}'
                          f'with {primitive2d.__class__.__name__}')
            else:
                raise AttributeError(f'Class {self.__class__.__name__} does not implement {method_name}')
        if return_primitives_mapping:
            return wires.Contour3D(primitives3d), primitives_mapping
        return wires.Contour3D(primitives3d)

    @classmethod
    def from_step(cls, arguments, object_dict, **kwargs):
        """
        Converts a step primitive to a SphericalSurface3D.

        :param arguments: The arguments of the step primitive.
        :type arguments: list
        :param object_dict: The dictionary containing all the step primitives
            that have already been instantiated.
        :type object_dict: dict
        :return: The corresponding SphericalSurface3D object.
        :rtype: :class:`design3d.faces.SphericalSurface3D`
        """
        length_conversion_factor = kwargs.get("length_conversion_factor", 1)

        frame = object_dict[arguments[1]]
        radius = float(arguments[2]) * length_conversion_factor
        return cls(frame, radius, arguments[0][1:-1])

    def to_step(self, current_id):
        """
        Converts the object to a STEP representation.

        :param current_id: The ID of the last written primitive.
        :type current_id: int
        :return: The STEP representation of the object and the last ID.
        :rtype: tuple[str, list[int]]
        """
        content, frame_id = self.frame.to_step(current_id)
        current_id = frame_id + 1
        content += f"#{current_id} = SPHERICAL_SURFACE('{self.name}',#{frame_id},{round(1000 * self.radius, 4)});\n"
        return content, [current_id]

    def point2d_to_3d(self, point2d):
        """
        Coverts a parametric coordinate on the surface into a 3D spatial point (x, y, z).

        source: https://mathcurve.com/surfaces/sphere
        # -pi<theta<pi, -pi/2<phi<pi/2

        :param point2d: Point at the CylindricalSuface3D.
        :type point2d: `design3d.`Point2D`
        """
        theta, phi = point2d
        x = self.radius * math.cos(phi) * math.cos(theta)
        y = self.radius * math.cos(phi) * math.sin(theta)
        z = self.radius * math.sin(phi)
        return self.frame.local_to_global_coordinates(design3d.Point3D(x, y, z))

    def point3d_to_2d(self, point3d):
        """
        Transform a 3D spatial point (x, y, z) into a 2D spherical parametric point (theta, phi).
        """
        x, y, z = self.frame.global_to_local_coordinates(point3d)
        z = min(self.radius, max(-self.radius, z))

        if z == -0.0:
            z = 0.0

        # Do not delete this, mathematical problem when x and y close to zero (should be zero) but not 0
        # Generally this is related to uncertainty of step files.
        if abs(x) < 1e-7:
            x = 0
        if abs(y) < 1e-7:
            y = 0

        theta = math.atan2(y, x)
        if abs(theta) < 1e-10:
            theta = 0

        z_over_r = z / self.radius
        phi = math.asin(z_over_r)
        if abs(phi) < 1e-10:
            phi = 0

        return design3d.Point2D(theta, phi)

    def parametric_points_to_3d(self, points: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Transform parametric coordinates to 3D points on the spherical surface.

        Given a set of parametric coordinates `(u, v)` representing points on the surface,
        this method returns the corresponding 3D points on the spherical surface.

        :param points: Parametric coordinates in the form of a numpy array with shape (n, 2),
                       where `n` is the number of points, and each row corresponds to `(u, v)`.
        :type points: numpy.ndarray[np.float64]

        :return: Array of 3D points representing the spherical surface in Cartesian coordinates.
        :rtype: numpy.ndarray[np.float64]
        """
        center = np.array(self.frame.origin)
        x = np.array([self.frame.u[0], self.frame.u[1], self.frame.u[2]])
        y = np.array([self.frame.v[0], self.frame.v[1], self.frame.v[2]])
        z = np.array([self.frame.w[0], self.frame.w[1], self.frame.w[2]])

        points = points.reshape(-1, 2, 1)

        u_values = points[:, 0]
        v_values = points[:, 1]

        common_term = self.radius * np.cos(v_values)
        x_component = np.cos(u_values) * x
        y_component = np.sin(u_values) * y
        z_component = self.radius * np.sin(v_values) * z

        return center + common_term * (x_component + y_component) + z_component

    def contour3d_to_2d(self, contour3d, return_primitives_mapping: bool = False):
        """
        Transforms a Contour3D into a Contour2D in the parametric domain of the surface.

        :param contour3d: The contour to be transformed.
        :type contour3d: :class:`wires.Contour3D`
        :param return_primitives_mapping: If True, returns a dictionary containing the correspondence between 2D and 3D
         primitives
        :type return_primitives_mapping: bool
        :return: A 2D contour object.
        :rtype: :class:`wires.Contour2D`
        """
        primitives2d = []
        primitives_mapping = {}
        # Transform the contour's primitives to parametric domain
        for primitive3d in contour3d.primitives:
            primitive3d = primitive3d.simplify if primitive3d.simplify.__class__.__name__ != "LineSegment3D" else \
                primitive3d
            method_name = f'{primitive3d.__class__.__name__.lower()}_to_2d'
            if hasattr(self, method_name):
                primitives = getattr(self, method_name)(primitive3d)

                if primitives is None:
                    continue
                self.update_primitives_mapping(primitives_mapping, primitives, primitive3d)
                primitives2d.extend(primitives)
            else:
                raise NotImplementedError(
                    f'Class {self.__class__.__name__} does not implement {method_name}')
        contour2d = wires.Contour2D(primitives2d)
        if contour2d.is_ordered(1e-2):
            if return_primitives_mapping:
                return contour2d, primitives_mapping
            return contour2d
        self.repair_primitives_periodicity(primitives2d, primitives_mapping)
        if return_primitives_mapping:
            return wires.Contour2D(primitives2d), primitives_mapping
        return wires.Contour2D(primitives2d)

    def is_lat_long_curve(self, arc):
        """
        Checks if a curve defined on the sphere is a latitude/longitude curve.

        Returns True if it is, False otherwise.
        """
        # Check if curve is a longitude curve (phi is constant)
        if self.frame.w.is_colinear_to(arc.circle.normal, abs_tol=1e-4):
            return True
        # Check if curve is a latitude curve (theta is constant)
        if self.frame.w.is_perpendicular_to(arc.circle.normal, abs_tol=1e-4) and \
                arc.circle.center.is_close(self.frame.origin, 1e-4):
            return True
        return False

    def _arc_start_end_3d_to_2d(self, arc3d):
        """
        Helper function to fix periodicity issues while performing transformations into parametric domain.
        """
        start = self.point3d_to_2d(arc3d.start)
        end = self.point3d_to_2d(arc3d.end)
        theta_i, _ = self.point3d_to_2d(arc3d.middle_point())
        theta1, phi1 = start
        theta2, phi2 = end
        point_after_start, point_before_end = self._reference_points(arc3d)
        theta3, _ = point_after_start
        theta4, _ = point_before_end

        # Fix sphere singularity point
        if math.isclose(abs(phi1), 0.5 * math.pi, abs_tol=1e-2) and theta1 == 0.0 \
                and math.isclose(theta3, theta_i, abs_tol=1e-2) and math.isclose(theta4, theta_i, abs_tol=1e-2):
            theta1 = theta_i
            start = design3d.Point2D(theta1, phi1)
        if math.isclose(abs(phi2), 0.5 * math.pi, abs_tol=1e-2) and theta2 == 0.0 \
                and math.isclose(theta3, theta_i, abs_tol=1e-2) and math.isclose(theta4, theta_i, abs_tol=1e-2):
            theta2 = theta_i
            end = design3d.Point2D(theta2, phi2)
        discontinuity, _, _ = self._helper_arc3d_to_2d_periodicity_verifications(arc3d, start)

        start, end = d3d_parametric.arc3d_to_spherical_coordinates_verification(
            [start, end], [point_after_start, point_before_end], discontinuity)
        return start, end

    def edge_passes_on_singularity_point(self, edge):
        """Helper function to verify id edge passes on the sphere singularity point."""
        half_pi = 0.5 * math.pi
        point_positive_singularity = self.point2d_to_3d(design3d.Point2D(0, half_pi))
        point_negative_singularity = self.point2d_to_3d(design3d.Point2D(0, -half_pi))
        positive_singularity = edge.point_belongs(point_positive_singularity, 1e-6)
        negative_singularity = edge.point_belongs(point_negative_singularity, 1e-6)
        if positive_singularity and negative_singularity:
            return [point_positive_singularity, point_negative_singularity]
        if positive_singularity:
            return [point_positive_singularity, None]
        if negative_singularity:
            return [None, point_negative_singularity]
        return [None, None]

    def arc3d_to_2d(self, arc3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        is_lat_long_curve = self.is_lat_long_curve(arc3d)
        if is_lat_long_curve:
            start, end = self._arc_start_end_3d_to_2d(arc3d)
            singularity_points = self.edge_passes_on_singularity_point(arc3d)
            if any(singularity_points):
                return self.arc3d_to_2d_with_singularity(arc3d, start, end, singularity_points)
            return [edges.LineSegment2D(start, end)]
        return self.arc3d_to_2d_any_direction(arc3d)

    def helper_arc3d_to_2d_with_singularity(self, arc3d, start, end, point_singularity, half_pi):
        """Helper function to arc3d_to_2d_with_singularity."""
        theta1, phi1 = start
        theta2, phi2 = end
        if arc3d.is_point_edge_extremity(point_singularity):
            return [edges.LineSegment2D(start, end)]
        if math.isclose(abs(theta2 - theta1), math.pi, abs_tol=1e-2):
            if theta1 == math.pi and theta2 != math.pi:
                theta1 = -math.pi
            if theta2 == math.pi and theta1 != math.pi:
                theta2 = -math.pi

            primitives = [edges.LineSegment2D(design3d.Point2D(theta1, phi1),
                                              design3d.Point2D(theta1, half_pi)),
                          edges.LineSegment2D(design3d.Point2D(theta1, half_pi),
                                              design3d.Point2D(theta2, half_pi),
                                              name="construction"),
                          edges.LineSegment2D(
                              design3d.Point2D(
                                  theta2, half_pi), design3d.Point2D(
                                  theta2, phi2))
                          ]
            return primitives
        n = 20
        degree = 2
        points = [self.point3d_to_2d(point3d) for point3d in arc3d.discretization_points(number_points=n)]
        return [edges.BSplineCurve2D.from_points_interpolation(points, degree)]

    def arc3d_to_2d_with_singularity(self, arc3d, start, end, singularity_points):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        # trying to treat when the arc starts at theta1 passes at the singularity at |phi| = 0.5*math.pi
        # and ends at theta2 = theta1 + math.pi
        theta1, phi1 = start
        theta2, phi2 = end

        half_pi = 0.5 * math.pi
        point_positive_singularity, point_negative_singularity = singularity_points

        if point_positive_singularity and point_negative_singularity:
            if arc3d.is_point_edge_extremity(point_positive_singularity) and \
                    arc3d.is_point_edge_extremity(point_negative_singularity):
                return [edges.LineSegment2D(start, end)]
            direction_vector = arc3d.direction_vector(0)
            dot = self.frame.w.dot(direction_vector)
            if dot == 0:
                direction_vector = arc3d.direction_vector(0.01 * arc3d.length())
                dot = self.frame.w.dot(direction_vector)
            if dot > 0:
                half_pi = 0.5 * math.pi
                thetai = theta1 - math.pi
            else:
                half_pi = -0.5 * math.pi
                thetai = theta1 + math.pi
            if arc3d.is_point_edge_extremity(point_positive_singularity):
                return [
                    edges.LineSegment2D(start, design3d.Point2D(start.x, -0.5 * math.pi)),
                    edges.LineSegment2D(design3d.Point2D(start.x, -0.5 * math.pi),
                                        design3d.Point2D(theta2, -0.5 * math.pi),
                                        name="construction"),
                    edges.LineSegment2D(design3d.Point2D(theta2, -0.5 * math.pi),
                                        design3d.Point2D(theta2, phi2))
                ]
            if arc3d.is_point_edge_extremity(point_negative_singularity):
                return [
                    edges.LineSegment2D(start, design3d.Point2D(start.x, 0.5 * math.pi)),
                    edges.LineSegment2D(design3d.Point2D(start.x, 0.5 * math.pi),
                                        design3d.Point2D(theta2, 0.5 * math.pi),
                                        name="construction"),
                    edges.LineSegment2D(design3d.Point2D(theta2, 0.5 * math.pi),
                                        design3d.Point2D(theta2, phi2))
                ]
            return [edges.LineSegment2D(design3d.Point2D(theta1, phi1), design3d.Point2D(theta1, half_pi)),
                    edges.LineSegment2D(design3d.Point2D(theta1, half_pi), design3d.Point2D(thetai, half_pi),
                                        name="construction"),
                    edges.LineSegment2D(design3d.Point2D(thetai, half_pi),
                                        design3d.Point2D(thetai, -half_pi)),
                    edges.LineSegment2D(design3d.Point2D(thetai, -half_pi),
                                        design3d.Point2D(theta2, -half_pi),
                                        name="construction"),
                    edges.LineSegment2D(design3d.Point2D(theta2, -half_pi), design3d.Point2D(theta2, phi2))
                    ]
        if point_positive_singularity:
            return self.helper_arc3d_to_2d_with_singularity(arc3d, start, end, point_positive_singularity, half_pi)
        if point_negative_singularity:
            return self.helper_arc3d_to_2d_with_singularity(arc3d, start, end, point_negative_singularity, -half_pi)

        raise NotImplementedError

    @staticmethod
    def _fix_start_end_singularity_point_at_parametric_domain(edge, reference_point, point_at_singularity):
        """Uses tangent line to find real theta angle of the singularity point on parametric domain."""
        _, phi = point_at_singularity
        abscissa_before_singularity = edge.abscissa(reference_point)
        direction_vector = edge.direction_vector(abscissa_before_singularity)
        direction_line = curves.Line2D(reference_point, reference_point + direction_vector)
        if phi > 0:
            line_positive_singularity = curves.Line2D(design3d.Point2D(-math.pi, 0.5 * math.pi),
                                                      design3d.Point2D(math.pi, 0.5 * math.pi))
            intersections = direction_line.line_intersections(line_positive_singularity)
            if intersections:
                return intersections[0]
            return intersections

        line_negative_singularity = curves.Line2D(design3d.Point2D(-math.pi, -0.5 * math.pi),
                                                  design3d.Point2D(math.pi, -0.5 * math.pi))

        intersections = direction_line.line_intersections(line_negative_singularity)
        if intersections:
            return intersections[0]
        return intersections

    def is_point2d_on_sphere_singularity(self, point2d, tol=1e-5):
        """Verifies if point is on the spherical singularity point on parametric domain."""
        half_pi = 0.5 * math.pi
        point = self.point2d_to_3d(point2d)
        point_positive_singularity = self.point2d_to_3d(design3d.Point2D(0, half_pi))
        point_negative_singularity = self.point2d_to_3d(design3d.Point2D(0, -half_pi))
        if point.is_close(point_positive_singularity, tol) or point.is_close(point_negative_singularity, tol):
            return True
        return False

    def is_point3d_on_sphere_singularity(self, point3d):
        """Verifies if point is on the spherical singularity point on parametric domain."""
        half_pi = 0.5 * math.pi
        point_positive_singularity = self.point2d_to_3d(design3d.Point2D(0, half_pi))
        point_negative_singularity = self.point2d_to_3d(design3d.Point2D(0, -half_pi))
        if point3d.is_close(point_positive_singularity) or point3d.is_close(point_negative_singularity):
            return True
        return False

    def find_edge_start_end_undefined_parametric_points(self, edge3d, points, points3d):
        """
        Helper function.

        Uses local discretization and line intersection with the tangent line at the point just before the undefined
        point on the BREP of the 3D edge to find the real value of theta on the sphere parametric domain.
        """

        def get_temp_edge2d(_points):
            if len(_points) == 2:
                edge2d = edges.LineSegment2D(_points[0], _points[1])
            else:
                edge2d = edges.BSplineCurve2D.from_points_interpolation(_points, 2)
            return edge2d

        if self.is_point3d_on_sphere_singularity(points3d[0]):
            distance = points3d[0].point_distance(points3d[1])
            maximum_linear_distance_reference_point = 1e-5
            if distance < maximum_linear_distance_reference_point:
                temp_points = points[1:]
            else:
                number_points = max(2, int(distance / maximum_linear_distance_reference_point))

                local_discretization = [self.point3d_to_2d(point)
                                        for point in edge3d.local_discretization(
                        points3d[0], points3d[1], number_points)]
                temp_points = local_discretization[1:] + points[2:]

            theta_list = [point.x for point in temp_points]
            theta_discontinuity, indexes_theta_discontinuity = angle_discontinuity(theta_list)

            if theta_discontinuity:
                temp_points = self._fix_angle_discontinuity_on_discretization_points(temp_points,
                                                                                     indexes_theta_discontinuity, "x")

            edge = get_temp_edge2d(temp_points)
            point = self._fix_start_end_singularity_point_at_parametric_domain(edge,
                                                                               reference_point=temp_points[1],
                                                                               point_at_singularity=points[0])
            if point:
                points[0] = point
            else:
                per = 0.001
                while per < 0.05:
                    point = self.point3d_to_2d(edge3d.point_at_abscissa(per * edge3d.length()))
                    if point != points[0]:
                        break
                    per += 0.0025
                points[0] = point
        if self.is_point3d_on_sphere_singularity(points3d[-1]):
            distance = points3d[-2].point_distance(points3d[-1])
            maximum_linear_distance_reference_point = 1e-5
            if distance < maximum_linear_distance_reference_point:
                temp_points = points[:-1]
            else:
                number_points = max(2, int(distance / maximum_linear_distance_reference_point))

                local_discretization = [self.point3d_to_2d(point)
                                        for point in edge3d.local_discretization(
                        points3d[-2], points3d[-1], number_points)]
                temp_points = points[:-2] + local_discretization[:-1]

            theta_list = [point.x for point in temp_points]
            theta_discontinuity, indexes_theta_discontinuity = angle_discontinuity(theta_list)

            if theta_discontinuity:
                temp_points = self._fix_angle_discontinuity_on_discretization_points(
                    temp_points, indexes_theta_discontinuity, "x")

            edge = get_temp_edge2d(temp_points)
            point = self._fix_start_end_singularity_point_at_parametric_domain(
                edge, reference_point=temp_points[-2], point_at_singularity=points[-1])
            if point:
                points[-1] = point
            else:
                per = 0.999
                while per > 0.95:
                    point = self.point3d_to_2d(edge3d.point_at_abscissa(per * edge3d.length()))
                    if point != points[-1]:
                        break
                    per -= 0.0025
                points[-1] = point
        return points

    def arc3d_to_2d_any_direction_singularity(self, arc3d, point_singularity, half_pi):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        split = arc3d.split(point_singularity)
        primitive0 = self.arc3d_to_2d_any_direction(split[0])[0]
        primitive2 = self.arc3d_to_2d_any_direction(split[1])[0]
        primitive1 = edges.LineSegment2D(design3d.Point2D(primitive0.end.x, half_pi),
                                         design3d.Point2D(primitive2.start.x, half_pi))
        return [primitive0, primitive1, primitive2]

    def arc3d_to_2d_any_direction(self, arc3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        singularity_points = self.edge_passes_on_singularity_point(arc3d)
        half_pi = 0.5 * math.pi  # this variable avoid doing this multiplication several times (performance)
        point_positive_singularity, point_negative_singularity = singularity_points

        if point_positive_singularity and point_negative_singularity:
            raise ValueError("Impossible. This case should be treated by arc3d_to_2d_with_singularity method."
                             "See arc3d_to_2d method for detail.")
        if point_positive_singularity and not arc3d.is_point_edge_extremity(point_positive_singularity):
            return self.arc3d_to_2d_any_direction_singularity(arc3d, point_positive_singularity, half_pi)
        if point_negative_singularity and not arc3d.is_point_edge_extremity(point_negative_singularity):
            return self.arc3d_to_2d_any_direction_singularity(arc3d, point_negative_singularity, -half_pi)

        number_points = max(math.ceil(arc3d.angle * 50) + 1, 5)
        points3d = arc3d.discretization_points(number_points=number_points)
        points = [self.point3d_to_2d(p) for p in points3d]
        point_after_start, point_before_end = self._reference_points(arc3d)
        start, end = d3d_parametric.spherical_repair_start_end_angle_periodicity(
            points[0], points[-1], point_after_start, point_before_end)
        points[0] = start
        points[-1] = end

        points = self.find_edge_start_end_undefined_parametric_points(arc3d, points, points3d)
        theta_discontinuity, indexes_theta_discontinuity = angle_discontinuity([point.x for point in points])

        if theta_discontinuity:
            points = self._fix_angle_discontinuity_on_discretization_points(points,
                                                                            indexes_theta_discontinuity, "x")

        return [edges.BSplineCurve2D.from_points_interpolation(points, 2)]

    def bsplinecurve3d_to_2d(self, bspline_curve3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        n = bspline_curve3d.ctrlpts.shape[0]
        points3d = bspline_curve3d.discretization_points(number_points=n)
        points = [self.point3d_to_2d(point) for point in points3d]

        point_after_start, point_before_end = self._reference_points(bspline_curve3d)
        start, end = d3d_parametric.spherical_repair_start_end_angle_periodicity(
            points[0], points[-1], point_after_start, point_before_end)
        points[0] = start
        points[-1] = end
        if start.x == 0.0 or end.x == 0.0:
            points = self.find_edge_start_end_undefined_parametric_points(bspline_curve3d, points, points3d)
        theta_list = [point.x for point in points]
        theta_discontinuity, indexes_theta_discontinuity = angle_discontinuity(theta_list)
        if theta_discontinuity:
            points = self._fix_angle_discontinuity_on_discretization_points(points,
                                                                            indexes_theta_discontinuity, "x")
        degree = bspline_curve3d.degree
        if degree > len(points) - 1:
            degree = len(points) - 1
        return [edges.BSplineCurve2D.from_points_interpolation(points, degree=degree).simplify]

    def bsplinecurve2d_to_3d(self, bspline_curve2d):
        """
        Converts a BREP BSpline curve 2D onto a 3D primitive on the surface.
        """
        # TODO: this is incomplete, a bspline_curve2d can be also a bspline_curve3d
        i = round(0.5 * len(bspline_curve2d.points))
        start = self.point2d_to_3d(bspline_curve2d.points[0])
        interior = self.point2d_to_3d(bspline_curve2d.points[i])
        end = self.point2d_to_3d(bspline_curve2d.points[-1])
        vector_u1 = interior - start
        vector_u2 = interior - end
        points3d = [self.point2d_to_3d(p) for p in bspline_curve2d.points]
        if vector_u1.cross(vector_u2).norm():
            arc3d = edges.Arc3D.from_3_points(start, interior, end)
            flag = True
            for point in points3d:
                if not arc3d.point_belongs(point, 1e-4):
                    flag = False
                    break
            if flag:
                return [arc3d]

        return [edges.BSplineCurve3D.from_points_interpolation(points3d, degree=bspline_curve2d.degree,
                                                               centripetal=True)]

    def arc2d_to_3d(self, arc2d):
        """
        Converts a BREP arc 2D onto a 3D primitive on the surface.
        """
        n = 10
        degree = 2
        points = [self.point2d_to_3d(point2d) for point2d in arc2d.discretization_points(number_points=n)]
        return [edges.BSplineCurve3D.from_points_interpolation(points, degree).simplify]

    @staticmethod
    def _horizontal_fullarc3d_to_2d(theta1, theta3, phi1, phi2):
        """
        Helper Convert primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.

        """
        point1 = design3d.Point2D(theta1, phi1)
        if theta1 > theta3:
            point2 = design3d.Point2D(theta1 - design3d.TWO_PI, phi2)
        elif theta1 < theta3:
            point2 = design3d.Point2D(theta1 + design3d.TWO_PI, phi2)
        return [edges.LineSegment2D(point1, point2)]

    @staticmethod
    def _vertical_through_origin_fullarc3d_to_2d(theta1, theta3, theta4, phi1, phi2, phi3):
        """
        Helper Convert primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        if theta1 > theta3:
            theta_plus_pi = theta1 - math.pi
        else:
            theta_plus_pi = theta1 + math.pi
        if phi1 > phi3:
            half_pi = 0.5 * math.pi
        else:
            half_pi = -0.5 * math.pi
        if abs(phi1) == 0.5 * math.pi:
            return [edges.LineSegment2D(design3d.Point2D(theta3, phi1),
                                        design3d.Point2D(theta3, -half_pi)),
                    edges.LineSegment2D(design3d.Point2D(theta4, -half_pi),
                                        design3d.Point2D(theta4, phi2))]

        return [edges.LineSegment2D(design3d.Point2D(theta1, phi1), design3d.Point2D(theta1, -half_pi)),
                edges.LineSegment2D(design3d.Point2D(theta_plus_pi, -half_pi),
                                    design3d.Point2D(theta_plus_pi, half_pi)),
                edges.LineSegment2D(design3d.Point2D(theta1, half_pi), design3d.Point2D(theta1, phi2))]

    def fullarc3d_to_2d(self, fullarc3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        # TODO: On a spherical surface we can have fullarc3d in any plane
        start, end = self._arc_start_end_3d_to_2d(fullarc3d)
        theta1, phi1 = start
        theta2, phi2 = end

        point_after_start, point_before_end = self._reference_points(fullarc3d)
        theta3, phi3 = point_after_start
        theta4, _ = point_before_end

        if self.frame.w.is_colinear_to(fullarc3d.circle.normal, abs_tol=1e-4):
            return self._horizontal_fullarc3d_to_2d(theta1, theta3, phi1, phi2)

        if self.frame.w.is_perpendicular_to(fullarc3d.circle.normal, abs_tol=1e-4) and \
                self.frame.origin.is_close(fullarc3d.center):
            return self._vertical_through_origin_fullarc3d_to_2d(theta1, theta3, theta4, phi1, phi2, phi3)

        points = [self.point3d_to_2d(p) for p in fullarc3d.discretization_points(angle_resolution=25)]

        # Verify if theta1 or theta2 point should be -pi because atan2() -> ]-pi, pi]
        theta1 = d3d_parametric.repair_start_end_angle_periodicity(theta1, theta3)
        theta2 = d3d_parametric.repair_start_end_angle_periodicity(theta2, theta4)

        points[0] = design3d.Point2D(theta1, phi1)
        points[-1] = design3d.Point2D(theta2, phi2)

        theta_list = [point.x for point in points]
        theta_discontinuity, indexes_theta_discontinuity = angle_discontinuity(theta_list)
        if theta_discontinuity:
            points = self._fix_angle_discontinuity_on_discretization_points(points, indexes_theta_discontinuity, "x")

        return [edges.BSplineCurve2D.from_points_interpolation(points, 2)]

    def plot(self, ax=None, edge_style: EdgeStyle = EdgeStyle(color='grey', alpha=0.5), **kwargs):
        """Plot sphere arcs."""
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')

        self.frame.plot(ax=ax, ratio=self.radius)
        for circle in self._circle_generatrices(50) + self._circle_generatrices_xy(50):
            circle.plot(ax, edge_style)
        return ax

    def rectangular_cut(self, theta1, theta2, phi1, phi2, name=''):
        """Deprecated method, Use ShericalFace3D from_surface_rectangular_cut method."""
        raise AttributeError('Use ShericalFace3D from_surface_rectangular_cut method')

    def triangulation(self):
        """
        Triangulation of Spherical Surface.

        """
        face = self.rectangular_cut(0, design3d.TWO_PI, -0.5 * math.pi, 0.5 * math.pi)
        return face.triangulation()

    def check_parametric_contour_end(self, primitives2d, tol):
        """Helper function to repair_primitives_periodicity."""
        last_end = primitives2d[-1].end
        first_start = primitives2d[0].start
        if not last_end.is_close(first_start, tol=tol):
            last_end_3d = self.point2d_to_3d(last_end)
            first_start_3d = self.point2d_to_3d(first_start)
            if last_end_3d.is_close(first_start_3d, 1e-6) and not self.is_singularity_point(last_end_3d):
                if first_start.x > last_end.x:
                    half_pi = -0.5 * math.pi
                else:
                    half_pi = 0.5 * math.pi
                if not first_start.is_close(design3d.Point2D(first_start.x, half_pi)):
                    lines = [edges.LineSegment2D(
                        last_end, design3d.Point2D(last_end.x, half_pi), name="construction"),
                        edges.LineSegment2D(design3d.Point2D(last_end.x, half_pi),
                                            design3d.Point2D(first_start.x, half_pi), name="construction"),
                        edges.LineSegment2D(design3d.Point2D(first_start.x, half_pi),
                                            first_start, name="construction")]
                    primitives2d.extend(lines)
            else:
                primitives2d.append(edges.LineSegment2D(last_end, first_start, name="construction"))

    def is_singularity_point(self, point, *args, **kwargs):
        """Verifies if point is on the surface singularity."""
        tol = kwargs.get("tol", 1e-6)
        positive_singularity = self.point2d_to_3d(design3d.Point2D(0.0, 0.5 * math.pi))
        negative_singularity = self.point2d_to_3d(design3d.Point2D(0.0, -0.5 * math.pi))
        return bool(positive_singularity.is_close(point, tol) or negative_singularity.is_close(point, tol))

    def rotation(self, center: design3d.Point3D, axis: design3d.Vector3D, angle: float):
        """
        Spherical Surface 3D rotation.

        :param center: rotation center
        :param axis: rotation axis
        :param angle: angle rotation
        :return: a new rotated Spherical Surface 3D
        """
        new_frame = self.frame.rotation(center=center, axis=axis, angle=angle)
        return SphericalSurface3D(new_frame, self.radius)

    def translation(self, offset: design3d.Vector3D):
        """
        Spherical Surface 3D translation.

        :param offset: translation vector
        :return: A new translated Spherical Surface 3D
        """
        new_frame = self.frame.translation(offset)
        return SphericalSurface3D(new_frame, self.radius)

    def frame_mapping(self, frame: design3d.Frame3D, side: str):
        """
        Changes Spherical Surface 3D's frame and return a new Spherical Surface 3D.

        :param frame: Frame of reference
        :type frame: `design3d.Frame3D`
        :param side: 'old' or 'new'
        """
        new_frame = self.frame.frame_mapping(frame, side)
        return SphericalSurface3D(new_frame, self.radius)

    def plane_intersections(self, plane3d):
        """
        Sphere intersections with a plane.

        :param plane3d: intersecting plane.
        :return: list of intersecting curves.
        """
        dist = plane3d.point_distance(self.frame.origin)
        if dist > self.radius:
            return []
        if dist == self.radius:
            line = curves.Line3D(self.frame.origin, self.frame.origin + plane3d.frame.w)
            return plane3d.line_intersections(line)
        line = curves.Line3D(self.frame.origin, self.frame.origin + plane3d.frame.w)
        circle_radius = math.sqrt(self.radius ** 2 - dist ** 2)
        circle_center = plane3d.line_intersections(line)[0]
        start_end = circle_center + plane3d.frame.u * circle_radius
        circle = curves.Circle3D(design3d.Frame3D(circle_center, plane3d.frame.u,
                                                 plane3d.frame.v, plane3d.frame.w),
                                 circle_radius)
        return [edges.FullArc3D(circle, start_end)]

    def line_intersections(self, line: curves.Line3D):
        """
        Calculates the intersection points between a 3D line and a spherical surface.

        The method calculates the intersection points between a 3D line and a sphere using
        the equation of the line and the equation of the sphere. It returns a list of intersection
        points, which can be empty if there are no intersections. The intersection points are
        represented as 3D points using the `design3d.Point3D` class.

        :param line: The 3D line object to intersect with the sphere.
        :type line:curves.Line3D
        :return: A list of intersection points between the line and the sphere. The list may be empty if there
        are no intersections.
        :rtype: List[design3d.Point3D]

        :Example:
        >>> from design3d import Point3D, edges, surfaces, OXYZ
        >>> spherical_surface3d = SphericalSurface3D(OXYZ, 1)
        >>> line2 = curves.Line3D(Point3D(0, 1, -0.5), Point3D(0, 1, 0.5))
        >>> line_intersections2 = spherical_surface3d.line_intersections(line2) #returns [Point3D(0.0, 1.0, 0.0)]
        """
        line_direction_vector = line.direction_vector()
        vector_linept1_center = self.frame.origin - line.point1
        vector_linept1_center = vector_linept1_center.to_vector()
        a_param = line_direction_vector[0] ** 2 + line_direction_vector[1] ** 2 + line_direction_vector[2] ** 2
        b_param = -2 * (line_direction_vector[0] * vector_linept1_center[0] +
                        line_direction_vector[1] * vector_linept1_center[1] +
                        line_direction_vector[2] * vector_linept1_center[2])
        c_param = (vector_linept1_center[0] ** 2 + vector_linept1_center[1] ** 2 +
                   vector_linept1_center[2] ** 2 - self.radius ** 2)
        b2_minus4ac = b_param ** 2 - 4 * a_param * c_param
        if math.isclose(b2_minus4ac, 0, abs_tol=1e-8):
            t_param = -b_param / (2 * a_param)
            return [line.point1 + line_direction_vector * t_param]
        if b2_minus4ac < 0:
            return []
        t_param1 = (-b_param + math.sqrt(b2_minus4ac)) / (2 * a_param)
        t_param2 = (-b_param - math.sqrt(b2_minus4ac)) / (2 * a_param)
        return line.point1 + line_direction_vector * t_param1, line.point1 + line_direction_vector * t_param2

    def circle_intersections(self, circle: curves.Circle3D):
        """
        Gets intersections between a circle 3D and a SphericalSurface3D.

        :param circle: other circle to search intersections with.
        :return: list containing the intersection points.
        """
        circle_plane = Plane3D(circle.frame)
        if circle_plane.point_distance(self.frame.origin) > self.radius:
            return []
        circle_plane_intersections = self.plane_intersections(circle_plane)
        if circle_plane_intersections and isinstance(circle_plane_intersections[0], design3d.Point3D):
            return []
        intersections = circle_plane_intersections[0].circle.circle_intersections(circle)
        return intersections

    def arc_intersections(self, arc: edges.Arc3D):
        """
        Gets intersections between an arc 3D and a SphericalSurface3D.

        :param arc: other arc to search intersections with.
        :return: list containing the intersection points.
        """
        circle_intersections = self.circle_intersections(arc.circle)
        intersections = [intersection for intersection in circle_intersections if arc.point_belongs(intersection)]
        return intersections

    def fullarc_intersections(self, fullarc: edges.Arc3D):
        """
        Gets intersections between a fullarc 3D and a SphericalSurface3D.

        :param fullarc: other fullarc to search intersections with.
        :return: list containing the intersection points.
        """
        return self.circle_intersections(fullarc.circle)

    def ellipse_intersections(self, ellipse: curves.Ellipse3D):
        """
        Gets intersections between an ellipse 3D and a SphericalSurface3D.

        :param ellipse: other ellipse to search intersections with.
        :return: list containing the intersection points.
        """
        ellipse_plane = Plane3D(ellipse.frame)
        if ellipse_plane.point_distance(self.frame.origin) > self.radius:
            return []
        ellipse_plane_intersections = self.plane_intersections(ellipse_plane)
        intersections = ellipse_plane_intersections[0].circle.ellipse_intersections(ellipse)
        return intersections

    def arcellipse_intersections(self, arcellipse: edges.ArcEllipse3D):
        """
        Gets intersections between an arcellipse 3D and a SphericalSurface3D.

        :param arcellipse: other arcellipse to search intersections with.
        :return: list containing the intersection points.
        """
        circle_intersections = self.ellipse_intersections(arcellipse.ellipse)
        intersections = [intersection for intersection in circle_intersections
                         if arcellipse.point_belongs(intersection)]
        return intersections

    def fullarcellipse_intersections(self, fullarcellipse: edges.FullArcEllipse3D):
        """
        Gets intersections between a full arcellipse 3D and a SphericalSurface3D.

        :param fullarcellipse: other full arcellipse to search intersections with.
        :return: list containing the intersection points.
        """
        return self.ellipse_intersections(fullarcellipse.ellipse)

    def _spherical_intersection_points(self, spherical_surface: 'SphericalSurface3D'):
        """
        Gets the points of intersections between the spherical surface and the toroidal surface.

        :param spherical_surface: other Spherical Surface 3d.
        :return: points of intersections.
        """
        cyl_generatrices = self._circle_generatrices(200) + self._circle_generatrices_xy(200)
        intersection_points = []
        for gene in cyl_generatrices:
            intersections = spherical_surface.edge_intersections(gene)
            for intersection in intersections:
                if not intersection.in_list(intersection_points):
                    intersection_points.append(intersection)
        return intersection_points

    def sphericalsurface_intersections(self, spherical_surface: 'SphericalSurface3D'):
        """
        Cylinder Surface intersections with a Spherical surface.

        :param spherical_surface: intersecting sphere.
        :return: list of intersecting curves.
        """
        intersection_points = self._spherical_intersection_points(spherical_surface)
        if not intersection_points:
            return []
        inters_points = d3d_common_operations.separate_points_by_closeness(intersection_points)
        curves_ = []
        for list_points in inters_points:
            bspline = edges.BSplineCurve3D.from_points_interpolation(list_points, 4, centripetal=False)
            if isinstance(bspline.simplify, edges.FullArc3D):
                curves_.append(bspline.simplify)
                continue
            curves_.append(bspline)
        return curves_

    def u_iso(self, u: float) -> curves.Circle3D:
        """
        Returns the u-iso curve of the surface.

        :param u: The value of u where to extract the curve.
        :type u: float
        :return: A circle 3D
        :rtype: :class:`curves.Circle3D`
        """

        center = self.frame.origin
        point_at_u_v0 = self.point2d_to_3d(design3d.Point2D(u, 0.0))
        u_vector = (point_at_u_v0 - center).unit_vector()
        frame = design3d.Frame3D(center, u_vector, self.frame.w, u_vector.cross(self.frame.w))
        return curves.Circle3D(frame, self.radius)

    def v_iso(self, v: float) -> curves.Circle3D:
        """
        Returns the v-iso curve of the surface.

        :param v: The value of u where to extract the curve.
        :type v: float
        :return: A Circle 3D
        :rtype: :class:`curves.Circle3D`
        """
        radius = self.radius * math.cos(v)
        if radius < 1e-15:
            return None
        z = self.radius * math.sin(v)
        frame = self.frame.translation(self.frame.w * z)
        return curves.Circle3D(frame, radius)

    def normal_at_point(self, point: design3d.Point3D):
        """
        Gets normal vector at given point on the surface.

        :param point: point to be verified.
        :return: normal
        """
        if not self.point_belongs(point):
            raise ValueError('Point given not on surface.')
        theta, phi = self.point3d_to_2d(point)
        normal = math.cos(phi) * (math.cos(theta) * self.frame.u +
                                  math.sin(theta) * self.frame.v) + math.sin(theta) * self.frame.w
        return normal



class RuledSurface3D(Surface3D):
    """
    Defines a ruled surface between two wires.

    :param wire1: Wire
    :type wire1: :class:`d3dw.Wire3D`
    :param wire2: Wire
    :type wire2: :class:`wires.Wire3D`
    """
    face_class = 'RuledFace3D'

    def __init__(self, wire1: wires.Wire3D, wire2: wires.Wire3D, name: str = ''):
        self.wire1 = wire1
        self.wire2 = wire2
        self.length1 = wire1.length()
        self.length2 = wire2.length()
        Surface3D.__init__(self, name=name)

    def __hash__(self):
        return hash((self.__class__.__name__, self.wire1, self.wire2))

    def __eq__(self, other):
        if self.__class__.__name__ != other.__class__.__name__:
            return False
        if self.wire1 == other.wire1 and self.wire2 == other.wire2:
            return True
        return False

    def point2d_to_3d(self, point2d: design3d.Point2D):
        """
        Coverts a parametric coordinate on the surface into a 3D spatial point (x, y, z).

        :param point2d: Point at the ToroidalSuface3D
        :type point2d: `design3d.`Point2D`
        """
        x, y = point2d
        point1 = self.wire1.point_at_abscissa(x * self.length1)
        point2 = self.wire2.point_at_abscissa(x * self.length2)
        joining_line = edges.LineSegment3D(point1, point2)
        point = joining_line.point_at_abscissa(y * joining_line.length())
        return point

    def point3d_to_2d(self, point3d):
        """
        Returns the parametric coordinates design3d.Point2D(u, v) of a cartesian coordinates point (x, y, z).

        :param point3d: Point at the CylindricalSuface3D
        :type point3d: `design3d.`Point3D`
        """
        raise NotImplementedError

    def rectangular_cut(self, x1: float, x2: float,
                        y1: float, y2: float, name: str = ''):
        """Deprecated method, Use RuledFace3D from_surface_rectangular_cut method."""
        raise NotImplementedError('Use RuledFace3D from_surface_rectangular_cut method')


class ExtrusionSurface3D(Surface3D):
    """
    Defines a surface of extrusion.

    An extrusion surface is a surface that is a generic cylindrical surface generated by the linear
    extrusion of a curve, generally an Ellipse or a B-Spline curve.

    :param edge: edge.
    :type edge: Union[:class:`d3dw.Wire3D`, :class:`d3dw.Contour3D`]
    :param axis_point: Axis placement
    :type axis_point: :class:`design3d.Point3D`
    :param axis: Axis of extrusion
    :type axis: :class:`design3d.Vector3D`
    """
    face_class = 'ExtrusionFace3D'
    y_periodicity = None

    def __init__(self, edge: Union[edges.FullArcEllipse3D, edges.BSplineCurve3D],
                 direction: design3d.Vector3D, name: str = ''):
        self.edge = edge
        direction = direction.unit_vector()
        self.direction = direction
        if hasattr(edge, "center"):
            frame = design3d.Frame3D.from_point_and_vector(edge.center, direction, design3d.Z3D)
        else:
            frame = design3d.Frame3D.from_point_and_vector(edge.start, direction, design3d.Z3D)
        self._x_periodicity = False

        Surface3D.__init__(self, frame=frame, name=name)

    def __hash__(self):
        return hash((self.__class__.__name__, self.edge, self.direction))

    def __eq__(self, other):
        if self.__class__.__name__ != other.__class__.__name__:
            return False
        if self.edge == other.edge and self.direction == other.direction:
            return True
        return False

    @property
    def x_periodicity(self):
        """Returns the periodicity in x direction."""
        if self._x_periodicity:
            return self._x_periodicity
        start = self.edge.start
        end = self.edge.end
        if start.is_close(end, 1e-6):
            self._x_periodicity = self.edge.length()
            return self._x_periodicity
        return None

    @x_periodicity.setter
    def x_periodicity(self, value):
        """X periodicity setter."""
        self._x_periodicity = value

    @property
    def u_domain(self):
        """The parametric domain of the surface in the U direction."""
        return 0.0, self.edge.length()

    @property
    def v_domain(self):
        """The parametric domain of the surface in the V direction."""
        return -math.inf, math.inf

    def point2d_to_3d(self, point2d: design3d.Point2D):
        """
        Transform a parametric (u, v) point into a 3D Cartesian point (x, y, z).

        # u = [0, 1] and v = z
        """
        u, v = point2d
        if abs(u) < 1e-7:
            u = 0.0
        if abs(v) < 1e-7:
            v = 0.0
        if self.x_periodicity:
            if u > self.x_periodicity:
                u -= self.x_periodicity
            elif u < 0:
                u += self.x_periodicity
        point_at_curve = self.edge.point_at_abscissa(u)
        point = point_at_curve.translation(self.frame.w * v)
        return point

    def point3d_to_2d(self, point3d):
        """
        Transform a 3D Cartesian point (x, y, z) into a parametric (u, v) point.
        """
        x, y, z = self.frame.global_to_local_coordinates(point3d)
        if abs(x) < 1e-7:
            x = 0.0
        if abs(y) < 1e-7:
            y = 0.0
        if abs(z) < 1e-7:
            z = 0.0
        point_at_curve = []
        tol = 1e-4 if self.edge.__class__.__name__ in ("FullArcEllipse3D", "ArcEllipse3D") else 1e-6

        if hasattr(self.edge, "line_intersections"):
            line = curves.Line3D(point3d, point3d.translation(self.frame.w))
            point_at_curve = self.edge.line_intersections(line, tol)
        if point_at_curve:
            point_at_curve = point_at_curve[0]
            point_at_curve_local = self.frame.global_to_local_coordinates(point_at_curve)
        else:
            if hasattr(self.edge, "point_projection"):
                point_at_curve = self.edge.point_projection(point3d)[0]
                point_at_curve_local = self.frame.global_to_local_coordinates(point_at_curve)
            else:
                point_at_curve_local = design3d.Point3D(x, y, 0)
                point_at_curve = self.frame.local_to_global_coordinates(point_at_curve_local)
        u = self.edge.abscissa(point_at_curve)
        v = z - point_at_curve_local.z

        return design3d.Point2D(u, v)

    def parametric_points_to_3d(self, points: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Transform parametric coordinates to 3D points on the extrusion surface.

        Given a set of parametric coordinates `(u, v)` representing points on the surface,
        this method returns the corresponding 3D points on the extrusion surface.

        :param points: Parametric coordinates in the form of a numpy array with shape (n, 2),
                       where `n` is the number of points, and each row corresponds to `(u, v)`.
        :type points: numpy.ndarray[np.float64]

        :return: Array of 3D points representing the extrusion surface in Cartesian coordinates.
        :rtype: numpy.ndarray[np.float64]
        """
        z = np.array([self.direction[0], self.direction[1], self.direction[2]])

        points = points.reshape(-1, 2, 1)

        u_values = points[:, 0]
        if self.x_periodicity:
            u_values[u_values > self.x_periodicity] -= self.x_periodicity
            u_values[u_values < 0] += self.x_periodicity
        v_values = points[:, 1]

        points_at_curve = np.array([self.edge.point_at_abscissa(u) for u in u_values])

        return points_at_curve + v_values * z

    def rectangular_cut(self, x1: float = 0.0, x2: float = 1.0,
                        y1: float = 0.0, y2: float = 1.0, name: str = ''):
        """Deprecated method, Use ExtrusionFace3D from_surface_rectangular_cut method."""
        raise AttributeError('Use ExtrusionFace3D from_surface_rectangular_cut method')

    def plot(self, ax=None, edge_style: EdgeStyle = EdgeStyle(color='grey', alpha=0.5), z: float = 0.5, **kwargs):
        """Plot for extrusion surface using matplotlib."""
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
        self.frame.plot(ax=ax, ratio=self.edge.length())
        for i in range(21):
            step = i / 20. * z
            wire = self.edge.translation(step * self.frame.w)
            wire.plot(ax=ax, edge_style=edge_style)
        for i in range(21):
            step = -i / 20. * z
            wire = self.edge.translation(step * self.frame.w)
            wire.plot(ax=ax, edge_style=edge_style)

        return ax

    @classmethod
    def from_step(cls, arguments, object_dict, **kwargs):
        """Creates an extrusion surface from step data."""
        name = arguments[0][1:-1]
        edge = object_dict[arguments[1]]
        if edge.__class__ is curves.Ellipse3D:
            start_end = edge.center + edge.major_axis * edge.major_dir
            fullarcellipse = edges.FullArcEllipse3D(edge, start_end, edge.name)
            direction = -object_dict[arguments[2]]
            surface = cls(edge=fullarcellipse, direction=direction, name=name)
            surface.x_periodicity = fullarcellipse.length()
        elif edge.__class__ is curves.Circle3D:
            start_end = edge.center + edge.frame.u * edge.radius
            fullarc = edges.FullArc3D(edge, start_end)
            direction = object_dict[arguments[2]]
            surface = cls(edge=fullarc, direction=direction, name=name)
            surface.x_periodicity = fullarc.length()

        else:
            direction = object_dict[arguments[2]]
            surface = cls(edge=edge, direction=direction, name=name)
        return surface

    def to_step(self, current_id):
        """
        Translate design3d primitive to step syntax.
        """
        content_edge, edge_id = self.edge.to_step(current_id)
        current_id = edge_id + 1
        content_vector, vector_id = self.direction.to_step(current_id)
        current_id = vector_id + 1
        content = content_edge + content_vector
        content += f"#{current_id} = SURFACE_OF_LINEAR_EXTRUSION('{self.name}',#{edge_id},#{vector_id});\n"
        return content, [current_id]

    def linesegment3d_to_2d(self, linesegment3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        start = self.point3d_to_2d(linesegment3d.start)
        end = self.point3d_to_2d(linesegment3d.end)
        if self.x_periodicity:
            line_at_periodicity = curves.Line3D(self.edge.start, self.edge.start.translation(self.direction))
            if (line_at_periodicity.point_belongs(linesegment3d.start) and
                    line_at_periodicity.point_belongs(linesegment3d.end) and start.x != end.x):
                end.x = start.x
        return [edges.LineSegment2D(start, end)]

    def arc3d_to_2d(self, arc3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        start = self.point3d_to_2d(arc3d.start)
        end = self.point3d_to_2d(arc3d.end)
        if self.x_periodicity:
            start, end = self._verify_start_end_parametric_points(start, end, arc3d)
            points3d = [arc3d.start, arc3d.point_at_abscissa(0.02 * arc3d.length()),
                        arc3d.point_at_abscissa(0.98 * arc3d.length()), arc3d.end]
            point_after_start = self.point3d_to_2d(points3d[1])
            point_before_end = self.point3d_to_2d(points3d[2])
            start, _, _, end = self._repair_points_order([start, point_after_start, point_before_end, end], arc3d,
                                                         points3d)
        return [edges.LineSegment2D(start, end, name="arc")]

    def arcellipse3d_to_2d(self, arcellipse3d):
        """
        Transformation of an arc-ellipse 3d to 2d, in a cylindrical surface.

        """
        start2d = self.point3d_to_2d(arcellipse3d.start)
        end2d = self.point3d_to_2d(arcellipse3d.end)
        if isinstance(self.edge, edges.ArcEllipse3D):
            return [edges.LineSegment2D(start2d, end2d)]
        points3d = arcellipse3d.discretization_points(number_points=15)
        points = [self.point3d_to_2d(p) for p in points3d]
        return self._edge3d_to_2d(points, arcellipse3d, points3d)

    def fullarcellipse3d_to_2d(self, fullarcellipse3d):
        """
        Converts a 3D full elliptical arc to a 2D line segment in the current plane.

        This method converts a 3D full elliptical arc to a 2D line segment in the current plane.
        It first calculates the length of the arc using the `length` method of the `fullarcellipse3d`
        object. Then, it converts the start and end points of the arc to 2D points using the `point3d_to_2d`
        method. Additionally, it calculates a point on the arc at a small abscissa value (0.01 * length)
        and converts it to a 2D point. Based on the relative position of this point, the method determines
        the start and end points of the line segment in 2D. If the abscissa point is closer to the start
        point, the line segment starts from (0, start.y) and ends at (length, end.y). If the abscissa point is
        closer to the end point, the line segment starts from (length, start.y) and ends at (0, end.y). If the
        abscissa point lies exactly at the midpoint of the arc, a NotImplementedError is raised. The resulting
        line segment is returned as a list.

        :param fullarcellipse3d: The 3D full elliptical arc object to convert.
        :return: A list containing a 2D line segment representing the converted arc.
        :raises: NotImplementedError: If the abscissa point lies exactly at the midpoint of the arc.
        """

        length = fullarcellipse3d.length()
        start = self.point3d_to_2d(fullarcellipse3d.start)
        end = self.point3d_to_2d(fullarcellipse3d.end)

        u3, _ = self.point3d_to_2d(fullarcellipse3d.point_at_abscissa(0.01 * length))
        if u3 > 0.5 * length:
            start.x = length
            end.x = 0.0
        elif u3 < 0.5 * length:
            start.x = 0.0
            end.x = length
        else:
            raise NotImplementedError
        return [edges.LineSegment2D(start, end)]

    def linesegment2d_to_3d(self, linesegment2d):
        """
        Converts a BREP line segment 2D onto a 3D primitive on the surface.
        """
        start3d = self.point2d_to_3d(linesegment2d.start)
        end3d = self.point2d_to_3d(linesegment2d.end)
        u1, param_z1 = linesegment2d.start
        u2, param_z2 = linesegment2d.end
        if math.isclose(u1, u2, abs_tol=1e-6):
            return [edges.LineSegment3D(start3d, end3d)]
        if math.isclose(param_z1, param_z2, abs_tol=1e-6):
            curve = self.v_iso(param_z1)
            if u1 > u2:
                curve = curve.reverse()
            return [curve.trim(start3d, end3d)]
        n = 20
        degree = 5
        points = [self.point2d_to_3d(point2d) for point2d in linesegment2d.discretization_points(number_points=n)]
        return [edges.BSplineCurve3D.from_points_interpolation(points, degree, centripetal=True)]

    def bsplinecurve3d_to_2d(self, bspline_curve3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        n = bspline_curve3d.ctrlpts.shape[0]
        points3d = bspline_curve3d.discretization_points(number_points=n)
        points = [self.point3d_to_2d(point)
                  for point in points3d]
        return self._edge3d_to_2d(points, bspline_curve3d, points3d)

    def frame_mapping(self, frame: design3d.Frame3D, side: str):
        """
        Returns a new Extrusion Surface positioned in the specified frame.

        :param frame: Frame of reference
        :type frame: `design3d.Frame3D`
        :param side: 'old' or 'new'
        """
        new_frame = self.frame.frame_mapping(frame, side)
        direction = new_frame.w
        new_edge = self.edge.frame_mapping(frame, side)
        return ExtrusionSurface3D(new_edge, direction, name=self.name)

    def _verify_start_end_parametric_points(self, start, end, edge3d):
        """
        When the generatrix of the surface is periodic we need to verify if the u parameter should be 0 or 1.
        """
        start_ref1 = self.point3d_to_2d(edge3d.point_at_abscissa(0.01 * edge3d.length()))
        start_ref2 = self.point3d_to_2d(edge3d.point_at_abscissa(0.02 * edge3d.length()))
        end_ref1 = self.point3d_to_2d(edge3d.point_at_abscissa(0.99 * edge3d.length()))
        end_ref2 = self.point3d_to_2d(edge3d.point_at_abscissa(0.98 * edge3d.length()))
        if math.isclose(start.x, self.x_periodicity, abs_tol=1e-4):
            vec1 = start_ref1 - start
            vec2 = start_ref2 - start_ref1
            if vec2.dot(vec1) < 0:
                start.x = 0
        if math.isclose(end.x, self.x_periodicity, abs_tol=1e-4):
            vec1 = end - end_ref1
            vec2 = end_ref1 - end_ref2
            if vec2.dot(vec1) < 0:
                end.x = 0
        if math.isclose(start.x, 0, abs_tol=1e-4):
            vec1 = start_ref1 - start
            vec2 = start_ref2 - start_ref1
            if vec2.dot(vec1) < 0:
                start.x = self.x_periodicity
        if math.isclose(end.x, 0, abs_tol=1e-4):
            vec1 = end - end_ref1
            vec2 = end_ref1 - end_ref2
            if vec2.dot(vec1) < 0:
                end.x = self.x_periodicity
        return start, end

    def _repair_points_order(self, points: List[design3d.Point2D], edge3d,
                             points3d: List[design3d.Point3D]) -> List[design3d.Point2D]:
        """
        Helper function to reorder discretization points along a parametric domain for an extrusion surface.

        When generating an extrusion surface from a periodic edge, there may be discontinuities in the parametric
        representation of the edge on the surface. This function addresses this issue by calculating how many times the
        edge crosses the periodic boundary of the surface. It then selects the first side as reference, and then all
        parts of the edge on the "opposite" side (lower/upper bound) are updated by adding or subtracting one
        periodicity. This is achieved using the 'sign' variable. The result is a list of parametric points that form a
        continuous path in parametric space. The cache_point_index keeps track of points that were already checked, so
        we don't need to check it again in the next remaining edge's piece.

        :param points: List of 2D parametric points representing the discretization of the edge on the surface.
        :param edge3d: The 3D curve representing the edge.
        :param points3d: List of corresponding 3D points.

        :return: The reordered list of parametric points forming a continuous path on the extrusion surface.
        """
        line_at_periodicity = curves.Line3D(self.edge.start, self.edge.start.translation(self.direction))
        intersections = edge3d.line_intersections(line_at_periodicity)
        intersections = [point for point in intersections if not edge3d.is_point_edge_extremity(point, abs_tol=5e-6)]
        if not intersections:
            return points
        sign = self._helper_get_sign_repair_points_order(edge3d, points[0], intersections[0])
        remaining_edge = edge3d
        cache_point_index = 0
        crossed_even_number_of_times = True
        for i, intersection in enumerate(intersections):
            current_split = remaining_edge.split(intersection)
            crossed_even_number_of_times = bool(i % 2 == 0)
            for point, point3d in zip(points[cache_point_index:], points3d[cache_point_index:]):
                if crossed_even_number_of_times and current_split[0].point_belongs(point3d):
                    cache_point_index += 1
                elif not crossed_even_number_of_times and current_split[0].point_belongs(point3d):
                    point.x = point.x + sign * self.x_periodicity
                    cache_point_index += 1

            remaining_edge = current_split[1]
        if crossed_even_number_of_times and cache_point_index < len(points):
            for point in points[cache_point_index:]:
                point.x = point.x + sign * self.x_periodicity
        return points

    def _helper_get_sign_repair_points_order(self, edge3d, starting_parametric_point, first_intersection_point):
        """Helper function to repair points order."""
        reference_point = edge3d.local_discretization(edge3d.start, first_intersection_point, 3)[1]
        reference_point_u_parm = self.point3d_to_2d(reference_point).x
        diff = reference_point_u_parm - starting_parametric_point.x
        return diff / abs(diff)

    def _edge3d_to_2d(self, points, edge3d, points3d):
        """Helper to get parametric representation of edges on the surface."""
        if self.x_periodicity:
            start, end = self._verify_start_end_parametric_points(points[0], points[-1], edge3d)
            points[0] = start
            points[-1] = end
            points = self._repair_points_order(points, edge3d, points3d)
        start = points[0]
        end = points[-1]
        if is_isocurve(points, 1e-5):
            return [edges.LineSegment2D(start, end)]
        if hasattr(edge3d, "degree"):
            degree = edge3d.degree
        else:
            degree = 2
        return [edges.BSplineCurve2D.from_points_interpolation(points, degree)]

    def u_iso(self, u: float) -> curves.Line3D:
        """
        Returns the u-iso curve of the surface.

        :param u: The value of u where to extract the curve.
        :type u: float
        :return: A line 3D
        :rtype: :class:`curves.Line3D`
        """

        point_at_u = self.point2d_to_3d(design3d.Point2D(u, 0.0))

        return curves.Line3D.from_point_and_vector(point_at_u, self.frame.w)

    def v_iso(self, v: float) -> curves.Curve:
        """
        Returns the v-iso curve of the surface.

        :param v: The value of u where to extract the curve.
        :type v: float
        :return: A Curve
        :rtype: :class:`curves.Curve`
        """
        return self.edge.curve().translation(self.direction * v)


class RevolutionSurface3D(UPeriodicalSurface):
    """
    Defines a surface of revolution.

    :param edge: Edge.
    :type edge: edges.Edge
    :param axis_point: Axis placement
    :type axis_point: :class:`design3d.Point3D`
    :param axis: Axis of revolution
    :type axis: :class:`design3d.Vector3D`
    """
    face_class = 'RevolutionFace3D'
    x_periodicity = design3d.TWO_PI

    def __init__(self, edge,
                 axis_point: design3d.Point3D, axis: design3d.Vector3D, name: str = ''):
        self.edge = edge
        self.axis_point = axis_point
        self.axis = axis.unit_vector()

        point1 = edge.point_at_abscissa(0)
        vector1 = point1 - axis_point
        w_vector = self.axis
        if point1.is_close(axis_point) or w_vector.is_colinear_to(vector1):
            if edge.__class__.__name__ != "Line3D":
                point1 = edge.point_at_abscissa(0.5 * edge.length())
            else:
                point1 = edge.point_at_abscissa(0.05)
            vector1 = point1 - axis_point
        u_vector = vector1 - vector1.vector_projection(w_vector)
        u_vector = u_vector.unit_vector()
        v_vector = w_vector.cross(u_vector)
        frame = design3d.Frame3D(origin=axis_point, u=u_vector, v=v_vector, w=w_vector)

        UPeriodicalSurface.__init__(self, frame=frame, name=name)

    def __hash__(self):
        return hash((self.__class__.__name__, self.edge, self.axis_point, self.axis))

    def __eq__(self, other):
        if self.__class__.__name__ != other.__class__.__name__:
            return False
        if self.edge == other.edge and self.axis_point == other.axis_point and self.axis == other.axis:
            return True
        return False

    @property
    def y_periodicity(self):
        """
        Evaluates the periodicity of the surface in v direction.
        """
        a, b, c, d = self.domain
        point_at_c = self.point2d_to_3d(design3d.Point2D(0.5 * (b - a), c))
        point_at_d = self.point2d_to_3d(design3d.Point2D(0.5 * (b - a), d))
        if point_at_d.is_close(point_at_c):
            return d
        return None

    @property
    def u_domain(self):
        """The parametric domain of the surface in the U direction."""
        return -math.pi, math.pi

    @property
    def v_domain(self):
        """The parametric domain of the surface in the V direction."""
        if self.edge.__class__.__name__ != "Line3D":
            return 0.0, self.edge.length()
        return -math.inf, math.inf

    @property
    def domain(self):
        """Returns u and v bounds."""
        d3din, d3dax = self.v_domain
        return -math.pi, math.pi, d3din, d3dax

    def point2d_to_3d(self, point2d: design3d.Point2D):
        """
        Transform a parametric (u, v) point into a 3D Cartesian point (x, y, z).

        u = [0, 2pi] and v = [0, 1] into a
        """
        u, v = point2d
        point_at_curve = self.edge.point_at_abscissa(v)
        point_vector = point_at_curve - self.axis_point
        point3d = (self.axis_point + point_vector * math.cos(u) +
                   point_vector.dot(self.axis) * self.axis * (1 - math.cos(u)) +
                   self.axis.cross(point_vector) * math.sin(u))
        return point3d

    def point3d_to_2d(self, point3d):
        """
        Transform a 3D Cartesian point (x, y, z) into a parametric (u, v) point.
        """
        x, y, _ = self.frame.global_to_local_coordinates(point3d)
        if abs(x) < 1e-12:
            x = 0
        if abs(y) < 1e-12:
            y = 0
        u = math.atan2(y, x)

        point_at_curve = point3d.rotation(self.axis_point, self.axis, -u)
        v = self.edge.abscissa(point_at_curve)
        return design3d.Point2D(u, v)

    def parametric_points_to_3d(self, points: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Transform parametric coordinates to 3D points on the revolution surface.

        Given a set of parametric coordinates `(u, v)` representing points on the surface,
        this method returns the corresponding 3D points on the revolution surface.

        :param points: Parametric coordinates in the form of a numpy array with shape (n, 2),
                       where `n` is the number of points, and each row corresponds to `(u, v)`.
        :type points: numpy.ndarray[np.float64]

        :return: Array of 3D points representing the revolution surface in Cartesian coordinates.
        :rtype: numpy.ndarray[np.float64]
        """
        center = np.array(self.axis_point)
        z = np.array([self.axis[0], self.axis[1], self.axis[2]])

        points = points.reshape(-1, 2, 1)

        u_values = points[:, 0]
        v_values = points[:, 1]
        if self.y_periodicity:
            v_values[v_values > self.y_periodicity] -= self.y_periodicity
            v_values[v_values < 0] += self.y_periodicity

        cos_u = np.cos(u_values)

        points_at_curve = np.array([self.edge.point_at_abscissa(v) for v in v_values])
        points_at_curve_minus_center = points_at_curve - center

        return (center + points_at_curve_minus_center * cos_u +
                np.dot(points_at_curve_minus_center, z).reshape(-1, 1) * z * (1 - cos_u) +
                np.cross(z, points_at_curve_minus_center * np.sin(u_values)))

    def rectangular_cut(self, x1: float, x2: float,
                        y1: float, y2: float, name: str = ''):
        """Deprecated method, Use RevolutionFace3D from_surface_rectangular_cut method."""
        raise AttributeError('Use RevolutionFace3D from_surface_rectangular_cut method')

    def plot(self, ax=None, edge_style: EdgeStyle = EdgeStyle(color='grey', alpha=0.5),
             number_curves: int = 20, **kwargs):
        """
        Plot rotated Revolution surface generatrix.

        :param number_curves: Number of curves to display.
        :param ax: matplotlib axis.
        :param edge_style: plot edge style.
        :type number_curves: int
        """
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
        for i in range(number_curves + 1):
            theta = i / number_curves * design3d.TWO_PI
            wire = self.edge.rotation(self.axis_point, self.axis, theta)
            wire.plot(ax=ax, edge_style=edge_style)

        return ax

    @classmethod
    def from_step(cls, arguments, object_dict, **kwargs):
        """
        Converts a step primitive to a RevolutionSurface3D.

        :param arguments: The arguments of the step primitive.
        :type arguments: list
        :param object_dict: The dictionary containing all the step primitives
            that have already been instantiated.
        :type object_dict: dict
        :return: The corresponding RevolutionSurface3D object.
        :rtype: :class:`design3d.faces.RevolutionSurface3D`
        """
        name = arguments[0][1:-1]
        edge = object_dict[arguments[1]]
        if edge.__class__ is curves.Circle3D:
            start_end = edge.center + edge.frame.u * edge.radius
            edge = edges.FullArc3D(edge, start_end, edge.name)

        axis_point, axis = object_dict[arguments[2]]
        surface = cls(edge=edge, axis_point=axis_point, axis=axis, name=name)
        return surface.simplify()

    def to_step(self, current_id):
        """
        Translate design3d primitive to step syntax.
        """
        content_wire, wire_id = self.edge.to_step(current_id)
        current_id = wire_id + 1
        content_axis_point, axis_point_id = self.axis_point.to_step(current_id)
        current_id = axis_point_id + 1
        content_axis, axis_id = self.axis.to_step(current_id)
        current_id = axis_id + 1
        content = content_wire + content_axis_point + content_axis
        content += f"#{current_id} = AXIS1_PLACEMENT('',#{axis_point_id},#{axis_id});\n"
        current_id += 1
        content += f"#{current_id} = SURFACE_OF_REVOLUTION('{self.name}',#{wire_id},#{current_id - 1});\n"
        return content, [current_id]

    def arc3d_to_2d(self, arc3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        start = self.point3d_to_2d(arc3d.start)
        end = self.point3d_to_2d(arc3d.end)
        if self.edge.__class__.__name__ != "Line3D" and hasattr(self.edge.simplify, "circle") and \
                math.isclose(self.edge.simplify.circle.radius, arc3d.circle.radius, rel_tol=0.01):
            if self.edge.is_point_edge_extremity(arc3d.start):
                middle_point = self.point3d_to_2d(arc3d.middle_point())
                if middle_point.x == math.pi:
                    middle_point.x = -math.pi
                    if end.x == math.pi:
                        end.x = middle_point.x
                start.x = middle_point.x
            if self.edge.is_point_edge_extremity(arc3d.end):
                middle_point = self.point3d_to_2d(arc3d.middle_point())
                if middle_point.x == math.pi:
                    middle_point.x = -math.pi
                    if start.x == math.pi:
                        start.x = middle_point.x
                end.x = middle_point.x
        if math.isclose(start.y, end.y, rel_tol=0.01):
            point_after_start, point_before_end = self._reference_points(arc3d)
            point_theta_discontinuity = self.point2d_to_3d(design3d.Point2D(math.pi, start.y))
            discontinuity = arc3d.point_belongs(point_theta_discontinuity) and not \
                arc3d.is_point_edge_extremity(point_theta_discontinuity)

            undefined_start_theta = arc3d.start.is_close(point_theta_discontinuity)
            undefined_end_theta = arc3d.end.is_close(point_theta_discontinuity)
            start, end = d3d_parametric.arc3d_to_cylindrical_coordinates_verification(
                [start, end], [undefined_start_theta, undefined_end_theta],
                [point_after_start.x, point_before_end.x], discontinuity)
        if math.isclose(start.y, end.y, rel_tol=0.01) or math.isclose(start.x, end.x, rel_tol=0.01):
            return [edges.LineSegment2D(start, end, name="arc")]
        n = 10
        degree = 3
        bsplinecurve3d = edges.BSplineCurve3D.from_points_interpolation(arc3d.discretization_points(number_points=n),
                                                                        degree, centripetal=True)
        return self.bsplinecurve3d_to_2d(bsplinecurve3d)

    def fullarc3d_to_2d(self, fullarc3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        start = self.point3d_to_2d(fullarc3d.start)
        end = self.point3d_to_2d(fullarc3d.end)
        point_after_start, point_before_end = self._reference_points(fullarc3d)
        point_theta_discontinuity = self.point2d_to_3d(design3d.Point2D(math.pi, start.y))
        discontinuity = fullarc3d.point_belongs(point_theta_discontinuity) and not \
            fullarc3d.is_point_edge_extremity(point_theta_discontinuity)

        undefined_start_theta = fullarc3d.start.is_close(point_theta_discontinuity)
        undefined_end_theta = fullarc3d.end.is_close(point_theta_discontinuity)
        start, end = d3d_parametric.arc3d_to_cylindrical_coordinates_verification(
            [start, end], [undefined_start_theta, undefined_end_theta],
            [point_after_start.x, point_before_end.x], discontinuity)
        theta1, z1 = start
        theta2, _ = end
        _, z3 = point_after_start

        if self.frame.w.is_colinear_to(fullarc3d.circle.normal):
            normal_dot_product = self.frame.w.dot(fullarc3d.circle.normal)
            start, end = d3d_parametric.fullarc_to_cylindrical_coordinates_verification(start, end, normal_dot_product)
            return [edges.LineSegment2D(start, end)]
        if math.isclose(theta1, theta2, abs_tol=1e-3):
            # Treating one case from Revolution Surface
            if z1 > z3:
                point1 = design3d.Point2D(theta1, 1)
                point2 = design3d.Point2D(theta1, 0)
            else:
                point1 = design3d.Point2D(theta1, 0)
                point2 = design3d.Point2D(theta1, 1)
            return [edges.LineSegment2D(point1, point2)]
        if math.isclose(abs(theta1 - theta2), math.pi, abs_tol=1e-3):
            if z1 > z3:
                point1 = design3d.Point2D(theta1, 1)
                point2 = design3d.Point2D(theta1, 0)
                point3 = design3d.Point2D(theta2, 0)
                point4 = design3d.Point2D(theta2, 1)
            else:
                point1 = design3d.Point2D(theta1, 0)
                point2 = design3d.Point2D(theta1, 1)
                point3 = design3d.Point2D(theta2, 1)
                point4 = design3d.Point2D(theta2, 0)
            return [edges.LineSegment2D(point1, point2),
                    edges.LineSegment2D(point2, point3),
                    edges.LineSegment2D(point3, point4)
                    ]

        raise NotImplementedError

    def linesegment2d_to_3d(self, linesegment2d):
        """
        Converts a BREP line segment 2D onto a 3D primitive on the surface.
        """
        if linesegment2d.name == "construction" or self.is_degenerated_brep(linesegment2d):
            return None
        start3d = self.point2d_to_3d(linesegment2d.start)
        end3d = self.point2d_to_3d(linesegment2d.end)
        theta1, abscissa1 = linesegment2d.start
        theta2, abscissa2 = linesegment2d.end

        if self.edge.point_at_abscissa(abscissa1).is_close(self.edge.point_at_abscissa(abscissa2)):
            circle = self.v_iso(abscissa1)
            if theta1 > theta2:
                circle = circle.reverse()
            return [circle.trim(start3d, end3d)]

        if math.isclose(theta1, theta2, abs_tol=1e-3):
            curve = self.u_iso(theta1)
            if abscissa1 > abscissa2:
                curve = curve.reverse()
            return [curve.trim(start3d, end3d)]
        n = int(54 * abs(theta2 - theta1)/math.pi)
        degree = 7
        points = [self.point2d_to_3d(point2d) for point2d in linesegment2d.discretization_points(number_points=n)]
        return [edges.BSplineCurve3D.from_points_interpolation(points, degree, centripetal=True).simplify]

    def bsplinecurve2d_to_3d(self, bspline_curve2d):
        """
        Is this right?.
        """
        n = len(bspline_curve2d.control_points)
        points = [self.point2d_to_3d(p)
                  for p in bspline_curve2d.discretization_points(number_points=n)]
        return [edges.BSplineCurve3D.from_points_interpolation(points, bspline_curve2d.degree, centripetal=True)]

    def frame_mapping(self, frame: design3d.Frame3D, side: str):
        """
        Returns a new Revolution Surface positioned in the specified frame.

        :param frame: Frame of reference
        :type frame: `design3d.Frame3D`
        :param side: 'old' or 'new'
        """
        new_frame = self.frame.frame_mapping(frame, side)
        axis = new_frame.w
        axis_point = new_frame.origin
        new_edge = self.edge.frame_mapping(frame, side)
        return RevolutionSurface3D(new_edge, axis_point, axis, name=self.name)

    def translation(self, offset):
        """
        Returns a new translated Revolution Surface.

        :param offset: translation vector.
        """
        new_edge = self.edge.translation(offset)
        new_axis_point = self.axis_point.translation(offset)
        return RevolutionSurface3D(new_edge, new_axis_point, self.axis)

    def rotation(self, center: design3d.Point3D, axis: design3d.Vector3D, angle: float):
        """
        Revolution Surface 3D rotation.

        :param center: rotation center
        :param axis: rotation axis
        :param angle: angle rotation
        :return: a new rotated Revolution Surface 3D
        """
        new_edge = self.edge.rotation(center, axis, angle)
        new_axis_point = self.axis_point.rotation(center, axis, angle)
        new_axis = self.axis.rotation(center, axis, angle)
        return RevolutionSurface3D(new_edge, new_axis_point, new_axis)

    def simplify(self):
        """Gets the simplified version of the surface."""
        line3d = curves.Line3D(self.axis_point, self.axis_point + self.axis)
        if isinstance(self.edge, edges.Arc3D):
            tore_center, _ = line3d.point_projection(self.edge.center)
            # Sphere
            if math.isclose(tore_center.point_distance(self.edge.center), 0., abs_tol=1e-6):
                return SphericalSurface3D(self.frame, self.edge.circle.radius, self.name)
        if isinstance(self.edge, (edges.LineSegment3D, curves.Line3D)):
            if isinstance(self.edge, edges.LineSegment3D):
                generatrix_line = self.edge.line
            else:
                generatrix_line = self.edge
            intersections = line3d.intersection(generatrix_line)
            if intersections:
                generatrix_line_direction = generatrix_line.unit_direction_vector()
                if self.axis.dot(generatrix_line_direction) > 0:
                    semi_angle = design3d.geometry.vectors3d_angle(self.axis, generatrix_line_direction)
                else:
                    semi_angle = design3d.geometry.vectors3d_angle(self.axis, -generatrix_line_direction)
                if not self.axis_point.is_close(intersections):
                    new_w = self.axis_point - intersections
                    new_w = new_w.unit_vector()
                    new_frame = design3d.Frame3D(intersections, self.frame.u, new_w.cross(self.frame.u), new_w)
                else:
                    new_frame = design3d.Frame3D(intersections, self.frame.u, self.frame.v, self.frame.w)
                return ConicalSurface3D(new_frame, semi_angle, name=self.name)
            generatrix_line_direction = generatrix_line.unit_direction_vector()
            if self.axis.is_colinear_to(generatrix_line_direction):
                radius = self.edge.point_distance(self.axis_point)
                return CylindricalSurface3D(self.frame, radius, self.name)
        return self

    def u_closed_lower(self):
        """
        Returns True if the surface is close in any of the u boundaries.
        """
        a, b, c, _ = self.domain
        point_at_a_lower = self.point2d_to_3d(design3d.Point2D(a, c))
        point_at_b_lower = self.point2d_to_3d(design3d.Point2D(0.5 * (a + b), c))
        if point_at_b_lower.is_close(point_at_a_lower):
            return True
        return False

    def u_closed_upper(self):
        """
        Returns True if the surface is close in any of the u boundaries.
        """
        a, b, _, d = self.domain
        point_at_a_upper = self.point2d_to_3d(design3d.Point2D(a, d))
        point_at_b_upper = self.point2d_to_3d(design3d.Point2D(0.5 * (a + b), d))
        if point_at_b_upper.is_close(point_at_a_upper):
            return True
        return False

    def u_closed(self):
        """
        Returns True if the surface is close in any of the u boundaries.
        """
        return bool(self.u_closed_lower() or self.u_closed_upper())

    def v_closed(self):
        """
        Returns True if the surface is close in any of the u boundaries.
        """
        return False

    def is_singularity_point(self, point, *args, **kwargs):
        """Returns True if the point belongs to the surface singularity and False otherwise."""
        tol = kwargs.get("tol", 1e-6)
        if self.u_closed_lower() and self.edge.start.is_close(point, tol):
            return True
        if self.u_closed_upper() and self.edge.end.is_close(point, tol):
            return True
        return False

    def get_singularity_lines(self):
        """
        Return lines that are parallel and coincident with surface singularity at parametric domain.
        """
        a, b, c, d = self.domain
        lines = []
        if self.u_closed_lower():
            lines.append(curves.Line2D(design3d.Point2D(a, c), design3d.Point2D(b, c)))
        if self.u_closed_upper():
            lines.append(curves.Line2D(design3d.Point2D(a, d), design3d.Point2D(b, d)))
        return lines

    def u_iso(self, u: float) -> curves.Curve:
        """
        Returns the u-iso curve of the surface.

        :param u: The value of u where to extract the curve.
        :type u: float
        :return: A curve
        :rtype: :class:`curves.Curve`
        """
        if isinstance(self.edge, curves.Curve):
            return self.edge.rotation(self.axis_point, self.axis, u)
        return self.edge.curve().rotation(self.axis_point, self.axis, u)

    def v_iso(self, v: float) -> curves.Circle3D:
        """
        Returns the v-iso curve of the surface.

        :param v: The value of u where to extract the curve.
        :type v: float
        :return: A Circle 3D
        :rtype: :class:`curves.Circle3D`
        """
        point_at_v = self.point2d_to_3d(design3d.Point2D(0.0, v))
        axis_line = curves.Line3D.from_point_and_vector(self.axis_point, self.axis)
        frame_origin = axis_line.point_projection(point_at_v)[0]
        frame = self.frame.copy()
        frame.origin = frame_origin
        radius = axis_line.point_distance(point_at_v)
        return curves.Circle3D(frame, radius)


class BSplineSurface3D(Surface3D):
    """
    A class representing a 3D B-spline surface.

    A B-spline surface is a smooth surface defined by a set of control points and
    a set of basis functions called B-spline basis functions. The shape of the
    surface is determined by the position of the control points and can be
    modified by moving the control points.

    :param degree_u: The degree of the B-spline curve in the u direction.
    :type degree_u: int
    :param degree_v: The degree of the B-spline curve in the v direction.
    :type degree_v: int
    :param control_points: A list of 3D control points that define the shape of
        the surface.
    :type control_points: List[`design3d.Point3D`]
    :param nb_u: The number of control points in the u direction.
    :type nb_u: int
    :param nb_v: The number of control points in the v direction.
    :type nb_v: int
    :param u_multiplicities: A list of multiplicities for the knots in the u direction.
        The multiplicity of a knot is the number of times it appears in the knot vector.
    :type u_multiplicities: List[int]
    :param v_multiplicities: A list of multiplicities for the knots in the v direction.
        The multiplicity of a knot is the number of times it appears in the knot vector.
    :type v_multiplicities: List[int]
    :param u_knots: A list of knots in the u direction. The knots are real numbers that
        define the position of the control points along the u direction.
    :type u_knots: List[float]
    :param v_knots: A list of knots in the v direction. The knots are real numbers that
        define the position of the control points along the v direction.
    :type v_knots: List[float]
    :param weights: (optional) A list of weights for the control points. The weights
        can be used to adjust the influence of each control point on the shape of the
        surface. Default is None.
    :type weights: List[float]
    :param name: (optional) A name for the surface. Default is an empty string.
    :type name: str
    """
    face_class = "BSplineFace3D"
    _eq_is_data_eq = False

    def __init__(self, degree_u: int, degree_v: int, control_points: List[design3d.Point3D], nb_u: int, nb_v: int,
                 u_multiplicities: List[int], v_multiplicities: List[int], u_knots: List[float], v_knots: List[float],
                 weights: List[float] = None, name: str = ''):
        self.ctrlpts = np.asarray(control_points)
        self.degree_u = int(degree_u)
        self.degree_v = int(degree_v)
        self.nb_u = int(nb_u)
        self.nb_v = int(nb_v)

        self.u_knots = np.asarray(nurbs_helpers.standardize_knot_vector(u_knots), dtype=np.float64)
        self.v_knots = np.asarray(nurbs_helpers.standardize_knot_vector(v_knots), dtype=np.float64)
        self.u_multiplicities = np.asarray(u_multiplicities, dtype=np.int16)
        self.v_multiplicities = np.asarray(v_multiplicities, dtype=np.int16)
        self._weights = weights
        self.rational = False
        if weights is not None:
            self.rational = True
            self._weights = np.asarray(weights, dtype=np.float64)

        self._surface = None
        Surface3D.__init__(self, name=name)

        # Hidden Attributes
        self._displacements = None
        self._grids2d = None
        self._grids2d_deformed = None
        self._bbox = None
        self._surface_curves = None
        self._knotvector = None
        self.ctrlptsw = None
        if self._weights is not None:
            self.ctrlptsw = np.hstack((self.ctrlpts * self._weights[:, np.newaxis], self._weights[:, np.newaxis]))
        self._delta = [0.05, 0.05]
        self._eval_points = None
        self._vertices = None
        self._domain = None

        self._x_periodicity = False  # Use False instead of None because None is a possible value of x_periodicity
        self._y_periodicity = False

    def __hash__(self):
        """
        Creates custom hash to the surface.
        """
        control_points = self.control_points
        if self.weights is None:
            return hash((tuple(control_points),
                         self.degree_u, tuple(self.u_multiplicities), tuple(self.u_knots), self.nb_u,
                         self.degree_v, tuple(self.v_multiplicities), tuple(self.v_knots), self.nb_v))
        weights = tuple(self.weights)
        return hash((tuple(control_points),
                     self.degree_u, tuple(self.u_multiplicities), tuple(self.u_knots), self.nb_u,
                     self.degree_v, tuple(self.v_multiplicities), tuple(self.v_knots), self.nb_v, weights))

    def __eq__(self, other):
        """
        Defines the BSpline surface equality operation.
        """
        if not isinstance(other, self.__class__):
            return False

        if (self.rational != other.rational or self.degree_u != other.degree_u or self.degree_v != other.degree_v or
                self.nb_u != other.nb_u or self.nb_v != other.nb_v):
            return False

        for s_k, o_k in zip(self.knotvector, other.knotvector):
            if len(s_k) != len(o_k) or any(not math.isclose(s, o, abs_tol=1e-8) for s, o in zip(s_k, o_k)):
                return False
        self_control_points = self.control_points
        other_control_points = other.control_points
        if len(self_control_points) != len(other_control_points) or \
                any(not s_point.is_close(o_point) for s_point, o_point in
                    zip(self_control_points, other_control_points)):
            return False
        if self.rational and other.rational:
            if len(self.weights) != len(other.weights) or \
                    any(not math.isclose(s_w, o_w, abs_tol=1e-8) for s_w, o_w in zip(self.weights, other.weights)):
                return False
        return True

    def _data_eq(self, other_object):
        """
        Defines dessia common object equality.
        """
        return self == other_object

    @property
    def data(self):
        """
        Returns a dictionary of the BSpline data.
        """
        datadict = {
            "degree": (self.degree_u, self.degree_v),
            "knotvector": self.knotvector,
            "size": (self.nb_u, self.nb_v),
            "sample_size": self.sample_size,
            "rational": self.rational,
            "precision": 18
        }
        if self.rational:
            datadict["control_points"] = self.ctrlptsw
        else:
            datadict["control_points"] = self.ctrlpts
        return datadict

    @property
    def control_points(self):
        """Gets control points."""
        return [design3d.Point3D(*point) for point in self.ctrlpts]

    @property
    def control_points_table(self):
        """Creates control points table."""
        control_points_table = []
        points_row = []
        i = 1
        for point in self.control_points:
            points_row.append(point)
            if i == self.nb_v:
                control_points_table.append(points_row)
                points_row = []
                i = 1
            else:
                i += 1
        return control_points_table

    @property
    def knots_vector_u(self):
        """
        Compute the global knot vector (u direction) based on knot elements and multiplicities.

        """
        return np.repeat(self.u_knots, self.u_multiplicities)

    @property
    def knots_vector_v(self):
        """
        Compute the global knot vector (v direction) based on knot elements and multiplicities.

        """
        return np.repeat(self.v_knots, self.v_multiplicities)

    @property
    def knotvector(self):
        """
        Knot vector in u and v direction respectively.
        """
        if not self._knotvector:
            self._knotvector = [self.knots_vector_u, self.knots_vector_v]
        return self._knotvector

    @property
    def sample_size_u(self):
        """
        Sample size for the u-direction.

        :getter: Gets sample size for the u-direction
        :setter: Sets sample size for the u-direction
        :type: int
        """
        s_size = math.floor((1.0 / self.delta_u) + 0.5)
        return int(s_size)

    @sample_size_u.setter
    def sample_size_u(self, value):
        if not isinstance(value, int):
            raise ValueError("Sample size must be an integer value")
        knotvector_u = self.knots_vector_u

        # To make it operate like linspace, we have to know the starting and ending points.
        start_u = knotvector_u[self.degree_u]
        stop_u = knotvector_u[-(self.degree_u + 1)]

        # Set delta values
        self.delta_u = (stop_u - start_u) / float(value)

    @property
    def sample_size_v(self):
        """
        Sample size for the v-direction.

        :getter: Gets sample size for the v-direction
        :setter: Sets sample size for the v-direction
        :type: int
        """
        s_size = math.floor((1.0 / self.delta_v) + 0.5)
        return int(s_size)

    @sample_size_v.setter
    def sample_size_v(self, value):
        if not isinstance(value, int):
            raise ValueError("Sample size must be an integer value")
        knotvector_v = self.knots_vector_v

        # To make it operate like linspace, we have to know the starting and ending points.
        start_v = knotvector_v[self.degree_v]
        stop_v = knotvector_v[-(self.degree_v + 1)]

        # Set delta values
        self.delta_v = (stop_v - start_v) / float(value)

    @property
    def sample_size(self):
        """
        Sample size for both u- and v-directions.

        :getter: Gets sample size as a tuple of values corresponding to u- and v-directions
        :setter: Sets sample size for both u- and v-directions
        :type: int
        """
        sample_size_u = math.floor((1.0 / self.delta_u) + 0.5)
        sample_size_v = math.floor((1.0 / self.delta_v) + 0.5)
        return int(sample_size_u), int(sample_size_v)

    @sample_size.setter
    def sample_size(self, value):
        knotvector_u = self.knots_vector_u
        knotvector_v = self.knots_vector_v

        # To make it operate like linspace, we have to know the starting and ending points.
        start_u = knotvector_u[self.degree_u]
        stop_u = knotvector_u[-(self.degree_u + 1)]
        start_v = knotvector_v[self.degree_v]
        stop_v = knotvector_v[-(self.degree_v + 1)]

        # Set delta values
        self.delta_u = (stop_u - start_u) / float(value)
        self.delta_v = (stop_v - start_v) / float(value)

    @property
    def delta_u(self):
        """
        Evaluation delta for the u-direction.

        :getter: Gets evaluation delta for the u-direction
        :setter: Sets evaluation delta for the u-direction
        :type: float
        """
        return self._delta[0]

    @delta_u.setter
    def delta_u(self, value):
        # Delta value for surface evaluation should be between 0 and 1
        if float(value) <= 0 or float(value) >= 1:
            raise ValueError("Surface evaluation delta (u-direction) must be between 0.0 and 1.0")

        # Set new delta value
        self._delta[0] = float(value)

    @property
    def delta_v(self):
        """
        Evaluation delta for the v-direction.

        :getter: Gets evaluation delta for the v-direction
        :setter: Sets evaluation delta for the v-direction
        :type: float
        """
        return self._delta[1]

    @delta_v.setter
    def delta_v(self, value):
        # Delta value for surface evaluation should be between 0 and 1
        if float(value) <= 0 or float(value) >= 1:
            raise ValueError("Surface evaluation delta (v-direction) should be between 0.0 and 1.0")

        # Set new delta value
        self._delta[1] = float(value)

    @property
    def delta(self):
        """
        Evaluation delta for both u- and v-directions.

        :getter: Gets evaluation delta as a tuple of values corresponding to u- and v-directions
        :setter: Sets evaluation delta for both u- and v-directions
        :type: float
        """
        return self.delta_u, self.delta_v

    @delta.setter
    def delta(self, value):
        if isinstance(value, (int, float)):
            self.delta_u = value
            self.delta_v = value
        elif isinstance(value, (list, tuple)):
            if len(value) == 2:
                self.delta_u = value[0]
                self.delta_v = value[1]
            else:
                raise ValueError("Surface requires 2 delta values")
        else:
            raise ValueError("Cannot set delta. Please input a numeric value or a list or tuple with 2 numeric values")

    @property
    def weights(self):
        """
        Gets the weights of the BSpline surface.
        """
        if self._weights is None:
            return self._weights
        return self._weights.tolist()

    @property
    def x_periodicity(self):
        """
        Evaluates the periodicity of the surface in u direction.
        """
        if self._x_periodicity is False:
            a, b, c, d = self.domain
            point_at_a = self.point2d_to_3d(design3d.Point2D(a, 0.5 * (d - c)))
            point_at_b = self.point2d_to_3d(design3d.Point2D(b, 0.5 * (d - c)))
            if point_at_b.is_close(point_at_a) or self.u_closed:
                self._x_periodicity = b - a
            else:
                self._x_periodicity = None
        return self._x_periodicity

    @property
    def y_periodicity(self):
        """
        Evaluates the periodicity of the surface in v direction.
        """
        if self._y_periodicity is False:
            a, b, c, d = self.domain
            point_at_c = self.point2d_to_3d(design3d.Point2D(0.5 * (b - a), c))
            point_at_d = self.point2d_to_3d(design3d.Point2D(0.5 * (b - a), d))
            if point_at_d.is_close(point_at_c) or self.v_closed:
                self._y_periodicity = d - c
            else:
                self._y_periodicity = None
        return self._y_periodicity

    @property
    def bounding_box(self):
        """Gets the Bounding box of the BSpline Surface 3d."""
        if not self._bbox:
            self._bbox = self._bounding_box()
        return self._bbox

    def _bounding_box(self):
        """
        Computes the bounding box of the surface.

        """
        points = self.evalpts
        xmin = np.min(points[:, 0])
        ymin = np.min(points[:, 1])
        zmin = np.min(points[:, 2])

        xmax = np.max(points[:, 0])
        ymax = np.max(points[:, 1])
        zmax = np.max(points[:, 2])
        return design3d.core.BoundingBox(xmin, xmax, ymin, ymax, zmin, zmax)

    @property
    def surface_curves(self):
        """
        Extracts curves from a surface.
        """
        if not self._surface_curves:
            self._surface_curves = self.get_surface_curves()
        return self._surface_curves

    def get_surface_curves(self, **kwargs):
        """
        Extracts curves from a surface.
        """
        # Get keyword arguments
        extract_u = kwargs.get('extract_u', True)
        extract_v = kwargs.get('extract_v', True)

        cpts = self.control_points

        # v-direction
        crvlist_v = []
        weights = []
        if extract_v:
            for u in range(self.nb_u):
                control_points = [cpts[v + (self.nb_v * u)] for v in range(self.nb_v)]
                if self.rational:
                    weights = [self.weights[v + (self.nb_v * u)] for v in range(self.nb_v)]
                curve = edges.BSplineCurve3D(self.degree_v, control_points, self.v_multiplicities,
                                             self.v_knots, weights)
                crvlist_v.append(curve)

        # u-direction
        crvlist_u = []
        if extract_u:
            for v in range(self.nb_v):
                control_points = [cpts[v + (self.nb_v * u)] for u in range(self.nb_u)]
                if self.rational:
                    weights = [self.weights[v + (self.nb_v * u)] for u in range(self.nb_u)]
                curve = edges.BSplineCurve3D(self.degree_u, control_points, self.u_multiplicities,
                                             self.u_knots, weights)
                crvlist_u.append(curve)

        # Return shapes as a dict object
        return {"u": crvlist_u, "v": crvlist_v}

    def extract_curves(self, u: List[float] = None, v: List[float] = None):
        """
        Extracts curves from a surface.

        :param u: a list of parameters in ascending order in u direction to extract curves
        :param v: a list of parameters in ascending order in v direction to extract curves
        :return: a dictionary containing the extracted curves in u and v direction
        :rtype: dict
        """
        umin, umax, d3din, d3dax = self.domain

        def extract_from_surface_boundary_u(u_pos):
            weights = None
            control_points = [self.control_points[j + (self.nb_v * u_pos)] for j in range(self.nb_v)]
            if self.rational:
                weights = [self.weights[j + (self.nb_v * u_pos)] for j in range(self.nb_v)]
            return edges.BSplineCurve3D(self.degree_v, control_points, self.v_multiplicities, self.v_knots, weights)

        def extract_from_surface_boundary_v(v_pos):
            weights = None
            control_points = [self.control_points[v_pos + (self.nb_v * i)] for i in range(self.nb_u)]
            if self.rational:
                weights = [self.weights[v_pos + (self.nb_v * i)] for i in range(self.nb_u)]
            return edges.BSplineCurve3D(self.degree_u, control_points, self.u_multiplicities, self.u_knots, weights)
        # v-direction
        crvlist_v = []
        if v:
            for param in v:
                if abs(param - d3din) < 1e-6:
                    crvlist_v.append(extract_from_surface_boundary_v(0))
                elif abs(param - d3dax) < 1e-6:
                    crvlist_v.append(extract_from_surface_boundary_v(self.nb_v - 1))
                else:
                    curve = extract_surface_curve_v(self, param, edges.BSplineCurve3D)
                    crvlist_v.append(curve)

        # u-direction
        crvlist_u = []
        if u:
            for param in u:
                if abs(param - umin) < 1e-6:
                    crvlist_u.append(extract_from_surface_boundary_u(0))
                elif abs(param - umax) < 1e-6:
                    crvlist_u.append(extract_from_surface_boundary_u(self.nb_u - 1))
                else:
                    curve = extract_surface_curve_u(self, param, edges.BSplineCurve3D)
                    crvlist_u.append(curve)

        # Return shapes as a dict object
        return {"u": crvlist_u, "v": crvlist_v}

    def u_iso(self, u: float) -> edges.BSplineCurve3D:
        """
        Returns the u-iso curve of the surface.

        :param u: The value of u where to extract the curve.
        :type u: float
        :return: A line 3D
        :rtype: :class:`curves.Line3D`
        """
        return self.extract_curves(u=[u])["u"][0]

    def v_iso(self, v: float) -> edges.BSplineCurve3D:
        """
        Returns the v-iso curve of the surface.

        :param v: The value of v where to extract the curve.
        :type u: float
        :return: A BSpline curve 3D
        :rtype: :class:`edges.BSplineCurve3D`
        """
        return self.extract_curves(v=[v])["v"][0]

    def evaluate(self, **kwargs):
        """
        Evaluates the surface.

        The evaluated points are stored in :py:attr:`evalpts` property.

        Keyword Arguments:
            * ``start_u``: start parameter on the u-direction
            * ``stop_u``: stop parameter on the u-direction
            * ``start_v``: start parameter on the v-direction
            * ``stop_v``: stop parameter on the v-direction

        The ``start_u``, ``start_v`` and ``stop_u`` and ``stop_v`` parameters allow evaluation of a surface segment
        in the range  *[start_u, stop_u][start_v, stop_v]* i.e. the surface will also be evaluated at the ``stop_u``
        and ``stop_v`` parameter values.

        """
        knotvector_u = self.knots_vector_u
        knotvector_v = self.knots_vector_v
        # Find evaluation start and stop parameter values
        start_u = kwargs.get('start_u', knotvector_u[self.degree_u])
        stop_u = kwargs.get('stop_u', knotvector_u[-(self.degree_u + 1)])
        start_v = kwargs.get('start_v', knotvector_v[self.degree_v])
        stop_v = kwargs.get('stop_v', knotvector_v[-(self.degree_v + 1)])

        # Evaluate and cache
        self._eval_points = np.asarray(evaluate_surface(self.data,
                                                        start=(start_u, start_v),
                                                        stop=(stop_u, stop_v)), dtype=np.float64)

    @property
    def evalpts(self):
        """
        Evaluated points.

        :getter: Gets the coordinates of the evaluated points
        :type: list
        """
        if self._eval_points is None or len(self._eval_points) == 0:
            self.evaluate()
        return self._eval_points

    @property
    def u_domain(self):
        """The parametric domain of the surface in the U direction."""
        knotvector_u = self.knots_vector_u
        start_u = knotvector_u[self.degree_u]
        stop_u = knotvector_u[-(self.degree_u + 1)]
        return start_u, stop_u

    @property
    def v_domain(self):
        """The parametric domain of the surface in the V direction."""
        knotvector_v = self.knots_vector_v
        # Find evaluation start and stop parameter values
        start_v = knotvector_v[self.degree_v]
        stop_v = knotvector_v[-(self.degree_v + 1)]
        return start_v, stop_v

    @property
    def domain(self):
        """
        Domain.

        Domain is determined using the knot vector(s).

        :getter: Gets the domain
        """
        if not self._domain:
            umin, umax = self.u_domain
            d3din, d3dax = self.v_domain

            self._domain = umin, umax, d3din, d3dax
        return self._domain

    def copy(self, deep: bool = True, **kwargs):
        """
        Returns a copy of the instance.

        :param deep: If False, perform a shallow copy. If True, perform a deep copy.
        """
        if deep:
            weights = None
            if self.rational:
                weights = self._weights.copy()
            return self.__class__(self.degree_u, self.degree_v, self.control_points, self.nb_u, self.nb_v,
                                  self.u_multiplicities.copy(), self.v_multiplicities.copy(), self.u_knots.copy(),
                                  self.v_knots.copy(), weights, name=self.name + "_copy")
        return self.__class__(self.degree_u, self.degree_v, self.control_points, self.nb_u, self.nb_v,
                              self.u_multiplicities, self.v_multiplicities, self.u_knots,
                              self.v_knots, self.weights, name=self.name + "_copy")

    def to_geomdl(self):
        """Translate into a geomdl object."""
        if not self._surface:
            if self._weights is None:
                surface = BSpline.Surface()
                points = self.ctrlpts.tolist()

            else:
                surface = NURBS.Surface()
                points = [(control_point[0] * self._weights[i], control_point[1] * self._weights[i],
                           control_point[2] * self._weights[i], self._weights[i])
                          for i, control_point in enumerate(self.control_points)]
            surface.degree_u = self.degree_u
            surface.degree_v = self.degree_v
            surface.set_ctrlpts(points, self.nb_u, self.nb_v)
            knot_vector = self.knotvector
            surface.knotvector_u = knot_vector[0]
            surface.knotvector_v = knot_vector[1]
            surface.delta = 0.05
            self._surface = surface
        return self._surface

    def to_dict(self, *args, **kwargs):
        """Avoids storing points in memo that makes serialization slow."""
        dict_ = self.base_dict()
        dict_['degree_u'] = self.degree_u
        dict_['degree_v'] = self.degree_v
        dict_['control_points'] = [point.to_dict() for point in self.control_points]
        dict_['nb_u'] = self.nb_u
        dict_['nb_v'] = self.nb_v
        dict_['u_multiplicities'] = self.u_multiplicities.tolist()
        dict_['v_multiplicities'] = self.v_multiplicities.tolist()
        dict_['u_knots'] = self.u_knots.tolist()
        dict_['v_knots'] = self.v_knots.tolist()
        dict_['weights'] = self.weights

        return dict_

    def ctrlpts2d(self):
        """
        Each row represents the control points in u direction and each column the points in v direction.
        """
        ctrlpts = self.ctrlptsw if self.rational else self.ctrlpts
        return np.reshape(ctrlpts, (self.nb_u, self.nb_v, -1))

    def vertices(self):
        """
        Evaluated points.

        :getter: Gets the coordinates of the evaluated points
        :type: list
        """
        u_min, u_max, v_min, v_max = self.domain
        if self._vertices is None or len(self._vertices) == 0:
            vertices = []
            u_vector = np.linspace(u_min, u_max, self.sample_size_u, dtype=np.float64)
            v_vector = np.linspace(v_min, v_max, self.sample_size_v, dtype=np.float64)
            for u in u_vector:
                for v in v_vector:
                    vertices.append((u, v))
            self._vertices = vertices
        return self._vertices

    def points(self):
        """
        Returns surface points.
        """
        return [design3d.Point3D(*point) for point in self.evalpts]

    def control_points_matrix(self, coordinates):
        """
        Define control points like a matrix, for each coordinate: x:0, y:1, z:2.
        """

        points = np.empty((self.nb_u, self.nb_v))
        for i in range(0, self.nb_u):
            for j in range(0, self.nb_v):
                points[i][j] = self.control_points_table[i][j][coordinates]
        return points

    def basis_functions_u(self, u, k, i):
        """
        Compute basis functions Bi in u direction for u=u and degree=k.

        """

        # k = self.degree_u
        knots_vector_u = self.knots_vector_u

        if k == 0:
            return 1.0 if knots_vector_u[i] <= u < knots_vector_u[i + 1] else 0.0
        if knots_vector_u[i + k] == knots_vector_u[i]:
            param_c1 = 0.0
        else:
            param_c1 = (u - knots_vector_u[i]) / (knots_vector_u[i + k] - knots_vector_u[i]) \
                       * self.basis_functions_u(u, k - 1, i)
        if knots_vector_u[i + k + 1] == knots_vector_u[i + 1]:
            param_c2 = 0.0
        else:
            param_c2 = (knots_vector_u[i + k + 1] - u) / (knots_vector_u[i + k + 1] - knots_vector_u[i + 1]) * \
                       self.basis_functions_u(u, k - 1, i + 1)
        return param_c1 + param_c2

    def basis_functions_v(self, v, k, i):
        """
        Compute basis functions Bi in v direction for v=v and degree=k.

        """

        # k = self.degree_u
        knots = self.knots_vector_v

        if k == 0:
            return 1.0 if knots[i] <= v < knots[i + 1] else 0.0
        if knots[i + k] == knots[i]:
            param_c1 = 0.0
        else:
            param_c1 = (v - knots[i]) / (knots[i + k] - knots[i]) * self.basis_functions_v(v, k - 1, i)
        if knots[i + k + 1] == knots[i + 1]:
            param_c2 = 0.0
        else:
            param_c2 = (knots[i + k + 1] - v) / (knots[i + k + 1] - knots[i + 1]) * self.basis_functions_v(v, k - 1,
                                                                                                           i + 1)
        return param_c1 + param_c2

    def derivatives(self, u, v, order):
        """
        Evaluates n-th order surface derivatives at the given (u, v) parameter pair.

        :param u: Point's u coordinate.
        :type u: float
        :param v: Point's v coordinate.
        :type v: float
        :param order: Order of the derivatives.
        :type order: int
        :return: A list SKL, where SKL[k][l] is the derivative of the surface S(u,v) with respect
        to u k times and v l times
        :rtype: List[`design3d.Vector3D`]
        """
        if self.weights is not None:
            control_points = self.ctrlptsw
        else:
            control_points = self.ctrlpts
        derivatives = derivatives_surface([self.degree_u, self.degree_v], self.knotvector, control_points,
                                          [self.nb_u, self.nb_v], self.rational, [u, v], order)
        for i in range(order + 1):
            for j in range(order + 1):
                derivatives[i][j] = design3d.Vector3D(*derivatives[i][j])
        return derivatives

    def blending_vector_u(self, u):
        """
        Compute a vector of basis_functions in u direction for u=u.
        """

        blending_vect = np.empty((1, self.nb_u))
        for j in range(0, self.nb_u):
            blending_vect[0][j] = self.basis_functions_u(u, self.degree_u, j)

        return blending_vect

    def blending_vector_v(self, v):
        """
        Compute a vector of basis_functions in v direction for v=v.

        """

        blending_vect = np.empty((1, self.nb_v))
        for j in range(0, self.nb_v):
            blending_vect[0][j] = self.basis_functions_v(v, self.degree_v, j)

        return blending_vect

    def blending_matrix_u(self, u):
        """
        Compute a matrix of basis_functions in u direction for a vector u like [0,1].

        """

        blending_mat = np.empty((len(u), self.nb_u))
        for i, u_i in enumerate(u):
            for j in range(self.nb_u):
                blending_mat[i][j] = self.basis_functions_u(u_i, self.degree_u, j)
        return blending_mat

    def blending_matrix_v(self, v):
        """
        Compute a matrix of basis_functions in v direction for a vector v like [0,1].

        """

        blending_mat = np.empty((len(v), self.nb_v))
        for i, v_i in enumerate(v):
            for j in range(self.nb_v):
                blending_mat[i][j] = self.basis_functions_v(v_i, self.degree_v, j)
        return blending_mat

    @lru_cache(maxsize=6)
    def decompose(self, return_params: bool = False, decompose_dir="uv"):
        """
        Decomposes the surface into Bezier surface patches of the same degree.

        :param return_params: If True, returns the parameters from start and end of each Bézier patch
         with repect to the input curve.
        :type return_params: bool
        :param decompose_dir: Direction of decomposition. 'uv', 'u' or 'v'.
        :type decompose_dir: str
        """
        return decompose_surface(self, return_params, decompose_dir=decompose_dir)

    def point2d_to_3d(self, point2d: design3d.Point2D):
        """
        Evaluate the surface at a given parameter coordinate.
        """
        u, v = point2d
        umin, umax, d3din, d3dax = self.domain
        u = float(min(max(u, umin), umax))
        v = float(min(max(v, d3din), d3dax))
        point_array = evaluate_surface(self.data, start=(u, v), stop=(u, v))[0]
        return design3d.Point3D(*point_array)

    def _get_grid_bounds(self, params, delta_u, delta_v):
        """
        Update bounds and grid_size at each iteration of point inversion grid search.
        """
        u, v = params
        if u == self.domain[0]:
            u_start = self.domain[0]
            u_stop = self.domain[0]
            sample_size_u = 1

        elif u == self.domain[1]:
            u_start = self.domain[1]
            u_stop = self.domain[1]
            sample_size_u = 1
        else:
            u_start = max(u - delta_u, self.domain[0])
            u_stop = min(u + delta_u, self.domain[1])
            sample_size_u = 10

        if v == self.domain[2]:
            v_start = self.domain[2]
            v_stop = self.domain[2]
            sample_size_v = 1
        elif v == self.domain[3]:
            v_start = self.domain[3]
            v_stop = self.domain[3]
            sample_size_v = 1
        else:
            v_start = max(v - delta_v, self.domain[2])
            v_stop = min(v + delta_v, self.domain[3])
            sample_size_v = 10
        return u_start, u_stop, v_start, v_stop, sample_size_u, sample_size_v

    def _update_parameters(self, bounds, sample_size_u, sample_size_v, index):
        """
        Helper function to update parameters of point inversion grid search at each iteration.
        """
        u_start, u_stop, v_start, v_stop = bounds
        if sample_size_u == 1:
            delta_u = 0.0
            u = u_start
            delta_v = (v_stop - v_start) / (sample_size_v - 1)
            v = v_start + index * delta_v
        elif sample_size_v == 1:
            delta_u = (u_stop - u_start) / (sample_size_u - 1)
            u = u_start + index * delta_u
            delta_v = 0.0
            v = v_start
        else:
            u, v, delta_u, delta_v = self._get_params_from_evaluation_position_bounds_and_sizes(index, bounds,
                                                                                                sample_size_u,
                                                                                                sample_size_v)

        return u, v, delta_u, delta_v

    @staticmethod
    def _find_index_min(matrix_points, point):
        """Helper function to find point of minimal distance."""
        distances = np.linalg.norm(matrix_points - point, axis=1)
        indexes = np.argsort(distances)
        index = indexes[0]
        return index, distances[index]

    def _point_inversion_initialization(self, point3d_array):
        """
        Helper function to initialize parameters.
        """

        if self.nb_u > 15 * self.nb_v:
            self.sample_size_u, self.sample_size_v = 80, 5
        elif self.nb_v > 15 * self.nb_u:
            self.sample_size_u, self.sample_size_v = 5, 80

        initial_index, minimal_distance = self._find_index_min(self.evalpts, point3d_array)

        u, v, delta_u, delta_v = self._get_params_from_evaluation_position_bounds_and_sizes(initial_index, self.domain,
                                                                                            self.sample_size_u,
                                                                                            self.sample_size_v)
        u_start, u_stop, v_start, v_stop = self.domain
        sample_size_u = 10
        sample_size_v = 10
        if u == u_start:
            u_stop = u + delta_u
            sample_size_u = 5
        elif u == u_stop:
            u_start = u - delta_u
            sample_size_u = 5
        else:
            u_start = max(u - delta_u, self.domain[0])
            u_stop = min(u + delta_u, self.domain[1])

        if v == v_start:
            v_stop = v + delta_v
            sample_size_v = 5
        elif v == v_stop:
            v_start = v - delta_v
            sample_size_v = 5
        else:
            v_start = max(v - delta_v, self.domain[2])
            v_stop = min(v + delta_v, self.domain[3])
        return u, v, u_start, u_stop, v_start, v_stop, delta_u, delta_v, sample_size_u, sample_size_v, minimal_distance

    def _helper_point_inversion_grid_search_update_evaluation_data(self, sample_size_u, sample_size_v):
        """
        Helper function to get the evaluation data of the surface adding a given sample size in both u and v direction.

        This function is required for performance and coherence purposes to avoid modifying the surface sample size
        in each iteration.
        """
        datadict = {
            "degree": (self.degree_u, self.degree_v),
            "knotvector": self.knotvector,
            "size": (self.nb_u, self.nb_v),
            "sample_size": [sample_size_u, sample_size_v],
            "rational": self.rational,
            "precision": 18
        }
        if self.rational:
            datadict["control_points"] = self.ctrlptsw
        else:
            datadict["control_points"] = self.ctrlpts
        return datadict

    @staticmethod
    def _get_params_from_evaluation_position_bounds_and_sizes(index, bounds, sample_size_u, sample_size_v):
        """
        Gets the values of u, v of an evalution point from its index in a list that follows a known structure.
        """
        u_start, u_stop, v_start, v_stop = bounds
        u_idx = int(index / sample_size_v)
        v_idx = index % sample_size_v
        delta_u = (u_stop - u_start) / (sample_size_u - 1)
        delta_v = (v_stop - v_start) / (sample_size_v - 1)
        u = u_start + u_idx * delta_u
        v = v_start + v_idx * delta_v

        return u, v, delta_u, delta_v

    def point_inversion_grid_search(self, point3d, acceptable_distance, max_iter: int = 15):
        """
        Find the parameters (u, v) of a 3D point on the BSpline surface using a grid search algorithm.
        """
        point3d_array = np.asarray(point3d)
        u, v, u_start, u_stop, v_start, v_stop, delta_u, delta_v, sample_size_u, sample_size_v, minimal_distance = \
            self._point_inversion_initialization(point3d_array)
        if minimal_distance <= acceptable_distance:
            return (u, v), minimal_distance

        datadict = self._helper_point_inversion_grid_search_update_evaluation_data(sample_size_u, sample_size_v)
        last_distance = 0.0
        count = 0
        while minimal_distance > acceptable_distance and count < max_iter:
            if count > 0:
                u_start, u_stop, v_start, v_stop, sample_size_u, sample_size_v = self._get_grid_bounds(
                    (u, v), delta_u, delta_v)

            if sample_size_u == 1 and sample_size_v == 1:
                break
            datadict["sample_size"] = [sample_size_u, sample_size_v]
            matrix = np.asarray(evaluate_surface(datadict, start=(u_start, v_start), stop=(u_stop, v_stop)),
                                dtype=np.float64)
            index, distance = self._find_index_min(matrix, point3d_array)
            u, v, delta_u, delta_v = self._update_parameters([u_start, u_stop, v_start, v_stop], sample_size_u,
                                                             sample_size_v, index)

            if distance < minimal_distance:
                minimal_distance = distance
            if minimal_distance < acceptable_distance:
                break
            if abs(distance - last_distance) < acceptable_distance * 0.01:
                break

            last_distance = distance
            count += 1

        return (u, v), minimal_distance

    def point3d_to_2d(self, point3d: design3d.Point3D, tol=1e-6):
        """
        Evaluates the parametric coordinates (u, v) of a 3D point (x, y, z).

        :param point3d: A 3D point to be evaluated.
        :type point3d: :class:`design3d.Point3D`
        :param tol: Tolerance to accept the results.
        :type tol: float
        :return: The parametric coordinates (u, v) of the point.
        :rtype: :class:`design3d.Point2D`
        """
        umin, umax, d3din, d3dax = self.domain
        point = None
        if self.is_singularity_point(point3d, tol=tol):
            if self.u_closed_upper(tol) and point3d.is_close(self.point2d_to_3d(design3d.Point2D(umin, d3dax)), tol):
                point = design3d.Point2D(umin, d3dax)
            elif self.u_closed_lower(tol) and point3d.is_close(self.point2d_to_3d(design3d.Point2D(umin, d3din)), tol):
                point = design3d.Point2D(umin, d3din)
            elif self.v_closed_upper(tol) and point3d.is_close(self.point2d_to_3d(design3d.Point2D(umax, d3din)), tol):
                return design3d.Point2D(umax, d3din)
            elif self.v_closed_lower(tol) and point3d.is_close(self.point2d_to_3d(design3d.Point2D(umin, d3din)), tol):
                point = design3d.Point2D(umin, d3din)
            if point:
                return point

        x0, distance = self.point_inversion_grid_search(point3d, 5e-5)
        if distance < tol:
            return design3d.Point2D(*x0)
        x1, _, distance = self.point_inversion(x0, point3d, tol)
        if distance <= tol:
            return design3d.Point2D(*x1)
        return self.point3d_to_2d_minimize(point3d, x0, distance, tol)

    def point3d_to_2d_minimize(self, point3d, initial_guess, point_inversion_result, tol):
        """Auxiliary function for point3d_to_2d in case the point inversion does not converge."""

        def fun(x):
            derivatives = self.derivatives(x[0], x[1], 1)
            vector = derivatives[0][0] - point3d
            f_value = vector.norm()
            if f_value == 0.0:
                jacobian = np.array([0.0, 0.0])
            else:
                jacobian = np.array([vector.dot(derivatives[1][0]) / f_value,
                                     vector.dot(derivatives[0][1]) / f_value])
            return f_value, jacobian

        u_start, u_stop, v_start, v_stop = self.domain
        results = []

        res = minimize(fun, x0=np.array(initial_guess), jac=True,
                       bounds=[(u_start, u_stop),
                               (v_start, v_stop)])
        if res.fun <= tol or (tol > 1e-7 and res.success
                              and abs(res.fun - point_inversion_result) <= tol and res.fun < 5 * tol):
            return design3d.Point2D(*res.x)
        results = [(res.x, res.fun)]
        if self.u_closed:
            res = minimize(fun, x0=np.array((u_start, initial_guess[1])), jac=True,
                           bounds=[(u_start, u_stop),
                                   (v_start, v_stop)])
            if res.fun <= tol:
                return design3d.Point2D(u_start, initial_guess[1])
            results.append((res.x, res.fun))
            res = minimize(fun, x0=np.array((u_stop, initial_guess[1])), jac=True,
                           bounds=[(u_start, u_stop),
                                   (v_start, v_stop)])
            if res.fun <= tol:
                return design3d.Point2D(u_stop, initial_guess[1])
            results.append((res.x, res.fun))
        if self.v_closed:
            res = minimize(fun, x0=np.array((initial_guess[0], v_start)), jac=True,
                           bounds=[(u_start, u_stop),
                                   (v_start, v_stop)])
            results.append((res.x, res.fun))
            if res.fun <= tol:
                return design3d.Point2D(initial_guess[0], v_start)
            res = minimize(fun, x0=np.array((initial_guess[0], v_stop)), jac=True,
                           bounds=[(u_start, u_stop),
                                   (v_start, v_stop)])
            if res.fun <= tol:
                return design3d.Point2D(initial_guess[0], v_stop)
            results.append((res.x, res.fun))

        point3d_array = np.asarray(point3d)

        if self.u_knots.shape[0] > 2 or self.v_knots.shape[0] > 2:
            decompose_dir = "uv"
            if self.u_closed:
                decompose_dir = "v"
            if self.v_closed:
                decompose_dir = "u"
            for patch, param in self.decompose(return_params=True, decompose_dir=decompose_dir):
                xmin, ymin, zmin = patch.ctrlpts.min(axis=0)
                xmax, ymax, zmax = patch.ctrlpts.max(axis=0)

                bbox = design3d.core.BoundingBox(xmin, xmax, ymin, ymax, zmin, zmax)
                if bbox.point_inside(point3d):
                    distances = np.linalg.norm(patch.evalpts - point3d_array, axis=1)
                    index = np.argmin(distances)
                    u_start, u_stop, v_start, v_stop = patch.domain
                    delta_u = (u_stop - u_start) / (patch.sample_size_u - 1)
                    delta_v = (v_stop - v_start) / (patch.sample_size_v - 1)
                    u_idx = int(index / patch.sample_size_v)
                    v_idx = index % patch.sample_size_v

                    u = u_start + u_idx * delta_u
                    v = v_start + v_idx * delta_v

                    x1, _, distance = patch.point_inversion((u, v), point3d, 1e-6)
                    u = x1[0] * (param[0][1] - param[0][0]) + param[0][0]
                    v = x1[1] * (param[1][1] - param[1][0]) + param[1][0]
                    if distance < 5e-6:
                        return design3d.Point2D(u, v)
                    results.append(((u, v), distance))

        distances = np.linalg.norm(self.evalpts - point3d_array, axis=1)
        indexes = np.argsort(distances)
        delta_u = (u_stop - u_start) / (self.sample_size_u - 1)
        delta_v = (v_stop - v_start) / (self.sample_size_v - 1)
        if self.weights is not None:
            control_points = self.ctrlptsw
        else:
            control_points = self.ctrlpts
        for index in indexes[:2]:
            if index == 0:
                u_idx, v_idx = 0, 0
            else:
                u_idx = int(index / self.sample_size_v)
                v_idx = index % self.sample_size_v

            u = u_start + u_idx * delta_u
            v = v_start + v_idx * delta_v
            x0 = (u, v)
            res = point_inversion(point3d_array, x0, [(u_start, u_stop), (v_start, v_stop)],
                                  [self.degree_u, self.degree_v], self.knotvector, control_points,
                                  [self.nb_u, self.nb_v], self.rational)

            if res.fun < 1e-6:
                return design3d.Point2D(*res.x)

            results.append((res.x, res.fun))
        return design3d.Point2D(*min(results, key=lambda r: r[1])[0])

    def point_inversion(self, x, point3d, tol, maxiter: int = 50):
        """
        Performs point inversion.

        Given a point P = (x, y, z) assumed to lie on the NURBS surface S(u, v), point inversion is
        the problem of finding the corresponding parameters u, v that S(u, v) = P.
        """
        jacobian, k, surface_derivatives, distance_vector = self.point_inversion_funcs(x, point3d)
        dist, check = self.check_convergence(surface_derivatives, distance_vector, tol1=tol)
        if maxiter == 1:
            return x, False, dist
        if check:
            return x, True, dist
        if maxiter == 1:
            return x, False, dist
        if jacobian[1][1]:
            lu, piv = lu_factor(jacobian)
            delta = lu_solve((lu, piv), k)
            new_x = [delta[0][0] + x[0], delta[1][0] + x[1]]
            new_x = self.check_bounds(new_x)
        else:
            new_x = x
        residual = (new_x[0] - x[0]) * surface_derivatives[1][0] + (new_x[1] - x[1]) * surface_derivatives[0][1]
        if residual.norm() <= 1e-12:
            return x, False, dist
        x = new_x
        return self.point_inversion(x, point3d, tol, maxiter=maxiter - 1)

    def point_inversion_funcs(self, x, point3d):
        """Returns functions evaluated at x."""
        surface_derivatives = self.derivatives(x[0], x[1], 2)
        distance_vector = surface_derivatives[0][0] - point3d
        common_term = (surface_derivatives[1][0].dot(surface_derivatives[0][1]) +
                       distance_vector.dot(surface_derivatives[1][1]))
        jacobian = np.asarray(
            [[surface_derivatives[1][0].norm() ** 2 + distance_vector.dot(surface_derivatives[2][0]),
              common_term],
             [common_term,
              surface_derivatives[0][1].norm() ** 2 + distance_vector.dot(surface_derivatives[0][2])]])
        k = np.asarray(
            [[-(distance_vector.dot(surface_derivatives[1][0]))], [-(distance_vector.dot(surface_derivatives[0][1]))]])

        return jacobian, k, surface_derivatives, distance_vector

    @staticmethod
    def check_convergence(surf_derivatives, distance_vector, tol1: float = 1e-6, tol2: float = 1e-8):
        """Check convergence of point inversion method."""
        dist = distance_vector.norm()
        if dist <= tol1:
            return dist, True
        zero_cos_u = abs(surf_derivatives[1][0].dot(distance_vector)) / (
                (surf_derivatives[1][0].norm() + 1e-12) * dist)
        zero_cos_v = abs(surf_derivatives[0][1].dot(distance_vector)) / (
                (surf_derivatives[0][1].norm() + 1e-12) * dist)

        if zero_cos_u <= tol2 and zero_cos_v <= tol2:
            return dist, True
        return dist, False

    def check_bounds(self, x):
        """Check surface bounds."""
        u, v = x
        a, b, c, d = self.domain

        if u < a:
            u = a

        elif u > b:
            u = b

        if v < c:
            v = c

        elif v > d:
            v = d

        x[0] = u
        x[1] = v
        return x

    def parametric_points_to_3d(self, points: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Transform parametric coordinates to 3D points on the BSpline surface.

        Given a set of parametric coordinates `(u, v)` representing points on the surface,
        this method returns the corresponding 3D points on the BSpline surface.

        :param points: Parametric coordinates in the form of a numpy array with shape (n, 2),
                       where `n` is the number of points, and each row corresponds to `(u, v)`.
        :type points: numpy.ndarray[np.float64]

        :return: Array of 3D points representing the BSpline surface in Cartesian coordinates.
        :rtype: numpy.ndarray[np.float64]
        """
        umin, umax, d3din, d3dax = self.domain
        params = [(float(min(max(u, umin), umax)), float(min(max(v, d3din), d3dax))) for u, v in points]
        return np.asarray([evaluate_surface(self.data, start=param, stop=param)[0] for param in params],
                          dtype=np.float64)

    def linesegment2d_to_3d(self, linesegment2d):
        """Evaluates the Euclidean form for the parametric line segment."""
        points = []
        direction_vector = linesegment2d.unit_direction_vector(0.0)
        start3d = self.point2d_to_3d(linesegment2d.start)
        end3d = self.point2d_to_3d(linesegment2d.end)
        if direction_vector.is_colinear_to(design3d.X2D):
            curve = self.v_iso(linesegment2d.start.y)
            if linesegment2d.start.x > linesegment2d.end.x:
                curve = curve.reverse()
            return [curve.trim(start3d, end3d)]
        if direction_vector.is_colinear_to(design3d.Y2D):
            curve = self.u_iso(linesegment2d.start.x)
            if linesegment2d.start.y > linesegment2d.end.y:
                curve = curve.reverse()
            return [curve.trim(start3d, end3d)]
        n = 20
        for point in linesegment2d.discretization_points(number_points=n):
            point3d = self.point2d_to_3d(point)
            if not point3d.in_list(points):
                points.append(point3d)
        if len(points) < 2:
            return None
        if len(points) == 2:
            return [design3d.edges.LineSegment3D(points[0], points[-1])]
        if len(points) < min(self.degree_u, self.degree_v) + 1:
            bspline = edges.BSplineCurve3D.from_points_interpolation(points, 2, centripetal=True)
            return [bspline]

        bspline = edges.BSplineCurve3D.from_points_interpolation(points, min(self.degree_u, self.degree_v),
                                                                 centripetal=True)
        return [bspline.simplify]

    def linesegment3d_to_2d(self, linesegment3d):
        """
        A line segment on a BSplineSurface3D will be in any case a line in 2D?.

        """
        tol = 1e-6 if linesegment3d.length() > 1e-5 else 1e-7
        if self.u_closed or self.v_closed:
            discretization_points = linesegment3d.discretization_points(number_points=3)
            parametric_points = [self.point3d_to_2d(point, tol) for point in discretization_points]
            start, _, end = self._fix_start_end_singularity_point_at_parametric_domain(linesegment3d,
                                                                                       parametric_points,
                                                                                       discretization_points, tol)
        else:
            start = self.point3d_to_2d(linesegment3d.start, tol)
            end = self.point3d_to_2d(linesegment3d.end, tol)
            umin, umax, d3din, d3dax = self.domain
            if self.x_periodicity and \
                    (math.isclose(end.x, umin, abs_tol=1e-3) or math.isclose(end.x, umax, abs_tol=1e-3)):
                end.x = start.x
            if self.y_periodicity and \
                    (math.isclose(end.y, d3din, abs_tol=1e-3) or math.isclose(end.y, d3dax, abs_tol=1e-3)):
                end.y = start.y
        if start.is_close(end):
            return None
        return [edges.LineSegment2D(start, end)]

    def _repair_periodic_boundary_points(self, edge3d, points, direction_periodicity):
        """
        Verifies points at boundary on a periodic BSplineSurface3D.

        :param points: List of `design3d.Point2D` after transformation from 3D Cartesian coordinates
        :type points: List[design3d.Point2D]
        :param direction_periodicity: should be 'x' if x_periodicity or 'y' if y periodicity
        :type direction_periodicity: str
        """
        lth = edge3d.length()
        pt_after_start = self.point3d_to_2d(edge3d.point_at_abscissa(0.15 * lth))
        pt_before_end = self.point3d_to_2d(edge3d.point_at_abscissa(0.85 * lth))
        min_bound_x, max_bound_x, min_bound_y, max_bound_y = self.domain
        if direction_periodicity == 'x':
            i = 0
            min_bound, max_bound = min_bound_x, max_bound_x
            periodicity = self.x_periodicity
        else:
            i = 1
            min_bound, max_bound = min_bound_y, max_bound_y
            periodicity = self.y_periodicity

        start = points[0]
        end = points[-1]
        delta = max_bound + min_bound

        if math.isclose(start[i], min_bound, abs_tol=1e-4) and pt_after_start[i] > 0.5 * delta:
            start[i] = max_bound
        elif math.isclose(start[i], max_bound, abs_tol=1e-4) and pt_after_start[i] < 0.5 * delta:
            start[i] = min_bound

        if math.isclose(end[i], min_bound, abs_tol=1e-4) and pt_before_end[i] > 0.5 * delta:
            end[i] = max_bound
        elif math.isclose(end[i], max_bound, abs_tol=1e-4) and pt_before_end[i] < 0.5 * delta:
            end[i] = min_bound

        points[0] = start
        points[-1] = end
        delta_i = abs(points[-1][i] - points[0][i])
        if ((delta_i <= 1e-5 or math.isclose(delta_i, periodicity, abs_tol=1e-3)) and
                all((math.isclose(p[i], max_bound, abs_tol=1e-2) or math.isclose(p[i], min_bound, abs_tol=1e-2))
                    for p in points)):
            # if the line is at the boundary of the surface domain, we take the first point as reference
            t_param = max_bound if math.isclose(points[0][i], max_bound, abs_tol=1e-4) else min_bound
            if direction_periodicity == 'x':
                points = [design3d.Point2D(t_param, p[1]) for p in points]
            else:
                points = [design3d.Point2D(p[0], t_param) for p in points]

        return points

    def _repair_points_order(self, points, edge3d, surface_domain, direction_periodicity):
        """Helper function to reorder edge discretization points on parametric domain."""
        min_bound_x, max_bound_x, min_bound_y, max_bound_y = surface_domain
        line_at_periodicity = edges.LineSegment3D(
            self.point2d_to_3d(design3d.Point2D(min_bound_x, min_bound_y)),
            self.point2d_to_3d(design3d.Point2D(
                min_bound_x if direction_periodicity == 'x' else max_bound_x,
                min_bound_y if direction_periodicity == 'y' else max_bound_y
            ))
        )
        if line_at_periodicity.point_belongs(edge3d.start) or line_at_periodicity.point_belongs(edge3d.end):
            return points

        intersections = edge3d.intersections(line_at_periodicity)
        if not intersections or len(intersections) > 1:
            return points
        point_at_periodicity = self.point3d_to_2d(intersections[0])
        index_periodicity = design3d.core.get_point_index_in_list(point_at_periodicity, points)

        if index_periodicity is not None:
            if edge3d.periodic:
                points = [point_at_periodicity] + points[index_periodicity + 1:-1] + points[:index_periodicity + 1]
            else:
                points = [point_at_periodicity] + points[index_periodicity + 1:] + points[:index_periodicity + 1]
        else:
            sign = points[1].x - points[0].x if direction_periodicity == 'x' else points[1].y - points[0].y
            for i, (point, next_point) in enumerate(zip(points[:-1], points[1:])):
                if sign * (next_point.x - point.x if direction_periodicity == 'x' else next_point.y - point.y) < 0:
                    index_periodicity = i
                    break
            if edge3d.periodic:
                points = ([point_at_periodicity] + points[index_periodicity + 1: -1] +
                          points[:index_periodicity + 1] + [point_at_periodicity])
            else:
                points = ([point_at_periodicity] + points[index_periodicity + 1:] +
                          points[:index_periodicity + 1] + [point_at_periodicity])

        return points

    def _fix_start_end_singularity_point_at_parametric_domain(self, edge3d, parametric_points,
                                                              discretization_points, tol):
        """
        Helper function to fix start and end points on surfaces with singularities.
        """
        start = parametric_points[0].copy()
        end = parametric_points[-1].copy()
        point_after_start = self.point3d_to_2d(edge3d.point_at_abscissa(0.02 * edge3d.length()))
        point_before_end = self.point3d_to_2d(edge3d.point_at_abscissa(0.98 * edge3d.length()))
        fixed = False
        if start_flag := self.is_singularity_point(edge3d.start) and self._is_line_segment(parametric_points[1:]):
            direction_vector = parametric_points[-1] - parametric_points[-2]
            if direction_vector.is_colinear_to(design3d.X2D, 1e-2):
                start.y = point_after_start.y
                parametric_points[0] = start
                fixed = True
            elif direction_vector.is_colinear_to(design3d.Y2D, 1e-2):
                start.x = point_after_start.x
                parametric_points[0] = start
                fixed = True
            else:
                fixed = False
        if end_flag := self.is_singularity_point(edge3d.end) and self._is_line_segment(parametric_points[:-1]):
            direction_vector = parametric_points[1] - parametric_points[0]
            if direction_vector.is_colinear_to(design3d.X2D, 1e-2):
                end.y = point_before_end.y
                parametric_points[-1] = end
                fixed = True
            elif direction_vector.is_colinear_to(design3d.Y2D, 1e-2):
                end.x = point_before_end.x
                parametric_points[-1] = end
                fixed = True
            else:
                fixed = False
        if (start_flag or end_flag) and not fixed:
            parametric_points = self.fix_start_end_singularity_point_any_direction(edge3d,
                                                                                   parametric_points,
                                                                                   discretization_points, tol)
        return parametric_points

    def _edge3d_to_2d(self, edge3d, discretization_points,
                      interpolation_degree, parametric_points, tol: float = 1e-6):
        """Helper function to get the parametric representation of a 3D edge on the BSpline surface."""
        if self.u_closed or self.v_closed:
            parametric_points = self._fix_start_end_singularity_point_at_parametric_domain(edge3d, parametric_points,
                                                                                           discretization_points, tol)

        if self.x_periodicity:
            parametric_points = self._repair_periodic_boundary_points(edge3d, parametric_points, 'x')

        if self.y_periodicity:
            parametric_points = self._repair_periodic_boundary_points(edge3d, parametric_points, 'y')

        if self._is_line_segment(parametric_points):
            return [edges.LineSegment2D(parametric_points[0], parametric_points[-1])]
        parametric_points = verify_repeated_parametric_points(parametric_points)
        if interpolation_degree >= len(parametric_points):
            interpolation_degree = len(parametric_points) - 1
        if len(parametric_points) > 1 and interpolation_degree > 1:
            brep = edges.BSplineCurve2D.from_points_interpolation(points=parametric_points,
                                                                  degree=interpolation_degree)
            if brep:
                return [brep]
        return None

    def bsplinecurve3d_to_2d(self, bspline_curve3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        lth = bspline_curve3d.length()

        if lth <= 1e-6:
            print('BSplineCurve3D skipped because it is too small')
            return None

        n = min(bspline_curve3d.ctrlpts.shape[0], 20)
        points3d = bspline_curve3d.discretization_points(number_points=n)
        tol = 1e-6 if lth > 5e-4 else 1e-7
        # todo: how to ensure convergence of point3d_to_2d ?
        points = [self.point3d_to_2d(point3d, tol) for point3d in points3d]
        if len(points) < 2:
            return None
        return self._edge3d_to_2d(bspline_curve3d, points3d, bspline_curve3d.degree, points)

    def fullarcellipse3d_to_2d(self, fullarcellipse3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        number_points = max(self.nb_u, self.nb_v)
        degree = max(self.degree_u, self.degree_v)
        tol = 1e-6 if fullarcellipse3d.length() > 1e-5 else 1e-7
        points3d = fullarcellipse3d.discretization_points(number_points=number_points)
        # todo: how to ensure convergence of point3d_to_2d ?
        points = [self.point3d_to_2d(point3d, tol) for point3d in points3d]
        return self._edge3d_to_2d(fullarcellipse3d, points3d, degree, points)

    @staticmethod
    def _is_line_segment(points):
        """Helper function to check if the BREP can be a line segment."""
        if points[0].is_close(points[-1]):
            return False
        linesegment = edges.LineSegment2D(points[0], points[-1])
        for point in points:
            if not linesegment.point_belongs(point, abs_tol=1e-2):
                return False
        return True

    def bsplinecurve2d_to_3d(self, bspline_curve2d):
        """
        Converts the parametric boundary representation into a 3D primitive.
        """
        if bspline_curve2d.name == "parametric.arc":
            start = self.point2d_to_3d(bspline_curve2d.start)
            interior = self.point2d_to_3d(bspline_curve2d.evaluate_single(0.5))
            end = self.point2d_to_3d(bspline_curve2d.end)
            vector_u1 = interior - start
            vector_u2 = interior - end
            dot_product = vector_u2.dot(vector_u1)
            if dot_product and abs(dot_product) != 1.0:
                return [edges.Arc3D.from_3_points(start, interior, end)]

        number_points = len(bspline_curve2d.control_points)
        points = []
        for point in bspline_curve2d.discretization_points(number_points=number_points):
            point3d = self.point2d_to_3d(point)
            if not point3d.in_list(points):
                points.append(point3d)
        if len(points) < bspline_curve2d.degree + 1:
            return None
        return [edges.BSplineCurve3D.from_points_interpolation(points, bspline_curve2d.degree, centripetal=True)]

    def arc3d_to_2d(self, arc3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        number_points = max(self.nb_u, self.nb_v)
        degree = min(self.degree_u, self.degree_v)
        points = []
        tol = 1e-6 if arc3d.length() > 1e-5 else 1e-8
        for point3d in arc3d.discretization_points(number_points=number_points):
            point2d = self.point3d_to_2d(point3d, tol)
            if not point2d.in_list(points):
                points.append(point2d)
        start = points[0]
        end = points[-1]
        min_bound_x, max_bound_x, min_bound_y, max_bound_y = self.domain
        if self.x_periodicity:
            points = self._repair_periodic_boundary_points(arc3d, points, 'x')
            start = points[0]
            end = points[-1]
            if start.is_close(end):
                if math.isclose(start.x, min_bound_x, abs_tol=1e-4):
                    end.x = max_bound_x
                else:
                    end.x = min_bound_x
        if self.y_periodicity:
            points = self._repair_periodic_boundary_points(arc3d, points, 'y')
            start = points[0]
            end = points[-1]
            if start.is_close(end):
                if math.isclose(start.y, min_bound_y, abs_tol=1e-4):
                    end.y = max_bound_y
                else:
                    end.y = min_bound_y
        if start.is_close(end):
            return []
        linesegment = edges.LineSegment2D(start, end, name="parametric.arc")
        flag = True
        for point in points:
            if not linesegment.point_belongs(point):
                flag = False
                break
        if flag:
            return [linesegment]
        if degree > len(points) - 1:
            degree = len(points) - 1
        return [edges.BSplineCurve2D.from_points_interpolation(points, degree, name="parametric.arc")]

    def arcellipse3d_to_2d(self, arcellipse3d):
        """
        Converts the primitive from 3D spatial coordinates to its equivalent 2D primitive in the parametric space.
        """
        # todo: Is this right? Needs detailed investigation
        number_points = max(self.nb_u, self.nb_v)
        degree = max(self.degree_u, self.degree_v)
        points3d = arcellipse3d.discretization_points(number_points=number_points)
        tol = 1e-6 if arcellipse3d.length() > 1e-5 else 1e-7
        points = [self.point3d_to_2d(point3d, tol) for point3d in points3d]
        return self._edge3d_to_2d(arcellipse3d, points3d, degree, points)

    def arc2d_to_3d(self, arc2d):
        """Evaluates the Euclidean form for the parametric arc."""
        number_points = math.ceil(arc2d.angle * 7) + 1  # 7 points per radian
        length = arc2d.length()
        points = [self.point2d_to_3d(arc2d.point_at_abscissa(i * length / (number_points - 1)))
                  for i in range(number_points)]
        return [edges.BSplineCurve3D.from_points_interpolation(
            points, max(self.degree_u, self.degree_v), centripetal=True)]

    def rectangular_cut(self, u1: float, u2: float,
                        v1: float, v2: float, name: str = ''):
        """Deprecated method, Use BSplineFace3D from_surface_rectangular_cut method."""
        raise AttributeError("BSplineSurface3D.rectangular_cut is deprecated."
                             " Use the class_method from_surface_rectangular_cut in BSplineFace3D instead")

    def rotation(self, center: design3d.Vector3D,
                 axis: design3d.Vector3D, angle: float):
        """
        BSplineSurface3D rotation.

        :param center: rotation center
        :param axis: rotation axis
        :param angle: angle rotation
        :return: a new rotated BSplineSurface3D
        """
        new_control_points = [p.rotation(center, axis, angle)
                              for p in self.control_points]
        new_bsplinesurface3d = BSplineSurface3D(self.degree_u, self.degree_v,
                                                new_control_points, self.nb_u,
                                                self.nb_v,
                                                self.u_multiplicities,
                                                self.v_multiplicities,
                                                self.u_knots, self.v_knots,
                                                self.weights, self.name)
        return new_bsplinesurface3d

    def translation(self, offset: design3d.Vector3D):
        """
        BSplineSurface3D translation.

        :param offset: translation vector
        :return: A new translated BSplineSurface3D
        """
        new_control_points = [p.translation(offset) for p in
                              self.control_points]
        new_bsplinesurface3d = BSplineSurface3D(self.degree_u, self.degree_v,
                                                new_control_points, self.nb_u,
                                                self.nb_v,
                                                self.u_multiplicities,
                                                self.v_multiplicities,
                                                self.u_knots, self.v_knots,
                                                self.weights, self.name)

        return new_bsplinesurface3d

    def frame_mapping(self, frame: design3d.Frame3D, side: str):
        """
        Changes frame_mapping and return a new BSplineSurface3D.

        side = 'old' or 'new'
        """
        new_control_points = [p.frame_mapping(frame, side) for p in
                              self.control_points]
        new_bsplinesurface3d = BSplineSurface3D(self.degree_u, self.degree_v,
                                                new_control_points, self.nb_u,
                                                self.nb_v,
                                                self.u_multiplicities,
                                                self.v_multiplicities,
                                                self.u_knots, self.v_knots,
                                                self.weights, self.name)
        return new_bsplinesurface3d

    def plot(self, ax=None, edge_style: EdgeStyle = EdgeStyle(color='grey', alpha=0.5), **kwargs):
        """Plot representation of the surface."""
        u_curves = self.surface_curves['u']
        v_curves = self.surface_curves['v']
        if ax is None:
            ax = plt.figure().add_subplot(111, projection='3d')
        for u in u_curves:
            u.plot(ax=ax, edge_style=edge_style)
        for v in v_curves:
            v.plot(ax=ax, edge_style=edge_style)
        for point in self.control_points:
            point.plot(ax, color=edge_style.color, alpha=edge_style.alpha)
        return ax

    def simplify_surface(self):
        """
        Verifies if BSplineSurface3D could be a Plane3D.

        :return: A planar surface if possible, otherwise, returns self.
        """
        points = [self.control_points[0]]
        vector_list = []
        for point in self.control_points[1:]:
            vector = point - points[0]
            is_colinear = any(vector.is_colinear_to(other_vector) for other_vector in vector_list)
            if not point.in_list(points) and not is_colinear:
                points.append(point)
                vector_list.append(vector)
                if len(points) == 3:
                    plane3d = Plane3D.from_3_points(*points)
                    if all(plane3d.point_belongs(point) for point in self.control_points):
                        return plane3d
                    break
        return self

    @classmethod
    def from_step(cls, arguments, object_dict, **kwargs):
        """
        Converts a step primitive to a BSplineSurface3D.

        :param arguments: The arguments of the step primitive.
        :type arguments: list
        :param object_dict: The dictionary containing all the step primitives
            that have already been instantiated.
        :type object_dict: dict
        :return: The corresponding BSplineSurface3D object.
        :rtype: :class:`design3d.faces.BSplineSurface3D`
        """
        name = arguments[0][1:-1]
        degree_u = int(arguments[1])
        degree_v = int(arguments[2])
        points_sets = arguments[3][1:-1].split("),")
        points_sets = [elem + ")" for elem in points_sets[:-1]] + [
            points_sets[-1]]
        control_points = []
        for points_set in points_sets:
            points = [object_dict[int(i[1:])] for i in
                      points_set[1:-1].split(",")]
            nb_v = len(points)
            control_points.extend(points)
        nb_u = int(len(control_points) / nb_v)

        u_multiplicities = [int(i) for i in arguments[8][1:-1].split(",")]
        v_multiplicities = [int(i) for i in arguments[9][1:-1].split(",")]
        u_knots = [float(i) for i in arguments[10][1:-1].split(",")]
        v_knots = [float(i) for i in arguments[11][1:-1].split(",")]
        # knot_spec = arguments[12]

        if len(arguments) >= 14:
            weight_data = [
                float(i) for i in
                arguments[13][1:-1].replace("(", "").replace(")", "").split(",")
            ]
        else:
            weight_data = None

        bsplinesurface = cls(degree_u, degree_v, control_points, nb_u, nb_v,
                             u_multiplicities, v_multiplicities, u_knots,
                             v_knots, weight_data, name)
        if not bsplinesurface.x_periodicity and not bsplinesurface.y_periodicity:
            bsplinesurface = bsplinesurface.simplify_surface()

        return bsplinesurface

    def to_step(self, current_id):
        """Converts object into a step entity."""
        content = ''
        point_matrix_ids = '('
        for points in self.control_points_table:
            point_ids = '('
            for point in points:
                point_content, point_id = point.to_step(current_id)
                content += point_content
                point_ids += f'#{point_id},'
                current_id = point_id + 1
            point_ids = point_ids[:-1]
            point_ids += '),'
            point_matrix_ids += point_ids
        point_matrix_ids = point_matrix_ids[:-1]
        point_matrix_ids += ')'

        u_close = '.T.' if self.x_periodicity else '.F.'
        v_close = '.T.' if self.y_periodicity else '.F.'

        content += f"#{current_id} = B_SPLINE_SURFACE_WITH_KNOTS('{self.name}',{self.degree_u},{self.degree_v}," \
                   f"{point_matrix_ids},.UNSPECIFIED.,{u_close},{v_close},.F.,{tuple(self.u_multiplicities)}," \
                   f"{tuple(self.v_multiplicities)},{tuple(self.u_knots)},{tuple(self.v_knots)},.UNSPECIFIED.);\n"
        return content, [current_id]

    def grid3d(self, grid2d: grid.Grid2D):
        """
        Generate 3d grid points of a Bspline surface, based on a Grid2D.

        """

        if not self._grids2d:
            self._grids2d = grid2d

        points_2d = grid2d.points
        points_3d = [self.point2d_to_3d(point2d) for point2d in points_2d]

        return points_3d

    def grid2d_deformed(self, grid2d: grid.Grid2D):
        """
        Dimension and deform a Grid2D points based on a Bspline surface.

        """

        points_2d = grid2d.points
        points_3d = self.grid3d(grid2d)

        points_x, points_y = grid2d.points_xy

        # Parameters
        index_x = {}  # grid point position(i,j), x coordinates position in X(unknown variable)
        index_y = {}  # grid point position(i,j), y coordinates position in X(unknown variable)
        index_points = {}  # grid point position(j,i), point position in points_2d (or points_3d)
        k_index, p_index = 0, 0
        for i in range(0, points_x):
            for j in range(0, points_y):
                index_x.update({(j, i): k_index})
                index_y.update({(j, i): k_index + 1})
                index_points.update({(j, i): p_index})
                k_index = k_index + 2
                p_index = p_index + 1

        equation_points = []  # points combination to compute distances between 2D and 3D grid points
        for i in range(0, points_y):  # row from (0,i)
            for j in range(1, points_x):
                equation_points.append(((0, i), (j, i)))
        for i in range(0, points_x):  # column from (i,0)
            for j in range(1, points_y):
                equation_points.append(((i, 0), (i, j)))
        for i in range(0, points_y):  # row
            for j in range(0, points_x - 1):
                equation_points.append(((j, i), (j + 1, i)))
        for i in range(0, points_x):  # column
            for j in range(0, points_x - 1):
                equation_points.append(((i, j), (i, j + 1)))
        for i in range(0, points_y - 1):  # diagonal
            for j in range(0, points_x - 1):
                equation_points.append(((j, i), (j + 1, i + 1)))

        for i in range(0, points_y):  # row 2segments (before.point.after)
            for j in range(1, points_x - 1):
                equation_points.append(((j - 1, i), (j + 1, i)))

        for i in range(0, points_x):  # column 2segments (before.point.after)
            for j in range(1, points_y - 1):
                equation_points.append(((i, j - 1), (i, j + 1)))

        # geodesic distances between 3D grid points (based on points combination [equation_points])
        geodesic_distances = []
        for point in equation_points:
            geodesic_distances.append((self.geodesic_distance(
                points_3d[index_points[point[0]]], points_3d[index_points[point[1]]])) ** 2)

        # System of nonlinear equations
        def non_linear_equations(xparam):
            vector_f = np.empty(len(equation_points) + 2)
            idx = 0
            for idx, point_ in enumerate(equation_points):
                vector_f[idx] = abs((xparam[index_x[point_[0]]] ** 2 +
                                     xparam[index_x[point_[1]]] ** 2 +
                                     xparam[index_y[point_[0]]] ** 2 +
                                     xparam[index_y[point_[1]]] ** 2 -
                                     2 *
                                     xparam[index_x[point_[0]]] *
                                     xparam[index_x[point_[1]]] -
                                     2 *
                                     xparam[index_y[point_[0]]] *
                                     xparam[index_y[point_[1]]] -
                                     geodesic_distances[idx]) /
                                    geodesic_distances[idx])

            vector_f[idx + 1] = xparam[0] * 1000
            vector_f[idx + 2] = xparam[1] * 1000

            return vector_f

        # Solution with "least_squares"
        x_init = []  # initial guess (2D grid points)
        for point in points_2d:
            x_init.append(point[0])
            x_init.append(point[1])
        z = least_squares(non_linear_equations, x_init)

        points_2d_deformed = [design3d.Point2D(z.x[i], z.x[i + 1])
                              for i in range(0, len(z.x), 2)]  # deformed 2d grid points

        grid2d_deformed = grid.Grid2D.from_points(points=points_2d_deformed,
                                                  points_dim_1=points_x,
                                                  direction=grid2d.direction)

        self._grids2d_deformed = grid2d_deformed

        return points_2d_deformed

    def grid2d_deformation(self, grid2d: grid.Grid2D):
        """
        Compute the deformation/displacement (dx/dy) of a Grid2D based on a Bspline surface.

        """

        if not self._grids2d_deformed:
            self.grid2d_deformed(grid2d)

        displacement = self._grids2d_deformed.displacement_compared_to(grid2d)
        self._displacements = displacement

        return displacement

    def point2d_parametric_to_dimension(self, point2d: design3d.Point3D, grid2d: grid.Grid2D):
        """
        Convert a point 2d from the parametric to the dimensioned frame.

        """

        # Check if the 0<point2d.x<1 and 0<point2d.y<1
        if point2d.x < 0:
            point2d.x = 0
        elif point2d.x > 1:
            point2d.x = 1
        if point2d.y < 0:
            point2d.y = 0
        elif point2d.y > 1:
            point2d.y = 1

        if self._grids2d == grid2d:
            points_2d = self._grids2d.points
        else:
            points_2d = grid2d.points
            self._grids2d = grid2d

        if self._displacements is not None:
            displacement = self._displacements
        else:
            displacement = self.grid2d_deformation(grid2d)

        points_x, points_y = grid2d.points_xy

        # Parameters
        index_points = {}  # grid point position(j,i), point position in points_2d (or points_3d)
        p_index = 0
        for i in range(0, points_x):
            for j in range(0, points_y):
                index_points.update({(j, i): p_index})
                p_index = p_index + 1

        # Form function "Finite Elements"
        def form_function(s_param, t_param):
            empty_n = np.empty(4)
            empty_n[0] = (1 - s_param) * (1 - t_param) / 4
            empty_n[1] = (1 + s_param) * (1 - t_param) / 4
            empty_n[2] = (1 + s_param) * (1 + t_param) / 4
            empty_n[3] = (1 - s_param) * (1 + t_param) / 4
            return empty_n

        finite_elements_points = []  # 2D grid points index that define one element
        for j in range(0, points_y - 1):
            for i in range(0, points_x - 1):
                finite_elements_points.append(((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)))
        finite_elements = []  # finite elements defined with closed polygon
        for point in finite_elements_points:
            finite_elements.append(
                wires.ClosedPolygon2D([points_2d[index_points[point[0]]],
                                       points_2d[index_points[point[1]]],
                                       points_2d[index_points[point[2]]],
                                       points_2d[index_points[point[3]]]]))
        k = 0
        for k, point in enumerate(finite_elements_points):
            if (wires.Contour2D(finite_elements[k].primitives).point_inside(point2d)
                    or wires.Contour2D(finite_elements[k].primitives).point_belongs(point2d)
                    or ((points_2d[index_points[point[0]]][0] < point2d.x <
                         points_2d[index_points[point[1]]][0])
                        and point2d.y == points_2d[index_points[point[0]]][1])
                    or ((points_2d[index_points[point[1]]][1] < point2d.y <
                         points_2d[index_points[point[2]]][1])
                        and point2d.x == points_2d[index_points[point[1]]][0])
                    or ((points_2d[index_points[point[3]]][0] < point2d.x <
                         points_2d[index_points[point[2]]][0])
                        and point2d.y == points_2d[index_points[point[1]]][1])
                    or ((points_2d[index_points[point[0]]][1] < point2d.y <
                         points_2d[index_points[point[3]]][1])
                        and point2d.x == points_2d[index_points[point[0]]][0])):
                break

        x0 = points_2d[index_points[finite_elements_points[k][0]]][0]
        y0 = points_2d[index_points[finite_elements_points[k][0]]][1]
        x1 = points_2d[index_points[finite_elements_points[k][1]]][0]
        y2 = points_2d[index_points[finite_elements_points[k][2]]][1]
        x = point2d.x
        y = point2d.y
        s_param = 2 * ((x - x0) / (x1 - x0)) - 1
        t_param = 2 * ((y - y0) / (y2 - y0)) - 1

        n = form_function(s_param, t_param)
        dx = np.array([displacement[index_points[finite_elements_points[k][0]]][0],
                       displacement[index_points[finite_elements_points[k][1]]][0],
                       displacement[index_points[finite_elements_points[k][2]]][0],
                       displacement[index_points[finite_elements_points[k][3]]][0]])
        dy = np.array([displacement[index_points[finite_elements_points[k][0]]][1],
                       displacement[index_points[finite_elements_points[k][1]]][1],
                       displacement[index_points[finite_elements_points[k][2]]][1],
                       displacement[index_points[finite_elements_points[k][3]]][1]])

        return design3d.Point2D(point2d.x + np.transpose(n).dot(dx), point2d.y + np.transpose(n).dot(dy))

    def point3d_to_2d_with_dimension(self, point3d: design3d.Point3D, grid2d: grid.Grid2D):
        """
        Compute the point2d of a point3d, on a Bspline surface, in the dimensioned frame.
        """

        point2d = self.point3d_to_2d(point3d)

        point2d_with_dimension = self.point2d_parametric_to_dimension(point2d, grid2d)

        return point2d_with_dimension

    def point2d_with_dimension_to_parametric_frame(self, point2d, grid2d: grid.Grid2D):
        """
        Convert a point 2d from the dimensioned to the parametric frame.

        """

        if self._grids2d != grid2d:
            self._grids2d = grid2d
        if not self._grids2d_deformed:
            self.grid2d_deformed(grid2d)

        points_2d = grid2d.points
        points_2d_deformed = self._grids2d_deformed.points
        points_x, points_y = grid2d.points_xy

        # Parameters
        index_points = {}  # grid point position(j,i), point position in points_2d (or points_3d)
        p_index = 0
        for i in range(0, points_x):
            for j in range(0, points_y):
                index_points.update({(j, i): p_index})
                p_index = p_index + 1

        finite_elements_points = []  # 2D grid points index that define one element
        for j in range(0, points_y - 1):
            for i in range(0, points_x - 1):
                finite_elements_points.append(((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)))
        finite_elements = []  # finite elements defined with closed polygon  DEFORMED
        for point in finite_elements_points:
            finite_elements.append(
                wires.ClosedPolygon2D((points_2d_deformed[index_points[point[0]]],
                                       points_2d_deformed[index_points[point[1]]],
                                       points_2d_deformed[index_points[point[2]]],
                                       points_2d_deformed[index_points[point[3]]])))

        finite_elements_initial = []  # finite elements defined with closed polygon  INITIAL
        for point in finite_elements_points:
            finite_elements_initial.append(
                wires.ClosedPolygon2D((points_2d[index_points[point[0]]],
                                       points_2d[index_points[point[1]]],
                                       points_2d[index_points[point[2]]],
                                       points_2d[index_points[point[3]]])))
        k = 0
        for k, point in enumerate(finite_elements_points):
            if (finite_elements[k].point_belongs(point2d)
                    or ((points_2d_deformed[index_points[point[0]]][0] < point2d.x <
                         points_2d_deformed[index_points[point[1]]][0])
                        and point2d.y == points_2d_deformed[index_points[point[0]]][1])
                    or ((points_2d_deformed[index_points[finite_elements_points[k][1]]][1] < point2d.y <
                         points_2d_deformed[index_points[finite_elements_points[k][2]]][1])
                        and point2d.x == points_2d_deformed[index_points[point[1]]][0])
                    or ((points_2d_deformed[index_points[point[3]]][0] < point2d.x <
                         points_2d_deformed[index_points[point[2]]][0])
                        and point2d.y == points_2d_deformed[index_points[point[1]]][1])
                    or ((points_2d_deformed[index_points[point[0]]][1] < point2d.y <
                         points_2d_deformed[index_points[point[3]]][1])
                        and point2d.x == points_2d_deformed[index_points[point[0]]][0])
                    or finite_elements[k].primitives[0].point_belongs(point2d) or finite_elements[k].primitives[
                        1].point_belongs(point2d)
                    or finite_elements[k].primitives[2].point_belongs(point2d) or finite_elements[k].primitives[
                        3].point_belongs(point2d)):
                break

        frame_deformed = design3d.Frame2D(
            finite_elements[k].center_of_mass(),
            design3d.Vector2D(finite_elements[k].primitives[1].middle_point()[0] -
                             finite_elements[k].center_of_mass()[0],
                             finite_elements[k].primitives[1].middle_point()[1] -
                             finite_elements[k].center_of_mass()[1]),
            design3d.Vector2D(finite_elements[k].primitives[0].middle_point()[0] -
                             finite_elements[k].center_of_mass()[0],
                             finite_elements[k].primitives[0].middle_point()[1] -
                             finite_elements[k].center_of_mass()[1]))

        point2d_frame_deformed = design3d.Point2D(point2d.frame_mapping(frame_deformed, 'new')[0],
                                                 point2d.frame_mapping(frame_deformed, 'new')[1])

        frame_inital = design3d.Frame2D(
            finite_elements_initial[k].center_of_mass(),
            design3d.Vector2D(finite_elements_initial[k].primitives[1].middle_point()[0] -
                             finite_elements_initial[k].center_of_mass()[0],
                             finite_elements_initial[k].primitives[1].middle_point()[1] -
                             finite_elements_initial[k].center_of_mass()[1]),
            design3d.Vector2D(finite_elements_initial[k].primitives[0].middle_point()[0] -
                             finite_elements_initial[k].center_of_mass()[0],
                             finite_elements_initial[k].primitives[0].middle_point()[1] -
                             finite_elements_initial[k].center_of_mass()[1]))

        point2d = point2d_frame_deformed.frame_mapping(frame_inital, 'old')
        if point2d.x < 0:
            point2d.x = 0
        elif point2d.x > 1:
            point2d.x = 1
        if point2d.y < 0:
            point2d.y = 0
        elif point2d.y > 1:
            point2d.y = 1

        return point2d

    def point2d_with_dimension_to_3d(self, point2d, grid2d: grid.Grid2D):
        """
        Compute the point 3d, on a Bspline surface, of a point 2d define in the dimensioned frame.

        """

        point2d_01 = self.point2d_with_dimension_to_parametric_frame(point2d, grid2d)

        return self.point2d_to_3d(point2d_01)

    def linesegment2d_parametric_to_dimension(self, linesegment2d, grid2d: grid.Grid2D):
        """
        Convert a linesegment2d from the parametric to the dimensioned frame.

        """

        points = linesegment2d.discretization_points(number_points=20)
        points_dim = [
            self.point2d_parametric_to_dimension(
                point, grid2d) for point in points]

        return edges.BSplineCurve2D.from_points_interpolation(
            points_dim, max(self.degree_u, self.degree_v))

    def linesegment3d_to_2d_with_dimension(self, linesegment3d, grid2d: grid.Grid2D):
        """
        Compute the linesegment2d of a linesegment3d, on a Bspline surface, in the dimensioned frame.

        """

        linesegment2d = self.linesegment3d_to_2d(linesegment3d)
        bsplinecurve2d_with_dimension = self.linesegment2d_parametric_to_dimension(linesegment2d, grid2d)

        return bsplinecurve2d_with_dimension

    def linesegment2d_with_dimension_to_parametric_frame(self, linesegment2d):
        """
        Convert a linesegment2d from the dimensioned to the parametric frame.

        """

        try:
            linesegment2d = edges.LineSegment2D(
                self.point2d_with_dimension_to_parametric_frame(linesegment2d.start, self._grids2d),
                self.point2d_with_dimension_to_parametric_frame(linesegment2d.end, self._grids2d))
        except NotImplementedError:
            return None

        return linesegment2d

    def linesegment2d_with_dimension_to_3d(self, linesegment2d):
        """
        Compute the linesegment3d, on a Bspline surface, of a linesegment2d defined in the dimensioned frame.

        """

        linesegment2d_01 = self.linesegment2d_with_dimension_to_parametric_frame(linesegment2d)
        linesegment3d = self.linesegment2d_to_3d(linesegment2d_01)

        return linesegment3d

    def bsplinecurve2d_parametric_to_dimension(self, bsplinecurve2d, grid2d: grid.Grid2D):
        """
        Convert a bsplinecurve2d from the parametric to the dimensioned frame.

        """

        # check if bsplinecurve2d is in a list
        if isinstance(bsplinecurve2d, list):
            bsplinecurve2d = bsplinecurve2d[0]
        points = bsplinecurve2d.control_points
        points_dim = []

        for point in points:
            points_dim.append(self.point2d_parametric_to_dimension(point, grid2d))

        bsplinecurve2d_with_dimension = edges.BSplineCurve2D(bsplinecurve2d.degree, points_dim,
                                                             bsplinecurve2d.knot_multiplicities,
                                                             bsplinecurve2d.knots,
                                                             bsplinecurve2d.weights,
                                                             bsplinecurve2d.periodic)

        return bsplinecurve2d_with_dimension

    def bsplinecurve3d_to_2d_with_dimension(self, bsplinecurve3d, grid2d: grid.Grid2D):
        """
        Compute the bsplinecurve2d of a bsplinecurve3d, on a Bspline surface, in the dimensioned frame.

        """

        bsplinecurve2d_01 = self.bsplinecurve3d_to_2d(bsplinecurve3d)
        bsplinecurve2d_with_dimension = self.bsplinecurve2d_parametric_to_dimension(
            bsplinecurve2d_01, grid2d)

        return bsplinecurve2d_with_dimension

    def bsplinecurve2d_with_dimension_to_parametric_frame(self, bsplinecurve2d):
        """
        Convert a bsplinecurve2d from the dimensioned to the parametric frame.

        """

        points_dim = bsplinecurve2d.control_points
        points = []
        for point in points_dim:
            points.append(
                self.point2d_with_dimension_to_parametric_frame(point, self._grids2d))

        bsplinecurve2d = edges.BSplineCurve2D(bsplinecurve2d.degree, points,
                                              bsplinecurve2d.knot_multiplicities,
                                              bsplinecurve2d.knots,
                                              bsplinecurve2d.weights,
                                              bsplinecurve2d.periodic)
        return bsplinecurve2d

    def bsplinecurve2d_with_dimension_to_3d(self, bsplinecurve2d):
        """
        Compute the bsplinecurve3d, on a Bspline surface, of a bsplinecurve2d defined in the dimensioned frame.

        """

        bsplinecurve2d_01 = self.bsplinecurve2d_with_dimension_to_parametric_frame(bsplinecurve2d)
        bsplinecurve3d = self.bsplinecurve2d_to_3d(bsplinecurve2d_01)

        return bsplinecurve3d

    def arc2d_parametric_to_dimension(self, arc2d, grid2d: grid.Grid2D):
        """
        Convert an arc 2d from the parametric to the dimensioned frame.

        """

        number_points = math.ceil(arc2d.angle * 7) + 1
        length = arc2d.length()
        points = [self.point2d_parametric_to_dimension(arc2d.point_at_abscissa(
            i * length / (number_points - 1)), grid2d) for i in range(number_points)]

        return edges.BSplineCurve2D.from_points_interpolation(
            points, max(self.degree_u, self.degree_v))

    def arc3d_to_2d_with_dimension(self, arc3d, grid2d: grid.Grid2D):
        """
        Compute the arc 2d of an arc 3d, on a Bspline surface, in the dimensioned frame.

        """

        bsplinecurve2d = self.arc3d_to_2d(arc3d)[0]  # it's a bsplinecurve2d
        arc2d_with_dimension = self.bsplinecurve2d_parametric_to_dimension(bsplinecurve2d, grid2d)

        return arc2d_with_dimension  # it's a bsplinecurve2d-dimension

    def arc2d_with_dimension_to_parametric_frame(self, arc2d):
        """
        Convert an arc 2d from the dimensioned to the parametric frame.

        """

        number_points = math.ceil(arc2d.angle * 7) + 1
        length = arc2d.length()

        points = [self.point2d_with_dimension_to_parametric_frame(arc2d.point_at_abscissa(
            i * length / (number_points - 1)), self._grids2d) for i in range(number_points)]

        return edges.BSplineCurve2D.from_points_interpolation(points, max(self.degree_u, self.degree_v))

    def arc2d_with_dimension_to_3d(self, arc2d):
        """
        Compute the arc 3d, on a Bspline surface, of an arc 2d in the dimensioned frame.

        """

        arc2d_01 = self.arc2d_with_dimension_to_parametric_frame(arc2d)
        arc3d = self.arc2d_to_3d(arc2d_01)

        return arc3d  # it's a bsplinecurve3d

    def contour2d_parametric_to_dimension(self, contour2d: wires.Contour2D,
                                          grid2d: grid.Grid2D):
        """
        Convert a contour 2d from the parametric to the dimensioned frame.

        """

        primitives2d_dim = []

        for primitive2d in contour2d.primitives:
            method_name = f'{primitive2d.__class__.__name__.lower()}_parametric_to_dimension'

            if hasattr(self, method_name):
                primitives = getattr(self, method_name)(primitive2d, grid2d)
                if primitives:
                    primitives2d_dim.append(primitives)

            else:
                raise NotImplementedError(
                    f'Class {self.__class__.__name__} does not implement {method_name}')

        return wires.Contour2D(primitives2d_dim)

    def contour3d_to_2d_with_dimension(self, contour3d: wires.Contour3D,
                                       grid2d: grid.Grid2D):
        """
        Compute the Contour 2d of a Contour 3d, on a Bspline surface, in the dimensioned frame.

        """

        contour2d_01 = self.contour3d_to_2d(contour3d)

        return self.contour2d_parametric_to_dimension(contour2d_01, grid2d)

    def contour2d_with_dimension_to_parametric_frame(self, contour2d):
        """
        Convert a contour 2d from the dimensioned to the parametric frame.

        """

        # TODO: check and avoid primitives with start=end
        primitives2d = []

        for primitive2d in contour2d.primitives:
            method_name = f'{primitive2d.__class__.__name__.lower()}_with_dimension_to_parametric_frame'

            if hasattr(self, method_name):
                primitives = getattr(self, method_name)(primitive2d)
                if primitives:
                    primitives2d.append(primitives)

            else:
                raise NotImplementedError(
                    f'Class {self.__class__.__name__} does not implement {method_name}')

        # #Avoid to have primitives with start=end
        # start_points = []
        # for i in range(0, len(new_start_points)-1):
        #     if new_start_points[i] != new_start_points[i+1]:
        #         start_points.append(new_start_points[i])
        # if new_start_points[-1] != new_start_points[0]:
        #     start_points.append(new_start_points[-1])

        return wires.Contour2D(primitives2d)

    def contour2d_with_dimension_to_3d(self, contour2d):
        """
        Compute the contour3d, on a Bspline surface, of a contour2d define in the dimensioned frame.

        """

        contour01 = self.contour2d_with_dimension_to_parametric_frame(contour2d)

        return self.contour2d_to_3d(contour01)

    @classmethod
    def from_geomdl_surface(cls, surface, name: str = ""):
        """
        Create a design3d BSpline_Surface3D from a geomdl's one.

        """

        control_points = []
        for point in surface.ctrlpts:
            control_points.append(design3d.Point3D(point[0], point[1], point[2]))

        (u_knots, u_multiplicities) = knots_vector_inv(surface.knotvector_u)
        (v_knots, v_multiplicities) = knots_vector_inv(surface.knotvector_v)

        bspline_surface = cls(degree_u=surface.degree_u,
                              degree_v=surface.degree_v,
                              control_points=control_points,
                              nb_u=surface.ctrlpts_size_u,
                              nb_v=surface.ctrlpts_size_v,
                              u_multiplicities=u_multiplicities,
                              v_multiplicities=v_multiplicities,
                              u_knots=u_knots,
                              v_knots=v_knots, weights=surface.weights, name=name)
        return bspline_surface

    @classmethod
    def points_fitting_into_bspline_surface(cls, points_3d, size_u, size_v, degree_u, degree_v, name: str = ""):
        """
        Bspline Surface interpolation through 3d points.
        """
        warnings.warn("points_fitting_into_bspline_surface is deprecated. Use from_points_interpolation instead")
        return cls.from_points_interpolation(points_3d, size_u, size_v, degree_u, degree_v, name)

    @classmethod
    def from_points_interpolation(cls, points_3d: List[design3d.Point3D], size_u: int, size_v: int,
                                  degree_u: int, degree_v: int, name: str = ""):
        """
        Bspline Surface interpolation through 3d points.

        :param points_3d: data points.
        :type points_3d: List[design3d.Point3D]
        :param size_u: number of data points on the u-direction.
        :type size_u: int
        :param size_v: number of data points on the v-direction.
        :type size_v: int
        :param degree_u: degree of the output surface for the u-direction.
        :type degree_u: int
        :param degree_v: degree of the output surface for the v-direction.
        :type degree_v: int
        :param name: (Optional) instance name.
        :type name: str
        :return: B-spline surface.
        :rtype: BSplineSurface3D
        """
        points = np.asarray(points_3d)

        ctrlpts, knots_u, knot_multiplicities_u, knots_v, knot_multiplicities_v = \
            interpolate_surface(points, size_u, size_v, degree_u, degree_v)
        ctrlpts = [design3d.Point3D(*point) for point in ctrlpts]
        return cls(degree_u, degree_v, ctrlpts, size_u, size_v, knot_multiplicities_u, knot_multiplicities_v, knots_u,
                   knots_v, name=name)

    @classmethod
    def points_approximate_into_bspline_surface(cls, points_3d, size_u, size_v, degree_u, degree_v,
                                                name: str = "", **kwargs):
        """
        Bspline Surface approximate through 3d points.
        """
        warnings.warn("points_approximate_into_bspline_surface is deprecated. Use from_points_approximation instead")
        return cls.from_points_approximation(points_3d, size_u, size_v, degree_u, degree_v, name, **kwargs)

    @classmethod
    def from_points_approximation(cls, points_3d: List[design3d.Point3D], size_u: int, size_v: int, degree_u: int,
                                  degree_v: int, name: str = "", **kwargs):
        """
        Bspline Surface approximate through 3d points.

        :param points_3d: data points.
        :type points_3d: List[design3d.Point3D]
        :param size_u: number of data points on the u-direction.
        :type size_u: int
        :param size_v: number of data points on the v-direction.
        :type size_v: int
        :param degree_u: degree of the output surface for the u-direction.
        :type degree_u: int
        :param degree_v: degree of the output surface for the v-direction.
        :type degree_v: int
        :param name: (Optional) instance name.
        :type name: str

        Keyword Arguments:
            * ``ctrlpts_size_u``: number of control points on the u-direction. *Default: size_u - 1*
            * ``ctrlpts_size_v``: number of control points on the v-direction. *Default: size_v - 1*

        :return: B-spline surface.
        :rtype: BSplineSurface3D

        """

        # Keyword arguments
        # number of data points, r + 1 > number of control points, n + 1
        num_cpts_u = kwargs.get('ctrlpts_size_u', size_u - 1)
        # number of data points, s + 1 > number of control points, m + 1
        num_cpts_v = kwargs.get('ctrlpts_size_v', size_v - 1)

        points = np.asarray(points_3d)

        ctrlpts, knots_u, knot_multiplicities_u, knots_v, knot_multiplicities_v = \
            approximate_surface(points, size_u, size_v, degree_u, degree_v,
                                ctrlpts_size_u=num_cpts_u, ctrlpts_size_v=num_cpts_v)

        ctrlpts = [design3d.Point3D(*point) for point in ctrlpts]
        return cls(degree_u, degree_v, ctrlpts, size_u, size_v, knot_multiplicities_u, knot_multiplicities_v, knots_u,
                   knots_v, name=name)

    @classmethod
    def _from_cylindrical_faces_x_direction(cls, cylindrical_faces, degree_u, degree_v,
                                            points_x: int = 10, points_y: int = 10, name: str = ''):
        """
        Define an x direction bspline surface from a list of cylindrical faces.

        Parameters
        ----------
        cylindrical_faces : List[design3d.faces.CylindricalFace3D]
            faces 3d
        degree_u : int
            degree of the output surface for the u-direction
        degree_v : int
            degree of the output surface for the v-direction
        points_x : int
            number of points in x-direction
        points_y : int
            number of points in y-direction
        name: str
            object's name.

        Returns
        -------
        B-spline surface

        """
        bspline_surfaces = []
        bounding_rectangle_0 = cylindrical_faces[0].surface2d.outer_contour.bounding_rectangle
        ymin = bounding_rectangle_0[2]
        ymax = bounding_rectangle_0[3]
        for face in cylindrical_faces:
            bounding_rectangle = face.surface2d.outer_contour.bounding_rectangle
            ymin = min(ymin, bounding_rectangle[2])
            ymax = max(ymax, bounding_rectangle[3])
        for face in cylindrical_faces:
            bounding_rectangle = face.surface2d.outer_contour.bounding_rectangle

            points_3d = face.surface3d.grid3d(
                grid.Grid2D.from_properties(
                    x_limits=(bounding_rectangle[0], bounding_rectangle[1]),
                    y_limits=(ymin, ymax),
                    points_nbr=(points_x, points_y)))

            bspline_surfaces.append(
                cls.points_fitting_into_bspline_surface(
                    points_3d, points_x, points_y, degree_u, degree_v, name))
        return bspline_surfaces

    @classmethod
    def _from_cylindrical_faces_y_direction(cls, cylindrical_faces, degree_u, degree_v,
                                            points_x: int = 10, points_y: int = 10, name: str = ''):
        """
        Define a y direction bspline surface from a list of cylindrical faces.

        Parameters
        ----------
        cylindrical_faces : List[design3d.faces.CylindricalFace3D]
            faces 3d
        degree_u : int
            degree of the output surface for the u-direction
        degree_v : int
            degree of the output surface for the v-direction
        points_x : int
            number of points in x-direction
        points_y : int
            number of points in y-direction
        name: str
            object's name.

        Returns
        -------
        B-spline surface

        """
        bspline_surfaces = []
        bounding_rectangle_0 = cylindrical_faces[0].surface2d.outer_contour.bounding_rectangle
        xmin = bounding_rectangle_0[0]
        xmax = bounding_rectangle_0[1]
        for face in cylindrical_faces:
            bounding_rectangle = face.surface2d.outer_contour.bounding_rectangle
            xmin = min(xmin, bounding_rectangle[0])
            xmax = max(xmax, bounding_rectangle[1])
        for face in cylindrical_faces:
            bounding_rectangle = face.surface2d.outer_contour.bounding_rectangle

            points_3d = face.surface3d.grid3d(
                grid.Grid2D.from_properties(
                    x_limits=(xmin, xmax),
                    y_limits=(bounding_rectangle[2], bounding_rectangle[3]),
                    points_nbr=(points_x, points_y)))

            bspline_surfaces.append(
                cls.points_fitting_into_bspline_surface(
                    points_3d, points_x, points_y, degree_u, degree_v, name))
        return bspline_surfaces

    @classmethod
    def from_cylindrical_faces(cls, cylindrical_faces, degree_u, degree_v,
                               points_x: int = 10, points_y: int = 10, name: str = ''):
        """
        Define a bspline surface from a list of cylindrical faces.

        Parameters
        ----------
        cylindrical_faces : List[design3d.faces.CylindricalFace3D]
            faces 3d
        degree_u : int
            degree of the output surface for the u-direction
        degree_v : int
            degree of the output surface for the v-direction
        points_x : int
            number of points in x-direction
        points_y : int
            number of points in y-direction
        name: str
            object's name.

        Returns
        -------
        B-spline surface

        """
        if len(cylindrical_faces) < 1:
            raise NotImplementedError
        if len(cylindrical_faces) == 1:
            return cls.from_cylindrical_face(cylindrical_faces[0], degree_u, degree_v, points_x=50, points_y=50)
        bspline_surfaces = []
        direction = cylindrical_faces[0].adjacent_direction(cylindrical_faces[1])

        if direction == 'x':
            bspline_surfaces.extend(cls._from_cylindrical_faces_x_direction(
                cylindrical_faces, degree_u, degree_v, points_x, points_y, name))

        elif direction == 'y':
            bspline_surfaces.extend(cls._from_cylindrical_faces_y_direction(
                cylindrical_faces, degree_u, degree_v, points_x, points_y, name
            ))

        to_be_merged = bspline_surfaces[0]
        for i in range(0, len(bspline_surfaces) - 1):
            merged = to_be_merged.merge_with(bspline_surfaces[i + 1])
            to_be_merged = merged

        bspline_surface = to_be_merged
        bspline_surface.name = name
        return bspline_surface

    @classmethod
    def from_cylindrical_face(cls, cylindrical_face, degree_u, degree_v, name: str = '',
                              **kwargs):  # points_x: int = 50, points_y: int = 50
        """
        Define a bspline surface from a cylindrical face.

        Parameters
        ----------
        cylindrical_face : design3d.faces.CylindricalFace3D
            face 3d
        degree_u : int
            degree of the output surface for the u-direction.
        degree_v : int
            degree of the output surface for the v-direction.
        points_x : int
            number of points in x-direction
        points_y : int
            number of points in y-direction
        name: str
            object's name.

        Returns
        -------
        B-spline surface

        """

        points_x = kwargs['points_x']
        points_y = kwargs['points_y']
        bounding_rectangle = cylindrical_face.surface2d.outer_contour.bounding_rectangle
        points_3d = cylindrical_face.surface3d.grid3d(
            grid.Grid2D.from_properties(x_limits=(bounding_rectangle[0],
                                                  bounding_rectangle[1]),
                                        y_limits=(bounding_rectangle[2],
                                                  bounding_rectangle[3]),
                                        points_nbr=(points_x, points_y)))

        return cls.points_fitting_into_bspline_surface(points_3d, points_x, points_x, degree_u, degree_v, name=name)

    def intersection_with(self, other_bspline_surface3d):
        """
        Compute intersection points between two Bspline surfaces.

        return u,v parameters for intersection points for both surfaces
        """

        def fun(param):
            return (self.point2d_to_3d(design3d.Point2D(param[0], param[1])) -
                    other_bspline_surface3d.point2d_to_3d(design3d.Point2D(param[2], param[3]))).norm()

        x = np.linspace(0, 1, 10)
        x_init = []
        for xi in x:
            for yi in x:
                x_init.append((xi, yi, xi, yi))

        u1, v1, u2, v2 = [], [], [], []
        solutions = []
        for x0 in x_init:
            z = least_squares(fun, x0=x0, bounds=([0, 1]))
            if z.fun < 1e-5:
                solution = z.x
                if solution not in solutions:
                    solutions.append(solution)
                    u1.append(solution[0])
                    v1.append(solution[1])
                    u2.append(solution[2])
                    v2.append(solution[3])

        # uv1 = [[min(u1),max(u1)],[min(v1),max(v1)]]
        # uv2 = [[min(u2),max(u2)],[min(v2),max(v2)]]

        return (u1, v1), (u2, v2)  # (uv1, uv2)

    def plane_intersections(self, plane3d):
        """
        Compute intersection points between a Bspline surface and a plane 3d.
        """
        a, b, c, d = plane3d.equation_coefficients()

        def fun(param):
            point3d = self.point2d_to_3d(design3d.Point2D(*param))
            return point3d[0] * a + point3d[1] * b + point3d[2] * c + d

        x = np.linspace(0, 1, 20)
        x_init = []
        for xi in x:
            for yi in x:
                x_init.append((xi, yi))

        intersection_points = []

        for x0 in x_init:
            z = least_squares(fun, x0=np.array(x0), bounds=([0, 1]))
            if abs(z.fun) < 1e-8:
                solution = z.x
                intersection_points.append(self.point2d_to_3d(design3d.Point2D(*solution)))
        return intersection_points

    def error_with_point3d(self, point3d):
        """
        Compute the error/distance between the Bspline surface and a point 3d.

        """

        def fun(x):
            return (point3d - self.point2d_to_3d(design3d.Point2D(x[0], x[1]))).norm()

        cost = []

        for x0 in [(0, 0), (0, 1), (1, 0), (1, 1), (0.5, 0.5)]:
            z = least_squares(fun, x0=x0, bounds=([0, 1]))
            cost.append(z.fun)

        return min(cost)

    def error_with_edge3d(self, edge3d):
        """
        Compute the error/distance between the Bspline surface and an edge 3d.

        it's the mean of the start and end points errors'
        """

        return (self.error_with_point3d(edge3d.start) + self.error_with_point3d(edge3d.end)) / 2

    def nearest_edges3d(self, contour3d, threshold: float):
        """
        Compute the nearest edges of a contour 3d to a Bspline_surface3d based on a threshold.

        """

        nearest = []
        for primitive in contour3d.primitives:
            if self.error_with_edge3d(primitive) <= threshold:
                nearest.append(primitive)
        nearest_primitives = wires.Wire3D(nearest)

        return nearest_primitives

    def edge3d_to_2d_with_dimension(self, edge3d, grid2d: grid.Grid2D):
        """
        Compute the edge 2d of an edge 3d, on a Bspline surface, in the dimensioned frame.

        """
        method_name = f'{edge3d.__class__.__name__.lower()}_to_2d_with_dimension'

        if hasattr(self, method_name):
            edge2d_dim = getattr(self, method_name)(edge3d, grid2d)
            if edge2d_dim:
                return edge2d_dim
            raise NotImplementedError
        raise NotImplementedError(
            f'Class {self.__class__.__name__} does not implement {method_name}')

    def wire3d_to_2d(self, wire3d):
        """
        Compute the 2d of a wire 3d, on a Bspline surface.

        """

        contour = self.contour3d_to_2d(wire3d)

        return wires.Wire2D(contour.primitives)

    def wire3d_to_2d_with_dimension(self, wire3d):
        """
        Compute the 2d of a wire 3d, on a Bspline surface, in the dimensioned frame.

        """

        contour = self.contour3d_to_2d_with_dimension(wire3d, self._grids2d)

        return wires.Wire2D(contour.primitives)

    def split_surface_u(self, u: float):
        """
        Splits the surface at the input parametric coordinate on the u-direction.

        :param u: Parametric coordinate u chosen between 0 and 1
        :type u: float
        :return: Two split surfaces
        :rtype: List[:class:`design3d.faces.BSplineSurface3D`]
        """
        return split_surface_u(self, u)

    def split_surface_v(self, v: float):
        """
        Splits the surface at the input parametric coordinate on the v-direction.

        :param v: Parametric coordinate v chosen between 0 and 1
        :type v: float
        :return: Two split surfaces
        :rtype: List[:class:`design3d.faces.BSplineSurface3D`]
        """
        return split_surface_v(self, v)

    def split_surface_with_bspline_curve(self, bspline_curve3d: edges.BSplineCurve3D):
        """
        Cuts the surface into two pieces with a bspline curve.

        :param bspline_curve3d: A BSplineCurve3d used for cutting
        :type bspline_curve3d: :class:`edges.BSplineCurve3D`
        :return: Two split surfaces
        :rtype: List[:class:`design3d.faces.BSplineSurface3D`]
        """

        surfaces = []
        bspline_curve2d = self.bsplinecurve3d_to_2d(bspline_curve3d)[0]
        # if type(bspline_curve2d) == list:
        #     points = [bspline_curve2d[0].start]
        #     for edge in bspline_curve2d:
        #         points.append(edge.end)
        #     bspline_curve2d = edges.BSplineCurve2D.from_points_approximation(points, 2, ctrlpts_size = 5)
        contour = design3d.faces.BSplineFace3D.from_surface_rectangular_cut(self, 0, 1, 0, 1).surface2d.outer_contour
        contours = contour.cut_by_bspline_curve(bspline_curve2d)

        du, dv = bspline_curve2d.end - bspline_curve2d.start
        resolution = 8

        for contour in contours:
            u_min, u_max, v_min, v_max = contour.bounding_rectangle.bounds()
            if du > dv:
                delta_u = u_max - u_min
                nlines_x = int(delta_u * resolution)
                lines_x = [curves.Line2D(design3d.Point2D(u_min, v_min),
                                         design3d.Point2D(u_min, v_max))]
                for i in range(nlines_x):
                    u = u_min + (i + 1) / (nlines_x + 1) * delta_u
                    lines_x.append(curves.Line2D(design3d.Point2D(u, v_min),
                                                 design3d.Point2D(u, v_max)))
                lines_x.append(curves.Line2D(design3d.Point2D(u_max, v_min),
                                             design3d.Point2D(u_max, v_max)))
                lines = lines_x

            else:
                delta_v = v_max - v_min
                nlines_y = int(delta_v * resolution)
                lines_y = [curves.Line2D(design3d.Point2D(v_min, v_min),
                                         design3d.Point2D(v_max, v_min))]
                for i in range(nlines_y):
                    v = v_min + (i + 1) / (nlines_y + 1) * delta_v
                    lines_y.append(curves.Line2D(design3d.Point2D(v_min, v),
                                                 design3d.Point2D(v_max, v)))
                lines_y.append(curves.Line2D(design3d.Point2D(v_min, v_max),
                                             design3d.Point2D(v_max, v_max)))
                lines = lines_y

            pt0 = design3d.O2D
            points = []

            for line in lines:
                inter = contour.line_intersections(line)
                if inter:
                    pt_ = set()
                    for point_intersection in inter:
                        pt_.add(point_intersection[0])
                else:
                    raise NotImplementedError

                pt_ = sorted(pt_, key=pt0.point_distance)
                pt0 = pt_[0]
                edge = edges.LineSegment2D(pt_[0], pt_[1])

                points.extend(edge.discretization_points(number_points=10))

            points3d = []
            for point in points:
                points3d.append(self.point2d_to_3d(point))

            size_u, size_v, degree_u, degree_v = 10, 10, self.degree_u, self.degree_v
            surfaces.append(
                BSplineSurface3D.points_fitting_into_bspline_surface(points3d, size_u, size_v, degree_u, degree_v))

        return surfaces

    def is_intersected_with(self, other_bspline_surface3d):
        """
        Check if the two surfaces are intersected or not.

        return True, when there are more 50points on the intersection zone.

        """

        def fun(param):
            return (self.point2d_to_3d(design3d.Point2D(param[0], param[1])) -
                    other_bspline_surface3d.point2d_to_3d(design3d.Point2D(param[2], param[3]))).norm()

        x = np.linspace(0, 1, 10)
        x_init = []
        for xi in x:
            for yi in x:
                x_init.append((xi, yi, xi, yi))

        i = 0
        for x0 in x_init:
            z = least_squares(fun, x0=x0, bounds=([0, 1]))
            if z.fun < 1e-5:
                i += 1
                if i >= 50:
                    return True
        return False

    def merge_with(self, other_bspline_surface3d, abs_tol: float = 1e-6):
        """
        Merges two adjacent surfaces based on their faces.

        :param other_bspline_surface3d: Other adjacent surface
        :type other_bspline_surface3d: :class:`design3d.faces.BSplineSurface3D`
        :param abs_tol: tolerance.
        :type abs_tol: float.

        :return: Merged surface
        :rtype: :class:`design3d.faces.BSplineSurface3D`
        """

        bspline_face3d = design3d.faces.BSplineFace3D.from_surface_rectangular_cut(self, 0, 1, 0, 1)
        other_bspline_face3d = design3d.faces.BSplineFace3D.from_surface_rectangular_cut(
            other_bspline_surface3d, 0, 1, 0, 1)

        bsplines = [self, other_bspline_surface3d]
        bsplines_new = bsplines

        center = [bspline_face3d.surface2d.outer_contour.center_of_mass(),
                  other_bspline_face3d.surface2d.outer_contour.center_of_mass()]
        grid2d_direction = (bspline_face3d.pair_with(other_bspline_face3d))[1]

        if (not bspline_face3d.outer_contour3d.is_sharing_primitives_with(
                other_bspline_face3d.outer_contour3d, abs_tol)
                and self.is_intersected_with(other_bspline_surface3d)):
            # find primitives to split with
            contour1 = bspline_face3d.outer_contour3d
            contour2 = other_bspline_face3d.outer_contour3d

            distances = []
            for prim1 in contour1.primitives:
                dis = []
                for prim2 in contour2.primitives:
                    point1 = (prim1.start + prim1.end) / 2
                    point2 = (prim2.start + prim2.end) / 2
                    dis.append(point1.point_distance(point2))
                distances.append(dis)

            i = distances.index((min(distances)))
            j = distances[i].index(min(distances[i]))

            curves_ = [contour2.primitives[j], contour1.primitives[i]]

            # split surface
            for i, bspline in enumerate(bsplines):
                surfaces = bspline.split_surface_with_bspline_curve(curves_[i])

                errors = []
                for surface in surfaces:
                    errors.append(surface.error_with_point3d(bsplines[i].point2d_to_3d(center[i])))

                bsplines_new[i] = surfaces[errors.index(min(errors))]

            grid2d_direction = (
                bsplines_new[0].rectangular_cut(
                    0, 1, 0, 1).pair_with(
                    bsplines_new[1].rectangular_cut(
                        0, 1, 0, 1)))[1]

        # grid3d
        number_points = 10
        points3d = []
        is_true = (bspline_face3d.outer_contour3d.is_sharing_primitives_with(
            other_bspline_face3d.outer_contour3d, abs_tol) or self.is_intersected_with(other_bspline_surface3d))

        for i, bspline in enumerate(bsplines_new):
            grid3d = bspline.grid3d(grid.Grid2D.from_properties(x_limits=(0, 1),
                                                                y_limits=(0, 1),
                                                                points_nbr=(number_points, number_points),
                                                                direction=grid2d_direction[i]))

            if is_true and i == 1:
                points3d.extend(grid3d[number_points:number_points * number_points])
            else:
                points3d.extend(grid3d)

        # fitting
        size_u, size_v, degree_u, degree_v = (number_points * 2) - 1, number_points, 3, 3

        merged_surface = BSplineSurface3D.points_fitting_into_bspline_surface(
            points3d, size_u, size_v, degree_u, degree_v)

        return merged_surface

    def xy_limits(self, other_bspline_surface3d):
        """
        Compute x, y limits to define grid2d.

        """

        grid2d_direction = (
            self.rectangular_cut(
                0, 1, 0, 1).pair_with(
                other_bspline_surface3d.rectangular_cut(
                    0, 1, 0, 1)))[1]

        xmin, xmax, ymin, ymax = [], [], [], []
        if grid2d_direction[0][1] == '+y':
            xmin.append(0)
            xmax.append(1)
            ymin.append(0)
            ymax.append(0.99)
        elif grid2d_direction[0][1] == '+x':
            xmin.append(0)
            xmax.append(0.99)
            ymin.append(0)
            ymax.append(1)
        elif grid2d_direction[0][1] == '-x':
            xmin.append(0.01)
            xmax.append(1)
            ymin.append(0)
            ymax.append(1)
        elif grid2d_direction[0][1] == '-y':
            xmin.append(0)
            xmax.append(1)
            ymin.append(0.01)
            ymax.append(1)

        xmin.append(0)
        xmax.append(1)
        ymin.append(0)
        ymax.append(1)

        return xmin, xmax, ymin, ymax

    def _determine_contour_params(self, outer_contour_start, outer_contour_end, inner_contour_start,
                                  inner_contour_end):
        """
        Helper function.
        """
        u1, v1 = outer_contour_start
        u2, v2 = outer_contour_end
        u3, v3 = inner_contour_start
        u4, v4 = inner_contour_end
        if self.x_periodicity and self.y_periodicity:
            raise NotImplementedError
        if self.x_periodicity:
            outer_contour_param = [u1, u2]
            inner_contour_param = [u3, u4]
        elif self.y_periodicity:
            outer_contour_param = [v1, v2]
            inner_contour_param = [v3, v4]
        else:
            raise NotImplementedError
        return outer_contour_param, inner_contour_param

    def connect_contours(self, outer_contour, inner_contours):
        """
        Create connections between contours on parametric domain.

        :param outer_contour: Outer contour 2D.
        :type inner_contours: wires.Contour2D
        :param inner_contours: List of 2D contours.
        :type inner_contours: list
        """
        new_inner_contours = []
        new_outer_contour = outer_contour
        point1 = outer_contour.primitives[0].start
        point2 = outer_contour.primitives[-1].end

        for inner_contour in inner_contours:
            if not inner_contour.is_ordered():
                outer_contour_param, inner_contour_param = self._determine_contour_params(
                    point1, point2, inner_contour.primitives[0].start, inner_contour.primitives[-1].end)

                outer_contour_direction = outer_contour_param[0] < outer_contour_param[1]
                inner_contour_direction = inner_contour_param[0] < inner_contour_param[1]
                if outer_contour_direction == inner_contour_direction:
                    inner_contour = inner_contour.invert()

                closing_linesegment1 = edges.LineSegment2D(outer_contour.primitives[-1].end,
                                                           inner_contour.primitives[0].start)
                closing_linesegment2 = edges.LineSegment2D(inner_contour.primitives[-1].end,
                                                           outer_contour.primitives[0].start)
                new_outer_contour_primitives = outer_contour.primitives + [closing_linesegment1] + \
                                               inner_contour.primitives + [closing_linesegment2]
                new_outer_contour = wires.Contour2D(primitives=new_outer_contour_primitives)
                new_outer_contour.order_contour(tol=1e-3)
            else:
                new_inner_contours.append(inner_contour)
        return new_outer_contour, new_inner_contours

    @staticmethod
    def _get_overlapping_theta(outer_contour_startend_theta, inner_contour_startend_theta):
        """
        Find overlapping theta domain between two contours on periodical Surfaces.
        """
        oc_xmin_index, outer_contour_xmin = min(enumerate(outer_contour_startend_theta), key=lambda x: x[1])
        oc_xmax_index, outer_contour_xman = max(enumerate(outer_contour_startend_theta), key=lambda x: x[1])
        inner_contour_xmin = min(inner_contour_startend_theta)
        inner_contour_xmax = max(inner_contour_startend_theta)

        # check if tetha3 or theta4 is in [theta1, theta2] interval
        overlap = outer_contour_xmin <= inner_contour_xmax and outer_contour_xman >= inner_contour_xmin

        if overlap:
            if inner_contour_xmin < outer_contour_xmin:
                overlapping_theta = outer_contour_startend_theta[oc_xmin_index]
                outer_contour_side = oc_xmin_index
                side = 0
                return overlapping_theta, outer_contour_side, side
            overlapping_theta = outer_contour_startend_theta[oc_xmax_index]
            outer_contour_side = oc_xmax_index
            side = 1
            return overlapping_theta, outer_contour_side, side

        # if not direct intersection -> find intersection at periodicity
        if inner_contour_xmin < outer_contour_xmin:
            overlapping_theta = outer_contour_startend_theta[oc_xmin_index] - 2 * math.pi
            outer_contour_side = oc_xmin_index
            side = 0
            return overlapping_theta, outer_contour_side, side
        overlapping_theta = outer_contour_startend_theta[oc_xmax_index] + 2 * math.pi
        outer_contour_side = oc_xmax_index
        side = 1
        return overlapping_theta, outer_contour_side, side

    def to_plane3d(self):
        """
        Converts a Bspline surface3d to a Plane3d.

        :return: A Plane
        :rtype: Plane3D
        """

        points_2d = [design3d.Point2D(0.1, 0.1),
                     design3d.Point2D(0.1, 0.8),
                     design3d.Point2D(0.8, 0.5)]
        points = [self.point2d_to_3d(pt) for pt in points_2d]

        surface3d = Plane3D.from_3_points(points[0],
                                          points[1],
                                          points[2])
        return surface3d

    def u_closed_lower(self, tol: float = 1e-6):
        """
        Returns True if the surface is close in any of the u boundaries.
        """
        a, b, c, _ = self.domain
        point_at_a_lower = self.point2d_to_3d(design3d.Point2D(a, c))
        point_at_b_lower = self.point2d_to_3d(design3d.Point2D(0.5 * (a + b), c))
        if point_at_b_lower.is_close(point_at_a_lower, tol):
            return True
        return False

    def u_closed_upper(self, tol: float = 1e-6):
        """
        Returns True if the surface is close in any of the u boundaries.
        """
        a, b, _, d = self.domain
        point_at_a_upper = self.point2d_to_3d(design3d.Point2D(a, d))
        point_at_b_upper = self.point2d_to_3d(design3d.Point2D(0.5 * (a + b), d))
        if point_at_b_upper.is_close(point_at_a_upper, tol):
            return True
        return False

    def v_closed_lower(self, tol: float = 1e-6):
        """
        Returns True if the surface is close in any of the u boundaries.
        """
        a, _, c, d = self.domain
        point_at_c_lower = self.point2d_to_3d(design3d.Point2D(a, c))
        point_at_d_lower = self.point2d_to_3d(design3d.Point2D(a, 0.5 * (c + d)))
        if point_at_d_lower.is_close(point_at_c_lower, tol):
            return True
        return False

    def v_closed_upper(self, tol: float = 1e-6):
        """
        Returns True if the surface is close in any of the u boundaries.
        """
        _, b, c, d = self.domain
        point_at_c_upper = self.point2d_to_3d(design3d.Point2D(b, c))
        point_at_d_upper = self.point2d_to_3d(design3d.Point2D(b, 0.5 * (c + d)))
        if point_at_d_upper.is_close(point_at_c_upper, tol):
            return True
        return False

    @cached_property
    def u_closed(self):
        """
        Returns True if the surface is close in any of the u boundaries.
        """
        return bool(self.u_closed_lower(tol=1e-7) or self.u_closed_upper(tol=1e-7))

    @cached_property
    def v_closed(self):
        """
        Returns True if the surface is close in any of the u boundaries.
        """
        return bool(self.v_closed_lower(tol=1e-7) or self.v_closed_upper(tol=1e-7))

    def is_singularity_point(self, point, *args, **kwargs):
        """Returns True if the point belongs to the surface singularity and False otherwise."""
        tol = kwargs.get("tol", 1e-6)
        if not self.u_closed and not self.v_closed:
            return False
        u_min, u_max, v_min, v_max = self.domain

        test_lower = self.point2d_to_3d(design3d.Point2D(u_min, v_min))
        test_upper = self.point2d_to_3d(design3d.Point2D(u_max, v_max))

        if self.u_closed_lower(tol=tol) and test_lower.is_close(point, tol):
            return True
        if self.u_closed_upper(tol=tol) and test_upper.is_close(point, tol):
            return True
        if self.v_closed_lower(tol=tol) and test_lower.is_close(point, tol):
            return True
        if self.v_closed_upper(tol=tol) and test_upper.is_close(point, tol):
            return True
        return False

    def _get_singularity_line(self, test_point):
        """
        Helper function to fix_start_end_singularity_point_any_direction.

        Determines the singularity line, side, and domain boundary for a given test point on the parametric domain.
        - line: A 2D line representing the singularity line (degenerated line) is a 2D line on UV that correspond to
            a point in 3D space.
        - side: A string indicating the side of the singularity line ('u-'/'u+' or 'v-'/'v+').
        - domain_bound: The domain boundary value associated with the singularity line.

        :param test_point: The test 3D point that lies on the singularity.
        """
        a, b, c, d = self.domain
        line = None
        _side = None
        _domain_bound = None
        if self.u_closed:
            if (self.u_closed_lower() and
                    test_point.is_close(self.point2d_to_3d(design3d.Point2D(0.5 * (a + b), c)))):
                line = curves.Line2D(design3d.Point2D(a, c), design3d.Point2D(b, c))
                _side = "u-"
                _domain_bound = c
            if (self.u_closed_upper() and
                    test_point.is_close(self.point2d_to_3d(design3d.Point2D(0.5 * (a + b), d)))):
                line = curves.Line2D(design3d.Point2D(a, d), design3d.Point2D(b, d))
                _side = "u+"
                _domain_bound = d
        else:
            if (self.v_closed_lower() and
                    test_point.is_close(self.point2d_to_3d(design3d.Point2D(a, 0.5 * (c + d))))):
                line = curves.Line2D(design3d.Point2D(a, c), design3d.Point2D(a, d))
                _side = "v-"
                _domain_bound = a
            if (self.v_closed_upper() and
                    test_point.is_close(self.point2d_to_3d(design3d.Point2D(b, 0.5 * (c + d))))):
                line = curves.Line2D(design3d.Point2D(b, c), design3d.Point2D(b, d))
                _side = "v+"
                _domain_bound = b
        return line, _side, _domain_bound

    @staticmethod
    def _verify_points(points, side, domain_bound, start_end):
        """
        Helper function to fix_start_end_singularity_point_any_direction.

        Verifies and adjusts the given list of points based on the singularity side and domain boundary.

        :param points: The list of points to be verified.
        :param side: A string indicating the side of the singularity line ('u-'/'u+' or 'v-'/'v+').
        :param domain_bound: The domain boundary value associated with the singularity line.
        :param start_end: An integer (0 or 1) indicating whether to process the start or end of the list.

        :return: Verified and adjusted list of points.
        """
        if side.startswith("u"):
            i = 1
        else:
            i = 0
        indexes = [idx for idx, point in enumerate(points) if point[i] == domain_bound]
        if len(indexes) == 1 and indexes[0] != len(points) - 1:
            if start_end == 0:
                return points[indexes[0]:]

            return points[:indexes[0] + 1]
        return points

    def fix_start_end_singularity_point_any_direction(self, edge3d, points, points3d, tol: float = 1e-6):
        """
        Helper function.

        Uses local discretization and line intersection with the tangent line at the point just before the undefined
        point on the BREP of the 3D edge to find the real values on parametric domain.
        """
        points = verify_repeated_parametric_points(points)

        def get_temp_edge2d(_points):
            if len(_points) == 2:
                edge2d = edges.LineSegment2D(_points[0], _points[1])
            else:
                edge2d = edges.BSplineCurve2D.from_points_interpolation(_points, 2, centripetal=False)
            return edge2d

        umin, umax, d3din, d3dax = self.domain
        if self.is_singularity_point(points3d[0], tol=tol):
            singularity_line, side, domain_bound = self._get_singularity_line(points3d[0])
            if singularity_line and len(points) >= 3:
                points = self._verify_points(points, side, domain_bound, 0)
                if len(points) >= 3:
                    temp_edge2d = get_temp_edge2d(points[1:])
                    point = find_parametric_point_at_singularity(temp_edge2d, abscissa=0,
                                                                 singularity_line=singularity_line,
                                                                 domain=[umin, umax, d3din, d3dax])
                    if point and not point.is_close(points[0], 1e-3):
                        points[0] = point
        if self.is_singularity_point(points3d[-1], tol=tol):
            singularity_line, side, domain_bound = self._get_singularity_line(points3d[-1])
            if singularity_line:
                points = self._verify_points(points, side, domain_bound, 1)
                if len(points) >= 3:
                    temp_edge2d = get_temp_edge2d(points[:-1])

                    point = find_parametric_point_at_singularity(temp_edge2d, abscissa=temp_edge2d.length(),
                                                                 singularity_line=singularity_line,
                                                                 domain=[umin, umax, d3din, d3dax])
                    if point and not point.is_close(points[-1], 1e-3):
                        points[-1] = point
        return points

    def is_undefined_brep(self, edge):
        """Returns True if the edge is contained within the periodicity boundary."""
        if isinstance(edge.simplify, edges.LineSegment2D):
            umin, umax, d3din, d3dax = self.domain
            if self.x_periodicity and edge.simplify.line.unit_direction_vector().is_colinear_to(design3d.Y2D) \
                    and (math.isclose(abs(edge.start.x), umin, abs_tol=1e-4) or
                         math.isclose(abs(edge.start.x), umax, abs_tol=1e-4)):
                if (self.point2d_to_3d(
                        design3d.Point2D(umin, d3din)).is_close(self.point2d_to_3d(design3d.Point2D(umax, d3din))) and
                        self.point2d_to_3d(
                            design3d.Point2D(umin, d3dax)).is_close(self.point2d_to_3d(design3d.Point2D(umax, d3dax)))):
                    return True
            if self.y_periodicity and edge.simplify.line.unit_direction_vector().is_colinear_to(design3d.X2D) \
                    and (math.isclose(abs(edge.start.y), d3din, abs_tol=1e-4) or
                         math.isclose(abs(edge.start.y), d3dax, abs_tol=1e-4)):
                if (self.point2d_to_3d(
                        design3d.Point2D(umin, d3din)).is_close(self.point2d_to_3d(design3d.Point2D(umin, d3dax))) and
                        self.point2d_to_3d(
                            design3d.Point2D(umax, d3din)).is_close(self.point2d_to_3d(design3d.Point2D(umax, d3dax)))):
                    return True
        return False

    def fix_undefined_brep_with_neighbors(self, edge, previous_edge, next_edge):
        """Uses neighbors edges to fix edge contained within the periodicity boundary."""
        delta_previous = previous_edge.end - edge.start
        delta_next = next_edge.start - edge.end

        def translate_brep(periodicity):
            edge_ = edge
            if not self.is_undefined_brep(previous_edge) and \
                    math.isclose(delta_previous.norm(), periodicity, abs_tol=1e-3):
                edge_ = edge.translation(delta_previous)
            elif not self.is_undefined_brep(next_edge) and \
                    math.isclose(delta_next.norm(), periodicity, abs_tol=1e-3):
                edge_ = edge.translation(delta_next)
            return edge_

        if self.x_periodicity:
            edge = translate_brep(self.x_periodicity)
        elif self.y_periodicity:
            edge = translate_brep(self.y_periodicity)
        return edge


class BezierSurface3D(BSplineSurface3D):
    """
    A 3D Bezier surface.

    :param degree_u: The degree of the Bezier surface in the u-direction.
    :type degree_u: int
    :param degree_v: The degree of the Bezier surface in the v-direction.
    :type degree_v: int
    :param control_points: A list of lists of control points defining the Bezier surface.
    :type control_points: List[List[`design3d.Point3D`]]
    :param nb_u: The number of control points in the u-direction.
    :type nb_u: int
    :param nb_v: The number of control points in the v-direction.
    :type nb_v: int
    :param name: (Optional) name for the Bezier surface.
    :type name: str
    """

    def __init__(self, degree_u: int, degree_v: int,
                 control_points: List[List[design3d.Point3D]],
                 nb_u: int, nb_v: int, name=''):
        u_knots = generate_knot_vector(degree_u, nb_u)
        v_knots = generate_knot_vector(degree_v, nb_v)

        u_multiplicities = [1] * len(u_knots)
        v_multiplicities = [1] * len(v_knots)

        BSplineSurface3D.__init__(self, degree_u, degree_v,
                                  control_points, nb_u, nb_v,
                                  u_multiplicities, v_multiplicities,
                                  u_knots, v_knots, None, name)
