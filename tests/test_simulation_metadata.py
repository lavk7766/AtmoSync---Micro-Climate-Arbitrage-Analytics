import csv

import pytest

from simulator.simulation_metadata import (
    load_product_references_for_containers,
)


METADATA_FIELDS = [
    "container_id",
    "product_name",
    "quantity",
    "quantity_unit",
    "origin",
    "destination",
    "batch_id",
    "source_type",
]

PRODUCT_FIELDS = [
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


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return path


def metadata_row(container_id, product_name):
    return {
        "container_id": container_id,
        "product_name": product_name,
        "quantity": "500",
        "quantity_unit": "kg",
        "origin": "Delhi",
        "destination": "Lucknow",
        "batch_id": f"BATCH_{container_id}",
        "source_type": "synthetic_simulated",
    }


def product_row(product_name, stage):
    return {
        "product_name": product_name,
        "product_stage_or_variety": stage,
        "recommended_temp_min_c": "-1",
        "recommended_temp_max_c": "4",
        "best_temp_c": "1.5",
        "humidity_min_pct": "90",
        "humidity_max_pct": "95",
        "shelf_life_min_hours": "720",
        "shelf_life_max_hours": "8640",
        "data_source": "test_reference",
        "source_url": "",
        "notes": "Test data only",
    }


def test_no_reference_files_uses_generic_mode(tmp_path):
    result = load_product_references_for_containers(
        ["CONT001"],
        tmp_path / "container_metadata.csv",
        tmp_path / "product_reference.csv",
    )

    assert result == {}


def test_loads_product_reference_for_each_container(tmp_path):
    metadata_path = write_csv(
        tmp_path / "container_metadata.csv",
        METADATA_FIELDS,
        [
            metadata_row("CONT001", "Apple"),
            metadata_row("CONT002", "Banana"),
        ],
    )

    product_path = write_csv(
        tmp_path / "product_reference.csv",
        PRODUCT_FIELDS,
        [
            product_row("Apple", "General fresh apples"),
            product_row("Banana", "General fresh bananas"),
        ],
    )

    result = load_product_references_for_containers(
        ["CONT001", "CONT002"],
        metadata_path,
        product_path,
    )

    assert len(result) == 2
    assert result["CONT001"].product_name == "Apple"
    assert result["CONT002"].product_name == "Banana"


def test_missing_metadata_csv_raises_error(tmp_path):
    product_path = write_csv(
        tmp_path / "product_reference.csv",
        PRODUCT_FIELDS,
        [product_row("Apple", "General fresh apples")],
    )

    with pytest.raises(
        FileNotFoundError,
        match="Container metadata CSV not found",
    ):
        load_product_references_for_containers(
            ["CONT001"],
            tmp_path / "missing_metadata.csv",
            product_path,
        )


def test_missing_product_reference_csv_raises_error(tmp_path):
    metadata_path = write_csv(
        tmp_path / "container_metadata.csv",
        METADATA_FIELDS,
        [metadata_row("CONT001", "Apple")],
    )

    with pytest.raises(
        FileNotFoundError,
        match="Product reference CSV not found",
    ):
        load_product_references_for_containers(
            ["CONT001"],
            metadata_path,
            tmp_path / "missing_products.csv",
        )


def test_missing_container_assignment_raises_error(tmp_path):
    metadata_path = write_csv(
        tmp_path / "container_metadata.csv",
        METADATA_FIELDS,
        [metadata_row("CONT001", "Apple")],
    )

    product_path = write_csv(
        tmp_path / "product_reference.csv",
        PRODUCT_FIELDS,
        [product_row("Apple", "General fresh apples")],
    )

    with pytest.raises(KeyError, match="No metadata found"):
        load_product_references_for_containers(
            ["CONT002"],
            metadata_path,
            product_path,
        )


def test_unknown_product_raises_error(tmp_path):
    metadata_path = write_csv(
        tmp_path / "container_metadata.csv",
        METADATA_FIELDS,
        [metadata_row("CONT001", "Pineapple")],
    )

    product_path = write_csv(
        tmp_path / "product_reference.csv",
        PRODUCT_FIELDS,
        [product_row("Apple", "General fresh apples")],
    )

    with pytest.raises(KeyError, match="No product reference found"):
        load_product_references_for_containers(
            ["CONT001"],
            metadata_path,
            product_path,
        )


def test_ambiguous_product_stage_raises_error(tmp_path):
    metadata_path = write_csv(
        tmp_path / "container_metadata.csv",
        METADATA_FIELDS,
        [metadata_row("CONT001", "Apple")],
    )

    product_path = write_csv(
        tmp_path / "product_reference.csv",
        PRODUCT_FIELDS,
        [
            product_row("Apple", "General fresh apples"),
            product_row("Apple", "Organic apples"),
        ],
    )

    with pytest.raises(ValueError, match="multiple stages"):
        load_product_references_for_containers(
            ["CONT001"],
            metadata_path,
            product_path,
        )