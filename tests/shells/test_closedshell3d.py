import math
import unittest
import os
import numpy

import dessia_common.core
import design3d
from design3d import edges, faces, primitives3d, wires, surfaces, shells


folder = os.path.join(os.path.dirname(os.path.realpath(__file__)))


class TestClosedShell3D(unittest.TestCase):
    def test_union_adjacent_blocks(self):
        frame1 = design3d.Frame3D(design3d.Point3D(0, 0, 0), design3d.X3D, design3d.Y3D, design3d.Z3D)
        frame2 = design3d.Frame3D(design3d.Point3D(0, 1, 0), design3d.X3D, design3d.Y3D, 3 * design3d.Z3D)
        block1 = primitives3d.Block(frame1)
        block2 = primitives3d.Block(frame2)
        closed_shell1 = shells.ClosedShell3D(block1.faces)
        closed_shell2 = shells.ClosedShell3D(block2.faces)
        block3 = closed_shell1.union(closed_shell2)
        block3[0].merge_faces()
        self.assertEqual(len(block3[0].faces), 10)

        contour = design3d.wires.ClosedPolygon2D([design3d.Point2D(0, 0), design3d.Point2D(-1, 0),
                                                 design3d.Point2D(-1, 1), design3d.Point2D(1, 1),
                                                 design3d.Point2D(1, -1), design3d.Point2D(0, -1)])
        extrude1 = design3d.primitives3d.ExtrudedProfile(
            design3d.OXYZ, contour, [], -1)
        frame1 = design3d.Frame3D(design3d.Point3D(0, 0, 0.5), 2 * design3d.X3D, 2 * design3d.Y3D, design3d.Z3D)
        block1 = design3d.primitives3d.Block(frame1)
        union1 = extrude1.union(block1)
        union1[0].merge_faces()
        self.assertEqual(len(union1[0].faces), 9)

        contour_primitives = [edges.LineSegment2D(start, end) for start, end in [
            (design3d.Point2D(0.0, 0.0), design3d.Point2D(-0.03, 0.0)),
            (design3d.Point2D(-0.03, 0.0), design3d.Point2D(-0.03, 0.02)),
            (design3d.Point2D(-0.03, 0.02), design3d.Point2D(-0.020436, 0.029871)),
            (design3d.Point2D(-0.020436, 0.029871), design3d.Point2D(0.0, 0.029871)),
            (design3d.Point2D(0.0, 0.029871), design3d.Point2D(0.0, 0.0))]]
        extruded_prifile1 = primitives3d.ExtrudedProfile(design3d.OYZX,
                                                         wires.Contour2D(contour_primitives), [],
                                                         0.01, (0.4, 0.1, 0.1), 0.6)
        extruded_prifile2 = extruded_prifile1.translation(design3d.Vector3D(0.01, 0, 0))
        union_shell1_shell2 = extruded_prifile1.union(extruded_prifile2)[0]
        union_shell1_shell2.merge_faces()
        self.assertEqual(len(union_shell1_shell2.faces), 7)
        boundary1 = primitives3d.Block(design3d.Frame3D(design3d.O3D, design3d.X3D, 0.3 * design3d.Y3D, 0.1 * design3d.Z3D))
        boundary2 = primitives3d.Block(
            design3d.Frame3D(design3d.O3D, 0.3 * design3d.X3D, 0.8 * design3d.Y3D, 0.2 * design3d.Z3D))
        boundary2 = boundary2.translation(offset=(0.5 + 0.15) * design3d.X3D)
        union = boundary1.union(boundary2)[0]
        self.assertEqual(len(union.faces), 11)

    def test_set_operations_blocks(self):
        box_red = primitives3d.Block(
            design3d.Frame3D(design3d.Point3D(0, 0, 0), design3d.Vector3D(0.4, 0, 0),
                            design3d.Vector3D(0, 0.4, 0), design3d.Vector3D(0, 0, 0.4)),
            color=(0.2, 1, 0.4), alpha=0.6)
        box_green = box_red.frame_mapping(design3d.Frame3D(design3d.Point3D(-0.4, 0, -0.1), design3d.Vector3D(1, 0, 0),
                                                          design3d.Vector3D(0, 1, 0), design3d.Vector3D(0, 0, 1)), 'new')
        union_red_green_boxes = box_red.union(box_green)[0]
        union_red_green_boxes.merge_faces()
        self.assertEqual(len(union_red_green_boxes.faces), 10)

        box_blue = primitives3d.Block(
            design3d.Frame3D(design3d.Point3D(0.1, 0, 0), design3d.Vector3D(0.2, 0, 0),
                            design3d.Vector3D(0, 0.1, 0), design3d.Vector3D(0, 0, 1)),
            alpha=0.6)
        box_blue2 = box_blue.frame_mapping(design3d.Frame3D(design3d.Point3D(0.2, 0, 0), design3d.Vector3D(1, 0, 0),
                                                           design3d.Vector3D(0, 1.8, 0), design3d.Vector3D(0, 0, 1)),
                                           'old')
        union_blue_blue2_boxes = box_blue.union(box_blue2)[0]
        union_blue_blue2_boxes.merge_faces()
        self.assertEqual(len(union_blue_blue2_boxes.faces), 10)

        union_box = union_red_green_boxes.union(union_blue_blue2_boxes)[0]
        union_box.merge_faces()
        self.assertEqual(len(union_box.faces), 28)
        # subtraction_box = union_red_green_boxes.subtract(union_blue_blue2_boxes)
        intersection_box = union_red_green_boxes.intersection(union_blue_blue2_boxes)[0]
        intersection_box.merge_faces()
        self.assertEqual(len(intersection_box.faces), 12)
        # subtraction_closedbox = union_red_green_boxes.subtract_to_closed_shell(union_blue_blue2_boxes)[0]
        # subtraction_closedbox.merge_faces()
        # self.assertEqual(len(subtraction_closedbox), 16)

    def test_union_equal_overlapping_blocks(self):
        frame1 = design3d.Frame3D(design3d.Point3D(0, 0, 0), design3d.X3D, design3d.Y3D, design3d.Z3D)
        frame2 = design3d.Frame3D(design3d.Point3D(0, 0.8, 0), design3d.X3D, design3d.Y3D, design3d.Z3D)
        block1 = design3d.primitives3d.Block(frame1)
        block2 = design3d.primitives3d.Block(frame2)
        block3 = block1.union(block2)
        block3[0].merge_faces()
        self.assertEqual(len(block3[0].faces), 6)

    def test_union_block1_inside_block1(self):
        contour = wires.ClosedPolygon2D([design3d.Point2D(0, 0), design3d.Point2D(-1, 0),
                                         design3d.Point2D(-1, 1), design3d.Point2D(1, 1),
                                         design3d.Point2D(1, -1), design3d.Point2D(0, -1)])
        extrude1 = design3d.primitives3d.ExtrudedProfile(design3d.OXYZ,
                                                        contour, [], -1)
        frame1 = design3d.Frame3D(design3d.Point3D(0, 0.5, -0.5), 2 * design3d.X3D, design3d.Y3D, design3d.Z3D)
        block1 = design3d.primitives3d.Block(frame1)
        union1 = extrude1.union(block1)[0]
        self.assertEqual(len(union1.faces), 8)

    def test_union_two_disjoint_objects(self):
        poly1_vol1 = wires.ClosedPolygon3D([design3d.Point3D(-0.1, -0.05, 0), design3d.Point3D(-0.15, 0.1, 0),
                                            design3d.Point3D(0.05, 0.2, 0), design3d.Point3D(0.12, 0.15, 0),
                                            design3d.Point3D(0.1, -0.02, 0)])

        poly2_vol1 = poly1_vol1.rotation(design3d.O3D, design3d.Z3D, math.pi).translation(0.2 * design3d.Z3D)
        poly3_vol1 = poly2_vol1.rotation(design3d.O3D, design3d.Z3D, math.pi / 8).translation(
            0.1 * (design3d.Z3D + design3d.X3D + design3d.Y3D))

        shell_faces = [faces.Triangle3D(*points)
                       for points in poly1_vol1.sewing(poly2_vol1, design3d.X3D, design3d.Y3D)] + \
                      [faces.Triangle3D(*points)
                       for points in poly2_vol1.sewing(poly3_vol1, design3d.X3D, design3d.Y3D)]

        plane3d_1 = surfaces.Plane3D.from_plane_vectors(design3d.O3D, design3d.X3D, design3d.Y3D)
        surf2d_1 = surfaces.Surface2D(poly1_vol1.to_2d(design3d.O3D, design3d.X3D, design3d.Y3D), [])

        plane3d_2 = surfaces.Plane3D.from_plane_vectors(0.3 * design3d.Z3D.to_point(), design3d.X3D, design3d.Y3D)
        surf2d_2 = surfaces.Surface2D(poly3_vol1.to_2d(design3d.O3D, design3d.X3D, design3d.Y3D), [])
        shell_faces += [faces.PlaneFace3D(plane3d_1, surf2d_1), faces.PlaneFace3D(plane3d_2, surf2d_2)]

        shell1 = shells.ClosedShell3D(shell_faces)
        shell2 = shell1.translation(design3d.Point3D(0, -0.28, -0.2)).rotation(design3d.O3D, design3d.X3D, math.pi)
        union_shell1_shell2 = shell1.union(shell2)
        self.assertEqual(len(union_shell1_shell2), 2)

    def test_cut_by_plane(self):
        boundary1 = primitives3d.Block(design3d.Frame3D(design3d.O3D, design3d.X3D, 0.3 * design3d.Y3D, 0.1 * design3d.Z3D))
        boundary2 = primitives3d.Block(
            design3d.Frame3D(design3d.O3D, 0.4 * design3d.X3D, 0.8 * design3d.Y3D, 0.4 * design3d.Z3D))
        boundary2 = boundary2.translation(offset=(0.5 + 0.14) * design3d.X3D)
        boundary2 = boundary2.translation(offset=(0.1) * design3d.Z3D)
        union = boundary1.union(boundary2)[0]
        center = union.bounding_box.center
        plane = surfaces.Plane3D.from_normal(center, design3d.Y3D)
        cut_by_plane = union.cut_by_plane(plane)
        self.assertEqual(len(cut_by_plane), 1)
        self.assertAlmostEqual(cut_by_plane[0].area(), 0.254)

    def test_intersection(self):
        box1 = primitives3d.Block(
            design3d.Frame3D(design3d.Point3D(0, 0, 0), design3d.Vector3D(0.6, 0, 0),
                            design3d.Vector3D(0, 0.6, 0), design3d.Vector3D(0, 0, 0.6)), color=(1, 0.2, 0.2),
            alpha=0.6)
        box2 = primitives3d.Block(
            design3d.Frame3D(design3d.Point3D(0, 0, 0), design3d.Vector3D(0.3, 0, 0),
                            design3d.Vector3D(0, 0.3, 0), design3d.Vector3D(0, 0, 0.3)), color=(.1, 0.2, 1),
            alpha=0.6)
        self.assertEqual(box1.intersection(box2)[0], box2)
        box3 = primitives3d.Block(
            design3d.Frame3D(design3d.Point3D(.3, 0, 0), design3d.Vector3D(0.3, 0, 0),
                            design3d.Vector3D(0, 0.3, 0), design3d.Vector3D(0, 0, 0.3)), color=(.1, 0.2, 1), alpha=0.6)
        expected_box = primitives3d.Block(
            design3d.Frame3D(design3d.Point3D(.15 * 3/2, 0, 0), design3d.Vector3D(0.15, 0, 0),
                            design3d.Vector3D(0, 0.3, 0), design3d.Vector3D(0, 0, 0.3)), color=(.1, 0.2, 1), alpha=0.6)
        self.assertTrue(all(expected_box.face_on_shell(face) for face in box1.intersection(box3)[0].faces))
        box4 = primitives3d.Block(
            design3d.Frame3D(design3d.Point3D(.5, 0, 0), design3d.Vector3D(0.3, 0, 0),
                            design3d.Vector3D(0, 0.3, 0), design3d.Vector3D(0, 0, 0.3)), color=(.1, 0.2, 1), alpha=0.6)
        self.assertFalse(box1.intersection(box4))

    def test_point_belongs(self):
        closed_shell = dessia_common.core.DessiaObject.from_json(
            os.path.join(folder, 'test_closed_shell_point_belongs2.json')).primitives[0]
        points = [design3d.Point3D(-.2, -0.6, 0.08), design3d.Point3D(-0.340920128805, -0.418071198223, 0.007036661148),
                  design3d.Point3D(-0.287522562519, -0.574786328164, 0.157256628036),
                  design3d.Point3D(-0.314221345662, -0.522547951517, 0.057109983444)]
        expected_results = [True, True, False, True]
        for i, expected_result in enumerate(expected_results):
            self.assertEqual(closed_shell.point_inside(points[i]), expected_result)

    def test_minimum_distance(self):
        closed_shell = dessia_common.core.DessiaObject.from_json(
            os.path.join(folder, 'test_shells_distance2.json'))
        u_vector = design3d.Vector3D(-0.5773502691896258, -0.5773502691896258, -0.5773502691896258)
        v_vector = design3d.Vector3D(0.8164965809277258, -0.40824829046386313, -0.40824829046386313)
        w_vector = design3d.Vector3D(0.0, -0.7071067811865476, 0.7071067811865476)
        frame = design3d.Frame3D(design3d.Point3D(-0.01661984584195119, -0.04221251977732219, -0.04351622102493058),
                                u_vector, v_vector, w_vector)
        fm_shell = closed_shell.frame_mapping(frame, 'new')
        min_distance = closed_shell.minimum_distance(fm_shell, False)
        self.assertAlmostEqual(min_distance, 0.022811959708641426, 6)
        frame = design3d.Frame3D(design3d.Point3D(0.011516851705803667, 0.012859651289434018, 0.015147046170848444),
                                u_vector, v_vector, w_vector)
        fm_shell = closed_shell.frame_mapping(frame, 'new')
        min_distance, point1, point2 = closed_shell.minimum_distance(fm_shell, True)
        self.assertEqual(min_distance, 0.0)

    def test_volume(self):
        closed_shell = dessia_common.core.DessiaObject.from_json(os.path.join(folder, 'test_shell_volume.json'))
        closed_shell2 = closed_shell.rotation(design3d.O3D - 0.95 * design3d.X3D, design3d.Z3D, numpy.pi / 2)
        closed_shell2 = closed_shell2.translation(-0.95 * design3d.X3D + 0.45 * design3d.Z3D + 0.2 * design3d.Y3D)
        self.assertAlmostEqual(closed_shell.volume(), closed_shell2.volume())


if __name__ == '__main__':
    unittest.main()
