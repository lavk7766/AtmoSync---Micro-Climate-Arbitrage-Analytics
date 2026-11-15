
import csv
import math
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_PRODUCT_REFERENCE_PATH = (
    PROJECT_ROOT
    / "data"
    / "reference"
    / "product_spoilage_reference.csv"
)

REQUIRED_COLUMNS = {
    "product_name",
    "product_stage_or_variety",
    "recommended_temp_min_c",
    "recommended_temp_max_c",
    "best_temp_c",
    "humidity_min_pct",
    "humidity_max_pct",
    "shelf_life_min_hours",
    "shelf_life_max_hours",
    "data_source",
}


@dataclass(frozen=True)
class ProductReference:
    product_name: str
    product_stage_or_variety: str
    recommended_temp_min_c: float
    recommended_temp_max_c: float
    best_temp_c: float
    humidity_min_pct: float
    humidity_max_pct: float
    shelf_life_min_hours: float
    shelf_life_max_hours: float
    data_source: str
    source_url: str = ""
    notes: str = ""


def normalize_product_name(value):
    """Match the lower-case, trimmed format used by dbt."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Product name cannot be empty")

    return value.strip().lower()


def _read_float(row, column, line_number):
    raw_value = row.get(column)

    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid numeric value for '{column}' "
            f"at CSV line {line_number}: {raw_value!r}"
        )

    if not math.isfinite(value):
        raise ValueError(
            f"Non-finite value for '{column}' "
            f"at CSV line {line_number}"
        )

    return value


def load_product_references(path=None):
    """
    Load and validate product reference data.

    Returns:
        Dictionary keyed by (normalized product name, normalized stage).
    """
    csv_path = Path(path) if path else DEFAULT_PRODUCT_REFERENCE_PATH

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Product reference CSV not found: {csv_path}. "
            "Obtain the canonical file before enabling product-aware "
            "simulation."
        )

    references = {}

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("Product reference CSV has no header")

        reader.fieldnames = [
            name.strip() if name else ""
            for name in reader.fieldnames
        ]

        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("Duplicate column names in product reference CSV")

        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)

        if missing_columns:
            raise ValueError(
                "Product reference CSV is missing columns: "
                + ", ".join(sorted(missing_columns))
            )

        for line_number, row in enumerate(reader, start=2):
            product_name = (row.get("product_name") or "").strip()
            stage = (
                row.get("product_stage_or_variety") or ""
            ).strip()
            data_source = (row.get("data_source") or "").strip()

            if not product_name or not stage or not data_source:
                raise ValueError(
                    f"Missing product name, stage or data source "
                    f"at CSV line {line_number}"
                )

            reference = ProductReference(
                product_name=product_name,
                product_stage_or_variety=stage,
                recommended_temp_min_c=_read_float(
                    row, "recommended_temp_min_c", line_number
                ),
                recommended_temp_max_c=_read_float(
                    row, "recommended_temp_max_c", line_number
                ),
                best_temp_c=_read_float(
                    row, "best_temp_c", line_number
                ),
                humidity_min_pct=_read_float(
                    row, "humidity_min_pct", line_number
                ),
                humidity_max_pct=_read_float(
                    row, "humidity_max_pct", line_number
                ),
                shelf_life_min_hours=_read_float(
                    row, "shelf_life_min_hours", line_number
                ),
                shelf_life_max_hours=_read_float(
                    row, "shelf_life_max_hours", line_number
                ),
                data_source=data_source,
                source_url=(row.get("source_url") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            )

            if (
                reference.recommended_temp_min_c
                > reference.recommended_temp_max_c
            ):
                raise ValueError(
                    f"Invalid temperature range at CSV line {line_number}"
                )

            if not (
                reference.recommended_temp_min_c
                <= reference.best_temp_c
                <= reference.recommended_temp_max_c
            ):
                raise ValueError(
                    f"Best temperature is outside the recommended range "
                    f"at CSV line {line_number}"
                )

            if not (
                0
                <= reference.humidity_min_pct
                <= reference.humidity_max_pct
                <= 100
            ):
                raise ValueError(
                    f"Invalid humidity range at CSV line {line_number}"
                )

            if not (
                0
                < reference.shelf_life_min_hours
                <= reference.shelf_life_max_hours
            ):
                raise ValueError(
                    f"Invalid shelf-life range at CSV line {line_number}"
                )

            key = (
                normalize_product_name(reference.product_name),
                normalize_product_name(
                    reference.product_stage_or_variety
                ),
            )

            if key in references:
                raise ValueError(
                    f"Duplicate product and stage at CSV line {line_number}: "
                    f"{reference.product_name} / "
                    f"{reference.product_stage_or_variety}"
                )

            references[key] = reference

    if not references:
        raise ValueError("Product reference CSV contains no product records")

    return references


def find_product_reference(references, product_name, stage=None):
    """Find a product reference without silently choosing an ambiguous stage."""
    normalized_name = normalize_product_name(product_name)

    matches = [
        reference
        for (name, _), reference in references.items()
        if name == normalized_name
    ]

    if stage is not None:
        normalized_stage = normalize_product_name(stage)

        matches = [
            reference
            for reference in matches
            if normalize_product_name(
                reference.product_stage_or_variety
            ) == normalized_stage
        ]

    if not matches:
        raise KeyError(
            f"No product reference found for {product_name!r}"
        )

    if len(matches) > 1:
        stages = ", ".join(
            reference.product_stage_or_variety
            for reference in matches
        )
        raise ValueError(
            f"Product {product_name!r} has multiple stages: {stages}. "
            "Specify the stage explicitly."
        )

    return matches[0]
