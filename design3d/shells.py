"""design3d shells module."""
import math
import random
import warnings
from itertools import chain, product
from typing import Iterable, List, Tuple, Union

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pyfqmr
from numpy.typing import NDArray
from trimesh import Trimesh

import design3d.core
import design3d.core_compiled
import design3d.faces
import design3d.geometry
from design3d import curves, display, edges, surfaces, wires
from design3d.core import edge_in_list, get_edge_index_in_list, get_point_index_in_list, point_in_list
from design3d.utils.step_writer import geometric_context_writer, product_writer, step_ids_to_str

# pylint: disable=unused-argument


def union_list_of_shells(list_shells, abs_tol: float = 1e-6):
    """
    Perform union operations with all shells from a list, until all groups of adjacent shells are merged.

    :param list_shells: A list of shells.
    :param abs_tol: tolerance.
    :return: A list of merged shells
    """
    shells = []
    union_shells = [list_shells.pop(0)]
    len_previous_shells_list = len(list_shells)
    while True:
        if not list_shells and union_shells:
            list_shells = union_shells[:]
            len_previous_shells_list = len(list_shells)
            union_shells = [list_shells.pop(0)]

        for i, union_shell in enumerate(union_shells[:]):
            for j, octant_box in enumerate(list_shells[:]):
                union = union_shell.union(octant_box, abs_tol)
                if len(union) != 2:
                    union_shells.pop(i)
                    union[0].merge_faces()
                    union_shells.insert(0, union[0])
                    list_shells.pop(j)
                    break
                if len(list_shells) != len_previous_shells_list - 1:
                    union_shells.insert(0, union[1])
                    list_shells.pop(j)
                    break
            else:
                shells.append(union_shell)
                union_shells.pop(i)
                if not union_shells and list_shells:
                    union_shells = [list_shells.pop(0)]
                break
            break
        if not union_shells:
            break
    return shells


