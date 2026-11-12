"""
Profiles the World Bank Pink Sheet monthly price workbook.

Prints a summary and writes docs/design/commodity_price_series_profile.csv.

Usage (from the repo root):
    python scripts/profile_commodity_prices.py
"""

import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
XLSX = REPO_ROOT / "data" / "raw" / "commodity_prices" / "CMO-Historical-Data-Monthly.xlsx"
OUT_FILE = REPO_ROOT / "docs" / "design" / "commodity_price_series_profile.csv"

NAME_ROW, UNIT_ROW, FIRST_DATA_ROW = 4, 5, 6  # zero-based rows in the sheet
PLACEHOLDERS = {"…", "..", "...", ""}

OUR_PRODUCTS = [
    "Apple", "Banana", "Tomato", "Strawberry", "Apricot", "Blueberry", "Grape",
    "Guava", "Mango", "Orange", "Broccoli", "Cabbage", "Carrot", "Cucumber",
    "Eggplant", "Garlic", "Spinach", "Sweet Pepper", "Green Beans", "Dry Onion",
]


def clean_name(value):
    text = str(value).strip()
    text = re.sub(r"\s*\*+\s*$", "", text)  # remove footnote marks like " **"
    return re.sub(r"\s+", " ", text).strip()


def clean_unit(value):
    return str(value).strip().strip("()").strip()


def main():
    raw = pd.read_excel(XLSX, sheet_name="Monthly Prices", header=None, dtype=object)

    names = [clean_name(v) for v in raw.iloc[NAME_ROW, 1:]]
    units = [clean_unit(v) for v in raw.iloc[UNIT_ROW, 1:]]

    body = raw.iloc[FIRST_DATA_ROW:].reset_index(drop=True)
    month_text = body.iloc[:, 0].astype(str).str.strip()
    valid = month_text.str.match(r"^\d{4}M(0[1-9]|1[0-2])$")
    skipped_rows = int((~valid).sum())
    body = body[valid].reset_index(drop=True)
    month_text = month_text[valid].reset_index(drop=True)
    price_month = pd.to_datetime(month_text.str.replace("M", "-", regex=False) + "-01")

    rows = []
    for j, (name, unit) in enumerate(zip(names, units), start=1):
        raw_col = body.iloc[:, j]
        as_text = raw_col.astype(str).str.strip()
        nums = pd.to_numeric(raw_col, errors="coerce")
        have = nums.notna()

        placeholder_cells = int(as_text.isin(PLACEHOLDERS).sum())
        blank_cells = int(raw_col.isna().sum())
        unexpected_text = int(((~have) & raw_col.notna() & ~as_text.isin(PLACEHOLDERS)).sum())

        if have.any():
            first, last = price_month[have].min(), price_month[have].max()
            span = (last.year - first.year) * 12 + (last.month - first.month) + 1
            rows.append({
                "commodity": name,
                "unit": unit,
                "first_month": first.strftime("%Y-%m"),
                "last_month": last.strftime("%Y-%m"),
                "months_with_price": int(have.sum()),
                "missing_inside_span": int(span - have.sum()),
                "placeholder_cells": placeholder_cells,
                "blank_cells": blank_cells,
                "unexpected_text_cells": unexpected_text,
                "latest_price": float(nums[have].iloc[-1]),
            })
        else:
            rows.append({
                "commodity": name, "unit": unit, "first_month": None, "last_month": None,
                "months_with_price": 0, "missing_inside_span": None,
                "placeholder_cells": placeholder_cells, "blank_cells": blank_cells,
                "unexpected_text_cells": unexpected_text, "latest_price": None,
            })

    profile = pd.DataFrame(rows)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    profile.to_csv(OUT_FILE, index=False)

    print(f"Series: {len(profile)}")
    print(f"Months: {len(price_month)} ({price_month.min():%Y-%m} to {price_month.max():%Y-%m})")
    print(f"Rows skipped (not a YYYYMmm month): {skipped_rows}")
    print(f"Duplicate commodity names after cleaning: {int(profile['commodity'].duplicated().sum())}")
    print()
    print("Series per unit:")
    print(profile["unit"].value_counts().to_string())
    print()
    print("Our 20 products found in this dataset:")
    for product in OUR_PRODUCTS:
        hits = profile[profile["commodity"].str.lower().str.contains(product.lower(), regex=False)]
        if hits.empty:
            print(f"  {product}: NO MATCH")
        else:
            for _, h in hits.iterrows():
                print(f"  {product}: {h['commodity']} ({h['unit']}), "
                      f"{h['first_month']} to {h['last_month']}, "
                      f"{h['months_with_price']} months, latest {h['latest_price']}")
    print()
    print(f"Full profile written to {OUT_FILE}")


if __name__ == "__main__":
    main()