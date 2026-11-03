import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scanner.detect import analyze, clock_label, light_verdict, surface_metal
from scanner.samples import render_coin


SPEC = {
    "id": "test-cent",
    "name": "Test cent",
    "diameter_mm": 19.05,
    "metal": "copper",
    "size_check": True,
}

CLAD = {
    "id": "test-dime",
    "name": "Test dime",
    "diameter_mm": 17.91,
    "metal": "clad",
    "size_check": True,
}


def kinds(result):
    return [item["kind"] for item in result["findings"]]


class DetectTests(unittest.TestCase):
    def test_clock_points(self):
        self.assertEqual(clock_label(0, 0, 0, 10), "6:00")
        self.assertEqual(clock_label(0, 0, -10, 0), "9:00")
        self.assertEqual(clock_label(0, 0, 0, -10), "12:00")
        self.assertEqual(clock_label(0, 0, 10, 0), "3:00")

    def test_blank_is_not_a_coin(self):
        blank = np.zeros((720, 960, 3), np.uint8)
        blank[:] = (40, 40, 40)
        result = analyze(blank, SPEC)
        self.assertFalse(result["locked"])

    def test_clean_coin_stays_quiet(self):
        result = analyze(render_coin("clean"), SPEC)
        self.assertTrue(result["locked"], result["hint"])
        quiet = {"bite", "line", "pit", "split", "color", "off_center", "bump"}
        hit = quiet.intersection(kinds(result))
        self.assertFalse(hit, result["findings"])

    def test_rim_bite_at_six(self):
        result = analyze(render_coin("chip"), SPEC)
        self.assertIn("bite", kinds(result), result["findings"])
        bite = next(item for item in result["findings"] if item["kind"] == "bite")
        hour = int(bite["clock"].split(":")[0])
        self.assertIn(hour, (5, 6, 7), bite)

    def test_long_line(self):
        result = analyze(render_coin("scratch"), SPEC)
        self.assertIn("line", kinds(result), result["findings"])

    def test_pit(self):
        result = analyze(render_coin("pit"), SPEC)
        self.assertIn("pit", kinds(result), result["findings"])

    def test_split_edges(self):
        result = analyze(render_coin("doubling"), SPEC)
        self.assertIn("split", kinds(result), result["doubling"])

    def test_green_on_copper(self):
        result = analyze(render_coin("green"), SPEC)
        self.assertIn("color", kinds(result), result["findings"])

    def test_off_center_design(self):
        result = analyze(render_coin("offcenter"), SPEC)
        self.assertIn("off_center", kinds(result), result.get("off_center_score"))

    def test_size_mismatch(self):
        image = render_coin("clean")
        known = analyze(image, SPEC)
        true_ppm = known["diameter_px"] / SPEC["diameter_mm"]
        result = analyze(image, SPEC, px_per_mm=true_ppm * 1.25)
        self.assertIn("size", kinds(result), result["diameter_mm"])

    def test_light_test_names_a_shadow(self):
        verdict = light_verdict(
            {"rate": 0.2, "consistency": 0.8, "angle_deg": 10},
            {"rate": 0.2, "consistency": 0.8, "angle_deg": 100},
        )
        self.assertEqual(verdict["verdict"], "relief")

    def test_light_test_keeps_a_stable_split(self):
        verdict = light_verdict(
            {"rate": 0.2, "consistency": 0.8, "angle_deg": 10},
            {"rate": 0.18, "consistency": 0.7, "angle_deg": 18},
        )
        self.assertEqual(verdict["verdict"], "die")

    def test_steel_color_is_not_called_copper(self):
        import cv2
        import numpy as np

        def disc(color):
            image = np.zeros((400, 400, 3), np.uint8)
            image[:] = (24, 26, 24)
            cv2.circle(image, (200, 200), 120, color, -1)
            return image

        gray = cv2.cvtColor(disc((176, 180, 184)), cv2.COLOR_BGR2HSV)
        dark = cv2.cvtColor(disc((55, 58, 52)), cv2.COLOR_BGR2HSV)
        copper = cv2.cvtColor(disc((46, 96, 176)), cv2.COLOR_BGR2HSV)
        self.assertEqual(surface_metal(gray, 200, 200, 120), "steel")
        self.assertEqual(surface_metal(dark, 200, 200, 120), "unknown")
        self.assertEqual(surface_metal(copper, 200, 200, 120), "copper")

    def test_clad_spec_is_accepted(self):
        result = analyze(render_coin("clean"), CLAD)
        self.assertTrue(result["locked"])

    def test_a_sharp_copper_coin_gets_a_wide_grade_band(self):
        result = analyze(render_coin("clean"), CLAD)
        condition = result["condition"]
        self.assertEqual(condition["color"], "RD")
        self.assertEqual(condition["sheldon"], "XF-40 to AU-50")

    def test_a_soft_picture_is_not_graded(self):
        image = cv2.GaussianBlur(render_coin("clean"), (0, 0), 2.4)
        result = analyze(image, CLAD)
        self.assertEqual(result["condition"]["sheldon"], "")
        self.assertEqual(result["condition"]["wear"], "")


if __name__ == "__main__":
    unittest.main()