class Shell3D(design3d.core.CompositePrimitive3D):
    """
    A 3D shell composed of multiple faces.

    This class represents a 3D shell, which is a collection of connected
    faces with volume. It is a subclass of the `CompositePrimitive3D` class
    and inherits all of its attributes and methods.


    :param faces: The faces of the shell.
    :type faces: List[`Face3D`]
    :param color: The color of the shell.
    :type color: Tuple[float, float, float]
    :param alpha: The transparency of the shell, should be a value in the interval (0, 1).
    :type alpha: float
    :param name: The name of the shell.
    :type name: str
    :param bounding_box: The bounding box of the shell.
    :type bounding_box: :class:`design3d.core.BoundingBox`
    """
    STEP_FUNCTION = None

    def __init__(self, faces: List[design3d.faces.Face3D],
                 color: Tuple[float, float, float] = None,
                 alpha: float = 1.,
                 name: str = '',
                 bounding_box: design3d.core.BoundingBox = None,
                 reference_path: str = design3d.PATH_ROOT):

        self.faces = faces
        if not color:
            self.color = design3d.core.DEFAULT_COLOR
        else:
            self.color = color
        self.alpha = alpha
        self._bbox = None
        if bounding_box:
            self._bbox = bounding_box

        self._faces_graph = None
        self._vertices_graph = None
        self._vertices_points = None
        self._shell_octree_decomposition = None

        design3d.core.CompositePrimitive3D.__init__(self,
                                                   primitives=faces, color=color, alpha=alpha,
                                                   reference_path=reference_path, name=name)

    def _data_hash(self):
        return len(self.faces)  # sum(face._data_hash() for face in self.faces)

    def _data_eq(self, other_object):
        if other_object.__class__.__name__ != self.__class__.__name__:
            return False
        for face1, face2 in zip(self.faces, other_object.faces):
            if not face1._data_eq(face2):
                return False
        return True

    def __eq__(self, other_face):
        if not self.__class__ == other_face.__class__:
            return False
        if len(self.faces) != len(other_face.faces):
            return False
        if all(face in self.faces for face in other_face.faces):
            return True
        return False

    def __hash__(self):
        return hash((self.__class__.__name__, tuple(self.faces)))

    @staticmethod
    def _helper_getter_vertices_points(faces):
        """Helper method to get shells faces vertices."""
        vertices_points = []
        for face in faces:
            for contour in [face.outer_contour3d] + face.inner_contours3d:
                for edge in contour.primitives:
                    if not edge.start.in_list(vertices_points):
                        vertices_points.append(edge.start)
                    if not edge.end.in_list(vertices_points):
                        vertices_points.append(edge.end)
        return vertices_points

    @property
    def vertices_points(self):
        """Gets the shell's vertices points. """
        if self._vertices_points is None:
            self._vertices_points = self._helper_getter_vertices_points(self.faces)
        return self._vertices_points

    @property
    def vertices_graph(self):
        """
        Gets the shells faces graph using networkx.

        :return: return a networkx graph for a shell faces' vertices.
        """
        if not self._faces_graph:
            vertices_graph = nx.Graph()
            for face in self.faces:
                for edge in face.outer_contour3d.primitives:
                    edge_start_index = design3d.core.get_point_index_in_list(edge.start, self.vertices_points)
                    edge_end_index = design3d.core.get_point_index_in_list(edge.end, self.vertices_points)
                    vertices_graph.add_edge(edge_start_index, edge_end_index, edge=edge)
            self._vertices_graph = vertices_graph
        return self._vertices_graph

    @staticmethod
    def _faces_graph_search_bridges(faces, graph, components, face_vertices, vertices_points):
        """
        Search for neighboring faces in the connected components to fix the graph.

        To make the shell faces' topology graph, we search faces that share the same vertices.
        Sometimes, in very specific cases, it can occur that two faces are neighbors of each other
        but their vertices aren't coincident.

        This method tries to find those cases, by searching bridges, which are edges that connect two components.
        The search is performed by checking if any vertices of one face in one component lie on the contours of
        another face in the other component. If such a connection is found, the two faces are considered neighbors.
        Once a connection is found between a pair of components we break the execution and proceed to
        the next pair of components. This behavior, in the average, avoids the need to verify all possible combinations

        :param graph: The graph representing the faces' topology.
        :type graph: nx.Graph
        :param components: A list of sets, where each set contains the indices of faces in a connected component.
        :type components: list
        :param face_vertices: A dictionary mapping face indices to their corresponding vertex indices.
        :type face_vertices: dict
        :param vertices_points: A list containing all faces vertices points.
        :type vertices_points: list[Point3D].
        :return: The updated graph with no disconnected components.
        """
        stack = components.copy()
        found = False

        def check_faces(face, other_face_id):
            for point_id in face_vertices[other_face_id]:
                point = vertices_points[point_id]
                if face.outer_contour3d.point_belongs(point):
                    return True
                if face.inner_contours3d:
                    for inner_contour in face.inner_contours3d:
                        if inner_contour.point_belongs(point):
                            return True
            return False

        while stack:
            group = stack.pop(0)
            for face_id_i in group:
                face_i = faces[face_id_i]
                for other_group in stack:
                    for face_id_j in other_group:
                        if check_faces(face_i, face_id_j):
                            found = True
                            graph.add_edge(face_id_i, face_id_j)
                            for face_id_k in graph.neighbors(face_id_j):
                                if check_faces(face_i, face_id_k):
                                    graph.add_edge(face_id_i, face_id_k)
                        if found:
                            break
        return graph

    @staticmethod
    def _helper_create_faces_graph(faces, vertices_points=None, verify_connected_components=True):
        if vertices_points is None:
            vertices_points = Shell3D._helper_getter_vertices_points(faces)

        graph = nx.Graph()
        vertice_faces = {}
        face_vertices = {}

        for face_index, face in enumerate(faces):
            face_contour_primitives = face.outer_contour3d.primitives[:]
            for inner_contour in face.inner_contours3d:
                face_contour_primitives.extend(inner_contour.primitives)
            for edge in face_contour_primitives:
                start_index = design3d.core.get_point_index_in_list(edge.start, vertices_points)
                vertice_faces.setdefault(start_index, set()).add(face_index)
                face_vertices.setdefault(face_index, set()).add(start_index)

        for i, _ in enumerate(faces):
            face_i_vertices = face_vertices[i]
            for vertice in face_i_vertices:
                connected_faces = vertice_faces[vertice]
                connected_faces.discard(i)
                for j in connected_faces:
                    graph.add_edge(i, j)

        if verify_connected_components:
            components = list(nx.connected_components(graph))
            if len(components) > 1:
                graph = Shell3D._faces_graph_search_bridges(faces, graph, components, face_vertices, vertices_points)
        return graph

    def faces_graph(self, verify_connected_components=True):
        """
        Gets the shells faces topology graph using networkx.

        :return: return a networkx graph for a shell faces.
        """
        if not self._faces_graph:
            self._faces_graph = self._helper_create_faces_graph(
                self.faces, self.vertices_points, verify_connected_components)
        return self._faces_graph

    def to_dict(self, *args, **kwargs):
        """
        Serializes a 3-dimensional open shell into a dictionary.

        This method does not use pointers for faces as it has no sense
        to have duplicate faces.

        :return: A serialized version of the OpenShell3D
        :rtype: dict

        . see also::
            How `serialization and de-serialization`_ works in dessia_common

        . _serialization and deserialization:
        https://documentation.dessia.tech/dessia_common/customizing.html#overloading-the-dict-to-object-method

        """
        dict_ = {}
        dict_.update({'color': self.color,
                      'alpha': self.alpha,
                      'faces': [f.to_dict(use_pointers=False) for f in self.faces]})
        if self._bbox:
            dict_['bounding_box'] = self._bbox.to_dict()

        return dict_

    @classmethod
    def from_step(cls, arguments, object_dict, **kwargs):
        """
        Converts a step primitive to an Open Shell 3D.

        :param arguments: The arguments of the step primitive.
        :type arguments: list
        :param object_dict: The dictionary containing all the step primitives
            that have already been instantiated.
        :type object_dict: dict
        :return: The corresponding OpenShell3D object.
        :rtype: :class:`design3d.faces.OpenShell3D`
        """
        # Quick fix:
        # ----------------------------------
        name = arguments[0][1:-1]
        if isinstance(arguments[-1], int):
            step_product = object_dict[arguments[-1]]
            name = step_product[1:-1]
        # ----------------------------------
        faces = [object_dict[int(face[1:])] for face in arguments[1] if object_dict[int(face[1:])]]
        if not faces:
            return None
        return cls(faces, name=name)

    def to_step(self, current_id):
        """
        Creates step file entities from design3d objects.
        """
        step_content = ''
        faces_content = ''
        face_ids = []

        for face in self.faces:
            if isinstance(face, (design3d.faces.Face3D, surfaces.Surface3D)):
                face_content, face_sub_ids = face.to_step(current_id)
            else:
                face_content, face_sub_ids = face.to_step(current_id)
                face_sub_ids = [face_sub_ids]
            faces_content += face_content
            face_ids.extend(face_sub_ids)
            current_id = max(face_sub_ids)
        step_content += faces_content

        shell_id = current_id + 1

        step_content += f"#{shell_id} = {self.STEP_FUNCTION}('{self.name}'," \
                        f"({step_ids_to_str(face_ids)}));\n"
        manifold_id = shell_id + 1
        if self.STEP_FUNCTION == "CLOSED_SHELL":
            step_content += f"#{manifold_id} = MANIFOLD_SOLID_BREP('{self.name}',#{shell_id});\n"
        else:
            step_content += f"#{manifold_id} = SHELL_BASED_SURFACE_MODEL('{self.name}',(#{shell_id}));\n"

        return step_content, manifold_id

    def to_step_product(self, current_id):
        """
        Creates step file entities from design3d objects.
        """
        step_content = ''
        faces_content = ''
        face_ids = []

        product_content, shape_definition_repr_id = product_writer(current_id, self.name)
        shape_representation_id = shape_definition_repr_id + 1
        product_id = shape_definition_repr_id - 4
        product_definition_id = shape_definition_repr_id - 2
        step_content += product_content

        brep_id = shape_representation_id
        frame_content, frame_id = design3d.OXYZ.to_step(brep_id)
        manifold_id = frame_id + 1
        shell_id = manifold_id + 1
        current_id = shell_id
        for face in self.faces:
            if isinstance(face, (design3d.faces.Face3D, surfaces.Surface3D)):
                face_content, face_sub_ids = face.to_step(current_id)
            else:
                face_content, face_sub_ids = face.to_step(current_id)
                face_sub_ids = [face_sub_ids]
            faces_content += face_content
            face_ids.extend(face_sub_ids)
            current_id = max(face_sub_ids)

        geometric_context_content, geometric_representation_context_id = geometric_context_writer(current_id)

        if self.STEP_FUNCTION == "CLOSED_SHELL":
            step_content += f"#{brep_id} = ADVANCED_BREP_SHAPE_REPRESENTATION('',(#{frame_id},#{manifold_id})," \
                            f"#{geometric_representation_context_id});\n"
            step_content += frame_content
            step_content += f"#{manifold_id} = MANIFOLD_SOLID_BREP('{self.name}',#{shell_id});\n"
        else:
            step_content += f"#{brep_id} = MANIFOLD_SURFACE_SHAPE_REPRESENTATION('',(#{frame_id},#{manifold_id})," \
                            f"#{geometric_representation_context_id});\n"
            step_content += frame_content
            step_content += f"#{manifold_id} = SHELL_BASED_SURFACE_MODEL('{self.name}',(#{shell_id}));\n"

        step_content += f"#{shell_id} = {self.STEP_FUNCTION}('{self.name}'," \
                        f"({step_ids_to_str(face_ids)}));\n"
        step_content += faces_content

        step_content += geometric_context_content

        product_related_category = geometric_representation_context_id + 1
        step_content += f"#{product_related_category} = PRODUCT_RELATED_PRODUCT_CATEGORY(" \
                        f"'part',$,(#{product_id}));\n"
        draughting_id = product_related_category + 1
        step_content += f"#{draughting_id} = DRAUGHTING_PRE_DEFINED_CURVE_FONT('continuous');\n"
        color_id = draughting_id + 1
        primitive_color = (1, 1, 1)
        if hasattr(self, 'color') and self.color is not None:
            primitive_color = self.color
        step_content += f"#{color_id} = COLOUR_RGB('',{round(float(primitive_color[0]), 4)}," \
                        f"{round(float(primitive_color[1]), 4)},{round(float(primitive_color[2]), 4)});\n"

        curve_style_id = color_id + 1
        step_content += f"#{curve_style_id} = CURVE_STYLE('',#{draughting_id}," \
                        f"POSITIVE_LENGTH_MEASURE(0.1),#{color_id});\n"

        fill_area_color_id = curve_style_id + 1
        step_content += f"#{fill_area_color_id} = FILL_AREA_STYLE_COLOUR('',#{color_id});\n"

        fill_area_id = fill_area_color_id + 1
        step_content += f"#{fill_area_id} = FILL_AREA_STYLE('',#{fill_area_color_id});\n"

        suface_fill_area_id = fill_area_id + 1
        step_content += f"#{suface_fill_area_id} = SURFACE_STYLE_FILL_AREA(#{fill_area_id});\n"

        suface_side_style_id = suface_fill_area_id + 1
        step_content += f"#{suface_side_style_id} = SURFACE_SIDE_STYLE('',(#{suface_fill_area_id}));\n"

        suface_style_usage_id = suface_side_style_id + 1
        step_content += f"#{suface_style_usage_id} = SURFACE_STYLE_USAGE(.BOTH.,#{suface_side_style_id});\n"

        presentation_style_id = suface_style_usage_id + 1

        step_content += f"#{presentation_style_id} = PRESENTATION_STYLE_ASSIGNMENT((#{suface_style_usage_id}," \
                        f"#{curve_style_id}));\n"

        styled_item_id = presentation_style_id + 1
        if self.__class__.__name__ == 'OpenShell3D':
            for face_id in face_ids:
                step_content += f"#{styled_item_id} = STYLED_ITEM('color',(#{presentation_style_id})," \
                                f"#{face_id});\n"
                styled_item_id += 1
            styled_item_id -= 1
        else:
            step_content += f"#{styled_item_id} = STYLED_ITEM('color',(#{presentation_style_id})," \
                            f"#{manifold_id});\n"
        mechanical_design_id = styled_item_id + 1
        step_content += f"#{mechanical_design_id} =" \
                        f" MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION(" \
                        f"'',(#{styled_item_id}),#{geometric_representation_context_id});\n"
        current_id = mechanical_design_id

        return step_content, current_id, [brep_id, product_definition_id]

    def to_step_face_ids(self, current_id):
        """
        Creates step file entities from design3d objects.
        """
        step_content = ''
        face_ids = []
        for face in self.faces:
            if isinstance(face, design3d.faces.Face3D):
                face_content, face_sub_ids = face.to_step(current_id)
            else:
                face_content, face_sub_ids = face.to_step(current_id)
                face_sub_ids = [face_sub_ids]
            step_content += face_content
            face_ids.extend(face_sub_ids)
            current_id = max(face_sub_ids) + 1

        shell_id = current_id
        step_content += f"#{current_id} = {self.STEP_FUNCTION}('{self.name}'," \
                        f"({design3d.core.step_ids_to_str(face_ids)}));\n"
        manifold_id = shell_id + 1
        step_content += f"#{manifold_id} = SHELL_BASED_SURFACE_MODEL('{self.name}',(#{shell_id}));\n"

        frame_content, frame_id = design3d.OXYZ.to_step(manifold_id + 1)
        step_content += frame_content
        brep_id = frame_id + 1
        step_content += f"#{brep_id} = MANIFOLD_SURFACE_SHAPE_REPRESENTATION('',(#{frame_id},#{manifold_id}),#7);\n"

        return step_content, brep_id, face_ids

    def rotation(self, center: design3d.Point3D, axis: design3d.Vector3D,
                 angle: float):
        """
        Open Shell 3D / Closed Shell 3D rotation.

        :param center: rotation center.
        :param axis: rotation axis.
        :param angle: angle rotation.
        :return: a new rotated OpenShell3D.
        """
        new_faces = [face.rotation(center, axis, angle) for face
                     in self.faces]
        return self.__class__(new_faces, color=self.color, alpha=self.alpha, name=self.name)

    def translation(self, offset: design3d.Vector3D):
        """
        Shell3D translation.

        :param offset: translation vector.
        :return: A new translated Open Shell 3D.
        """
        new_faces = [face.translation(offset) for face in
                     self.faces]
        return self.__class__(new_faces, color=self.color, alpha=self.alpha,
                              name=self.name)

    def frame_mapping(self, frame: design3d.Frame3D, side: str):
        """
        Changes frame_mapping and return a new OpenShell3D.

        side = 'old' or 'new'.
        """
        new_faces = [face.frame_mapping(frame, side) for face in
                     self.faces]
        return self.__class__(new_faces, name=self.name)

    def copy(self, deep=True, memo=None):
        """
        Copy of Shell3D.

        :return: return a copy a shell 3D.
        """
        new_faces = [face.copy(deep=deep, memo=memo) for face in self.faces]
        return self.__class__(new_faces, color=self.color, alpha=self.alpha,
                              name=self.name)

    @property
    def bounding_box(self):
        """
        Returns the boundary box.

        """
        if not self._bbox:
            self._bbox = self.get_bounding_box()
        return self._bbox

    @bounding_box.setter
    def bounding_box(self, new_bounding_box):
        self._bbox = new_bounding_box

    def get_bounding_box(self):
        """Gets the Shell bounding box."""
        bounding_boxes = []
        for face in self.faces:
            if face.outer_contour3d.primitives:
                bounding_boxes.append(face.bounding_box)
        return design3d.core.BoundingBox.from_bounding_boxes(bounding_boxes)

    def cut_by_plane(self, plane_3d: surfaces.Plane3D):
        """
        Cut Shell3D by plane 3d.

        :param plane_3d: plane 3d o cut shell.
        :return: return a list of faces containing the shell's sections at the plane 3d given.
        """
        frame_block = self.bounding_box.to_frame()
        frame_block.u = 1.1 * frame_block.u
        frame_block.v = 1.1 * frame_block.v
        frame_block.w = 1.1 * frame_block.w
        block = design3d.primitives3d.Block(frame_block,
                                           color=(0.1, 0.2, 0.2),
                                           alpha=0.6)
        face_3d = block.cut_by_orthogonal_plane(plane_3d)
        intersection_primitives = []
        for face in self.faces:
            intersection_wires = face.face_intersections(face_3d)
            if intersection_wires:
                for intersection_wire in intersection_wires:
                    intersection_primitives.extend(intersection_wire.primitives)
        contours3d = wires.Contour3D.contours_from_edges(
            intersection_primitives[:])
        if not contours3d:
            return []
        contours2d = [contour.to_2d(plane_3d.frame.origin,
                                    plane_3d.frame.u,
                                    plane_3d.frame.v) for contour in contours3d]
        resulting_faces = []
        for contour2d in contours2d:
            if contour2d.area() > 1e-7:
                surface2d = surfaces.Surface2D(contour2d, [])
                resulting_faces.append(design3d.faces.PlaneFace3D(plane_3d, surface2d))
        return resulting_faces

    def linesegment_intersections(self, linesegment3d: edges.LineSegment3D) \
            -> List[Tuple[design3d.faces.Face3D, List[design3d.Point3D]]]:
        """
        Gets the intersections of a Shell3D with a Line Segment 3D.

        :param linesegment3d: other line segment.
        :return: List of tuples (face, intersections).
        """
        # intersections = []
        for face in self.faces:
            face_intersections = face.linesegment_intersections(linesegment3d)
            if face_intersections:
                yield face, face_intersections
        # return intersections

    def line_intersections(self,
                           line3d: curves.Line3D) \
            -> List[Tuple[design3d.faces.Face3D, List[design3d.Point3D]]]:
        """
        Gets the intersections of a Shell3D with a Line Segment 3D.

        :param line3d: other line segment.
        :return: List of tuples (face, intersections).
        """
        intersections = []
        for face in self.faces:
            face_intersections = face.line_intersections(line3d)
            if face_intersections:
                intersections.append((face, face_intersections))
        return intersections

    def minimum_distance_points(self, shell2):
        """
        Returns a Measure object if the distance is not zero, otherwise returns None.

        """
        shell2_inter = self.is_intersecting_with(shell2)
        if shell2_inter:
            return None
        _, point1, point2 = self.minimum_distance(shell2, return_points=True)
        return point1, point2

    def minimum_distance_point(self,
                               point: design3d.Point3D) -> design3d.Point3D:
        """
        Computes the distance of a point to a Shell3D, whether it is inside or outside the Shell3D.

        """
        distance_min, point1_min = self.faces[0].distance_to_point(point,
                                                                   return_other_point=True)
        for face in self.faces[1:]:
            bbox_distance = self.bounding_box.distance_to_point(point)
            if bbox_distance < distance_min:
                distance, point1 = face.distance_to_point(point,
                                                          return_other_point=True)
                if distance < distance_min:
                    distance_min, point1_min = distance, point1

        return point1_min

    @staticmethod
    def _minimum_distance_helper_points_sets(shell_decomposition):
        """
        Gets a set of points representing the shell, some kink of a cloud of points.

        """
        list_set_points = [{point for face in faces
                            for point in face.outer_contour3d.discretization_points(number_points=10)} for _, faces in
                           shell_decomposition.items()]
        list_set_points = [np.array([(point[0], point[1], point[2]) for point in sets_points1])
                           for sets_points1 in list_set_points]
        return list_set_points

    def get_minimum_distance_nearby_faces(self, other_shell):
        """
        Gets the nearby faces of the two shells where the minimum distance points could be, for further calculations.

        :param other_shell: other shell.
        :return: A list faces of self, with the closest faces to shell2, and another faces list of shell2,
        with those closest to self.
        """
        shell_decomposition1 = self.shell_decomposition()
        shell_decomposition2 = other_shell.shell_decomposition()
        list_set_points1 = self._minimum_distance_helper_points_sets(shell_decomposition1)
        list_set_points2 = self._minimum_distance_helper_points_sets(shell_decomposition2)
        minimum_distance = math.inf
        index1, index2 = None, None
        for sets_points1, sets_points2 in product(list_set_points1, list_set_points2):
            distances = np.linalg.norm(sets_points2[:, np.newaxis] - sets_points1, axis=2)
            sets_min_dist = np.min(distances)
            if sets_min_dist < minimum_distance:
                minimum_distance = sets_min_dist
                index1 = next((i for i, x in enumerate(list_set_points1) if np.array_equal(x, sets_points1)), -1)
                index2 = next((i for i, x in enumerate(list_set_points2) if np.array_equal(x, sets_points2)), -1)
        faces1 = list(shell_decomposition1.values())[index1]
        faces2 = list(shell_decomposition2.values())[index2]
        return faces1, faces2

    def minimum_distance(self, other_shell, return_points=False):
        """
        Calculates the minimum distance between two shells 3D.

        :param other_shell: other shell.
        :param return_points: weather to return the minimum distance corresponding points.
        :return: minimum distance, and if condition is True, the corresponding points.
        """
        faces1, faces2 = self.get_minimum_distance_nearby_faces(other_shell)
        minimum_distance = math.inf
        best_distance_points = None
        for face1, face2 in product(faces1, faces2):
            distance, point1, point2 = face1.face_minimum_distance(face2, True)
            if distance < minimum_distance:
                minimum_distance = distance
                best_distance_points = [point1, point2]
        if return_points:
            return minimum_distance, *best_distance_points
        return minimum_distance

    def shell_decomposition(self):
        """Decomposition of a shell 3D."""
        if not self._shell_octree_decomposition:
            self._shell_octree_decomposition = design3d.faces.octree_decomposition(self.bounding_box, self.faces)
        return self._shell_octree_decomposition

    def intersection_internal_aabb_volume(self, shell2: 'OpenShell3D',
                                          resolution: float):
        """
        Aabb made of the intersection points and the points of self internal to shell2.
        """
        intersections_points = []
        for face1 in self.faces:
            for face2 in shell2.faces:
                intersection_points = face1.face_intersections(face2)
                if intersection_points:
                    intersection_points = [
                        intersection_points[0].primitives[0].start,
                        intersection_points[0].primitives[0].end]
                    intersections_points.extend(intersection_points)

        shell1_points_inside_shell2 = []
        for face in self.faces:
            for point in face.outer_contour3d.discretization_points(angle_resolution=resolution):
                if shell2.point_inside(point):
                    shell1_points_inside_shell2.append(point)

        if len(intersections_points + shell1_points_inside_shell2) == 0:
            return 0
        bbox = design3d.core.BoundingBox.from_points(
            intersections_points + shell1_points_inside_shell2)
        return bbox.volume()

    def intersection_external_aabb_volume(self, shell2: 'OpenShell3D',
                                          resolution: float):
        """
        Aabb made of the intersection points and the points of self external to shell2.
        """
        intersections_points = []
        for face1 in self.faces:
            for face2 in shell2.faces:
                intersection_points = face1.face_intersections(face2)
                if intersection_points:
                    intersection_points = [
                        intersection_points[0].primitives[0].start,
                        intersection_points[0].primitives[0].end]
                    intersections_points.extend(intersection_points)

        shell1_points_outside_shell2 = []
        for face in self.faces:
            for point in face.outer_contour3d.discretization_points(
                    angle_resolution=resolution):
                if not shell2.point_inside(point):
                    shell1_points_outside_shell2.append(point)

        if len(intersections_points + shell1_points_outside_shell2) == 0:
            return 0
        bbox = design3d.core.BoundingBox.from_points(
            intersections_points + shell1_points_outside_shell2)
        return bbox.volume()

    def face_on_shell(self, face, abs_tol: float = 1e-6):
        """
        Verifies if a face lies on the shell's surface.

        """
        for face_ in self.faces:
            if face_.face_inside(face, abs_tol):
                return True
        return False

    def point_on_shell(self, point: design3d.Point3D):
        """
        Verify if a point is on the shell (on one of the shell's faces).

        :param point: point to be verified.
        :return: return True or False.
        """
        for face in self.faces:
            if face.point_belongs(point):
                return True
        return False

    def triangulation(self) -> display.Mesh3D:
        """
        Performs triangulation on a Shell3D object.

        This method iterates through each face of the Shell3D object and attempts to perform a triangulation.
        In cases where a face cannot be triangulated, a warning is issued, and the method proceeds to the next face.
        The triangulation of successfully processed faces are collected and merged into a single Mesh3D object.

        :return: A Mesh3D object representing the triangulated shell.
        :rtype: display.Mesh3D
        """
        meshes = []
        for i, face in enumerate(self.faces):
            try:
                face_mesh = face.triangulation()
                if face_mesh:
                    meshes.append(face_mesh)
            except Exception as exception:
                warnings.warn(f"Could not triangulate face {i} ({face.__class__.__name__}) in '{self.name}' "
                              f"due to: {exception}. This may be due to a topology error in contour2d.")

        return display.Mesh3D.from_meshes(meshes)

    def to_triangle_shell(self) -> Union["OpenTriangleShell3D", "ClosedTriangleShell3D"]:
        """
        Convert the current shell to a triangle shell.

        If the current shell is already a triangle shell, return it "as is".
        This conversion conserves the Open / Closed specification.
        """
        if "Triangle" in self.__class__.__name__:
            return self

        triangles = self.triangulation().faces

        if "Closed" in self.__class__.__name__:
            return ClosedTriangleShell3D(faces=triangles, color=self.color, alpha=self.alpha, name=self.name)

        return OpenTriangleShell3D(faces=triangles, color=self.color, alpha=self.alpha, name=self.name)

    def babylon_meshes(self, merge_meshes=True):
        """
        Returns the babylonjs mesh.
        """
        if merge_meshes:
            return super().babylon_meshes()

        babylon_meshes = []
        for face in self.faces:
            face_babylon_meshes = face.babylon_meshes()
            if not face_babylon_meshes:
                continue
            if face_babylon_meshes[0]['positions']:
                babylon_meshes.extend(face.babylon_meshes())
        babylon_mesh = {'primitives_meshes': babylon_meshes}
        babylon_mesh.update(self.babylon_param())
        return [babylon_mesh]

    def plot(self, ax=None, color: str = 'k', alpha: float = 1.0):
        """
        Plot a Shell 3D using Matplotlib.

        """
        if ax is None:
            ax = plt.figure().add_subplot(111, projection='3d')

        for face in self.faces:
            face.plot(ax=ax, color=color, alpha=alpha)

        return ax

    def project_coincident_faces_of(self, shell):
        """
        Divides self's faces based on coincident shell's faces.

        """

        list_faces = []
        initial_faces = self.faces[:]

        for face1 in initial_faces:
            list_faces.extend(face1.project_faces(shell.faces))

        return self.__class__(list_faces)

    def get_geo_lines(self, update_data, point_mesh_size: float = None):
        """
        Gets the lines that define an OpenShell3D geometry in a .geo file.

        :param update_data: Data used for VolumeModel defined with different shells
        :type update_data: dict
        :param point_mesh_size: The mesh size at a specific point, defaults to None
        :type point_mesh_size: float, optional
        :return: A list of lines that describe the geometry & the updated data
        :rtype: Tuple(List[str], dict)
        """

        primitives = []
        points = []
        for face in self.faces:
            for contour in list(chain(*[[face.outer_contour3d], face.inner_contours3d])):
                for point_contour in contour.get_geo_points():
                    if not point_in_list(point_contour, points):
                        points.append(point_contour)

                if isinstance(contour, curves.Circle2D):
                    pass
                else:
                    for primitive in contour.primitives:
                        if (not edge_in_list(primitive, primitives)
                                and not edge_in_list(primitive.reverse(), primitives)):
                            primitives.append(primitive)

        indices_check = len(primitives) * [None]

        point_account = update_data['point_account']
        line_account, line_loop_account = update_data['line_account'] + 1, update_data['line_loop_account']
        lines, line_surface, lines_tags = [], [], []

        points = list(points)
        for p_index, point in enumerate(points):
            lines.append(point.get_geo_lines(tag=p_index + point_account + 1,
                                             point_mesh_size=point_mesh_size))

        for f_index, face in enumerate(self.faces):
            line_surface = []
            for contour in list(chain(*[[face.outer_contour3d], face.inner_contours3d])):
                lines_tags = []
                if isinstance(contour, curves.Circle2D):
                    pass
                else:
                    for primitive in contour.primitives:
                        # index = get_edge_index_in_list(primitive, primitives)
                        index = get_edge_index_in_list(primitive, primitives)
                        if index is None:
                            index = get_edge_index_in_list(primitive.reverse(), primitives)

                        if primitives[index].is_close(primitive):

                            if isinstance(primitive, design3d.edges.BSplineCurve3D):
                                discretization_points = primitive.discretization_points()

                                start_point_tag = get_point_index_in_list(discretization_points[0], points) + 1
                                end_point_tag = get_point_index_in_list(discretization_points[1], points) + 1

                                primitive_linesegments = design3d.edges.LineSegment3D(
                                    discretization_points[0], discretization_points[1])
                                lines.append(primitive_linesegments.get_geo_lines(tag=line_account,
                                                                                  start_point_tag=start_point_tag
                                                                                  + point_account,
                                                                                  end_point_tag=end_point_tag
                                                                                  + point_account))

                            if isinstance(primitive, design3d.edges.LineSegment):

                                start_point_tag = get_point_index_in_list(primitive.start, points) + 1
                                end_point_tag = get_point_index_in_list(primitive.end, points) + 1

                                lines.append(primitive.get_geo_lines(tag=line_account,
                                                                     start_point_tag=start_point_tag + point_account,
                                                                     end_point_tag=end_point_tag + point_account))
                            elif isinstance(primitive, design3d.edges.ArcMixin):

                                start_point_tag = get_point_index_in_list(primitive.start, points) + 1
                                center_point_tag = get_point_index_in_list(primitive.circle.center, points) + 1
                                end_point_tag = get_point_index_in_list(primitive.end, points) + 1

                                lines.append(primitive.get_geo_lines(tag=line_account,
                                                                     start_point_tag=start_point_tag + point_account,
                                                                     center_point_tag=center_point_tag + point_account,
                                                                     end_point_tag=end_point_tag + point_account))

                            lines_tags.append(line_account)
                            indices_check[index] = line_account
                            line_account += 1

                        if primitives[index].is_close(primitive.reverse()):
                            lines_tags.append(-indices_check[index])

                    lines.append(contour.get_geo_lines(line_loop_account + 1, lines_tags))

                    line_surface.append(line_loop_account + 1)
                    line_loop_account += 1
                    lines_tags = []

            lines.append(face.get_geo_lines((f_index + 1 + update_data['surface_account']),
                                            line_surface))

            line_surface = []

        lines.append('Surface Loop(' + str(1 + update_data['surface_loop_account']) + ') = {'
                     + str(list(range(update_data['surface_account'] + 1,
                                      update_data['surface_account'] +
                                      len(self.faces) + 1)))[1:-1] + '};')

        update_data['point_account'] += len(points)
        update_data['line_account'] += line_account - 1
        update_data['line_loop_account'] += line_loop_account
        update_data['surface_account'] += len(self.faces)
        update_data['surface_loop_account'] += 1

        return lines, update_data

    def get_mesh_lines_with_transfinite_curves(self, min_points, size):
        """Gets Shells' mesh lines with transfinite curves."""
        lines = []
        for face in self.faces:
            lines.extend(face.surface2d.get_mesh_lines_with_transfinite_curves(
                [[face.outer_contour3d], face.inner_contours3d], min_points, size))
        return lines

    @staticmethod
    def is_shell_open(faces, faces_graph=None):
        """Returns True if shell is an open shell."""
        if faces_graph is None:
            vertices_points = Shell3D._helper_getter_vertices_points(faces)
            faces_graph = Shell3D._helper_create_faces_graph(faces, vertices_points, False)

        def is_primitive_on_neighbor_face(prim, neighbor_face):
            """Verifies if primitive is on a neighbor face."""
            return any(
                neighbor_face_contour.is_primitive_section_over_wire(prim)
                for neighbor_face_contour in [neighbor_face.outer_contour3d] + neighbor_face.inner_contours3d
            )

        for n_index in faces_graph.nodes:
            face = faces[n_index]
            if any(
                    not any(
                        is_primitive_on_neighbor_face(prim, faces[neighbor])
                        for neighbor in faces_graph.neighbors(n_index)
                    )
                    for prim in [prim for contour in [face.outer_contour3d] + face.inner_contours3d
                                 for prim in contour.primitives]
            ):
                return True

        return False

    @classmethod
    def from_faces(cls, faces, name: str = ''):
        """
        Defines a List of separated OpenShell3D from a list of faces, based on the faces graph.
        """
        vertices_points = Shell3D._helper_getter_vertices_points(faces)
        graph = Shell3D._helper_create_faces_graph(faces, vertices_points, verify_connected_components=False)
        components = [graph.subgraph(c).copy() for c in nx.connected_components(graph)]

        shells_list = []
        for index, graph_i in enumerate(components, start=1):
            faces_list = [faces[n_index] for n_index in graph_i.nodes]
            if cls.is_shell_open(faces, graph_i):
                shells_list.append(OpenShell3D(faces_list, name=name + f'_{index}'))
            else:
                shells_list.append(ClosedShell3D(faces_list, name=name + f'_{index}'))

        return shells_list

    def is_disjoint_from(self, shell2, tol=1e-8):
        """
        Verifies and returns a Boolean if two shells are disjointed or not.

        """
        disjoint = True
        if self.bounding_box.is_intersecting(shell2.bounding_box, tol):
            return False
        return disjoint

    def is_face_intersecting(self, face: design3d.faces.Face3D):
        """Verifies if face is intersecting shell somehow."""
        if not self.bounding_box.is_intersecting(face.bounding_box):
            return False
        for i_face in self.faces:
            if i_face.face_intersections(face):
                return True
        return False

    def is_intersecting_with(self, shell2):
        """Verifies if two closed shells are intersecting somehow."""
        if self.is_disjoint_from(shell2):
            return False
        for face2 in shell2.faces:
            if self.is_face_intersecting(face2):
                return True
        return False


