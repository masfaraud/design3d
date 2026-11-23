import os
import unittest
import design3d
from design3d.wires import Contour2D, Contour3D, Wire2D
from design3d.step import Step
from design3d import edges, core

# %% Contour2d_1

primitives = [
    edges.LineSegment2D(design3d.Point2D(0.001, 0.014), design3d.Point2D(0.001, 0.0125)),
    edges.Arc2D.from_3_points(
        design3d.Point2D(0.001, 0.0125),
        design3d.Point2D(0.009862829911410362, 0.007744326060968065),
        design3d.Point2D(0.012539936203984454, 0.0),
    ),
    edges.Arc2D.from_3_points(
        design3d.Point2D(0.012539936203984454, 0.0),
        design3d.Point2D(0.0, -0.012539936203984454),
        design3d.Point2D(-0.012539936203984454, 0.0),
    ),
    edges.Arc2D.from_3_points(
        design3d.Point2D(-0.012539936203984454, 0.0),
        design3d.Point2D(-0.00921384654213387, 0.008506176103162205),
        design3d.Point2D(-0.001, 0.0125),
    ),
    edges.LineSegment2D(design3d.Point2D(-0.001, 0.0125), design3d.Point2D(-0.001, 0.014)),
    edges.LineSegment2D(design3d.Point2D(-0.001, 0.014), design3d.Point2D(0.001, 0.014)),
]

contour2d_1 = Contour2D(primitives)

# %% Contour2d_2

points2d = [
    design3d.Point2D(0.7557261768236382, 0.047840610095316816),
    design3d.Point2D(0.7557153778090784, 0.053529840943971466),
    design3d.Point2D(0.7548352148318592, 0.059379242604894106),
    design3d.Point2D(0.7509972673886837, 0.06812701209830616),
    design3d.Point2D(0.7463815515547884, 0.06876367708780329),
    design3d.Point2D(0.7426873841819802, 0.06850598841747624),
    design3d.Point2D(0.7386859822441963, 0.0690723949917957),
    design3d.Point2D(0.7344087842895368, 0.0660771254673235),
    design3d.Point2D(0.7316087522378829, 0.0572133737658937),
    design3d.Point2D(0.7306755405178993, 0.04995246337945117),
    design3d.Point2D(0.7310451707836978, 0.044346281865748856),
]

curve2d_1 = edges.BSplineCurve2D(
    degree=3,
    control_points=points2d,
    knot_multiplicities=[4, 1, 1, 1, 1, 1, 1, 1, 4],
    knots=[
        0.0,
        0.26206414743620277,
        0.3531225286567413,
        0.42241139891509305,
        0.4822254408401885,
        0.5440692281614715,
        0.6202023477514225,
        0.7222748100879735,
        1.0,
    ],
)

points2d = [
    design3d.Point2D(0.7310451707836978, 0.044346281865748856),
    design3d.Point2D(0.7308827017192874, 0.03840965331596735),
    design3d.Point2D(0.7318250470334302, 0.03228668394110015),
    design3d.Point2D(0.7354633489443133, 0.023006441447214778),
    design3d.Point2D(0.7402551819180077, 0.022102466430262133),
    design3d.Point2D(0.7440795569187786, 0.02242177670352842),
    design3d.Point2D(0.7482500898246996, 0.02178574616551938),
    design3d.Point2D(0.7525849938211369, 0.025193737559804485),
    design3d.Point2D(0.7553036624157348, 0.03437896214237193),
    design3d.Point2D(0.7561315600530795, 0.042073178367651974),
    design3d.Point2D(0.7557261768236382, 0.047840610095316816),
]

curve2d_2 = edges.BSplineCurve2D(
    degree=3,
    control_points=points2d,
    knot_multiplicities=[4, 1, 1, 1, 1, 1, 1, 1, 4],
    knots=[
        0.0,
        0.26231860269644847,
        0.35446984209379995,
        0.4237193471508679,
        0.48275286541966095,
        0.5439383602451768,
        0.62045686469776,
        0.7233434357617774,
        1.0,
    ],
)

contour2d_2 = Contour2D([curve2d_1, curve2d_2])

