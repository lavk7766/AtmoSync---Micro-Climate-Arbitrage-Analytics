"""Deterministic synthetic local-market price generator for AtmoSync.

IMPORTANT:
Generated prices are illustrative assumptions, not actual market quotations.
They must not be represented as observed or verified Indian market prices.
"""

import csv
import math
import random
import re
from datetime import date
from numbers import Real
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONTAINER_METADATA_PATH = (
    PROJECT_ROOT / "data/reference/container_metadata.csv"
)
PRODUCT_REFERENCE_PATH = (
    PROJECT_ROOT / "data/reference/product_spoilage_reference.csv"
)
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/processed/synthetic_market_prices/"
    / "synthetic_local_market_prices.csv"
)

DEFAULT_RANDOM_SEED = 20261125
DEFAULT_VARIATION_PCT = 0.15
DEFAULT_AS_OF_DATE = "2026-11-25"

# Explicit synthetic development assumptions.
# These are NOT sourced market prices.
BASE_PRICE_ASSUMPTIONS_INR_PER_KG = {
    "Apple": 150.0,
    "Banana": 45.0,
    "Orange": 65.0,
    "Tomato": 35.0,
    "Strawberry": 220.0,
}

CSV_FIELDS = [
    "price_observation_id",
    "scenario_id",
    "scenario_type",
    "simulated_as_of_date",
    "product_name",
    "market_name",
    "market_country",
    "price_per_kg",
    "currency",
    "quantity_unit",
    "base_assumption_inr_per_kg",
    "market_adjustment_pct",
    "price_source_type",
    "source_name",
    "source_note",
    "random_seed",
]


def _validate_names(values: Iterable[str], field_name: str) -> list[str]:
    """Validate, normalize and sort a collection of unique names."""

    if isinstance(values, (str, bytes)):
        raise ValueError(f"{field_name} must be a collection of names.")

    try:
        names = list(values)
    except TypeError as exc:
        raise ValueError(
            f"{field_name} must be an iterable of names."
        ) from exc

    if not names:
        raise ValueError(f"{field_name} cannot be empty.")

    normalized = []

    for value in names:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Every item in {field_name} must be a non-empty string."
            )
        normalized.append(value.strip())

    normalized_keys = [value.casefold() for value in normalized]

    if len(normalized_keys) != len(set(normalized_keys)):
        raise ValueError(f"{field_name} contains duplicate names.")

    return sorted(normalized, key=str.casefold)


def load_project_products_and_markets(
    metadata_path: Path = CONTAINER_METADATA_PATH,
    product_reference_path: Path = PRODUCT_REFERENCE_PATH,
) -> tuple[list[str], list[str]]:
    """Read active products and shipment markets from project reference CSVs.

    All active products must have an entry in the product spoilage reference.
    """

    metadata_path = Path(metadata_path)
    product_reference_path = Path(product_reference_path)

    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Container metadata not found: {metadata_path}"
        )

    if not product_reference_path.exists():
        raise FileNotFoundError(
            f"Product reference not found: {product_reference_path}"
        )

    with metadata_path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        metadata_reader = csv.DictReader(file)

        required_metadata = {
            "container_id",
            "product_name",
            "origin",
            "destination",
        }

        if not required_metadata.issubset(
            set(metadata_reader.fieldnames or [])
        ):
            raise ValueError(
                "Container metadata is missing required columns."
            )

        metadata_rows = list(metadata_reader)

    with product_reference_path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reference_reader = csv.DictReader(file)

        if "product_name" not in (reference_reader.fieldnames or []):
            raise ValueError(
                "Product reference is missing product_name."
            )

        reference_rows = list(reference_reader)

    if not metadata_rows:
        raise ValueError("Container metadata contains no records.")

    if not reference_rows:
        raise ValueError("Product reference contains no records.")

    products = _validate_names(
        (row["product_name"] for row in metadata_rows),
        "Products",
    )

    reference_products = {
        row["product_name"].strip()
        for row in reference_rows
        if row.get("product_name", "").strip()
    }

    missing_products = set(products) - reference_products

    if missing_products:
        raise ValueError(
            "Products missing from spoilage reference: "
            + ", ".join(sorted(missing_products))
        )

    # The same city can appear in multiple shipments.
    # Deduplicate metadata-derived markets case-insensitively.
    market_values = [
        market
        for row in metadata_rows
        for market in (row["origin"], row["destination"])
    ]

    unique_markets = {}

    for market in market_values:
        if not isinstance(market, str) or not market.strip():
            raise ValueError(
                "Every metadata market must be a non-empty string."
            )

        normalized_market = market.strip()
        unique_markets.setdefault(
            normalized_market.casefold(),
            normalized_market,
        )

    markets = _validate_names(
        unique_markets.values(),
        "Markets",
    )

    return products, markets


def _slug(value: str) -> str:
    """Create a stable identifier component from a name."""

    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return slug.upper()


