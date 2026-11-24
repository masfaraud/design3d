#!/usr/bin/env python3
"""
Extended primitives 2D classes.
"""

import math

import matplotlib.patches
import matplotlib.pyplot as plt

import design3d
from design3d import PATH_ROOT, curves, edges, wires
from design3d.core import EdgeStyle
from design3d.primitives import RoundedLineSegments


class RoundedLineSegments2D(RoundedLineSegments):
    """
    A class representing a series of rounded line segments in 2D.

    This class inherits from the `RoundedLineSegments` class,
    and provides methods to work with rounded line segments in 2D.

    :param points: The list of points defining the line segments.
    :type points: List[design3d.Point2D]
    :param radius: The dictionary mapping segment indices to their respective radii.
    :type radius: Dict[int, float]
    :param adapt_radius: Flag indicating whether to adapt the radius based on segment length.
        Defaults to False.
    :type adapt_radius: bool, optional
    :param name: The name of the rounded line segments. Defaults to ''.
    :type name: str, optional
    """

    line_class = design3d.edges.LineSegment2D
    arc_class = design3d.edges.Arc2D

    def __init__(
        self,
        points: list[design3d.Point2D],
        radius: dict[int, float],
        adapt_radius: bool = False,
        reference_path: str = PATH_ROOT,
        name: str = "",
    ):
        RoundedLineSegments.__init__(
            self, points=points, radius=radius, adapt_radius=adapt_radius, reference_path=reference_path, name=name
        )

    def arc_features(self, point_index: int):
        """
        Returns the arc features for point at index.
        """
        # raise NotImplementedError
        radius = self.radius[point_index]
        pt1, pti, pt2 = self.get_points(point_index)
        # TODO: change to point_distance ------> done
        point_distance1 = (pt1 - pti).norm()
        point_distance2 = (pt2 - pti).norm()
        point_distance3 = (pt1 - pt2).norm()
        alpha = (
            math.acos(
                -(point_distance3**2 - point_distance1**2 - point_distance2**2)
                / (2 * point_distance1 * point_distance2)
            )
            / 2.0
        )
        point_distance = radius / math.tan(alpha)

        u1 = (pt1 - pti) / point_distance1
        u2 = (pt2 - pti) / point_distance2

        p3 = pti + u1 * point_distance
        p4 = pti + u2 * point_distance

        w = (u1 + u2).to_vector()
        if not w.is_close(design3d.Vector2D(0, 0)):
            w = w.unit_vector()

        v1 = u1.deterministic_unit_normal_vector()
        if v1.dot(w) < 0:
            v1 = -v1

        point_curvature = p3 + v1 * radius
        point_interior = point_curvature - radius * w

        return p3, point_interior, p4, point_distance, alpha

    def rotation(self, center: design3d.Point2D, angle: float):
        """
        OpenedRoundedLineSegments2D rotation.

        :param center: rotation center
        :param angle: angle rotation
        :return: a new rotated OpenedRoundedLineSegments2D
        """
        return self.__class__(
            [point.rotation(center, angle) for point in self.points],
            self.radius,
            adapt_radius=self.adapt_radius,
            name=self.name,
        )

    def translation(self, offset: design3d.Vector2D):
        """
        OpenedRoundedLineSegments2D translation.

        :param offset: translation vector
        :return: A new translated OpenedRoundedLineSegments2D
        """
        return self.__class__(
            [point.translation(offset) for point in self.points],
            self.radius,
            adapt_radius=self.adapt_radius,
            name=self.name,
        )

    def invert(self):
        """
        Returns the rounded line segments traveled in the opposite direction.

        The points are reversed, and each radius follows its point to its new index.
        """
        last_index = len(self.points) - 1
        return self.__class__(
            self.points[::-1],
            {last_index - index: radius for index, radius in self.radius.items()},
            adapt_radius=self.adapt_radius,
            reference_path=self.reference_path,
            name=self.name,
        )

    def _helper_offset_points_and_radii(self, vectors, number_points, offset):
        """
        Helper method to get offset points and new radii for offset method.

        :param vectors: offset vectors.
        :param number_points: number of points.
        :param offset: offset.
        :return: list of offset points and radii.
        """
        offset_vectors = []
        new_radii = {}
        offset_points = []

        for i in range((not self.closed), number_points - (not self.closed)):
            check = False
            normal_i = vectors[2 * i - 1] + vectors[2 * i]
            if normal_i.is_close(design3d.Vector2D(0, 0)):
                normal_i = vectors[2 * i]
                normal_i = normal_i.normal_vector()
                offset_vectors.append(normal_i)
            else:
                normal_i = normal_i.unit_vector()
                if normal_i.dot(vectors[2 * i - 1].normal_vector()) > 0:
                    normal_i = -normal_i
                    check = True
                offset_vectors.append(normal_i)

            if i in self.radius:
                if (check and offset > 0) or (not check and offset < 0):
                    new_radius = self.radius[i] + abs(offset)
                else:
                    new_radius = self.radius[i] - abs(offset)
                if new_radius > 0:
                    new_radii[i] = new_radius
                else:
                    if self.adapt_radius:
                        new_radii[i] = 1e-6

            normal_vector1 = -vectors[2 * i - 1].normal_vector().unit_vector()
            normal_vector2 = vectors[2 * i].normal_vector().unit_vector()
            alpha = math.acos(normal_vector1.dot(normal_vector2))

            offset_point = self.points[i] + offset / math.cos(alpha / 2) * offset_vectors[i - (not self.closed)]
            offset_points.append(offset_point)
        return offset_points, new_radii

    def offset(self, offset):
        """
        Return a new rounded line segment with the specified offset.

        This method creates a new rounded line segment by offsetting the current one by a given distance.
        As for Wire2D.offset, a positive offset moves the line segments to the right of the direction of travel: it
        enlarges a counterclockwise contour and shrinks a clockwise one.

        :param offset: The offset distance for the new rounded line segment.
        :type offset: float

        :return: A new RoundedLineSegments2D instance with the specified offset.
        :rtype: RoundedLineSegments2D
        """
        # The computation below offsets to the left of the direction of travel.
        offset = -offset
        number_points = len(self.points)
        vectors = []
        for i in range(number_points - 1):
            v1 = (self.points[i + 1] - self.points[i]).unit_vector()
            v2 = (self.points[i] - self.points[i + 1]).unit_vector()
            vectors.extend([v1, v2])

        if self.closed:
            v1 = (self.points[0] - self.points[-1]).unit_vector()
            v2 = (self.points[-1] - self.points[0]).unit_vector()
            vectors.extend([v1, v2])
        offset_points, new_radii = self._helper_offset_points_and_radii(vectors, number_points, offset)

        if not self.closed:
            normal_1 = vectors[0].normal_vector()
            offset_points.insert(0, self.points[0] + offset * normal_1)

            n_last = vectors[-1].normal_vector()
            n_last = -n_last
            offset_points.append(self.points[-1] + offset * n_last)

        return self.__class__(offset_points, new_radii, adapt_radius=self.adapt_radius)

    def _offset_directive_vector_helper(self, line_indexes):
        """
        Computes the directive vectors between which the offset will be drawn.

        :param line_indexes: A list of consecutive line indexes.
        :return: directive vector 1 and 2.
        """
        dir_vec_1 = None
        dir_vec_2 = None

        if line_indexes[0] == 0 and not self.closed:
            pass
        else:
            dir_vec_1 = self.points[line_indexes[0]] - self.points[line_indexes[0] - 1]

        if line_indexes[-1] == len(self.points) - (2 - self.closed):
            if not self.closed:
                pass
            else:
                dir_vec_2 = design3d.Vector2D(self.points[0] - self.points[1])
        elif self.closed and line_indexes[-1] == len(self.points) - 2:
            dir_vec_2 = design3d.Vector2D(self.points[line_indexes[-1] + 1] - self.points[0])
        else:
            dir_vec_2 = self.points[line_indexes[-1] + 1] - self.points[line_indexes[-1] + 2]

        if dir_vec_1 is None:
            dir_vec_1 = dir_vec_2
        if dir_vec_2 is None:
            dir_vec_2 = dir_vec_1

        dir_vec_1 = dir_vec_1.unit_vector()
        dir_vec_2 = dir_vec_2.unit_vector()
        return dir_vec_1, dir_vec_2

    def get_offset_normal_vectors(self, line_indexes):
        """
        Gets offset normal vectors.

        :param line_indexes:
        :return: A list of consecutive line indexes.
        """
        normal_vectors = []
        for index in line_indexes:
            if index == len(self.points) - 1:
                normal_vectors.append(design3d.Vector2D(self.points[0] - self.points[index]).normalVector(unit=True))
            else:
                normal_vectors.append((self.points[index + 1] - self.points[index]).unit_normal_vector())
        return normal_vectors

    def _helper_get_offset_vectors(self, line_indexes, directive_vector1, directive_vector2):
        """
        Helper method: get offset vectors.

        """
        intersection = design3d.Point2D.line_intersection(
            curves.Line2D(self.points[line_indexes[0]], self.points[line_indexes[0]] + directive_vector1),
            curves.Line2D(self.points[line_indexes[-1] + 1], self.points[line_indexes[-1] + 1] + directive_vector2),
        )
        vec1 = intersection.point_distance(self.points[line_indexes[0]]) * directive_vector1
        vec2 = intersection.point_distance(self.points[line_indexes[-1] + 1]) * directive_vector2
        return vec1, vec2

    def get_offset_new_points(
        self, line_indexes, offset, distance_dir1, distance_dir2, directive_vector1, directive_vector2, normal_vectors
    ):
        """
        Get Offset new points.

        """
        if len(line_indexes) <= 1:
            return []
        vec1, vec2 = self._helper_get_offset_vectors(line_indexes, directive_vector1, directive_vector2)
        new_points = {line_indexes[0]: self.points[line_indexes[0]] + distance_dir1 * directive_vector1}

        for i, index in enumerate(line_indexes[1:]):
            coeff_vec_2 = design3d.Point2D.point_distance(
                self.points[line_indexes[0]], self.points[index]
            ) / design3d.Point2D.point_distance(self.points[line_indexes[0]], self.points[line_indexes[-1] + 1])
            coeff_vec_1 = 1 - coeff_vec_2
            if directive_vector1.dot(normal_vectors[i + 1]) < 0:
                coeff_vec_1 = -coeff_vec_1
            if directive_vector2.dot(normal_vectors[i + 1]) < 0:
                coeff_vec_2 = -coeff_vec_2
            index_dir_vector = coeff_vec_1 * vec1 + coeff_vec_2 * vec2
            index_dot = index_dir_vector.dot(normal_vectors[i + 1])
            new_points[index] = self.points[index] + (offset / index_dot) * index_dir_vector
        if self.closed and line_indexes[-1] == len(self.points) - 1:
            new_points[0] = self.points[0] + distance_dir2 * directive_vector2
        else:
            new_points[line_indexes[-1] + 1] = self.points[line_indexes[-1] + 1] + distance_dir2 * directive_vector2
        return new_points

    def offset_lines(self, line_indexes, offset):
        """
        Offsets some consecutive aligned lines, the other points being kept.

        Line indexes is a list of consecutive line indexes, line_indexes = 0 being the 1st line.
        These lines should all be aligned.

        if self.close last line_index can be len(self.points)-1
        if not, last line_index can be len(self.points)-2

        As for offset, a positive offset moves the lines to the right of the direction of travel.
        """
        return self._offset_lines_to_the_left(line_indexes, -offset)

    def _offset_lines_to_the_left(self, line_indexes, offset):
        """Offsets some consecutive aligned lines to the left of the direction of travel."""
        new_linesegment2d_points = []

        dir_vec_1, dir_vec_2 = self._offset_directive_vector_helper(line_indexes)

        normal_vectors = self.get_offset_normal_vectors(line_indexes)

        # =============================================================================
        # COMPUTES THE ANGLE BETWEEN THE NORMAL VECTOR OF THE SURFACE TO OFFSET AND
        # THE DIRECTIVE VECTOR IN ORDER TO SET THE NEW POINT AT THE RIGHT DISTANCE
        # =============================================================================
        dot1 = dir_vec_1.dot(normal_vectors[0])
        dot2 = dir_vec_2.dot(normal_vectors[-1])

        if math.isclose(dot1, 0, abs_tol=1e-9):
            # call function considering the line before, because the latter and
            # the first offset segment are parallel
            return self._offset_lines_to_the_left([line_indexes[0] - 1] + line_indexes, offset)
        if math.isclose(dot2, 0, abs_tol=1e-9):
            # call function considering the line after, because the latter and
            # the last offset segment are parallel
            return self._offset_lines_to_the_left(line_indexes + [line_indexes[-1] + 1], offset)

        distance_dir1 = offset / dot1
        distance_dir2 = offset / dot2

        new_points = self.get_offset_new_points(
            line_indexes, offset, distance_dir1, distance_dir2, dir_vec_1, dir_vec_2, normal_vectors
        )
        for i, point in enumerate(self.points):
            if i in new_points:
                new_linesegment2d_points.append(new_points[i])
            else:
                new_linesegment2d_points.append(point)

        rls_2d = self.__class__(new_linesegment2d_points, self.radius, adapt_radius=self.adapt_radius)

        return rls_2d


