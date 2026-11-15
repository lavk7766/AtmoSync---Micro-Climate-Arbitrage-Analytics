
import csv

import pytest

from simulator.container_metadata import (
    get_container_metadata,
    load_container_metadata,
)


FIELDNAMES = [
    "container_id",
    "product_name",
    "quantity",
    "quantity_unit",
    "origin",
    "destination",
    "batch_id",
    "source_type",
]

VALID_ROW = {
    "container_id": "CONT001",
    "product_name": "Apple",
    "quantity": "1000",
    "quantity_unit": "kg",
    "origin": "Delhi",
    "destination": "Lucknow",
    "batch_id": "BATCH001",
    "source_type": "synthetic_simulated",
}


def write_csv(tmp_path, rows, fieldnames=None):
    """Create a temporary container metadata CSV."""
    columns = fieldnames or FIELDNAMES
    csv_path = tmp_path / "container_metadata.csv"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()

        for row in rows:
            writer.writerow({
                column: row.get(column, "")
                for column in columns
            })

    return csv_path


def test_load_valid_container_metadata(tmp_path):
    path = write_csv(tmp_path, [VALID_ROW])

    metadata = load_container_metadata(path)

    assert len(metadata) == 1
    assert "CONT001" in metadata
    assert metadata["CONT001"].product_name == "Apple"
    assert metadata["CONT001"].quantity == 1000.0
    assert metadata["CONT001"].quantity_unit == "kg"


def test_missing_csv_raises_error(tmp_path):
    path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        load_container_metadata(path)


def test_missing_required_column_raises_error(tmp_path):
    columns = [
        column for column in FIELDNAMES
        if column != "batch_id"
    ]
    path = write_csv(tmp_path, [VALID_ROW], columns)

    with pytest.raises(ValueError, match="missing columns"):
        load_container_metadata(path)


def test_empty_csv_raises_error(tmp_path):
    path = write_csv(tmp_path, [])

    with pytest.raises(ValueError, match="no records"):
        load_container_metadata(path)


@pytest.mark.parametrize(
    "quantity",
    ["0", "-10", "nan", "inf"],
)
def test_invalid_quantity_values_raise_error(tmp_path, quantity):
    row = {**VALID_ROW, "quantity": quantity}
    path = write_csv(tmp_path, [row])

    with pytest.raises(ValueError, match="positive and finite"):
        load_container_metadata(path)


def test_non_numeric_quantity_raises_error(tmp_path):
    row = {**VALID_ROW, "quantity": "unknown"}
    path = write_csv(tmp_path, [row])

    with pytest.raises(ValueError, match="Invalid quantity"):
        load_container_metadata(path)


def test_empty_required_text_raises_error(tmp_path):
    row = {**VALID_ROW, "batch_id": ""}
    path = write_csv(tmp_path, [row])

    with pytest.raises(ValueError, match="batch_id"):
        load_container_metadata(path)


def test_duplicate_container_ids_raise_error(tmp_path):
    second_row = {
        **VALID_ROW,
        "container_id": " cont001 ",
    }
    path = write_csv(tmp_path, [VALID_ROW, second_row])

    with pytest.raises(ValueError, match="Duplicate container ID"):
        load_container_metadata(path)


def test_container_id_is_normalized(tmp_path):
    row = {**VALID_ROW, "container_id": " cont001 "}
    path = write_csv(tmp_path, [row])

    metadata = load_container_metadata(path)

    assert "CONT001" in metadata


def test_lookup_normalizes_container_id(tmp_path):
    path = write_csv(tmp_path, [VALID_ROW])

    metadata = load_container_metadata(path)
    record = get_container_metadata(metadata, " cont001 ")

    assert record.container_id == "CONT001"
    assert record.product_name == "Apple"


def test_unknown_container_raises_error(tmp_path):
    path = write_csv(tmp_path, [VALID_ROW])

    metadata = load_container_metadata(path)

    with pytest.raises(KeyError, match="No metadata found"):
        get_container_metadata(metadata, "CONT999")