points = [
    design3d.Point2D(0.20308817713481986, 0.04966773764193705),
    design3d.Point2D(0.7969119765656952, 0.04966797879396336),
    design3d.Point2D(0.8442697800221348, 0.04966805448106126),
    design3d.Point2D(0.9031379981759905, 0.04545485716230839),
    design3d.Point2D(0.9479619187253645, 0.10517762923653938),
    design3d.Point2D(0.9545454713622077, 0.19659816573695035),
    design3d.Point2D(0.9193352753725873, 0.27036785408838365),
    design3d.Point2D(0.9193352733808331, 0.2891129034169921),
    design3d.Point2D(0.9193352491395294, 0.7108874440320542),
    design3d.Point2D(0.9193352445733572, 0.7296301344365137),
    design3d.Point2D(0.9545453968718225, 0.8034021061594617),
    design3d.Point2D(0.9479618025250582, 0.8948226395224322),
    design3d.Point2D(0.9031378875027738, 0.9545453756361115),
    design3d.Point2D(0.8442696587355882, 0.9503323074053969),
    design3d.Point2D(0.7969118264212707, 0.950332267803071),
    design3d.Point2D(0.203088054423346, 0.9503320443667395),
    design3d.Point2D(0.15573023404235076, 0.9503319931770652),
    design3d.Point2D(0.09686198756850553, 0.9545451189134176),
    design3d.Point2D(0.05203811911069425, 0.8948223672618099),
    design3d.Point2D(0.04545450905371345, 0.8034018054641981),
    design3d.Point2D(0.08066468979315351, 0.7296322065226041),
    design3d.Point2D(0.08066468965825305, 0.7108871704475791),
    design3d.Point2D(0.08066474955300275, 0.289112539074918),
    design3d.Point2D(0.08066475417207301, 0.27036750263798714),
    design3d.Point2D(0.04545459207437027, 0.19659788603626316),
    design3d.Point2D(0.05203818215846509, 0.10517733497317228),
    design3d.Point2D(0.09686210943003962, 0.04545460320088811),
    design3d.Point2D(0.15573034610061637, 0.04966777166777087),
]

contour1_cut_by_wire = Contour2D.from_points(points)

# %% Contour 2

points = [
    design3d.Point2D(0.2030881575366132, 0.04966771677601732),
    design3d.Point2D(0.20308809125575447, 0.2891126765655333),
    design3d.Point2D(0.08066474910267005, 0.2891125988482983),
    design3d.Point2D(0.05674291581332371, 0.28911260559053886),
    design3d.Point2D(0.04267127288273421, 0.311080039363985),
    design3d.Point2D(0.04267123136672513, 0.6889196955746452),
    design3d.Point2D(0.056742861492621116, 0.7108870816261534),
    design3d.Point2D(0.08066469250960157, 0.7108871106086502),
    design3d.Point2D(0.2030880435632797, 0.7108871156873701),
    design3d.Point2D(0.20308804388447252, 0.9503320678576602),
    design3d.Point2D(0.20308798646643267, 0.9876766506444887),
    design3d.Point2D(0.21715969201684732, 1.0),
    design3d.Point2D(0.7828401610275215, 1.0),
    design3d.Point2D(0.7969118753894622, 0.9876767973117213),
    design3d.Point2D(0.7969118376396574, 0.9503322697795179),
    design3d.Point2D(0.796911890394745, 0.7108872963268008),
    design3d.Point2D(0.9193352406490979, 0.7108873750750229),
    design3d.Point2D(0.943257068363107, 0.7108873714262228),
    design3d.Point2D(0.957328707411281, 0.6889199122213159),
    design3d.Point2D(0.9573287795940568, 0.3110803289147694),
    design3d.Point2D(0.9432571269950443, 0.28911295065634096),
    design3d.Point2D(0.9193352813560651, 0.2891129208514467),
    design3d.Point2D(0.7969119478569466, 0.289112868790721),
    design3d.Point2D(0.7969119771240915, 0.049667935920999225),
    design3d.Point2D(0.7969119981329132, 0.012323366834239619),
    design3d.Point2D(0.7828402953854121, 0.0),
    design3d.Point2D(0.21715982313378532, 0.0),
    design3d.Point2D(0.2030881157414971, 0.012323183603131671),
]

contour2_cut_by_wire = Contour2D.from_points(points)