class OpenedRoundedLineSegments2D(RoundedLineSegments2D, wires.Wire2D):
    """
    Opened Rounded LineSegment2D class.

    :param points: Points used to draw the wire.
    :type points: List of Point2D.
    :param radius: Radius used to connect different parts of the wire.
    :type radius: {position1(n): float which is the radius linked the n-1 and n+1 points, position2(n+1):...}.
    """

    def __init__(
        self,
        points: list[design3d.Point2D],
        radius: dict[int, float],
        adapt_radius: bool = False,
        reference_path: str = PATH_ROOT,
        name: str = "",
    ):
        RoundedLineSegments2D.__init__(
            self, points, radius, adapt_radius=adapt_radius, reference_path=reference_path, name=""
        )
        self.closed = False
        wires.Wire2D.__init__(self, self._primitives(), reference_path=reference_path, name=name)


class ClosedRoundedLineSegments2D(RoundedLineSegments2D, wires.Contour2D):
    """
    Defines a polygon with some rounded corners.

    :param points: Points used to draw the wire
    :type points: List of Point2D
    :param radius: Radius used to connect different parts of the wire
    :type radius: {position1(n): float which is the radius linked the n-1 and n+1 points, position2(n+1):...}
    """

    def __init__(
        self,
        points: list[design3d.Point2D],
        radius: dict[int, float],
        adapt_radius: bool = False,
        reference_path: str = PATH_ROOT,
        name: str = "",
    ):
        RoundedLineSegments2D.__init__(
            self, points, radius, adapt_radius=adapt_radius, reference_path=reference_path, name=""
        )
        self.closed = True
        # RoundedLineSegments.__init__(self, points, radius, closed=True, adapt_radius=adapt_radius, name=name)
        wires.Contour2D.__init__(self, self._primitives(), reference_path=reference_path, name=name)

    def copy(self, deep=True, memo=None):
        """Returns a copy of the object."""
        return self.__class__(
            [point.copy(deep, memo) for point in self.points],
            self.radius.copy(),
            self.adapt_radius,
            name="copy_" + self.name,
        )


