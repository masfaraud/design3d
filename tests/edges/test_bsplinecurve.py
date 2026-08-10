"""
Unit tests for design3d.faces.BSplineCurve
"""

import unittest
import os
from geomdl import BSpline
import design3d
import design3d.edges as d3de
from design3d import curves
from design3d.base import SerializableObject
import design3d.nurbs.helpers as nurbs_helpers

import design3d.edges

dict_bspline = {
    "name": "",
    "object_class": "design3d.edges.BSplineCurve2D",
    "package_version": "0.5.1.dev193+gc6bdd70e",
    "degree": 3,
    "weights": None,
    "periodic": False,
    "start": {"object_class": "design3d.Point2D", "x": -0.4544751134860842, "y": 1.5707977686871983, "name": ""},
    "end": {"object_class": "design3d.Point2D", "x": -0.3124009292097013, "y": -3.141592653588988, "name": ""},
    "control_points": [
        {"$ref": "#/start"},
        {"object_class": "design3d.Point2D", "x": -0.4553429239113792, "y": 1.620595708870625, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.45583687948274487, "y": 1.7225897961445817, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4520590939005643, "y": 1.8859455670744714, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4432673038692045, "y": 2.0505943691631203, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.43149023009611276, "y": 2.196369778630224, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.41807624324211334, "y": 2.3265228465729813, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.40398926099996524, "y": 2.442576243391531, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.390014646035353, "y": 2.5455258258288014, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3767380630341135, "y": 2.636436435451037, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.364420681738801, "y": 2.717006060784525, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.352993811394062, "y": 2.790125033607336, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.34264250918889616, "y": 2.856354311373755, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3334693750607423, "y": 2.9167961005375314, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3251167944404208, "y": 2.9758770725556776, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.31834827936261717, "y": 3.031890968787418, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.31362756905698363, "y": 3.086173401011527, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.31239657524755504, "y": 3.1230758830026706, "name": ""},
        {"$ref": "#/end"},
    ],
    "knots": [
        0.0,
        0.0625,
        0.125,
        0.1875,
        0.25,
        0.3125,
        0.375,
        0.4375,
        0.5,
        0.5625,
        0.625,
        0.6875,
        0.75,
        0.8125,
        0.875,
        0.9375,
        1.0,
    ],
    "knot_multiplicities": [4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4],
    "points": [
        {"$ref": "#/start"},
        {"object_class": "design3d.Point2D", "x": -0.4548466635787877, "y": 1.5950384158111264, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.45511756697976646, "y": 1.6194803667255397, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.45528447308284226, "y": 1.6441370032839118, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.455344031281837, "y": 1.6690217073397149, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4552928909705727, "y": 1.694147860746423, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4551277015428712, "y": 1.7195288453575088, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4548452250154656, "y": 1.7451734233409908, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.45444302314566176, "y": 1.7710575522618923, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.45391900376144056, "y": 1.7971429941929713, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4532710760748605, "y": 1.8233914544334284, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.45249714929798024, "y": 1.8497646382824626, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.45159513264285833, "y": 1.8762242510392753, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4505633688659587, "y": 1.9027300922649175, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4494060865225913, "y": 1.929216089219333, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4481317559665275, "y": 1.955597523420418, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.44674894119712977, "y": 1.9817892647466278, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.44526620621376106, "y": 2.0077061830764182, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4436921150157843, "y": 2.0332631482882464, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4420351915186864, "y": 2.058376409937326, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.44030269810607103, "y": 2.083005639184192, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4385004119546198, "y": 2.107161627632355, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4366340250481718, "y": 2.130858099201241, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4347092293705654, "y": 2.1541087778102743, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4327317169056396, "y": 2.17692738737888, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.43070717541087433, "y": 2.199327632826092, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.42864078125434185, "y": 2.221320920023585, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4265367176098109, "y": 2.242914189751056, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4243990535393636, "y": 2.264113869777636, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.42223185810508257, "y": 2.2849263878724546, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4200392003690504, "y": 2.305358171804641, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.41782514936267906, "y": 2.3254156492528355, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4155936235578411, "y": 2.345104803680675, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.41334804177974516, "y": 2.3644301443805538, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4110917193419994, "y": 2.3833958752413955, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4088279715582119, "y": 2.4020062001521234, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.40656011374199097, "y": 2.4202653230016637, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.40429146120694454, "y": 2.4381774476789384, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.4020252351425574, "y": 2.4557468105876525, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3997641070863636, "y": 2.472977838006455, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3975105496254905, "y": 2.4898750249405714, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3952670350726511, "y": 2.506442866490023, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3930360357405587, "y": 2.5226858577548303, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3908200239419262, "y": 2.538608493835015, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.388621397802237, "y": 2.5542154145829894, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.38644175510555184, "y": 2.5695128214586704, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3842822053156306, "y": 2.5845078687211487, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.38214385092898795, "y": 2.599207724223843, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3800277944421384, "y": 2.613619555820171, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3779351383515963, "y": 2.6277505313635516, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3758669561441629, "y": 2.641607923568505, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3738236540832329, "y": 2.6552014169549416, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.37180497120879513, "y": 2.668543107848158, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3698106175511247, "y": 2.6816451974345528, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.36784030314049704, "y": 2.694519886900528, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3658937380071872, "y": 2.7071793774324835, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.36397063762970416, "y": 2.719635820202718, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.36207109934234555, "y": 2.731897860995254, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.36019584632888635, "y": 2.743968400374352, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.35834565978589195, "y": 2.755849806354134, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3565213209099278, "y": 2.767544446948719, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.354723610897559, "y": 2.7790546901722277, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3529533108320427, "y": 2.7903829047825366, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3512111196480645, "y": 2.8015319987603426, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3494975093236369, "y": 2.8125063698288493, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.347812912972, "y": 2.8233106708194367, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.34615776370639384, "y": 2.8339495545634827, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.34453249464005853, "y": 2.8444276738923673, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3429375388862342, "y": 2.8547496816374696, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.34137306276343055, "y": 2.864922157883073, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.33983794478187596, "y": 2.87496098549184, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3383306753939227, "y": 2.884884850551473, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3368497449728728, "y": 2.894712439720711, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.33539364389202847, "y": 2.9044624396582925, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3339608625246917, "y": 2.9141535370229574, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.332550224012169, "y": 2.923802598123358, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3311634478098794, "y": 2.933410645480362, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3298037446668912, "y": 2.9429705437496354, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3284743376570138, "y": 2.9524750901664705, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.32717844985405625, "y": 2.961917081966161, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.32591930433182814, "y": 2.9712893163839995, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3247000866268476, "y": 2.9805849715556563, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3235233278703795, "y": 2.989803866032311, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.322391003343133, "y": 2.998951458721221, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3213050706642383, "y": 3.0080333877461474, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.32026748745282596, "y": 3.017055291230848, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3192802113280263, "y": 3.0260228072990825, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3183452133649473, "y": 3.034941628508501, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3174650741446269, "y": 3.0438199130702976, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3166432199811892, "y": 3.052669240466372, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3158831394849492, "y": 3.0615014421873665, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.31518832126622176, "y": 3.0703283497239235, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3145622539353218, "y": 3.0791617945666845, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.314008426188227, "y": 3.08783875316965, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.31353034813979486, "y": 3.052475966713578, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3131315794021342, "y": 2.8281563457618653, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3128156865577697, "y": 2.255734781785127, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3125862361892262, "y": 1.1760661662539973, "name": ""},
        {"object_class": "design3d.Point2D", "x": -0.3124467948790285, "y": -0.569994609360928, "name": ""},
        {"$ref": "#/end"},
    ],
}

