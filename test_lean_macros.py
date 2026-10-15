"""Run with:  python -m unittest   (no network needed)"""
import unittest

from lean_macros import get_grams, pick_food, read_line, to_number


def food(fdc_id, description, nutrients):
    return {
        "fdcId": fdc_id,
        "description": description,
        "foodNutrients": [{"nutrientId": nid, "value": val} for nid, val in nutrients.items()],
    }


class TestNumbers(unittest.TestCase):
    def test_whole_decimal_fraction_mixed(self):
        self.assertEqual(to_number("2"), 2)
        self.assertEqual(to_number("1.5"), 1.5)
        self.assertEqual(to_number("1/2"), 0.5)
        self.assertEqual(to_number("1 1/2"), 1.5)


class TestReadLine(unittest.TestCase):
    def test_weight(self):
        self.assertEqual(read_line("200 g chicken breast"), (200, "g", "chicken breast"))

    def test_no_space_before_unit(self):
        self.assertEqual(read_line("100g oats"), (100, "g", "oats"))

    def test_mixed_fraction_and_plural_unit(self):
        self.assertEqual(read_line("1 1/2 cups cooked rice"), (1.5, "cup", "cooked rice"))

    def test_of_is_dropped(self):
        self.assertEqual(read_line("1/2 cup of milk"), (0.5, "cup", "milk"))

    def test_size_word(self):
        self.assertEqual(read_line("2 large eggs"), (2, "large", "eggs"))

    def test_plain_count(self):
        self.assertEqual(read_line("2 eggs"), (2, "each", "eggs"))

    def test_missing_amount_is_an_error(self):
        with self.assertRaises(ValueError):
            read_line("chicken")


class TestPickFood(unittest.TestCase):
    def test_chicken_breast_skips_lunchmeat_with_no_macros(self):
        foods = [
            food(2759004, "Lunchmeat, chicken breast, sliced", {1258: 0.7}),
            food(171515, "Chicken breast tenders, breaded, uncooked", {1008: 263, 1003: 14.7, 1004: 15.8, 1005: 15}),
            food(2646170, "Chicken, breast, boneless, skinless, raw", {2047: 106, 1003: 22.5, 1004: 1.93, 1005: 0}),
        ]
        fdc_id, name, macros = pick_food("chicken breast", foods)
        self.assertEqual(fdc_id, 2646170)
        self.assertEqual(name, "Chicken, breast, boneless, skinless, raw")
        self.assertEqual(macros["calories"], 106)
        self.assertEqual(macros["protein"], 22.5)

    def test_rice_skips_crackers(self):
        foods = [
            food(173161, "Rice crackers", {1008: 387, 1003: 8, 1004: 4, 1005: 80}),
            food(169756, "Rice, white, long-grain, regular, raw, unenriched", {1008: 365, 1003: 7.1, 1004: 0.7, 1005: 80}),
        ]
        fdc_id, name, macros = pick_food("rice", foods)
        self.assertEqual(fdc_id, 169756)
        self.assertGreater(macros["calories"], 0)

    def test_buffalo_sauce_does_not_match_buffalo_milk(self):
        foods = [
            food(171280, "Milk, indian buffalo, fluid", {1008: 97, 1003: 3.8, 1004: 6.9, 1005: 5.2}),
        ]
        with self.assertRaises(ValueError):
            pick_food("buffalo sauce", foods)


class TestWeights(unittest.TestCase):
    def test_ounces_to_grams(self):
        grams, note = get_grams(2, "oz", None)  # weights never need a USDA lookup
        self.assertAlmostEqual(grams, 56.699)
        self.assertEqual(note, "")


if __name__ == "__main__":
    unittest.main()
