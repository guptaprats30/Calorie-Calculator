"""
Type in ingredients, get total macros.

    python lean_macros.py                      (then type one ingredient per line, blank line to finish)
    python lean_macros.py "200 g chicken breast" "1 1/2 cups cooked rice" "2 large eggs"

Needs a free USDA key:  export FDC_API_KEY=your_key   (https://fdc.nal.usda.gov)
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

KEY = os.environ.get("FDC_API_KEY", "DEMO_KEY")
URL = "https://api.nal.usda.gov/fdc/v1"

WEIGHTS = {"g": 1, "kg": 1000, "oz": 28.3495, "lb": 453.592}
VOLUMES = {"ml": 1, "l": 1000, "tsp": 4.92892, "tbsp": 14.7868, "cup": 236.588}
COUNTS = ["small", "medium", "large", "whole", "clove", "slice", "piece"]
ALIASES = {
    "gram": "g", "grams": "g", "ounce": "oz", "ounces": "oz",
    "pound": "lb", "pounds": "lb", "lbs": "lb",
    "teaspoon": "tsp", "teaspoons": "tsp", "tablespoon": "tbsp", "tablespoons": "tbsp",
    "cups": "cup", "cloves": "clove", "slices": "slice", "pieces": "piece",
}
KNOWN_UNITS = list(WEIGHTS) + list(VOLUMES) + COUNTS

# USDA nutrient ids. Foundation foods publish energy as 2047, SR Legacy as 1008.
NUTRIENTS = {1008: "calories", 2047: "calories", 1003: "protein", 1005: "carbs", 1004: "fat"}
# Words USDA tacks onto a plain food ("Rice, white, long-grain, raw"). They should
# not make that food lose to a short lookalike like "Rice crackers".
QUALIFIERS = {
    "raw", "cooked", "white", "brown", "long", "grain", "regular", "enriched",
    "unenriched", "boneless", "skinless", "meat", "skin", "dry", "boiled",
    "without", "salt", "fresh", "plain", "and", "or", "with",
}
# Short prepared foods that the search API ranks above the plain ingredient.
PREPARED = {
    "breaded", "fried", "cracker", "crackers", "cake", "cakes", "snack", "snacks",
    "lunchmeat", "sliced", "tender", "tenders", "nugget", "nuggets", "roll",
    "patty", "patties",
}


def ask_usda(path, **params):
    params["api_key"] = KEY
    url = URL + path + "?" + urllib.parse.urlencode(params)
    return json.load(urllib.request.urlopen(url, timeout=10))


def words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def food_macros(food):
    """Calories and macros per 100 g. Missing nutrients are left out."""
    macros = {}
    for nutrient in food.get("foodNutrients") or []:
        key = NUTRIENTS.get(nutrient.get("nutrientId"))
        if key and nutrient.get("value") is not None:
            macros.setdefault(key, nutrient["value"])
    return macros


def match_penalty(query, description):
    """Lower is a closer name. None when a query word is missing."""
    query_words = words(query)
    desc_words = words(description)
    if not query_words or any(word not in desc_words for word in query_words):
        return None
    extra = [word for word in desc_words if word not in query_words and word not in QUALIFIERS]
    penalty = len(extra) + 8 * sum(word in PREPARED for word in extra)
    if desc_words[0] != query_words[0]:
        penalty += 4
    return penalty


def pick_food(query, foods):
    """Best search hit that actually publishes calories and protein."""
    best = None
    best_penalty = None
    for food in foods:
        macros = food_macros(food)
        if "calories" not in macros or "protein" not in macros:
            continue
        penalty = match_penalty(query, food.get("description") or "")
        if penalty is None:
            continue
        if best is None or penalty < best_penalty:
            best = (food["fdcId"], food["description"], macros)
            best_penalty = penalty
    if best is None:
        raise ValueError("no match found")
    return best


def find_food(name):
    """Returns (food id, food name, macros per 100 g)."""
    # pageSize 1 returns "Lunchmeat, chicken breast", which has no energy or protein.
    results = ask_usda("/foods/search", query=name, dataType="Foundation,SR Legacy", pageSize=50)
    return pick_food(name, results.get("foods") or [])


def portion_grams(food_id, word):
    """Grams in one 'cup' / 'large' / etc. of this food, or None if USDA doesn't list it."""
    for p in ask_usda("/food/" + str(food_id)).get("foodPortions", []):
        label = (p.get("modifier") or "") + " " + (p.get("measureUnit") or {}).get("name", "")
        if word in label.lower().replace(",", " ").split() and p.get("gramWeight"):
            return p["gramWeight"] / (p.get("amount") or 1)
    return None


def to_number(text):
    """'2' -> 2, '1.5' -> 1.5, '1/2' -> 0.5, '1 1/2' -> 1.5"""
    total = 0
    for part in text.split():
        if "/" in part:
            top, bottom = part.split("/")
            total += float(top) / float(bottom)
        else:
            total += float(part)
    return total


def read_line(line):
    """'1 1/2 cups cooked rice' -> (1.5, 'cup', 'cooked rice')"""
    i = 0
    while i < len(line) and (line[i].isdigit() or line[i] in "./ "):
        i += 1
    if i == 0:
        raise ValueError("start with an amount, like '200 g chicken'")
    amount = to_number(line[:i])
    words = line[i:].split()

    unit = "each"
    if len(words) > 1:
        first = words[0].lower().rstrip(".")
        first = ALIASES.get(first, first)
        if first in KNOWN_UNITS:
            unit = first
            words.pop(0)
    if words and words[0].lower() == "of":
        words.pop(0)
    if not words:
        raise ValueError("no ingredient name")
    return amount, unit, " ".join(words)


def get_grams(amount, unit, food_id):
    if unit in WEIGHTS:
        return amount * WEIGHTS[unit], ""

    if unit in VOLUMES:
        if unit in ("cup", "tbsp", "tsp"):
            one = portion_grams(food_id, unit)
            if one:
                return amount * one, ""
        return amount * VOLUMES[unit], " (no measure found, assumed 1 ml = 1 g)"

    # counts: "2 large eggs", "3 cloves garlic", "2 eggs"
    words = ["medium", "large", "whole", "small"] if unit == "each" else [unit]
    for word in words:
        one = portion_grams(food_id, word)
        if one:
            return amount * one, ""
    raise ValueError("no size found for '" + unit + "', use grams instead")


def main():
    if len(sys.argv) > 1:
        lines = sys.argv[1:]
    else:
        print("Type one ingredient per line (like '200 g chicken breast'). Blank line to finish.")
        lines = []
        while True:
            line = input("> ").strip()
            if not line:
                break
            lines.append(line)

    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    problems = []

    for line in lines:
        try:
            amount, unit, name = read_line(line)
            food_id, food_name, macros = find_food(name.lower())
            grams, note = get_grams(amount, unit, food_id)
        except Exception as error:
            problems.append(line + "  ->  " + str(error))
            continue

        for key in total:
            total[key] += macros.get(key, 0) * grams / 100
        print(line + "  =  " + format(grams, ".0f") + " g of '" + food_name + "'" + note)

    print()
    for problem in problems:
        print("SKIPPED: " + problem)
    print("TOTAL: {calories:.0f} kcal | protein {protein:.1f} g | carbs {carbs:.1f} g | fat {fat:.1f} g".format(**total))


if __name__ == "__main__":
    main()