bspline_curve2d_1 = design3d.edges.BSplineCurve2D.dict_to_object(dict_bspline)


DELTA = 0.001
folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "bsplinecurve_objects")


class TestBSplineCurve2D(unittest.TestCase):
    degree = 3
    points = [design3d.Point2D(0, 0), design3d.Point2D(1, 1), design3d.Point2D(2, -1), design3d.Point2D(3, 0)]
    knotvector = nurbs_helpers.generate_knot_vector(degree, len(points))
    knot_multiplicity = [1] * len(knotvector)
    bspline1 = d3de.BSplineCurve2D(degree, points, knot_multiplicity, knotvector, None, "")
    bspline2, bspline3 = bspline1.split(design3d.Point2D(1.5, 0.0))
    bspline4, bspline5 = bspline2.split(bspline2.point_at_abscissa(0.3 * bspline2.length()))
    bspline6 = bspline1.split(bspline1.point_at_abscissa(0.7 * bspline1.length()))[0]
    bspline7 = bspline1.split(bspline1.point_at_abscissa(0.3 * bspline1.length()))[1]
    degree = 3
    ctrlpts = [
        design3d.Point2D(5.0, 5.0),
        design3d.Point2D(10.0, 10.0),
        design3d.Point2D(20.0, 15.0),
        design3d.Point2D(35.0, 15.0),
        design3d.Point2D(45.0, 10.0),
        design3d.Point2D(50.0, 5.0),
    ]
    knot_multiplicities = [4, 1, 1, 4]
    knots = [0.0, 0.33, 0.66, 1.0]

    bspline2d = d3de.BSplineCurve2D(degree, ctrlpts, knot_multiplicities, knots)
    weights = [0.5, 1.0, 0.75, 1.0, 0.25, 1.0]
    bspline2d_rational = d3de.BSplineCurve2D(degree, ctrlpts, knot_multiplicities, knots, weights=weights)

    def test_evaluate_single(self):
        test_cases = [
            (0.0, (5.0, 5.0)),
            (0.3, (18.617, 13.377)),
            (0.5, (27.645, 14.691)),
            (0.6, (32.143, 14.328)),
            (1.0, (50.0, 5.0)),
        ]
        for param, res in test_cases:
            with self.subTest(param=param):
                evalpt = self.bspline2d.evaluate_single(param)
                self.assertAlmostEqual(evalpt[0], res[0], delta=DELTA)
                self.assertAlmostEqual(evalpt[1], res[1], delta=DELTA)

        test_cases = [
            (0.0, (5.0, 5.0)),
            (0.2, (13.8181, 11.5103)),
            (0.5, (28.1775, 14.7858)),
            (0.95, (48.7837, 6.0022)),
        ]
        for param, res in test_cases:
            with self.subTest(param=param):
                evalpt = self.bspline2d_rational.evaluate_single(param)

                self.assertAlmostEqual(evalpt[0], res[0], delta=DELTA)
                self.assertAlmostEqual(evalpt[1], res[1], delta=DELTA)

    def test_derivatives(self):
        derivatives = self.bspline2d.derivatives(u=0.35, order=2)
        expected_result = [
            [20.879272837543425, 13.96350686701158],
            [45.20015428165102, 9.987462558623653],
            [-1.334434093851499, -68.74685708529317],
        ]
        for der, res in zip(derivatives, expected_result):
            self.assertAlmostEqual(der[0], res[0], delta=DELTA)
            self.assertAlmostEqual(der[1], res[1], delta=DELTA)

        test_cases = [
            (0.0, 1, ((5.0, 5.0), (90.9090, 90.9090))),
            (0.2, 2, ((13.8181, 11.5103), (40.0602, 17.3878), (104.4062, -29.3672))),
            (0.5, 3, ((28.1775, 14.7858), (39.7272, 2.2562), (-116.9254, -49.7367), (125.5276, 196.8865))),
            (0.95, 1, ((48.7837, 6.0022), (39.5178, -29.9962))),
        ]
        for param, order, res in test_cases:
            deriv = self.bspline2d_rational.derivatives(u=param, order=order)

            for computed, expected in zip(deriv, res):
                for c, e in zip(computed, expected):
                    self.assertAlmostEqual(c, e, delta=DELTA)

    def test_interpolate_curve(self):
        # The NURBS Book Ex9.1
        points = [
            design3d.Point2D(0, 0),
            design3d.Point2D(3, 4),
            design3d.Point2D(-1, 4),
            design3d.Point2D(-4, 0),
            design3d.Point2D(-4, -3),
        ]
        degree = 3  # cubic curve

        # Do global curve interpolation
        curve = d3de.BSplineCurve2D.from_points_interpolation(points, degree, centripetal=False)
        expected_ctrlpts = [
            [0.0, 0.0],
            [7.3169635171119936, 3.6867775257587367],
            [-2.958130565851424, 6.678276528176592],
            [-4.494953466891109, -0.6736915062424752],
            [-4.0, -3.0],
        ]
        for point, expected_point in zip(curve.control_points, expected_ctrlpts):
            self.assertAlmostEqual(point[0], expected_point[0], delta=DELTA)
            self.assertAlmostEqual(point[1], expected_point[1], delta=DELTA)

    def test_approximate_curve(self):
        # The NURBS Book Ex9.1
        points = [
            design3d.Point2D(0, 0),
            design3d.Point2D(3, 4),
            design3d.Point2D(-1, 4),
            design3d.Point2D(-4, 0),
            design3d.Point2D(-4, -3),
        ]
        degree = 3  # cubic curve

        # Do global curve interpolation
        curve = d3de.BSplineCurve2D.from_points_approximation(points, degree, centripetal=False)
        expected_ctrlpts = [
            [0.0, 0.0],
            [9.610024470158852, 8.200277881464892],
            [-8.160625855418692, 3.3820642030608417],
            [-4.0, -3.0],
        ]
        for point, expected_point in zip(curve.control_points, expected_ctrlpts):
            self.assertAlmostEqual(point[0], expected_point[0], delta=DELTA)
            self.assertAlmostEqual(point[1], expected_point[1], delta=DELTA)

        points2d = [
            design3d.Point2D(0, 0.1),
            design3d.Point2D(0.2, 0.3),
            design3d.Point2D(0.4, 0.4),
            design3d.Point2D(0.5, 0.6),
            design3d.Point2D(0.6, 0.7),
            design3d.Point2D(0.8, 0.8),
            design3d.Point2D(1, 0.9),
        ]

        # %%% Approximation
        bspline_curve2d_approximated = d3de.BSplineCurve2D.from_points_approximation(points2d, 3, ctrlpts_size=5)
        expected_ctrlpts = [
            design3d.Point2D(0.0, 0.1),
            design3d.Point2D(0.1686778402310228, 0.2366540266279785),
            design3d.Point2D(0.466545895266623, 0.5077440536607246),
            design3d.Point2D(0.7432185866086097, 0.852531277025759),
            design3d.Point2D(1.0, 0.9),
        ]
        for point, expected_point in zip(bspline_curve2d_approximated.control_points, expected_ctrlpts):
            self.assertAlmostEqual(point[0], expected_point[0], delta=DELTA)
            self.assertAlmostEqual(point[1], expected_point[1], delta=DELTA)

    def test_length(self):
        total_length = self.bspline2d.length()
        self.assertAlmostEqual(total_length, 50.33433959792692, delta=DELTA)

    def test_abscissa(self):
        bspline_curve2d = bspline_curve2d_1
        point = design3d.Point2D(-0.31240117104573617, -2.8555856978321796)

        bspline = d3de.BSplineCurve2D.from_json(os.path.join(folder, "bg_bspline5_.json"))
        point1 = bspline.points[25]
        point2 = bspline.points[75]

        abscissa1 = bspline.abscissa(point1)
        abscissa2 = bspline.abscissa(point2)

        test_point1 = bspline.point_at_abscissa(abscissa1)
        test_point2 = bspline.point_at_abscissa(abscissa2)

        self.assertTrue(point1.is_close(test_point1))
        self.assertTrue(point2.is_close(test_point2))

        abscissa3 = 0.00016294494116532595
        abscissa4 = 0.00017682955170114393

        point_at_abscissa3 = bspline.point_at_abscissa(abscissa3)
        point_at_abscissa4 = bspline.point_at_abscissa(abscissa4)

        test_abscissa3 = bspline.abscissa(point_at_abscissa3)
        test_abscissa4 = bspline.abscissa(point_at_abscissa4)

        self.assertAlmostEqual(abscissa3, test_abscissa3, 6)
        self.assertAlmostEqual(abscissa4, test_abscissa4, 6)

        self.assertAlmostEqual(bspline_curve2d.abscissa(point), 7.747599410268476)

    def test_line_intersections(self):
        bspline_curve2d = SerializableObject.from_json(os.path.join(folder, "bsplinecurve2d_1.json"))
        line = curves.Line2D(
            design3d.Point2D(1.263163105753452, -0.002645572020392778),
            design3d.Point2D(1.263163105753452, -0.001820963841291406),
        )

        line_intersections = bspline_curve2d.line_intersections(line)
        self.assertEqual(len(line_intersections), 1)
        self.assertTrue(line_intersections[0].is_close(design3d.Point2D(1.263163105753452, -0.0026450893856384914)))

    def test_discretization_points(self):
        control_points_2d = [
            design3d.Point2D(1.5707963267948966, 2.3),
            design3d.Point2D(1.680890866936472, 2.256043878001211),
            design3d.Point2D(1.8428579918488803, 2.190912791233705),
            design3d.Point2D(2.0551351923128847, 2.110710771857296),
            design3d.Point2D(2.2068399827060317, 2.057538514554844),
            design3d.Point2D(2.3561943231153806, 2.010935033351481),
            design3d.Point2D(2.505548683644506, 1.9715519259143607),
            design3d.Point2D(2.65725353031637, 1.940017133765504),
            design3d.Point2D(2.8695307222689292, 1.908674758526091),
            design3d.Point2D(3.031498051508191, 1.89997293414679),
            design3d.Point2D(3.141592653589793, 1.9000000000000003),
        ]
        bspline_curve2d = d3de.BSplineCurve2D(
            3,
            control_points_2d,
            [4, 1, 1, 1, 1, 1, 1, 1, 4],
            [
                0.0,
                0.2102659043588606,
                0.30933566258662554,
                0.40542083024287023,
                0.5000013075051806,
                0.5945816603424732,
                0.6906664654007513,
                0.7897356531977031,
                1.0,
            ],
        )

        curve = BSpline.Curve()
        curve.degree = 2
        curve.ctrlpts = [[1, 0, 0], [1, 1, 0], [0, 1, 0]]
        curve.knotvector = [0, 0, 0, 1, 1, 1]

        bspline_curve3d = d3de.BSplineCurve3D.from_geomdl_curve(curve)
        # Test discretization with default number of points (20)
        points = bspline_curve3d.discretization_points()
        self.assertEqual(len(points), 100)

        # Test accuracy of first 5 discretized points
        expected_points = [
            design3d.Point3D(0.0, 0.0, 0.0),
            design3d.Point3D(0.10526315789473684, 0.10526315789473684, 0.10526315789473684),
            design3d.Point3D(0.21052631578947367, 0.21052631578947367, 0.21052631578947367),
            design3d.Point3D(0.3157894736842105, 0.3157894736842105, 0.3157894736842105),
            design3d.Point3D(0.42105263157894735, 0.42105263157894735, 0.42105263157894735),
        ]
        for i in range(5):
            self.assertTrue(points[i], expected_points[i])

        # Test discretization with specified number of points
        points = bspline_curve2d.discretization_points(number_points=10)
        self.assertEqual(len(points), 10)

        # Test discretization with angle resolution
        points = bspline_curve2d.discretization_points(angle_resolution=10)
        self.assertEqual(len(points), 31)

    def test_offset(self):
        offseted_bspline = self.bspline1.offset(-0.2)
        expected_distances = [
            0.2,
            0.20000160183808904,
            0.20053651951715856,
            0.20372910969690097,
            0.210441370708919,
            0.2192581584663399,
            0.22774528008118392,
            0.23404460706854788,
            0.23739001591364056,
            0.2379018126594174,
            0.2362014374337063,
            0.23307773295678147,
            0.22924032294583793,
            0.22517329538697972,
            0.22109005047384114,
            0.21697594011450796,
            0.21267059325565962,
            0.2079610665048543,
            0.20299372351359257,
            0.19999999999999987,
        ]
        for i, (point1, point2) in enumerate(
            zip(
                self.bspline1.discretization_points(number_points=20),
                offseted_bspline.discretization_points(number_points=20),
            )
        ):
            self.assertAlmostEqual(point1.point_distance(point2), expected_distances[i], 5)

    def test_point_distance(self):
        point = design3d.Point2D(1.5, 0.1)
        self.assertAlmostEqual(self.bspline1.point_distance(point), 0.08945546033235202)
        point2 = self.bspline1.point_at_abscissa(0.4)
        self.assertAlmostEqual(self.bspline1.point_distance(point2), 0.0, 7)

    def test_point_belongs(self):
        point = design3d.Point2D(1.5, 0.1)
        self.assertFalse(self.bspline1.point_belongs(point))
        point2 = self.bspline1.point_at_abscissa(0.4)
        self.assertTrue(self.bspline1.point_belongs(point2))

    def test_get_shared_primitives(self):
        shared_section1 = self.bspline1.get_shared_section(self.bspline2)
        self.assertEqual(len(shared_section1), 1)
        self.assertTrue(shared_section1[0].start.is_close(design3d.Point2D(0.0, 0.0)))
        self.assertTrue(shared_section1[0].end.is_close(design3d.Point2D(1.5, 0.0)))
        shared_section2 = self.bspline6.get_shared_section(self.bspline7)
        self.assertEqual(len(shared_section2), 1)
        self.assertTrue(shared_section2[0].start.is_close(design3d.Point2D(0.8999999, 0.252000000)))
        self.assertTrue(shared_section2[0].end.is_close(design3d.Point2D(2.09999999, -0.251999999)))
        self.assertAlmostEqual(shared_section2[0].length(), 1.3039875674329982, 6)
        shared_section3 = self.bspline1.get_shared_section(self.bspline5)
        self.assertEqual(shared_section3, [self.bspline5])
        shared_section4 = self.bspline5.get_shared_section(self.bspline1)
        self.assertEqual(shared_section4, [self.bspline5])
        self.assertFalse(self.bspline4.get_shared_section(self.bspline3))

    def test_delete_shared_primitives(self):
        remaining_section1 = self.bspline1.delete_shared_section(self.bspline2)
        self.assertEqual(len(remaining_section1), 1)
        self.assertTrue(remaining_section1[0].start.is_close(design3d.Point2D(1.5, 0.0)))
        self.assertTrue(remaining_section1[0].end.is_close(design3d.Point2D(3.0, 0.0)))
        self.assertAlmostEqual(remaining_section1[0].length(), 1.6373881438050524, 6)
        remaining_section2 = self.bspline6.delete_shared_section(self.bspline7)
        self.assertEqual(len(remaining_section2), 1)
        self.assertTrue(remaining_section2[0].start.is_close(design3d.Point2D(0.0, 0.0)))
        self.assertTrue(remaining_section2[0].end.is_close(design3d.Point2D(0.8999999997498065, 0.25200000006505024)))
        self.assertAlmostEqual(remaining_section2[0].length(), 0.9854029549808058, 6)
        remaining_section3 = self.bspline1.delete_shared_section(self.bspline5)
        self.assertEqual(len(remaining_section3), 2)
        self.assertTrue(remaining_section3[0].start.is_close(design3d.Point2D(0.0, 0.0)))
        self.assertTrue(remaining_section3[0].end.is_close(design3d.Point2D(0.44999999682593295, 0.26774999925409426)))
        self.assertAlmostEqual(remaining_section3[0].length(), 0.5305607215935024, 6)
        self.assertTrue(remaining_section3[1].start.is_close(design3d.Point2D(1.4999999878769186, 0.0)))
        self.assertTrue(remaining_section3[1].end.is_close(design3d.Point2D(3.0, 0.0)))
        self.assertAlmostEqual(remaining_section3[1].length(), 1.6373881438050524, 6)
        self.assertFalse(self.bspline5.delete_shared_section(self.bspline1))
        remaining_section4 = self.bspline4.delete_shared_section(self.bspline3)
        self.assertEqual(remaining_section4, [self.bspline4])

    def test_local_discretization(self):
        expected_points = [
            design3d.Point2D(0.22902909156524637, 0.17924444819399216),
            design3d.Point2D(0.26974537451069974, 0.2013444443084787),
            design3d.Point2D(0.3104616574561531, 0.22072505985054805),
            design3d.Point2D(0.35117794040160644, 0.23747629494418182),
            design3d.Point2D(0.3918942233470598, 0.25168814971336145),
            design3d.Point2D(0.4326105062925132, 0.26345062428206867),
            design3d.Point2D(0.4733267892379665, 0.2728537187742847),
            design3d.Point2D(0.5140430721834197, 0.27998743331399134),
            design3d.Point2D(0.5547593551288732, 0.28494176802517024),
            design3d.Point2D(0.5954756380743265, 0.28780672303180266),
        ]
        point1 = self.bspline1.point_at_abscissa(0.25)
        point2 = self.bspline1.point_at_abscissa(0.65)
        local_discretization = self.bspline1.local_discretization(point1, point2, 10)
        for point1, point2 in zip(expected_points, local_discretization):
            self.assertTrue(point1.is_close(point2))

    def test_simplify(self):
        bsplinecurve = d3de.BSplineCurve3D.from_json(os.path.join(folder, "bsplinecurve_fullarc.json"))
        fullarc = bsplinecurve.simplify
        self.assertTrue(isinstance(fullarc, d3de.FullArc3D))

    def test_direction_independent_is_close(self):
        bsplinecurve1 = d3de.BSplineCurve3D.from_json(os.path.join(folder, "bspline_curve1.json"))
        bsplinecurve2 = d3de.BSplineCurve3D.from_json(os.path.join(folder, "bspline_curve2.json"))
        self.assertTrue(bsplinecurve1.direction_independent_is_close(bsplinecurve2))

    def test_split_curve(self):
        split_point = design3d.Point2D(28.1775252667145, 14.785855215217019)
        splitted_curves = self.bspline2d_rational.split(split_point)
        self.assertTrue(splitted_curves[0].start.is_close(design3d.Point2D(5.0, 5.0)))
        self.assertTrue(splitted_curves[0].end.is_close(split_point))
        self.assertTrue(splitted_curves[1].start.is_close(split_point))
        self.assertTrue(splitted_curves[1].end.is_close(design3d.Point2D(50.0, 5.0)))

        split_point = design3d.Point2D(0.04820589473987067, 0.011936395549382077)
        bsplinecurve = d3de.BSplineCurve2D.from_json(os.path.join(folder, "bsplinecurve_split_bug.json"))
        splitted_curves = bsplinecurve.split(split_point)
        self.assertTrue(splitted_curves[0].start.is_close(design3d.Point2D(0.04873977000999985, 0.011815456390639745)))
        self.assertTrue(splitted_curves[0].end.is_close(split_point))
        self.assertTrue(splitted_curves[1].start.is_close(split_point))
        self.assertTrue(splitted_curves[1].end.is_close(design3d.Point2D(0.04793931370999993, 0.011891887758212483)))
        self.assertAlmostEqual(splitted_curves[0].length(), 0.0005535177002044544, 5)
        self.assertAlmostEqual(splitted_curves[1].length(), 0.0002710315376536523, 5)

    def test_tangent(self):
        tangent = self.bspline1.tangent(0.5)
        tangent_rational = self.bspline2d_rational.tangent(0.5)
        self.assertTrue(tangent.is_close(design3d.Vector2D(0.8944271909999159, -0.4472135954999579)))
        self.assertTrue(tangent_rational.is_close(design3d.Vector2D(0.998391126712381, 0.05670236416572517)))


