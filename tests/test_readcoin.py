import unittest
from pathlib import Path

import cv2
import numpy as np

from scanner.catalog import suggest_series
from scanner.charts import price_for as chart_price
from scanner.indian_head import price_for
from scanner.readcoin import parse_words
from scanner.relief import read_relief_year, relief_year_from_circle, sample_date

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ReadCoinTests(unittest.TestCase):
    def test_year_and_nearby_mint(self):
        words = [
            ("2022", {"x": 10, "y": 40, "width": 80, "height": 24}),
            ("D", {"x": 100, "y": 40, "width": 16, "height": 24}),
            ("LIBERTY", {"x": 10, "y": 10, "width": 120, "height": 20}),
        ]
        parsed = parse_words(words)
        self.assertEqual(parsed["year"], 2022)
        self.assertEqual(parsed["mint"], "D")
        self.assertEqual(parsed["mint_name"], "Denver")

    def test_dual_date_uses_the_strike_year(self):
        words = [
            ("1776", {"x": 10, "y": 40, "width": 70, "height": 24}),
            ("2026", {"x": 90, "y": 40, "width": 70, "height": 24}),
        ]
        parsed = parse_words(words)
        self.assertEqual(parsed["year"], 2026)
        self.assertEqual(parsed["mint"], "")

    def test_ignores_a_mint_letter_far_from_the_date(self):
        words = [
            ("1964", {"x": 10, "y": 20, "width": 70, "height": 20}),
            ("S", {"x": 400, "y": 300, "width": 12, "height": 16}),
        ]
        parsed = parse_words(words)
        self.assertEqual(parsed["year"], 1964)
        self.assertEqual(parsed["mint"], "")

    def test_no_date(self):
        parsed = parse_words([("LIBERTY", {"x": 0, "y": 0, "width": 40, "height": 16})])
        self.assertIsNone(parsed["year"])


class SeriesYearTests(unittest.TestCase):
    def test_1896_on_a_shield_cent_is_an_indian_head(self):
        self.assertEqual(suggest_series(1896, "lincoln-shield"), "indian-head")

    def test_a_year_inside_the_selected_series_stays_there(self):
        self.assertIsNone(suggest_series(2020, "lincoln-shield"))
        self.assertIsNone(suggest_series(1896, "indian-head"))

    def test_1909_is_not_forced_when_two_cent_series_fit(self):
        self.assertIsNone(suggest_series(1909, "lincoln-shield"))

    def test_1943_on_a_shield_cent_is_a_wheat_cent(self):
        self.assertEqual(suggest_series(1943, "lincoln-shield"), "lincoln-wheat")

    def test_copper_color_picks_the_cent_across_groups(self):
        self.assertEqual(suggest_series(1896, "washington", "copper"), "indian-head")

    def test_a_dollar_sized_1896_is_a_morgan(self):
        self.assertEqual(suggest_series(1896, "lincoln-shield", None, 38.1), "morgan")

    def test_an_unmeasured_1896_is_not_forced_off_a_quarter(self):
        self.assertEqual(suggest_series(1896, "barber-quarter"), None)


class IndianHeadChartTests(unittest.TestCase):
    def test_1896_good_to_fine_uses_the_chart(self):
        quote = price_for(1896, sheldon="G-4 to F-12")
        self.assertEqual(quote["low"], 1)
        self.assertEqual(quote["high"], 5)

    def test_1877_is_the_key_date_range(self):
        quote = price_for(1877, sheldon="G-4 to F-12")
        self.assertEqual(quote["low"], 590)
        self.assertEqual(quote["high"], 1280)

    def test_1909_s_uses_the_mint_row(self):
        quote = price_for(1909, "S", "XF-40 to AU-50")
        self.assertEqual(quote["key"], "1909-S")
        self.assertGreater(quote["low"], 500)

    def test_other_series_use_the_same_chart_columns(self):
        wheat = chart_price("lincoln-wheat", 1955)
        quarter = chart_price("washington", 1964)
        self.assertLess(wheat["high"], 1)
        self.assertGreater(quarter["low"], 5)


class ReliefYearTests(unittest.TestCase):
    def test_worn_1896_date(self):
        image = cv2.imread(str(FIXTURES / "date-1896.png"), cv2.IMREAD_GRAYSCALE)
        self.assertEqual(read_relief_year(image), 1896)

    def test_worn_1896_with_the_bust_in_frame(self):
        image = cv2.imread(str(FIXTURES / "date-1896-wide.png"), cv2.IMREAD_GRAYSCALE)
        self.assertEqual(read_relief_year(image), 1896)

    def test_drawn_dates_keep_their_year(self):
        for year in (1896, 1943, 2020, 1859):
            self.assertEqual(read_relief_year(sample_date(str(year))), year, year)

    def test_blank_and_noise_are_not_a_year(self):
        self.assertIsNone(read_relief_year(np.full((120, 400), 140, np.uint8)))
        noise = np.random.default_rng(1).integers(90, 160, (140, 420), dtype=np.uint8)
        self.assertIsNone(read_relief_year(noise))

    def test_date_view_through_the_coin_circle(self):
        image = cv2.imread(str(FIXTURES / "date-1896-wide.png"))
        height, width = image.shape[:2]
        year = relief_year_from_circle(image, {"cx": width / 2, "cy": height / 2, "r": max(width, height) / 2})
        self.assertEqual(year, 1896)


if __name__ == "__main__":
    unittest.main()

