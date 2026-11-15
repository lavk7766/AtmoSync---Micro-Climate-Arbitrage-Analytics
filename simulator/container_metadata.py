
import csv
import math
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_METADATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "reference"
    / "container_metadata.csv"
)

REQUIRED_COLUMNS = {
    "container_id",
    "product_name",
    "quantity",
    "quantity_unit",
    "origin",
    "destination",
    "batch_id",
    "source_type",
}


@dataclass(frozen=True)
class ContainerMetadata:
    container_id: str
    product_name: str
    quantity: float
    quantity_unit: str
    origin: str
    destination: str
    batch_id: str
    source_type: str


def normalize_container_id(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Container ID cannot be empty")

    return value.strip().upper()


def _required_text(row, column, line_number):
    value = row.get(column)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Missing or empty '{column}' at CSV line {line_number}"
        )

    return value.strip()


def load_container_metadata(path=None):
    """
    Load and validate container metadata.

    Returns:
        Dictionary keyed by normalized container_id.
    """
    csv_path = Path(path) if path else DEFAULT_METADATA_PATH

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Container metadata CSV not found: {csv_path}. "
            "Create it only after container-product assignments "
            "are confirmed."
        )

    metadata_records = {}

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("Container metadata CSV has no header")

        reader.fieldnames = [
            name.strip() if name else ""
            for name in reader.fieldnames
        ]

        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(
                "Duplicate column names in container metadata CSV"
            )

        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)

        if missing_columns:
            raise ValueError(
                "Container metadata CSV is missing columns: "
                + ", ".join(sorted(missing_columns))
            )

        for line_number, row in enumerate(reader, start=2):

            container_id = normalize_container_id(
                _required_text(row, "container_id", line_number)
            )

            product_name = _required_text(
                row, "product_name", line_number
            )

            try:
                quantity = float(row.get("quantity"))
            except (TypeError, ValueError):
                raise ValueError(
                    f"Invalid quantity at CSV line {line_number}"
                )

            if not math.isfinite(quantity) or quantity <= 0:
                raise ValueError(
                    f"Quantity must be positive and finite "
                    f"at CSV line {line_number}"
                )

            record = ContainerMetadata(
                container_id=container_id,
                product_name=product_name,
                quantity=quantity,
                quantity_unit=_required_text(
                    row, "quantity_unit", line_number
                ),
                origin=_required_text(
                    row, "origin", line_number
                ),
                destination=_required_text(
                    row, "destination", line_number
                ),
                batch_id=_required_text(
                    row, "batch_id", line_number
                ),
                source_type=_required_text(
                    row, "source_type", line_number
                ),
            )

            if container_id in metadata_records:
                raise ValueError(
                    f"Duplicate container ID at CSV line {line_number}: "
                    f"{container_id}"
                )

            metadata_records[container_id] = record

    if not metadata_records:
        raise ValueError(
            "Container metadata CSV contains no records"
        )

    return metadata_records


def get_container_metadata(metadata, container_id):
    """Find metadata using a case-insensitive container ID."""
    normalized_id = normalize_container_id(container_id)

    if normalized_id not in metadata:
        raise KeyError(
            f"No metadata found for container {normalized_id}"
        )

    return metadata[normalized_id]