line_segment1 = edges.LineSegment2D(design3d.Point2D(1, -1), design3d.Point2D(1.5, 1))
arc = edges.Arc2D.from_3_points(design3d.Point2D(1.5, 1), design3d.Point2D(1.3, 1.5), design3d.Point2D(0.5, 1.5))
line_segment2 = edges.LineSegment2D(design3d.Point2D(0.5, 1.5), design3d.Point2D(-2, 1))
line_segment3 = edges.LineSegment2D(design3d.Point2D(-2, 1), design3d.Point2D(-2, 0.7))
line_segment4 = edges.LineSegment2D(design3d.Point2D(-2, 0.7), design3d.Point2D(-1, 1))
points2d = [design3d.Point2D(-1, 1), design3d.Point2D(2, 2), design3d.Point2D(-2, -2), design3d.Point2D(1, -1)]
bspline = edges.BSplineCurve2D(3, points2d, knot_multiplicities=[4, 4], knots=[0.0, 1.0])
contour2_unittest = Contour2D([bspline, line_segment1, arc, line_segment2, line_segment3, line_segment4])
unordered_contour2_unittest = Contour2D(
    [line_segment2, bspline.reverse(), arc.reverse(), line_segment1, line_segment3, line_segment4]
)

invalid_unordered_contour2_unittest = Contour2D(
    [
        line_segment2,
        bspline.reverse(),
        arc.reverse(),
        line_segment1,
        line_segment3,
        line_segment4,
        edges.LineSegment2D(design3d.Point2D(1, -1), design3d.Point2D(1.5, -1)),
    ]
)

unordered_wire_unittest = Wire2D([line_segment2, bspline.reverse(), arc.reverse(), line_segment1, line_segment3])

# Contour3D with all edges.
control_points = [
    design3d.Point3D(0, 3, 0),
    design3d.Point3D(3, 2, 1),
    design3d.Point3D(5, -1, 4),
    design3d.Point3D(5, -4, 0),
    design3d.Point3D(-1, -2, -3),
    design3d.Point3D(-3, 4, 1),
]
knots = [0.0, 1.0]
knot_multiplicities = [6, 6]
bspline_curve3d = edges.BSplineCurve3D(
    degree=5,
    control_points=control_points,
    knot_multiplicities=knot_multiplicities,
    knots=knots,
    weights=None,
    name="B Spline Curve 3D 1",
)
lineseg1 = edges.LineSegment3D(design3d.Point3D(3, 3, 2), bspline_curve3d.start)
lineseg2 = edges.LineSegment3D(bspline_curve3d.end, design3d.Point3D(-3, -3, 0))
arc = edges.Arc3D.from_3_points(
    design3d.Point3D(-3, -3, 0),
    design3d.Point3D(6.324555320336761, -5.692099788303083, -0.8973665961010275),
    design3d.Point3D(3, 3, 2),
)
contour3d = Contour3D([lineseg1, bspline_curve3d, lineseg2, arc])

folder = os.path.dirname(os.path.realpath(__file__))


