# Macro Calculator

## Aim

Type in ingredients and their measurements, get the total calories, protein,
carbs and fat. Nothing else.

## Principles

- **Lean.** One small Python file, plain code, no frameworks.
- **No dependencies.** Standard library only (`urllib`, `json`, `os`, `sys`).
- **Honest output.** Anything that can't be read or matched is listed as
  `SKIPPED` rather than guessed, so the total is never silently wrong.

## Run it

Get a free key at https://fdc.nal.usda.gov, then:

```bash
export FDC_API_KEY=your_key

python lean_macros.py                     # type one ingredient per line, blank line to finish
python lean_macros.py "200 g chicken breast" "1 1/2 cups cooked rice" "2 large eggs"
```

Example output (numbers illustrative):

```
200 g chicken breast  =  200 g of 'Chicken breast'
1 1/2 cups cooked rice  =  237 g of 'Rice, cooked'
2 large eggs  =  100 g of 'Egg'

TOTAL: 691 kcal | protein 64.0 g | carbs 67.1 g | fat 15.4 g
```

## Input format

`<amount> <unit> <ingredient>`

- Amounts: `2`, `1.5`, `1/2`, `1 1/2`
- Weights: `g`, `kg`, `oz`, `lb`
- Volumes: `ml`, `l`, `tsp`, `tbsp`, `cup`
- Counts and sizes: `small`, `medium`, `large`, `whole`, `clove`, `slice`, `piece`
  (or no unit at all: `2 eggs`)

## How it works

1. `read_line` splits a line into amount, unit and ingredient name.
2. `find_food` searches USDA FoodData Central (Foundation and SR Legacy
   data) and takes the top match, with macros per 100 g.
3. `get_grams` converts the amount to grams. Weights convert directly.
   Cups, tablespoons, teaspoons and counts use USDA's measured portion for
   that specific food (a cup of flour weighs less than a cup of honey).
4. Macros = per-100 g value x grams / 100, summed across ingredients.

## Known limitations

- The top USDA search result is used, so vague names can match oddly. Use
  specific names ("cooked white rice", "raw chicken breast"). The matched
  food is printed on each line so you can check it.
- If USDA has no measured portion for a cup/tbsp/tsp, it assumes
  1 ml = 1 g and prints a note. Grams are more accurate for dense or fluffy foods.
- Needs internet access. `DEMO_KEY` works but is heavily rate-limited.
- Two-word units like "fl oz" aren't supported.

## Maintaining

- Run the tests after any change: `python -m unittest`
  (they cover parsing and unit conversion and need no network).
- The USDA lookups are the only part not covered by tests; after changing
  `find_food`, `portion_grams` or `get_grams`, run a real request and
  check the matched foods look right.
- Keep it lean: before adding a dependency or a feature, ask whether the
  aim above needs it.

## Files

- `lean_macros.py` - the program
- `test_lean_macros.py` - offline tests
- `README.md` - this file