class ParametricContour2DMixin:
    """
    Common behavior of the parametric 2D profiles placed by a center and an angle.

    Subclasses store their shape parameters as attributes, list them in ``_parameters`` and implement
    ``generic_contour``. Transformations that keep the shape (copy, rotation, translation, frame mapping) return a
    new instance of the subclass with an updated placement. Operations that change the shape (invert, offset, axial
    symmetry, reordering) return the equivalent generic contour, as their result is no longer the parametric profile.
    The profiles are counterclockwise, so a positive offset enlarges them.
    """

    def _parameters(self) -> dict:
        """Returns the shape parameters, as keyword arguments of the constructor."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _parameters")

    def generic_contour(self):
        """Returns the profile as a generic contour of the parent class."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement generic_contour")

    def _local_to_global(self, x: float, y: float) -> design3d.Point2D:
        """Places a point given in the profile local coordinates (centered, not rotated)."""
        cos_angle, sin_angle = math.cos(self.angle), math.sin(self.angle)
        return design3d.Point2D(
            self.center.x + cos_angle * x - sin_angle * y, self.center.y + sin_angle * x + cos_angle * y
        )

    def _placed(self, center: design3d.Point2D, angle: float):
        """Returns the same profile at another placement."""
        return self.__class__(
            **self._parameters(), center=center, angle=angle, reference_path=self.reference_path, name=self.name
        )

    def copy(self, deep=True, memo=None):
        """Returns a copy of the profile."""
        return self._placed(self.center.copy(), self.angle)

    def rotation(self, center: design3d.Point2D, angle: float):
        """
        Rotates the profile.

        :param center: rotation center.
        :param angle: rotation angle.
        :return: a new rotated profile of the same class.
        """
        return self._placed(self.center.rotation(center, angle), self.angle + angle)

    def translation(self, offset: design3d.Vector2D):
        """
        Translates the profile.

        :param offset: translation vector.
        :return: a new translated profile of the same class.
        """
        return self._placed(self.center.translation(offset), self.angle)

    def frame_mapping(self, frame: design3d.Frame2D, side: str):
        """
        Changes the frame of the profile.

        The profiles are symmetric with respect to their local x-axis, so an indirect frame is also handled.

        :param frame: the frame.
        :param side: 'old' or 'new'.
        :return: a new profile of the same class.
        """
        new_center = self.center.frame_mapping(frame, side)
        direction_point = self._local_to_global(1.0, 0.0).frame_mapping(frame, side)
        direction = direction_point - new_center
        return self._placed(new_center, math.atan2(direction.y, direction.x))

    def to_dict(self, *args, **kwargs):
        """Serializes the profile from its parameters."""
        dict_ = self.base_dict()
        dict_.update(self._parameters())
        dict_.update({"center": self.center.to_dict(), "angle": self.angle, "reference_path": self.reference_path})
        return dict_

    def invert(self):
        """Returns the inverted generic contour."""
        return self.generic_contour().invert()

    def order_wire(self, tol=1e-6):
        """Returns the ordered generic contour."""
        return self.generic_contour().order_wire(tol)

    def offset(self, offset):
        """Returns the offset generic contour."""
        return self.generic_contour().offset(offset)

    def axial_symmetry(self, line):
        """Returns the generic contour symmetric with respect to a line."""
        return self.generic_contour().axial_symmetry(line)

    def reorder_contour_at_point(self, point):
        """Returns the generic contour reordered to start at a point."""
        return self.generic_contour().reorder_contour_at_point(point)