class OpenShell3D(Shell3D):
    """
    A 3D Open shell composed of multiple faces.

    This class represents a 3D open shell, which is a collection of connected
    faces with no volume. It is a subclass of the `Shell3D` class and
    inherits all of its attributes and methods.
    """

    STEP_FUNCTION = 'OPEN_SHELL'

    def union(self, shell2):
        """
        Combine two shells faces.

        :return: a new OpenShell3D with the combined faces.
        """
        new_faces = self.faces + shell2.faces
        new_name = self.name + ' union ' + shell2.name
        new_color = self.color
        return self.__class__(new_faces, name=new_name, color=new_color)


class ClosedShell3D(Shell3D):
    """
    A 3D closed shell composed of multiple faces.

    This class represents a 3D closed shell, which is a collection of connected
    faces with a volume. It is a subclass of the `Shell3D` class and
    inherits all of its attributes and methods. In addition, it has a method
    to check whether a face is inside the shell.
    """

    STEP_FUNCTION = 'CLOSED_SHELL'

    def volume(self):
        """
        Does not consider holes.

        """
        volume = 0
        center_x, center_y, center_z = self.bounding_box.center
        for face in self.faces:
            display3d = face.triangulation()
            for triangle_index in display3d.triangles:
                point1 = display3d.vertices[triangle_index[0]]
                point2 = display3d.vertices[triangle_index[1]]
                point3 = display3d.vertices[triangle_index[2]]

                point1_adj = (point1[0] - center_x, point1[1] - center_y, point1[2] - center_z)
                point2_adj = (point2[0] - center_x, point2[1] - center_y, point2[2] - center_z)
                point3_adj = (point3[0] - center_x, point3[1] - center_y, point3[2] - center_z)

                volume_tetraedre = 1 / 6 * abs(-point3_adj[0] * point2_adj[1] * point1_adj[2] +
                                               point2_adj[0] * point3_adj[1] * point1_adj[2] +
                                               point3_adj[0] * point1_adj[1] * point2_adj[2] -
                                               point1_adj[0] * point3_adj[1] * point2_adj[2] -
                                               point2_adj[0] * point1_adj[1] * point3_adj[2] +
                                               point1_adj[0] * point2_adj[1] * point3_adj[2])

                volume += volume_tetraedre

        return abs(volume)

    def is_face_inside(self, face: design3d.faces.Face3D):
        """
        Verifies if a face is inside the closed shell 3D.

        :param face: other face.
        :return: returns True if face is inside, and False otherwise.
        """
        if not face.bounding_box.is_inside_bbox(self.bounding_box):
            return False
        points = []
        if face.area() > 1e-8:
            points.append(face.random_point_inside())

        for prim in face.outer_contour3d.primitives:
            points.extend([prim.middle_point(), prim.end])
        for point in points:
            point_inside_shell = self.point_inside(point)
            if not point_inside_shell:
                return False
        return True

    def get_ray_casting_line_segment(self, point3d):
        """Gets the best ray for performing ray casting algorithm."""
        boxes_size = [self.bounding_box.size[0] / 2, self.bounding_box.size[1] / 2, self.bounding_box.size[2] / 2]
        xyz = [design3d.Vector3D(boxes_size[0], 0, 0), design3d.Vector3D(0, boxes_size[1], 0),
               design3d.Vector3D(0, 0, boxes_size[2])]
        points = sorted(self.bounding_box.get_points_inside_bbox(2, 2, 2), key=point3d.point_distance)
        bbox_outside_points = []
        for vector in xyz:
            for direction in [1, -1]:
                bbox_outside_point = points[0] + direction * vector
                if not self.bounding_box.point_inside(bbox_outside_point):
                    bbox_outside_points.append(bbox_outside_point)
        bbox_outside_points = sorted(bbox_outside_points, key=point3d.point_distance)
        vec1 = bbox_outside_points[0] - point3d
        vec1 = vec1.to_vector()
        vec2 = bbox_outside_points[1] - point3d
        vec2 = vec2.to_vector()
        vec3 = bbox_outside_points[2] - point3d
        vec3 = vec3.to_vector()
        rays = [edges.LineSegment3D(
                point3d, point3d + 2 * vec1 + random.random() * vec2 + random.random() * vec3) for _ in range(10)]
        return rays

    def point_inside(self, point3d: design3d.Point3D, **kwargs):
        """
        Ray Casting algorithm.

        Returns True if the point is inside the Shell, False otherwise
        """
        bbox = self.bounding_box

        if not bbox.point_inside(point3d):
            return False
        rays = self.get_ray_casting_line_segment(point3d)

        count = 0
        for ray in rays:
            count = 0
            intersections = []
            for _, point_inters in self.linesegment_intersections(ray):
                if point_inters[0].is_close(point3d):
                    return True
                for inter in point_inters:
                    if inter.in_list(intersections):
                        break
                    intersections.append(inter)
                    count += 1
                else:
                    continue
                break
            else:
                continue
            break
        is_inside = True
        if count % 2 == 0:
            is_inside = False
        return is_inside

    def is_inside_shell(self, shell2):
        """
        Returns True if all the points of self are inside shell2 and no face are intersecting.

        This method is not exact.
        """
        bbox1 = self.bounding_box
        bbox2 = shell2.bounding_box
        if not bbox1.is_inside_bbox(bbox2):
            return False
        for face in self.faces:
            if not shell2.is_face_inside(face):
                return False
        return True

    def intersecting_faces_combinations(self, shell2, tol=1e-8):
        """
        Gets intersecting faces combinations.

        :param shell2: ClosedShell3D
        :param tol: Corresponds to the tolerance to consider two faces as intersecting faces

        :return: returns a dictionary containing as keys the combination of intersecting faces
        and as the values the resulting primitive from the two intersecting faces.
        It is done, so it is not needed to calculate the same intersecting primitive twice.
        """
        face_combinations1 = {face: [] for face in self.faces}
        face_combinations2 = {face: [] for face in shell2.faces}
        for face1 in self.faces:
            for face2 in shell2.faces:
                if face1.surface3d.is_coincident(face2.surface3d, abs_tol=tol):
                    contours1, contours2 = face1.get_coincident_face_intersections(face2)
                    face_combinations1[face1].extend(contours1)
                    face_combinations2[face2].extend(contours2)

                face_intersections = face1.face_intersections(face2, tol)
                face_combinations1[face1].extend(face_intersections)
                face_combinations2[face2].extend(face_intersections)
                # if face_intersections:
                #     face_combinations[(face1, face2)] = face_intersections
        return face_combinations1, face_combinations2

    @staticmethod
    def validate_non_intersecting_faces(shell2, non_intersecting_faces, intersection_method=False):
        """
        Gets lists of faces that never intersect with any of the shell2's faces.

        :param shell2: ClosedShell3D.
        :param non_intersecting_faces:
        :param intersection_method: determines if running for intersection operation.
        returns a list of all the faces that never intersect any
        face of the other shell.
        """
        valid_non_intercting_faces = []
        for face in non_intersecting_faces:
            if shell2.face_on_shell(face):
                continue
            if intersection_method:
                if shell2.is_face_inside(face):
                    valid_non_intercting_faces.append(face)
            elif not shell2.is_face_inside(face):
                valid_non_intercting_faces.append(face)
        return valid_non_intercting_faces

    def get_coincident_faces(self, shell2, abs_tol: float = 1e-6):
        """
        Finds all pairs of faces that are coincident faces, that is, faces lying on the same plane.

        returns a List of tuples with the face pairs.
        """
        list_coincident_faces = []
        for face1 in self.faces:
            for face2 in shell2.faces:
                if face1.surface3d.is_coincident(face2.surface3d, abs_tol):
                    contour1 = face1.outer_contour3d.to_2d(
                        face1.surface3d.frame.origin,
                        face1.surface3d.frame.u,
                        face1.surface3d.frame.v)
                    contour2 = face2.outer_contour3d.to_2d(
                        face1.surface3d.frame.origin,
                        face1.surface3d.frame.u,
                        face1.surface3d.frame.v)
                    if contour1.bounding_rectangle.b_rectangle_intersection(contour2.bounding_rectangle):
                        list_coincident_faces.append((face1, face2))

        return list_coincident_faces

    def set_operations_valid_exterior_faces(self, new_faces: List[design3d.faces.Face3D],
                                            valid_faces: List[design3d.faces.Face3D],
                                            list_coincident_faces: List[design3d.faces.Face3D],
                                            shell2):
        """
        Select the valid faces from the new faces created during Boolean operations.

        :param new_faces: list of new divided faces.
        :param valid_faces: list of already validated faces.
        :param list_coincident_faces: if of coincident faces.
        :param shell2: shell2, used in the Boolean operation.
        :return:
        """
        for new_face in new_faces:
            if self.set_operations_exterior_face(new_face, valid_faces, list_coincident_faces, shell2):
                valid_faces.append(new_face)
        return valid_faces

    def union_faces(self, shell2, intersecting_faces, dict_faces_intersections, list_coincident_faces):
        """
        Gets new faces for union Boolean operation between two closed shell 3d.

        :param shell2: other shell
        :param intersecting_faces: list of all intersecting faces.
        :param dict_faces_intersections: Dictionary containing all combination of faces intersection,\
        with corresponding intersections.
        :param list_coincident_faces: list of coincident faces.
        :return: list of new faces for union of two closed shell3.
        """
        faces = []
        for face in intersecting_faces:
            new_faces = face.set_operations_new_faces(dict_faces_intersections)
            faces = self.set_operations_valid_exterior_faces(new_faces, faces, list_coincident_faces, shell2)
        return faces

    def get_subtraction_valid_faces(self, new_faces, valid_faces, shell2, keep_interior_faces):
        """
        Gets valid faces for subtraction Boolean operations.

        :param new_faces: list of new divided faces.
        :param valid_faces: list of already validated faces.
        :param shell2: other shell.
        :param keep_interior_faces: Boolean to decide to keep interior faces on reference shell or not.
        :return: return a list a valid faces.
        """
        faces = []
        for new_face in new_faces:
            if shell2.face_on_shell(new_face):
                if self.face_on_shell(new_face):
                    if self.is_face_between_shells(shell2, new_face):
                        faces.append(new_face)
                continue
            if keep_interior_faces:
                if self.set_operations_interior_face(new_face, valid_faces, shell2):
                    faces.append(new_face)
            elif self.set_operations_exterior_face(new_face, faces, [], shell2):
                faces.append(new_face)
        return faces

    @staticmethod
    def validate_set_operations_faces(faces):
        """
        Final validation of new faces created during intersections or subtractions of two closed shells.

        :param faces: new faces.
        :return: valid faces.
        """
        valid_faces = []
        while True:
            if not faces:
                break
            for face in valid_faces:
                if face.face_inside(faces[0]):
                    faces.pop(0)
                    break
            else:
                valid_faces.append(faces.pop(0))
        return valid_faces

    def subtraction_faces(self, shell2, intersecting_faces, dict_faces_intersections, keep_interior_faces: bool):
        """
        Gets new faces for subtraction Boolean operation between two closed shell 3d.

        :param shell2: other shell
        :param intersecting_faces: list of all intersecting faces.
        :param dict_faces_intersections: Dictionary containing all combination of faces intersection,\
        with corresponding intersections.
        :return: list of new faces for subtraction of two closed shells 3.
        """
        faces = []
        for face in intersecting_faces:
            new_faces = face.set_operations_new_faces(dict_faces_intersections)
            valid_faces = self.get_subtraction_valid_faces(new_faces, faces,
                                                           shell2, keep_interior_faces)
            faces.extend(valid_faces)

        return faces

    def valid_intersection_faces(self, new_faces, valid_faces, shell2):
        """
        Validate Boolean intersection operation new faces.

        :param new_faces: list of new divided faces.
        :param valid_faces: list of already validated faces.
        :param shell2: other shell.
        :return:
        """
        faces = []
        for new_face in new_faces:
            if shell2.face_on_shell(new_face):
                point3d = new_face.random_point_inside()
                if new_face.point_belongs(point3d):
                    normal1 = point3d - 0.00001 * new_face.surface3d.frame.w.unit_vector()
                    normal2 = point3d + 0.00001 * new_face.surface3d.frame.w.unit_vector()
                    if (self.point_inside(normal1) and shell2.point_inside(normal1)) or \
                            (shell2.point_inside(normal2) and self.point_inside(normal2)):
                        faces.append(new_face)
                continue
            inside_shell2 = shell2.point_inside(
                new_face.random_point_inside())
            if inside_shell2 and new_face not in valid_faces:
                faces.append(new_face)

        return faces

    def intersection_faces(self, shell2, intersecting_faces, dict_faces_intersections):
        """
        Gets new faces for intersection Boolean operation between two closed shell 3d.

        :param shell2: other shell
        :param intersecting_faces: list of all intersecting faces.
        :param dict_faces_intersections: Dictionary containing all combination of faces intersection,\
        with corresponding intersections.
        :return: list of new faces for intersection of two closed shells 3d.
        """
        faces = []
        for face in intersecting_faces:
            new_faces = face.set_operations_new_faces(dict_faces_intersections)
            valid_faces = self.valid_intersection_faces(
                new_faces, faces, shell2)
            faces.extend(valid_faces)

        return faces

    @staticmethod
    def set_operations_interior_face(new_face, faces, shell2):
        """
        Verify if new face is inside reference shell for Boolean operations.

        :param new_face: new divided face.
        :param faces: list of already validated faces.
        :param shell2: reference shell, to help decide if a new divided face should be saved or not.
        """
        inside_shell2 = shell2.point_inside(new_face.random_point_inside())
        if inside_shell2 and new_face not in faces:
            return True
        # if self.face_on_shell(new_face):
        #     return True
        return False

    def is_face_between_shells(self, shell2, face):
        """
        Verify if face is between the two shells.

        :param shell2: other shell
        :param face: face to be verified.
        :return:
        """
        points = []
        center_of_mass = face.surface2d.outer_contour.center_of_mass()
        if face.surface2d.outer_contour.point_inside(center_of_mass):
            points = [center_of_mass]

        if face.surface2d.inner_contours:
            normal_0 = face.surface2d.outer_contour.primitives[0].normal_vector(0.0)
            middle_point_0 = face.surface2d.outer_contour.primitives[0].middle_point()
            point1 = middle_point_0 + 0.0001 * normal_0
            point2 = middle_point_0 - 0.0001 * normal_0
            points = [point1, point2]
        else:
            points.extend([face.surface2d.outer_contour.random_point_inside()])

        for point in points:
            point3d = face.surface3d.point2d_to_3d(point)
            if face.point_belongs(point3d):
                normal_at_point = face.normal_at_point(point3d)
                normal1 = point3d - 0.00001 * normal_at_point
                normal2 = point3d + 0.00001 * normal_at_point
                if (self.point_inside(normal1) and
                    shell2.point_inside(normal2)) or \
                        (shell2.point_inside(normal1) and
                         self.point_inside(normal2)):
                    return True
        return False

    def set_operations_exterior_face(self, new_face, valid_faces,
                                     list_coincident_faces, shell2):
        """
        Selects exterior faces during bool operations, like union or subtraction.

        :param new_face: divided faces.
        :param valid_faces: list of already validated faces.
        :param shell2: other shell.
        :param list_coincident_faces: list of coincident faces.
        :return:
        """
        if new_face.area() < 1e-8:
            return False
        if new_face not in valid_faces:
            inside_shell2 = shell2.point_inside(new_face.random_point_inside())
            face_on_shell2 = shell2.face_on_shell(new_face)
            if not inside_shell2 or face_on_shell2:
                if list_coincident_faces and any(new_face.surface3d.is_coincident(face.surface3d)
                                                 for faces in list_coincident_faces for face in faces):
                    if self.is_face_between_shells(shell2, new_face):
                        return False
                return True
        return False

    def validate_set_operation(self, shell2, tol):
        """
        Verifies if two shells are valid for union or subtractions operations.

        Its Verifies if they are disjointed or if one is totally inside the other.

        If it returns an empty list, it means the two shells are valid to continue the
        operation.
        """
        if self.is_disjoint_from(shell2, tol):
            return [self, shell2]
        if self.is_inside_shell(shell2):
            return [shell2]
        if shell2.is_inside_shell(self):
            return [self]
        return []

    @staticmethod
    def _separate_intersecting_and_non_intersecting_faces(dict_face_intersections):
        """
        Separates intersecting and non-intersecting faces.

        :param dict_face_intersections: dictionary containing all faces intersections.
        :return:
        """
        non_intersecting_faces = []
        intersecting_faces = []
        for face, value in dict_face_intersections.items():
            if value:
                intersecting_faces.append(face)
                continue
            non_intersecting_faces.append(face)
        return intersecting_faces, non_intersecting_faces

    def _delete_coincident_faces(self, shell2, list_coincident_faces, abs_tol: float = 1e-6):
        """
        Helper method to delete coincident faces during union operation.

        :param shell2: other shell2.
        :param list_coincident_faces: list of coincident faces.
        :param abs_tol: tolerance.
        :return: list of closed shells.
        """
        faces1 = self.faces[:]
        faces2 = shell2.faces[:]
        if list_coincident_faces:
            for face1, face2 in list_coincident_faces:
                if shell2.face_on_shell(face1, abs_tol):
                    if face1 in faces1:
                        faces1.remove(face1)
                if self.face_on_shell(face2, abs_tol):
                    if face2 in faces2:
                        faces2.remove(face2)
        if len(faces1) + len(faces2) == len(self.faces) + len(shell2.faces):
            return [self, shell2]
        return [ClosedShell3D(faces1+faces2)]

    def union(self, shell2: 'ClosedShell3D', tol: float = 1e-8):
        """
        Given Two closed shells, it returns a new united ClosedShell3D object.

        """
        validate_set_operation = self.validate_set_operation(shell2, tol)
        if validate_set_operation:
            return validate_set_operation
        list_coincident_faces = self.get_coincident_faces(shell2, tol)
        dict_face_intersections1, dict_face_intersections2 = self.intersecting_faces_combinations(shell2, tol)
        intersecting_faces_1, non_intersecting_faces1 = self._separate_intersecting_and_non_intersecting_faces(
            dict_face_intersections1)
        intersecting_faces_2, non_intersecting_faces2 = self._separate_intersecting_and_non_intersecting_faces(
            dict_face_intersections2)
        non_intersecting_faces1 = self.validate_non_intersecting_faces(shell2, non_intersecting_faces1)
        non_intersecting_faces2 = shell2.validate_non_intersecting_faces(self, non_intersecting_faces2)
        faces = non_intersecting_faces1 + non_intersecting_faces2
        if len(faces) == len(self.faces + shell2.faces) and not intersecting_faces_1 + intersecting_faces_2:
            return self._delete_coincident_faces(shell2, list_coincident_faces, tol)
        new_valid_faces = self.union_faces(shell2, intersecting_faces_1,
                                           dict_face_intersections1, list_coincident_faces)
        new_valid_faces += shell2.union_faces(self, intersecting_faces_2,
                                              dict_face_intersections2, list_coincident_faces)
        if list_coincident_faces:
            new_valid_faces = self.validate_set_operations_faces(new_valid_faces)
        faces += new_valid_faces
        new_shell = ClosedShell3D(faces)
        return [new_shell]

    @staticmethod
    def get_faces_to_be_merged(union_faces):
        """Gets faces that are adjacent, and sharing the same surface, so they can be merged."""
        coincident_planes_faces = []
        for i, face1 in enumerate(union_faces):
            for j, face2 in enumerate(union_faces):
                if j != i and face1.surface3d.is_coincident(face2.surface3d):
                    if face1 not in coincident_planes_faces:
                        coincident_planes_faces.append(face1)
                    coincident_planes_faces.append(face2)
            if coincident_planes_faces:
                break
        return coincident_planes_faces

    @staticmethod
    def clean_faces(union_faces, list_new_faces):
        """Clean union faces."""
        list_remove_faces = []
        if union_faces:
            for face1 in union_faces:
                for face2 in list_new_faces:
                    if face1.face_inside(face2):
                        list_remove_faces.append(face2)
                    elif face2.face_inside(face1):
                        list_remove_faces.append(face1)
        list_new_faces += union_faces
        for face in list_remove_faces:
            list_new_faces.remove(face)
        return list_new_faces

    def merge_faces(self):
        """
        Merges all shells' adjacent faces into one.

        """
        union_faces = self.faces
        finished = False
        list_new_faces = []
        count = 0
        while not finished:
            valid_coicident_faces = ClosedShell3D.get_faces_to_be_merged(union_faces)
            list_valid_coincident_faces = valid_coicident_faces[:]
            if valid_coicident_faces:
                list_new_faces += design3d.faces.PlaneFace3D.merge_faces(valid_coicident_faces)
            for face in list_valid_coincident_faces:
                union_faces.remove(face)
            count += 1
            if count >= len(self.faces) and not list_valid_coincident_faces:
                finished = True

        list_new_faces = self.clean_faces(union_faces, list_new_faces)

        self.faces = list_new_faces

    def subtract(self, shell2, tol=1e-8):
        """
        Given Two closed shells, it returns a new subtracted OpenShell3D.

        """
        validate_set_operation = self.validate_set_operation(shell2, tol)
        if validate_set_operation:
            return validate_set_operation

        list_coincident_faces = self.get_coincident_faces(shell2)

        dict_face_intersections1, _ = self.intersecting_faces_combinations(shell2, tol)
        intersecting_faces_1, non_intersecting_faces1 = self._separate_intersecting_and_non_intersecting_faces(
            dict_face_intersections1)
        non_intersecting_faces1 = self.validate_non_intersecting_faces(shell2, non_intersecting_faces1)
        faces = non_intersecting_faces1
        if len(intersecting_faces_1) == 0:
            return [self, shell2]
        new_valid_faces = self.union_faces(shell2, intersecting_faces_1,  dict_face_intersections1,
                                           list_coincident_faces)
        faces += new_valid_faces
        return OpenShell3D.from_faces(faces)

    def subtract_to_closed_shell(self, shell2: 'ClosedShell3D', tol: float = 1e-8):
        """
        Subtracts shell2's volume from self.

        :param shell2: other shell
        :param tol: tolerance
        :return:
        """
        if self.is_disjoint_from(shell2, tol):
            return [self]
        dict_face_intersections1, dict_face_intersections2 = self.intersecting_faces_combinations(shell2, tol)
        intersecting_faces_1, non_intersecting_faces1 = self._separate_intersecting_and_non_intersecting_faces(
            dict_face_intersections1)
        intersecting_faces_2, non_intersecting_faces2 = self._separate_intersecting_and_non_intersecting_faces(
            dict_face_intersections2)
        non_intersecting_faces1 = self.validate_non_intersecting_faces(shell2, non_intersecting_faces1)
        non_intersecting_faces2 = shell2.validate_non_intersecting_faces(self, non_intersecting_faces2, True)
        faces = non_intersecting_faces1 + non_intersecting_faces2
        new_valid_faces = self.subtraction_faces(shell2, intersecting_faces_1, dict_face_intersections1, False)
        new_valid_faces += shell2.subtraction_faces(self, intersecting_faces_2, dict_face_intersections2, True)
        faces += new_valid_faces
        faces = self.validate_set_operations_faces(faces)
        new_shell = ClosedShell3D(faces)
        return [new_shell]

    def validate_intersection_operation(self, shell2):
        """
        Verifies if two shells are valid for union or subtractions operations.

        Its Verifies if they are disjointed or if one is totally inside the other.
        If it returns an empty list, it means the two shells are valid to continue the
        operation.
        """
        if self.is_inside_shell(shell2):
            return [self]
        if shell2.is_inside_shell(self):
            return [shell2]
        return []

    def intersection(self, shell2, tol=1e-8):
        """
        Given two ClosedShell3D, it returns the new object resulting from the intersection of the two.

        """
        if self.is_disjoint_from(shell2, tol):
            return []
        validate_set_operation = self.validate_intersection_operation(shell2)
        if validate_set_operation:
            return validate_set_operation
        dict_face_intersections1, dict_face_intersections2 = self.intersecting_faces_combinations(shell2, tol)
        intersecting_faces_1, non_intersecting_faces1 = self._separate_intersecting_and_non_intersecting_faces(
            dict_face_intersections1)
        intersecting_faces_2, non_intersecting_faces2 = self._separate_intersecting_and_non_intersecting_faces(
            dict_face_intersections2)
        non_intersecting_faces1 = self.validate_non_intersecting_faces(shell2, non_intersecting_faces1, True)
        non_intersecting_faces2 = shell2.validate_non_intersecting_faces(self, non_intersecting_faces2, True)
        faces = non_intersecting_faces1 + non_intersecting_faces2
        if len(intersecting_faces_1) + len(intersecting_faces_2) == 0:
            return []
        faces += self.intersection_faces(shell2, intersecting_faces_1, dict_face_intersections1)
        faces += shell2.intersection_faces(self, intersecting_faces_2, dict_face_intersections2)
        faces = self.validate_set_operations_faces(faces)
        new_shell = ClosedShell3D(faces)
        return [new_shell]

    def eliminate_not_valid_closedshell_faces(self):
        """
        Eliminate not valid closed shell faces resulted from boolean operations.

        """
        nodes_with_2degrees = [node for node, degree in list(self.vertices_graph.degree()) if degree <= 2]
        for node in nodes_with_2degrees:
            neighbors = nx.neighbors(self.vertices_graph, node)
            for neighbor_node in neighbors:
                for face in self.faces:
                    if self.vertices_graph.edges[(node, neighbor_node)]['edge'] in face.outer_contour3d.primitives:
                        self.faces.remove(face)
                        break
        self._faces_graph = None