class TestBSplineCurve3D(unittest.TestCase):
    b_splinecurve3d = d3de.BSplineCurve3D(
        degree=5,
        control_points=[
            design3d.Point3D(0.5334, 4.61e-10, -2.266),
            design3d.Point3D(0.5334, 0.236642912449, -2.26599999893),
            design3d.Point3D(0.5334, 0.473285829931, -2.23144925183),
            design3d.Point3D(0.5334, 0.70316976404, -2.16234807551),
            design3d.Point3D(0.5334, 1.13611540546, -1.95904362568),
            design3d.Point3D(0.5334, 1.49286052971, -1.64044168585),
            design3d.Point3D(0.5334, 1.64654439419, -1.45604332404),
            design3d.Point3D(0.5334, 1.77109261028, -1.25188280667),
            design3d.Point3D(0.5334, 1.86385510975, -1.03417888209),
        ],
        knot_multiplicities=[6, 3, 6],
        knots=[0.0, 0.4999999725155696, 1.0],
    )

    def test_line_intersections(self):
        line = curves.Line3D(
            design3d.Point3D(0.5334, -0.44659009801843536, 0.0),
            design3d.Point3D(0.5334, 0.4342689853571558, -0.47337857496375274),
        )
        bspline_line_intersections = self.b_splinecurve3d.line_intersections(line)
        self.assertTrue(
            bspline_line_intersections[0].is_close(design3d.Point3D(0.5334, 1.784620497933768, -1.1990649949459866))
        )

    def test_linesegment_intersection(self):
        linesegment1 = d3de.LineSegment3D(
            design3d.Point3D(0.5334, -0.44659009801843536, 0.0),
            design3d.Point3D(0.5334, 0.4342689853571558, -0.47337857496375274),
        )
        linesegment2 = d3de.LineSegment3D(
            design3d.Point3D(0.5334, -0.44659009801843536, 0.0),
            design3d.Point3D(0.5334, 2.1959871521083385, -1.4201357248912583),
        )
        bspline_lineseg_intersections1 = self.b_splinecurve3d.linesegment_intersections(linesegment1)
        bspline_lineseg_intersections2 = self.b_splinecurve3d.linesegment_intersections(linesegment2)
        self.assertFalse(bspline_lineseg_intersections1)
        self.assertTrue(
            bspline_lineseg_intersections2[0].is_close(
                design3d.Point3D(0.5334, 1.7846204999239552, -1.1990649960155242)
            )
        )

    def test_normal(self):
        normal = self.b_splinecurve3d.normal()
        self.assertTrue(normal.is_close(design3d.Z3D))


class TestBezierCurve2D(unittest.TestCase):
    # Set up the Bezier curve
    degree = 2
    ctrlpts = [design3d.Point2D(10, 0), design3d.Point2D(20, 15), design3d.Point2D(30, 0)]

    curve1 = d3de.BezierCurve2D(degree, ctrlpts)

    # Set evaluation delta
    curve1.sample_size = 5

    def test_setup(self):
        points = self.curve1.points
        expected_points = [[10.0, 0.0], [15.0, 5.625], [20.0, 7.5], [25.0, 5.625], [30.0, 0.0]]
        expected_knot_vector = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]

        self.assertEqual(list(self.curve1.knotvector), expected_knot_vector)
        for point, test in zip(points, expected_points):
            self.assertAlmostEqual(point[0], test[0], delta=1e-6)
            self.assertAlmostEqual(point[1], test[1], delta=1e-6)


if __name__ == "__main__":
    unittest.main()