class RoundedRectangle2D(ParametricContour2DMixin, ClosedRoundedLineSegments2D):
    """
    A rectangle with its four corners rounded with the same radius.

    :param width: the dimension along the local x-axis.
    :param height: the dimension along the local y-axis.
    :param corner_radius: the radius of the corners. A zero radius gives sharp corners.
    :param center: the center of the rectangle.
    :param angle: the angle between the global x-axis and the width direction.
    """

    def __init__(
        self,
        width: float,
        height: float,
        corner_radius: float,
        center: design3d.Point2D = design3d.O2D,
        angle: float = 0.0,
        reference_path: str = PATH_ROOT,
        name: str = "",
    ):
        self.width = width
        self.height = height
        self.corner_radius = corner_radius
        self.center = center
        self.angle = angle
        half_width, half_height = 0.5 * width, 0.5 * height
        points = [
            self._local_to_global(-half_width, -half_height),
            self._local_to_global(half_width, -half_height),
            self._local_to_global(half_width, half_height),
            self._local_to_global(-half_width, half_height),
        ]
        radius = {i: corner_radius for i in range(4)} if corner_radius else {}
        ClosedRoundedLineSegments2D.__init__(self, points, radius, reference_path=reference_path, name=name)

    def _parameters(self) -> dict:
        return {"width": self.width, "height": self.height, "corner_radius": self.corner_radius}

    def generic_contour(self):
        """Returns the profile as a Contour2D."""
        return wires.Contour2D([primitive.copy() for primitive in self.primitives], reference_path=self.reference_path)

    def _rounded_line_segments(self):
        """Returns the profile as a ClosedRoundedLineSegments2D, used for the offsets."""
        return ClosedRoundedLineSegments2D(
            [point.copy() for point in self.points], self.radius.copy(), reference_path=self.reference_path
        )

    def offset(self, offset):
        """Returns the offset profile, as a ClosedRoundedLineSegments2D. A positive offset enlarges it."""
        return self._rounded_line_segments().offset(offset)

    def offset_lines(self, line_indexes, offset):
        """Returns the profile with some lines offset, as a ClosedRoundedLineSegments2D."""
        return self._rounded_line_segments().offset_lines(line_indexes, offset)


