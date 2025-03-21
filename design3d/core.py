#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base classes.
"""
import os
import tempfile
import warnings
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import List, Tuple

try:
    import gmsh
except (TypeError, OSError):
    pass
import matplotlib.pyplot as plt
import numpy as np


import design3d
import design3d.templates
from design3d.core_compiled import bbox_is_intersecting
from design3d.discrete_representation_compiled import triangle_intersects_voxel
from design3d.utils.step_writer import product_writer, geometric_context_writer, assembly_definition_writer, \
    STEP_HEADER, STEP_FOOTER, step_ids_to_str
from design3d.geometry import get_transfer_matrix_from_basis

np.seterr(divide='raise')

DEFAULT_COLOR = (0.8, 0.8, 0.8)


def element_in_list(element, list_elements, tol: float = 1e-6):
    """
    Verifies if a design3d element is inside a list  of elements, considering a certain tolerance.

    :param element: Element to be verified inside list.
    :param list_elements: List of elements to be used.
    :param tol: Tolerance to consider if two points are the same.
    :return: True if there is an element inside the list close to the element to given tolerance.
    """
    for element_i in list_elements:
        if element.is_close(element_i, tol):
            return True
    return False


def point_in_list(point, list_points, tol: float = 1e-6):
    """
    Verifies if a point is inside a list  of points, considering a certain tolerance.

    :param point: Point to be verified inside list.
    :param list_points: List of points to be used.
    :param tol: Tolerance to consider if two points are the same.
    :return: True if there is a point inside the list close to the point to given tolerance.
    """

    if not list_points:
        return False
    return point.in_list(list_points, tol)


def edge_in_list(edge, list_edges, tol: float = 1e-6):
    """
    Verifies if an edge is inside a list  of edges, considering a certain tolerance.

    :param edge: Edge to be verified inside list.
    :param list_edges: List of edges to be used.
    :param tol: Tolerance to consider if two points are the same.
    :return: True if there is an edge inside the list close to the edge to given tolerance.
    """

    return element_in_list(edge, list_edges, tol)


def get_element_index_in_list(element, list_elements, tol: float = 1e-6):
    """
    Gets the index an element inside a list of elements, considering a certain tolerance.

    :param element: Element to be verified inside list.
    :param list_elements: List of elements to be used.
    :param tol: Tolerance to consider if two elements are the same.
    :return: The element index.
    """
    for i, element_i in enumerate(list_elements):
        if element_i.is_close(element, tol):
            return i
    return None


def get_point_index_in_list(point, list_points, tol: float = 1e-6):
    """
    Gets the index a point inside a list of points, considering a certain tolerance.

    :param point: Point to be verified inside list.
    :param list_points: List of points to be used.
    :param tol: Tolerance to consider if two points are the same.
    :return: The point index.
    """

    return get_element_index_in_list(point, list_points, tol)


def get_edge_index_in_list(edge, list_edges, tol: float = 1e-6):
    """
    Gets the index a edge inside a list of edges, considering a certain tolerance.

    :param edge: Edge to be verified inside list.
    :param list_edges: List of edges to be used.
    :param tol: Tolerance to consider if two edges are the same.
    :return: The edge index.
    """

    return get_element_index_in_list(edge, list_edges, tol)


def determinant(vec1, vec2, vec3):
    """
    Calculates the determinant for a three vector matrix.

    """
    # TODO: to be removed
    a = np.array((vec1.vector, vec2.vector, vec3.vector))
    return np.linalg.det(a)


def delete_double_point(list_point):
    """
    Delete duplicate points from a list of points.

    :param list_point: The initial list of points
    :type list_point: Union[List[:class:`design3d.Point2D`],
        List[:class:`design3d.Point3D`]]
    :return: The final list of points containing no duplicates
    :rtype: Union[List[:class:`design3d.Point2D`],
        List[:class:`design3d.Point3D`]]
    """
    # TODO : this method would be faster using sets
    points = []
    for point in list_point:
        if point not in points:
            points.append(point)
        else:
            continue
    return points


def map_primitive_with_initial_and_final_frames(primitive, initial_frame, final_frame):
    """
    Frame maps a primitive in an assembly to its good position.

    :param primitive: primitive to map
    :type primitive: Primitive3D
    :param initial_frame: Initial frame
    :type initial_frame: design3d.Frame3D
    :param final_frame: The frame resulted after applying a transformation to the initial frame
    :type final_frame: design3d.Frame3D
    :return: A new positioned primitive
    :rtype: Primitive3D

    """
    if initial_frame == final_frame:
        return primitive
    if initial_frame == primitive:
        return final_frame
    transfer_matrix = get_transfer_matrix_from_basis(initial_frame.basis(), final_frame.basis())
    u_vector = design3d.Vector3D(*transfer_matrix[0])
    v_vector = design3d.Vector3D(*transfer_matrix[1])
    w_vector = design3d.Vector3D(*transfer_matrix[2])
    new_frame = design3d.Frame3D(final_frame.origin, u_vector, v_vector, w_vector)
    if new_frame == design3d.OXYZ:
        return primitive
    new_primitive = primitive.frame_mapping(new_frame, 'old')
    return new_primitive


def helper_babylon_data(babylon_data, display_points):
    """Helper function to babylon_data."""
    # Compute max length in each direction
    all_positions = []
    all_points = []
    for mesh in babylon_data["meshes"]:
        all_positions += _extract_positions(mesh)

    for line in babylon_data["lines"]:
        points = line["points"]
        all_points.extend(points)
    if display_points:
        all_points.extend(display_points)

    # Convert to a NumPy array and reshape
    positions_array = np.array([])
    if all_points and all_positions:
        positions_array = np.concatenate((np.array(all_positions).reshape(-1, 3), np.array(all_points)))
    elif all_positions:
        positions_array = np.array(all_positions).reshape(-1, 3)
    elif all_points:
        positions_array = np.array(all_points)
    # Compute min and max for each dimension
    min_vals = positions_array.min(axis=0)
    max_vals = positions_array.max(axis=0)

    # Calculate max length of the bounding box
    max_length = float(max(max_vals - min_vals))
    print('max_length', max_length)

    # Calculate center point of the bounding box
    center = (0.5 * (min_vals + max_vals)).tolist()

    babylon_data['max_length'] = max_length
    babylon_data['center'] = center

    return babylon_data


def _extract_positions(mesh):
    """Helper function to extract positions from babylon_data."""
    all_positions = []

    for primitives_mesh in mesh.get("primitives_meshes", []):
        all_positions += _extract_positions(primitives_mesh)

    all_positions += mesh.get("positions", [])
    return all_positions


@dataclass
class EdgeStyle:
    """
    Data class for styling edges Matplotlib plots.

    """
    color: str = 'k'
    alpha: float = 1
    edge_ends: bool = False
    edge_direction: bool = False
    width: float = None
    arrow: bool = False
    plot_points: bool = False
    dashed: bool = True
    linestyle: str = '-'
    linewidth: float = 1
    equal_aspect: bool = True


class Primitive3D:
    """
    Defines a Primitive3D.
    """

    def __init__(self, color: Tuple[float, float, float] = None, alpha: float = 1.0,
                 reference_path: str = design3d.PATH_ROOT, name: str = ''):
        self.color = color
        self.alpha = alpha
        self.reference_path = reference_path
        self.name = name

    def babylon_param(self):
        """
        Returns babylonjs parameters.

        :return: babylonjs parameters (alpha, name, color)
        :rtype: dict
        """

        babylon_param = {
            'alpha': self.alpha,
            'name': self.name,
            'color': list(self.color) if self.color is not None else [0.8, 0.8, 0.8]
        }

        return babylon_param

    def triangulation(self, *args, **kwargs):
        """
        Get object triangulation.
        """
        raise NotImplementedError(
            f"triangulation method should be implemented on class {self.__class__.__name__}")

    def babylon_meshes(self, *args, **kwargs):
        """
        Returns the babylonjs mesh.
        """
        mesh = self.triangulation()
        if mesh is None:
            return []
        babylon_mesh = mesh.to_babylon()
        babylon_mesh.update(self.babylon_param())
        babylon_mesh["reference_path"] = self.reference_path
        return [babylon_mesh]
    

    def babylonjs(
        self,
        page_name: str = None,
        use_cdn: bool = True,
        debug: bool = False,
        merge_meshes: bool = True,
        dark_mode: bool = False,
    ):
        model = VolumeModel([self], name=self.name)
        return model.babylonjs(page_name=page_name, use_cdn=use_cdn, debug=debug, merge_meshes=merge_meshes,
                        dark_mode=dark_mode)


class CompositePrimitive3D(Primitive3D):
    """
    A collection of simple primitives3D.
    """

    def __init__(self, primitives: List[Primitive3D], color: Tuple[float, float, float] = None, alpha: float = 1,
                 reference_path: str = design3d.PATH_ROOT, name: str = ""):
        self.primitives = primitives
        Primitive3D.__init__(self, color=color, alpha=alpha, reference_path=reference_path, name=name)
        self._utd_primitives_to_index = False

    # def to_dict(self, *args, **kwargs):
    #     """Avoids storing points in memo that makes serialization slow."""
    #     return dc.PhysicalObject.to_dict(self, use_pointers=False)

    def plot(self, ax=None, edge_style: EdgeStyle = EdgeStyle()):
        """
        Plot the 3D primitives onto the given Axes3D object.

        :param ax: optional
            The Axes3D object onto which to plot the primitives. If None, a new
            figure and Axes3D object will be created.
        :type ax: Matplotlib plot
        edge_style : optional
            The EdgeStyle to use when plotting the primitives.
        :type edge_style: d3de.EdgeStyle
        :return: The Axes3D object onto which the primitives were plotted.
        :rtype: Matplotlib plot
        """
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
        for primitive in self.primitives:
            primitive.plot(ax=ax, edge_style=edge_style)
        return ax


class BoundingRectangle:
    """
    Bounding rectangle.

    :param xmin: minimal x coordinate
    :type xmin: float
    :param xmax: maximal x coordinate
    :type xmax: float
    :param ymin: minimal y coordinate
    :type ymin: float
    :param ymax: maximal y coordinate
    :type ymax: float
    """

    def __init__(self, xmin: float, xmax: float, ymin: float, ymax: float, name: str = ''):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.name = name

    def __getitem__(self, key):
        if key == 0:
            return self.xmin
        if key == 1:
            return self.xmax
        if key == 2:
            return self.ymin
        if key == 3:
            return self.ymax
        raise IndexError

    def bounds(self):
        """
        Return the bounds of the BoundingRectangle.
        """
        return self.xmin, self.xmax, self.ymin, self.ymax

    def bounding_points(self):
        """
        Return the bounds of the BoundingRectangle.
        """
        return [design3d.Point2D(self.xmin, self.ymin), design3d.Point2D(self.xmax, self.ymin),
                design3d.Point2D(self.xmax, self.ymax), design3d.Point2D(self.xmin, self.ymax)]

    def plot(self, ax=None, color='k', linestyle='dotted'):
        """
        Plot of the bounding rectangle and its vertex.
        """

        if not ax:
            _, ax = plt.subplots()
        x = [self.xmin, self.xmax, self.xmax, self.xmin, self.xmin]
        y = [self.ymin, self.ymin, self.ymax, self.ymax, self.ymin]

        ax.plot(x, y, color=color, linestyle=linestyle)
        ax.scatter(x, y, color=color)
        return ax

    def area(self):
        """
        Calculates the area of the bounding rectangle.
        """
        return (self.xmax - self.xmin) * (self.ymax - self.ymin)

    def center(self):
        """
        Calculates the bounding rectangle center.
        """
        return design3d.Point2D(0.5 * (self.xmin + self.xmax), 0.5 * (self.ymin + self.ymax))

    def is_intersecting(self, b_rectangle2):
        """
        Returns True if there is an intersection with another specified bounding rectangle or False otherwise.

        :param b_rectangle2: bounding rectangle to verify intersection
        :type b_rectangle2: :class:`BoundingRectangle`
        """
        return self.xmin < b_rectangle2.xmax and self.xmax > b_rectangle2.xmin \
            and self.ymin < b_rectangle2.ymax and self.ymax > b_rectangle2.ymin

    def b_rectangle_intersection(self, b_rectangle2):
        """
        Returns True if there is an intersection with another specified bounding rectangle or False otherwise.

        :param b_rectangle2: bounding rectangle to verify intersection
        :type b_rectangle2: :class:`BoundingRectangle`
        """
        warnings.warn('b_rectangle_intersection is deprecated, please use is_intersecting instead')
        return self.is_intersecting(b_rectangle2)

    def is_inside_b_rectangle(self, b_rectangle2, tol: float = 1e-6):
        """
        Returns True if the bounding rectangle is totally inside specified bounding rectangle and False otherwise.

        :param b_rectangle2: A bounding rectangle
        :type b_rectangle2: :class:`BoundingRectangle`
        :param tol: A tolerance for considering inside
        :type tol: float
        """
        return (self.xmin >= b_rectangle2.xmin - tol) and (self.xmax <= b_rectangle2.xmax + tol) \
            and (self.ymin >= b_rectangle2.ymin - tol) and (self.ymax <= b_rectangle2.ymax + tol)

    def point_inside(self, point: design3d.Point2D):
        """
        Returns True if a specified point is inside the bounding rectangle and False otherwise.

        :param point: A 2 dimensional point
        :type point: :class:`design3d.Point2D`
        """
        return self.xmin < point.x < self.xmax and self.ymin < point.y < self.ymax

    def intersection_area(self, b_rectangle2):
        """
        Calculates the intersection area between two bounding rectangle.

        :param b_rectangle2: A bounding rectangle
        :type b_rectangle2: :class:`BoundingRectangle`
        """
        if not self.is_intersecting(b_rectangle2):
            return 0
        if self.is_inside_b_rectangle(b_rectangle2) or b_rectangle2.is_inside_b_rectangle(self):
            return min(self.area(), b_rectangle2.area())

        lx = min(self.xmax, b_rectangle2.xmax) - max(self.xmin, b_rectangle2.xmin)
        ly = min(self.ymax, b_rectangle2.ymax) - max(self.ymin, b_rectangle2.ymin)

        return lx * ly

    def distance_to_b_rectangle(self, b_rectangle2):
        """
        Calculates the minimal distance between two bounding rectangles.

        :param b_rectangle2: A bounding rectangle
        :type b_rectangle2: :class:`BoundingRectangle`
        """
        if self.is_intersecting(b_rectangle2):
            return 0

        permute_b_rec1 = self
        permute_b_rec2 = b_rectangle2

        if permute_b_rec2.xmin < permute_b_rec1.xmin:
            permute_b_rec1, permute_b_rec2 = permute_b_rec2, permute_b_rec1
        dx = max(permute_b_rec2.xmin - permute_b_rec1.xmax, 0)

        if permute_b_rec2.ymin < permute_b_rec1.ymin:
            permute_b_rec1, permute_b_rec2 = permute_b_rec2, permute_b_rec1
        dy = max(permute_b_rec2.ymin - permute_b_rec1.ymax, 0)

        return (dx ** 2 + dy ** 2) ** 0.5

    def distance_to_point(self, point: design3d.Point2D):
        """
        Calculate the minimal distance between the bounding rectangle and a specified point.

        :param point: A 2D point
        :type point: :class:`design3d.Point2D`
        """
        if self.point_inside(point):
            return min([self.xmax - point.x, point.y - self.xmin,
                        self.ymax - point.y, point.y - self.ymin])

        if point.x < self.xmin:
            dx = self.xmin - point.x
        elif self.xmax < point.x:
            dx = point.x - self.xmax
        else:
            dx = 0

        if point.y < self.ymin:
            dy = self.ymin - point.y
        elif self.ymax < point.y:
            dy = point.y - self.ymax
        else:
            dy = 0

        return (dx ** 2 + dy ** 2) ** 0.5

    @classmethod
    def from_points(cls, points: List[design3d.Point2D], name: str = '') -> "BoundingRectangle":
        """
        Initializes a bounding rectangle from a list of points.

        :param points: The list of points to create the bounding rectangle from.
        :type points: List[design3d.Point2D].
        :param name: object's name.
        :return: The bounding rectangle initialized from the list of points.
        :rtype: BoundingRectangle
        """
        points_array = np.array(points)
        # Compute min and max for each dimension
        xmin, ymin = points_array.min(axis=0)
        xmax, ymax = points_array.max(axis=0)
        return cls(xmin, xmax, ymin, ymax, name=name)


class BoundingBox:
    """
    An axis aligned boundary box.
    """

    def __init__(self, xmin: float, xmax: float, ymin: float, ymax: float, zmin: float, zmax: float, name: str = ""):
        """
        Initializes a bounding box.

        :param xmin: The x-coordinate of the lower-left corner.
        :type xmin: float
        :param xmax: The x-coordinate of the upper-right corner.
        :type xmax: float
        :param ymin: The y-coordinate of the lower-left corner.
        :type ymin: float
        :param ymax: The y-coordinate of the upper-right corner.
        :type ymax: float
        :param zmin: The z-coordinate of the lower-left corner.
        :type zmin: float
        :param zmax: The z-coordinate of the upper-right corner.
        :type zmax: float
        :param name: The name of the bounding box.
        :type name: str, optional
        """
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.zmin = zmin
        self.zmax = zmax
        self._size = None
        self._octree = None
        self.name = name

    @property
    @lru_cache
    def center(self):
        """
        Computes the center of the bounding box.

        TODO: change lru_cache to cached property when support for py3.7 is dropped.
        """
        return design3d.Point3D(0.5 * (self.xmin + self.xmax),
                               0.5 * (self.ymin + self.ymax),
                               0.5 * (self.zmin + self.zmax))

    def __hash__(self) -> int:
        return sum(hash(point) for point in self.points)

    def __add__(self, other_bbox) -> "BoundingBox":
        return BoundingBox(min(self.xmin, other_bbox.xmin),
                           max(self.xmax, other_bbox.xmax),
                           min(self.ymin, other_bbox.ymin),
                           max(self.ymax, other_bbox.ymax),
                           min(self.zmin, other_bbox.zmin),
                           max(self.zmax, other_bbox.zmax))

    def to_dict(self, *args, **kwargs) -> dict:
        """
        Converts the bounding box to a dictionary representation.

        :param use_pointers: DESCRIPTION, defaults to True
        :type use_pointers: bool, optional
        :param memo: DESCRIPTION, defaults to None
        :type memo: TYPE, optional
        :param path: A string representing the current position of the object in the serialized data structure.
        :type path: str, optional

        :return: The dictionary representation of the bounding box.
        :rtype: dict
        """
        return {'object_class': 'design3d.core.BoundingBox',
                'name': self.name,
                'xmin': self.xmin,
                'xmax': self.xmax,
                'ymin': self.ymin,
                'ymax': self.ymax,
                'zmin': self.zmin,
                'zmax': self.zmax,
                }

    @property
    def points(self) -> List[design3d.Point3D]:
        """
        Returns the eight corner points of the bounding box.

        :return: A list of eight 3D points representing the corners of the bounding box.
        :rtype: list of design3d.Point3D
        """
        return [design3d.Point3D(self.xmin, self.ymin, self.zmin),
                design3d.Point3D(self.xmax, self.ymin, self.zmin),
                design3d.Point3D(self.xmax, self.ymax, self.zmin),
                design3d.Point3D(self.xmin, self.ymax, self.zmin),
                design3d.Point3D(self.xmin, self.ymin, self.zmax),
                design3d.Point3D(self.xmax, self.ymin, self.zmax),
                design3d.Point3D(self.xmax, self.ymax, self.zmax),
                design3d.Point3D(self.xmin, self.ymax, self.zmax)]

    def plot(self, ax=None, color='gray'):
        """
        Plot the bounding box on 3D axes.

        :param ax: The 3D axes to plot on. If not provided, a new figure will be created.
        :type ax: Matplotlib.axes._subplots.Axes3DSubplot, optional
        :param color: The color of the lines used to plot the bounding box.
        :type color: str, optional
        :return: The 3D axes with the plotted bounding box.
        :rtype: Matplotlib.axes._subplots.Axes3DSubplot
        """
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')

        bbox_edges = [[self.points[0], self.points[1]],
                      [self.points[0], self.points[3]],
                      [self.points[0], self.points[4]],
                      [self.points[1], self.points[2]],
                      [self.points[1], self.points[5]],
                      [self.points[2], self.points[3]],
                      [self.points[2], self.points[6]],
                      [self.points[3], self.points[7]],
                      [self.points[4], self.points[5]],
                      [self.points[5], self.points[6]],
                      [self.points[6], self.points[7]],
                      [self.points[7], self.points[4]]]

        for edge in bbox_edges:
            ax.plot3D([edge[0][0], edge[1][0]],
                      [edge[0][1], edge[1][1]],
                      [edge[0][2], edge[1][2]],
                      color=color)
        ax.set_xlabel('X Label')
        ax.set_ylabel('Y Label')
        ax.set_zlabel('Z Label')
        return ax

    @classmethod
    def from_bounding_boxes(cls, bounding_boxes: List["BoundingBox"], name: str = "") -> "BoundingBox":
        """
        Create a bounding box that contains multiple bounding boxes.

        :param bounding_boxes: A list of bounding boxes that need to be contained.
        :type bounding_boxes: List[BoundingBox]
        :param name: A name for the bounding box, optional.
        :type name: str

        :return: A new bounding box that contains all the input bounding boxes.
        :rtype: BoundingBox
        """
        # Create a 2D NumPy array where each row corresponds to the coordinates of a bounding box
        # [xmin, xmax, ymin, ymax, zmin, zmax]
        coords = np.array([[bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax] for bb in bounding_boxes])

        # Find the global minimum and maximum for each axis
        mins = np.amin(coords, axis=0)
        maxs = np.amax(coords, axis=0)

        # Assign min and max for each axis
        xmin, xmax, ymin, ymax, zmin, zmax = mins[0], maxs[1], mins[2], maxs[3], mins[4], maxs[5]

        return cls(xmin, xmax, ymin, ymax, zmin, zmax, name=name)

    @classmethod
    def from_points(cls, points: List[design3d.Point3D], name: str = '') -> "BoundingBox":
        """
        Initializes a bounding box from a list of points.

        :param points: The list of points to create the bounding box from.
        :type points: List[design3d.Point3D].
        :param name: object's name.
        :return: The bounding box initialized from the list of points.
        :rtype: BoundingBox
        """
        points_array = np.array(points)
        # Compute min and max for each dimension
        xmin, ymin, zmin = points_array.min(axis=0)
        xmax, ymax, zmax = points_array.max(axis=0)

        return cls(xmin, xmax, ymin, ymax, zmin, zmax, name=name)

    def to_frame(self) -> design3d.Frame3D:
        """
        Converts the bounding box to a 3D frame.

        :return: A 3D frame with origin at the center and axes aligned with the x, y, and z dimensions of
            the bounding box.
        :rtype: design3d.Frame3D
        """
        x = design3d.Vector3D((self.xmax - self.xmin), 0, 0)
        y = design3d.Vector3D(0, (self.ymax - self.ymin), 0)
        z = design3d.Vector3D(0, 0, (self.zmax - self.zmin))
        return design3d.Frame3D(self.center, x, y, z)

    def get_points_inside_bbox(self, points_x, points_y, points_z):
        """
        Gets points inside the BoudingBox.

        :param points_x: Number of points in x direction.
        :param points_y: Number of points in y direction.
        :param points_z: Number of points in z direction.
        :return: list of points inside bounding box.
        """
        _size = [self.size[0] / points_x, self.size[1] / points_y,
                 self.size[2] / points_z]
        initial_center = self.center.translation(
            -design3d.Vector3D(self.size[0] / 2 - _size[0] / 2,
                              self.size[1] / 2 - _size[1] / 2,
                              self.size[2] / 2 - _size[2] / 2))
        points = []
        for z_box in range(points_z):
            for y_box in range(points_y):
                for x_box in range(points_x):
                    translation_vector = design3d.Vector3D(x_box * _size[0], y_box * _size[1],
                                                          z_box * _size[2])
                    point = initial_center.translation(translation_vector)
                    points.append(point)
        return points

    @property
    def size(self):
        """Gets the Size of the Bounding Box."""

        if not self._size:
            self._size = [self.xmax - self.xmin, self.ymax - self.ymin, self.zmax - self.zmin]
        return self._size

    def volume(self) -> float:
        """
        Calculates the volume of a bounding box.

        :return: The volume of the bounding box.
        :rtype: float
        """
        return (self.xmax - self.xmin) * (self.ymax - self.ymin) * (self.zmax - self.zmin)

    def scale(self, factor: float) -> "BoundingBox":
        """
        Scales the bounding box by a given factor and returns a new BoundingBox.

        :param factor: The scaling factor.
        :type factor: float

        :return: A new scaled BoundingBox.
        :rtype: BoundingBox
        """
        x_center = (self.xmin + self.xmax) / 2
        y_center = (self.ymin + self.ymax) / 2
        z_center = (self.zmin + self.zmax) / 2
        x_size, y_size, z_size = self.size

        scaled_half_x_size = (x_size * factor) / 2
        scaled_half_y_size = (y_size * factor) / 2
        scaled_half_z_size = (z_size * factor) / 2

        # Calculate new min and max values
        new_xmin = x_center - scaled_half_x_size
        new_xmax = x_center + scaled_half_x_size
        new_ymin = y_center - scaled_half_y_size
        new_ymax = y_center + scaled_half_y_size
        new_zmin = z_center - scaled_half_z_size
        new_zmax = z_center + scaled_half_z_size

        # Return a new BoundingBox object
        return BoundingBox(new_xmin, new_xmax, new_ymin, new_ymax, new_zmin, new_zmax, self.name)

    def is_intersecting(self, bbox2, tol: float = 1e-6):
        """
        Checks if two bounding boxes are intersecting or touching.

        :param self: BoundingBox object representing the first bounding box.
        :param bbox2: BoundingBox object representing the second bounding box.
        :param tol: tolerance to be considered.

        :return: True if the bounding boxes are intersecting or touching, False otherwise.
        """
        return bbox_is_intersecting(self, bbox2, tol)

    def is_inside_bbox(self, bbox2: "BoundingBox") -> bool:
        """
        Checks if a bounding box is contained inside another bounding box.

        :param bbox2: The bounding box to check against.
        :type bbox2: BoundingBox
        :return: True if the bounding box is contained inside bbox2, False otherwise.
        :rtype: bool
        """
        return (self.xmin >= bbox2.xmin - 1e-6) and (self.xmax <= bbox2.xmax + 1e-6) \
            and (self.ymin >= bbox2.ymin - 1e-6) and (self.ymax <= bbox2.ymax + 1e-6) \
            and (self.zmin >= bbox2.zmin - 1e-6) and (self.zmax <= bbox2.zmax + 1e-6)

    def intersection_volume(self, bbox2: "BoundingBox") -> float:
        """
        Calculate the volume of the intersection of two bounding boxes.

        :param bbox2: The second bounding box to intersect with the first one.
        :type bbox2: BoundingBox
        :return: The volume of the intersection of two bounding boxes.
        :rtype: float
        """
        if not self.is_intersecting(bbox2):
            return 0
        if self.is_inside_bbox(bbox2) or bbox2.is_inside_bbox(self):
            return min(self.volume(), bbox2.volume())

        lx = min(self.xmax, bbox2.xmax) - max(self.xmin, bbox2.xmin)
        ly = min(self.ymax, bbox2.ymax) - max(self.ymin, bbox2.ymin)
        lz = min(self.zmax, bbox2.zmax) - max(self.zmin, bbox2.zmin)

        return lx * ly * lz

    def is_intersecting_triangle(self, triangle: "Triangle3D") -> bool:
        """
        Check if the bounding box and a triangle are intersecting or touching.

        :param triangle: the triangle to check if there is an intersection with.
        :type triangle: Triangle3D

        :return: True if the bounding box and the triangle are intersecting or touching, False otherwise.
        :rtype: bool
        """
        _triangle = tuple((point.x, point.y, point.z) for point in triangle.points)
        _center = (self.center[0], self.center[1], self.center[2])
        _extents = tuple(size / 2 for size in self.size)

        return triangle_intersects_voxel(_triangle, _center, _extents)

    def distance_to_bbox(self, bbox2: "BoundingBox") -> float:
        """
        Calculates the distance between the bounding box and another bounding box.

        If the bounding boxes intersect, the distance is 0.
        Otherwise, the distance is the minimum Euclidean distance between their closest faces.

        :param bbox2: Another bounding box to compare with.
        :type bbox2: BoundingBox
        :return: The distance between the bounding boxes.
        :rtype: float
        """

        if self.is_intersecting(bbox2):
            return 0

        permute_bbox1 = self
        permute_bbox2 = bbox2

        if permute_bbox2.xmin < permute_bbox1.xmin:
            permute_bbox1, permute_bbox2 = permute_bbox2, permute_bbox1
        dx = max(permute_bbox2.xmin - permute_bbox1.xmax, 0)

        if permute_bbox2.ymin < permute_bbox1.ymin:
            permute_bbox1, permute_bbox2 = permute_bbox2, permute_bbox1
        dy = max(permute_bbox2.ymin - permute_bbox1.ymax, 0)

        if permute_bbox2.zmin < permute_bbox1.zmin:
            permute_bbox1, permute_bbox2 = permute_bbox2, permute_bbox1
        dz = max(permute_bbox2.zmin - permute_bbox1.zmax, 0)

        return (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5

    def point_inside(self, point: design3d.Point3D, tol=1e-6) -> bool:
        """
        Determines if a point belongs to the bounding box.

        :param point: The point to check for inclusion.
        :type point: design3d.Point3D
        :param tol: tolerance.
        :return: True if the point belongs to the bounding box, False otherwise.
        :rtype: bool
        """
        return (
                self.xmin - tol <= point[0] <= self.xmax + tol
                and self.ymin - tol <= point[1] <= self.ymax + tol
                and self.zmin - tol <= point[2] <= self.zmax + tol
        )

    def distance_to_point(self, point: design3d.Point3D) -> float:
        """
        Calculates the minimum Euclidean distance between the bounding box and a point.

        :param point: The point to compare with.
        :type point: design3d.Point3D
        :return: The minimum distance between the point and the bounding box.
        :rtype: float
        """
        if self.point_inside(point):
            return min([self.xmax - point[0], point[0] - self.xmin,
                        self.ymax - point[1], point[1] - self.ymin,
                        self.zmax - point[2], point[2] - self.zmin])

        if point[0] < self.xmin:
            dx = self.xmin - point[0]
        elif self.xmax < point[0]:
            dx = point[0] - self.xmax
        else:
            dx = 0

        if point[1] < self.ymin:
            dy = self.ymin - point[1]
        elif self.ymax < point[1]:
            dy = point[1] - self.ymax
        else:
            dy = 0

        if point[2] < self.zmin:
            dz = self.zmin - point[2]
        elif self.zmax < point[2]:
            dz = point[2] - self.zmax
        else:
            dz = 0
        return (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5

    def is_close(self, other_bounding_box: "BoundingBox", tol: float = 1e-6) -> bool:
        """
        Check if two bounding boxes are close to each other considering the Euclidean distance of their corners points.

        The tolerance can be modified.

        :param other_bounding_box: the other bounding box.
        :type other_bounding_box: BoundingBox
        :param tol: The tolerance under which the Euclidean distance is considered equal to 0.
        :type tol: float

        :return: True if the bounding boxes are equal at the given tolerance, False otherwise.
        :rtype: bool
        """
        self_corner_min = design3d.Point3D(self.xmin, self.ymin, self.zmin)
        self_conrer_max = design3d.Point3D(self.xmax, self.ymax, self.zmax)
        other_corner_min = design3d.Point3D(other_bounding_box.xmin, other_bounding_box.ymin, other_bounding_box.zmin)
        other_corner_max = design3d.Point3D(other_bounding_box.xmax, other_bounding_box.ymax, other_bounding_box.zmax)

        return self_corner_min.is_close(other_corner_min, tol) and self_conrer_max.is_close(other_corner_max, tol)

    def octree(self):
        """Creates a simple octree structure for a bounding box."""
        if not self._octree:
            octants = []
            points_x, points_y, points_z = 2, 2, 2
            _size = [self.size[0] / points_x, self.size[1] / points_y,
                     self.size[2] / points_z]
            octants_center = self.get_points_inside_bbox(points_x, points_y, points_z)
            for octant_center in octants_center:
                mins_maxs = []
                for i, size_component in enumerate(_size):
                    mins_maxs.extend([octant_center[i] - size_component / 2, octant_center[i] + size_component / 2])
                octants.append(self.__class__(mins_maxs[0], mins_maxs[1], mins_maxs[2], mins_maxs[3],
                                              mins_maxs[4], mins_maxs[5]))
            self._octree = octants
        return self._octree


class Assembly:
    """
    Defines an assembly.

    :param components: A list of design3d objects
    :type components: List[:class:`design3d.core.Primitive3D`]
    :param positions: A list of design3d.Frame3D representing the positions of each component in the assembly absolute
        frame.
    :type positions: List[:class:`design3d.Frame3D`]
    :param name: The Assembly's name
    :type name: str
    """

    def __init__(self, components: List[Primitive3D], positions: List[design3d.Frame3D],
                 frame: design3d.Frame3D = design3d.OXYZ, name: str = ''):
        self.components = components
        self.frame = frame
        self.positions = positions
        self.primitives = [map_primitive_with_initial_and_final_frames(primitive, frame, frame_primitive)
                           for primitive, frame_primitive in zip(components, positions)]
        self._bbox = None
        self.name = name

    @property
    def bounding_box(self):
        """
        Returns the bounding box.

        """
        if not self._bbox:
            self._bbox = self._bounding_box()
        return self._bbox

    @bounding_box.setter
    def bounding_box(self, new_bounding_box):
        self._bbox = new_bounding_box

    def _bounding_box(self) -> BoundingBox:
        """
        Computes the bounding box of the model.
        """
        bbox_list = [prim.bounding_box for prim in self.primitives if hasattr(prim, "bounding_box")]
        if not bbox_list:
            return BoundingBox.from_points(self.primitives)
        return BoundingBox.from_bounding_boxes(bbox_list)

    def babylon_data(self, merge_meshes=True):
        """
        Get babylonjs data.

        :return: Dictionary with babylon data.
        """

        babylon_data = {'meshes': [],
                        'lines': []}
        display_points = []
        for primitive in self.primitives:
            if hasattr(primitive, 'babylon_meshes'):
                babylon_data['meshes'].extend(primitive.babylon_meshes(merge_meshes=merge_meshes))
            elif hasattr(primitive, 'babylon_curves'):
                curves = primitive.babylon_curves()
                if curves:
                    babylon_data['lines'].append(curves)
            elif hasattr(primitive, 'babylon_data'):
                data = primitive.babylon_data(merge_meshes=merge_meshes)
                babylon_data['meshes'].extend(mesh for mesh in data.get("meshes"))
                babylon_data['lines'].extend(line for line in data.get("lines"))
            elif isinstance(primitive, design3d.Point3D):
                display_points.append(primitive)
        return helper_babylon_data(babylon_data, display_points)

    def frame_mapping(self, frame: design3d.Frame3D, side: str):
        """
        Changes frame_mapping and return a new Assembly.

        side = 'old' or 'new'
        """
        new_positions = [position.frame_mapping(frame, side)
                         for position in self.positions]
        return Assembly(self.components, new_positions, self.frame, self.name)


    def to_step(self, current_id):
        """
        Creates step file entities from design3d objects.
        """
        step_content = ''

        product_content, current_id, assembly_data = self.to_step_product(current_id)
        step_content += product_content
        assembly_frames = assembly_data[-1]
        for i, primitive in enumerate(self.components):
            if primitive.__class__.__name__ in ('OpenShell3D', 'ClosedShell3D') or hasattr(primitive, "shell_faces"):
                primitive_content, current_id, primitive_data = primitive.to_step_product(current_id)
                assembly_frame_id = assembly_frames[0]
                component_frame_id = assembly_frames[i + 1]
                assembly_content, current_id = assembly_definition_writer(current_id, assembly_data[:-1],
                                                                          primitive_data, assembly_frame_id,
                                                                          component_frame_id)

            else:
                primitive_content, current_id, primitive_data = primitive.to_step(current_id)
                step_content += primitive_content
                assembly_frame_id = assembly_frames[0]
                component_frame_id = assembly_frames[i + 1]
                assembly_content, current_id = assembly_definition_writer(current_id, assembly_data[:-1],
                                                                          primitive_data, assembly_frame_id,
                                                                          component_frame_id)
            step_content += primitive_content
            step_content += assembly_content

        return step_content, current_id, assembly_data[:-1]

    def plot(self, ax=None, equal_aspect=True):
        """
        Matplotlib plot of model.

        To use for debug.
        """
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d', adjustable='box')
        for primitive in self.primitives:
            primitive.plot(ax)
        if not equal_aspect:
            # ax.set_aspect('equal')
            ax.set_aspect('auto')
        ax.margins(0.1)
        return ax

    def to_step_product(self, current_id):
        """
        Returns step product entities from design3d objects.
        """
        step_content = ''
        product_content, shape_definition_repr_id = product_writer(current_id, self.name)
        product_definition_id = shape_definition_repr_id - 2
        step_content += product_content
        shape_representation_id = shape_definition_repr_id + 1
        current_id = shape_representation_id
        assembly_position_content = ''
        frame_ids = []
        for frame in [self.frame] + self.positions:
            frame_content, current_id = frame.to_step(current_id + 1)
            assembly_position_content += frame_content
            frame_ids.append(current_id)

        geometric_context_content, geometric_representation_context_id = geometric_context_writer(current_id)

        step_content += f"#{shape_representation_id} = SHAPE_REPRESENTATION('',({step_ids_to_str(frame_ids)})," \
                        f"#{geometric_representation_context_id});\n"

        step_content += assembly_position_content

        step_content += geometric_context_content

        return step_content, geometric_representation_context_id, \
            [shape_representation_id, product_definition_id, frame_ids]


class Compound:
    """
    A class that can be a collection of any design3d primitives.
    """

    def __init__(self, primitives, name: str = ""):
        self.primitives = primitives
        self._bbox = None
        self._type = None
        self.name = name

    @property
    def bounding_box(self):
        """
        Returns the bounding box.

        """
        if not self._bbox:
            self._bbox = self._bounding_box()
        return self._bbox

    @bounding_box.setter
    def bounding_box(self, new_bounding_box):
        """Bounding box setter."""
        self._bbox = new_bounding_box

    @property
    def compound_type(self):
        """
        Returns the compound type.

        """
        if not self._type:
            if all(primitive.__class__.__name__ in ('OpenShell3D', 'ClosedShell3D') or
                   hasattr(primitive, "shell_faces") for primitive in self.primitives):
                self._type = "manifold_solid_brep"
            elif all(isinstance(primitive, (design3d.wires.Wire3D, design3d.edges.Edge, design3d.Point3D))
                     for primitive in self.primitives):
                self._type = "geometric_curve_set"
            else:
                self._type = "shell_based_surface_model"
        return self._type

    @compound_type.setter
    def compound_type(self, value):
        """Compound typesetter."""
        self._type = value

    def _bounding_box(self) -> BoundingBox:
        """
        Computes the bounding box of the model.
        """
        bbox_list = [p.bounding_box for p in self.primitives if hasattr(p, "bounding_box")]
        if not bbox_list:
            return BoundingBox.from_points(self.primitives)
        return BoundingBox.from_bounding_boxes(bbox_list)

    def frame_mapping(self, frame: design3d.Frame3D, side: str):
        """
        Changes frame_mapping and return a new Compound.

        side = 'old' or 'new'
        """
        new_primitives = [primitive.frame_mapping(frame, side)
                          for primitive in self.primitives]
        return Compound(new_primitives, self.name)

    def babylon_data(self, merge_meshes=True):
        """
        Get babylonjs data.

        :return: Dictionary with babylon data.
        """

        babylon_data = {'meshes': [],
                        'lines': []}
        display_points = []
        for primitive in self.primitives:
            if hasattr(primitive, 'babylon_meshes'):
                babylon_data['meshes'].extend(primitive.babylon_meshes(merge_meshes=merge_meshes))
            elif hasattr(primitive, 'babylon_curves'):
                curves = primitive.babylon_curves()
                if curves:
                    babylon_data['lines'].append(curves)
            elif hasattr(primitive, 'babylon_data'):
                data = primitive.babylon_data(merge_meshes=merge_meshes)
                babylon_data['meshes'].extend(mesh for mesh in data.get("meshes"))
                babylon_data['lines'].extend(line for line in data.get("lines"))
            elif isinstance(primitive, design3d.Point3D):
                display_points.append(primitive)
        return helper_babylon_data(babylon_data, display_points)


    def to_step(self, current_id):
        """
        Creates step file entities from design3d objects.
        """
        step_content = ''
        primitives_content = ''
        shape_ids = []
        product_content, current_id = product_writer(current_id, self.name)
        product_definition_id = current_id - 2
        step_content += product_content
        brep_id = current_id + 1
        frame_content, frame_id = design3d.OXYZ.to_step(brep_id)
        current_id = frame_id

        for primitive in self.primitives:
            primitive_content, current_id = primitive.to_step(current_id)
            primitives_content += primitive_content
            shape_ids.append(current_id)

        geometric_context_content, geometric_representation_context_id = geometric_context_writer(current_id)
        current_id = geometric_representation_context_id
        if self.compound_type == "manifold_solid_brep":
            step_content += f"#{brep_id} = MANIFOLD_SURFACE_SHAPE_REPRESENTATION(''," \
                            f"({step_ids_to_str(shape_ids)})," \
                            f"#{geometric_representation_context_id});\n"
        elif self.compound_type == "geometric_curve_set":
            current_id += 1
            step_content += f"#{brep_id} = GEOMETRICALLY_BOUNDED_SURFACE_SHAPE_REPRESENTATION(''," \
                            f"(#{current_id})," \
                            f"#{geometric_representation_context_id});\n"

            step_content += f"#{current_id} = GEOMETRIC_SET('',({step_ids_to_str(shape_ids)}));\n"
        step_content += frame_content
        step_content += primitives_content
        step_content += geometric_context_content

        return step_content, current_id, [brep_id, product_definition_id]


class VolumeModel:
    """
    A class containing one or several :class:`design3d.core.Primitive3D`.

    :param primitives: The vector's abscissa
    :type primitives: List[:class:`design3d.core.Primitive3D`]
    :param name: The VolumeModel's name
    :type name: str
    """

    def __init__(self, primitives: List[Primitive3D], name: str = ''):
        self.primitives = primitives
        self.name = name
        self.shells = []
        self._bbox = None
        self.name = name

    def __hash__(self):
        return sum(hash(point) for point in self.primitives)

    def __eq__(self, other):
        if self.__class__.__name__ != other.__class__.__name__:
            return False
        equ = True
        if len(self.primitives) != len(other.primitives):
            return False
        for p1, p2 in zip(self.primitives, other.primitives):
            # TODO: if 2 volume models has exact same primitives but in a different order, they are different?
            equ = equ and p1 == p2
        return equ

    @property
    def bounding_box(self):
        """
        Returns the bounding box.

        """
        if not self._bbox:
            self._bbox = self._bounding_box()
        return self._bbox

    @bounding_box.setter
    def bounding_box(self, new_bounding_box):
        self._bbox = new_bounding_box

    def _bounding_box(self) -> BoundingBox:
        """
        Computes the bounding box of the model.
        """
        return BoundingBox.from_bounding_boxes([p.bounding_box for p in self.primitives if hasattr(p, "bounding_box")])

    def volume(self) -> float:
        """
        Return the sum of volumes of the primitives.

        It does not make any Boolean operation in case of overlapping.

        """
        volume = 0
        for primitive in self.primitives:
            volume += primitive.volume()
        return volume

    def rotation(self, center: design3d.Point3D, axis: design3d.Vector3D,
                 angle: float):
        """
        Rotates the VolumeModel.

        :param center: rotation center
        :param axis: rotation axis
        :param angle: angle rotation
        :return: a new rotated VolumeModel
        """
        new_primitives = [
            primitive.rotation(center, axis, angle) for
            primitive in self.primitives]
        return VolumeModel(new_primitives, self.name)

    def translation(self, offset: design3d.Vector3D):
        """
        Translates the VolumeModel.

        :param offset: translation vector
        :return: A new translated VolumeModel
        """
        new_primitives = [primitive.translation(offset) for
                          primitive in self.primitives]
        return VolumeModel(new_primitives, self.name)

    def frame_mapping(self, frame: design3d.Frame3D, side: str):
        """
        Changes frame_mapping and return a new VolumeModel.

        side = 'old' or 'new'
        """
        new_primitives = [primitive.frame_mapping(frame, side)
                          for primitive in self.primitives]
        return VolumeModel(new_primitives, self.name)

    def copy(self, deep=True, memo=None):
        """
        Specific copy.
        """
        new_primitives = [primitive.copy(deep=deep, memo=memo) for primitive in self.primitives]
        return VolumeModel(new_primitives, self.name)

    def plot(self, equal_aspect=True):
        """
        Matplotlib plot of model.

        To use for debug.
        """
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d', adjustable='box')
        for primitive in self.primitives:
            primitive.plot(ax)
        if not equal_aspect:
            # ax.set_aspect('equal')
            ax.set_aspect('auto')
        ax.margins(0.1)
        return ax

    def babylon_data(self, merge_meshes=True):
        """
        Get babylonjs data.

        :return: Dictionary with babylon data.
        """

        babylon_data = {'meshes': [],
                        'lines': []}
        display_points = []
        for primitive in self.primitives:
            if hasattr(primitive, 'babylon_meshes'):
                babylon_data['meshes'].extend(primitive.babylon_meshes(merge_meshes=merge_meshes))
            elif hasattr(primitive, 'babylon_curves'):
                curves = primitive.babylon_curves()
                if curves:
                    babylon_data['lines'].append(curves)
            elif hasattr(primitive, 'babylon_data'):
                data = primitive.babylon_data(merge_meshes=merge_meshes)
                babylon_data['meshes'].extend(mesh for mesh in data.get("meshes"))
                babylon_data['lines'].extend(line for line in data.get("lines"))
            elif isinstance(primitive, design3d.Point3D):
                display_points.append(primitive)
        return helper_babylon_data(babylon_data, display_points)

    @classmethod
    def babylonjs_script(cls, babylon_data, title="", use_cdn=True, **kwargs):
        """
        Run babylonjs script.

        """
        if use_cdn:
            script = design3d.templates.BABYLON_UNPACKER_CDN_HEADER.substitute(title=title)
        else:
            script = design3d.templates.BABYLON_UNPACKER_EMBEDDED_HEADER.substitute(title=title)

        script += design3d.templates.BABYLON_UNPACKER_BODY_TEMPLATE.substitute(
            babylon_data=babylon_data)
        return script

    def babylonjs(
        self,
        page_name: str = None,
        use_cdn: bool = True,
        debug: bool = False,
        merge_meshes: bool = True,
        dark_mode: bool = False,
    ):
        """
        Generate and display an HTML file to visualize the 3D model using Babylon.js in a web browser.

        This method creates a 3D representation of the volume model using the Babylon.js framework.
        The method allows options for debugging, merging meshes, and toggling dark mode for the visualization.
        The resulting HTML file can either be a temporary file or a user-specified file.

        :param page_name: The name of the HTML file to be generated. If None, a temporary file is created.
        :type page_name: str, optional
        :param use_cdn: Flag to use CDN for loading Babylon.js resources. Defaults to True.
        :type use_cdn: bool
        :param debug: Enable debugging mode for more detailed console output in the browser. Defaults to False.
        :type debug: bool
        :param merge_meshes: Flag to chose to merge all the faces of each shell into a single mesh. Defaults to True.
            If False, shell are decomposed according to their faces in the Babylon.js scene nodes tree.
        :type merge_meshes: bool
        :param dark_mode: Enable dark mode for the HTML visualization. Defaults to False.
        :type dark_mode: bool

        :return: The file path of the generated HTML file.
        :rtype: str
        """
        babylon_data = self.babylon_data(merge_meshes=merge_meshes)
        babylon_data["dark_mode"] = 1 if dark_mode else 0
        script = self.babylonjs_script(babylon_data, title=self.name, use_cdn=use_cdn, debug=debug)
        if page_name is None:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as file:
                file.write(bytes(script, "utf8"))
            page_name = file.name
        else:
            if not page_name.endswith(".html"):
                page_name += ".html"
            with open(page_name, "w", encoding="utf-8") as file:
                file.write(script)

        webbrowser.open("file://" + os.path.realpath(page_name))

        return page_name

    def save_babylonjs_to_file(self, filename: str = None, use_cdn=True, debug=False, dark_mode=False):
        """Export a html file of the model."""
        babylon_data = self.babylon_data()
        babylon_data['dark_mode'] = 1 if dark_mode else 0
        script = self.babylonjs_script(babylon_data, use_cdn=use_cdn, debug=debug)
        if filename is None:
            with tempfile.NamedTemporaryFile(suffix=".html",
                                             delete=False) as file:
                file.write(bytes(script, 'utf8'))
                return file.name

        if not filename.endswith('.html'):
            filename += '.html'

        with open(filename, 'w', encoding='utf-8') as file:
            file.write(script)
        return filename

    def to_mesh_list(self):
        """
        Converts the volume model to a list Mesh3D object.

        :return: A list of Mesh3D objects representing the VolumeModel shells.
        """
        meshes = []

        for shell in self.get_shells():
            mesh = shell.triangulation()

            if len(mesh.triangles) > 0:
                meshes.append(mesh)
                meshes[-1].name = shell.name

        return meshes

    def to_mesh(self, merge_vertices: bool = True, merge_triangles: bool = True):
        """
        Converts the volume model to a Mesh3D object.

        :param merge_vertices: Flag to indicate whether to merge vertices of the shells meshes.
        :param merge_triangles: Flag to indicate whether to merge triangles of the shells meshes.

        :return: A Mesh3D of the VolumeModel
        """
        meshes = self.to_mesh_list()

        if not meshes:
            raise ValueError("VolumeModel has no primitive that can be converted to mesh.")

        merged_mesh = meshes[0]
        for mesh in meshes[1:]:
            merged_mesh = merged_mesh.merge(mesh, merge_vertices=merge_vertices, merge_triangles=merge_triangles)

        merged_mesh.name = self.name

        return merged_mesh

    def to_stl_model(self):
        """Converts the model into a stl object."""
        warnings.warn(
            "design3d.stl module is deprecated. Use design3d.display module and 'Mesh3D' class instead for STL export.",
            DeprecationWarning
        )

        mesh = self.to_mesh()

        # from design3d import stl
        stl = design3d.stl.Stl.from_display_mesh(mesh)
        return stl

    def to_stl(self, filepath: str):
        """Export a stl file of the model."""
        self.to_mesh().save_to_stl_file(filepath)

    def to_stl_stream(self, stream):
        """Converts the model into a stl stream file."""
        self.to_mesh().save_to_stl_stream(stream)
        return stream

    def to_step(self, filepath: str):
        """Export a step file of the model."""
        if not (filepath.endswith('.step') or filepath.endswith('.stp')):
            filepath += '.step'
        with open(filepath, 'w', encoding='utf-8') as file:
            self.to_step_stream(file)

    def to_step_stream(self, stream):
        """
        Export object CAD to given stream in STEP format.

        """
        step_content = STEP_HEADER.format(name=self.name,
                                          filename='',
                                          timestamp=datetime.now().isoformat(),
                                          version=design3d.__version__)
        current_id = 2

        for primitive in self.primitives:
            if primitive.__class__.__name__ in ('OpenShell3D', 'ClosedShell3D') or hasattr(primitive, "shell_faces"):
                primitive_content, primitive_id, _ = primitive.to_step_product(current_id)
            elif primitive.__class__.__name__ in ('Assembly', 'Compound'):
                primitive_content, primitive_id, _ = primitive.to_step(current_id)
            else:
                continue

            step_content += primitive_content
            current_id = primitive_id

        step_content += STEP_FOOTER

        stream.write(step_content)

    def design3d_volume_model(self):
        """
        Method needed due to PhysicalObject inheritance.
        """
        return self

    def get_geo_lines(self):
        """
        Gets the lines that define a VolumeModel geometry in a .geo file.

        :return: A list of lines that describe the geometry
        :rtype: List[str]

        """

        update_data = {'point_account': 0,
                       'line_account': 0,
                       'line_loop_account': 0,
                       'surface_account': 0,
                       'surface_loop_account': 0}

        lines = []
        volume = 0
        for primitive in self.primitives:
            if isinstance(primitive, design3d.shells.ClosedShell3D):
                volume += 1
                lines_primitives, update_data = primitive.get_geo_lines(update_data)
                lines.extend(lines_primitives)
                surface_loop = ((lines[-1].split('('))[1].split(')')[0])
                lines.append('Volume(' + str(volume) + ') = {' + surface_loop + '};')
            elif isinstance(primitive, design3d.shells.OpenShell3D):
                lines_primitives, update_data = primitive.get_geo_lines(update_data)
                lines.extend(lines_primitives)

        return lines

    def get_mesh_lines(self, factor: float, **kwargs):
        """
        Gets the lines that define mesh parameters for a VolumeModel, to be added to a .geo file.

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

        for element in [('curvature_mesh_size', 0), ('min_points', None), ('initial_mesh_size', 5)]:
            if element[0] not in kwargs:
                kwargs[element[0]] = element[1]

        field_num = 1
        field_nums = []
        lines = []

        lines.append('Mesh.CharacteristicLengthMin = 0;')
        lines.append('Mesh.CharacteristicLengthMax = 1e+22;')
        lines.append('Geometry.Tolerance = 1e-5;')
        lines.append('Mesh.AngleToleranceFacetOverlap = 0.01;')
        lines.append('General.Verbosity = 0;')

        for i, primitive in enumerate(self.primitives):
            if isinstance(primitive, design3d.shells.ClosedShell3D):
                bbx = primitive.bounding_box
                dim1, dim2, dim3 = (bbx.xmax - bbx.xmin), (bbx.ymax - bbx.ymin), (bbx.zmax - bbx.zmin)
                volume = dim1 * dim2 * dim3

                if factor == 0:
                    factor = 1e-3

                size = ((volume ** (1. / 3.)) / kwargs['initial_mesh_size']) * factor

                if kwargs['min_points']:
                    lines.extend(primitive.get_mesh_lines_with_transfinite_curves(min_points=kwargs['min_points'],
                                                                                  size=size))

                lines.append('Field[' + str(field_num) + '] = MathEval;')
                lines.append('Field[' + str(field_num) + '].F = "' + str(size) + '";')

                lines.append('Field[' + str(field_num + 1) + '] = Restrict;')
                lines.append('Field[' + str(field_num + 1) + '].InField = ' + str(field_num) + ';')
                lines.append('Field[' + str(field_num + 1) + '].VolumesList = {' + str(i + 1) + '};')
                field_nums.append(field_num + 1)
                field_num += 2

            elif isinstance(primitive, design3d.shells.OpenShell3D):
                continue

        lines.append('Field[' + str(field_num) + '] = MinAniso;')
        lines.append('Field[' + str(field_num) + '].FieldsList = {' + str(field_nums)[1:-1] + '};')
        lines.append('Background Field = ' + str(field_num) + ';')

        lines.append('Mesh.MeshSizeFromCurvature = ' + str(kwargs['curvature_mesh_size']) + ';')

        lines.append('Coherence;')

        return lines

    def to_geo_stream(self, stream,
                      factor: float, **kwargs):
        """
        Gets the .geo file for the VolumeModel.

        :param file_name: The geo. file name
        :type file_name: str
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

        lines = self.get_geo_lines()
        lines.extend(self.get_mesh_lines(factor,
                                         curvature_mesh_size=kwargs['curvature_mesh_size'],
                                         min_points=kwargs['min_points'],
                                         initial_mesh_size=kwargs['initial_mesh_size']))

        content = ''
        for line in lines:
            content += line + '\n'

        stream.write(content)

    def to_geo(self, file_name: str = '',
               factor: float = 0.5, **kwargs):
        # curvature_mesh_size: int = 0,
        # min_points: int = None,
        # initial_mesh_size: float = 5):
        """
        Gets the .geo file for the VolumeModel.

        :param file_name: The geo. file name
        :type file_name: str
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

        if not (file_name.endswith('.geo') or file_name.endswith('.geo')):
            file_name += '.geo'

        with open(file_name, mode='w', encoding='utf-8') as file:

            self.to_geo_stream(file, factor,
                               curvature_mesh_size=kwargs['curvature_mesh_size'],
                               min_points=kwargs['min_points'],
                               initial_mesh_size=kwargs['initial_mesh_size'])

        # for element in [('curvature_mesh_size', 0), ('min_points', None), ('initial_mesh_size', 5)]:
        #     if element[0] not in kwargs:
        #         kwargs[element[0]] = element[1]

        # # try:
        # #     curvature_mesh_size = kwargs['curvature_mesh_size']
        # # except KeyError:
        # #     curvature_mesh_size = 0
        # # try:
        # #     min_points = kwargs['min_points']
        # # except KeyError:
        # #     min_points = None
        # # try:
        # #     initial_mesh_size = kwargs['initial_mesh_size']
        # # except KeyError:
        # #     initial_mesh_size = 5

        # lines = self.get_geo_lines()
        # lines.extend(self.get_mesh_lines(factor,
        #                                   curvature_mesh_size=kwargs['curvature_mesh_size'],
        #                                   min_points=kwargs['min_points'],
        #                                   initial_mesh_size=kwargs['initial_mesh_size']))
        # with open(file_name + '.geo', 'w', encoding="utf-8") as file:
        #     for line in lines:
        #         file.write(line)
        #         file.write('\n')
        # file.close()

    def to_geo_with_stl(self, file_name: str,
                        factor: float, **kwargs):
        # curvature_mesh_size: int = 0,
        # min_points: int = None,
        # initial_mesh_size: float = 5):
        """
        Gets the .geo file for the VolumeModel, with saving each closed shell in a stl file.

        :param file_name: The geo. file name
        :type file_name: str
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

        # try:
        #     curvature_mesh_size = kwargs['curvature_mesh_size']
        # except KeyError:
        #     curvature_mesh_size = 0
        # try:
        #     min_points = kwargs['min_points']
        # except KeyError:
        #     min_points = None
        # try:
        #     initial_mesh_size = kwargs['initial_mesh_size']
        # except KeyError:
        #     initial_mesh_size = 5

        lines = self.get_geo_lines()
        lines.extend(self.get_mesh_lines(factor,
                                         curvature_mesh_size=kwargs['curvature_mesh_size'],
                                         min_points=kwargs['min_points'],
                                         initial_mesh_size=kwargs['initial_mesh_size']))

        contours, faces_account = [], 0
        surfaces = []
        for i, primitive in enumerate(self.primitives):
            if i == 0:
                surfaces.append(list(range(1, 1 + len(primitive.faces))))
                face_contours = [face.outer_contour3d for face in primitive.faces]
                contours.append(face_contours)
                lines.append('Mesh 2;')
                lines.append('Physical Surface(' + str(i + 1) + ') = {' + str(surfaces[i])[1:-1] + '};')
                lines.append('Save "' + file_name + '.stl" ;')
                faces_account += len(primitive.faces) + 1
            else:
                surfaces.append(list(range(faces_account, faces_account + len(primitive.faces))))
                face_contours = [face.outer_contour3d for face in primitive.faces]
                surfaces = self.update_surfaces_list(face_contours, surfaces, contours, i)
                # for k, face_c in enumerate(face_contours):
                #     for l, contour_l in enumerate(contours):
                #         for c, contour in enumerate(contour_l):
                #             if face_c.is_superposing(contour):
                #                 surfaces[i][k] = surfaces[l][c]
                #                 continue
                lines.append('Mesh 2;')
                lines.append('Physical Surface(' + str(i + 1) + ') = {' + str(surfaces[i])[1:-1] + '};')
                lines.append('Save "' + file_name + '.stl" ;')
                faces_account += len(primitive.faces) + 1
                contours.append(face_contours)

        return lines

    @staticmethod
    def update_surfaces_list(face_contours, surfaces, contours, i):
        """Update surfaces list."""
        for k_f, face_c in enumerate(face_contours):
            for l_c, contour_l in enumerate(contours):
                for c_c, contour in enumerate(contour_l):
                    if face_c.is_superposing(contour):
                        surfaces[i][k_f] = surfaces[l_c][c_c]
                        continue
        return surfaces

    def to_msh(self, mesh_dimension: int, factor: float,
               mesh_order: int = 1, file_name: str = '', **kwargs):
        # curvature_mesh_size: int = 0,
        # min_points: int = None,
        # initial_mesh_size: float = 5):
        """
        Gets .msh file for the VolumeModel generated by gmsh.

        :param file_name: The msh. file name
        :type file_name: str
        :param mesh_dimension: The mesh dimension (1: 1D-Edge, 2: 2D-Triangle, 3D-Tetrahedra)
        :type mesh_dimension: int
        :param mesh_order: The msh order (1: linear, 2: 2nd order)
        :type mesh_order: int
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

        # try:
        #     curvature_mesh_size = kwargs['curvature_mesh_size']
        # except KeyError:
        #     curvature_mesh_size = 0
        # try:
        #     min_points = kwargs['min_points']
        # except KeyError:
        #     min_points = None
        # try:
        #     initial_mesh_size = kwargs['initial_mesh_size']
        # except KeyError:
        #     initial_mesh_size = 5

        if file_name == '':
            with tempfile.NamedTemporaryFile(delete=False) as file:
                file_name = file.name

        self.to_geo(file_name=file_name,
                    factor=factor,
                    curvature_mesh_size=kwargs['curvature_mesh_size'],
                    min_points=kwargs['min_points'],
                    initial_mesh_size=kwargs['initial_mesh_size'])

        self.generate_msh_file(file_name, mesh_dimension, mesh_order)

        # gmsh.initialize()
        # gmsh.open(file_name + ".geo")

        # gmsh.model.geo.synchronize()
        # gmsh.model.mesh.generate(mesh_dimension)

        # gmsh.write(file_name + ".msh")

        # gmsh.finalize()

    @staticmethod
    def generate_msh_file(file_name, mesh_dimension, mesh_order):
        """
        Generates a mesh written in a .msh file using GMSH library.

        :param file_name: DESCRIPTION
        :type file_name: TYPE
        :param mesh_dimension: DESCRIPTION
        :type mesh_dimension: TYPE
        :param mesh_order: The msh order (1: linear, 2: 2nd order)
        :type mesh_order: int

        :return: DESCRIPTION
        :rtype: TYPE

        """

        gmsh.initialize()
        gmsh.open(file_name + ".geo")

        gmsh.model.geo.synchronize()
        gmsh.model.mesh.generate(mesh_dimension)
        gmsh.model.mesh.setOrder(mesh_order)

        gmsh.write(file_name + ".msh")

        gmsh.finalize()

    def to_msh_stream(self, mesh_dimension: int,
                      factor: float, stream,
                      mesh_order: int = 1,
                      file_name: str = '', **kwargs):
        """
        Gets .msh file for the VolumeModel generated by gmsh.

        :param file_name: The msh. file name
        :type file_name: str
        :param mesh_dimension: The mesh dimension (1: 1D-Edge, 2: 2D-Triangle, 3D-Tetrahedra)
        :type mesh_dimension: int
        :param mesh_order: The msh order (1: linear, 2: 2nd order)
        :type mesh_order: int

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

        if file_name == '':
            with tempfile.NamedTemporaryFile(delete=False) as file:
                file_name = file.name

        self.to_geo(file_name=file_name,
                    factor=factor,
                    curvature_mesh_size=kwargs['curvature_mesh_size'],
                    min_points=kwargs['min_points'],
                    initial_mesh_size=kwargs['initial_mesh_size'])

        gmsh.initialize()
        gmsh.open(file_name + ".geo")

        gmsh.model.geo.synchronize()
        gmsh.model.mesh.generate(mesh_dimension)
        gmsh.model.mesh.setOrder(mesh_order)

        lines = []
        lines.append('$MeshFormat')
        lines.append('4.1 0 8')
        lines.append('$EndMeshFormat')

        lines.extend(self.get_nodes_lines(gmsh))
        lines.extend(self.get_elements_lines(gmsh))

        content = ''
        for line in lines:
            content += line + '\n'

        stream.write(content)

        # gmsh.finalize()

    def to_msh_file(self, mesh_dimension: int,
                    factor: float, stream,
                    mesh_order: int = 1, file_name: str = '', **kwargs):
        """ Convert and write model to a .msh file. """

        for element in [('curvature_mesh_size', 0), ('min_points', None), ('initial_mesh_size', 5)]:
            if element[0] not in kwargs:
                kwargs[element[0]] = element[1]

        if file_name == '':
            with tempfile.NamedTemporaryFile(delete=False) as file:
                file_name = file.name

        with open(file_name, mode='w', encoding='utf-8') as file:
            self.to_msh_stream(mesh_dimension=mesh_dimension,
                               factor=factor, file_name=file,
                               mesh_order=mesh_order,
                               stream=stream,
                               curvature_mesh_size=kwargs['curvature_mesh_size'],
                               min_points=kwargs['min_points'],
                               initial_mesh_size=kwargs['initial_mesh_size'])

    @staticmethod
    def get_nodes_lines(gmsh_model):
        """Get nodes lines."""
        lines_nodes = []
        lines_nodes.append('$Nodes')

        tag = None
        entities = gmsh_model.model.getEntities()
        for dim, tag in entities:
            node_tags, node_coords, _ = gmsh_model.model.mesh.getNodes(dim, tag)

            lines_nodes.append(str(dim) + ' ' + str(tag) + ' ' + '0 ' + str(len(node_tags)))
            for tag in node_tags:
                lines_nodes.append(str(tag))
            for n in range(0, len(node_coords), 3):
                lines_nodes.append(str(node_coords[n:n + 3])[1:-1])

        lines_nodes.insert(1, str(len(entities)) + ' ' + str(tag) + ' 1 ' + str(tag))
        lines_nodes.append('$EndNodes')

        return lines_nodes

    @staticmethod
    def get_elements_lines(gmsh_model):
        """
        Helper function to export the volume model into gmsh format.
        """
        lines_elements = []
        lines_elements.append('$Elements')

        entities = gmsh_model.model.getEntities()
        for dim, tag in entities:
            elem_types, elem_tags, elem_node_tags = gmsh_model.model.mesh.getElements(dim, tag)

            lines_elements.append(str(dim) + ' ' + str(tag) + ' ' + str(elem_types[0]) + ' ' + str(len(elem_tags[0])))
            range_list = int(len(elem_node_tags[0]) / len(elem_tags[0]))
            for n in range(0, len(elem_node_tags[0]), range_list):
                lines_elements.append(str(elem_tags[0][int(n / range_list)]) + ' ' +
                                      str(elem_node_tags[0][n:n + range_list])[1:-1])

        tag = str(elem_tags[0][int(n / range_list)])
        lines_elements.insert(1, str(len(entities)) + ' ' + tag + ' 1 ' + tag)
        lines_elements.append('$EndElements')

        return lines_elements

    def get_shells(self):
        """
        Dissociates all the assemblies to get a list of shells only.

        :return: A list of closed shells
        :rtype: List[OpenShell3D]
        """

        list_shells = []

        def unpack_assembly(assembly):
            for prim in assembly.primitives:
                if prim.__class__.__name__ in ('Assembly', "Compound"):
                    unpack_assembly(prim)
                elif hasattr(prim, "faces") or hasattr(prim, "shell_faces"):
                    list_shells.append(prim)

        for primitive in self.primitives:
            if primitive.__class__.__name__ in ('Assembly', "Compound"):
                unpack_assembly(primitive)
            elif hasattr(primitive, "faces") or hasattr(primitive, "shell_faces"):
                list_shells.append(primitive)

        return list_shells


class MovingVolumeModel(VolumeModel):
    """
    A volume model with possibility to declare time steps at which the primitives are positioned with frames.

    """

    def __init__(self, primitives: List[Primitive3D], step_frames: List[List[design3d.Frame3D]], name: str = ''):
        VolumeModel.__init__(self, primitives=primitives, name=name)
        self.step_frames = step_frames

        if not self.is_consistent():
            raise ConsistencyError

    def is_consistent(self):
        """ Check if the number of frames for each step corresponds to the number of primitives of the model. """
        n_primitives = len(self.primitives)
        for frames in self.step_frames:
            if len(frames) != n_primitives:
                return False
        return True

    def step_volume_model(self, istep: int):
        """
        Moves the volume model with a list of local frames.
        """
        primitives = []
        for primitive, frame in zip(self.primitives, self.step_frames[istep]):
            primitives.append(
                primitive.frame_mapping(frame, side='old'))
        return VolumeModel(primitives)

    def babylon_data(self, merge_meshes=True):
        """
        Get babylonjs data.

        :return: Dictionary with babylonjs data.
        """
        meshes = []
        primitives_to_meshes = []
        for i_prim, primitive in enumerate(self.primitives):
            if hasattr(primitive, 'babylon_meshes'):
                meshes.extend(primitive.babylon_meshes(merge_meshes=merge_meshes))
                primitives_to_meshes.append(i_prim)

        # Compute max length in each direction
        all_positions = []
        for mesh in meshes:
            positions = mesh["positions"]
            all_positions.extend(positions)

        # Convert to a NumPy array and reshape
        positions_array = np.array(all_positions).reshape(-1, 3)

        # Compute min and max for each dimension
        min_vals = positions_array.min(axis=0)
        max_vals = positions_array.max(axis=0)

        # Calculate max length of the bounding box
        max_length = np.max(max_vals - min_vals)

        # Calculate center point of the bounding box
        center = (0.5 * (min_vals + max_vals)).tolist()

        steps = []
        for istep, frames in enumerate(self.step_frames):

            # step_positions = []
            # step_orientations = []
            step = {'time': istep}
            for iframe, frame in enumerate(frames):
                if iframe in primitives_to_meshes:
                    imesh = primitives_to_meshes.index(iframe)
                    step[imesh] = {}
                    step[imesh]['position'] = list(round(frame.origin, 6))
                    step[imesh]['orientations'] = [list(round(frame.u, 6)),
                                                   list(round(frame.v, 6)),
                                                   list(round(frame.w, 6))]

            steps.append(step)

        babylon_data = {'meshes': meshes,
                        'max_length': max_length,
                        'center': center,
                        'steps': steps}
        return babylon_data