class OpenTriangleShell3D(OpenShell3D):
    """
    A 3D open shell composed of multiple triangle faces.

    This class represents a 3D open shell, which is a collection of connected
    triangle faces with no volume. It is a subclass of the `OpenShell3D` class
    and inherits all of its attributes and methods.

    :param faces: The triangle faces of the shell.
    :type faces: List[`Triangle3D`]
    :param color: The color of the shell.
    :type color: Tuple[float, float, float]
    :param alpha: The transparency of the shell, should be a value in the range (0, 1).
    :type alpha: float
    :param name: The name of the shell.
    :type name: str
    """

    def __init__(
        self,
        faces: List[design3d.faces.Triangle3D],
        color: Tuple[float, float, float] = None,
        alpha: float = 1.0,
        reference_path: str = design3d.PATH_ROOT,
        name: str = "",
    ):
        OpenShell3D.__init__(self, faces=faces, color=color, alpha=alpha, reference_path=reference_path, name=name)

    def get_bounding_box(self) -> design3d.core.BoundingBox:
        """Gets the Shell bounding box."""
        vertices = np.array(
            [(face.points[i].x, face.points[i].y, face.points[i].z) for face in self.faces for i in range(3)]
        )
        bbox_min, bbox_max = np.min(vertices, axis=0), np.max(vertices, axis=0)

        return design3d.core.BoundingBox(bbox_min[0], bbox_max[0], bbox_min[1], bbox_max[1], bbox_min[2], bbox_max[2])

    def to_mesh_data(self, round_vertices: bool, n_decimals: int = 9) -> Tuple[NDArray[float], NDArray[int]]:
        """
        Convert the TriangleShell3D to mesh data: vertices and faces described as index of vertices.

        :param round_vertices: Allows to choose to round vertices coordinates or not.
            Rounding vertices coordinates allows to prevent numerical imprecision, which allows vertex sharing between
            adjacent triangles.
        :type round_vertices: bool
        :param n_decimals: int
        :type n_decimals: float

        :return: The vertices and faces composing the mesh data.
        :rtype: Tuple[NDArray[float], NDArray[int]]
        """
        # Flatten and round the vertices array
        vertices = np.array(
            [(face.points[i].x, face.points[i].y, face.points[i].z) for face in self.faces for i in range(3)]
        )

        if round_vertices:
            vertices = np.round(vertices, n_decimals)  # rounding to prevent numerical imprecision

        # Get unique vertices and their indices
        vertices, unique_indices = np.unique(vertices, axis=0, return_inverse=True)

        # Create the triangle indices array using NumPy indexing
        flattened_indices = unique_indices.reshape(-1, 3)
        faces = flattened_indices[: len(self.faces)]

        return vertices, faces

    @classmethod
    def from_mesh_data(cls, vertices: Iterable[Iterable[float]], faces: Iterable[Iterable[int]], name: str = ""):
        """
        Create a TriangleShell3D from mesh data: vertices and faces described as index of vertices.

        :param vertices: The vertices of the mesh.
        :type vertices: Iterable[Iterable[float]]
        :param faces: The faces of the mesh, using vertices indexes.
        :type faces: Iterable[Iterable[int]]
        :param name: A name for the TriangleShell3D, optional.
        :type name: str

        :return: The created TriangleShell3D.
        :rtype: TriangleShell3D
        """
        triangles = []

        points = [design3d.Point3D(px, py, pz) for px, py, pz in vertices]

        for i1, i2, i3 in faces:
            try:
                triangles.append(design3d.faces.Triangle3D(points[i1], points[i2], points[i3]))
            except ZeroDivisionError:
                pass
        return cls(triangles, name=name)

    def decimate(
        self,
        target_count: int,
        update_rate: int = 5,
        aggressiveness: float = 7.0,
        max_iterations: int = 100,
        verbose: bool = False,
        lossless: bool = False,
        threshold_lossless: float = 1e-3,
        alpha: float = 1e-9,
        k: int = 3,
        preserve_border: bool = True,
    ):
        """
        Decimate the triangle shell, and return it.

        Note: threshold = alpha * pow(iteration + k, aggressiveness)

        :param target_count: Target number of triangles. Not used if `lossless` is True.
        :type target_count: int
        :param update_rate: Number of iterations between each update. If `lossless` flag is set to True, rate is 1.
        :type update_rate: int
        :param aggressiveness: Parameter controlling the growth rate of the threshold at each iteration when `lossless`
            is False.
        :type aggressiveness: float
        :param max_iterations: Maximal number of iterations.
        :type max_iterations: int
        :param verbose: Control verbosity.
        :type verbose: bool
        :param lossless: Use the lossless simplification method.
        :type lossless: bool
        :param threshold_lossless: Maximal error after which a vertex is not deleted. Only for `lossless` method.
        :type threshold_lossless: float
        :param alpha: Parameter for controlling the threshold growth.
        :type alpha: float
        :param k: Parameter for controlling the threshold growth.
        :type k: int
        :param preserve_border: Flag for preserving vertices on open border.
        :type preserve_border: bool

        :return: The decimated triangle shell.
        :rtype: OpenTriangleShell3D
        """
        # pylint: disable=too-many-arguments

        vertices, triangles = self.to_mesh_data(round_vertices=True, n_decimals=9)

        simplifier = pyfqmr.Simplify()
        simplifier.setMesh(vertices, triangles)
        simplifier.simplify_mesh(
            target_count=target_count,
            update_rate=update_rate,
            aggressiveness=aggressiveness,
            max_iterations=max_iterations,
            verbose=verbose,
            lossless=lossless,
            threshold_lossless=threshold_lossless,
            alpha=alpha,
            K=k,
            preserve_border=preserve_border,
        )

        vertices, faces, _ = simplifier.getMesh()

        return self.__class__.from_mesh_data(vertices, faces)

    def to_trimesh(self):
        """Creates a Trimesh from a TriangleShell3D."""
        return Trimesh(*self.to_mesh_data(round_vertices=True))

    @classmethod
    def from_trimesh(cls, trimesh, name: str = ""):
        """Creates a TriangleShell3D from Trimesh."""
        return cls.from_mesh_data(trimesh.vertices, trimesh.faces, name=name)

    def triangulation(self):
        """Triangulation of an Open Triangle Shell 3D."""
        points = []
        triangles = []
        for i, triangle in enumerate(self.faces):
            points.append(np.array(triangle.point1))
            points.append(np.array(triangle.point2))
            points.append(np.array(triangle.point3))
            triangles.append((3 * i, 3 * i + 1, 3 * i + 2))
        vertices = np.array(points, dtype=np.float64)
        return display.Mesh3D(vertices, np.array(triangles, dtype=np.int32))

    def to_dict(self, *args, **kwargs):
        """Overload of 'to_dict' for performance."""
        dict_ = self.base_dict()

        # not rounding to make sure to retrieve the exact same object with 'dict_to_object'
        vertices, faces = self.to_mesh_data(round_vertices=False)

        dict_.update({"vertices": vertices.tolist(), "faces": faces.tolist(), "alpha": self.alpha,
                      "color": self.color, "reference_path": self.reference_path})
        return dict_

    @classmethod
    def dict_to_object(cls, dict_, **kwargs) -> "OpenTriangleShell3D":
        """Overload of 'dict_to_object' for performance."""
        vertices = dict_["vertices"]
        faces = dict_["faces"]
        name = dict_["name"]

        triangle_shell = cls.from_mesh_data(vertices, faces, name)
        triangle_shell.alpha = dict_["alpha"]
        triangle_shell.color = dict_["color"]
        triangle_shell.reference_path = dict_.get("reference_path", design3d.PATH_ROOT)
        return triangle_shell

    def to_display_triangle_shell(self) -> "DisplayTriangleShell3D":
        """
        Create a DisplayTriangleShell3D from the current TriangleShell3D.

        :return: The created DisplayTriangleShell3D.
        :rtype: DisplayTriangleShell3D
        """
        return DisplayTriangleShell3D.from_triangle_shell(self)


