
import csv

import pytest

from simulator.product_reference import (
    find_product_reference,
    load_product_references,
)


FIELDNAMES = [
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
    "source_url",
    "notes",
]

VALID_ROW = {
    "product_name": "Apple",
    "product_stage_or_variety": "General fresh apples",
    "recommended_temp_min_c": "-1.0",
    "recommended_temp_max_c": "4.0",
    "best_temp_c": "1.5",
    "humidity_min_pct": "90",
    "humidity_max_pct": "95",
    "shelf_life_min_hours": "720",
    "shelf_life_max_hours": "8640",
    "data_source": "FAO",
    "source_url": "https://example.com",
    "notes": "Test reference",
}


def write_csv(tmp_path, rows, fieldnames=None):
    """Create a temporary product reference CSV for testing."""
    columns = fieldnames or FIELDNAMES
    csv_path = tmp_path / "product_reference.csv"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()

        for row in rows:
            writer.writerow({
                column: row.get(column, "")
                for column in columns
            })

    return csv_path


def test_load_valid_product_reference(tmp_path):
    path = write_csv(tmp_path, [VALID_ROW])

    references = load_product_references(path)

    assert len(references) == 1
    assert ("apple", "general fresh apples") in references

    apple = find_product_reference(references, "APPLE")

    assert apple.product_name == "Apple"
    assert apple.best_temp_c == 1.5
    assert apple.recommended_temp_min_c == -1.0


def test_missing_csv_raises_error(tmp_path):
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        load_product_references(missing_path)


def test_missing_required_column_raises_error(tmp_path):
    columns = [
        column for column in FIELDNAMES
        if column != "data_source"
    ]
    path = write_csv(tmp_path, [VALID_ROW], columns)

    with pytest.raises(ValueError, match="missing columns"):
        load_product_references(path)


@pytest.mark.parametrize(
    "column,value,error_message",
    [
        (
            "recommended_temp_min_c",
            "5",
            "Invalid temperature range",
        ),
        (
            "best_temp_c",
            "5",
            "Best temperature is outside",
        ),
        (
            "humidity_max_pct",
            "105",
            "Invalid humidity range",
        ),
        (
            "shelf_life_min_hours",
            "9000",
            "Invalid shelf-life range",
        ),
        (
            "best_temp_c",
            "not-a-number",
            "Invalid numeric value",
        ),
    ],
)
def test_invalid_reference_values_raise_error(
    tmp_path, column, value, error_message
):
    row = {**VALID_ROW, column: value}
    path = write_csv(tmp_path, [row])

    with pytest.raises(ValueError, match=error_message):
        load_product_references(path)


def test_duplicate_product_and_stage_raise_error(tmp_path):
    path = write_csv(tmp_path, [VALID_ROW, VALID_ROW])

    with pytest.raises(ValueError, match="Duplicate product"):
        load_product_references(path)


def test_product_lookup_normalizes_name_and_stage(tmp_path):
    path = write_csv(tmp_path, [VALID_ROW])

    references = load_product_references(path)

    apple = find_product_reference(
        references,
        " apple ",
        "GENERAL FRESH APPLES",
    )

    assert apple.product_name == "Apple"


def test_ambiguous_product_requires_stage(tmp_path):
    second_row = {
        **VALID_ROW,
        "product_stage_or_variety": "Organic apples",
    }
    path = write_csv(tmp_path, [VALID_ROW, second_row])

    references = load_product_references(path)

    with pytest.raises(ValueError, match="multiple stages"):
        find_product_reference(references, "Apple")


def test_unknown_product_raises_error(tmp_path):
    path = write_csv(tmp_path, [VALID_ROW])

    references = load_product_references(path)

    with pytest.raises(KeyError, match="No product reference"):
        find_product_reference(references, "Pineapple")
