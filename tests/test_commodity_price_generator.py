import csv
import math

import pytest

from simulator.commodity_price_generator import (
    BASE_PRICE_ASSUMPTIONS_INR_PER_KG,
    generate_synthetic_local_market_prices,
    load_project_products_and_markets,
    write_market_price_csv,
)


def test_project_reference_data_loads_active_products_and_markets():
    products, markets = load_project_products_and_markets()

    assert set(products) == {
        "Apple",
        "Banana",
        "Orange",
        "Tomato",
        "Strawberry",
    }

    assert len(markets) == 9


def test_generator_creates_complete_product_market_matrix():
    products = ["Apple", "Banana"]
    markets = ["Delhi", "Lucknow", "Mumbai"]

    records = generate_synthetic_local_market_prices(
        products,
        markets,
        seed=10,
    )

    assert len(records) == 6

    pairs = {
        (row["product_name"], row["market_name"])
        for row in records
    }

    assert len(pairs) == 6


def test_generator_is_deterministic_for_same_seed():
    products = ["Apple", "Banana"]
    markets = ["Delhi", "Lucknow"]

    first = generate_synthetic_local_market_prices(
        products,
        markets,
        seed=123,
    )

    second = generate_synthetic_local_market_prices(
        products,
        markets,
        seed=123,
    )

    assert first == second


def test_different_seed_changes_generated_prices():
    products = ["Apple"]
    markets = ["Delhi", "Lucknow"]

    first = generate_synthetic_local_market_prices(
        products,
        markets,
        seed=100,
    )

    second = generate_synthetic_local_market_prices(
        products,
        markets,
        seed=200,
    )

    assert [
        row["price_per_kg"] for row in first
    ] != [
        row["price_per_kg"] for row in second
    ]


def test_generated_prices_are_positive_and_finite():
    records = generate_synthetic_local_market_prices(
        ["Apple", "Banana", "Orange"],
        ["Delhi", "Mumbai"],
        seed=50,
    )

    for row in records:
        price = float(row["price_per_kg"])

        assert math.isfinite(price)
        assert price > 0


def test_generated_records_are_explicitly_synthetic_in_inr_per_kg():
    records = generate_synthetic_local_market_prices(
        ["Apple"],
        ["Delhi"],
    )

    for row in records:
        assert row["currency"] == "INR"
        assert row["quantity_unit"] == "kg"
        assert row["price_source_type"] == "synthetic_simulated"
        assert row["market_country"] == "India"
        assert "not an observed" in row["source_note"]


def test_generated_prices_respect_configured_variation():
    products = ["Apple"]
    markets = ["Delhi", "Mumbai", "Lucknow"]
    variation = 0.10

    records = generate_synthetic_local_market_prices(
        products,
        markets,
        seed=42,
        variation_pct=variation,
    )

    base = BASE_PRICE_ASSUMPTIONS_INR_PER_KG["Apple"]

    for row in records:
        price = float(row["price_per_kg"])
        assert base * (1 - variation) - 0.01 <= price
        assert price <= base * (1 + variation) + 0.01


def test_generator_rejects_unknown_products():
    with pytest.raises(ValueError, match="No synthetic base-price"):
        generate_synthetic_local_market_prices(
            ["Watermelon"],
            ["Delhi"],
        )


@pytest.mark.parametrize(
    "variation",
    [-0.1, 1.0, float("nan"), float("inf"), True],
)
def test_generator_rejects_invalid_variation(variation):
    with pytest.raises(ValueError, match="variation_pct"):
        generate_synthetic_local_market_prices(
            ["Apple"],
            ["Delhi"],
            variation_pct=variation,
        )


def test_generator_rejects_duplicate_market_names():
    with pytest.raises(ValueError, match="duplicate"):
        generate_synthetic_local_market_prices(
            ["Apple"],
            ["Delhi", "Delhi"],
        )


def test_generator_rejects_invalid_seed():
    with pytest.raises(ValueError, match="seed"):
        generate_synthetic_local_market_prices(
            ["Apple"],
            ["Delhi"],
            seed=-1,
        )


def test_csv_writer_preserves_all_generated_records(tmp_path):
    records = generate_synthetic_local_market_prices(
        ["Apple", "Banana"],
        ["Delhi", "Lucknow"],
        seed=15,
    )

    output = tmp_path / "market_prices.csv"
    written_path = write_market_price_csv(records, output)

    with written_path.open(
        "r", encoding="utf-8", newline=""
    ) as file:
        saved_records = list(csv.DictReader(file))

    assert written_path.exists()
    assert len(saved_records) == len(records)
    assert saved_records[0]["currency"] == "INR"