class ClosedTriangleShell3D(OpenTriangleShell3D, ClosedShell3D):
    """
    A 3D closed shell composed of multiple triangle faces.

    This class represents a 3D closed shell, which is a collection of connected
    triangle faces with a volume. It is a subclass of both the `ClosedShell3D`
    and `OpenTriangleShell3D` classes and inherits all of their attributes and
    methods.

    :param faces: The triangle faces of the shell.
    :type faces: List[`Triangle3D`]
    :param color: The color of the shell.
    :type color: Tuple[float, float, float]
    :param alpha: The transparency of the shell, should be a value in the range (0, 1).
    :type alpha: float
    :param name: The name of the shell.
    :type name: str
    """

    def __init__(
        self,
        faces: List[design3d.faces.Triangle3D],
        color: Tuple[float, float, float] = None,
        alpha: float = 1.0,
        reference_path: str = design3d.PATH_ROOT,
        name: str = "",
    ):
        OpenTriangleShell3D.__init__(self, faces=faces, color=color, alpha=alpha, name=name)
        ClosedShell3D.__init__(self, faces=faces, color=color, alpha=alpha, reference_path=reference_path, name=name)

    def are_normals_pointing_outwards(self):
        """Verifies if all face's normal are pointing outwards the closed shell."""
        return not any(self.point_inside(face.middle() + face.normal() * 1e-4) for face in self.faces)

    def are_normals_pointing_inwards(self):
        """Verifies if all face's normal are pointing inwards the closed shell."""
        return not any(not self.point_inside(face.middle() + face.normal() * 1e-4) for face in self.faces)

    def turn_normals_outwards(self):
        """
        Turns the normals of the closed shells faces always outwards.

        :return: A new ClosedTriangleShell3D object having all faces normals pointing outwards.
        """
        new_faces = []
        for face in self.faces:
            if self.point_inside(face.middle() + face.normal() * 1e-5):
                new_faces.append(design3d.faces.Triangle3D(*face.points[::-1]))
            else:
                new_faces.append(face)
        return ClosedTriangleShell3D(new_faces)

    def turn_normals_inwards(self):
        """
        Turns the normals of the closed shells faces always inwards.

        :return: A new ClosedTriangleShell3D object having all faces normals pointing inwards.
        """
        new_faces = []
        for face in self.faces:
            if not self.point_inside(face.middle() + face.normal() * 1e-5):
                new_faces.append(design3d.faces.Triangle3D(*face.points[::-1]))
            else:
                new_faces.append(face)
        return ClosedTriangleShell3D(new_faces)


