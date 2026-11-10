"""
Loads data/reference/product_spoilage_reference.csv into
ATMOSYNC.RAW.PRODUCT_SPOILAGE_REFERENCE.

The table is fully reloaded on each run, so you can re-run it whenever the
CSV changes. Nothing is loaded if any row is invalid.

Usage:
    python ingestion/load_reference_csv.py --dry-run   # validate the CSV only
    python ingestion/load_reference_csv.py             # validate and load
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

DEFAULT_CSV = REPO_ROOT / "data" / "reference" / "product_spoilage_reference.csv"

COLUMNS = [
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

NUMERIC = {
    "recommended_temp_min_c",
    "recommended_temp_max_c",
    "best_temp_c",
    "humidity_min_pct",
    "humidity_max_pct",
    "shelf_life_min_hours",
    "shelf_life_max_hours",
}


def read_rows(path):
    """Return (rows, errors). rows are tuples in COLUMNS order."""
    rows, errors = [], []

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            return [], ["file is empty"]

        header = [h.strip() for h in header]
        if header != COLUMNS:
            return [], [f"header does not match.\n  expected: {COLUMNS}\n  found:    {header}"]

        for row in reader:
            line = reader.line_num
            if not any(cell.strip() for cell in row):
                continue  # skip blank lines

            if len(row) != len(COLUMNS):
                errors.append(
                    f"line {line}: expected {len(COLUMNS)} columns, found {len(row)} "
                    f"(starts with {row[0][:40]!r}). A note may contain a line break or an unquoted comma."
                )
                continue

            record = {}
            for col, value in zip(COLUMNS, row):
                value = value.strip()
                if col in NUMERIC:
                    if value == "":
                        record[col] = None
                    else:
                        try:
                            record[col] = float(value)
                        except ValueError:
                            errors.append(f"line {line}: {col} is not a number: {value!r}")
                            record[col] = None
                else:
                    record[col] = value or None

            if not record["product_name"]:
                errors.append(f"line {line}: product_name is empty")
                continue

            rows.append(tuple(record[c] for c in COLUMNS))

    return rows, errors


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
        cur.execute("DELETE FROM PRODUCT_SPOILAGE_REFERENCE")
        placeholders = ",".join(["%s"] * len(COLUMNS))
        sql = (
            f"INSERT INTO PRODUCT_SPOILAGE_REFERENCE ({','.join(COLUMNS)}) "
            f"VALUES ({placeholders})"
        )
        cur.executemany(sql, rows)
        cur.execute("SELECT COUNT(*) FROM PRODUCT_SPOILAGE_REFERENCE")
        count = cur.fetchone()[0]
        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Load the product spoilage reference CSV")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="path to the CSV file")
    parser.add_argument("--dry-run", action="store_true", help="validate only, do not load")
    args = parser.parse_args()

    rows, errors = read_rows(args.csv)

    if errors:
        print(f"CSV has {len(errors)} problem(s). Nothing was loaded:")
        for err in errors:
            print("  -", err)
        return 1

    print(f"CSV is valid: {len(rows)} products found.")
    for row in rows:
        print(f"  {row[0]} ({row[1]})")

    if args.dry_run:
        print("Dry run: nothing loaded.")
        return 0

    count = load(rows)
    print(f"Loaded {count} rows into PRODUCT_SPOILAGE_REFERENCE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())