class RegularPolygon2D(ParametricContour2DMixin, wires.ClosedPolygon2D):
    """
    A regular polygon defined by its circumscribed circle.

    :param number_sides: the number of sides.
    :param radius: the radius of the circumscribed circle.
    :param center: the center of the polygon.
    :param angle: the angle between the global x-axis and the direction from the center to the first vertex.
    """

    def __init__(
        self,
        number_sides: int,
        radius: float,
        center: design3d.Point2D = design3d.O2D,
        angle: float = 0.0,
        reference_path: str = PATH_ROOT,
        name: str = "",
    ):
        self.number_sides = number_sides
        self.radius = radius
        self.center = center
        self.angle = angle
        angle_step = 2 * math.pi / number_sides
        points = [
            self._local_to_global(radius * math.cos(i * angle_step), radius * math.sin(i * angle_step))
            for i in range(number_sides)
        ]
        wires.ClosedPolygon2D.__init__(self, points, name=name)
        # ClosedPolygon2D has no reference_path argument: set it after the parent initialization.
        self.reference_path = reference_path

    def _parameters(self) -> dict:
        return {"number_sides": self.number_sides, "radius": self.radius}

    def generic_contour(self):
        """Returns the profile as a ClosedPolygon2D."""
        return wires.ClosedPolygon2D([point.copy() for point in self.points])

    def simplify_polygon(self, min_distance: float = 0.01, max_distance: float = 0.05, angle: float = 15):
        """Returns the simplified generic polygon."""
        return self.generic_contour().simplify_polygon(min_distance, max_distance, angle)