class DisplayTriangleShell3D(Shell3D):
    """
    A Triangle Shell 3D optimized for display and saving purpose.

    This shell has the particularity to not instantiate the Triangle3D objects, to reduce memory usage and improve
    performance.
    """

    def __init__(self, positions: NDArray[float], indices: NDArray[int],
                 reference_path: str = design3d.PATH_ROOT, name: str = ""):
        """
        Instantiate the DisplayTriangleShell3D.

        :param positions: A 3D numpy array of float representing the positions of the vertices of the triangles.
        :param indices: A 3D numpy array of int representing the indices of the vertices representing the triangles.
        :param name: A name for the DisplayTriangleShell3D, optional.
        """
        warnings.warn(
            "'design3d.shells.DisplayTriangleShell3D' class is deprecated. Use 'design3d.display.Mesh3D' instead",
            DeprecationWarning
        )

        self.positions = positions
        self.indices = indices

        # Avoid saving the faces for memory and performance
        Shell3D.__init__(self, faces=[], reference_path=reference_path, name=name)

    @classmethod
    def from_triangle_shell(
        cls, triangle_shell: Union["OpenTriangleShell3D", "ClosedTriangleShell3D"]
    ) -> "DisplayTriangleShell3D":
        """
        Instantiate a DisplayTriangleShell3D from an OpenTriangleShell3D or a ClosedTriangleShell3D.

        :param triangle_shell: The triangle shell to create the DisplayTriangleShell3D from.
        :type triangle_shell: OpenTriangleShell3D | ClosedTriangleShell3D

        :return: The created DisplayTriangleShell3D.
        :rtype: DisplayTriangleShell3D
        """
        positions, indices = triangle_shell.to_mesh_data(round_vertices=True, n_decimals=6)
        name = triangle_shell.name

        display_triangle_shell = cls(positions, indices, name)

        display_triangle_shell.alpha = triangle_shell.alpha
        display_triangle_shell.color = triangle_shell.color

        return display_triangle_shell

    def get_bounding_box(self) -> design3d.core.BoundingBox:
        """Gets the Shell bounding box."""
        bbox_min, bbox_max = np.min(self.positions, axis=0), np.max(self.positions, axis=0)

        return design3d.core.BoundingBox(bbox_min[0], bbox_max[0], bbox_min[1], bbox_max[1], bbox_min[2], bbox_max[2])

    def babylon_meshes(self, merge_meshes=True):
        """Overload of 'babylon_meshes' for performance."""

        babylon_mesh = {"positions": self.positions.flatten().tolist(), "indices": self.indices.flatten().tolist()}
        babylon_mesh.update(self.babylon_param())

        return [babylon_mesh]

    def to_dict(self, *args, **kwargs):
        """Overload of 'to_dict' for performance."""
        dict_ = self.base_dict()

        dict_["positions"] = self.positions.tolist()
        dict_["indices"] = self.indices.tolist()
        dict_["alpha"] = self.alpha
        dict_["color"] = self.color

        return dict_

    @classmethod
    def dict_to_object(cls, dict_, **kwargs) -> 'DisplayTriangleShell3D':
        """Overload of 'dict_to_object' for performance."""
        positions = np.array(dict_["positions"])
        indices = np.array(dict_["indices"])
        name = dict_["name"]

        display_triangle_shell = cls(positions, indices, name)

        display_triangle_shell.alpha = dict_["alpha"]
        display_triangle_shell.color = dict_["color"]
        return display_triangle_shell

    def concatenate(self, other: "DisplayTriangleShell3D") -> "DisplayTriangleShell3D":
        """
        Concatenates two DisplayTriangleShell3D instances into a single instance.

        This method merges the positions and indices of both shells. If the same vertex exists in both shells,
        it is only included once in the merged shell to optimize memory usage. It also ensures that each face is
        represented uniquely by sorting the vertices of each triangle.

        :param other: Another DisplayTriangleShell3D instance to concatenate with this instance.
        :return: A new DisplayTriangleShell3D instance representing the concatenated shells.
        """
        if len(self.positions) == 0 or len(self.indices) == 0:
            return other
        if len(other.positions) == 0 or len(other.indices) == 0:
            return self

        # Merge and remove duplicate vertices
        merged_positions = np.vstack((self.positions, other.positions))
        unique_positions, indices_map = np.unique(merged_positions, axis=0, return_inverse=True)

        # Adjust indices to account for duplicates and offset from concatenation
        self_indices_adjusted = self.indices
        other_indices_adjusted = other.indices + len(self.positions)

        # Re-map indices to unique vertices
        all_indices = np.vstack((self_indices_adjusted, other_indices_adjusted))
        final_indices = indices_map[all_indices]

        # Use np.unique to find unique subarrays
        _, unique_indices = np.unique(np.sort(final_indices, axis=1), axis=0, return_index=True)

        # Get the unique subarrays
        merged_indices = final_indices[unique_indices]

        # Create a new DisplayTriangleShell3D with merged data
        return DisplayTriangleShell3D(
            positions=unique_positions, indices=merged_indices, name=self.name + "+" + other.name
        )

    def __add__(self, other: "DisplayTriangleShell3D") -> "DisplayTriangleShell3D":
        """
        Overloads the + operator to concatenate two DisplayTriangleShell3D instances.

        :param other: Another DisplayTriangleShell3D instance to concatenate with this instance.
        :type other: DisplayTriangleShell3D

        :return: A new DisplayTriangleShell3D instance representing the concatenated shells.
        :rtype: DisplayTriangleShell3D
        """
        return self.concatenate(other)

    def __hash__(self):
        return hash(
            (
                self.__class__.__name__,
                (tuple(self.indices[0]), tuple(self.indices[-1]), len(self.indices)),
                (tuple(self.positions[0]), tuple(self.positions[-1]), len(self.positions)),
            )
        )

    def __eq__(self, other):
        return hash(self) == hash(other)

    def _data_hash(self):
        return hash(
            (
                self.__class__.__name__,
                (tuple(self.indices[0]), tuple(self.indices[-1]), len(self.indices)),
                (tuple(self.positions[0]), tuple(self.positions[-1]), len(self.positions)),
            )
        )

    def _data_eq(self, other_object):
        if other_object.__class__.__name__ != self.__class__.__name__:
            return False
        return self._data_hash() == other_object._data_hash()