class TestContour3D(unittest.TestCase):

    def test_order_contour(self):
        contour_to_order = Contour3D.from_json(os.path.join(folder, "contour_order.json"))
        self.assertFalse(contour_to_order.is_ordered())
        contour_to_order.order_contour()
        self.assertTrue(contour_to_order.is_ordered())

    def test_merge_with(self):
        contour1_to_merge = Contour3D.from_json(os.path.join(folder, "contour3d_merge_with1.json"))
        contour2_to_merge = Contour3D.from_json(os.path.join(folder, "contour3d_merge_with2.json"))
        expected_contour1 = Contour3D.from_json(os.path.join(folder, "expected_contour_merge_with1.json"))
        expected_contour2 = Contour3D.from_json(os.path.join(folder, "expected_contour_merge_with2.json"))
        merged_contours = contour1_to_merge.merge_with(contour2_to_merge)
        self.assertEqual(merged_contours[0], expected_contour1)
        self.assertEqual(merged_contours[1], expected_contour2)
        contour1 = Contour3D.from_json(os.path.join(folder, "contour1_merge_bug.json"))
        contour2 = Contour3D.from_json(os.path.join(folder, "contour2_merge_bug.json"))
        merged_contour1_contour2 = contour1.merge_with(contour2)
        merged_contour2_contour1 = contour2.merge_with(contour1)
        self.assertEqual(len(merged_contour1_contour2), len(merged_contour2_contour1))
        self.assertEqual(merged_contour1_contour2[0], merged_contour2_contour1[0])

    def test_is_sharing_primitives_with(self):
        contour1_sharing_primitives = Contour3D.from_json(os.path.join(folder, "contour3d_sharing_primitives1.json"))
        contour2_sharing_primitives = Contour3D.from_json(os.path.join(folder, "contour3d_sharing_primitives2.json"))
        self.assertTrue(contour1_sharing_primitives.is_sharing_primitives_with(contour2_sharing_primitives))

    def test_from_step(self):
        step = Step.from_file(filepath=os.path.join(folder, "contour_with_repeated_edge_in_contour3d.step"))
        model = step.to_volume_model()
        face = model.primitives[0].primitives[0]
        self.assertEqual(len(face.outer_contour3d.primitives), 5)
        self.assertTrue(face.outer_contour3d.is_ordered())

        # todo: refactor SphericalSuface3D repair periodicity
        # step = Step.from_file(filepath="wires/sphere_with_singularity.step")
        # model = step.to_volume_model()
        # self.assertTrue(model)

        step = Step.from_file(filepath=os.path.join(folder, "contour_with_repeated_edge_in_contour3d.step"))
        model = step.to_volume_model()
        face = model.primitives[0].primitives[0]
        self.assertEqual(len(face.outer_contour3d.primitives), 5)
        self.assertTrue(face.outer_contour3d.is_ordered())

        arguments = ["", ["#2518728", "#2518729"]]
        primitives = core.VolumeModel.from_json(
            os.path.join(folder, "strange_contour_from_step_primitives.json")
        ).primitives
        object_dict = {2518728: primitives[0], 2518729: primitives[1]}

        contour = Contour3D.from_step(arguments, object_dict)

        self.assertFalse(contour)

        arguments = [
            "''",
            [
                "#13203123",
                "#13203124",
                "#13203125",
                "#13203126",
                "#13203127",
                "#13203128",
                "#13203129",
                "#13203130",
                "#13203131",
                "#13203132",
            ],
        ]
        primitives = Contour3D.from_json(os.path.join(folder, "edge_loop_with_small_edges_and_gaps.json")).primitives
        object_dict = {int(arg[1:]): edge for arg, edge in zip(arguments[1], primitives)}
        contour = Contour3D.from_step(arguments, object_dict)
        self.assertFalse(contour.is_ordered())
        self.assertTrue(contour.is_ordered(5e-6))

    def test_edge_intersections(self):
        points = [
            design3d.Point3D(1.2918566581549966, 2.3839907440191492, 0.5678759590090421),
            design3d.Point3D(1.2067665579541171, -1.246879774203074, -0.4359328108960321),
            design3d.Point3D(-1.2905737351068276, -5.961765089244547, -0.9872550297481824),
            design3d.Point3D(7.33260591629263, -4.272128323147327, -0.4240427743824422),
            design3d.Point3D(7.115095014105684, 0.40888620982702983, 1.1362954032756774),
            design3d.Point3D(-3.0, 1.022248896290622, 0.5746069851843745),
            design3d.Point3D(2.739350840642852, -5.869347626045908, -0.7880999427201254),
        ]
        bspline = edges.BSplineCurve3D.from_points_interpolation(points, 3)
        edge_intersections = contour3d.edge_intersections(bspline, abs_tol=1e-6)
        expected_results = [
            design3d.Point3D(1.2918566581549966, 2.3839907440191492, 0.5678759590090421),
            design3d.Point3D(1.206766559907027, -1.2468797685507946, -0.4359328046874991),
            design3d.Point3D(-3.0, 1.0222488954206392, 0.5746069850600913),
            design3d.Point3D(-1.2905737300311637, -5.9617650927233345, -0.9872550300602736),
            design3d.Point3D(7.332606025327417, -4.272128068303522, -0.42404268513457977),
            design3d.Point3D(7.115095100684387, 0.408886063311686, 1.136295354437229),
        ]
        for intersection, expected_result in zip(edge_intersections, expected_results):
            self.assertTrue(intersection.is_close(expected_result))


if __name__ == "__main__":
    unittest.main()