class Slot2D(ParametricContour2DMixin, wires.Contour2D):
    """
    An oblong profile: two parallel lines joined by two half circles.

    :param total_length: the overall length, from one end to the other, along the local x-axis.
    :param width: the width of the slot, which is the diameter of the half circles.
    :param center: the center of the slot.
    :param angle: the angle between the global x-axis and the length direction.
    """

    def __init__(
        self,
        total_length: float,
        width: float,
        center: design3d.Point2D = design3d.O2D,
        angle: float = 0.0,
        reference_path: str = PATH_ROOT,
        name: str = "",
    ):
        self.total_length = total_length
        self.width = width
        self.center = center
        self.angle = angle
        radius = 0.5 * width
        half_straight = 0.5 * total_length - radius
        bottom_right = self._local_to_global(half_straight, -radius)
        top_right = self._local_to_global(half_straight, radius)
        top_left = self._local_to_global(-half_straight, radius)
        bottom_left = self._local_to_global(-half_straight, -radius)
        primitives = [
            edges.LineSegment2D(bottom_left, bottom_right),
            edges.Arc2D.from_3_points(bottom_right, self._local_to_global(half_straight + radius, 0.0), top_right),
            edges.LineSegment2D(top_right, top_left),
            edges.Arc2D.from_3_points(top_left, self._local_to_global(-half_straight - radius, 0.0), bottom_left),
        ]
        wires.Contour2D.__init__(self, primitives, reference_path=reference_path, name=name)

    def _parameters(self) -> dict:
        return {"total_length": self.total_length, "width": self.width}

    def offset(self, offset):
        """
        Returns the offset slot, which is still a slot. A positive offset enlarges it.

        :param offset: offset distance.
        :return: a new Slot2D with the same center and angle.
        """
        return self.__class__(
            self.total_length + 2 * offset,
            self.width + 2 * offset,
            center=self.center.copy(),
            angle=self.angle,
            reference_path=self.reference_path,
            name=self.name,
        )

    def generic_contour(self):
        """Returns the profile as a Contour2D."""
        return wires.Contour2D([primitive.copy() for primitive in self.primitives], reference_path=self.reference_path)


