"""Tests for design3d.primitives2d.Measure2D."""

import unittest

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import design3d  # noqa: E402
from design3d.core import EdgeStyle  # noqa: E402
from design3d.primitives2d import Measure2D  # noqa: E402


class TestMeasure2D(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def test_plot_with_default_arguments(self):
        measure = Measure2D(design3d.Point2D(0.0, 0.0), design3d.Point2D(0.1, 0.0), label="length")
        ax = measure.plot()
        self.assertEqual(len(ax.patches), 1)
        self.assertEqual(ax.texts[0].get_text(), "length: 100.0 mm")

    def test_plot_radius_in_meters_with_style(self):
        measure = Measure2D(design3d.Point2D(0.0, 0.0), design3d.Point2D(0.0, 2.0), unit="m", type_="radius")
        _, ax = plt.subplots()
        returned_ax = measure.plot(ax, EdgeStyle(color="red"))
        self.assertIs(returned_ax, ax)
        self.assertEqual(ax.texts[0].get_text(), "2.0 m")
        self.assertEqual(ax.texts[0].get_rotation(), 90.0)


if __name__ == "__main__":
    unittest.main()