def generate_synthetic_local_market_prices(
    products: Iterable[str],
    markets: Iterable[str],
    *,
    seed: int = DEFAULT_RANDOM_SEED,
    variation_pct: float = DEFAULT_VARIATION_PCT,
    as_of_date: str = DEFAULT_AS_OF_DATE,
) -> list[dict[str, object]]:
    """Generate deterministic synthetic INR/kg prices.

    Each product-market pair receives one quote.

    The seeded market adjustments are independent illustrative variations
    around the configured synthetic product price assumptions.
    """

    products = _validate_names(products, "Products")
    markets = _validate_names(markets, "Markets")

    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer.")

    if (
        isinstance(variation_pct, bool)
        or not isinstance(variation_pct, Real)
        or not math.isfinite(float(variation_pct))
        or not 0 <= float(variation_pct) < 1
    ):
        raise ValueError(
            "variation_pct must be finite and between zero and one."
        )

    if not isinstance(as_of_date, str):
        raise ValueError("as_of_date must be an ISO date string.")

    try:
        date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise ValueError(
            "as_of_date must use YYYY-MM-DD format."
        ) from exc

    unsupported_products = (
        set(products) - set(BASE_PRICE_ASSUMPTIONS_INR_PER_KG)
    )

    if unsupported_products:
        raise ValueError(
            "No synthetic base-price assumption configured for: "
            + ", ".join(sorted(unsupported_products))
        )

    rng = random.Random(seed)

    compact_date = as_of_date.replace("-", "")
    scenario_id = (
        f"SYNTHETIC-LOCAL-{compact_date}-SEED-{seed}"
    )

    records = []

    for product in products:
        base_price = BASE_PRICE_ASSUMPTIONS_INR_PER_KG[product]

        for market in markets:
            adjustment = rng.uniform(
                -float(variation_pct),
                float(variation_pct),
            )

            simulated_price = round(
                base_price * (1.0 + adjustment),
                2,
            )

            if simulated_price <= 0:
                raise ValueError(
                    "Generated market price must be positive."
                )

            record_id = (
                f"SMP-{compact_date}-{seed}-"
                f"{_slug(product)}-{_slug(market)}"
            )

            records.append({
                "price_observation_id": record_id,
                "scenario_id": scenario_id,
                "scenario_type": "SYNTHETIC_BASELINE",
                "simulated_as_of_date": as_of_date,
                "product_name": product,
                "market_name": market,
                "market_country": "India",
                "price_per_kg": f"{simulated_price:.2f}",
                "currency": "INR",
                "quantity_unit": "kg",
                "base_assumption_inr_per_kg": f"{base_price:.2f}",
                "market_adjustment_pct": f"{adjustment * 100:.2f}",
                "price_source_type": "synthetic_simulated",
                "source_name": "AtmoSync synthetic market price generator",
                "source_note": (
                    "Illustrative seeded simulation assumption; "
                    "not an observed or verified local market quotation."
                ),
                "random_seed": seed,
            })

    return records


def write_market_price_csv(
    records: Iterable[dict[str, object]],
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Write generated market prices to a separate CSV file."""

    records = list(records)

    if not records:
        raise ValueError("Cannot write an empty market-price dataset.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)

    return output_path


def generate_project_market_prices(
    *,
    seed: int = DEFAULT_RANDOM_SEED,
    variation_pct: float = DEFAULT_VARIATION_PCT,
    as_of_date: str = DEFAULT_AS_OF_DATE,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> list[dict[str, object]]:
    """Generate market prices using the current project reference data."""

    products, markets = load_project_products_and_markets()

    records = generate_synthetic_local_market_prices(
        products,
        markets,
        seed=seed,
        variation_pct=variation_pct,
        as_of_date=as_of_date,
    )

    write_market_price_csv(records, output_path)

    return records


def main() -> None:
    records = generate_project_market_prices()

    print("\n========== SYNTHETIC MARKET PRICE GENERATOR ==========")
    print("Generated records:", len(records))
    print("Unique products:", len({
        row["product_name"] for row in records
    }))
    print("Unique markets:", len({
        row["market_name"] for row in records
    }))
    print("Currency: INR")
    print("Unit: per kg")
    print("Random seed:", DEFAULT_RANDOM_SEED)
    print("Variation: +/-", DEFAULT_VARIATION_PCT * 100, "%")
    print("Source type: synthetic_simulated")
    print("Output:", DEFAULT_OUTPUT_PATH)

    print("\n========== PRICE RANGE BY PRODUCT ==========")

    for product in sorted({
        row["product_name"] for row in records
    }):
        prices = [
            float(row["price_per_kg"])
            for row in records
            if row["product_name"] == product
        ]

        print(
            f"{product}: "
            f"min INR {min(prices):.2f}/kg | "
            f"max INR {max(prices):.2f}/kg"
        )

    print("\nGeneration completed successfully.")
    print("Reminder: all generated prices are synthetic assumptions.")


if __name__ == "__main__":
    main()
