
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data/reference/product_spoilage_reference.csv"

EXPECTED_PRODUCTS = {
    "Apple", "Banana", "Tomato", "Strawberry",
    "Apricot", "Blueberry", "Grape", "Guava",
    "Mango", "Orange", "Broccoli", "Cabbage",
    "Carrot", "Cucumber", "Eggplant", "Garlic",
    "Spinach", "Sweet Pepper", "Green Beans",
    "Dry Onion"
}

with PATH.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

errors = []
names = []

for row in rows:
    product = row["product_name"]
    names.append(product)

    try:
        tmin = float(row["recommended_temp_min_c"])
        tmax = float(row["recommended_temp_max_c"])
        best = float(row["best_temp_c"])
        hmin = float(row["humidity_min_pct"])
        hmax = float(row["humidity_max_pct"])
        smin = float(row["shelf_life_min_hours"])
        smax = float(row["shelf_life_max_hours"])

        values = [tmin, tmax, best, hmin, hmax, smin, smax]

        if not all(math.isfinite(v) for v in values):
            errors.append(f"{product}: Non-finite value")

        if not tmin <= best <= tmax:
            errors.append(f"{product}: Invalid temperature range")

        if not math.isclose(best, (tmin + tmax) / 2):
            errors.append(f"{product}: Incorrect midpoint")

        if not 0 <= hmin <= hmax <= 100:
            errors.append(f"{product}: Invalid humidity range")

        if not 0 < smin <= smax:
            errors.append(f"{product}: Invalid shelf life")

        if row["data_source"] != "FAO":
            errors.append(f"{product}: Unexpected source")

        if row["source_url"] != "https://www.fao.org/4/ae075e/ae075e15.htm":
            errors.append(f"{product}: Incorrect source URL")

        if any(v is None or not str(v).strip()
               for v in row.values()):
            errors.append(f"{product}: Missing field")

    except (ValueError, TypeError, KeyError) as exc:
        errors.append(f"{product}: {exc}")

if set(names) != EXPECTED_PRODUCTS:
    errors.append("Product names do not match expected products")

if len(names) != len(set(names)):
    errors.append("Duplicate product names")

if len(rows) != 20:
    errors.append("Expected exactly 20 products")

print("=== PRODUCT REFERENCE VALIDATION ===")
print(f"Total products: {len(rows)}")
print(f"Unique products: {len(set(names))}")
print(f"Validation errors: {len(errors)}")

for error in errors:
    print(error)

if errors:
    print("RESULT: FAILED")
    raise SystemExit(1)

print("RESULT: PASSED")
print("All product reference consistency checks passed.")
print("Original CSV unchanged.")
