"""
Loads the World Bank Pink Sheet monthly prices into
ATMOSYNC.RAW.RAW_COMMODITY_PRICE_MONTHLY in long format.

The table is fully reloaded on each run. If the loaded row count does not
match the rows read from the workbook, the load is rolled back.

Usage (from the repo root):
    python ingestion/load_commodity_prices.py --dry-run   # read and check only
    python ingestion/load_commodity_prices.py             # read, check and load
"""

import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd
import snowflake.connector
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

XLSX = REPO_ROOT / "data" / "raw" / "commodity_prices" / "CMO-Historical-Data-Monthly.xlsx"
SHEET = "Monthly Prices"
NAME_ROW, UNIT_ROW, FIRST_DATA_ROW = 4, 5, 6  # zero-based rows in the sheet
BATCH = 2000


def clean_name(value):
    text = str(value).strip()
    text = re.sub(r"\s*\*+\s*$", "", text)  # footnote marks such as " **"
    return re.sub(r"\s+", " ", text).strip()


def clean_unit(value):
    return str(value).strip().strip("()").strip()


def read_long():
    """Return (rows, series_count, month_count, skipped_rows)."""
    raw = pd.read_excel(XLSX, sheet_name=SHEET, header=None, dtype=object)

    names = [clean_name(v) for v in raw.iloc[NAME_ROW, 1:]]
    units = [clean_unit(v) for v in raw.iloc[UNIT_ROW, 1:]]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate commodity names after cleaning")

    body = raw.iloc[FIRST_DATA_ROW:].reset_index(drop=True)
    month_text = body.iloc[:, 0].astype(str).str.strip()
    valid = month_text.str.match(r"^\d{4}M(0[1-9]|1[0-2])$")
    skipped = int((~valid).sum())
    body = body[valid].reset_index(drop=True)
    month_text = month_text[valid].reset_index(drop=True)
    months = pd.to_datetime(month_text.str.replace("M", "-", regex=False) + "-01")

    rows = []
    for j, (name, unit) in enumerate(zip(names, units), start=1):
        prices = pd.to_numeric(body.iloc[:, j], errors="coerce")  # placeholders become NaN
        keep = prices.notna()
        for month, price in zip(months[keep], prices[keep]):
            rows.append((month.date().isoformat(), name, unit, float(price), XLSX.name))

    return rows, len(names), len(months), skipped


def load(rows):
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )
    conn.autocommit(False)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM RAW_COMMODITY_PRICE_MONTHLY")
        sql = (
            "INSERT INTO RAW_COMMODITY_PRICE_MONTHLY "
            "(PRICE_MONTH, COMMODITY, UNIT, PRICE, SOURCE_FILE) "
            "VALUES (%s, %s, %s, %s, %s)"
        )
        for i in range(0, len(rows), BATCH):
            cur.executemany(sql, rows[i:i + BATCH])
        cur.execute("SELECT COUNT(*) FROM RAW_COMMODITY_PRICE_MONTHLY")
        count = cur.fetchone()[0]
        if count != len(rows):
            raise RuntimeError(f"Row count mismatch: read {len(rows)}, table has {count}")
        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Load World Bank monthly prices")
    parser.add_argument("--dry-run", action="store_true", help="read and check only, do not load")
    args = parser.parse_args()

    rows, series_count, month_count, skipped = read_long()
    print(f"Series: {series_count} | months: {month_count} | rows skipped (bad month): {skipped}")
    print(f"Price rows to load (placeholders and blanks removed): {len(rows)}")
    print("Latest rows for banana and orange:")
    for r in [r for r in rows if r[1] in ("Banana, Europe", "Banana, US", "Orange")][-1:]:
        pass
    latest = {}
    for r in rows:
        if r[1] in ("Banana, Europe", "Banana, US", "Orange"):
            latest[r[1]] = r  # later months overwrite earlier ones
    for name in sorted(latest):
        print("  ", latest[name][:4])

    if args.dry_run:
        print("Dry run: nothing loaded.")
        return 0

    count = load(rows)
    print(f"Loaded {count} rows into RAW_COMMODITY_PRICE_MONTHLY.")
    return 0


if __name__ == "__main__":
    sys.exit(main())