class Measure2D(edges.LineSegment2D):
    """
    Measure 2D class.

    :param unit: 'mm', 'm' or None. If None, the distance won't be in the label.
    """

    def __init__(self, point1, point2, label="", unit: str = "mm", type_: str = "distance"):
        """
        :param unit: 'mm', 'm' or None. If None, the distance won't be in the label.

        """
        # TODO: offset parameter
        edges.LineSegment2D.__init__(self, point1, point2)
        self.label = label
        self.unit = unit
        self.type_ = type_

    def plot(self, ax=None, edge_style: EdgeStyle = None):
        """Plots the Measure2D."""
        if ax is None:
            _, ax = plt.subplots()
        if edge_style is None:
            edge_style = EdgeStyle()
        ndigits = 6
        x1, y1 = self.start
        x2, y2 = self.end
        x_middle, y_middle = 0.5 * (self.start + self.end)
        distance = self.end.point_distance(self.start)

        if self.label != "":
            label = f"{self.label}: "
        else:
            label = ""
        if self.unit == "mm":
            label += f"{round(distance * 1000, ndigits)} mm"
        else:
            label += f"{round(distance, ndigits)} m"

        if self.type_ == "distance":
            arrow = matplotlib.patches.FancyArrowPatch(
                (x1, y1),
                (x2, y2),
                arrowstyle="<|-|>,head_length=10,head_width=5",
                shrinkA=0,
                shrinkB=0,
                color=edge_style.color,
            )
        elif self.type_ == "radius":
            arrow = matplotlib.patches.FancyArrowPatch(
                (x1, y1),
                (x2, y2),
                arrowstyle="-|>,head_length=10,head_width=5",
                shrinkA=0,
                shrinkB=0,
                color=edge_style.color,
            )

        ax.add_patch(arrow)
        if x2 - x1 == 0.0:
            theta = 90.0
        else:
            theta = math.degrees(math.atan((y2 - y1) / (x2 - x1)))
        ax.text(x_middle, y_middle, label, va="bottom", ha="center", rotation=theta)
        return ax
