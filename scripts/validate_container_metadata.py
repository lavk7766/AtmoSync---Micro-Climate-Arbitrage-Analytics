
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data/reference"

EXPECTED_COLUMNS = [
    "container_id",
    "product_name",
    "quantity",
    "quantity_unit",
    "origin",
    "destination",
    "batch_id",
    "source_type",
]

EXPECTED_ROUTES = {
    "CONT001": ("Delhi", "Lucknow"),
    "CONT002": ("Mumbai", "Solapur"),
    "CONT003": ("Bengaluru", "Kurnool"),
    "CONT004": ("Kolkata", "Patna"),
    "CONT005": ("Mumbai", "Mangaluru"),
}

with (REFERENCE / "product_spoilage_reference.csv").open(
    encoding="utf-8-sig", newline=""
) as f:
    products = {
        row["product_name"]
        for row in csv.DictReader(f)
    }

with (REFERENCE / "container_metadata.csv").open(
    encoding="utf-8-sig", newline=""
) as f:
    reader = csv.DictReader(f)
    columns = reader.fieldnames
    rows = list(reader)

errors = []
container_ids = []
batch_ids = []

if columns != EXPECTED_COLUMNS:
    errors.append("Incorrect CSV columns")

for line, row in enumerate(rows, start=2):

    if None in row or any(
        not row.get(col, "").strip()
        if isinstance(row.get(col), str)
        else True
        for col in EXPECTED_COLUMNS
    ):
        errors.append(f"Line {line}: Invalid or missing field")
        continue

    cid = row["container_id"].strip().upper()
    product = row["product_name"]
    container_ids.append(cid)
    batch_ids.append(row["batch_id"])

    if product not in products:
        errors.append(f"{cid}: Unknown product {product}")

    try:
        quantity = float(row["quantity"])

        if not math.isfinite(quantity) or quantity <= 0:
            errors.append(f"{cid}: Invalid quantity")

    except (ValueError, TypeError):
        errors.append(f"{cid}: Non-numeric quantity")

    if row["quantity_unit"] != "kg":
        errors.append(f"{cid}: Expected kg")

    if row["source_type"] != "synthetic_simulated":
        errors.append(f"{cid}: Invalid source type")

    route = (row["origin"], row["destination"])

    if EXPECTED_ROUTES.get(cid) != route:
        errors.append(f"{cid}: Route mismatch")

    print(f"{cid} | {product} | {row['quantity']} kg | "
          f"{row['origin']} -> {row['destination']}")

if len(container_ids) != len(set(container_ids)):
    errors.append("Duplicate container IDs")

if len(batch_ids) != len(set(batch_ids)):
    errors.append("Duplicate batch IDs")

if set(container_ids) != set(EXPECTED_ROUTES):
    errors.append("Missing or unexpected container IDs")

if len(rows) != 5:
    errors.append("Expected exactly five containers")

print("\n=== CONTAINER METADATA VALIDATION ===")
print("Total containers:", len(rows))
print("Unique containers:", len(set(container_ids)))
print("Reference products available:", len(products))
print("Validation errors:", len(errors))

for error in errors:
    print(error)

if errors:
    print("RESULT: FAILED")
    raise SystemExit(1)

print("RESULT: PASSED")
print("Product mappings and route checks passed.")
print("Approval status: PENDING COORDINATOR REVIEW")
